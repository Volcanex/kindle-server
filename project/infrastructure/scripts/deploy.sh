#!/bin/bash

# Kindle Content Server Deployment Script
# This script deploys the Kindle Content Server to Google Cloud Platform

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRASTRUCTURE_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$INFRASTRUCTURE_DIR")"

# Default values
DEFAULT_ENVIRONMENT="dev"
DEFAULT_BUILD_ONLY="false"
DEFAULT_SKIP_TESTS="false"
DEFAULT_TERRAFORM_APPLY="true"

# Global variables
PROJECT_ID=""
REGION=""
ENVIRONMENT=""
BUILD_ONLY=""
SKIP_TESTS=""
TERRAFORM_APPLY=""
SERVICE_URL=""
BUILD_ID=""

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -e, --environment ENV    Deployment environment (dev/staging/prod) [default: dev]"
    echo "  -b, --build-only         Only build and push container, skip deployment"
    echo "  -s, --skip-tests         Skip running tests before deployment"
    echo "  -t, --skip-terraform     Skip Terraform infrastructure deployment"
    echo "  -h, --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                       Deploy to dev environment"
    echo "  $0 -e prod               Deploy to production environment"
    echo "  $0 -b                    Only build container image"
    echo "  $0 -e staging -s         Deploy to staging, skip tests"
}

# Function to parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -b|--build-only)
                BUILD_ONLY="true"
                shift
                ;;
            -s|--skip-tests)
                SKIP_TESTS="true"
                shift
                ;;
            -t|--skip-terraform)
                TERRAFORM_APPLY="false"
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Set defaults
    ENVIRONMENT="${ENVIRONMENT:-$DEFAULT_ENVIRONMENT}"
    BUILD_ONLY="${BUILD_ONLY:-$DEFAULT_BUILD_ONLY}"
    SKIP_TESTS="${SKIP_TESTS:-$DEFAULT_SKIP_TESTS}"
    TERRAFORM_APPLY="${TERRAFORM_APPLY:-$DEFAULT_TERRAFORM_APPLY}"
}

# Function to load configuration
load_config() {
    print_status "Loading configuration..."
    
    # Try to get project ID from gcloud config
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "")
    if [ -z "$PROJECT_ID" ]; then
        print_error "No project ID configured. Run 'gcloud config set project PROJECT_ID' or setup.sh first."
        exit 1
    fi
    
    # Get region from gcloud config
    REGION=$(gcloud config get-value compute/region 2>/dev/null || echo "us-central1")
    
    # Load Terraform variables if they exist
    local tf_vars_file="$INFRASTRUCTURE_DIR/terraform/terraform.tfvars"
    if [ -f "$tf_vars_file" ]; then
        while IFS='=' read -r key value; do
            case "$key" in
                project_id)
                    PROJECT_ID=$(echo "$value" | tr -d '"' | xargs)
                    ;;
                region)
                    REGION=$(echo "$value" | tr -d '"' | xargs)
                    ;;
            esac
        done < "$tf_vars_file"
    fi
    
    print_success "Configuration loaded - Project: $PROJECT_ID, Region: $REGION, Environment: $ENVIRONMENT"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    local missing_tools=()
    
    if ! command -v gcloud >/dev/null 2>&1; then
        missing_tools+=("gcloud")
    fi
    
    if ! command -v docker >/dev/null 2>&1; then
        missing_tools+=("docker")
    fi
    
    if [ "$TERRAFORM_APPLY" = "true" ] && ! command -v terraform >/dev/null 2>&1; then
        missing_tools+=("terraform")
    fi
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        exit 1
    fi
    
    # Check if authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        print_error "Not authenticated with Google Cloud. Run 'gcloud auth login'."
        exit 1
    fi
    
    # Check if Docker is configured for Artifact Registry
    if ! docker-credential-gcloud list | grep -q "${REGION}-docker.pkg.dev"; then
        print_status "Configuring Docker for Artifact Registry..."
        gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet
    fi
    
    print_success "Prerequisites check passed"
}

# Function to run tests
run_tests() {
    if [ "$SKIP_TESTS" = "true" ]; then
        print_warning "Skipping tests"
        return 0
    fi
    
    print_status "Running tests..."
    
    local backend_dir="$PROJECT_ROOT/backend"
    if [ ! -d "$backend_dir" ]; then
        print_warning "Backend directory not found, skipping tests"
        return 0
    fi
    
    cd "$backend_dir"
    
    # Check if requirements.txt exists
    if [ ! -f "requirements.txt" ]; then
        print_warning "requirements.txt not found, skipping tests"
        cd - > /dev/null
        return 0
    fi
    
    # Install test dependencies if they exist
    if [ -f "requirements-dev.txt" ]; then
        print_status "Installing test dependencies..."
        pip install -r requirements-dev.txt >/dev/null 2>&1 || true
    fi
    
    # Run pytest if available
    if command -v pytest >/dev/null 2>&1 && [ -d "tests" ]; then
        print_status "Running pytest..."
        pytest tests/ -v --tb=short || {
            print_error "Tests failed"
            cd - > /dev/null
            exit 1
        }
    else
        print_warning "No pytest or tests directory found, skipping unit tests"
    fi
    
    # Run linting if available
    if command -v flake8 >/dev/null 2>&1; then
        print_status "Running linting..."
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics || {
            print_warning "Linting issues found, but continuing..."
        }
    fi
    
    cd - > /dev/null
    print_success "Tests completed"
}

# Function to build Docker image
build_image() {
    print_status "Building Docker image..."
    
    local backend_dir="$PROJECT_ROOT/backend"
    if [ ! -d "$backend_dir" ]; then
        print_error "Backend directory not found at $backend_dir"
        exit 1
    fi
    
    # Generate image tag
    local git_commit
    git_commit=$(git rev-parse --short HEAD 2>/dev/null || echo "latest")
    local image_tag="${REGION}-docker.pkg.dev/${PROJECT_ID}/kindle-server-repo/kindle-server:${git_commit}"
    local latest_tag="${REGION}-docker.pkg.dev/${PROJECT_ID}/kindle-server-repo/kindle-server:latest"
    local env_tag="${REGION}-docker.pkg.dev/${PROJECT_ID}/kindle-server-repo/kindle-server:${ENVIRONMENT}-${git_commit}"
    
    print_status "Building image: $image_tag"
    
    # Build the image
    docker build \
        -f "$INFRASTRUCTURE_DIR/docker/Dockerfile" \
        -t "$image_tag" \
        -t "$latest_tag" \
        -t "$env_tag" \
        --build-arg ENVIRONMENT="$ENVIRONMENT" \
        "$backend_dir" || {
            print_error "Docker build failed"
            exit 1
        }
    
    print_success "Docker image built successfully"
    
    # Push the image
    print_status "Pushing image to Artifact Registry..."
    docker push "$image_tag" || {
        print_error "Failed to push image"
        exit 1
    }
    
    docker push "$latest_tag" || {
        print_warning "Failed to push latest tag"
    }
    
    docker push "$env_tag" || {
        print_warning "Failed to push environment tag"
    }
    
    print_success "Image pushed successfully"
    
    # Store image info for later use
    echo "$image_tag" > /tmp/kindle-server-image-tag
}

# Function to deploy infrastructure with Terraform
deploy_infrastructure() {
    if [ "$TERRAFORM_APPLY" = "false" ]; then
        print_warning "Skipping Terraform deployment"
        return 0
    fi
    
    print_status "Deploying infrastructure with Terraform..."
    
    cd "$INFRASTRUCTURE_DIR/terraform"
    
    # Check if Terraform is initialized
    if [ ! -d ".terraform" ]; then
        print_status "Initializing Terraform..."
        terraform init
    fi
    
    # Plan the deployment
    print_status "Planning Terraform deployment..."
    terraform plan -var="environment=$ENVIRONMENT" -out=tfplan || {
        print_error "Terraform plan failed"
        cd - > /dev/null
        exit 1
    }
    
    # Apply the plan
    print_status "Applying Terraform plan..."
    terraform apply tfplan || {
        print_error "Terraform apply failed"
        cd - > /dev/null
        exit 1
    }
    
    # Get outputs
    local cloud_run_url
    cloud_run_url=$(terraform output -raw cloud_run_url 2>/dev/null || echo "")
    if [ -n "$cloud_run_url" ]; then
        SERVICE_URL="$cloud_run_url"
        echo "$SERVICE_URL" > /tmp/kindle-server-service-url
    fi
    
    cd - > /dev/null
    print_success "Infrastructure deployed successfully"
}

# Function to deploy application to Cloud Run
deploy_application() {
    if [ "$BUILD_ONLY" = "true" ]; then
        print_warning "Build-only mode, skipping application deployment"
        return 0
    fi
    
    print_status "Deploying application to Cloud Run..."
    
    # Get image tag
    local image_tag
    if [ -f "/tmp/kindle-server-image-tag" ]; then
        image_tag=$(cat /tmp/kindle-server-image-tag)
    else
        local git_commit
        git_commit=$(git rev-parse --short HEAD 2>/dev/null || echo "latest")
        image_tag="${REGION}-docker.pkg.dev/${PROJECT_ID}/kindle-server-repo/kindle-server:${git_commit}"
    fi
    
    # Set environment-specific configuration
    local min_instances=0
    local max_instances=3
    local memory="512Mi"
    local cpu="1"
    local service_name="kindle-server-service-${ENVIRONMENT}"
    
    case "$ENVIRONMENT" in
        prod)
            min_instances=1
            max_instances=10
            memory="1Gi"
            cpu="2"
            ;;
        staging)
            min_instances=0
            max_instances=5
            memory="512Mi"
            cpu="1"
            ;;
    esac
    
    print_status "Deploying to Cloud Run service: $service_name"
    
    # Deploy to Cloud Run
    gcloud run deploy "$service_name" \
        --image="$image_tag" \
        --platform=managed \
        --region="$REGION" \
        --allow-unauthenticated \
        --set-env-vars="ENVIRONMENT=$ENVIRONMENT,PROJECT_ID=$PROJECT_ID,REGION=$REGION" \
        --memory="$memory" \
        --cpu="$cpu" \
        --min-instances="$min_instances" \
        --max-instances="$max_instances" \
        --port=8080 \
        --timeout=300 \
        --concurrency=100 \
        --execution-environment=gen2 \
        --labels="environment=$ENVIRONMENT,app=kindle-server" \
        --quiet || {
            print_error "Cloud Run deployment failed"
            exit 1
        }
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe "$service_name" \
        --region="$REGION" \
        --format='value(status.url)')
    
    print_success "Application deployed successfully"
    echo "Service URL: $SERVICE_URL"
}

# Function to run health checks
run_health_checks() {
    if [ -z "$SERVICE_URL" ]; then
        print_warning "No service URL available, skipping health checks"
        return 0
    fi
    
    print_status "Running health checks..."
    
    # Wait for service to be ready
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        print_status "Health check attempt $attempt/$max_attempts..."
        
        if curl -f "$SERVICE_URL/health" >/dev/null 2>&1; then
            print_success "Health check passed"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            print_error "Health check failed after $max_attempts attempts"
            exit 1
        fi
        
        sleep 10
        ((attempt++))
    done
    
    # Run additional checks
    if curl -f "$SERVICE_URL/ready" >/dev/null 2>&1; then
        print_success "Readiness check passed"
    else
        print_warning "Readiness check failed"
    fi
    
    print_success "Health checks completed"
}

# Function to run smoke tests
run_smoke_tests() {
    if [ -z "$SERVICE_URL" ]; then
        print_warning "No service URL available, skipping smoke tests"
        return 0
    fi
    
    print_status "Running smoke tests..."
    
    # Test basic endpoints
    local endpoints=("/health" "/ready" "/api/status")
    
    for endpoint in "${endpoints[@]}"; do
        local url="${SERVICE_URL}${endpoint}"
        print_status "Testing endpoint: $endpoint"
        
        if curl -f "$url" >/dev/null 2>&1; then
            print_success "✓ $endpoint"
        else
            print_warning "✗ $endpoint (may not be implemented yet)"
        fi
    done
    
    print_success "Smoke tests completed"
}

# Function to cleanup temporary files
cleanup() {
    rm -f /tmp/kindle-server-image-tag
    rm -f /tmp/kindle-server-service-url
}

# Function to display deployment summary
display_summary() {
    echo ""
    print_success "Deployment completed successfully!"
    echo ""
    echo "Deployment Summary:"
    echo "  Environment: $ENVIRONMENT"
    echo "  Project ID: $PROJECT_ID"
    echo "  Region: $REGION"
    if [ -n "$SERVICE_URL" ]; then
        echo "  Service URL: $SERVICE_URL"
    fi
    if [ -n "$BUILD_ID" ]; then
        echo "  Build ID: $BUILD_ID"
    fi
    echo ""
    
    if [ "$BUILD_ONLY" = "true" ]; then
        echo "Container image built and pushed successfully."
        echo "To deploy, run: $0 -e $ENVIRONMENT -t"
    else
        echo "Next steps:"
        echo "  1. Test the application: curl $SERVICE_URL/health"
        echo "  2. Monitor logs: gcloud logs tail --follow --format=json"
        echo "  3. View metrics in Cloud Console: https://console.cloud.google.com/run"
    fi
    
    echo ""
    print_warning "Important:"
    echo "  - Monitor the application for the first few minutes after deployment"
    echo "  - Check Cloud Console for any errors or performance issues"
    echo "  - Update DNS records if using a custom domain"
}

# Main function
main() {
    echo "=================================================="
    echo "Kindle Content Server Deployment"
    echo "=================================================="
    echo ""
    
    parse_args "$@"
    load_config
    check_prerequisites
    run_tests
    build_image
    deploy_infrastructure
    deploy_application
    run_health_checks
    run_smoke_tests
    display_summary
}

# Handle script interruption
trap 'print_error "Deployment interrupted"; cleanup; exit 1' INT TERM EXIT

# Run main function
main "$@"

# Remove trap and cleanup on successful completion
trap - INT TERM EXIT
cleanup
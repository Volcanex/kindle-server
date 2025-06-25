#!/bin/bash

# Kindle Content Server Infrastructure Setup Script
# This script sets up the Google Cloud infrastructure for the Kindle Content Server

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
DEFAULT_PROJECT_ID=""
DEFAULT_REGION="us-central1"
DEFAULT_ZONE="us-central1-a"
DEFAULT_ENVIRONMENT="dev"

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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    local missing_tools=()
    
    if ! command_exists gcloud; then
        missing_tools+=("gcloud (Google Cloud SDK)")
    fi
    
    if ! command_exists terraform; then
        missing_tools+=("terraform")
    fi
    
    if ! command_exists docker; then
        missing_tools+=("docker")
    fi
    
    if ! command_exists kubectl; then
        missing_tools+=("kubectl")
    fi
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        print_error "Missing required tools:"
        for tool in "${missing_tools[@]}"; do
            echo "  - $tool"
        done
        echo ""
        echo "Please install the missing tools and run this script again."
        exit 1
    fi
    
    print_success "All prerequisites are installed"
}

# Function to get user input with default value
get_input() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    
    if [ -n "$default" ]; then
        read -p "$prompt [$default]: " input
        if [ -z "$input" ]; then
            input="$default"
        fi
    else
        read -p "$prompt: " input
        while [ -z "$input" ]; do
            read -p "$prompt (required): " input
        done
    fi
    
    eval "$var_name='$input'"
}

# Function to configure Google Cloud project
configure_gcloud() {
    print_status "Configuring Google Cloud..."
    
    # Check if user is authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        print_warning "Not authenticated with Google Cloud"
        read -p "Do you want to authenticate now? (y/n): " auth_choice
        if [[ "$auth_choice" =~ ^[Yy]$ ]]; then
            gcloud auth login
        else
            print_error "Authentication required to proceed"
            exit 1
        fi
    fi
    
    # Get project configuration
    get_input "Enter Google Cloud Project ID" "$DEFAULT_PROJECT_ID" "PROJECT_ID"
    get_input "Enter region" "$DEFAULT_REGION" "REGION"
    get_input "Enter zone" "$DEFAULT_ZONE" "ZONE"
    get_input "Enter environment (dev/staging/prod)" "$DEFAULT_ENVIRONMENT" "ENVIRONMENT"
    
    # Set gcloud configuration
    gcloud config set project "$PROJECT_ID"
    gcloud config set compute/region "$REGION"
    gcloud config set compute/zone "$ZONE"
    
    print_success "Google Cloud configuration completed"
}

# Function to enable required APIs
enable_apis() {
    print_status "Enabling required Google Cloud APIs..."
    
    local apis=(
        "run.googleapis.com"
        "cloudbuild.googleapis.com"
        "storage.googleapis.com"
        "sql.googleapis.com"
        "artifactregistry.googleapis.com"
        "cloudresourcemanager.googleapis.com"
        "compute.googleapis.com"
        "logging.googleapis.com"
        "monitoring.googleapis.com"
        "secretmanager.googleapis.com"
        "iam.googleapis.com"
        "servicenetworking.googleapis.com"
        "vpcaccess.googleapis.com"
        "cloudkms.googleapis.com"
        "binaryauthorization.googleapis.com"
        "containeranalysis.googleapis.com"
    )
    
    for api in "${apis[@]}"; do
        print_status "Enabling $api..."
        if gcloud services enable "$api" --quiet; then
            print_success "Enabled $api"
        else
            print_error "Failed to enable $api"
            exit 1
        fi
    done
    
    print_success "All required APIs enabled"
}

# Function to create service accounts
create_service_accounts() {
    print_status "Creating service accounts..."
    
    local service_accounts=(
        "kindle-server-cloud-run:Cloud Run Service Account"
        "kindle-server-cloud-build:Cloud Build Service Account"
        "kindle-server-backup:Backup Service Account"
        "kindle-server-monitoring:Monitoring Service Account"
    )
    
    for sa_info in "${service_accounts[@]}"; do
        local sa_name="${sa_info%%:*}"
        local sa_description="${sa_info##*:}"
        
        if gcloud iam service-accounts describe "${sa_name}@${PROJECT_ID}.iam.gserviceaccount.com" >/dev/null 2>&1; then
            print_warning "Service account $sa_name already exists"
        else
            print_status "Creating service account: $sa_name"
            gcloud iam service-accounts create "$sa_name" \
                --description="$sa_description" \
                --display-name="$sa_name"
            print_success "Created service account: $sa_name"
        fi
    done
}

# Function to initialize Terraform
init_terraform() {
    print_status "Initializing Terraform..."
    
    cd "$INFRASTRUCTURE_DIR/terraform"
    
    # Create terraform.tfvars file
    cat > terraform.tfvars <<EOF
project_id   = "$PROJECT_ID"
region       = "$REGION"
zone         = "$ZONE"
environment  = "$ENVIRONMENT"
app_name     = "kindle-server"
EOF
    
    # Initialize Terraform
    terraform init
    
    # Validate Terraform configuration
    terraform validate
    
    print_success "Terraform initialized successfully"
    
    cd - > /dev/null
}

# Function to create Cloud Storage buckets for Terraform state
create_terraform_backend() {
    print_status "Setting up Terraform backend..."
    
    local backend_bucket="${PROJECT_ID}-terraform-state"
    
    if gsutil ls "gs://$backend_bucket" >/dev/null 2>&1; then
        print_warning "Terraform state bucket already exists"
    else
        print_status "Creating Terraform state bucket: $backend_bucket"
        gsutil mb -p "$PROJECT_ID" -l "$REGION" "gs://$backend_bucket"
        
        # Enable versioning
        gsutil versioning set on "gs://$backend_bucket"
        
        print_success "Created Terraform state bucket"
    fi
    
    # Update backend configuration
    cat > "$INFRASTRUCTURE_DIR/terraform/backend.tf" <<EOF
terraform {
  backend "gcs" {
    bucket = "$backend_bucket"
    prefix = "kindle-server/$ENVIRONMENT"
  }
}
EOF
    
    print_success "Terraform backend configured"
}

# Function to set up Docker registry
setup_docker_registry() {
    print_status "Setting up Docker registry..."
    
    local repo_name="kindle-server-repo"
    
    if gcloud artifacts repositories describe "$repo_name" --location="$REGION" >/dev/null 2>&1; then
        print_warning "Artifact Registry repository already exists"
    else
        print_status "Creating Artifact Registry repository: $repo_name"
        gcloud artifacts repositories create "$repo_name" \
            --repository-format=docker \
            --location="$REGION" \
            --description="Docker repository for Kindle Content Server"
        print_success "Created Artifact Registry repository"
    fi
    
    # Configure Docker authentication
    gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet
    
    print_success "Docker registry setup completed"
}

# Function to create Cloud Build trigger
setup_cloud_build() {
    print_status "Setting up Cloud Build..."
    
    local trigger_name="kindle-server-trigger"
    
    # Check if trigger already exists
    if gcloud builds triggers describe "$trigger_name" >/dev/null 2>&1; then
        print_warning "Cloud Build trigger already exists"
    else
        print_status "Creating Cloud Build trigger: $trigger_name"
        
        # Create trigger configuration
        cat > /tmp/trigger-config.yaml <<EOF
name: $trigger_name
description: "Trigger for Kindle Content Server"
github:
  owner: YOUR_GITHUB_USERNAME
  name: kindle-content-server
  push:
    branch: "^(main|staging|develop)$"
filename: infrastructure/cloudbuild.yaml
substitutions:
  _REGION: $REGION
  _ENVIRONMENT: $ENVIRONMENT
EOF
        
        print_warning "Please update the GitHub configuration in /tmp/trigger-config.yaml and run:"
        print_warning "gcloud builds triggers import --source=/tmp/trigger-config.yaml"
    fi
    
    print_success "Cloud Build setup completed"
}

# Function to create initial secrets
create_secrets() {
    print_status "Creating initial secrets..."
    
    local secrets=(
        "kindle-server-db-password"
        "kindle-server-jwt-secret"
        "kindle-server-flask-secret"
    )
    
    for secret in "${secrets[@]}"; do
        if gcloud secrets describe "$secret" >/dev/null 2>&1; then
            print_warning "Secret $secret already exists"
        else
            print_status "Creating secret: $secret"
            
            # Generate random secret value
            local secret_value
            secret_value=$(openssl rand -base64 32)
            
            echo -n "$secret_value" | gcloud secrets create "$secret" \
                --data-file=- \
                --labels="app=kindle-server,environment=$ENVIRONMENT"
            
            print_success "Created secret: $secret"
        fi
    done
}

# Function to setup monitoring
setup_monitoring() {
    print_status "Setting up monitoring workspace..."
    
    # Create monitoring workspace (if it doesn't exist)
    if ! gcloud alpha monitoring workspaces list --filter="name:projects/$PROJECT_ID" --format="value(name)" | grep -q .; then
        print_status "Creating monitoring workspace..."
        gcloud alpha monitoring workspaces create --project="$PROJECT_ID" || true
    fi
    
    print_success "Monitoring setup completed"
}

# Function to validate setup
validate_setup() {
    print_status "Validating setup..."
    
    local validation_errors=()
    
    # Check if project exists and is accessible
    if ! gcloud projects describe "$PROJECT_ID" >/dev/null 2>&1; then
        validation_errors+=("Cannot access project: $PROJECT_ID")
    fi
    
    # Check if required APIs are enabled
    local required_apis=("run.googleapis.com" "cloudbuild.googleapis.com" "storage.googleapis.com")
    for api in "${required_apis[@]}"; do
        if ! gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
            validation_errors+=("API not enabled: $api")
        fi
    done
    
    # Check if Terraform configuration is valid
    if ! (cd "$INFRASTRUCTURE_DIR/terraform" && terraform validate >/dev/null 2>&1); then
        validation_errors+=("Terraform configuration is invalid")
    fi
    
    if [ ${#validation_errors[@]} -gt 0 ]; then
        print_error "Validation failed:"
        for error in "${validation_errors[@]}"; do
            echo "  - $error"
        done
        exit 1
    fi
    
    print_success "Setup validation passed"
}

# Function to display next steps
display_next_steps() {
    echo ""
    print_success "Setup completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Review and customize the Terraform configuration in $INFRASTRUCTURE_DIR/terraform/"
    echo "2. Plan the infrastructure deployment:"
    echo "   cd $INFRASTRUCTURE_DIR/terraform && terraform plan"
    echo "3. Deploy the infrastructure:"
    echo "   cd $INFRASTRUCTURE_DIR/terraform && terraform apply"
    echo "4. Set up your application code and run the deployment script:"
    echo "   $SCRIPT_DIR/deploy.sh"
    echo ""
    echo "Configuration summary:"
    echo "  Project ID: $PROJECT_ID"
    echo "  Region: $REGION"
    echo "  Zone: $ZONE"
    echo "  Environment: $ENVIRONMENT"
    echo ""
    echo "Important files:"
    echo "  - Terraform variables: $INFRASTRUCTURE_DIR/terraform/terraform.tfvars"
    echo "  - Backend config: $INFRASTRUCTURE_DIR/terraform/backend.tf"
    echo ""
    print_warning "Remember to:"
    echo "  - Update GitHub repository settings in Cloud Build trigger"
    echo "  - Configure your domain name in DNS settings"
    echo "  - Review security policies and IAM roles"
    echo "  - Set up monitoring alerts and notification channels"
}

# Main function
main() {
    echo "=================================================="
    echo "Kindle Content Server Infrastructure Setup"
    echo "=================================================="
    echo ""
    
    check_prerequisites
    configure_gcloud
    enable_apis
    create_service_accounts
    create_terraform_backend
    init_terraform
    setup_docker_registry
    setup_cloud_build
    create_secrets
    setup_monitoring
    validate_setup
    display_next_steps
}

# Handle script interruption
trap 'print_error "Script interrupted"; exit 1' INT TERM

# Run main function
main "$@"
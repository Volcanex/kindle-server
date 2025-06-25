#!/bin/bash

# Kindle Content Server Cleanup Script
# This script safely removes the Kindle Content Server infrastructure from Google Cloud

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

# Global variables
PROJECT_ID=""
REGION=""
ENVIRONMENT=""
FORCE_DELETE="false"
PRESERVE_DATA="false"
DRY_RUN="false"

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
    echo "  -e, --environment ENV    Environment to cleanup (dev/staging/prod) [required]"
    echo "  -f, --force              Force deletion without confirmation prompts"
    echo "  -p, --preserve-data      Preserve data (databases and storage buckets)"
    echo "  -d, --dry-run            Show what would be deleted without actually deleting"
    echo "  -h, --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -e dev                Cleanup dev environment with confirmations"
    echo "  $0 -e staging -f         Force cleanup staging environment"
    echo "  $0 -e prod -p            Cleanup prod but preserve data"
    echo "  $0 -e dev -d             Dry run for dev environment"
    echo ""
    echo "WARNING: This script will permanently delete cloud resources!"
    echo "         Make sure you have backups of any important data."
}

# Function to parse command line arguments
parse_args() {
    if [ $# -eq 0 ]; then
        show_usage
        exit 1
    fi
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -f|--force)
                FORCE_DELETE="true"
                shift
                ;;
            -p|--preserve-data)
                PRESERVE_DATA="true"
                shift
                ;;
            -d|--dry-run)
                DRY_RUN="true"
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
    
    if [ -z "$ENVIRONMENT" ]; then
        print_error "Environment is required. Use -e option."
        show_usage
        exit 1
    fi
}

# Function to load configuration
load_config() {
    print_status "Loading configuration..."
    
    # Get project ID from gcloud config
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "")
    if [ -z "$PROJECT_ID" ]; then
        print_error "No project ID configured. Run 'gcloud config set project PROJECT_ID' first."
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

# Function to confirm deletion
confirm_deletion() {
    if [ "$FORCE_DELETE" = "true" ] || [ "$DRY_RUN" = "true" ]; then
        return 0
    fi
    
    echo ""
    print_warning "⚠️  DANGER ZONE ⚠️"
    echo ""
    echo "This will delete the following from project '$PROJECT_ID':"
    echo "  • Cloud Run services for environment: $ENVIRONMENT"
    echo "  • Container images in Artifact Registry"
    echo "  • IAM service accounts and bindings"
    echo "  • VPC networks and firewall rules"
    echo "  • Load balancers and SSL certificates"
    
    if [ "$PRESERVE_DATA" = "false" ]; then
        echo "  • 🔥 Cloud SQL databases and data"
        echo "  • 🔥 Cloud Storage buckets and files"
        echo "  • 🔥 Secret Manager secrets"
    else
        echo "  • (Preserving databases, storage, and secrets)"
    fi
    
    echo ""
    print_warning "This action CANNOT be undone!"
    echo ""
    
    # Double confirmation for production
    if [ "$ENVIRONMENT" = "prod" ]; then
        echo "You are about to delete the PRODUCTION environment."
        read -p "Type 'DELETE PRODUCTION' to confirm: " confirmation
        if [ "$confirmation" != "DELETE PRODUCTION" ]; then
            print_error "Confirmation failed. Aborting."
            exit 1
        fi
    fi
    
    read -p "Are you sure you want to proceed? (type 'yes' to confirm): " confirmation
    if [ "$confirmation" != "yes" ]; then
        print_error "Confirmation failed. Aborting."
        exit 1
    fi
    
    echo ""
    print_status "Proceeding with cleanup..."
}

# Function to execute or show command
execute_command() {
    local description="$1"
    local command="$2"
    
    if [ "$DRY_RUN" = "true" ]; then
        print_status "[DRY RUN] $description"
        echo "  Command: $command"
        return 0
    fi
    
    print_status "$description"
    if eval "$command"; then
        print_success "✓ $description"
        return 0
    else
        print_warning "✗ Failed: $description"
        return 1
    fi
}

# Function to cleanup Cloud Run services
cleanup_cloud_run() {
    print_status "Cleaning up Cloud Run services..."
    
    local services
    services=$(gcloud run services list --region="$REGION" --filter="metadata.labels.environment:$ENVIRONMENT OR metadata.labels.app:kindle-server" --format="value(metadata.name)" 2>/dev/null || echo "")
    
    if [ -z "$services" ]; then
        print_warning "No Cloud Run services found"
        return 0
    fi
    
    for service in $services; do
        execute_command "Deleting Cloud Run service: $service" \
            "gcloud run services delete '$service' --region='$REGION' --quiet"
    done
}

# Function to cleanup container images
cleanup_container_images() {
    print_status "Cleaning up container images..."
    
    local repo_name="kindle-server-repo"
    
    # Check if repository exists
    if ! gcloud artifacts repositories describe "$repo_name" --location="$REGION" >/dev/null 2>&1; then
        print_warning "Artifact Registry repository not found"
        return 0
    fi
    
    # List and delete images
    local images
    images=$(gcloud artifacts docker images list "${REGION}-docker.pkg.dev/${PROJECT_ID}/${repo_name}" --format="value(IMAGE)" 2>/dev/null || echo "")
    
    if [ -n "$images" ]; then
        for image in $images; do
            execute_command "Deleting container image: $image" \
                "gcloud artifacts docker images delete '$image' --quiet"
        done
    fi
    
    # Delete the repository
    execute_command "Deleting Artifact Registry repository: $repo_name" \
        "gcloud artifacts repositories delete '$repo_name' --location='$REGION' --quiet"
}

# Function to cleanup Cloud SQL (if not preserving data)
cleanup_cloud_sql() {
    if [ "$PRESERVE_DATA" = "true" ]; then
        print_warning "Skipping Cloud SQL cleanup (preserve-data flag set)"
        return 0
    fi
    
    print_status "Cleaning up Cloud SQL instances..."
    
    local instances
    instances=$(gcloud sql instances list --filter="labels.app:kindle-server OR labels.environment:$ENVIRONMENT" --format="value(name)" 2>/dev/null || echo "")
    
    if [ -z "$instances" ]; then
        print_warning "No Cloud SQL instances found"
        return 0
    fi
    
    for instance in $instances; do
        # Disable deletion protection first
        execute_command "Disabling deletion protection for: $instance" \
            "gcloud sql instances patch '$instance' --no-deletion-protection --quiet"
        
        execute_command "Deleting Cloud SQL instance: $instance" \
            "gcloud sql instances delete '$instance' --quiet"
    done
}

# Function to cleanup Cloud Storage (if not preserving data)
cleanup_cloud_storage() {
    if [ "$PRESERVE_DATA" = "true" ]; then
        print_warning "Skipping Cloud Storage cleanup (preserve-data flag set)"
        return 0
    fi
    
    print_status "Cleaning up Cloud Storage buckets..."
    
    local buckets
    buckets=$(gsutil ls -p "$PROJECT_ID" 2>/dev/null | grep "kindle-server" || echo "")
    
    if [ -z "$buckets" ]; then
        print_warning "No Cloud Storage buckets found"
        return 0
    fi
    
    for bucket in $buckets; do
        bucket_name=$(echo "$bucket" | sed 's|gs://||' | sed 's|/||')
        
        execute_command "Removing all objects from bucket: $bucket_name" \
            "gsutil -m rm -r '$bucket' || true"
        
        execute_command "Deleting bucket: $bucket_name" \
            "gsutil rb 'gs://$bucket_name' || true"
    done
}

# Function to cleanup VPC and networking
cleanup_networking() {
    print_status "Cleaning up networking resources..."
    
    # Get VPC name pattern
    local vpc_pattern="kindle-server-vpc"
    
    # Cleanup firewall rules
    local firewall_rules
    firewall_rules=$(gcloud compute firewall-rules list --filter="network~'$vpc_pattern'" --format="value(name)" 2>/dev/null || echo "")
    
    for rule in $firewall_rules; do
        execute_command "Deleting firewall rule: $rule" \
            "gcloud compute firewall-rules delete '$rule' --quiet"
    done
    
    # Cleanup VPC connector
    local connectors
    connectors=$(gcloud compute networks vpc-access connectors list --region="$REGION" --filter="name~'kindle-server'" --format="value(name)" 2>/dev/null || echo "")
    
    for connector in $connectors; do
        execute_command "Deleting VPC connector: $connector" \
            "gcloud compute networks vpc-access connectors delete '$connector' --region='$REGION' --quiet"
    done
    
    # Cleanup Cloud NAT
    local nat_gateways
    nat_gateways=$(gcloud compute routers list --filter="name~'kindle-server'" --format="value(name)" 2>/dev/null || echo "")
    
    for router in $nat_gateways; do
        execute_command "Deleting Cloud Router: $router" \
            "gcloud compute routers delete '$router' --region='$REGION' --quiet"
    done
    
    # Cleanup subnets
    local subnets
    subnets=$(gcloud compute networks subnets list --filter="network~'$vpc_pattern'" --format="value(name)" 2>/dev/null || echo "")
    
    for subnet in $subnets; do
        execute_command "Deleting subnet: $subnet" \
            "gcloud compute networks subnets delete '$subnet' --region='$REGION' --quiet"
    done
    
    # Cleanup VPC network
    local networks
    networks=$(gcloud compute networks list --filter="name~'$vpc_pattern'" --format="value(name)" 2>/dev/null || echo "")
    
    for network in $networks; do
        execute_command "Deleting VPC network: $network" \
            "gcloud compute networks delete '$network' --quiet"
    done
}

# Function to cleanup load balancers
cleanup_load_balancers() {
    print_status "Cleaning up load balancers..."
    
    # Cleanup global forwarding rules
    local forwarding_rules
    forwarding_rules=$(gcloud compute forwarding-rules list --global --filter="name~'kindle-server'" --format="value(name)" 2>/dev/null || echo "")
    
    for rule in $forwarding_rules; do
        execute_command "Deleting global forwarding rule: $rule" \
            "gcloud compute forwarding-rules delete '$rule' --global --quiet"
    done
    
    # Cleanup target HTTPS proxies
    local https_proxies
    https_proxies=$(gcloud compute target-https-proxies list --filter="name~'kindle-server'" --format="value(name)" 2>/dev/null || echo "")
    
    for proxy in $https_proxies; do
        execute_command "Deleting target HTTPS proxy: $proxy" \
            "gcloud compute target-https-proxies delete '$proxy' --quiet"
    done
    
    # Cleanup URL maps
    local url_maps
    url_maps=$(gcloud compute url-maps list --filter="name~'kindle-server'" --format="value(name)" 2>/dev/null || echo "")
    
    for url_map in $url_maps; do
        execute_command "Deleting URL map: $url_map" \
            "gcloud compute url-maps delete '$url_map' --quiet"
    done
    
    # Cleanup backend services
    local backend_services
    backend_services=$(gcloud compute backend-services list --filter="name~'kindle-server'" --format="value(name)" 2>/dev/null || echo "")
    
    for service in $backend_services; do
        execute_command "Deleting backend service: $service" \
            "gcloud compute backend-services delete '$service' --quiet"
    done
    
    # Cleanup health checks
    local health_checks
    health_checks=$(gcloud compute health-checks list --filter="name~'kindle-server'" --format="value(name)" 2>/dev/null || echo "")
    
    for check in $health_checks; do
        execute_command "Deleting health check: $check" \
            "gcloud compute health-checks delete '$check' --quiet"
    done
    
    # Cleanup SSL certificates
    local ssl_certs
    ssl_certs=$(gcloud compute ssl-certificates list --filter="name~'kindle-server'" --format="value(name)" 2>/dev/null || echo "")
    
    for cert in $ssl_certs; do
        execute_command "Deleting SSL certificate: $cert" \
            "gcloud compute ssl-certificates delete '$cert' --quiet"
    done
    
    # Cleanup global addresses
    local addresses
    addresses=$(gcloud compute addresses list --global --filter="name~'kindle-server'" --format="value(name)" 2>/dev/null || echo "")
    
    for address in $addresses; do
        execute_command "Deleting global address: $address" \
            "gcloud compute addresses delete '$address' --global --quiet"
    done
}

# Function to cleanup secrets (if not preserving data)
cleanup_secrets() {
    if [ "$PRESERVE_DATA" = "true" ]; then
        print_warning "Skipping secrets cleanup (preserve-data flag set)"
        return 0
    fi
    
    print_status "Cleaning up secrets..."
    
    local secrets
    secrets=$(gcloud secrets list --filter="labels.app:kindle-server OR name~'kindle-server'" --format="value(name)" 2>/dev/null || echo "")
    
    if [ -z "$secrets" ]; then
        print_warning "No secrets found"
        return 0
    fi
    
    for secret in $secrets; do
        execute_command "Deleting secret: $secret" \
            "gcloud secrets delete '$secret' --quiet"
    done
}

# Function to cleanup IAM service accounts
cleanup_iam() {
    print_status "Cleaning up IAM service accounts..."
    
    local service_accounts
    service_accounts=$(gcloud iam service-accounts list --filter="email~'kindle-server'" --format="value(email)" 2>/dev/null || echo "")
    
    if [ -z "$service_accounts" ]; then
        print_warning "No service accounts found"
        return 0
    fi
    
    for sa in $service_accounts; do
        execute_command "Deleting service account: $sa" \
            "gcloud iam service-accounts delete '$sa' --quiet"
    done
}

# Function to cleanup with Terraform
cleanup_terraform() {
    print_status "Cleaning up infrastructure with Terraform..."
    
    local tf_dir="$INFRASTRUCTURE_DIR/terraform"
    if [ ! -d "$tf_dir" ] || [ ! -f "$tf_dir/terraform.tfstate" ]; then
        print_warning "No Terraform state found, skipping Terraform cleanup"
        return 0
    fi
    
    cd "$tf_dir"
    
    if [ "$DRY_RUN" = "true" ]; then
        print_status "[DRY RUN] Would run: terraform destroy"
        cd - > /dev/null
        return 0
    fi
    
    # Plan destroy
    print_status "Planning Terraform destroy..."
    terraform plan -destroy -var="environment=$ENVIRONMENT" -out=tfplan-destroy || {
        print_warning "Terraform destroy plan failed, continuing with manual cleanup"
        cd - > /dev/null
        return 1
    }
    
    # Apply destroy
    print_status "Applying Terraform destroy..."
    terraform apply tfplan-destroy || {
        print_warning "Terraform destroy failed, some resources may remain"
        cd - > /dev/null
        return 1
    }
    
    cd - > /dev/null
    print_success "Terraform destroy completed"
}

# Function to cleanup Cloud Build triggers
cleanup_cloud_build() {
    print_status "Cleaning up Cloud Build triggers..."
    
    local triggers
    triggers=$(gcloud builds triggers list --filter="name~'kindle-server'" --format="value(name)" 2>/dev/null || echo "")
    
    if [ -z "$triggers" ]; then
        print_warning "No Cloud Build triggers found"
        return 0
    fi
    
    for trigger in $triggers; do
        execute_command "Deleting Cloud Build trigger: $trigger" \
            "gcloud builds triggers delete '$trigger' --quiet"
    done
}

# Function to display cleanup summary
display_summary() {
    echo ""
    if [ "$DRY_RUN" = "true" ]; then
        print_success "Dry run completed!"
        echo ""
        echo "The above resources would be deleted in a real cleanup operation."
        echo "To perform the actual cleanup, run the same command without --dry-run."
    else
        print_success "Cleanup completed!"
        echo ""
        echo "Cleanup Summary:"
        echo "  Environment: $ENVIRONMENT"
        echo "  Project ID: $PROJECT_ID"
        echo "  Region: $REGION"
        echo "  Data preserved: $PRESERVE_DATA"
        echo ""
        
        if [ "$PRESERVE_DATA" = "true" ]; then
            print_warning "Data preservation was enabled. The following may still exist:"
            echo "  - Cloud SQL databases"
            echo "  - Cloud Storage buckets"
            echo "  - Secret Manager secrets"
            echo ""
            echo "To remove these, run the cleanup script again without --preserve-data"
        fi
    fi
    
    echo ""
    print_warning "Next steps:"
    echo "  - Verify all resources have been deleted in the Cloud Console"
    echo "  - Check for any remaining resources that may incur charges"
    echo "  - Remove any custom domains or DNS records"
    echo "  - Update any external systems that referenced these services"
}

# Main function
main() {
    echo "=================================================="
    echo "Kindle Content Server Cleanup"
    echo "=================================================="
    echo ""
    
    parse_args "$@"
    load_config
    confirm_deletion
    
    # Try Terraform cleanup first
    cleanup_terraform
    
    # Manual cleanup for any remaining resources
    cleanup_cloud_run
    cleanup_container_images
    cleanup_load_balancers
    cleanup_networking
    cleanup_cloud_sql
    cleanup_cloud_storage
    cleanup_secrets
    cleanup_iam
    cleanup_cloud_build
    
    display_summary
}

# Handle script interruption
trap 'print_error "Cleanup interrupted"; exit 1' INT TERM

# Run main function
main "$@"
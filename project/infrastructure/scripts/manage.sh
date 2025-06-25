#!/bin/bash

# Kindle Content Server Management Script
# This script provides various management operations for the deployed infrastructure

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

# Global variables
PROJECT_ID=""
REGION=""
ENVIRONMENT=""
ACTION=""

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
    echo "Usage: $0 [ACTION] [OPTIONS]"
    echo ""
    echo "Actions:"
    echo "  status                   Show deployment status"
    echo "  logs                     View service logs"
    echo "  scale                    Scale the service"
    echo "  rollback                 Rollback to previous revision"
    echo "  backup                   Create database backup"
    echo "  restore                  Restore from backup"
    echo "  secrets                  Manage secrets"
    echo "  monitoring               Show monitoring information"
    echo "  health                   Check service health"
    echo "  shell                    Connect to service shell"
    echo ""
    echo "Options:"
    echo "  -e, --environment ENV    Environment (dev/staging/prod) [default: dev]"
    echo "  -h, --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 status -e prod        Show production deployment status"
    echo "  $0 logs -e staging       View staging logs"
    echo "  $0 scale -e dev          Scale dev environment"
    echo "  $0 backup -e prod        Create production backup"
}

# Function to parse command line arguments
parse_args() {
    if [ $# -eq 0 ]; then
        show_usage
        exit 1
    fi
    
    ACTION="$1"
    shift
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
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
    
    ENVIRONMENT="${ENVIRONMENT:-dev}"
}

# Function to load configuration
load_config() {
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "")
    if [ -z "$PROJECT_ID" ]; then
        print_error "No project ID configured. Run 'gcloud config set project PROJECT_ID' first."
        exit 1
    fi
    
    REGION=$(gcloud config get-value compute/region 2>/dev/null || echo "us-central1")
}

# Function to show deployment status
show_status() {
    print_status "Checking deployment status for environment: $ENVIRONMENT"
    echo ""
    
    # Cloud Run services
    echo "=== Cloud Run Services ==="
    gcloud run services list \
        --region="$REGION" \
        --filter="metadata.labels.environment:$ENVIRONMENT OR metadata.labels.app:kindle-server" \
        --format="table(
            metadata.name:label='SERVICE',
            status.url:label='URL',
            status.latestReadyRevisionName:label='REVISION',
            spec.template.spec.containers[0].image:label='IMAGE',
            metadata.creationTimestamp:label='CREATED'
        )" || print_warning "No Cloud Run services found"
    
    echo ""
    
    # Cloud SQL instances
    echo "=== Cloud SQL Instances ==="
    gcloud sql instances list \
        --filter="labels.app:kindle-server OR labels.environment:$ENVIRONMENT" \
        --format="table(
            name:label='INSTANCE',
            databaseVersion:label='VERSION',
            region:label='REGION',
            settings.tier:label='TIER',
            state:label='STATE'
        )" || print_warning "No Cloud SQL instances found"
    
    echo ""
    
    # Storage buckets
    echo "=== Storage Buckets ==="
    gsutil ls -L -p "$PROJECT_ID" | grep "kindle-server" | head -20 || print_warning "No storage buckets found"
    
    echo ""
    
    # Service accounts
    echo "=== Service Accounts ==="
    gcloud iam service-accounts list \
        --filter="email~'kindle-server'" \
        --format="table(
            email:label='EMAIL',
            displayName:label='DISPLAY_NAME',
            disabled:label='DISABLED'
        )" || print_warning "No service accounts found"
}

# Function to view logs
show_logs() {
    print_status "Viewing logs for environment: $ENVIRONMENT"
    
    local service_name="kindle-server-service-${ENVIRONMENT}"
    
    # Check if service exists
    if ! gcloud run services describe "$service_name" --region="$REGION" >/dev/null 2>&1; then
        print_error "Service $service_name not found in region $REGION"
        exit 1
    fi
    
    echo ""
    echo "Showing recent logs (press Ctrl+C to stop):"
    echo "=========================================="
    
    # Show logs from Cloud Logging
    gcloud logs tail "projects/$PROJECT_ID/logs/run.googleapis.com%2Frequests" \
        --filter="
            resource.type=\"cloud_run_revision\" 
            resource.labels.service_name=\"$service_name\"
            resource.labels.location=\"$REGION\"
        " \
        --format="value(timestamp,severity,textPayload,jsonPayload.message)" \
        --follow
}

# Function to scale service
scale_service() {
    print_status "Scaling service for environment: $ENVIRONMENT"
    
    local service_name="kindle-server-service-${ENVIRONMENT}"
    
    echo "Current service configuration:"
    gcloud run services describe "$service_name" \
        --region="$REGION" \
        --format="table(
            spec.template.metadata.annotations['autoscaling.knative.dev/minScale']:label='MIN_SCALE',
            spec.template.metadata.annotations['autoscaling.knative.dev/maxScale']:label='MAX_SCALE',
            spec.template.spec.containers[0].resources.limits.memory:label='MEMORY',
            spec.template.spec.containers[0].resources.limits.cpu:label='CPU'
        )"
    
    echo ""
    
    # Get scaling parameters
    read -p "Enter minimum instances [current]: " min_instances
    read -p "Enter maximum instances [current]: " max_instances
    read -p "Enter memory limit (e.g., 512Mi, 1Gi) [current]: " memory
    read -p "Enter CPU limit (e.g., 1, 2) [current]: " cpu
    
    # Build update command
    local update_args=()
    
    if [ -n "$min_instances" ]; then
        update_args+=(--min-instances="$min_instances")
    fi
    
    if [ -n "$max_instances" ]; then
        update_args+=(--max-instances="$max_instances")
    fi
    
    if [ -n "$memory" ]; then
        update_args+=(--memory="$memory")
    fi
    
    if [ -n "$cpu" ]; then
        update_args+=(--cpu="$cpu")
    fi
    
    if [ ${#update_args[@]} -eq 0 ]; then
        print_warning "No changes specified"
        return 0
    fi
    
    # Apply scaling
    print_status "Applying scaling changes..."
    gcloud run services update "$service_name" \
        --region="$REGION" \
        "${update_args[@]}" \
        --quiet
    
    print_success "Service scaled successfully"
}

# Function to rollback service
rollback_service() {
    print_status "Rolling back service for environment: $ENVIRONMENT"
    
    local service_name="kindle-server-service-${ENVIRONMENT}"
    
    # List recent revisions
    echo "Recent revisions:"
    gcloud run revisions list \
        --service="$service_name" \
        --region="$REGION" \
        --limit=10 \
        --format="table(
            metadata.name:label='REVISION',
            spec.containers[0].image:label='IMAGE',
            metadata.creationTimestamp:label='CREATED',
            status.conditions[0].status:label='READY'
        )"
    
    echo ""
    read -p "Enter revision name to rollback to: " revision_name
    
    if [ -z "$revision_name" ]; then
        print_error "Revision name is required"
        exit 1
    fi
    
    # Confirm rollback
    read -p "Are you sure you want to rollback to $revision_name? (y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        print_warning "Rollback cancelled"
        return 0
    fi
    
    # Perform rollback
    print_status "Rolling back to revision: $revision_name"
    gcloud run services update-traffic "$service_name" \
        --region="$REGION" \
        --to-revisions="$revision_name=100" \
        --quiet
    
    print_success "Rollback completed successfully"
}

# Function to create database backup
create_backup() {
    print_status "Creating database backup for environment: $ENVIRONMENT"
    
    # Find Cloud SQL instances
    local instances
    instances=$(gcloud sql instances list \
        --filter="labels.app:kindle-server OR labels.environment:$ENVIRONMENT" \
        --format="value(name)" 2>/dev/null || echo "")
    
    if [ -z "$instances" ]; then
        print_error "No Cloud SQL instances found"
        exit 1
    fi
    
    for instance in $instances; do
        local backup_id="backup-$(date +%Y%m%d-%H%M%S)"
        
        print_status "Creating backup for instance: $instance"
        gcloud sql backups create \
            --instance="$instance" \
            --description="Manual backup created on $(date)" \
            --quiet
        
        print_success "Backup created for instance: $instance"
    done
}

# Function to restore from backup
restore_backup() {
    print_status "Restoring from backup for environment: $ENVIRONMENT"
    
    # List instances
    local instances
    instances=$(gcloud sql instances list \
        --filter="labels.app:kindle-server OR labels.environment:$ENVIRONMENT" \
        --format="value(name)" 2>/dev/null || echo "")
    
    if [ -z "$instances" ]; then
        print_error "No Cloud SQL instances found"
        exit 1
    fi
    
    echo "Available instances:"
    for instance in $instances; do
        echo "  - $instance"
    done
    
    read -p "Enter instance name: " instance_name
    
    if [ -z "$instance_name" ]; then
        print_error "Instance name is required"
        exit 1
    fi
    
    # List backups
    echo ""
    echo "Available backups for $instance_name:"
    gcloud sql backups list \
        --instance="$instance_name" \
        --limit=10 \
        --format="table(
            id:label='BACKUP_ID',
            type:label='TYPE',
            windowStartTime:label='CREATED',
            status:label='STATUS'
        )"
    
    read -p "Enter backup ID: " backup_id
    
    if [ -z "$backup_id" ]; then
        print_error "Backup ID is required"
        exit 1
    fi
    
    # Confirm restore
    print_warning "⚠️  This will overwrite the current database!"
    read -p "Are you sure you want to restore from backup $backup_id? (y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        print_warning "Restore cancelled"
        return 0
    fi
    
    # Perform restore
    print_status "Restoring from backup: $backup_id"
    gcloud sql backups restore "$backup_id" \
        --restore-instance="$instance_name" \
        --quiet
    
    print_success "Restore completed successfully"
}

# Function to manage secrets
manage_secrets() {
    print_status "Managing secrets for environment: $ENVIRONMENT"
    
    echo "What would you like to do?"
    echo "1. List secrets"
    echo "2. View secret value"
    echo "3. Update secret value"
    echo "4. Create new secret"
    echo "5. Delete secret"
    
    read -p "Enter choice (1-5): " choice
    
    case $choice in
        1)
            # List secrets
            echo ""
            echo "Secrets for Kindle Server:"
            gcloud secrets list \
                --filter="labels.app:kindle-server OR name~'kindle-server'" \
                --format="table(
                    name:label='SECRET_NAME',
                    createTime:label='CREATED',
                    labels:label='LABELS'
                )"
            ;;
        2)
            # View secret value
            read -p "Enter secret name: " secret_name
            if [ -n "$secret_name" ]; then
                print_status "Secret value for $secret_name:"
                gcloud secrets versions access latest --secret="$secret_name" || print_error "Failed to access secret"
            fi
            ;;
        3)
            # Update secret value
            read -p "Enter secret name: " secret_name
            read -s -p "Enter new secret value: " secret_value
            echo ""
            if [ -n "$secret_name" ] && [ -n "$secret_value" ]; then
                echo -n "$secret_value" | gcloud secrets versions add "$secret_name" --data-file=-
                print_success "Secret updated successfully"
            fi
            ;;
        4)
            # Create new secret
            read -p "Enter secret name: " secret_name
            read -s -p "Enter secret value: " secret_value
            echo ""
            if [ -n "$secret_name" ] && [ -n "$secret_value" ]; then
                echo -n "$secret_value" | gcloud secrets create "$secret_name" \
                    --data-file=- \
                    --labels="app=kindle-server,environment=$ENVIRONMENT"
                print_success "Secret created successfully"
            fi
            ;;
        5)
            # Delete secret
            read -p "Enter secret name: " secret_name
            if [ -n "$secret_name" ]; then
                read -p "Are you sure you want to delete secret '$secret_name'? (y/N): " confirm
                if [[ "$confirm" =~ ^[Yy]$ ]]; then
                    gcloud secrets delete "$secret_name" --quiet
                    print_success "Secret deleted successfully"
                fi
            fi
            ;;
        *)
            print_error "Invalid choice"
            ;;
    esac
}

# Function to show monitoring information
show_monitoring() {
    print_status "Monitoring information for environment: $ENVIRONMENT"
    
    local service_name="kindle-server-service-${ENVIRONMENT}"
    
    echo ""
    echo "=== Service Metrics ==="
    
    # Get service URL
    local service_url
    service_url=$(gcloud run services describe "$service_name" \
        --region="$REGION" \
        --format="value(status.url)" 2>/dev/null || echo "")
    
    if [ -n "$service_url" ]; then
        echo "Service URL: $service_url"
        echo ""
        
        # Try to get basic metrics via health endpoint
        print_status "Checking service health..."
        if curl -f "$service_url/health" >/dev/null 2>&1; then
            print_success "✓ Health check passed"
        else
            print_error "✗ Health check failed"
        fi
        
        if curl -f "$service_url/ready" >/dev/null 2>&1; then
            print_success "✓ Readiness check passed"
        else
            print_warning "✗ Readiness check failed"
        fi
    fi
    
    echo ""
    echo "=== Recent Error Logs ==="
    gcloud logs read "projects/$PROJECT_ID/logs/run.googleapis.com%2Frequests" \
        --filter="
            resource.type=\"cloud_run_revision\" 
            resource.labels.service_name=\"$service_name\"
            severity>=ERROR
        " \
        --limit=10 \
        --format="table(timestamp,severity,textPayload)" || print_warning "No error logs found"
    
    echo ""
    echo "For detailed monitoring, visit:"
    echo "https://console.cloud.google.com/run/detail/$REGION/$service_name/metrics?project=$PROJECT_ID"
}

# Function to check service health
check_health() {
    print_status "Checking service health for environment: $ENVIRONMENT"
    
    local service_name="kindle-server-service-${ENVIRONMENT}"
    
    # Get service details
    local service_url
    service_url=$(gcloud run services describe "$service_name" \
        --region="$REGION" \
        --format="value(status.url)" 2>/dev/null || echo "")
    
    if [ -z "$service_url" ]; then
        print_error "Service not found: $service_name"
        exit 1
    fi
    
    echo "Service URL: $service_url"
    echo ""
    
    # Check various endpoints
    local endpoints=("/health" "/ready" "/api/status")
    
    for endpoint in "${endpoints[@]}"; do
        local url="${service_url}${endpoint}"
        print_status "Testing endpoint: $endpoint"
        
        local response_code
        response_code=$(curl -s -o /dev/null -w "%{http_code}" "$url" || echo "000")
        
        case $response_code in
            200)
                print_success "✓ $endpoint - OK ($response_code)"
                ;;
            404)
                print_warning "? $endpoint - Not Found ($response_code)"
                ;;
            000)
                print_error "✗ $endpoint - Connection Failed"
                ;;
            *)
                print_error "✗ $endpoint - Error ($response_code)"
                ;;
        esac
    done
    
    echo ""
    print_status "Response time test..."
    time curl -s "$service_url/health" >/dev/null || print_warning "Response time test failed"
}

# Function to connect to service shell
connect_shell() {
    print_status "Connecting to service shell for environment: $ENVIRONMENT"
    
    local service_name="kindle-server-service-${ENVIRONMENT}"
    
    # Get latest revision
    local revision
    revision=$(gcloud run services describe "$service_name" \
        --region="$REGION" \
        --format="value(status.latestReadyRevisionName)" 2>/dev/null || echo "")
    
    if [ -z "$revision" ]; then
        print_error "No revision found for service: $service_name"
        exit 1
    fi
    
    print_status "Connecting to revision: $revision"
    
    # Use gcloud run services proxy for local connection
    print_status "Starting local proxy to service..."
    echo "Once the proxy is running, you can connect to the service at http://localhost:8080"
    echo "Press Ctrl+C to stop the proxy"
    
    gcloud run services proxy "$service_name" \
        --region="$REGION" \
        --port=8080
}

# Main function
main() {
    parse_args "$@"
    load_config
    
    case "$ACTION" in
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        scale)
            scale_service
            ;;
        rollback)
            rollback_service
            ;;
        backup)
            create_backup
            ;;
        restore)
            restore_backup
            ;;
        secrets)
            manage_secrets
            ;;
        monitoring)
            show_monitoring
            ;;
        health)
            check_health
            ;;
        shell)
            connect_shell
            ;;
        *)
            print_error "Unknown action: $ACTION"
            show_usage
            exit 1
            ;;
    esac
}

# Handle script interruption
trap 'print_error "Operation interrupted"; exit 1' INT TERM

# Run main function
main "$@"
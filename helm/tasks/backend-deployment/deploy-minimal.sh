#!/bin/bash
# Minimal deployment script for Kindle Content Server backend
# This version uses SQLite for simplicity

set -e

# Configuration
PROJECT_ID="geo-butler"
INSTANCE_NAME="kindle-backend-server"
ZONE="us-central1-a"
MACHINE_TYPE="e2-micro"
IMAGE_FAMILY="ubuntu-2204-lts"
IMAGE_PROJECT="ubuntu-os-cloud"
DISK_SIZE="10GB"
DISK_TYPE="pd-standard"

# Storage configuration
BUCKET_NAME="kindle-content-storage-$(date +%s)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if gcloud is configured
check_gcloud() {
    log_info "Checking gcloud configuration..."
    
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI is not installed"
        exit 1
    fi
    
    CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
    if [[ "$CURRENT_PROJECT" != "$PROJECT_ID" ]]; then
        log_warn "Setting project to $PROJECT_ID"
        gcloud config set project $PROJECT_ID
    fi
    
    log_info "Using project: $PROJECT_ID"
}

# Create firewall rules
create_firewall_rules() {
    log_info "Creating firewall rules..."
    
    # HTTP traffic
    if ! gcloud compute firewall-rules describe allow-http &>/dev/null; then
        gcloud compute firewall-rules create allow-http \
            --allow tcp:80 \
            --source-ranges 0.0.0.0/0 \
            --description "Allow HTTP traffic"
    fi
    
    # HTTPS traffic
    if ! gcloud compute firewall-rules describe allow-https &>/dev/null; then
        gcloud compute firewall-rules create allow-https \
            --allow tcp:443 \
            --source-ranges 0.0.0.0/0 \
            --description "Allow HTTPS traffic"
    fi
    
    # Application port
    if ! gcloud compute firewall-rules describe allow-app-port &>/dev/null; then
        gcloud compute firewall-rules create allow-app-port \
            --allow tcp:8080 \
            --source-ranges 0.0.0.0/0 \
            --description "Allow application port 8080"
    fi
    
    log_info "Firewall rules created successfully"
}

# Create service account
create_service_account() {
    log_info "Creating service account..."
    
    SERVICE_ACCOUNT_NAME="kindle-backend-service"
    SERVICE_ACCOUNT_EMAIL="$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com"
    
    if ! gcloud iam service-accounts describe $SERVICE_ACCOUNT_EMAIL &>/dev/null; then
        gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
            --display-name="Kindle Backend Service Account" \
            --description="Service account for Kindle backend application"
        
        # Grant necessary permissions
        gcloud projects add-iam-policy-binding $PROJECT_ID \
            --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
            --role="roles/storage.admin"
        
        gcloud projects add-iam-policy-binding $PROJECT_ID \
            --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
            --role="roles/logging.logWriter"
        
        # Create and download key
        gcloud iam service-accounts keys create service-account-key.json \
            --iam-account=$SERVICE_ACCOUNT_EMAIL
        
        log_info "Service account created: $SERVICE_ACCOUNT_EMAIL"
    else
        log_warn "Service account already exists: $SERVICE_ACCOUNT_EMAIL"
        # Try to create key anyway
        gcloud iam service-accounts keys create service-account-key.json \
            --iam-account=$SERVICE_ACCOUNT_EMAIL || true
    fi
    
    echo $SERVICE_ACCOUNT_EMAIL
}

# Create compute instance
create_instance() {
    log_info "Creating Compute Engine instance..."
    
    SERVICE_ACCOUNT_EMAIL=$(create_service_account)
    
    if ! gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE &>/dev/null; then
        gcloud compute instances create $INSTANCE_NAME \
            --zone=$ZONE \
            --machine-type=$MACHINE_TYPE \
            --network-interface=network-tier=PREMIUM,subnet=default \
            --maintenance-policy=MIGRATE \
            --provisioning-model=STANDARD \
            --service-account=$SERVICE_ACCOUNT_EMAIL \
            --scopes=https://www.googleapis.com/auth/cloud-platform \
            --create-disk=auto-delete=yes,boot=yes,device-name=$INSTANCE_NAME,image=projects/$IMAGE_PROJECT/global/images/family/$IMAGE_FAMILY,mode=rw,size=$DISK_SIZE,type=projects/$PROJECT_ID/zones/$ZONE/diskTypes/$DISK_TYPE \
            --metadata-from-file startup-script=startup-script.sh \
            --tags=http-server,https-server \
            --reservation-affinity=any
        
        log_info "Compute instance created: $INSTANCE_NAME"
        
        # Wait for instance to be ready
        log_info "Waiting for instance to be ready..."
        gcloud compute instances wait-until-running $INSTANCE_NAME --zone=$ZONE
        
        # Get external IP
        EXTERNAL_IP=$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --format='get(networkInterfaces[0].accessConfigs[0].natIP)')
        log_info "Instance external IP: $EXTERNAL_IP"
        
    else
        log_warn "Compute instance already exists: $INSTANCE_NAME"
        EXTERNAL_IP=$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --format='get(networkInterfaces[0].accessConfigs[0].natIP)')
    fi
    
    echo $EXTERNAL_IP
}

# Wait for startup script to complete
wait_for_startup() {
    local instance_ip=$1
    log_info "Waiting for startup script to complete..."
    
    # Wait up to 10 minutes for startup script
    local max_attempts=60
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="test -f /var/log/startup-script.log && grep -q 'Startup script completed successfully' /var/log/startup-script.log" &>/dev/null; then
            log_info "Startup script completed successfully"
            return 0
        fi
        
        log_info "Waiting for startup script... (attempt $((attempt + 1))/$max_attempts)"
        sleep 10
        ((attempt++))
    done
    
    log_error "Startup script did not complete within expected time"
    log_info "Checking startup script logs..."
    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="tail -20 /var/log/startup-script.log" || true
    return 1
}

# Deploy application code
deploy_application() {
    log_info "Deploying application code..."
    
    # Create deployment package
    local backend_dir="/home/gabriel/Desktop/kindle/project/backend"
    local temp_dir=$(mktemp -d)
    
    # Copy backend files
    cp -r "$backend_dir"/* "$temp_dir/"
    
    # Create deployment archive
    cd "$temp_dir"
    tar -czf kindle-backend.tar.gz .
    
    # Upload to instance
    gcloud compute scp kindle-backend.tar.gz $INSTANCE_NAME:/tmp/ --zone=$ZONE --scp-flag="-o StrictHostKeyChecking=no"
    
    # Extract and setup on instance
    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="
        cd /opt/kindle-backend
        sudo tar -xzf /tmp/kindle-backend.tar.gz
        sudo chown -R kindle:kindle /opt/kindle-backend
        
        # Install dependencies
        sudo -u kindle bash -c '
            source venv/bin/activate
            pip install -r requirements.txt
        '
    "
    
    # Cleanup
    rm -rf "$temp_dir"
    
    log_info "Application code deployed successfully"
}

# Create configuration files
create_config_files() {
    log_info "Creating configuration files..."
    
    # Create environment file (using SQLite for simplicity)
    cat > env_config << EOF
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=$(openssl rand -base64 32)
PORT=8080

# Database Configuration (SQLite for simplicity)
DATABASE_URL=sqlite:////opt/kindle-backend/data/kindle.db

# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=$PROJECT_ID
GCS_BUCKET_NAME=$BUCKET_NAME
GOOGLE_APPLICATION_CREDENTIALS=/opt/kindle-backend/service-account-key.json

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Application Configuration
LOG_LEVEL=INFO
ALLOWED_ORIGINS=*
EOF
    
    # Upload configuration
    gcloud compute scp env_config $INSTANCE_NAME:/tmp/ --zone=$ZONE --scp-flag="-o StrictHostKeyChecking=no"
    gcloud compute scp service-account-key.json $INSTANCE_NAME:/tmp/ --zone=$ZONE --scp-flag="-o StrictHostKeyChecking=no"
    
    # Move files to proper location
    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="
        sudo mkdir -p /opt/kindle-backend/data
        sudo mv /tmp/env_config /opt/kindle-backend/.env
        sudo mv /tmp/service-account-key.json /opt/kindle-backend/
        sudo chown -R kindle:kindle /opt/kindle-backend
        sudo chmod 600 /opt/kindle-backend/.env /opt/kindle-backend/service-account-key.json
    "
    
    log_info "Configuration files created"
}

# Create systemd service
create_systemd_service() {
    log_info "Creating systemd service..."
    
    cat > kindle-backend.service << 'EOF'
[Unit]
Description=Kindle Content Server Backend
After=network.target

[Service]
Type=notify
User=kindle
Group=kindle
WorkingDirectory=/opt/kindle-backend
Environment=PATH=/opt/kindle-backend/venv/bin
EnvironmentFile=/opt/kindle-backend/.env
ExecStart=/opt/kindle-backend/venv/bin/gunicorn --bind 0.0.0.0:8080 --workers 2 --timeout 120 --access-logfile /var/log/kindle-backend/access.log --error-logfile /var/log/kindle-backend/error.log app:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # Upload and install service
    gcloud compute scp kindle-backend.service $INSTANCE_NAME:/tmp/ --zone=$ZONE --scp-flag="-o StrictHostKeyChecking=no"
    
    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="
        sudo mv /tmp/kindle-backend.service /etc/systemd/system/
        sudo systemctl daemon-reload
        sudo systemctl enable kindle-backend
    "
    
    log_info "Systemd service created and enabled"
}

# Initialize database
initialize_database() {
    log_info "Initializing database..."
    
    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="
        cd /opt/kindle-backend
        sudo -u kindle bash -c '
            source venv/bin/activate
            python -c \"
from app import create_app
from models import db

app = create_app()
with app.app_context():
    db.create_all()
    print('Database tables created successfully')
\"
        '
    "
    
    log_info "Database initialized successfully"
}

# Start services
start_services() {
    log_info "Starting services..."
    
    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="
        sudo systemctl start kindle-backend
        sleep 5
        sudo systemctl status kindle-backend --no-pager
    "
    
    log_info "Services started successfully"
}

# Test deployment
test_deployment() {
    log_info "Testing deployment..."
    
    local external_ip=$1
    
    # Wait a moment for service to start
    sleep 10
    
    # Test health endpoint
    log_info "Testing health endpoint..."
    if curl -f "http://$external_ip:8080/health" > /dev/null 2>&1; then
        log_info "Health endpoint is accessible"
    else
        log_warn "Health endpoint test failed, checking service status..."
        gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="sudo systemctl status kindle-backend --no-pager" || true
        gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="sudo tail -20 /var/log/kindle-backend/error.log" || true
    fi
    
    # Test root endpoint
    log_info "Testing root endpoint..."
    if curl -f "http://$external_ip:8080/" > /dev/null 2>&1; then
        log_info "Root endpoint is accessible"
    else
        log_warn "Root endpoint test failed"
    fi
    
    log_info "Deployment testing completed"
}

# Generate deployment report
generate_report() {
    local external_ip=$1
    
    cat > deployment-report.md << EOF
# Kindle Content Server Backend Deployment Report

## Deployment Summary
- **Instance Name**: $INSTANCE_NAME
- **Zone**: $ZONE
- **Machine Type**: $MACHINE_TYPE
- **External IP**: $external_ip
- **Project**: $PROJECT_ID

## Service URLs
- **HTTP**: http://$external_ip:8080
- **Health Check**: http://$external_ip:8080/health
- **API Base**: http://$external_ip:8080/api

## Database Details
- **Type**: SQLite
- **Location**: /opt/kindle-backend/data/kindle.db

## Storage
- **Bucket**: gs://$BUCKET_NAME

## Service Management
- **Service**: kindle-backend.service
- **Logs**: /var/log/kindle-backend/
- **Configuration**: /opt/kindle-backend/.env

## Commands
\`\`\`bash
# Check service status
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="sudo systemctl status kindle-backend"

# View logs
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="sudo tail -f /var/log/kindle-backend/error.log"

# Restart service
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="sudo systemctl restart kindle-backend"
\`\`\`

## Connection Information for Frontend
\`\`\`
BACKEND_URL=http://$external_ip:8080
API_BASE_URL=http://$external_ip:8080/api
\`\`\`

Deployment completed at: $(date)
EOF
    
    log_info "Deployment report generated: deployment-report.md"
}

# Main deployment function
main() {
    log_info "Starting Kindle Content Server backend deployment (minimal version)..."
    
    check_gcloud
    create_firewall_rules
    
    external_ip=$(create_instance)
    wait_for_startup "$external_ip"
    
    deploy_application
    create_config_files
    create_systemd_service
    initialize_database
    start_services
    
    test_deployment "$external_ip"
    generate_report "$external_ip"
    
    log_info "Deployment completed successfully!"
    log_info "Backend is accessible at: http://$external_ip:8080"
    log_info "Check deployment-report.md for full details"
}

# Run deployment
main "$@"
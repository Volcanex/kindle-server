#!/bin/bash

# Kindle Content Server - Google Cloud Deployment Script
# This script automates the deployment process to Google Cloud

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Kindle Content Server Deployment Script${NC}"
echo "================================================"

# Check if required tools are installed
check_dependencies() {
    echo -e "${YELLOW}📋 Checking dependencies...${NC}"
    
    if ! command -v gcloud &> /dev/null; then
        echo -e "${RED}❌ Google Cloud CLI not found. Please install: https://cloud.google.com/sdk/docs/install${NC}"
        exit 1
    fi
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker not found. Please install Docker${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Dependencies check passed${NC}"
}

# Configuration
setup_config() {
    echo -e "${YELLOW}⚙️  Setting up configuration...${NC}"
    
    # Check if .env exists
    if [ ! -f ".env" ]; then
        echo -e "${YELLOW}📝 Creating .env file from template...${NC}"
        cp .env.example .env
        echo -e "${RED}❗ Please edit .env file with your configuration before continuing${NC}"
        echo -e "   Required values: PROJECT_ID, DATABASE credentials, SECRET_KEY"
        read -p "Press Enter after configuring .env file..."
    fi
    
    # Load environment variables
    if [ -f ".env" ]; then
        export $(cat .env | grep -v '#' | xargs)
    fi
    
    # Check required environment variables
    if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
        read -p "Enter your Google Cloud Project ID: " GOOGLE_CLOUD_PROJECT
        export GOOGLE_CLOUD_PROJECT
    fi
    
    echo -e "${GREEN}✅ Configuration setup complete${NC}"
}

# Google Cloud setup
setup_gcloud() {
    echo -e "${YELLOW}☁️  Setting up Google Cloud...${NC}"
    
    # Set project
    gcloud config set project $GOOGLE_CLOUD_PROJECT
    
    # Enable required APIs
    echo "Enabling required APIs..."
    gcloud services enable cloudbuild.googleapis.com
    gcloud services enable run.googleapis.com
    gcloud services enable sqladmin.googleapis.com
    gcloud services enable storage.googleapis.com
    
    echo -e "${GREEN}✅ Google Cloud setup complete${NC}"
}

# Build and deploy
deploy_to_cloud_run() {
    echo -e "${YELLOW}🏗️  Building and deploying to Cloud Run...${NC}"
    
    # Build with Cloud Build
    echo "Building Docker image with Cloud Build..."
    gcloud builds submit --config cloudbuild.yaml .
    
    echo -e "${GREEN}✅ Deployment complete${NC}"
}

# Deploy using Docker (alternative method)
deploy_with_docker() {
    echo -e "${YELLOW}🐳 Building and deploying with Docker...${NC}"
    
    # Build Docker image
    IMAGE_NAME="gcr.io/$GOOGLE_CLOUD_PROJECT/kindle-content-server"
    docker build -t $IMAGE_NAME .
    
    # Push to Container Registry
    docker push $IMAGE_NAME
    
    # Deploy to Cloud Run
    gcloud run deploy kindle-content-server \
        --image $IMAGE_NAME \
        --region us-central1 \
        --platform managed \
        --allow-unauthenticated \
        --memory 1Gi \
        --cpu 1 \
        --max-instances 10 \
        --set-env-vars FLASK_ENV=production \
        --set-env-vars GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT
    
    echo -e "${GREEN}✅ Docker deployment complete${NC}"
}

# Setup database
setup_database() {
    echo -e "${YELLOW}🗄️  Database setup...${NC}"
    
    read -p "Do you want to create a Cloud SQL instance? (y/N): " create_db
    if [[ $create_db =~ ^[Yy]$ ]]; then
        echo "Creating Cloud SQL PostgreSQL instance..."
        
        read -p "Enter instance name [kindle-db]: " instance_name
        instance_name=${instance_name:-kindle-db}
        
        gcloud sql instances create $instance_name \
            --database-version=POSTGRES_15 \
            --tier=db-f1-micro \
            --region=us-central1
        
        echo "Creating database and user..."
        gcloud sql databases create kindle_content_server --instance=$instance_name
        gcloud sql users create kindle_user --instance=$instance_name --password=kindle_pass
        
        echo -e "${GREEN}✅ Database setup complete${NC}"
        echo -e "${YELLOW}📝 Update your .env file with the connection details${NC}"
    fi
}

# Health check
health_check() {
    echo -e "${YELLOW}🏥 Running health check...${NC}"
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe kindle-content-server --region=us-central1 --format="value(status.url)")
    
    if [ -n "$SERVICE_URL" ]; then
        echo "Testing service at: $SERVICE_URL"
        
        # Test health endpoint
        if curl -f "$SERVICE_URL/health" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Service is healthy and responding${NC}"
            echo -e "${GREEN}🌐 Service URL: $SERVICE_URL${NC}"
        else
            echo -e "${RED}❌ Service health check failed${NC}"
        fi
    else
        echo -e "${RED}❌ Could not get service URL${NC}"
    fi
}

# Main deployment menu
main_menu() {
    echo ""
    echo "Select deployment option:"
    echo "1) Full deployment (Cloud Build + Cloud Run)"
    echo "2) Docker deployment (local build + push)"
    echo "3) Setup database only"
    echo "4) Health check only"
    echo "5) Exit"
    
    read -p "Enter your choice [1-5]: " choice
    
    case $choice in
        1)
            setup_config
            setup_gcloud
            deploy_to_cloud_run
            health_check
            ;;
        2)
            setup_config
            setup_gcloud
            deploy_with_docker
            health_check
            ;;
        3)
            setup_config
            setup_gcloud
            setup_database
            ;;
        4)
            health_check
            ;;
        5)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo "Invalid option"
            main_menu
            ;;
    esac
}

# Cleanup function
cleanup() {
    echo -e "${YELLOW}🧹 Cleanup options:${NC}"
    read -p "Do you want to delete the Cloud Run service? (y/N): " delete_service
    if [[ $delete_service =~ ^[Yy]$ ]]; then
        gcloud run services delete kindle-content-server --region=us-central1 --quiet
    fi
}

# Trap cleanup on script exit
trap cleanup EXIT

# Main execution
check_dependencies
main_menu

echo ""
echo -e "${GREEN}🎉 Deployment script completed!${NC}"
echo ""
echo "Next steps:"
echo "1. Configure your .env file with production values"
echo "2. Set up your KUAL client to connect to the deployed service"
echo "3. Test the API endpoints with your Kindle device"
echo ""
echo "Useful commands:"
echo "• View logs: gcloud logging read 'resource.type=cloud_run_revision'"
echo "• Service info: gcloud run services describe kindle-content-server --region=us-central1"
echo "• Update service: gcloud run services update kindle-content-server --region=us-central1"
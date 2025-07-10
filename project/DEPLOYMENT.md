# Kindle Content Server - Production Deployment Guide

This guide covers deploying the Kindle Content Server to Google Cloud Platform for production use.

## Quick Start

1. **Clone and Setup**
   ```bash
   git clone <your-repo-url>
   cd kindle-content-server
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Deploy to Google Cloud**
   ```bash
   ./deploy.sh
   ```

3. **Configure KUAL Client**
   - Update your Kindle's config.json with the deployed service URL
   - Test the connection

## Prerequisites

### Required Tools
- [Google Cloud CLI](https://cloud.google.com/sdk/docs/install)
- [Docker](https://docs.docker.com/get-docker/)
- Python 3.12+

### Google Cloud Setup
1. Create a Google Cloud Project
2. Enable billing for the project
3. Install and authenticate Google Cloud CLI:
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

## Configuration

### Environment Variables
Copy `.env.example` to `.env` and configure:

```bash
# Required
GOOGLE_CLOUD_PROJECT=your-project-id
SECRET_KEY=your-secure-secret-key
SERVER_PASSCODE=your-api-passcode

# Database (Cloud SQL)
CLOUD_SQL_CONNECTION_NAME=project:region:instance
DB_USER=kindle_user
DB_PASS=secure-password
DB_NAME=kindle_content_server

# Optional
GCS_BUCKET_NAME=kindle-content-storage
SERVICE_VERSION=1.0.0
```

## Deployment Options

### Option 1: Automated Deployment (Recommended)
Run the deployment script:
```bash
./deploy.sh
```

This script will:
- Check dependencies
- Set up Google Cloud services
- Build and deploy using Cloud Build
- Run health checks

### Option 2: Manual Cloud Build Deployment
```bash
# Enable required APIs
gcloud services enable cloudbuild.googleapis.com run.googleapis.com

# Build and deploy
gcloud builds submit --config cloudbuild.yaml .
```

### Option 3: Docker Deployment
```bash
# Build and push image
docker build -t gcr.io/PROJECT_ID/kindle-content-server .
docker push gcr.io/PROJECT_ID/kindle-content-server

# Deploy to Cloud Run
gcloud run deploy kindle-content-server \
  --image gcr.io/PROJECT_ID/kindle-content-server \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated
```

### Option 4: App Engine Deployment
```bash
# Update app.yaml with your configuration
gcloud app deploy app.yaml
```

## Database Setup

### Cloud SQL PostgreSQL (Recommended)
```bash
# Create instance
gcloud sql instances create kindle-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

# Create database and user
gcloud sql databases create kindle_content_server --instance=kindle-db
gcloud sql users create kindle_user --instance=kindle-db --password=secure-password
```

### Connection String
Update your `.env` file:
```
CLOUD_SQL_CONNECTION_NAME=project:region:instance-name
```

## Storage Setup

### Google Cloud Storage
```bash
# Create bucket for content storage
gsutil mb gs://kindle-content-storage

# Set permissions (optional, for public access)
gsutil iam ch allUsers:objectViewer gs://kindle-content-storage
```

## Monitoring and Logging

### View Logs
```bash
# Real-time logs
gcloud logging tail "resource.type=cloud_run_revision"

# Recent logs
gcloud logging read "resource.type=cloud_run_revision" --limit=50
```

### Health Checks
The service includes health check endpoints:
- `/health` - Basic health check
- `/api/health` - API health with database check

### Monitoring Dashboard
Set up monitoring in Google Cloud Console:
1. Navigate to Monitoring
2. Create dashboard for Cloud Run metrics
3. Set up alerts for errors and high latency

## Security

### Service Account
Create a service account with minimal permissions:
```bash
gcloud iam service-accounts create kindle-server \
  --description="Kindle Content Server" \
  --display-name="Kindle Server"

# Grant necessary permissions
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:kindle-server@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"
```

### API Security
- Uses server passcode authentication
- Device-based authentication for KUAL client
- CORS configuration for frontend access
- Rate limiting enabled

## Scaling Configuration

### Cloud Run Auto-scaling
Configure in `cloudbuild.yaml`:
- `min_instances`: Minimum number of instances
- `max_instances`: Maximum number of instances
- `cpu`: CPU allocation per instance
- `memory`: Memory allocation per instance

### Database Scaling
- Start with `db-f1-micro` (shared CPU)
- Scale to `db-n1-standard-1` or higher for production load
- Enable automatic storage increase

## KUAL Client Configuration

After deployment, update your Kindle's KUAL configuration:

```json
{
  "server_url": "https://kindle-content-server-xxxxx-uc.a.run.app",
  "api_key": "your-server-passcode"
}
```

## Troubleshooting

### Common Issues

**Service won't start:**
- Check environment variables in Cloud Run
- Verify database connection string
- Check service account permissions

**Database connection errors:**
- Verify Cloud SQL instance is running
- Check connection name format
- Ensure database and user exist

**KUAL client can't connect:**
- Verify service URL is accessible
- Check server passcode configuration
- Test API endpoints manually

### Debug Commands
```bash
# Service status
gcloud run services describe kindle-content-server --region=us-central1

# View environment variables
gcloud run services describe kindle-content-server --region=us-central1 --format="value(spec.template.spec.template.spec.containers[0].env[].name,spec.template.spec.template.spec.containers[0].env[].value)"

# Test API endpoints
curl https://your-service-url/health
curl -X POST -H "X-Device-ID: TEST" -H "X-API-Key: your-passcode" https://your-service-url/api/v1/auth/device
```

## Cost Optimization

### Cloud Run
- Use minimum instances = 1 for low traffic
- Set CPU to allocated only during requests
- Use concurrency = 100 for better resource utilization

### Cloud SQL
- Use `db-f1-micro` for development/low traffic
- Enable automatic storage increase
- Set maintenance window during low traffic

### Storage
- Use Standard storage class for frequently accessed content
- Set lifecycle policies for old content

## Backup and Recovery

### Database Backups
```bash
# Enable automated backups
gcloud sql instances patch kindle-db --backup-start-time=02:00

# Manual backup
gcloud sql backups create --instance=kindle-db
```

### Content Backups
- GCS automatically replicates data
- Set up cross-region replication for disaster recovery
- Use lifecycle policies for old content archival

## CI/CD Pipeline

### GitHub Actions
Create `.github/workflows/deploy.yml`:
```yaml
name: Deploy to Cloud Run
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: google-github-actions/setup-gcloud@v1
        with:
          service_account_key: ${{ secrets.GCP_SA_KEY }}
          project_id: ${{ secrets.GCP_PROJECT_ID }}
      - run: gcloud builds submit --config cloudbuild.yaml .
```

## Production Checklist

- [ ] Environment variables configured
- [ ] Database created and accessible
- [ ] Storage bucket created
- [ ] Service deployed and healthy
- [ ] KUAL client configured and tested
- [ ] Monitoring and alerts set up
- [ ] Backups configured
- [ ] Security review completed
- [ ] Load testing performed
- [ ] Documentation updated

## Support

For issues:
1. Check logs in Google Cloud Console
2. Verify configuration in `.env`
3. Test API endpoints manually
4. Review security settings
5. Check resource quotas and limits
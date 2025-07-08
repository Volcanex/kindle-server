# Flask Backend Deployment to Google Cloud e2 Instance

## Overview
This document outlines the deployment strategy for the Kindle Content Server Flask backend to a Google Cloud Compute Engine e2-micro instance.

## Backend Analysis
The Flask backend includes:
- Flask application with multiple routes (sync, books, news)
- PostgreSQL database integration
- Google Cloud services integration (Storage, Logging)
- RSS feed aggregation
- EPUB generation capabilities
- Email functionality for Kindle delivery
- Redis caching support

## Deployment Architecture

### Infrastructure Components
1. **Compute Engine e2-micro Instance** (free tier eligible)
   - Ubuntu 22.04 LTS
   - 1 vCPU, 1GB RAM
   - 10GB persistent disk

2. **Cloud SQL PostgreSQL Instance** (for production database)
   - db-f1-micro (free tier eligible)
   - PostgreSQL 15

3. **Cloud Storage Bucket** (for file storage)

4. **Firewall Rules**
   - HTTP (port 80)
   - HTTPS (port 443)
   - Custom application port (8080)

### Deployment Steps

#### Phase 1: Infrastructure Setup
1. Create and configure e2-micro instance
2. Set up Cloud SQL PostgreSQL database
3. Create Cloud Storage bucket
4. Configure firewall rules
5. Set up static IP address

#### Phase 2: Server Configuration
1. Install Python 3.11 and pip
2. Install PostgreSQL client tools
3. Install Nginx as reverse proxy
4. Set up SSL/TLS with Let's Encrypt
5. Configure system users and permissions

#### Phase 3: Application Deployment
1. Clone/upload application code
2. Create Python virtual environment
3. Install application dependencies
4. Configure environment variables
5. Set up database migrations
6. Configure Gunicorn WSGI server

#### Phase 4: Service Management
1. Create systemd service files
2. Configure Nginx virtual host
3. Set up log rotation
4. Enable automatic startup
5. Configure monitoring

#### Phase 5: Security and Optimization
1. Configure firewall rules
2. Set up SSL certificates
3. Implement basic security hardening
4. Configure backup procedures
5. Set up basic monitoring

## Configuration Files Required

### 1. Instance Startup Script
- Install dependencies
- Configure users and permissions
- Set up basic security

### 2. Application Configuration
- Environment variables file
- Database connection settings
- Google Cloud service configuration

### 3. Systemd Service Files
- Flask application service
- Redis service (if needed locally)

### 4. Nginx Configuration
- Reverse proxy setup
- SSL termination
- Static file serving

### 5. Deployment Scripts
- Application deployment script
- Database migration script
- Backup and restore scripts

## Environment Variables
```bash
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=<generated-secret>
PORT=8080

# Database Configuration
DATABASE_URL=postgresql://user:pass@localhost/kindle_db
CLOUD_SQL_CONNECTION_NAME=project:region:instance

# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=geo-butler
GCS_BUCKET_NAME=kindle-content-storage
GOOGLE_APPLICATION_CREDENTIALS=/opt/app/service-account.json

# Email Configuration
EMAIL_USER=<email>
EMAIL_PASSWORD=<app-password>
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Kindle Configuration
KINDLE_SEND_TO_EMAIL=<kindle-email>

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
```

## Security Considerations
1. Service account with minimal permissions
2. Firewall rules restricting access
3. SSL/TLS encryption
4. Environment variable security
5. Regular security updates
6. Database connection security

## Monitoring and Logging
1. Cloud Logging integration
2. Application health checks
3. System resource monitoring
4. Database connection monitoring
5. Error alerting

## Backup Strategy
1. Cloud SQL automated backups
2. Application code backup
3. Configuration backup
4. Cloud Storage backup

## Rollback Procedures
1. Application rollback using Git
2. Database rollback using snapshots
3. Configuration rollback
4. Service restart procedures

## Cost Optimization
- Use free tier resources where possible
- Implement auto-scaling policies
- Monitor resource usage
- Optimize database queries
- Use CDN for static content

## Expected Outcomes
- Accessible Flask backend at public IP
- Secure HTTPS connection
- Reliable service startup
- Monitoring and logging in place
- Database connectivity established
- API endpoints functional
- Connection URL for frontend configuration

## Next Steps
1. Execute infrastructure deployment
2. Configure and deploy application
3. Test all endpoints
4. Provide connection details
5. Document operational procedures
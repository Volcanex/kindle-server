# Kindle Content Server Infrastructure

This directory contains the complete Google Cloud Platform (GCP) infrastructure setup for the Kindle Content Server project. The infrastructure is designed to be production-ready, cost-optimized, and follows cloud-native best practices.

## 🏗️ Architecture Overview

The Kindle Content Server uses a serverless, microservices architecture on Google Cloud Platform:

- **Compute**: Cloud Run for serverless Flask application hosting
- **Database**: Cloud SQL (PostgreSQL) for relational data storage
- **Storage**: Cloud Storage for books, news content, and static assets
- **Networking**: VPC with private networking and Cloud Load Balancing
- **Security**: IAM, Secret Manager, Cloud Armor, and Binary Authorization
- **Monitoring**: Cloud Operations Suite (formerly Stackdriver)
- **CI/CD**: Cloud Build with automated testing and deployment

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│  Global Load    │    │   Cloud      │    │   Cloud SQL     │
│  Balancer       │───▶│   Run        │───▶│   (PostgreSQL)  │
│  (HTTPS/SSL)    │    │   Service    │    │   (Private)     │
└─────────────────┘    └──────────────┘    └─────────────────┘
         │                       │                    │
         │                       │                    │
         ▼                       ▼                    ▼
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Cloud Armor   │    │   Secret     │    │   VPC Network   │
│   (WAF/DDoS)    │    │   Manager    │    │   (Private)     │
└─────────────────┘    └──────────────┘    └─────────────────┘
                               │
                               ▼
                    ┌──────────────────┐
                    │   Cloud Storage  │
                    │   (Books/News)   │
                    └──────────────────┘
```

## 📁 Directory Structure

```
infrastructure/
├── terraform/              # Infrastructure as Code
│   ├── main.tf             # Main Terraform configuration
│   ├── variables.tf        # Input variables
│   ├── outputs.tf          # Output values
│   ├── cloud_run.tf        # Cloud Run service configuration
│   ├── database.tf         # Cloud SQL database setup
│   ├── storage.tf          # Cloud Storage buckets
│   ├── network.tf          # VPC and networking
│   └── iam.tf              # IAM roles and service accounts
├── docker/                 # Container configuration
│   ├── Dockerfile          # Production Docker image
│   ├── Dockerfile.dev      # Development Docker image
│   ├── docker-compose.yml  # Local development stack
│   ├── requirements.txt    # Python dependencies
│   └── .dockerignore       # Docker ignore patterns
├── kubernetes/             # Kubernetes manifests (optional)
│   ├── namespace.yaml      # Kubernetes namespace
│   ├── deployment.yaml     # Application deployment
│   ├── service.yaml        # Service definitions
│   ├── ingress.yaml        # Ingress configuration
│   ├── configmap.yaml      # Configuration maps
│   ├── secrets.yaml        # Secret templates
│   └── rbac.yaml           # RBAC configuration
├── monitoring/             # Observability configuration
│   ├── logging.yaml        # Cloud Logging setup
│   ├── metrics.yaml        # Custom metrics and dashboards
│   └── alerting.yaml       # Alerting policies
├── security/               # Security policies and rules
│   ├── iam-policies.yaml   # IAM security policies
│   ├── firewall-rules.yaml # VPC firewall rules
│   └── security-policies.yaml # Advanced security policies
├── scripts/                # Management and deployment scripts
│   ├── setup.sh            # Initial infrastructure setup
│   ├── deploy.sh           # Application deployment
│   ├── cleanup.sh          # Resource cleanup
│   └── manage.sh           # Operations management
├── cloudbuild.yaml         # CI/CD pipeline configuration
├── rules.md                # Infrastructure rules and guidelines
├── readme.md               # This file
└── patterns.md             # Design patterns and best practices
```

## 🚀 Quick Start

### Prerequisites

Before you begin, ensure you have the following tools installed:

- [Google Cloud SDK (gcloud)](https://cloud.google.com/sdk/docs/install)
- [Terraform](https://developer.hashicorp.com/terraform/downloads) (>= 1.0)
- [Docker](https://docs.docker.com/get-docker/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/) (optional, for Kubernetes features)

### 1. Initial Setup

Run the setup script to configure your Google Cloud project and initialize the infrastructure:

```bash
# Make the script executable
chmod +x scripts/setup.sh

# Run the setup (will prompt for configuration)
./scripts/setup.sh
```

The setup script will:
- Verify prerequisites
- Configure Google Cloud authentication
- Enable required APIs
- Create service accounts
- Set up Terraform backend
- Create initial secrets
- Configure Docker registry

### 2. Deploy Infrastructure

Deploy the infrastructure using Terraform:

```bash
cd terraform/

# Review the planned changes
terraform plan

# Apply the infrastructure
terraform apply
```

### 3. Deploy Application

Build and deploy the application:

```bash
# Deploy to development environment
./scripts/deploy.sh

# Deploy to production environment
./scripts/deploy.sh -e prod
```

### 4. Verify Deployment

Check that everything is working correctly:

```bash
# Check deployment status
./scripts/manage.sh status -e dev

# Run health checks
./scripts/manage.sh health -e dev

# View logs
./scripts/manage.sh logs -e dev
```

## 🔧 Configuration

### Environment Variables

The infrastructure supports multiple environments (dev, staging, prod) with different configurations:

| Variable | Dev | Staging | Prod |
|----------|-----|---------|------|
| Min Instances | 0 | 0 | 1 |
| Max Instances | 3 | 5 | 10 |
| Memory | 512Mi | 512Mi | 1Gi |
| CPU | 1 | 1 | 2 |

### Terraform Variables

Key Terraform variables in `terraform.tfvars`:

```hcl
project_id   = "your-gcp-project-id"
region       = "us-central1"
zone         = "us-central1-a"
environment  = "dev"
app_name     = "kindle-server"

# Database configuration
db_tier      = "db-f1-micro"  # Free tier
db_disk_size = 10

# Scaling configuration
max_instances = 10
min_instances = 0
```

### Cost Optimization

The default configuration is optimized for Google Cloud's free tier:

- **Cloud Run**: 2M requests, 400K GB-seconds, 200K CPU-seconds/month
- **Cloud SQL**: db-f1-micro instance (0.6 GB RAM, shared CPU)
- **Cloud Storage**: 5 GB standard storage/month
- **Cloud Operations**: 50 GiB logs/month
- **Egress**: 1 GB/month to most regions

## 🔒 Security

### Security Features

- **Zero Trust Networking**: All services communicate over private networks
- **IAM Best Practices**: Least privilege access with custom roles
- **Encryption**: Data encrypted at rest and in transit using CMEK
- **Secret Management**: All secrets managed via Secret Manager
- **Binary Authorization**: Container images must be signed and scanned
- **Web Application Firewall**: Cloud Armor protects against attacks
- **DLP Integration**: Data Loss Prevention scanning for sensitive data

### Access Control

- **Service Accounts**: Each component has its own service account
- **Workload Identity**: Kubernetes pods use Google service accounts
- **Time-based Access**: Developer access restricted to business hours
- **Geographic Restrictions**: Access limited to approved regions
- **MFA Required**: Multi-factor authentication for human users

## 📊 Monitoring and Observability

### Metrics and Dashboards

- **Application Metrics**: Request rate, response time, error rate
- **Infrastructure Metrics**: CPU, memory, disk, network usage
- **Business Metrics**: User activity, content uploads, sync operations
- **Custom Dashboards**: Grafana dashboards for all metrics

### Alerting

Comprehensive alerting policies:
- **Performance**: High latency, error rates, resource usage
- **Security**: Authentication failures, suspicious activity
- **Business**: Upload failures, sync issues, quota limits
- **Infrastructure**: Service availability, database connectivity

### Logging

Centralized logging with:
- **Structured Logging**: JSON format with consistent fields
- **Log Aggregation**: All services log to Cloud Logging
- **Log-based Metrics**: Custom metrics derived from logs
- **Retention Policies**: Cost-optimized log retention

## 🔄 CI/CD Pipeline

### Build Process

The Cloud Build pipeline includes:

1. **Code Quality**: Linting, formatting, security scanning
2. **Testing**: Unit tests, integration tests, coverage reports
3. **Security**: Vulnerability scanning, binary authorization
4. **Build**: Multi-stage Docker build with optimization
5. **Deploy**: Automated deployment with health checks
6. **Monitoring**: Post-deployment verification and rollback

### Deployment Strategies

- **Development**: Direct deployment with minimal gates
- **Staging**: Automated deployment with integration tests
- **Production**: Manual approval with gradual rollout

### Pipeline Configuration

```yaml
# cloudbuild.yaml excerpt
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', '${_IMAGE_URL}', '.']
  
  - name: 'gcr.io/cloud-builders/gcloud'
    args: ['run', 'deploy', '${_SERVICE_NAME}', 
           '--image', '${_IMAGE_URL}',
           '--region', '${_REGION}']
```

## 🛠️ Operations

### Management Scripts

#### setup.sh
Initial project setup and configuration:
```bash
./scripts/setup.sh
```

#### deploy.sh
Application deployment with options:
```bash
# Deploy to dev environment
./scripts/deploy.sh

# Deploy to production with all checks
./scripts/deploy.sh -e prod

# Build only (skip deployment)
./scripts/deploy.sh -b

# Skip tests (not recommended)
./scripts/deploy.sh -s
```

#### manage.sh
Day-to-day operations management:
```bash
# Check deployment status
./scripts/manage.sh status -e prod

# View real-time logs
./scripts/manage.sh logs -e staging

# Scale service up/down
./scripts/manage.sh scale -e dev

# Create database backup
./scripts/manage.sh backup -e prod

# Rollback to previous version
./scripts/manage.sh rollback -e staging
```

#### cleanup.sh
Safe resource cleanup:
```bash
# Cleanup dev environment
./scripts/cleanup.sh -e dev

# Force cleanup without prompts
./scripts/cleanup.sh -e staging -f

# Cleanup but preserve data
./scripts/cleanup.sh -e dev -p

# Dry run to see what would be deleted
./scripts/cleanup.sh -e dev -d
```

### Backup and Recovery

#### Database Backups
- **Automated Backups**: Daily automated backups with 7-day retention
- **Point-in-time Recovery**: 7-day point-in-time recovery window
- **Manual Backups**: On-demand backups before major deployments
- **Cross-region Backups**: Backups replicated to secondary region

#### Storage Backups
- **Versioning**: Object versioning enabled on all buckets
- **Lifecycle Policies**: Automatic transition to cheaper storage classes
- **Backup Bucket**: Separate bucket for backup storage
- **Cross-region Replication**: Critical data replicated across regions

### Disaster Recovery

#### Recovery Procedures
1. **Service Outage**: Automatic failover to backup region
2. **Data Corruption**: Restore from point-in-time backup
3. **Security Incident**: Isolate affected systems, restore from clean backup
4. **Regional Failure**: Activate disaster recovery region

#### RTO/RPO Targets
- **Recovery Time Objective (RTO)**: 1 hour
- **Recovery Point Objective (RPO)**: 15 minutes
- **Data Backup Frequency**: Every 6 hours
- **Failover Testing**: Monthly

## 🎯 Performance Optimization

### Scaling Strategies

#### Horizontal Scaling
- **Cloud Run**: Automatic scaling based on request volume
- **Database**: Read replicas for read-heavy workloads
- **Storage**: Parallel uploads and downloads
- **CDN**: Global content distribution for static assets

#### Vertical Scaling
- **Memory Optimization**: Right-sized memory allocation
- **CPU Optimization**: CPU allocation based on workload
- **Database Tuning**: Optimized database configuration
- **Network**: High-bandwidth network configuration

### Caching Strategies

- **Application Cache**: Redis for session and data caching
- **HTTP Cache**: Cloud CDN for static content
- **Database Cache**: Connection pooling and query caching
- **API Cache**: Response caching for expensive operations

### Performance Monitoring

- **SLI/SLO Tracking**: Service Level Indicators and Objectives
- **Error Budgets**: Systematic approach to reliability
- **Performance Baselines**: Established performance benchmarks
- **Load Testing**: Regular load testing and capacity planning

## 💰 Cost Management

### Cost Optimization Strategies

#### Resource Optimization
- **Right-sizing**: Resources sized based on actual usage
- **Scheduling**: Non-production environments shutdown after hours
- **Storage Classes**: Automatic lifecycle management
- **Reserved Capacity**: Committed use discounts for predictable workloads

#### Monitoring and Alerts
- **Budget Alerts**: Proactive budget monitoring
- **Cost Attribution**: Cost tracking by environment and feature
- **Usage Analytics**: Regular usage pattern analysis
- **Waste Identification**: Automated identification of unused resources

### Free Tier Optimization

The infrastructure is designed to maximize Google Cloud free tier usage:

- **Cloud Run**: Stays within free tier limits for small workloads
- **Cloud SQL**: Uses free tier eligible instance types
- **Storage**: Optimized storage classes and lifecycle policies
- **Networking**: Minimized egress costs
- **Operations**: Log retention optimized for free tier

## 🔍 Troubleshooting

### Common Issues

#### Deployment Failures
```bash
# Check build logs
gcloud builds list --limit=5

# View build details
gcloud builds describe BUILD_ID

# Check service logs
./scripts/manage.sh logs -e dev
```

#### Database Connection Issues
```bash
# Test database connectivity
gcloud sql connect INSTANCE_NAME --user=USERNAME

# Check VPC connector status
gcloud compute networks vpc-access connectors list

# Verify firewall rules
gcloud compute firewall-rules list --filter="name~kindle-server"
```

#### Performance Issues
```bash
# Check service metrics
./scripts/manage.sh monitoring -e prod

# View performance dashboards
gcloud monitoring dashboards list

# Analyze slow queries
gcloud sql operations list --instance=INSTANCE_NAME
```

### Getting Help

#### Documentation
- [Google Cloud Documentation](https://cloud.google.com/docs)
- [Terraform Google Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)

#### Support Channels
- **Internal**: Check `patterns.md` for design patterns
- **Community**: Google Cloud Community Forum
- **Professional**: Google Cloud Support (if applicable)

#### Logging and Debugging
```bash
# Enable debug logging
export TF_LOG=DEBUG

# Verbose deployment
./scripts/deploy.sh -e dev --verbose

# Check infrastructure state
cd terraform && terraform show
```

## 📈 Roadmap and Future Enhancements

### Planned Improvements

#### Short Term (Next 3 months)
- [ ] Multi-region deployment capability
- [ ] Enhanced monitoring dashboards
- [ ] Automated security scanning
- [ ] Performance optimization analysis

#### Medium Term (3-6 months)
- [ ] Kubernetes migration option
- [ ] Advanced caching layer
- [ ] Enhanced disaster recovery
- [ ] Compliance automation (SOC2, GDPR)

#### Long Term (6+ months)
- [ ] Machine learning integration
- [ ] Global content distribution
- [ ] Advanced analytics platform
- [ ] Mobile SDK integration

### Contributing

To contribute to the infrastructure:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly in dev environment
5. Submit a pull request with detailed description

### License

This infrastructure code is licensed under the MIT License. See the LICENSE file for details.

---

For more detailed information, see:
- [Infrastructure Rules](rules.md) - Detailed rules and guidelines
- [Design Patterns](patterns.md) - Architectural patterns and best practices

**Need help?** Contact the DevOps team or create an issue in the project repository.
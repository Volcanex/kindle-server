# Infrastructure Rules for Kindle Content Server

## Core Infrastructure Principles

### 1. Cloud-First Architecture
- **Serverless by Default**: Use Cloud Run for compute, Cloud SQL for databases, Cloud Storage for files
- **Managed Services**: Prefer Google Cloud managed services over self-managed solutions
- **Auto-scaling**: Design for automatic scaling based on demand
- **Stateless Design**: Application must be stateless to support horizontal scaling

### 2. Security-First Approach
- **Zero Trust**: Never trust, always verify - implement strict IAM and network policies
- **Least Privilege**: Grant minimum required permissions to each component
- **Defense in Depth**: Multiple layers of security controls (network, application, data)
- **Encryption Everywhere**: Data encrypted at rest and in transit using customer-managed keys

### 3. Cost Optimization
- **Free Tier Utilization**: Default configurations optimized for Google Cloud free tier
- **Resource Right-sizing**: Start small, scale based on actual usage
- **Lifecycle Management**: Automatic cleanup of old resources and data
- **Monitoring**: Track costs and set up alerts for budget overruns

### 4. High Availability and Reliability
- **Multi-Zone Deployment**: Distribute resources across availability zones
- **Health Checks**: Comprehensive health monitoring and automatic recovery
- **Graceful Degradation**: Service continues with reduced functionality during failures
- **Disaster Recovery**: Regular backups and tested recovery procedures

## Infrastructure Components Rules

### Cloud Run Services
1. **Resource Limits**: 
   - Dev: 512Mi memory, 1 CPU, 0-3 instances
   - Staging: 512Mi memory, 1 CPU, 0-5 instances  
   - Prod: 1Gi memory, 2 CPU, 1-10 instances

2. **Environment Variables**: 
   - Sensitive data must use Secret Manager
   - Environment-specific configs in ConfigMaps
   - No hardcoded values in container images

3. **Health Checks**:
   - `/health` endpoint for liveness probes
   - `/ready` endpoint for readiness probes
   - 30s startup timeout, 10s health check interval

### Database (Cloud SQL)
1. **Instance Configuration**:
   - PostgreSQL 15 or later
   - Private IP only (no public access)
   - SSL/TLS encryption required
   - Automated backups with 7-day retention

2. **Access Control**:
   - Application connects via private VPC
   - Connection pooling enabled (max 20 connections)
   - Read replicas for read-heavy workloads in production

3. **Data Protection**:
   - Point-in-time recovery enabled
   - Customer-managed encryption keys
   - Database flags for audit logging

### Storage (Cloud Storage)
1. **Bucket Organization**:
   - `{app-name}-books-{suffix}`: Book files storage
   - `{app-name}-news-{suffix}`: News content storage
   - `{app-name}-static-{suffix}`: Static assets
   - `{app-name}-backup-{suffix}`: Backup storage

2. **Access Patterns**:
   - Uniform bucket-level access
   - IAM-based permissions (no ACLs)
   - CORS enabled for web uploads
   - Lifecycle policies for cost optimization

3. **Data Lifecycle**:
   - Books: Standard → Nearline (1 year) → Coldline (3 years)
   - News: Delete after 30 days
   - Backups: Coldline storage, 7-year retention

### Networking
1. **VPC Configuration**:
   - Private subnet: 10.0.0.0/24
   - Secondary ranges for GKE: 10.1.0.0/16 (pods), 10.2.0.0/16 (services)
   - VPC connector for serverless access: 10.3.0.0/28

2. **Firewall Rules**:
   - Deny all by default
   - Allow internal VPC communication
   - Allow ingress from Google Load Balancers only
   - Egress restricted to necessary services

3. **Load Balancing**:
   - Global HTTPS Load Balancer for production
   - SSL certificates managed by Google
   - Cloud Armor for DDoS protection and WAF

### Security
1. **IAM Policies**:
   - Custom roles with minimal permissions
   - Service account for each component
   - No user accounts for service access
   - Regular access reviews and cleanup

2. **Secret Management**:
   - Secret Manager for all sensitive data
   - Automatic secret rotation (90 days)
   - No secrets in environment variables or configs
   - Audit logging for secret access

3. **Binary Authorization**:
   - All containers must be signed and scanned
   - Production requires security and quality attestations
   - Vulnerability scanner integration
   - Block unsigned or vulnerable images

## Development Workflow Rules

### 1. Environment Separation
- **Development**: Individual developer instances, relaxed security
- **Staging**: Production-like, integration testing, security hardened
- **Production**: Minimal access, all security controls enabled

### 2. Infrastructure as Code
- **Terraform Only**: All infrastructure defined in Terraform
- **Version Control**: Infrastructure changes go through git workflow
- **Review Process**: All changes require peer review
- **Testing**: Terraform plan before apply, validate configurations

### 3. CI/CD Pipeline
- **Automated Testing**: Unit tests, integration tests, security scans
- **Progressive Deployment**: Dev → Staging → Production
- **Rollback Capability**: Ability to quickly rollback deployments
- **Approval Gates**: Manual approval required for production

### 4. Monitoring and Alerting
- **Comprehensive Metrics**: Application, infrastructure, and business metrics
- **Proactive Alerting**: Alert on trends, not just failures
- **Centralized Logging**: All logs aggregated in Cloud Logging
- **Performance Monitoring**: Track SLIs/SLOs, error budgets

## Compliance and Governance

### 1. Data Protection
- **Encryption**: AES-256 encryption for data at rest, TLS 1.2+ for transit
- **Data Classification**: Sensitive data identified and protected
- **Access Logging**: All data access logged and monitored
- **Data Residency**: Data stored in compliant geographic regions

### 2. Audit Requirements
- **Change Tracking**: All infrastructure changes tracked and auditable
- **Access Logs**: User and service account access logged
- **Compliance Reporting**: Regular compliance status reports
- **Incident Response**: Documented incident response procedures

### 3. Business Continuity
- **Backup Strategy**: Regular automated backups with tested restore
- **RTO/RPO Targets**: Recovery Time Objective: 1 hour, Recovery Point Objective: 15 minutes
- **Disaster Recovery**: Cross-region backup and recovery capabilities
- **Business Impact**: Clear understanding of service criticality

## Operational Excellence

### 1. Change Management
- **Scheduled Maintenance**: Regular maintenance windows for updates
- **Change Documentation**: All changes documented with rationale
- **Impact Assessment**: Changes assessed for business impact
- **Rollback Plan**: Every change has a tested rollback procedure

### 2. Capacity Planning
- **Resource Monitoring**: Track resource utilization trends
- **Scaling Policies**: Automated scaling based on metrics
- **Performance Baselines**: Establish and monitor performance baselines
- **Growth Planning**: Plan capacity based on business growth projections

### 3. Cost Management
- **Budget Alerts**: Alerts when spending exceeds thresholds
- **Resource Optimization**: Regular review and optimization of resources
- **Cost Attribution**: Track costs by environment and feature
- **Waste Elimination**: Identify and eliminate unused resources

## Technology Standards

### 1. Container Standards
- **Base Images**: Use official, minimal base images (Python slim)
- **Multi-stage Builds**: Optimize image size with multi-stage builds
- **Security Scanning**: All images scanned for vulnerabilities
- **Image Tagging**: Semantic versioning with git commit SHA

### 2. Configuration Management
- **Environment Parity**: Same configuration pattern across environments
- **External Configuration**: All configs externalized from application
- **Secret Separation**: Secrets separated from regular configuration
- **Validation**: Configuration validated before deployment

### 3. API Standards
- **RESTful Design**: Follow REST principles for API design
- **Versioning**: API versioning strategy (URL path versioning)
- **Documentation**: OpenAPI/Swagger documentation required
- **Rate Limiting**: API rate limiting implemented

## Emergency Procedures

### 1. Incident Response
- **On-call Rotation**: 24/7 on-call coverage for production
- **Escalation Matrix**: Clear escalation path for incidents
- **Communication Plan**: Stakeholder communication during incidents
- **Post-mortem Process**: Blameless post-mortems for all incidents

### 2. Emergency Access
- **Break-glass Procedures**: Emergency access procedures documented
- **Audit Trail**: All emergency access logged and reviewed
- **Time Limits**: Emergency access automatically expires
- **Approval Process**: Emergency access requires approval

### 3. Service Recovery
- **Runbooks**: Detailed runbooks for common scenarios
- **Recovery Procedures**: Step-by-step recovery procedures
- **Testing**: Regular testing of recovery procedures
- **Automation**: Automated recovery where possible

## Validation and Testing

### 1. Infrastructure Testing
- **Terraform Validation**: Syntax and configuration validation
- **Policy Testing**: Security policy compliance testing
- **Integration Testing**: Test infrastructure integration points
- **Performance Testing**: Load testing of deployed infrastructure

### 2. Security Testing
- **Vulnerability Scanning**: Regular vulnerability assessments
- **Penetration Testing**: Annual penetration testing
- **Compliance Audits**: Regular compliance audits
- **Security Reviews**: Security review of all changes

### 3. Disaster Recovery Testing
- **Backup Testing**: Regular backup and restore testing
- **Failover Testing**: Test failover procedures
- **RTO/RPO Validation**: Validate recovery time and point objectives
- **Communication Testing**: Test incident communication procedures

## Continuous Improvement

### 1. Performance Optimization
- **Regular Reviews**: Monthly infrastructure performance reviews
- **Optimization Opportunities**: Identify and implement optimizations
- **Technology Updates**: Stay current with platform updates
- **Best Practices**: Adopt industry best practices

### 2. Learning and Development
- **Training**: Regular training on cloud technologies and security
- **Documentation**: Maintain up-to-date documentation
- **Knowledge Sharing**: Share lessons learned across team
- **Innovation**: Encourage experimentation with new technologies

### 3. Feedback Integration
- **User Feedback**: Incorporate user feedback into infrastructure decisions
- **Metrics Analysis**: Regular analysis of operational metrics
- **Process Improvement**: Continuous improvement of processes
- **Tool Evaluation**: Regular evaluation of tooling and automation
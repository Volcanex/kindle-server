# Terraform Outputs for Kindle Content Server

# Cloud Run service URL
output "cloud_run_url" {
  description = "URL of the Cloud Run service"
  value       = google_cloud_run_service.main.status[0].url
}

# Load balancer IP (if created)
output "load_balancer_ip" {
  description = "IP address of the load balancer"
  value       = var.environment == "prod" ? google_compute_global_address.lb_ip.address : null
}

# Database connection details
output "database_instance_name" {
  description = "Cloud SQL instance name"
  value       = google_sql_database_instance.main.name
}

output "database_connection_name" {
  description = "Cloud SQL instance connection name"
  value       = google_sql_database_instance.main.connection_name
}

output "database_private_ip" {
  description = "Private IP address of the database"
  value       = google_sql_database_instance.main.private_ip_address
  sensitive   = true
}

# Storage bucket names
output "books_bucket_name" {
  description = "Name of the books storage bucket"
  value       = google_storage_bucket.books_bucket.name
}

output "news_bucket_name" {
  description = "Name of the news storage bucket"
  value       = google_storage_bucket.news_bucket.name
}

output "static_bucket_name" {
  description = "Name of the static assets bucket"
  value       = google_storage_bucket.static_bucket.name
}

output "backup_bucket_name" {
  description = "Name of the backup storage bucket"
  value       = google_storage_bucket.backup_bucket.name
}

# Service account emails
output "cloud_run_service_account" {
  description = "Email of the Cloud Run service account"
  value       = google_service_account.cloud_run_sa.email
}

output "cloud_build_service_account" {
  description = "Email of the Cloud Build service account"
  value       = google_service_account.cloud_build_sa.email
}

output "backup_service_account" {
  description = "Email of the backup service account"
  value       = google_service_account.backup_sa.email
}

output "monitoring_service_account" {
  description = "Email of the monitoring service account"
  value       = google_service_account.monitoring_sa.email
}

# Artifact Registry repository
output "artifact_registry_repo" {
  description = "Artifact Registry repository URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.main.repository_id}"
}

# VPC and networking
output "vpc_network_name" {
  description = "Name of the VPC network"
  value       = google_compute_network.vpc.name
}

output "subnet_name" {
  description = "Name of the subnet"
  value       = google_compute_subnetwork.subnet.name
}

output "vpc_connector_name" {
  description = "Name of the VPC connector"
  value       = google_vpc_access_connector.connector.name
}

# Secret Manager secrets
output "database_password_secret" {
  description = "Secret Manager secret name for database password"
  value       = google_secret_manager_secret.db_password.secret_id
}

output "database_connection_secret" {
  description = "Secret Manager secret name for database connection string"
  value       = google_secret_manager_secret.db_connection.secret_id
}

output "ssl_cert_secret" {
  description = "Secret Manager secret name for SSL certificate"
  value       = google_secret_manager_secret.db_ssl_cert.secret_id
}

output "ssl_key_secret" {
  description = "Secret Manager secret name for SSL private key"
  value       = google_secret_manager_secret.db_ssl_key.secret_id
}

# Development-only outputs
output "service_account_key_secret" {
  description = "Secret Manager secret name for service account key (dev only)"
  value       = var.environment == "dev" ? google_secret_manager_secret.service_account_key[0].secret_id : null
}

# DNS and domain information
output "dns_zone_name" {
  description = "Name of the DNS zone (prod only)"
  value       = var.environment == "prod" ? google_dns_managed_zone.main[0].name : null
}

output "dns_zone_name_servers" {
  description = "Name servers for the DNS zone (prod only)"
  value       = var.environment == "prod" ? google_dns_managed_zone.main[0].name_servers : null
}

output "domain_mapping_status" {
  description = "Status of the domain mapping (prod only)"
  value       = var.environment == "prod" ? google_cloud_run_domain_mapping.main[0].status : null
}

# Project and environment information
output "project_id" {
  description = "GCP project ID"
  value       = var.project_id
}

output "region" {
  description = "GCP region"
  value       = var.region
}

output "environment" {
  description = "Environment name"
  value       = var.environment
}

# Cost optimization information
output "estimated_monthly_cost" {
  description = "Estimated monthly cost breakdown"
  value = {
    cloud_run = "Free tier: 2 million requests, 400,000 GB-seconds, 200,000 CPU-seconds per month"
    cloud_sql = "Free tier: db-f1-micro instance with 1 vCPU, 0.6 GB RAM"
    storage   = "Free tier: 5 GB standard storage per month"
    networking = "Free tier: 1 GB egress per month to most regions"
    operations = "Free tier: First 50 GiB of logs per month"
  }
}

# Health check URLs
output "health_check_url" {
  description = "Health check endpoint URL"
  value       = "${google_cloud_run_service.main.status[0].url}/health"
}

output "ready_check_url" {
  description = "Readiness check endpoint URL"
  value       = "${google_cloud_run_service.main.status[0].url}/ready"
}

# Deployment information
output "deployment_info" {
  description = "Information for CI/CD deployment"
  value = {
    image_url             = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.main.repository_id}/${var.app_name}"
    service_name          = google_cloud_run_service.main.name
    service_location      = google_cloud_run_service.main.location
    service_account_email = google_service_account.cloud_run_sa.email
  }
}
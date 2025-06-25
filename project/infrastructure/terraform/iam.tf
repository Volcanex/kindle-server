# IAM Service Accounts and Roles for Kindle Content Server

# Cloud Run service account
resource "google_service_account" "cloud_run_sa" {
  account_id   = "${var.app_name}-cloud-run-${local.name_suffix}"
  display_name = "Cloud Run Service Account for ${var.app_name}"
  description  = "Service account used by Cloud Run service for ${var.app_name}"
}

# Cloud Build service account
resource "google_service_account" "cloud_build_sa" {
  account_id   = "${var.app_name}-cloud-build-${local.name_suffix}"
  display_name = "Cloud Build Service Account for ${var.app_name}"
  description  = "Service account used by Cloud Build for ${var.app_name}"
}

# Backup service account
resource "google_service_account" "backup_sa" {
  account_id   = "${var.app_name}-backup-${local.name_suffix}"
  display_name = "Backup Service Account for ${var.app_name}"
  description  = "Service account used for backup operations"
}

# Monitoring service account
resource "google_service_account" "monitoring_sa" {
  account_id   = "${var.app_name}-monitoring-${local.name_suffix}"
  display_name = "Monitoring Service Account for ${var.app_name}"
  description  = "Service account used for monitoring and alerting"
}

# IAM roles for Cloud Run service account
resource "google_project_iam_member" "cloud_run_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_project_iam_member" "cloud_run_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_project_iam_member" "cloud_run_logging_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_project_iam_member" "cloud_run_monitoring_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_project_iam_member" "cloud_run_trace_agent" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# IAM roles for Cloud Build service account
resource "google_project_iam_member" "cloud_build_builder" {
  project = var.project_id
  role    = "roles/cloudbuild.builds.builder"
  member  = "serviceAccount:${google_service_account.cloud_build_sa.email}"
}

resource "google_project_iam_member" "cloud_build_storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.cloud_build_sa.email}"
}

resource "google_project_iam_member" "cloud_build_artifact_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.cloud_build_sa.email}"
}

resource "google_project_iam_member" "cloud_build_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.cloud_build_sa.email}"
}

resource "google_project_iam_member" "cloud_build_service_account_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.cloud_build_sa.email}"
}

# IAM roles for backup service account
resource "google_project_iam_member" "backup_sql_admin" {
  project = var.project_id
  role    = "roles/cloudsql.admin"
  member  = "serviceAccount:${google_service_account.backup_sa.email}"
}

# IAM roles for monitoring service account
resource "google_project_iam_member" "monitoring_viewer" {
  project = var.project_id
  role    = "roles/monitoring.viewer"
  member  = "serviceAccount:${google_service_account.monitoring_sa.email}"
}

resource "google_project_iam_member" "monitoring_notification_channel_editor" {
  project = var.project_id
  role    = "roles/monitoring.notificationChannelEditor"
  member  = "serviceAccount:${google_service_account.monitoring_sa.email}"
}

# Custom IAM role for minimal Cloud Run permissions
resource "google_project_iam_custom_role" "cloud_run_minimal" {
  role_id = "${var.app_name}_cloud_run_minimal_${local.name_suffix}"
  title   = "Cloud Run Minimal Role for ${var.app_name}"
  description = "Minimal permissions for Cloud Run service"
  
  permissions = [
    "run.services.get",
    "run.services.list",
    "run.revisions.get",
    "run.revisions.list",
    "run.routes.get",
    "run.routes.list",
    "storage.objects.get",
    "storage.objects.list",
    "storage.objects.create",
    "storage.objects.update",
    "storage.objects.delete",
    "secretmanager.versions.access",
    "cloudsql.instances.connect"
  ]
}

# Bind custom role to Cloud Run service account
resource "google_project_iam_member" "cloud_run_minimal_role" {
  project = var.project_id
  role    = "projects/${var.project_id}/roles/${google_project_iam_custom_role.cloud_run_minimal.role_id}"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Workload Identity binding for future Kubernetes integration
resource "google_service_account_iam_binding" "cloud_run_workload_identity" {
  service_account_id = google_service_account.cloud_run_sa.name
  role              = "roles/iam.workloadIdentityUser"
  
  members = [
    "serviceAccount:${var.project_id}.svc.id.goog[default/${var.app_name}]",
  ]
}

# Service account keys for local development (not recommended for production)
resource "google_service_account_key" "cloud_run_key" {
  service_account_id = google_service_account.cloud_run_sa.name
  public_key_type    = "TYPE_X509_PEM_FILE"
  
  # Only create in development environment
  count = var.environment == "dev" ? 1 : 0
}

# Store service account key in Secret Manager
resource "google_secret_manager_secret" "service_account_key" {
  secret_id = "${var.app_name}-sa-key-${local.name_suffix}"
  
  replication {
    auto {}
  }
  
  count = var.environment == "dev" ? 1 : 0
  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "service_account_key" {
  secret      = google_secret_manager_secret.service_account_key[0].id
  secret_data = base64decode(google_service_account_key.cloud_run_key[0].private_key)
  
  count = var.environment == "dev" ? 1 : 0
}

# Conditional access for external users (e.g., mobile app authentication)
resource "google_project_iam_member" "external_user_access" {
  for_each = var.environment == "prod" ? toset([
    "roles/run.invoker"
  ]) : toset([
    "roles/run.invoker",
    "roles/cloudsql.client"  # Additional permissions for development
  ])
  
  project = var.project_id
  role    = each.value
  member  = "allUsers"  # In production, this should be more restrictive
}

# Organization-level policies (if applicable)
resource "google_project_organization_policy" "restrict_vm_external_ip" {
  project    = var.project_id
  constraint = "constraints/compute.vmExternalIpAccess"
  
  list_policy {
    deny {
      all = true
    }
  }
  
  # Only apply in production
  count = var.environment == "prod" ? 1 : 0
}

resource "google_project_organization_policy" "require_ssl_for_storage" {
  project    = var.project_id
  constraint = "constraints/storage.uniformBucketLevelAccess"
  
  boolean_policy {
    enforced = true
  }
}
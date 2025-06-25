# Cloud Run service for Kindle Content Server

# Artifact Registry repository for container images
resource "google_artifact_registry_repository" "main" {
  repository_id = "${var.app_name}-repo-${local.name_suffix}"
  location      = var.region
  format        = "DOCKER"
  description   = "Docker repository for ${var.app_name}"
  
  # Cost optimization - cleanup policy
  cleanup_policies {
    id     = "keep-minimum-versions"
    action = "KEEP"
    
    most_recent_versions {
      keep_count = 10
    }
  }
  
  cleanup_policies {
    id     = "delete-old-versions"
    action = "DELETE"
    
    condition {
      older_than = "2592000s"  # 30 days
    }
  }
  
  depends_on = [google_project_service.required_apis]
}

# Cloud Run service
resource "google_cloud_run_service" "main" {
  name     = "${var.app_name}-service-${local.name_suffix}"
  location = var.region
  
  template {
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale"      = var.min_instances
        "autoscaling.knative.dev/maxScale"      = var.max_instances
        "run.googleapis.com/cloudsql-instances" = google_sql_database_instance.main.connection_name
        "run.googleapis.com/vpc-access-connector" = google_vpc_access_connector.connector.name
        "run.googleapis.com/vpc-access-egress"    = "private-ranges-only"
        "run.googleapis.com/execution-environment" = "gen2"
        "run.googleapis.com/cpu-throttling"       = "false"
      }
      
      labels = {
        environment = var.environment
        app         = var.app_name
        version     = "latest"
      }
    }
    
    spec {
      service_account_name = google_service_account.cloud_run_sa.email
      
      # Container configuration
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.main.repository_id}/${var.app_name}:latest"
        
        # Resource limits
        resources {
          limits = {
            cpu    = var.cloud_run_cpu
            memory = var.cloud_run_memory
          }
        }
        
        # Environment variables
        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }
        
        env {
          name  = "PROJECT_ID"
          value = var.project_id
        }
        
        env {
          name  = "REGION"
          value = var.region
        }
        
        # Database connection string from Secret Manager
        env {
          name = "DATABASE_URL"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.db_connection.secret_id
              key  = "latest"
            }
          }
        }
        
        # Storage bucket names
        env {
          name  = "BOOKS_BUCKET"
          value = google_storage_bucket.books_bucket.name
        }
        
        env {
          name  = "NEWS_BUCKET"
          value = google_storage_bucket.news_bucket.name
        }
        
        env {
          name  = "STATIC_BUCKET"
          value = google_storage_bucket.static_bucket.name
        }
        
        # Flask configuration
        env {
          name  = "FLASK_ENV"
          value = var.environment == "prod" ? "production" : "development"
        }
        
        env {
          name  = "FLASK_DEBUG"
          value = var.environment == "prod" ? "False" : "True"
        }
        
        # Health check endpoint
        env {
          name  = "PORT"
          value = "8080"
        }
        
        # Logging configuration
        env {
          name  = "LOG_LEVEL"
          value = var.environment == "prod" ? "INFO" : "DEBUG"
        }
        
        # CORS origins
        env {
          name  = "CORS_ORIGINS"
          value = join(",", var.allowed_domains)
        }
        
        # Ports
        ports {
          name           = "http1"
          container_port = 8080
        }
        
        # Startup probe
        startup_probe {
          http_get {
            path = "/health"
            port = 8080
          }
          initial_delay_seconds = 10
          timeout_seconds       = 5
          period_seconds        = 3
          failure_threshold     = 3
        }
        
        # Liveness probe
        liveness_probe {
          http_get {
            path = "/health"
            port = 8080
          }
          initial_delay_seconds = 30
          timeout_seconds       = 5
          period_seconds        = 10
          failure_threshold     = 3
        }
        
        # Readiness probe
        readiness_probe {
          http_get {
            path = "/ready"
            port = 8080
          }
          initial_delay_seconds = 5
          timeout_seconds       = 5
          period_seconds        = 5
          failure_threshold     = 3
        }
      }
      
      # Request timeout
      timeout_seconds = 300  # 5 minutes
      
      # Container concurrency
      container_concurrency = 100
    }
  }
  
  # Traffic allocation
  traffic {
    percent         = 100
    latest_revision = true
  }
  
  autogenerate_revision_name = true
  
  depends_on = [
    google_project_service.required_apis,
    google_service_account.cloud_run_sa,
    google_sql_database_instance.main,
    google_vpc_access_connector.connector
  ]
}

# IAM policy for Cloud Run service
resource "google_cloud_run_service_iam_policy" "noauth" {
  location = google_cloud_run_service.main.location
  project  = google_cloud_run_service.main.project
  service  = google_cloud_run_service.main.name
  
  policy_data = data.google_iam_policy.noauth.policy_data
}

data "google_iam_policy" "noauth" {
  binding {
    role = "roles/run.invoker"
    members = [
      "allUsers",  # In production, restrict this to authenticated users
    ]
  }
}

# Domain mapping (for custom domain)
resource "google_cloud_run_domain_mapping" "main" {
  location = var.region
  name     = "${var.app_name}.example.com"
  
  metadata {
    namespace = var.project_id
    labels = {
      environment = var.environment
      app         = var.app_name
    }
  }
  
  spec {
    route_name = google_cloud_run_service.main.name
  }
  
  # Only create domain mapping in production
  count = var.environment == "prod" ? 1 : 0
  
  depends_on = [google_cloud_run_service.main]
}

# SSL certificate for custom domain
resource "google_compute_managed_ssl_certificate" "main" {
  name = "${var.app_name}-ssl-cert-${local.name_suffix}"
  
  managed {
    domains = ["${var.app_name}.example.com"]
  }
  
  # Only create SSL certificate in production
  count = var.environment == "prod" ? 1 : 0
  
  depends_on = [google_project_service.required_apis]
}

# Load balancer for custom domain (if needed)
resource "google_compute_url_map" "main" {
  name            = "${var.app_name}-url-map-${local.name_suffix}"
  default_url_redirect {
    https_redirect = true
    strip_query    = false
  }
  
  host_rule {
    hosts        = ["${var.app_name}.example.com"]
    path_matcher = "allpaths"
  }
  
  path_matcher {
    name            = "allpaths"
    default_service = google_compute_backend_service.main[0].id
  }
  
  # Only create load balancer in production
  count = var.environment == "prod" ? 1 : 0
  
  depends_on = [google_project_service.required_apis]
}

# Backend service for load balancer
resource "google_compute_backend_service" "main" {
  name                  = "${var.app_name}-backend-${local.name_suffix}"
  load_balancing_scheme = "EXTERNAL"
  protocol              = "HTTP"
  
  backend {
    group = google_compute_region_network_endpoint_group.cloud_run[0].id
  }
  
  # Health check
  health_checks = [google_compute_health_check.main[0].id]
  
  # Only create backend service in production
  count = var.environment == "prod" ? 1 : 0
  
  depends_on = [google_project_service.required_apis]
}

# Network endpoint group for Cloud Run
resource "google_compute_region_network_endpoint_group" "cloud_run" {
  name                  = "${var.app_name}-neg-${local.name_suffix}"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  
  cloud_run {
    service = google_cloud_run_service.main.name
  }
  
  # Only create NEG in production
  count = var.environment == "prod" ? 1 : 0
  
  depends_on = [google_project_service.required_apis]
}

# Health check for load balancer
resource "google_compute_health_check" "main" {
  name = "${var.app_name}-health-check-${local.name_suffix}"
  
  http_health_check {
    request_path = "/health"
    port         = 8080
  }
  
  check_interval_sec  = 10
  timeout_sec         = 5
  healthy_threshold   = 2
  unhealthy_threshold = 3
  
  # Only create health check in production
  count = var.environment == "prod" ? 1 : 0
  
  depends_on = [google_project_service.required_apis]
}

# HTTPS proxy for load balancer
resource "google_compute_target_https_proxy" "main" {
  name             = "${var.app_name}-https-proxy-${local.name_suffix}"
  url_map          = google_compute_url_map.main[0].id
  ssl_certificates = [google_compute_managed_ssl_certificate.main[0].id]
  
  # Only create HTTPS proxy in production
  count = var.environment == "prod" ? 1 : 0
  
  depends_on = [google_project_service.required_apis]
}

# Global forwarding rule for load balancer
resource "google_compute_global_forwarding_rule" "main" {
  name       = "${var.app_name}-forwarding-rule-${local.name_suffix}"
  target     = google_compute_target_https_proxy.main[0].id
  port_range = "443"
  ip_address = google_compute_global_address.lb_ip.address
  
  # Only create forwarding rule in production
  count = var.environment == "prod" ? 1 : 0
  
  depends_on = [google_project_service.required_apis]
}
# Cloud SQL Database for Kindle Content Server

# Database instance
resource "google_sql_database_instance" "main" {
  name             = "${var.app_name}-db-${local.name_suffix}"
  database_version = "POSTGRES_15"
  region           = var.region
  
  settings {
    tier                        = var.db_tier
    disk_size                   = var.db_disk_size
    disk_type                   = "PD_SSD"
    disk_autoresize            = true
    disk_autoresize_limit      = 100  # Cap at 100GB for cost control
    
    # Backup and maintenance configuration
    backup_configuration {
      enabled                        = true
      start_time                     = "02:00"  # 2 AM UTC
      location                       = var.region
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 7
        retention_unit   = "COUNT"
      }
    }
    
    maintenance_window {
      day          = 7  # Sunday
      hour         = 3  # 3 AM UTC
      update_track = "stable"
    }
    
    # Performance and reliability
    availability_type = "ZONAL"  # REGIONAL for HA in production
    
    # Security settings
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.self_link
      require_ssl     = true
      
      # Only allow private IP access
      authorized_networks {
        name  = "cloud-run-connector"
        value = "0.0.0.0/0"  # Will be restricted by VPC
      }
    }
    
    # Database flags for optimization
    dynamic "database_flags" {
      for_each = var.database_flags
      content {
        name  = database_flags.value.name
        value = database_flags.value.value
      }
    }
    
    # Additional performance flags
    database_flags {
      name  = "shared_preload_libraries"
      value = "pg_stat_statements"
    }
    
    database_flags {
      name  = "log_min_duration_statement"
      value = "1000"  # Log queries taking > 1 second
    }
    
    database_flags {
      name  = "log_connections"
      value = "on"
    }
    
    database_flags {
      name  = "log_disconnections"
      value = "on"
    }
    
    # Memory optimization for micro instance
    database_flags {
      name  = "shared_buffers"
      value = "32MB"
    }
    
    database_flags {
      name  = "effective_cache_size"
      value = "128MB"
    }
  }
  
  # Deletion protection
  deletion_protection = var.environment == "prod" ? true : false
  
  depends_on = [
    google_project_service.required_apis,
    google_compute_network.vpc,
    google_service_networking_connection.private_vpc_connection
  ]
}

# Main application database
resource "google_sql_database" "app_db" {
  name     = "${var.app_name}_${var.environment}"
  instance = google_sql_database_instance.main.name
}

# Database user for the application
resource "google_sql_user" "app_user" {
  name     = "${var.app_name}_user"
  instance = google_sql_database_instance.main.name
  password = random_password.db_password.result
}

# Random password for database user
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Store database credentials in Secret Manager
resource "google_secret_manager_secret" "db_password" {
  secret_id = "${var.app_name}-db-password-${local.name_suffix}"
  
  replication {
    auto {}
  }
  
  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}

# Database connection string secret
resource "google_secret_manager_secret" "db_connection" {
  secret_id = "${var.app_name}-db-connection-${local.name_suffix}"
  
  replication {
    auto {}
  }
  
  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "db_connection" {
  secret = google_secret_manager_secret.db_connection.id
  secret_data = "postgresql://${google_sql_user.app_user.name}:${random_password.db_password.result}@${google_sql_database_instance.main.private_ip_address}:5432/${google_sql_database.app_db.name}"
}

# SSL certificate for database connection
resource "google_sql_ssl_cert" "client_cert" {
  common_name = "${var.app_name}-client-cert"
  instance    = google_sql_database_instance.main.name
}

# Store SSL certificate in Secret Manager
resource "google_secret_manager_secret" "db_ssl_cert" {
  secret_id = "${var.app_name}-db-ssl-cert-${local.name_suffix}"
  
  replication {
    auto {}
  }
  
  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "db_ssl_cert" {
  secret      = google_secret_manager_secret.db_ssl_cert.id
  secret_data = google_sql_ssl_cert.client_cert.cert
}

resource "google_secret_manager_secret" "db_ssl_key" {
  secret_id = "${var.app_name}-db-ssl-key-${local.name_suffix}"
  
  replication {
    auto {}
  }
  
  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "db_ssl_key" {
  secret      = google_secret_manager_secret.db_ssl_key.id
  secret_data = google_sql_ssl_cert.client_cert.private_key
}
# Cloud Storage buckets for Kindle Content Server

# Books storage bucket
resource "google_storage_bucket" "books_bucket" {
  name     = "${var.app_name}-books-${local.name_suffix}"
  location = var.storage_location
  
  # Cost optimization
  storage_class = var.storage_class
  
  # Lifecycle management for cost optimization
  lifecycle_rule {
    condition {
      age = 365  # Move to Nearline after 1 year
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }
  
  lifecycle_rule {
    condition {
      age = 1095  # Move to Coldline after 3 years
    }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }
  
  # Security settings
  uniform_bucket_level_access = true
  
  # Enable versioning for data protection
  versioning {
    enabled = true
  }
  
  # CORS configuration for web uploads
  cors {
    origin          = var.allowed_domains
    method          = ["GET", "HEAD", "PUT", "POST", "DELETE"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
  
  depends_on = [google_project_service.required_apis]
}

# News content storage bucket
resource "google_storage_bucket" "news_bucket" {
  name     = "${var.app_name}-news-${local.name_suffix}"
  location = var.storage_location
  
  storage_class = var.storage_class
  
  # Shorter lifecycle for news content
  lifecycle_rule {
    condition {
      age = 30  # Delete news content after 30 days
    }
    action {
      type = "Delete"
    }
  }
  
  uniform_bucket_level_access = true
  
  versioning {
    enabled = false  # News content doesn't need versioning
  }
  
  cors {
    origin          = var.allowed_domains
    method          = ["GET", "HEAD"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
  
  depends_on = [google_project_service.required_apis]
}

# Static assets bucket (for frontend if needed)
resource "google_storage_bucket" "static_bucket" {
  name     = "${var.app_name}-static-${local.name_suffix}"
  location = var.storage_location
  
  storage_class = var.storage_class
  
  uniform_bucket_level_access = true
  
  # Make bucket publicly readable for static assets
  website {
    main_page_suffix = "index.html"
    not_found_page   = "404.html"
  }
  
  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD"]
    response_header = ["*"]
    max_age_seconds = 86400
  }
  
  depends_on = [google_project_service.required_apis]
}

# Backup bucket
resource "google_storage_bucket" "backup_bucket" {
  name     = "${var.app_name}-backup-${local.name_suffix}"
  location = var.storage_location
  
  storage_class = "COLDLINE"  # Cost-effective for backups
  
  lifecycle_rule {
    condition {
      age = 2555  # 7 years retention for compliance
    }
    action {
      type = "Delete"
    }
  }
  
  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }
  
  depends_on = [google_project_service.required_apis]
}

# Cloud Storage IAM bindings
resource "google_storage_bucket_iam_binding" "books_bucket_binding" {
  bucket = google_storage_bucket.books_bucket.name
  role   = "roles/storage.objectAdmin"
  
  members = [
    "serviceAccount:${google_service_account.cloud_run_sa.email}",
  ]
}

resource "google_storage_bucket_iam_binding" "news_bucket_binding" {
  bucket = google_storage_bucket.news_bucket.name
  role   = "roles/storage.objectAdmin"
  
  members = [
    "serviceAccount:${google_service_account.cloud_run_sa.email}",
  ]
}

resource "google_storage_bucket_iam_binding" "static_bucket_public" {
  bucket = google_storage_bucket.static_bucket.name
  role   = "roles/storage.objectViewer"
  
  members = [
    "allUsers",
  ]
}

resource "google_storage_bucket_iam_binding" "backup_bucket_binding" {
  bucket = google_storage_bucket.backup_bucket.name
  role   = "roles/storage.objectAdmin"
  
  members = [
    "serviceAccount:${google_service_account.backup_sa.email}",
  ]
}
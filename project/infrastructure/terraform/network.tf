# VPC and Networking for Kindle Content Server

# VPC Network
resource "google_compute_network" "vpc" {
  name                    = "${var.app_name}-vpc-${local.name_suffix}"
  auto_create_subnetworks = false
  mtu                     = 1460
  
  depends_on = [google_project_service.required_apis]
}

# Subnet for Cloud Run and other services
resource "google_compute_subnetwork" "subnet" {
  name          = "${var.app_name}-subnet-${local.name_suffix}"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.vpc.id
  
  # Enable private Google access for serverless services
  private_ip_google_access = true
  
  # Secondary ranges for future use (GKE, etc.)
  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.1.0.0/16"
  }
  
  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.2.0.0/16"
  }
}

# Reserve IP range for VPC peering with Google services
resource "google_compute_global_address" "private_ip_range" {
  name          = "${var.app_name}-private-ip-${local.name_suffix}"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
  
  depends_on = [google_project_service.required_apis]
}

# VPC peering connection for Cloud SQL
resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_range.name]
  
  depends_on = [google_project_service.required_apis]
}

# Serverless VPC Access Connector for Cloud Run
resource "google_vpc_access_connector" "connector" {
  name          = "${var.app_name}-connector-${local.name_suffix}"
  region        = var.region
  ip_cidr_range = "10.3.0.0/28"
  network       = google_compute_network.vpc.name
  
  # Cost optimization - minimum machine type
  min_throughput = 200
  max_throughput = 300
  machine_type   = "e2-micro"
  
  depends_on = [
    google_project_service.required_apis,
    google_compute_subnetwork.subnet
  ]
}

# Cloud NAT for outbound internet access
resource "google_compute_router" "router" {
  name    = "${var.app_name}-router-${local.name_suffix}"
  region  = var.region
  network = google_compute_network.vpc.id
}

resource "google_compute_router_nat" "nat" {
  name                               = "${var.app_name}-nat-${local.name_suffix}"
  router                             = google_compute_router.router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
  
  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# Firewall rules
resource "google_compute_firewall" "allow_internal" {
  name    = "${var.app_name}-allow-internal-${local.name_suffix}"
  network = google_compute_network.vpc.name
  
  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }
  
  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }
  
  allow {
    protocol = "icmp"
  }
  
  source_ranges = [
    "10.0.0.0/24",    # Main subnet
    "10.1.0.0/16",    # Pods range
    "10.2.0.0/16",    # Services range
    "10.3.0.0/28"     # VPC connector range
  ]
  
  target_tags = ["internal"]
}

# Allow health checks from Google Cloud Load Balancers
resource "google_compute_firewall" "allow_health_checks" {
  name    = "${var.app_name}-allow-health-checks-${local.name_suffix}"
  network = google_compute_network.vpc.name
  
  allow {
    protocol = "tcp"
    ports    = ["8080", "80", "443"]
  }
  
  source_ranges = [
    "130.211.0.0/22",
    "35.191.0.0/16"
  ]
  
  target_tags = ["load-balancer-backend"]
}

# Allow SSH for debugging (can be removed in production)
resource "google_compute_firewall" "allow_ssh" {
  name    = "${var.app_name}-allow-ssh-${local.name_suffix}"
  network = google_compute_network.vpc.name
  
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
  
  source_ranges = ["35.235.240.0/20"]  # Google Cloud Shell IP range
  target_tags   = ["ssh-allowed"]
  
  # Only create in non-production environments
  count = var.environment != "prod" ? 1 : 0
}

# Deny all other inbound traffic
resource "google_compute_firewall" "deny_all" {
  name    = "${var.app_name}-deny-all-${local.name_suffix}"
  network = google_compute_network.vpc.name
  
  deny {
    protocol = "all"
  }
  
  source_ranges = ["0.0.0.0/0"]
  priority      = 65534  # Lower priority than allow rules
}

# Reserve static IP for load balancer (if needed)
resource "google_compute_global_address" "lb_ip" {
  name = "${var.app_name}-lb-ip-${local.name_suffix}"
  
  depends_on = [google_project_service.required_apis]
}

# DNS zone for custom domain (optional)
resource "google_dns_managed_zone" "main" {
  name        = "${var.app_name}-zone-${local.name_suffix}"
  dns_name    = "${var.app_name}.example.com."
  description = "DNS zone for ${var.app_name}"
  
  # Only create if custom domain is needed
  count = var.environment == "prod" ? 1 : 0
  
  depends_on = [google_project_service.required_apis]
}
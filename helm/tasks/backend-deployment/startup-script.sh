#!/bin/bash
# Startup script for Kindle Content Server backend deployment
# This script will be executed when the VM instance starts

set -e

# Variables
APP_USER="kindle"
APP_DIR="/opt/kindle-backend"
LOG_FILE="/var/log/startup-script.log"

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a $LOG_FILE
}

log "Starting Kindle Content Server backend setup..."

# Update system packages
log "Updating system packages..."
apt-get update -y
apt-get upgrade -y

# Install essential packages
log "Installing essential packages..."
apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    postgresql-client \
    nginx \
    git \
    curl \
    wget \
    unzip \
    certbot \
    python3-certbot-nginx \
    supervisor \
    redis-server \
    build-essential \
    libpq-dev \
    pkg-config \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libjpeg-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff5-dev \
    tk-dev \
    tcl-dev \
    libffi-dev \
    libssl-dev

# Create application user
log "Creating application user..."
if ! id "$APP_USER" &>/dev/null; then
    useradd -r -s /bin/bash -m -d /home/$APP_USER $APP_USER
    log "Created user: $APP_USER"
else
    log "User $APP_USER already exists"
fi

# Create application directory
log "Creating application directory..."
mkdir -p $APP_DIR
chown $APP_USER:$APP_USER $APP_DIR

# Install Google Cloud SDK
log "Installing Google Cloud SDK..."
if [ ! -f /usr/bin/gcloud ]; then
    curl https://sdk.cloud.google.com | bash
    exec -l $SHELL
    gcloud init --skip-diagnostics
fi

# Configure Redis
log "Configuring Redis..."
systemctl enable redis-server
systemctl start redis-server

# Configure Nginx
log "Configuring Nginx..."
systemctl enable nginx

# Create log directories
log "Creating log directories..."
mkdir -p /var/log/kindle-backend
chown $APP_USER:$APP_USER /var/log/kindle-backend

# Configure firewall (if ufw is available)
log "Configuring firewall..."
if command -v ufw >/dev/null 2>&1; then
    ufw --force enable
    ufw allow ssh
    ufw allow http
    ufw allow https
    ufw allow 8080
fi

# Set up Python environment as app user
log "Setting up Python environment..."
sudo -u $APP_USER bash << 'EOF'
cd /opt/kindle-backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install Gunicorn first
pip install gunicorn

EOF

log "Startup script completed successfully!"
log "Next steps: Deploy application code and configure services"
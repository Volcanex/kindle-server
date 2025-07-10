#!/bin/bash

# Kindle Content Server - Production Startup Script
# Simple script to start the production server locally

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 Starting Kindle Content Server (Production Mode)${NC}"
echo "=============================================="

# Check if we're in the right directory
if [ ! -f "backend/app_production.py" ]; then
    echo -e "${RED}❌ Error: backend/app_production.py not found${NC}"
    echo "Please run this script from the project root directory"
    exit 1
fi

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is required but not installed${NC}"
    exit 1
fi

# Load environment variables if .env exists
if [ -f ".env" ]; then
    echo -e "${YELLOW}📄 Loading environment variables from .env${NC}"
    export $(cat .env | grep -v '#' | grep -v '^$' | xargs)
else
    echo -e "${YELLOW}⚠️  No .env file found. Using default development settings.${NC}"
    echo "For production, create .env file from .env.example"
fi

# Set default values
export FLASK_ENV=${FLASK_ENV:-production}
export PORT=${PORT:-8080}
export HOST=${HOST:-0.0.0.0}

# Check if requirements are installed
echo -e "${YELLOW}📦 Checking Python dependencies...${NC}"
cd backend

# Try to import required modules
python3 -c "
import flask
import flask_sqlalchemy
import flask_cors
print('✅ Core dependencies available')
" 2>/dev/null || {
    echo -e "${RED}❌ Required dependencies not found${NC}"
    echo "Installing dependencies..."
    pip3 install -r ../requirements.txt
}

# Create database tables if needed
echo -e "${YELLOW}🗄️  Initializing database...${NC}"
python3 -c "
from app_production import app
with app.app_context():
    from models import db
    db.create_all()
    print('✅ Database initialized')
" || echo -e "${YELLOW}⚠️  Database initialization skipped${NC}"

# Start the server
echo -e "${GREEN}🌐 Starting server on ${HOST}:${PORT}${NC}"
echo ""
echo "Service endpoints:"
echo "  Health Check: http://${HOST}:${PORT}/health"
echo "  API Health:   http://${HOST}:${PORT}/api/health"
echo "  KUAL API:     http://${HOST}:${PORT}/api/v1/"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Check if gunicorn is available for production serving
if command -v gunicorn &> /dev/null; then
    echo -e "${GREEN}🚀 Starting with Gunicorn (Production Server)${NC}"
    gunicorn --bind ${HOST}:${PORT} --workers 2 --timeout 120 --access-logfile - --error-logfile - app_production:app
else
    echo -e "${YELLOW}⚠️  Gunicorn not found, starting with Flask development server${NC}"
    echo "For production, install gunicorn: pip install gunicorn"
    python3 app_production.py
fi
# Kindle Content Server Project

## Overview
Flask-based server for aggregating news and managing book storage for Kindle devices, deployed on Google Cloud Platform.

## Project Structure

### `/backend/` - Flask Server
- **Core Flask application** with REST API endpoints
- **News aggregation** service using RSS feeds
- **Book management** system with Cloud Storage integration
- **Kindle sync** protocol implementation
- **Database models** for PostgreSQL/Cloud SQL

### `/frontend/` - React Native Mobile App
- **Cross-platform mobile interface** using Expo
- **File upload functionality** for books
- **News source management** interface
- **Sync status monitoring** dashboard
- **Authentication** integration

### `/kindle/` - KUAL Plugin
- **Kindle device plugin** for content synchronization
- **Sync client** for downloading content
- **Configuration management** for device settings
- **Local storage** management on Kindle

### `/infrastructure/` - Cloud Infrastructure
- **Google Cloud** deployment configurations
- **Docker** containerization setup
- **CI/CD** pipeline configurations
- **Database** schema and migrations
- **Security** IAM and firewall rules

### `/shared/` - Common Utilities
- **Data transfer** formats and schemas
- **Authentication** utilities
- **Logging** and monitoring tools
- **Configuration** management
- **Testing** utilities

## Technology Stack
- **Backend**: Flask, Python 3.9+, feedparser, ebooklib
- **Frontend**: React Native, Expo, TypeScript
- **Cloud**: Google Cloud Run, Cloud Storage, Cloud SQL
- **Database**: PostgreSQL
- **Kindle**: KUAL plugin, Shell scripts
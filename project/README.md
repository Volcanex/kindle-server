# Kindle Content Server

A comprehensive content management and synchronization system for Kindle devices, featuring automated news aggregation, book management, and seamless device synchronization.

## 🚀 Quick Start

### Production Deployment
```bash
git clone <your-repo-url>
cd kindle-content-server
cp .env.example .env
# Edit .env with your configuration
./deploy.sh
```

### Local Development
```bash
# Backend
cd backend
python app_local.py

# Frontend  
cd frontend
npm start

# Test KUAL client
python test_kual_simulation.py
```

## 📋 Features

### 🗞️ News Aggregation
- **RSS Feed Processing**: Automated aggregation from multiple sources
- **EPUB Generation**: Convert articles to Kindle-compatible format
- **Daily Digests**: Automatic compilation of daily news
- **Smart Filtering**: Content curation and deduplication

### 📚 Book Management
- **Upload & Storage**: Secure cloud storage for personal library
- **Format Support**: EPUB, PDF, MOBI, TXT
- **Metadata Management**: Automatic book information extraction
- **Sync Status**: Real-time synchronization tracking

### 📱 Mobile Interface
- **React Native App**: Cross-platform mobile management
- **File Upload**: Direct book upload from mobile device
- **News Sources**: Manage RSS feeds and content sources
- **Sync Dashboard**: Monitor device synchronization status

### 🔧 KUAL Integration
- **Kindle Plugin**: Native device synchronization
- **Automatic Downloads**: Background content retrieval
- **Device Authentication**: Secure API access
- **Status Reporting**: Sync progress and error handling

### ☁️ Production Ready
- **Google Cloud**: Auto-scaling deployment on Cloud Run
- **Docker Support**: Containerized deployment
- **Security**: Authentication, CORS, rate limiting
- **Monitoring**: Health checks and logging
- **CI/CD**: Automated deployment pipelines

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Native  │    │   Flask API     │    │   Google Cloud  │
│   Mobile App    │◄──►│   Backend       │◄──►│   Storage       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              ▲
                              │
                       ┌─────────────────┐
                       │   KUAL Plugin   │
                       │   Kindle Device │
                       └─────────────────┘
```

## 📁 Project Structure

### `/backend/` - Flask API Server
```
backend/
├── app_local.py          # Development server
├── app_production.py     # Production server
├── routes/               # API endpoints
│   ├── articles.py       # News article management
│   ├── books.py          # Book management
│   ├── kual_api.py       # KUAL device API
│   ├── news.py           # News aggregation
│   ├── rss_feeds.py      # RSS feed management
│   └── sync.py           # Synchronization
├── models.py             # Database models
├── config/               # Configuration
└── tests/                # Unit tests
```

### `/frontend/` - React Native App
```
frontend/
├── App.tsx               # Main application
├── screens/              # App screens
│   ├── BooksScreen.tsx   # Book management
│   ├── NewsScreen.tsx    # News reading
│   └── SyncScreen.tsx    # Sync dashboard
├── components/           # Reusable components
├── services/             # API integration
└── types/                # TypeScript definitions
```

### `/kindle/` - KUAL Plugin
```
kindle/
├── README.md             # Installation guide
├── extensions/
│   └── kindle_sync/      # KUAL plugin
│       ├── bin/          # Executables
│       ├── config/       # Configuration
│       ├── logs/         # Log files
│       ├── scripts/      # Utility scripts
│       ├── meta.ini      # KUAL metadata
│       └── sync.sh       # Main entry point
```

### Production Deployment Files
```
├── Dockerfile            # Container configuration
├── requirements.txt      # Python dependencies
├── app.yaml             # App Engine config
├── cloudbuild.yaml      # Cloud Build config
├── deploy.sh            # Deployment script
├── start_production.sh  # Production startup
├── .env.example         # Environment template
└── DEPLOYMENT.md        # Deployment guide
```

## 🛠️ Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend** | Flask, Python 3.12+ | REST API server |
| **Frontend** | React Native, Expo | Mobile application |
| **Database** | PostgreSQL, SQLAlchemy | Data persistence |
| **Storage** | Google Cloud Storage | File storage |
| **Deployment** | Docker, Cloud Run | Container deployment |
| **Kindle** | KUAL, Bash scripts | Device integration |
| **News** | feedparser, BeautifulSoup | Content processing |
| **Books** | ebooklib, Pillow | File processing |

## 🔧 API Endpoints

### Content Management
- `GET /api/books` - List books
- `POST /api/books` - Upload book
- `GET /api/news` - Get news articles
- `POST /api/rss-feeds` - Add RSS feed

### KUAL Device API
- `POST /api/v1/auth/device` - Authenticate device
- `GET /api/v1/content/list` - Get available content
- `GET /api/v1/content/download/{id}` - Download content
- `POST /api/v1/content/sync-status` - Report sync status

### Health & Monitoring
- `GET /health` - Service health check
- `GET /api/health` - API health with database check

## 🚀 Deployment Options

### 1. Google Cloud Run (Recommended)
```bash
./deploy.sh
# Select option 1 for full Cloud Build deployment
```

### 2. Docker Local
```bash
docker build -t kindle-content-server .
docker run -p 8080:8080 --env-file .env kindle-content-server
```

### 3. App Engine
```bash
gcloud app deploy app.yaml
```

### 4. Manual Production
```bash
./start_production.sh
```

## ⚙️ Configuration

### Environment Variables
```env
# Required
GOOGLE_CLOUD_PROJECT=your-project-id
SECRET_KEY=your-secure-secret-key
SERVER_PASSCODE=your-api-passcode

# Database
CLOUD_SQL_CONNECTION_NAME=project:region:instance
DB_USER=kindle_user
DB_PASS=secure-password
DB_NAME=kindle_content_server

# Optional
GCS_BUCKET_NAME=kindle-content-storage
SERVICE_VERSION=1.0.0
```

### KUAL Configuration
Update `/mnt/us/extensions/kindle_sync/config/config.json` on your Kindle:
```json
{
  "server_url": "https://your-deployed-service-url.com",
  "api_key": "your-server-passcode"
}
```

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest tests/
```

### KUAL Client Simulation
```bash
python test_kual_simulation.py
```

### Full Test Suite
```bash
./run_kual_tests.sh
```

## 📚 Documentation

- **[Deployment Guide](DEPLOYMENT.md)** - Complete production deployment
- **[KUAL Installation](kindle/README.md)** - Kindle plugin setup
- **[API Documentation](backend/routes/)** - REST API reference

## 🔒 Security Features

- **Device Authentication**: Secure API key system
- **CORS Protection**: Configured for production domains
- **Rate Limiting**: API request throttling
- **Security Headers**: HTTPS enforcement, XSS protection
- **Input Validation**: Request sanitization and validation

## 📊 Monitoring

- **Health Checks**: Automated service monitoring
- **Google Cloud Logging**: Centralized log aggregation
- **Error Tracking**: Comprehensive error reporting
- **Performance Metrics**: Request timing and throughput

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and support:
1. Check the [Deployment Guide](DEPLOYMENT.md)
2. Review [KUAL Installation](kindle/README.md)
3. Check logs in Google Cloud Console
4. Create an issue in the repository

## 🔄 Version History

- **v1.0.0** - Initial release with full KUAL integration
- **v0.9.0** - Production deployment ready
- **v0.8.0** - KUAL client API implementation
- **v0.7.0** - React Native mobile app
- **v0.6.0** - News aggregation system
- **v0.5.0** - Book management system

---

**Ready for production deployment!** 🎉

Clone, configure, and deploy in minutes with the automated deployment script.
# Kindle Content Server Architecture Plan

## Project Overview
A Flask-based server running on Google Cloud that aggregates daily news and manages book storage for Kindle devices. The system includes automated news compilation, book storage, and sync functionality with Kindle devices through a KUAL plugin.

## Architecture Components

### 1. Core Infrastructure
- **Platform**: Google Cloud Platform (GCP)
- **Compute**: Cloud Run (recommended) or E2-micro instance for development
- **Container Registry**: Google Artifact Registry
- **Storage**: Cloud Storage for books/content + Cloud SQL for metadata
- **CI/CD**: Cloud Build with automated deployments

### 2. Application Stack

#### Backend Server (Flask)
```
├── app/
│   ├── __init__.py
│   ├── routes/
│   │   ├── sync.py          # Kindle sync endpoints
│   │   ├── books.py         # Book management
│   │   └── news.py          # News aggregation
│   ├── services/
│   │   ├── news_aggregator.py
│   │   ├── book_manager.py
│   │   └── kindle_sync.py
│   ├── models/
│   │   ├── book.py
│   │   └── news_item.py
│   └── utils/
│       ├── epub_creator.py
│       └── file_handler.py
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

#### Frontend Interface
- **Framework**: Flask-based web interface
- **Features**: Book upload, news source management, sync status monitoring
- **Authentication**: Google Identity-Aware Proxy (IAP)

#### Mobile/Web Frontend (React Native)
- **Cross-platform**: React Native with Expo for iOS/Android/Web deployment
- **Simple UI**: Book upload, RSS feed management, sync status dashboard
- **Connection**: Direct HTTPS to Cloud Run endpoint or SSH tunnel to development server
- **Features**: File picker for book uploads, real-time sync status, basic configuration
- **Deployment**: Expo web build for browser access, mobile apps via app stores

#### KUAL Plugin for Kindle
```
├── extensions/
│   └── kindle_sync/
│       ├── meta.ini
│       ├── bin/
│       │   └── sync_client
│       ├── config.json
│       └── sync.sh
```

## Detailed Architecture

### Google Cloud Infrastructure

#### Recommended: Cloud Run Deployment
```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/kindle-server', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/kindle-server']
  - name: 'gcr.io/cloud-builders/gcloud'
    args: ['run', 'deploy', 'kindle-server', '--image', 'gcr.io/$PROJECT_ID/kindle-server', '--region', 'us-central1']
```

**Benefits of Cloud Run:**
- Serverless scaling (0-1000+ instances)
- Pay-per-request pricing
- Automatic HTTPS and load balancing
- No infrastructure management

**Reference**: [Cloud Run Python Quickstart](https://cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-service)

#### Alternative: E2-micro Instance
**Free Tier Specifications:**
- 0.25 vCPU (bursts to 2 vCPU)
- 1 GB RAM
- 744 hours/month (always-free)
- Perfect for development/testing

**Reference**: [Google Cloud Free Tier](https://cloud.google.com/free)

### Storage Architecture

#### Cloud Storage Structure
```
kindle-content-bucket/
├── books/
│   ├── uploaded/          # User-uploaded books
│   └── processed/         # Converted/optimized books
├── news/
│   ├── daily/            # Daily news compilations
│   └── archives/         # Historical news
└── temp/                 # Temporary processing files
```

#### Database Schema (Cloud SQL)
```sql
-- Books table
CREATE TABLE books (
    id UUID PRIMARY KEY,
    title VARCHAR(255),
    author VARCHAR(255),
    file_path VARCHAR(500),
    format VARCHAR(10),
    uploaded_at TIMESTAMP,
    kindle_compatible BOOLEAN
);

-- News sources table
CREATE TABLE news_sources (
    id UUID PRIMARY KEY,
    name VARCHAR(100),
    rss_url VARCHAR(500),
    active BOOLEAN,
    last_fetched TIMESTAMP
);

-- Sync logs table
CREATE TABLE sync_logs (
    id UUID PRIMARY KEY,
    kindle_id VARCHAR(100),
    sync_type VARCHAR(50),
    items_synced INTEGER,
    sync_timestamp TIMESTAMP,
    status VARCHAR(20)
);
```

### Flask Application Architecture

#### Containerized Flask Setup
```dockerfile
# Multi-stage build for optimization
FROM python:3.9-slim as builder
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
RUN apt-get update && apt-get install -y --no-install-recommends gcc
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

FROM python:3.9-slim
WORKDIR /app
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/*
COPY . .
RUN adduser --disabled-password --gecos '' appuser
USER appuser
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "app:app"]
```

**Security Features:**
- Non-root user execution
- Multi-stage builds for smaller images
- Environment variable configuration
- Flask-Talisman for security headers

**Reference**: [Python Docker Best Practices](https://snyk.io/blog/best-practices-containerizing-python-docker/)

#### Core Dependencies
```python
# requirements.txt
Flask==2.3.3
gunicorn==21.2.0
google-cloud-storage==2.10.0
google-cloud-sql-connector==1.4.3
SQLAlchemy==2.0.23
feedparser==6.0.10
ebooklib==0.18
beautifulsoup4==4.12.2
APScheduler==3.10.4
Flask-SQLAlchemy==3.1.1
Flask-Migrate==4.0.5
Flask-Talisman==1.1.0
python-dotenv==1.0.0
```

### News Aggregation System

#### RSS Processing Pipeline
```python
# services/news_aggregator.py
class NewsAggregator:
    def __init__(self):
        self.feeds = self.load_rss_feeds()
        self.scheduler = BackgroundScheduler()
    
    def daily_aggregation(self):
        """Run daily at 6 AM"""
        articles = self.fetch_articles()
        epub_file = self.create_kindle_book(articles)
        self.store_in_cloud_storage(epub_file)
        self.notify_kindle_devices()
    
    def create_kindle_book(self, articles):
        """Convert articles to EPUB format"""
        book = epub.EpubBook()
        # ... EPUB creation logic
        return filename
```

#### Supported News Sources
- RSS feeds from major news outlets
- Custom content scraping with Mozilla Readability
- Article extraction and cleaning
- Automatic EPUB generation

**Reference**: [EbookLib Documentation](https://docs.sourcefabric.org/projects/ebooklib/en/latest/)

### Kindle Sync Protocol

#### KUAL Plugin Architecture
The KUAL (Kindle Unified Application Launcher) plugin enables communication between Kindle devices and the server.

```bash
# extensions/kindle_sync/sync.sh
#!/bin/bash
KINDLE_ID=$(cat /var/local/kindle_id)
SERVER_URL="https://your-kindle-server.cloudrun.app"

# Fetch available content
curl -H "X-Kindle-ID: $KINDLE_ID" \
     "$SERVER_URL/api/sync/available" \
     -o /tmp/available_content.json

# Download new content
curl -H "X-Kindle-ID: $KINDLE_ID" \
     "$SERVER_URL/api/sync/download" \
     --data @/tmp/available_content.json \
     -o /tmp/new_content.zip

# Extract to documents folder
unzip /tmp/new_content.zip -d /mnt/us/documents/
```

#### Server Sync Endpoints
```python
# routes/sync.py
@app.route('/api/sync/available', methods=['GET'])
def get_available_content():
    kindle_id = request.headers.get('X-Kindle-ID')
    
    # Get new books and daily news
    new_books = get_new_books_for_kindle(kindle_id)
    daily_news = get_latest_news_compilation()
    
    return jsonify({
        'books': new_books,
        'news': daily_news,
        'last_sync': get_last_sync_time(kindle_id)
    })

@app.route('/api/sync/download', methods=['POST'])
def download_content():
    # Stream content files to Kindle
    # Log sync activity
    pass
```

**Reference**: [KUAL Development Guide](https://www.mobileread.com/forums/showthread.php?t=203326)

## Deployment Strategy

### Development Phase
1. **Local Development**: Docker Compose setup
2. **Testing**: Deploy to Cloud Run with staging environment
3. **Free Tier**: Use E2-micro instance for cost-effective testing

### Production Deployment
1. **Cloud Run**: Serverless scaling for production traffic
2. **Artifact Registry**: Container image management
3. **Cloud Build**: Automated CI/CD pipeline
4. **Monitoring**: Cloud Operations Suite for observability

### Security Considerations
- **IAM**: Service accounts with minimal permissions
- **Network**: VPC firewall rules for Kindle device access
- **Data**: Encryption at rest and in transit
- **Authentication**: Google Identity-Aware Proxy for admin interface

**Reference**: [Google Cloud Security Best Practices](https://cloud.google.com/architecture/best-practices-vpc-design)

## Cost Optimization

### Free Tier Usage
- **Cloud Run**: 2M requests/month, 360,000 GB-seconds
- **Cloud Storage**: 5 GB storage
- **Cloud SQL**: 1 shared-core instance
- **Cloud Build**: 120 build-minutes/day

### Estimated Monthly Costs (Beyond Free Tier)
- **Cloud Run**: ~$0.01 per 1000 requests
- **Cloud Storage**: ~$0.02 per GB/month
- **Cloud SQL**: ~$7-15/month for db-f1-micro
- **Network**: ~$0.12 per GB egress

**Reference**: [Google Cloud Pricing Calculator](https://cloud.google.com/products/calculator)

## Implementation Timeline

### Phase 1: Core Infrastructure (Week 1-2)
- Set up Google Cloud project and IAM
- Create Flask application structure
- Implement basic book upload/storage
- Deploy to Cloud Run

### Phase 2: News Aggregation (Week 3)
- RSS feed processing
- EPUB generation
- Automated scheduling
- Content management interface

### Phase 3: Mobile Frontend (Week 3-4)
- React Native app with Expo setup
- Basic UI for book uploads and sync status
- HTTPS API integration with Flask backend
- SSH tunnel configuration for development

### Phase 4: Kindle Integration (Week 4-5)
- KUAL plugin development
- Sync protocol implementation
- Testing with Kindle devices
- Error handling and logging

### Phase 5: Production Hardening (Week 6)
- Security review and hardening
- Performance optimization
- Monitoring and alerting
- Documentation and user guides

## Getting Started

### Prerequisites
- Google Cloud account with billing enabled
- Docker and Docker Compose installed
- Jailbroken Kindle device (for KUAL plugin)

### Quick Start Commands
```bash
# Clone repository
git clone <repository-url>
cd kindle-server

# Set up environment
cp .env.example .env
# Edit .env with your Google Cloud credentials

# Local development
docker-compose up --build

# Deploy to Google Cloud
gcloud builds submit --config cloudbuild.yaml
```

## References and Documentation

### Google Cloud Resources
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Artifact Registry](https://cloud.google.com/artifact-registry/docs)
- [Cloud Storage](https://cloud.google.com/storage/docs)
- [Cloud SQL](https://cloud.google.com/sql/docs)

### Development Resources
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Docker Best Practices](https://docs.docker.com/develop/best-practices/)
- [EbookLib Library](https://github.com/aerkalov/ebooklib)
- [Feedparser Library](https://feedparser.readthedocs.io/)

### Kindle Development
- [MobileRead Forums](https://www.mobileread.com/forums/)
- [Kindle Modding Wiki](https://kindlemodding.org/)
- [KUAL Extension Development](https://www.mobileread.com/forums/showthread.php?t=203326)

This architecture provides a scalable, cost-effective solution for automated Kindle content management using modern cloud infrastructure and containerization best practices.
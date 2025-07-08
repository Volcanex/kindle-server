# Kindle Content Server Backend

A Flask-based backend service for managing and syncing ebooks and news content to Kindle devices. Optimized for Google Cloud Run deployment with modern 2024 best practices.

## Features

### 📚 Book Management
- Upload and store ebooks in multiple formats (EPUB, PDF, MOBI, AZW, TXT)
- Extract metadata from ebook files automatically
- Google Cloud Storage integration for scalable file storage
- Book organization with genres, tags, and reading progress tracking

### 📰 News Aggregation
- RSS feed parsing and content aggregation
- Automatic content quality scoring and filtering
- News digest generation in EPUB format
- Support for multiple news sources and categories

### 📧 Kindle Sync
- Email-based delivery to Kindle devices
- Batch synchronization support
- Retry mechanisms for failed deliveries
- Comprehensive sync logging and monitoring

### ☁️ Cloud-Native
- Google Cloud Run optimized deployment
- Cloud SQL PostgreSQL database
- Cloud Storage for file management
- Cloud Logging integration

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL (or Google Cloud SQL)
- Google Cloud Storage bucket
- Email credentials for Kindle delivery

### Local Development

1. **Clone and setup**
```bash
cd backend/
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Initialize database**
```bash
flask db upgrade
```

4. **Run development server**
```bash
python app.py
```

The API will be available at `http://localhost:8080`

### Docker Deployment

```bash
# Build image
docker build -t kindle-backend .

# Run container
docker run -p 8080:8080 --env-file .env kindle-backend
```

### Google Cloud Run Deployment

```bash
# Build and deploy
gcloud run deploy kindle-backend \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

## API Endpoints

### Books API (`/api/books`)
- `GET /` - List books with filtering and pagination
- `POST /` - Create new book entry
- `POST /upload` - Upload book file
- `GET /{book_id}` - Get book details
- `PUT /{book_id}` - Update book metadata
- `DELETE /{book_id}` - Delete book
- `GET /{book_id}/download` - Get download URL
- `PUT /{book_id}/progress` - Update reading progress

### News API (`/api/news`)
- `GET /` - List news items with filtering
- `POST /aggregate` - Trigger news aggregation
- `POST /digest` - Create news digest EPUB
- `GET /sources` - List news sources
- `GET /categories` - List categories
- `PUT /{news_id}/include` - Include in EPUB
- `PUT /{news_id}/exclude` - Exclude from EPUB

### Sync API (`/api/sync`)
- `POST /book/{book_id}` - Sync book to Kindle
- `POST /news-digest` - Sync news digest to Kindle
- `POST /batch` - Batch sync multiple books
- `GET /logs` - Get sync logs
- `POST /retry/{log_id}` - Retry failed sync

### Health and Status
- `GET /health` - Health check endpoint
- `GET /` - Service information

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | Required |
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `GCS_BUCKET_NAME` | Google Cloud Storage bucket | Required |
| `EMAIL_USER` | SMTP username | Required |
| `EMAIL_PASSWORD` | SMTP password | Required |
| `SMTP_SERVER` | SMTP server address | smtp.gmail.com |
| `SMTP_PORT` | SMTP server port | 587 |
| `ALLOWED_ORIGINS` | CORS allowed origins | * |

### Google Cloud Configuration

1. **Cloud SQL Setup**
```bash
# Create instance
gcloud sql instances create kindle-db \
  --database-version=POSTGRES_14 \
  --tier=db-f1-micro \
  --region=us-central1

# Create database
gcloud sql databases create kindle_content_server \
  --instance=kindle-db
```

2. **Cloud Storage Setup**
```bash
# Create bucket
gsutil mb gs://your-kindle-content-bucket

# Set permissions
gsutil iam ch serviceAccount:your-service-account@project.iam.gserviceaccount.com:roles/storage.admin gs://your-kindle-content-bucket
```

## Architecture

### Service Layer
```
├── BookManager - File upload, storage, metadata
├── NewsAggregator - RSS parsing, content processing
└── KindleSyncService - Email delivery, sync tracking
```

### Data Models
```
├── Book - Ebook metadata and storage info
├── NewsItem - RSS article content and metadata
└── SyncLog - Sync operation tracking
```

### Utilities
```
├── EpubCreator - EPUB file generation
└── FileHandler - Google Cloud Storage operations
```

## Development

### Code Structure
- **Models**: SQLAlchemy ORM models for database entities
- **Routes**: Flask blueprints for API endpoints
- **Services**: Business logic and external integrations
- **Utils**: Reusable utility functions

### Testing
```bash
# Run tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

### Code Quality
```bash
# Format code
black .

# Lint code
flake8 .
```

## Monitoring and Logging

### Health Checks
- `/health` endpoint for load balancer checks
- Database connectivity verification
- External service health monitoring

### Logging
- Structured JSON logging
- Google Cloud Logging integration
- Request tracing with correlation IDs
- Error tracking and alerting

### Metrics
- Sync success/failure rates
- File upload/download metrics
- News aggregation statistics
- API response times

## Security

### Authentication
- Kindle email validation (@kindle.com domain)
- Input sanitization and validation
- SQL injection prevention through ORM

### File Security
- File type validation
- Size limits for uploads
- Malware scanning (configurable)
- Secure temporary file handling

### Data Protection
- Encryption in transit (HTTPS)
- Encryption at rest (Cloud Storage)
- No sensitive data in logs
- IAM-based access controls

## Troubleshooting

### Common Issues

1. **Email delivery failures**
   - Check SMTP credentials and server settings
   - Verify Kindle email format (@kindle.com)
   - Check email rate limits

2. **File upload errors**
   - Verify Google Cloud Storage permissions
   - Check file size limits
   - Ensure supported file format

3. **Database connection issues**
   - Check Cloud SQL instance status
   - Verify connection string format
   - Review IAM permissions

### Debugging
- Enable debug logging with `LOG_LEVEL=DEBUG`
- Check Cloud Logging for detailed error traces
- Use `/api/sync/logs` to monitor sync operations

## Performance Optimization

### Caching
- Redis for session and metadata caching
- RSS feed result caching
- Database query optimization

### Async Processing
- Celery for background tasks
- Queue-based sync operations
- Async file operations

### Resource Management
- Connection pooling for database
- File cleanup after operations
- Memory-efficient streaming

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes following the code style
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
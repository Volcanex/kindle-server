# Backend Implementation Patterns

## Architectural Patterns

### 1. Service Layer Pattern
The backend implements a clear service layer that encapsulates business logic and external integrations.

```python
# Service classes handle domain-specific operations
class BookManager:
    def upload_book(self, file, metadata):
        # File validation
        # Storage operations  
        # Database operations
        # Return result

class NewsAggregator:
    def aggregate_feed(self, feed_url):
        # RSS parsing
        # Content processing
        # Deduplication
        # Quality scoring
```

**Benefits:**
- Separation of concerns
- Testable business logic
- Reusable components
- Clear API boundaries

### 2. Repository Pattern (via SQLAlchemy)
Data access is abstracted through SQLAlchemy ORM, providing a repository-like interface.

```python
# Model methods act as repository pattern
class Book:
    @classmethod
    def search(cls, query, limit=50):
        # Complex query logic
        return results
    
    @classmethod
    def get_pending_sync(cls):
        # Domain-specific queries
        return books
```

**Benefits:**
- Database abstraction
- Complex query encapsulation
- Domain-driven queries
- Easy testing with mocks

### 3. Factory Pattern for Application Creation
Flask application uses factory pattern for flexible configuration.

```python
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    
    # Register blueprints
    app.register_blueprint(sync_bp)
    
    return app
```

**Benefits:**
- Multiple configurations
- Testing flexibility
- Extension initialization
- Modular setup

## Data Flow Patterns

### 1. Request-Response Flow
```
Request → Route → Service → Model → Database
                    ↓
Response ← Route ← Service ← Model ← Database
```

**Implementation:**
```python
@books_bp.route('/', methods=['POST'])
def create_book():
    # 1. Validate request
    data = request.json
    
    # 2. Call service
    book_manager = BookManager()
    book = book_manager.upload_book(data)
    
    # 3. Return response
    return jsonify(book.to_dict()), 201
```

### 2. Background Task Pattern
Long-running operations use async processing with Celery.

```python
# Sync operations happen asynchronously
@celery.task
def sync_book_task(book_id, kindle_email):
    sync_service = KindleSyncService()
    return sync_service.sync_book_to_kindle(book_id, kindle_email)

# API triggers task
@sync_bp.route('/book/<book_id>', methods=['POST'])
def sync_book(book_id):
    task = sync_book_task.delay(book_id, kindle_email)
    return jsonify({'task_id': task.id})
```

### 3. Event-Driven Updates
Models emit events for cross-cutting concerns.

```python
class Book:
    def mark_synced(self):
        self.sync_status = 'synced'
        self.last_synced_at = datetime.utcnow()
        db.session.commit()
        
        # Event emission
        self._emit_sync_event('book_synced')
```

## Error Handling Patterns

### 1. Structured Error Responses
Consistent error format across all endpoints.

```python
def handle_error(error_message, status_code=500, error_code=None):
    return jsonify({
        'error': error_message,
        'error_code': error_code,
        'timestamp': datetime.utcnow().isoformat()
    }), status_code

# Usage in routes
try:
    result = service.operation()
except ValidationError as e:
    return handle_error(str(e), 400, 'VALIDATION_ERROR')
```

### 2. Exception Translation
Service layer exceptions are translated to HTTP responses.

```python
# Service raises domain exceptions
class BookUploadError(Exception):
    pass

# Route translates to HTTP
except BookUploadError as e:
    logger.error(f"Book upload failed: {e}")
    return handle_error("Failed to upload book", 500)
```

### 3. Transaction Rollback Pattern
Database operations use transaction boundaries.

```python
def create_book_with_metadata(book_data, metadata):
    try:
        book = Book(**book_data)
        db.session.add(book)
        
        # Additional operations
        process_metadata(book, metadata)
        
        db.session.commit()
        return book
        
    except Exception as e:
        db.session.rollback()
        raise
```

## Integration Patterns

### 1. External Service Adapter
External services are wrapped in adapter classes.

```python
class GoogleCloudStorageAdapter:
    def __init__(self):
        self.client = storage.Client()
        self.bucket = self.client.bucket(Config.GCS_BUCKET_NAME)
    
    def upload_file(self, content, path):
        # GCS-specific logic
        blob = self.bucket.blob(path)
        blob.upload_from_string(content)
        return blob.public_url

# Usage in services
class BookManager:
    def __init__(self):
        self.storage = GoogleCloudStorageAdapter()
```

### 2. Retry Pattern with Exponential Backoff
Failed operations are retried with increasing delays.

```python
import time
from functools import wraps

def retry_with_backoff(max_retries=3, base_delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
            
        return wrapper
    return decorator

@retry_with_backoff(max_retries=3)
def send_email(to_email, content):
    # Email sending logic
```

### 3. Circuit Breaker Pattern
Prevent cascading failures with circuit breaker.

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func, *args, **kwargs):
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'HALF_OPEN'
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self.reset()
            return result
        except Exception as e:
            self.record_failure()
            raise

# Usage
rss_circuit_breaker = CircuitBreaker()

def fetch_rss_feed(url):
    return rss_circuit_breaker.call(requests.get, url)
```

## Caching Patterns

### 1. Function-Level Caching
Cache expensive computations at function level.

```python
from functools import lru_cache
import redis

redis_client = redis.Redis()

def cache_result(expiration=3600):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try cache first
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Compute and cache
            result = func(*args, **kwargs)
            redis_client.setex(cache_key, expiration, json.dumps(result))
            
            return result
        return wrapper
    return decorator

@cache_result(expiration=1800)
def get_news_digest_preview(max_articles, min_quality):
    # Expensive operation
    return preview_data
```

### 2. Model-Level Caching
Cache frequently accessed model data.

```python
class Book:
    @classmethod
    @cache_result(expiration=900)
    def get_popular_books(cls, limit=20):
        return cls.query.order_by(cls.download_count.desc()).limit(limit).all()
    
    @property
    def cached_metadata(self):
        cache_key = f"book_metadata:{self.id}"
        metadata = redis_client.get(cache_key)
        
        if not metadata:
            metadata = self._compute_metadata()
            redis_client.setex(cache_key, 3600, json.dumps(metadata))
        else:
            metadata = json.loads(metadata)
            
        return metadata
```

### 3. Response Caching
Cache API responses for read-heavy endpoints.

```python
def cache_response(expiration=300):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key from request
            cache_key = f"response:{request.path}:{request.query_string.decode()}"
            
            cached_response = redis_client.get(cache_key)
            if cached_response:
                return Response(cached_response, mimetype='application/json')
            
            # Generate response
            response = func(*args, **kwargs)
            
            # Cache if successful
            if response.status_code == 200:
                redis_client.setex(cache_key, expiration, response.get_data())
            
            return response
        return wrapper
    return decorator

@books_bp.route('/stats')
@cache_response(expiration=600)
def get_book_stats():
    # Expensive stats computation
    return jsonify(stats)
```

## Security Patterns

### 1. Input Validation Pattern
Validate all inputs at the boundary.

```python
from marshmallow import Schema, fields, validate

class BookUploadSchema(Schema):
    title = fields.Str(required=True, validate=validate.Length(min=1, max=500))
    author = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    genre = fields.Str(validate=validate.Length(max=100))
    
def validate_request(schema_class):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            schema = schema_class()
            try:
                validated_data = schema.load(request.json)
                return func(validated_data, *args, **kwargs)
            except ValidationError as e:
                return handle_error("Validation failed", 400, errors=e.messages)
        return wrapper
    return decorator

@books_bp.route('/', methods=['POST'])
@validate_request(BookUploadSchema)
def create_book(validated_data):
    # Use validated_data safely
```

### 2. Authorization Pattern
Check permissions at service level.

```python
class PermissionChecker:
    @staticmethod
    def can_access_book(user_id, book_id):
        book = Book.query.get(book_id)
        return book and book.owner_id == user_id
    
    @staticmethod
    def can_sync_to_kindle(kindle_email):
        return kindle_email.endswith('@kindle.com')

def require_permission(permission_func):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not permission_func(*args, **kwargs):
                return handle_error("Permission denied", 403)
            return func(*args, **kwargs)
        return wrapper
    return decorator

@books_bp.route('/<book_id>/sync', methods=['POST'])
@require_permission(lambda book_id, **kwargs: 
                   PermissionChecker.can_access_book(current_user.id, book_id))
def sync_book(book_id):
    # Authorized access
```

### 3. Rate Limiting Pattern
Protect APIs from abuse.

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["100 per hour"]
)

@books_bp.route('/upload', methods=['POST'])
@limiter.limit("5 per minute")
def upload_book():
    # Rate-limited endpoint
```

## Testing Patterns

### 1. Test Factory Pattern
Create test data with factories.

```python
class BookFactory:
    @staticmethod
    def create(title="Test Book", author="Test Author", **kwargs):
        book_data = {
            'title': title,
            'author': author,
            'format': 'EPUB',
            'file_size': 1024,
            'gcs_path': 'test/path.epub',
            'file_hash': 'testhash',
            **kwargs
        }
        return Book(**book_data)

# Usage in tests
def test_book_search():
    book1 = BookFactory.create(title="Python Guide")
    book2 = BookFactory.create(title="Flask Tutorial")
    
    results = Book.search("Python")
    assert len(results) == 1
    assert results[0].title == "Python Guide"
```

### 2. Mock Pattern for External Services
Mock external dependencies in tests.

```python
import pytest
from unittest.mock import Mock, patch

@patch('services.book_manager.storage.Client')
def test_file_upload(mock_storage):
    # Setup mock
    mock_bucket = Mock()
    mock_blob = Mock()
    mock_storage.return_value.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    
    # Test
    book_manager = BookManager()
    result = book_manager.upload_file(file_content, 'test/path')
    
    # Verify
    assert result is True
    mock_blob.upload_from_string.assert_called_once()
```

### 3. Integration Test Pattern
Test complete workflows end-to-end.

```python
def test_book_upload_workflow(client, db):
    # Upload book
    response = client.post('/api/books/upload', 
                          data={'title': 'Test Book', 'author': 'Author'},
                          content_type='multipart/form-data')
    
    assert response.status_code == 201
    book_id = response.json['book']['id']
    
    # Verify in database
    book = Book.query.get(book_id)
    assert book.title == 'Test Book'
    
    # Test sync
    sync_response = client.post(f'/api/sync/book/{book_id}',
                               json={'kindle_email': 'test@kindle.com'})
    
    assert sync_response.status_code == 200
```

These patterns provide a solid foundation for building maintainable, scalable, and testable Flask applications optimized for Google Cloud deployment.
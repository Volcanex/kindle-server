# Backend Module Rules

## Architecture Principles

### 1. Service-Oriented Design
- Each service handles a specific domain (books, news, sync)
- Services are stateless and can be called independently
- Clear separation between data access (models), business logic (services), and API (routes)

### 2. Cloud-First Implementation
- All file operations go through Google Cloud Storage
- Database uses Cloud SQL PostgreSQL with connection pooling
- Logging integrates with Google Cloud Logging
- Configuration through environment variables

### 3. Error Handling and Resilience
- Comprehensive error handling with structured logging
- Retry mechanisms for failed operations
- Graceful degradation when external services are unavailable
- Transaction rollback on database errors

## File Organization Rules

### 1. Directory Structure
```
backend/
├── app.py              # Flask application factory
├── config/             # Configuration management
├── models/             # Database models (SQLAlchemy)
├── routes/             # API endpoints (Flask blueprints)
├── services/           # Business logic services
├── utils/              # Utility functions and helpers
├── tests/              # Unit and integration tests
├── requirements.txt    # Python dependencies
└── Dockerfile         # Container configuration
```

### 2. Import Rules
- Models only import from database layer
- Services can import models and utilities
- Routes import services, not models directly
- Utilities are standalone and import-independent

### 3. Naming Conventions
- Files: snake_case.py
- Classes: PascalCase
- Functions/variables: snake_case
- Constants: UPPER_SNAKE_CASE
- Database tables: snake_case

## Service Layer Rules

### 1. Service Responsibilities
- **BookManager**: File upload, storage, metadata extraction
- **NewsAggregator**: RSS parsing, content processing, deduplication
- **KindleSyncService**: Email delivery, sync tracking, retry logic

### 2. Service Patterns
- Each service is a class with clear initialization
- Methods return consistent result types (bool for success/failure, objects for data)
- Services handle their own error logging
- Services are transaction-aware (commit/rollback)

### 3. External Dependencies
- Google Cloud Storage for file operations
- SMTP for email delivery
- RSS feeds for news aggregation
- PostgreSQL for data persistence

## Database Rules

### 1. Model Design
- Use UUIDs for primary keys
- Include created_at/updated_at timestamps
- Use JSONB for flexible metadata storage
- Implement proper indexes for query performance

### 2. Migration Strategy
- Use Alembic for database migrations
- All schema changes through migration files
- No direct SQL in application code
- Support for rollback scenarios

### 3. Query Optimization
- Use SQLAlchemy ORM with proper relationship loading
- Implement pagination for large result sets
- Use database functions for aggregations
- Connection pooling for Cloud SQL

## API Design Rules

### 1. RESTful Conventions
- Use HTTP methods semantically (GET, POST, PUT, DELETE)
- Consistent JSON response format
- Proper HTTP status codes
- Resource-based URL structure

### 2. Response Format
```json
{
  "data": {},           // Success response data
  "message": "string",  // Human-readable message
  "error": "string",    // Error message (if applicable)
  "pagination": {}      // Pagination info (for lists)
}
```

### 3. Error Handling
- Structured error responses
- Appropriate HTTP status codes
- No sensitive information in error messages
- Detailed logging for debugging

## Security Rules

### 1. Authentication & Authorization
- Validate Kindle email format (@kindle.com)
- Input validation on all endpoints
- SQL injection prevention through ORM
- XSS prevention through proper escaping

### 2. File Security
- Validate uploaded file types and sizes
- Scan file content for malicious patterns
- Use secure temporary file handling
- Implement file access controls

### 3. Data Protection
- No sensitive data in logs
- Encrypt data in transit and at rest
- Use Cloud IAM for service permissions
- Secure configuration management

## Performance Rules

### 1. Caching Strategy
- Cache RSS feed results
- Cache frequently accessed book metadata
- Use Redis for session storage
- Implement cache invalidation policies

### 2. Async Operations
- Use Celery for background tasks
- Async file uploads to Cloud Storage
- Background news aggregation
- Queue-based sync operations

### 3. Resource Management
- Connection pooling for database
- File cleanup after operations
- Memory-efficient file processing
- Proper resource disposal

## Testing Rules

### 1. Test Coverage
- Unit tests for all service methods
- Integration tests for API endpoints
- Mock external dependencies
- Test error conditions

### 2. Test Organization
```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── fixtures/       # Test data
└── conftest.py     # Test configuration
```

### 3. Test Data
- Use factories for test data creation
- Clean database state between tests
- Mock external API calls
- Use temporary files for file operations

## Deployment Rules

### 1. Cloud Run Configuration
- Single container deployment
- Environment-based configuration
- Health check endpoints
- Proper resource limits

### 2. Environment Management
- Separate dev/staging/production configs
- Secret management through Google Secret Manager
- Database migration on deployment
- Blue-green deployment support

### 3. Monitoring
- Structured logging with request IDs
- Application metrics and alerting
- Error tracking and reporting
- Performance monitoring
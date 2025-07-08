"""
Configuration settings for Kindle Content Server
Optimized for Google Cloud deployment
"""

import os
from datetime import timedelta

class Config:
    """Base configuration with Cloud-first defaults"""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-change-in-production'
    
    # Database configuration - Cloud SQL PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://kindle_user:kindle_pass@localhost/kindle_content_server'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,  # 1 hour
        'pool_timeout': 30,
        'max_overflow': 0,
        'pool_size': 5
    }
    
    # Google Cloud Storage settings
    GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', 'kindle-content-storage')
    GCS_CREDENTIALS_PATH = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    
    # Kindle sync settings
    KINDLE_EMAIL_DOMAIN = '@kindle.com'
    KINDLE_SEND_TO_EMAIL = os.environ.get('KINDLE_SEND_TO_EMAIL')
    KINDLE_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB limit
    
    # RSS News aggregation settings
    RSS_FEEDS = [
        'https://feeds.feedburner.com/oreilly',
        'https://blog.google/rss/',
        'https://aws.amazon.com/blogs/aws/feed/',
        'https://stackoverflow.blog/feed/',
        'https://github.blog/feed/'
    ]
    RSS_UPDATE_INTERVAL = timedelta(hours=6)
    RSS_MAX_ARTICLES_PER_FEED = 10
    
    # Email settings for Kindle delivery
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    EMAIL_USER = os.environ.get('EMAIL_USER')
    EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
    
    # EPUB generation settings
    EPUB_AUTHOR = 'Kindle Content Server'
    EPUB_PUBLISHER = 'Personal Library'
    EPUB_MAX_CHAPTERS = 50
    
    # Caching settings
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CACHE_DEFAULT_TIMEOUT = 3600  # 1 hour
    
    # Security settings
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    
    # Rate limiting
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')
    RATELIMIT_DEFAULT = "100 per hour"
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    @staticmethod
    def init_app(app):
        """Initialize application with configuration"""
        pass

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///kindle_local.db'
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
    }

class ProductionConfig(Config):
    """Production configuration for Cloud Run"""
    DEBUG = False
    
    # Use Cloud SQL connection
    if os.environ.get('CLOUD_SQL_CONNECTION_NAME'):
        SQLALCHEMY_DATABASE_URI = (
            f"postgresql+psycopg2://{os.environ.get('DB_USER')}:"
            f"{os.environ.get('DB_PASS')}@/{os.environ.get('DB_NAME')}"
            f"?host=/cloudsql/{os.environ.get('CLOUD_SQL_CONNECTION_NAME')}"
        )
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Log to Cloud Logging
        import google.cloud.logging
        client = google.cloud.logging.Client()
        client.setup_logging()

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
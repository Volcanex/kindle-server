"""
Test configuration and fixtures
"""

import pytest
import tempfile
import os
from app import create_app
from models import db
from config.settings import TestingConfig

@pytest.fixture
def app():
    """Create application for testing."""
    # Create temporary database
    db_fd, db_path = tempfile.mkstemp()
    
    # Override database URL for testing
    TestingConfig.SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path}'
    
    app = create_app(TestingConfig)
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()
    
    # Clean up
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """Test client for making requests."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Test CLI runner."""
    return app.test_cli_runner()

@pytest.fixture
def sample_book_data():
    """Sample book data for testing."""
    return {
        'title': 'Test Book',
        'author': 'Test Author',
        'description': 'A test book for unit testing',
        'format': 'EPUB',
        'file_size': 1024000,
        'gcs_path': 'test/book.epub',
        'file_hash': 'testhash123',
        'language': 'en',
        'genre': 'Technology'
    }

@pytest.fixture
def sample_news_data():
    """Sample news item data for testing."""
    return {
        'title': 'Test News Article',
        'content': 'This is a test news article content.',
        'summary': 'Test summary',
        'source_name': 'Test Source',
        'source_url': 'https://example.com/article',
        'feed_url': 'https://example.com/feed',
        'author': 'Test Author',
        'category': 'Technology',
        'word_count': 10,
        'quality_score': 0.8
    }
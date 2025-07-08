"""
Book model for storing ebook metadata and content
"""

from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON
from sqlalchemy import func
import uuid

from . import db

class Book(db.Model):
    """Book model for storing ebook information"""
    
    __tablename__ = 'books'
    
    # Primary key
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Book metadata
    title = db.Column(db.String(500), nullable=False, index=True)
    author = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    isbn = db.Column(db.String(20), unique=True, index=True)
    
    # Content information
    format = db.Column(db.String(10), nullable=False, default='EPUB')  # EPUB, PDF, MOBI
    file_size = db.Column(db.BigInteger, nullable=False)
    page_count = db.Column(db.Integer)
    word_count = db.Column(db.Integer)
    
    # Storage information
    gcs_path = db.Column(db.String(500), nullable=False)  # Path in Google Cloud Storage
    file_hash = db.Column(db.String(64), nullable=False)  # SHA-256 hash for integrity
    
    # Metadata
    language = db.Column(db.String(10), default='en')
    publisher = db.Column(db.String(200))
    publication_date = db.Column(db.Date)
    genre = db.Column(db.String(100))
    tags = db.Column(JSON)  # Flexible tagging system
    
    # Reading progress
    reading_progress = db.Column(db.Float, default=0.0)  # 0.0 to 1.0
    last_read_position = db.Column(db.String(100))  # Chapter/page identifier
    
    # Status and sync
    status = db.Column(db.String(20), default='available')  # available, processing, error
    sync_status = db.Column(db.String(20), default='pending')  # pending, synced, failed
    last_synced_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sync_logs = db.relationship('SyncLog', backref='book', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Book {self.title} by {self.author}>'
    
    def to_dict(self):
        """Convert book to dictionary for API responses"""
        return {
            'id': str(self.id),
            'title': self.title,
            'author': self.author,
            'description': self.description,
            'isbn': self.isbn,
            'format': self.format,
            'file_size': self.file_size,
            'page_count': self.page_count,
            'word_count': self.word_count,
            'language': self.language,
            'publisher': self.publisher,
            'publication_date': self.publication_date.isoformat() if self.publication_date else None,
            'genre': self.genre,
            'tags': self.tags,
            'reading_progress': self.reading_progress,
            'last_read_position': self.last_read_position,
            'status': self.status,
            'sync_status': self.sync_status,
            'last_synced_at': self.last_synced_at.isoformat() if self.last_synced_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def update_reading_progress(self, progress, position=None):
        """Update reading progress and position"""
        self.reading_progress = max(0.0, min(1.0, progress))
        if position:
            self.last_read_position = position
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def mark_for_sync(self):
        """Mark book for Kindle sync"""
        self.sync_status = 'pending'
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def mark_synced(self):
        """Mark book as successfully synced"""
        self.sync_status = 'synced'
        self.last_synced_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def mark_sync_failed(self):
        """Mark book sync as failed"""
        self.sync_status = 'failed'
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    @classmethod
    def get_pending_sync(cls):
        """Get books pending sync to Kindle"""
        return cls.query.filter_by(sync_status='pending').all()
    
    @classmethod
    def search(cls, query, limit=50):
        """Search books by title, author, or description"""
        search_term = f'%{query}%'
        return cls.query.filter(
            db.or_(
                cls.title.ilike(search_term),
                cls.author.ilike(search_term),
                cls.description.ilike(search_term)
            )
        ).limit(limit).all()
    
    @classmethod
    def get_by_genre(cls, genre, limit=50):
        """Get books by genre"""
        return cls.query.filter_by(genre=genre).limit(limit).all()
    
    @classmethod
    def get_recent(cls, limit=20):
        """Get recently added books"""
        return cls.query.order_by(cls.created_at.desc()).limit(limit).all()
"""
News item model for RSS aggregated content
"""

from datetime import datetime, timedelta
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON
from sqlalchemy import func, Index
import uuid

from . import db

class NewsItem(db.Model):
    """News item model for RSS aggregated content"""
    
    __tablename__ = 'news_items'
    
    # Primary key
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # News content
    title = db.Column(db.String(500), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text)
    
    # Source information
    source_name = db.Column(db.String(100), nullable=False, index=True)
    source_url = db.Column(db.String(1000), nullable=False)
    feed_url = db.Column(db.String(1000), nullable=False)
    
    # Article metadata
    author = db.Column(db.String(200))
    category = db.Column(db.String(100), index=True)
    tags = db.Column(JSON)  # Flexible tagging system
    
    # Publishing information
    published_at = db.Column(db.DateTime, nullable=False, index=True)
    original_id = db.Column(db.String(200))  # Original RSS item ID
    guid = db.Column(db.String(500), unique=True)  # RSS GUID for deduplication
    
    # Processing status
    status = db.Column(db.String(20), default='pending')  # pending, processed, included, excluded
    epub_included = db.Column(db.Boolean, default=False)
    processing_notes = db.Column(db.Text)
    
    # Content analysis
    word_count = db.Column(db.Integer)
    reading_time = db.Column(db.Integer)  # Estimated reading time in minutes
    quality_score = db.Column(db.Float)  # Content quality score (0.0-1.0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_news_published_source', 'published_at', 'source_name'),
        Index('idx_news_status_created', 'status', 'created_at'),
        Index('idx_news_epub_included', 'epub_included', 'published_at'),
    )
    
    def __repr__(self):
        return f'<NewsItem {self.title} from {self.source_name}>'
    
    def to_dict(self):
        """Convert news item to dictionary for API responses"""
        return {
            'id': str(self.id),
            'title': self.title,
            'content': self.content,
            'summary': self.summary,
            'source_name': self.source_name,
            'source_url': self.source_url,
            'feed_url': self.feed_url,
            'author': self.author,
            'category': self.category,
            'tags': self.tags,
            'published_at': self.published_at.isoformat(),
            'original_id': self.original_id,
            'guid': self.guid,
            'status': self.status,
            'epub_included': self.epub_included,
            'processing_notes': self.processing_notes,
            'word_count': self.word_count,
            'reading_time': self.reading_time,
            'quality_score': self.quality_score,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def calculate_reading_time(self):
        """Calculate estimated reading time based on word count"""
        if self.word_count:
            # Average reading speed: 200 words per minute
            self.reading_time = max(1, self.word_count // 200)
        else:
            self.reading_time = 1
    
    def calculate_quality_score(self):
        """Calculate content quality score based on various factors"""
        score = 0.5  # Base score
        
        # Title quality
        if self.title and len(self.title.strip()) > 10:
            score += 0.1
        
        # Content length
        if self.word_count:
            if 100 <= self.word_count <= 2000:  # Optimal range
                score += 0.2
            elif self.word_count > 2000:
                score += 0.1
        
        # Has summary
        if self.summary and len(self.summary.strip()) > 20:
            score += 0.1
        
        # Has author
        if self.author and len(self.author.strip()) > 0:
            score += 0.1
        
        self.quality_score = min(1.0, score)
    
    def process_content(self):
        """Process the news item content"""
        if not self.word_count and self.content:
            self.word_count = len(self.content.split())
        
        self.calculate_reading_time()
        self.calculate_quality_score()
        self.status = 'processed'
        self.updated_at = datetime.utcnow()
    
    def include_in_epub(self):
        """Mark item for inclusion in EPUB"""
        self.epub_included = True
        self.status = 'included'
        self.updated_at = datetime.utcnow()
    
    def exclude_from_epub(self, reason=None):
        """Mark item for exclusion from EPUB"""
        self.epub_included = False
        self.status = 'excluded'
        if reason:
            self.processing_notes = reason
        self.updated_at = datetime.utcnow()
    
    @classmethod
    def get_for_epub(cls, limit=50, min_quality=0.5):
        """Get news items for EPUB generation"""
        return cls.query.filter(
            cls.epub_included == True,
            cls.quality_score >= min_quality
        ).order_by(cls.published_at.desc()).limit(limit).all()
    
    @classmethod
    def get_by_source(cls, source_name, limit=20):
        """Get news items by source"""
        return cls.query.filter_by(source_name=source_name)\
            .order_by(cls.published_at.desc()).limit(limit).all()
    
    @classmethod
    def get_recent(cls, hours=24, limit=100):
        """Get recent news items"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return cls.query.filter(cls.published_at >= cutoff)\
            .order_by(cls.published_at.desc()).limit(limit).all()
    
    @classmethod
    def get_pending_processing(cls):
        """Get items pending processing"""
        return cls.query.filter_by(status='pending').all()
    
    @classmethod
    def exists_by_guid(cls, guid):
        """Check if item exists by GUID to prevent duplicates"""
        return cls.query.filter_by(guid=guid).first() is not None
    
    @classmethod
    def search(cls, query, limit=50):
        """Search news items by title or content"""
        search_term = f'%{query}%'
        return cls.query.filter(
            db.or_(
                cls.title.ilike(search_term),
                cls.content.ilike(search_term),
                cls.summary.ilike(search_term)
            )
        ).order_by(cls.published_at.desc()).limit(limit).all()
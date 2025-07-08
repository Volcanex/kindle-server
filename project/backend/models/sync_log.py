"""
Sync log model for tracking Kindle sync operations
"""

from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON
from sqlalchemy import func
import uuid

from . import db

class SyncLog(db.Model):
    """Sync log model for tracking Kindle sync operations"""
    
    __tablename__ = 'sync_logs'
    
    # Primary key
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Sync operation details
    operation_type = db.Column(db.String(50), nullable=False, index=True)  # book_sync, news_digest, etc.
    status = db.Column(db.String(20), nullable=False, index=True)  # pending, success, failed, retrying
    
    # Related entities
    book_id = db.Column(UUID(as_uuid=True), db.ForeignKey('books.id'), nullable=True, index=True)
    news_digest_id = db.Column(db.String(100), nullable=True)  # For news digest operations
    
    # Sync details
    kindle_email = db.Column(db.String(200), nullable=False)
    file_name = db.Column(db.String(300))
    file_size = db.Column(db.BigInteger)
    
    # Operation metadata
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Integer)
    
    # Error handling
    error_message = db.Column(db.Text)
    error_code = db.Column(db.String(50))
    retry_count = db.Column(db.Integer, default=0)
    max_retries = db.Column(db.Integer, default=3)
    
    # Additional metadata
    sync_metadata = db.Column(JSON)  # Flexible metadata storage
    user_agent = db.Column(db.String(500))
    ip_address = db.Column(db.String(45))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SyncLog {self.operation_type} - {self.status}>'
    
    def to_dict(self):
        """Convert sync log to dictionary for API responses"""
        return {
            'id': str(self.id),
            'operation_type': self.operation_type,
            'status': self.status,
            'book_id': str(self.book_id) if self.book_id else None,
            'news_digest_id': self.news_digest_id,
            'kindle_email': self.kindle_email,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_seconds': self.duration_seconds,
            'error_message': self.error_message,
            'error_code': self.error_code,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'metadata': self.sync_metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def start_operation(self):
        """Mark operation as started"""
        self.status = 'pending'
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def complete_success(self, metadata=None):
        """Mark operation as successfully completed"""
        self.status = 'success'
        self.completed_at = datetime.utcnow()
        self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())
        if metadata:
            self.sync_metadata = {**(self.sync_metadata or {}), **metadata}
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def complete_failure(self, error_message, error_code=None, metadata=None):
        """Mark operation as failed"""
        self.status = 'failed'
        self.completed_at = datetime.utcnow()
        self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())
        self.error_message = error_message
        self.error_code = error_code
        if metadata:
            self.sync_metadata = {**(self.sync_metadata or {}), **metadata}
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def retry_operation(self):
        """Increment retry count and mark for retry"""
        self.retry_count += 1
        if self.retry_count <= self.max_retries:
            self.status = 'retrying'
        else:
            self.status = 'failed'
            self.error_message = f"Max retries ({self.max_retries}) exceeded"
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return self.retry_count <= self.max_retries
    
    def can_retry(self):
        """Check if operation can be retried"""
        return self.retry_count < self.max_retries and self.status in ['failed', 'retrying']
    
    @classmethod
    def create_sync_log(cls, operation_type, kindle_email, book_id=None, 
                       news_digest_id=None, file_name=None, file_size=None, 
                       max_retries=3, metadata=None, user_agent=None, ip_address=None):
        """Create a new sync log entry"""
        sync_log = cls(
            operation_type=operation_type,
            status='pending',
            kindle_email=kindle_email,
            book_id=book_id,
            news_digest_id=news_digest_id,
            file_name=file_name,
            file_size=file_size,
            max_retries=max_retries,
            sync_metadata=metadata,
            user_agent=user_agent,
            ip_address=ip_address
        )
        db.session.add(sync_log)
        db.session.commit()
        return sync_log
    
    @classmethod
    def get_pending_retries(cls):
        """Get sync logs that can be retried"""
        return cls.query.filter(
            cls.status.in_(['failed', 'retrying']),
            cls.retry_count < cls.max_retries
        ).all()
    
    @classmethod
    def get_recent_by_email(cls, kindle_email, limit=20):
        """Get recent sync logs for a Kindle email"""
        return cls.query.filter_by(kindle_email=kindle_email)\
            .order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_stats(cls, days=30):
        """Get sync statistics for the last N days"""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        stats = db.session.query(
            cls.status,
            func.count(cls.id).label('count')
        ).filter(cls.created_at >= cutoff)\
         .group_by(cls.status).all()
        
        return {status: count for status, count in stats}
    
    @classmethod
    def cleanup_old_logs(cls, days=90):
        """Clean up old sync logs"""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        deleted_count = cls.query.filter(cls.created_at < cutoff).delete()
        db.session.commit()
        return deleted_count
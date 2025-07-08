"""
Database models for Kindle Content Server
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# Import all models to ensure they're registered
from .book import Book
from .news_item import NewsItem  
from .sync_log import SyncLog

__all__ = ['db', 'Book', 'NewsItem', 'SyncLog']
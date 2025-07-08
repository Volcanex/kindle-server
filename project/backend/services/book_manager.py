"""
Book Manager Service
Handles book file operations, Cloud Storage integration, and metadata management
"""

import os
import hashlib
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
import mimetypes

# Google Cloud Storage
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError

# Book processing libraries
import ebooklib
from ebooklib import epub
import PyPDF2
from PIL import Image
import zipfile

from models import db, Book
from config.settings import Config
from utils.file_handler import FileHandler

logger = logging.getLogger(__name__)

class BookManager:
    """Service for managing book files and metadata"""
    
    def __init__(self):
        self.storage_client = storage.Client()
        self.bucket_name = Config.GCS_BUCKET_NAME
        self.bucket = self.storage_client.bucket(self.bucket_name)
        self.file_handler = FileHandler()
        
        # Supported file formats
        self.supported_formats = {
            '.epub': 'EPUB',
            '.pdf': 'PDF',
            '.mobi': 'MOBI',
            '.azw': 'AZW',
            '.azw3': 'AZW3',
            '.txt': 'TXT'
        }
        
        # MIME types for validation
        self.supported_mime_types = {
            'application/epub+zip': 'EPUB',
            'application/pdf': 'PDF',
            'application/x-mobipocket-ebook': 'MOBI',
            'text/plain': 'TXT'
        }
    
    def upload_book(self, file: FileStorage, title: str, author: str, 
                   description: str = None, genre: str = None) -> Optional[Book]:
        """
        Upload a new book file to Google Cloud Storage and create database entry
        
        Args:
            file: Uploaded file object
            title: Book title
            author: Book author
            description: Book description
            genre: Book genre
            
        Returns:
            Book object if successful, None otherwise
        """
        try:
            # Validate file
            if not self._validate_file(file):
                logger.error(f"Invalid file format: {file.filename}")
                return None
            
            # Generate secure filename
            original_filename = secure_filename(file.filename)
            file_extension = os.path.splitext(original_filename)[1].lower()
            book_format = self.supported_formats.get(file_extension, 'UNKNOWN')
            
            # Generate unique filename
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{original_filename}"
            
            # Calculate file hash
            file.seek(0)
            file_content = file.read()
            file_hash = hashlib.sha256(file_content).hexdigest()
            file_size = len(file_content)
            
            # Check if file already exists by hash
            existing_book = Book.query.filter_by(file_hash=file_hash).first()
            if existing_book:
                logger.warning(f"Book with same hash already exists: {existing_book.title}")
                return existing_book
            
            # Upload to Google Cloud Storage
            gcs_path = f"books/{unique_filename}"
            blob = self.bucket.blob(gcs_path)
            
            file.seek(0)
            blob.upload_from_file(file, content_type=file.content_type)
            
            logger.info(f"Uploaded book to GCS: {gcs_path}")
            
            # Extract metadata from file
            metadata = self._extract_metadata(file_content, book_format)
            
            # Create book entry
            book = Book(
                title=title,
                author=author,
                description=description or metadata.get('description'),
                isbn=metadata.get('isbn'),
                format=book_format,
                file_size=file_size,
                gcs_path=gcs_path,
                file_hash=file_hash,
                page_count=metadata.get('page_count'),
                word_count=metadata.get('word_count'),
                language=metadata.get('language', 'en'),
                publisher=metadata.get('publisher'),
                publication_date=metadata.get('publication_date'),
                genre=genre or metadata.get('genre'),
                tags=metadata.get('tags'),
                status='available'
            )
            
            db.session.add(book)
            db.session.commit()
            
            logger.info(f"Created book entry: {book.title} by {book.author}")
            return book
            
        except Exception as e:
            logger.error(f"Error uploading book: {e}")
            db.session.rollback()
            return None
    
    def delete_book(self, book: Book) -> bool:
        """
        Delete a book and its associated file from Google Cloud Storage
        
        Args:
            book: Book object to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete file from Google Cloud Storage
            if book.gcs_path:
                blob = self.bucket.blob(book.gcs_path)
                if blob.exists():
                    blob.delete()
                    logger.info(f"Deleted book file from GCS: {book.gcs_path}")
            
            # Delete book from database
            db.session.delete(book)
            db.session.commit()
            
            logger.info(f"Deleted book: {book.title}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting book {book.id}: {e}")
            db.session.rollback()
            return False
    
    def get_download_url(self, book: Book, expiration_hours: int = 1) -> Optional[str]:
        """
        Generate a signed URL for downloading a book
        
        Args:
            book: Book object
            expiration_hours: URL expiration time in hours
            
        Returns:
            Signed URL string if successful, None otherwise
        """
        try:
            if not book.gcs_path:
                logger.error(f"No GCS path for book {book.id}")
                return None
            
            blob = self.bucket.blob(book.gcs_path)
            
            # Check if file exists
            if not blob.exists():
                logger.error(f"Book file not found in GCS: {book.gcs_path}")
                return None
            
            # Generate signed URL
            expiration = datetime.utcnow() + timedelta(hours=expiration_hours)
            url = blob.generate_signed_url(
                expiration=expiration,
                method='GET',
                response_disposition=f'attachment; filename="{book.title}.{book.format.lower()}"'
            )
            
            logger.info(f"Generated download URL for book {book.id}")
            return url
            
        except Exception as e:
            logger.error(f"Error generating download URL for book {book.id}: {e}")
            return None
    
    def update_book_metadata(self, book: Book, metadata: Dict) -> bool:
        """
        Update book metadata
        
        Args:
            book: Book object to update
            metadata: Dictionary of metadata to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update allowed fields
            allowed_fields = [
                'title', 'author', 'description', 'isbn', 'genre', 'tags',
                'language', 'publisher', 'publication_date', 'page_count',
                'word_count'
            ]
            
            for field, value in metadata.items():
                if field in allowed_fields and hasattr(book, field):
                    setattr(book, field, value)
            
            book.updated_at = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"Updated metadata for book {book.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating book metadata {book.id}: {e}")
            db.session.rollback()
            return False
    
    def get_book_content(self, book: Book) -> Optional[bytes]:
        """
        Download book content from Google Cloud Storage
        
        Args:
            book: Book object
            
        Returns:
            Book file content as bytes if successful, None otherwise
        """
        try:
            if not book.gcs_path:
                logger.error(f"No GCS path for book {book.id}")
                return None
            
            blob = self.bucket.blob(book.gcs_path)
            
            if not blob.exists():
                logger.error(f"Book file not found in GCS: {book.gcs_path}")
                return None
            
            content = blob.download_as_bytes()
            logger.info(f"Downloaded book content for {book.id}")
            return content
            
        except Exception as e:
            logger.error(f"Error downloading book content {book.id}: {e}")
            return None
    
    def _validate_file(self, file: FileStorage) -> bool:
        """
        Validate uploaded file format and size
        
        Args:
            file: Uploaded file object
            
        Returns:
            True if valid, False otherwise
        """
        # Check file extension
        if not file.filename:
            return False
        
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in self.supported_formats:
            return False
        
        # Check MIME type
        mime_type, _ = mimetypes.guess_type(file.filename)
        if mime_type and mime_type not in self.supported_mime_types:
            return False
        
        # Check file size (max 50MB)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > Config.KINDLE_MAX_FILE_SIZE:
            return False
        
        return True
    
    def _extract_metadata(self, file_content: bytes, book_format: str) -> Dict:
        """
        Extract metadata from book file
        
        Args:
            file_content: Book file content as bytes
            book_format: Book format (EPUB, PDF, etc.)
            
        Returns:
            Dictionary of extracted metadata
        """
        metadata = {}
        
        try:
            if book_format == 'EPUB':
                metadata = self._extract_epub_metadata(file_content)
            elif book_format == 'PDF':
                metadata = self._extract_pdf_metadata(file_content)
            elif book_format == 'TXT':
                metadata = self._extract_txt_metadata(file_content)
            
        except Exception as e:
            logger.error(f"Error extracting metadata for {book_format}: {e}")
        
        return metadata
    
    def _extract_epub_metadata(self, file_content: bytes) -> Dict:
        """Extract metadata from EPUB file"""
        metadata = {}
        
        try:
            # Save to temp file for processing
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as temp_file:
                temp_file.write(file_content)
                temp_file.flush()
                
                # Read EPUB
                book = epub.read_epub(temp_file.name)
                
                # Extract metadata
                metadata['title'] = book.get_metadata('DC', 'title')
                metadata['author'] = book.get_metadata('DC', 'creator')
                metadata['description'] = book.get_metadata('DC', 'description')
                metadata['publisher'] = book.get_metadata('DC', 'publisher')
                metadata['language'] = book.get_metadata('DC', 'language')
                metadata['isbn'] = book.get_metadata('DC', 'identifier')
                
                # Clean up metadata
                for key, value in metadata.items():
                    if isinstance(value, list) and value:
                        metadata[key] = value[0][0] if isinstance(value[0], tuple) else value[0]
                    elif isinstance(value, tuple):
                        metadata[key] = value[0]
                
                # Count words (approximate)
                word_count = 0
                for item in book.get_items():
                    if item.get_type() == ebooklib.ITEM_DOCUMENT:
                        content = item.get_content().decode('utf-8', errors='ignore')
                        # Remove HTML tags roughly
                        import re
                        text = re.sub(r'<[^>]+>', ' ', content)
                        word_count += len(text.split())
                
                metadata['word_count'] = word_count
                
                # Clean up temp file
                os.unlink(temp_file.name)
                
        except Exception as e:
            logger.error(f"Error extracting EPUB metadata: {e}")
        
        return metadata
    
    def _extract_pdf_metadata(self, file_content: bytes) -> Dict:
        """Extract metadata from PDF file"""
        metadata = {}
        
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(file_content)
                temp_file.flush()
                
                with open(temp_file.name, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    
                    # Extract basic info
                    if pdf_reader.metadata:
                        metadata['title'] = pdf_reader.metadata.get('/Title', '')
                        metadata['author'] = pdf_reader.metadata.get('/Author', '')
                        metadata['creator'] = pdf_reader.metadata.get('/Creator', '')
                        metadata['producer'] = pdf_reader.metadata.get('/Producer', '')
                    
                    # Page count
                    metadata['page_count'] = len(pdf_reader.pages)
                    
                    # Estimate word count
                    word_count = 0
                    for page in pdf_reader.pages[:10]:  # Sample first 10 pages
                        try:
                            text = page.extract_text()
                            word_count += len(text.split())
                        except:
                            continue
                    
                    # Extrapolate word count
                    if word_count > 0 and metadata['page_count'] > 0:
                        metadata['word_count'] = int(word_count * metadata['page_count'] / min(10, metadata['page_count']))
                
                os.unlink(temp_file.name)
                
        except Exception as e:
            logger.error(f"Error extracting PDF metadata: {e}")
        
        return metadata
    
    def _extract_txt_metadata(self, file_content: bytes) -> Dict:
        """Extract metadata from TXT file"""
        metadata = {}
        
        try:
            text = file_content.decode('utf-8', errors='ignore')
            
            # Word count
            metadata['word_count'] = len(text.split())
            
            # Estimate page count (250 words per page)
            metadata['page_count'] = max(1, metadata['word_count'] // 250)
            
        except Exception as e:
            logger.error(f"Error extracting TXT metadata: {e}")
        
        return metadata
    
    def get_storage_stats(self) -> Dict:
        """
        Get storage statistics
        
        Returns:
            Dictionary with storage statistics
        """
        try:
            total_size = db.session.query(db.func.sum(Book.file_size)).scalar() or 0
            total_books = Book.query.count()
            
            # Get format distribution
            format_stats = dict(
                db.session.query(Book.format, db.func.count(Book.id))
                .group_by(Book.format).all()
            )
            
            return {
                'total_books': total_books,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'average_size_mb': round(total_size / (1024 * 1024) / max(1, total_books), 2),
                'format_distribution': format_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {}
    
    def cleanup_orphaned_files(self) -> int:
        """
        Clean up orphaned files in Google Cloud Storage
        
        Returns:
            Number of files cleaned up
        """
        try:
            # Get all GCS paths from database
            db_paths = set()
            books = Book.query.with_entities(Book.gcs_path).all()
            for book in books:
                if book.gcs_path:
                    db_paths.add(book.gcs_path)
            
            # List all files in books/ directory
            gcs_files = set()
            blobs = self.bucket.list_blobs(prefix='books/')
            for blob in blobs:
                gcs_files.add(blob.name)
            
            # Find orphaned files
            orphaned_files = gcs_files - db_paths
            
            # Delete orphaned files
            deleted_count = 0
            for file_path in orphaned_files:
                try:
                    blob = self.bucket.blob(file_path)
                    blob.delete()
                    deleted_count += 1
                    logger.info(f"Deleted orphaned file: {file_path}")
                except Exception as e:
                    logger.error(f"Error deleting orphaned file {file_path}: {e}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up orphaned files: {e}")
            return 0
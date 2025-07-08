"""
Kindle Sync Service
Handles synchronization of books and news digests to Kindle devices via email
"""

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from typing import Optional, List, Dict
from datetime import datetime
import tempfile
import os

from models import db, Book, NewsItem, SyncLog
from services.book_manager import BookManager
from utils.epub_creator import EpubCreator
from config.settings import Config

logger = logging.getLogger(__name__)

class KindleSyncService:
    """Service for syncing content to Kindle devices"""
    
    def __init__(self):
        self.smtp_server = Config.SMTP_SERVER
        self.smtp_port = Config.SMTP_PORT
        self.email_user = Config.EMAIL_USER
        self.email_password = Config.EMAIL_PASSWORD
        self.book_manager = BookManager()
        self.epub_creator = EpubCreator()
    
    def sync_book_to_kindle(self, book: Book, kindle_email: str, sync_log: SyncLog) -> bool:
        """
        Sync a book to Kindle device via email
        
        Args:
            book: Book object to sync
            kindle_email: Target Kindle email address
            sync_log: Sync log object for tracking
            
        Returns:
            True if successful, False otherwise
        """
        try:
            sync_log.start_operation()
            
            # Validate Kindle email
            if not kindle_email.endswith('@kindle.com'):
                sync_log.complete_failure("Invalid Kindle email address")
                return False
            
            # Get book content
            book_content = self.book_manager.get_book_content(book)
            if not book_content:
                sync_log.complete_failure("Failed to retrieve book content")
                return False
            
            # Prepare email
            subject = f"[Kindle Content Server] {book.title}"
            body = f"""
Your book "{book.title}" by {book.author} is ready for your Kindle.

Book Details:
- Format: {book.format}
- Size: {self._format_file_size(book.file_size)}
- Pages: {book.page_count or 'Unknown'}
- Language: {book.language or 'Unknown'}

{book.description if book.description else ''}

Sent from Kindle Content Server
            """.strip()
            
            # Create filename
            filename = f"{book.title[:50]}.{book.format.lower()}"
            filename = self._sanitize_filename(filename)
            
            # Send email
            success = self._send_email_with_attachment(
                to_email=kindle_email,
                subject=subject,
                body=body,
                attachment_data=book_content,
                attachment_name=filename,
                attachment_type=self._get_content_type(book.format)
            )
            
            if success:
                sync_log.complete_success({
                    'file_name': filename,
                    'kindle_email': kindle_email,
                    'book_title': book.title
                })
                return True
            else:
                sync_log.complete_failure("Failed to send email")
                return False
                
        except Exception as e:
            logger.error(f"Error syncing book {book.id} to {kindle_email}: {e}")
            sync_log.complete_failure(str(e))
            return False
    
    def sync_news_digest_to_kindle(self, kindle_email: str, digest_title: str, 
                                 max_articles: int, min_quality: float, 
                                 sync_log: SyncLog) -> bool:
        """
        Create and sync news digest to Kindle device
        
        Args:
            kindle_email: Target Kindle email address
            digest_title: Title for the news digest
            max_articles: Maximum number of articles to include
            min_quality: Minimum quality score for articles
            sync_log: Sync log object for tracking
            
        Returns:
            True if successful, False otherwise
        """
        try:
            sync_log.start_operation()
            
            # Validate Kindle email
            if not kindle_email.endswith('@kindle.com'):
                sync_log.complete_failure("Invalid Kindle email address")
                return False
            
            # Get news articles for digest
            articles = NewsItem.get_for_epub(limit=max_articles, min_quality=min_quality)
            
            if not articles:
                sync_log.complete_failure("No articles found for digest")
                return False
            
            # Create EPUB digest
            epub_path = self.epub_creator.create_news_digest(digest_title, articles)
            
            if not epub_path or not os.path.exists(epub_path):
                sync_log.complete_failure("Failed to create news digest EPUB")
                return False
            
            try:
                # Read EPUB content
                with open(epub_path, 'rb') as epub_file:
                    epub_content = epub_file.read()
                
                # Prepare email
                subject = f"[Kindle Content Server] {digest_title}"
                body = f"""
Your news digest "{digest_title}" is ready for your Kindle.

Digest Details:
- Articles: {len(articles)}
- Created: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}
- Sources: {', '.join(set(article.source_name for article in articles[:5]))}
{'...' if len(set(article.source_name for article in articles)) > 5 else ''}

Articles included:
"""
                
                # Add article list to body
                for i, article in enumerate(articles[:10], 1):
                    body += f"\n{i}. {article.title} ({article.source_name})"
                
                if len(articles) > 10:
                    body += f"\n... and {len(articles) - 10} more articles"
                
                body += "\n\nSent from Kindle Content Server"
                
                # Create filename
                filename = f"{digest_title[:50]}.epub"
                filename = self._sanitize_filename(filename)
                
                # Update sync log file info
                sync_log.file_name = filename
                sync_log.file_size = len(epub_content)
                
                # Send email
                success = self._send_email_with_attachment(
                    to_email=kindle_email,
                    subject=subject,
                    body=body,
                    attachment_data=epub_content,
                    attachment_name=filename,
                    attachment_type='application/epub+zip'
                )
                
                if success:
                    sync_log.complete_success({
                        'file_name': filename,
                        'kindle_email': kindle_email,
                        'digest_title': digest_title,
                        'article_count': len(articles),
                        'sources': list(set(article.source_name for article in articles))
                    })
                    return True
                else:
                    sync_log.complete_failure("Failed to send email")
                    return False
                    
            finally:
                # Clean up temporary EPUB file
                if os.path.exists(epub_path):
                    os.unlink(epub_path)
                
        except Exception as e:
            logger.error(f"Error syncing news digest to {kindle_email}: {e}")
            sync_log.complete_failure(str(e))
            return False
    
    def sync_multiple_books(self, books: List[Book], kindle_email: str) -> List[Dict]:
        """
        Sync multiple books to Kindle device
        
        Args:
            books: List of Book objects to sync
            kindle_email: Target Kindle email address
            
        Returns:
            List of sync results
        """
        results = []
        
        for book in books:
            # Create sync log for each book
            sync_log = SyncLog.create_sync_log(
                operation_type='batch_book_sync',
                kindle_email=kindle_email,
                book_id=book.id,
                file_name=f"{book.title}.{book.format.lower()}",
                file_size=book.file_size
            )
            
            success = self.sync_book_to_kindle(book, kindle_email, sync_log)
            
            results.append({
                'book_id': str(book.id),
                'book_title': book.title,
                'sync_log_id': str(sync_log.id),
                'success': success
            })
            
            if success:
                book.mark_synced()
        
        return results
    
    def _send_email_with_attachment(self, to_email: str, subject: str, body: str,
                                  attachment_data: bytes, attachment_name: str,
                                  attachment_type: str) -> bool:
        """
        Send email with attachment using SMTP
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body
            attachment_data: Attachment content as bytes
            attachment_name: Attachment filename
            attachment_type: MIME type of attachment
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if email configuration is available
            if not self.email_user or not self.email_password:
                logger.error("Email credentials not configured")
                return False
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_user
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MIMEText(body, 'plain'))
            
            # Add attachment
            attachment = MIMEBase('application', 'octet-stream')
            attachment.set_payload(attachment_data)
            encoders.encode_base64(attachment)
            attachment.add_header(
                'Content-Disposition',
                f'attachment; filename= {attachment_name}'
            )
            msg.attach(attachment)
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_user, self.email_password)
            
            text = msg.as_string()
            server.sendmail(self.email_user, to_email, text)
            server.quit()
            
            logger.info(f"Successfully sent email to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {e}")
            return False
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for email attachment
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Remove leading/trailing spaces and dots
        filename = filename.strip(' .')
        
        # Ensure filename is not empty
        if not filename:
            filename = 'attachment'
        
        return filename
    
    def _format_file_size(self, size_bytes: int) -> str:
        """
        Format file size in human readable format
        
        Args:
            size_bytes: File size in bytes
            
        Returns:
            Formatted file size string
        """
        if size_bytes < 1024:
            return f"{size_bytes} bytes"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    def _get_content_type(self, book_format: str) -> str:
        """
        Get MIME content type for book format
        
        Args:
            book_format: Book format (EPUB, PDF, etc.)
            
        Returns:
            MIME content type
        """
        content_types = {
            'EPUB': 'application/epub+zip',
            'PDF': 'application/pdf',
            'MOBI': 'application/x-mobipocket-ebook',
            'AZW': 'application/vnd.amazon.ebook',
            'AZW3': 'application/vnd.amazon.ebook',
            'TXT': 'text/plain'
        }
        
        return content_types.get(book_format, 'application/octet-stream')
    
    def test_email_connection(self) -> bool:
        """
        Test email server connection
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            if not self.email_user or not self.email_password:
                return False
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_user, self.email_password)
            server.quit()
            
            logger.info("Email connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"Email connection test failed: {e}")
            return False
    
    def get_sync_statistics(self, days: int = 30) -> Dict:
        """
        Get sync statistics for the last N days
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with sync statistics
        """
        try:
            stats = SyncLog.get_stats(days=days)
            
            # Get additional statistics
            total_syncs = sum(stats.values())
            success_rate = (stats.get('success', 0) / max(1, total_syncs)) * 100
            
            return {
                'period_days': days,
                'total_syncs': total_syncs,
                'success_rate': round(success_rate, 2),
                'status_breakdown': stats,
                'pending_retries': len(SyncLog.get_pending_retries())
            }
            
        except Exception as e:
            logger.error(f"Error getting sync statistics: {e}")
            return {}
    
    def retry_failed_syncs(self, max_retries: int = 5) -> Dict:
        """
        Retry failed sync operations
        
        Args:
            max_retries: Maximum number of syncs to retry
            
        Returns:
            Dictionary with retry results
        """
        try:
            pending_retries = SyncLog.get_pending_retries()[:max_retries]
            
            results = {
                'attempted': 0,
                'successful': 0,
                'failed': 0,
                'details': []
            }
            
            for sync_log in pending_retries:
                results['attempted'] += 1
                
                try:
                    # Retry based on operation type
                    if sync_log.operation_type in ['book_sync', 'batch_book_sync']:
                        if sync_log.book_id:
                            book = Book.query.get(sync_log.book_id)
                            if book:
                                success = self.sync_book_to_kindle(book, sync_log.kindle_email, sync_log)
                            else:
                                sync_log.complete_failure("Book not found")
                                success = False
                        else:
                            sync_log.complete_failure("No book ID in sync log")
                            success = False
                            
                    elif sync_log.operation_type == 'news_digest':
                        metadata = sync_log.metadata or {}
                        success = self.sync_news_digest_to_kindle(
                            sync_log.kindle_email,
                            metadata.get('digest_title', 'News Digest'),
                            metadata.get('max_articles', 20),
                            metadata.get('min_quality', 0.5),
                            sync_log
                        )
                    else:
                        sync_log.complete_failure(f"Unknown operation type: {sync_log.operation_type}")
                        success = False
                    
                    if success:
                        results['successful'] += 1
                    else:
                        results['failed'] += 1
                    
                    results['details'].append({
                        'sync_log_id': str(sync_log.id),
                        'operation_type': sync_log.operation_type,
                        'success': success
                    })
                    
                except Exception as e:
                    logger.error(f"Error retrying sync {sync_log.id}: {e}")
                    results['failed'] += 1
                    results['details'].append({
                        'sync_log_id': str(sync_log.id),
                        'operation_type': sync_log.operation_type,
                        'success': False,
                        'error': str(e)
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error retrying failed syncs: {e}")
            return {'error': str(e)}
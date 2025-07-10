"""
KUAL API endpoints
Provides API endpoints expected by the Kindle KUAL client for downloading content
"""

from flask import Blueprint, request, jsonify, send_file, current_app
from datetime import datetime, timedelta
import logging
import json
import os
import tempfile

from models import db, NewsItem, Book
from services.kindle_sync import KindleSyncService
from utils.epub_creator import EpubCreator

kual_api_bp = Blueprint('kual_api', __name__, url_prefix='/api/v1')
logger = logging.getLogger(__name__)


def verify_device_auth():
    """Verify device authentication using headers"""
    device_id = request.headers.get('X-Device-ID')
    api_key = request.headers.get('X-API-Key')
    
    if not device_id or not api_key:
        return None, "Missing device ID or API key"
    
    # For now, accept any device with valid API key format
    # In production, you'd validate against a database of registered devices
    if len(api_key) < 8:
        return None, "Invalid API key format"
    
    return device_id, None


@kual_api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for KUAL client"""
    return jsonify({
        'status': 'healthy',
        'service': 'kindle-content-server',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@kual_api_bp.route('/auth/device', methods=['POST'])
def authenticate_device():
    """Authenticate Kindle device"""
    try:
        device_id, error = verify_device_auth()
        if error:
            return jsonify({
                'status': 'error',
                'message': error
            }), 401
        
        data = request.get_json() or {}
        device_type = data.get('device_type', 'kindle')
        
        # Log device authentication
        logger.info(f"Device authentication request: {device_id} ({device_type})")
        
        # In production, you'd register/update device in database
        # For now, just return success for valid format
        return jsonify({
            'status': 'success',
            'message': 'Device authenticated successfully',
            'device_id': device_id,
            'device_type': device_type,
            'server_time': datetime.utcnow().isoformat(),
            'session_expires': (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error authenticating device: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Authentication failed'
        }), 500


@kual_api_bp.route('/content/list', methods=['GET'])
def get_content_list():
    """Get list of content available for download"""
    try:
        device_id, error = verify_device_auth()
        if error:
            return jsonify({'error': error}), 401
        
        logger.info(f"Content list requested by device: {device_id}")
        
        content_items = []
        
        # Get available books
        books = Book.query.filter_by(status='available').limit(50).all()
        for book in books:
            content_items.append({
                'id': str(book.id),
                'type': 'book',
                'title': book.title,
                'author': book.author,
                'filename': f"{book.title}.{book.format.lower()}",
                'format': book.format.lower(),
                'file_size': book.file_size,
                'upload_date': book.upload_date.isoformat() if book.upload_date else None,
                'description': f"Book by {book.author}",
                'ready_for_sync': True
            })
        
        # Get recent articles ready for sync (create EPUBs)
        cutoff_time = datetime.utcnow() - timedelta(hours=48)
        articles = NewsItem.query.filter(
            NewsItem.epub_included == True,
            NewsItem.published_at >= cutoff_time,
            NewsItem.quality_score >= 0.3
        ).order_by(NewsItem.source_name, NewsItem.published_at.desc()).all()
        
        # Group articles by source for EPUB creation
        articles_by_source = {}
        for article in articles:
            source = article.source_name
            if source not in articles_by_source:
                articles_by_source[source] = []
            articles_by_source[source].append(article)
        
        # Create EPUB entries for each source
        for source_name, source_articles in articles_by_source.items():
            if len(source_articles) > 0:
                # Calculate total size estimate
                total_words = sum(article.word_count or 0 for article in source_articles)
                estimated_size = max(50000, total_words * 10)  # Rough estimate
                
                content_items.append({
                    'id': f"news_{source_name.lower().replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d')}",
                    'type': 'news_digest',
                    'title': f"{source_name} - {datetime.utcnow().strftime('%Y-%m-%d')}",
                    'author': source_name,
                    'filename': f"{source_name.replace(' ', '_')}_digest_{datetime.utcnow().strftime('%Y%m%d')}.epub",
                    'format': 'epub',
                    'file_size': estimated_size,
                    'upload_date': datetime.utcnow().isoformat(),
                    'description': f"News digest from {source_name} ({len(source_articles)} articles)",
                    'article_count': len(source_articles),
                    'source_name': source_name,
                    'ready_for_sync': True
                })
        
        return jsonify({
            'content': content_items,
            'total_items': len(content_items),
            'last_updated': datetime.utcnow().isoformat(),
            'device_id': device_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting content list: {e}")
        return jsonify({'error': 'Failed to get content list'}), 500


@kual_api_bp.route('/content/download/<content_id>', methods=['GET'])
def download_content(content_id):
    """Download specific content file"""
    try:
        device_id, error = verify_device_auth()
        if error:
            return jsonify({'error': error}), 401
        
        logger.info(f"Content download requested: {content_id} by device: {device_id}")
        
        # Check if it's a book
        try:
            book = Book.query.get(content_id)
            if book and book.status == 'available':
                # Get book file path
                file_handler = current_app.config.get('FILE_HANDLER')
                if file_handler:
                    file_path = file_handler.get_book_file_path(book.id)
                    if os.path.exists(file_path):
                        logger.info(f"Serving book file: {book.title}")
                        return send_file(
                            file_path,
                            as_attachment=True,
                            download_name=f"{book.title}.{book.format.lower()}",
                            mimetype='application/octet-stream'
                        )
        except Exception as e:
            logger.warning(f"Book download failed for {content_id}: {e}")
        
        # Check if it's a news digest
        if content_id.startswith('news_'):
            try:
                # Parse content ID to extract source and date
                parts = content_id.split('_')
                if len(parts) >= 3:
                    source_parts = parts[1:-1]  # Everything between 'news_' and date
                    source_name = ' '.join(word.capitalize() for word in source_parts)
                    date_str = parts[-1]
                    
                    # Get articles for this source from recent time
                    cutoff_time = datetime.utcnow() - timedelta(hours=48)
                    articles = NewsItem.query.filter(
                        NewsItem.source_name == source_name,
                        NewsItem.epub_included == True,
                        NewsItem.published_at >= cutoff_time,
                        NewsItem.quality_score >= 0.3
                    ).order_by(NewsItem.published_at.desc()).limit(20).all()
                    
                    if articles:
                        # Create EPUB
                        epub_creator = EpubCreator()
                        title = f"{source_name} News Digest - {datetime.utcnow().strftime('%Y-%m-%d')}"
                        
                        try:
                            epub_path = epub_creator.create_news_digest(
                                title=title,
                                articles=articles,
                                author=source_name
                            )
                            
                            if not epub_path or not os.path.exists(epub_path):
                                raise Exception("Failed to create EPUB file")
                            
                            logger.info(f"Serving news digest: {title} ({len(articles)} articles)")
                            
                            filename = f"{source_name.replace(' ', '_')}_digest_{datetime.utcnow().strftime('%Y%m%d')}.epub"
                            
                            # Send file
                            response = send_file(
                                epub_path,
                                as_attachment=True,
                                download_name=filename,
                                mimetype='application/epub+zip'
                            )
                            
                            # Clean up temp file after sending
                            try:
                                os.unlink(epub_path)
                            except Exception:
                                pass
                            
                            return response
                            
                        except Exception as e:
                            logger.error(f"Error creating EPUB: {e}")
                            # Clean up temp file on error
                            if 'epub_path' in locals() and epub_path:
                                try:
                                    os.unlink(epub_path)
                                except Exception:
                                    pass
                            raise e
                            
            except Exception as e:
                logger.error(f"News digest creation failed for {content_id}: {e}")
        
        # Content not found
        logger.warning(f"Content not found: {content_id}")
        return jsonify({'error': 'Content not found'}), 404
        
    except Exception as e:
        logger.error(f"Error downloading content {content_id}: {e}")
        return jsonify({'error': 'Failed to download content'}), 500


@kual_api_bp.route('/content/sync-status', methods=['POST'])
def report_sync_status():
    """Receive sync status report from Kindle device"""
    try:
        device_id, error = verify_device_auth()
        if error:
            return jsonify({'error': error}), 401
        
        data = request.get_json() or {}
        content_id = data.get('content_id')
        status = data.get('status')  # 'success', 'failed', 'in_progress'
        message = data.get('message', '')
        download_time = data.get('download_time')
        file_size = data.get('file_size')
        
        logger.info(f"Sync status report from {device_id}: {content_id} - {status}")
        
        # Log the sync status (in production, you'd store this in database)
        sync_log_data = {
            'device_id': device_id,
            'content_id': content_id,
            'status': status,
            'message': message,
            'download_time': download_time,
            'file_size': file_size,
            'reported_at': datetime.utcnow().isoformat()
        }
        
        # For now, just log it
        logger.info(f"Sync report: {json.dumps(sync_log_data)}")
        
        # If it's a book, update its sync status
        try:
            book = Book.query.get(content_id)
            if book:
                if status == 'success':
                    book.mark_synced()
                    db.session.commit()
                    logger.info(f"Marked book {book.title} as synced")
        except Exception as e:
            logger.warning(f"Failed to update book sync status: {e}")
        
        return jsonify({
            'status': 'received',
            'message': 'Sync status recorded successfully',
            'content_id': content_id,
            'server_time': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error recording sync status: {e}")
        return jsonify({'error': 'Failed to record sync status'}), 500


@kual_api_bp.route('/device/info', methods=['GET'])
def get_device_info():
    """Get device-specific information and settings"""
    try:
        device_id, error = verify_device_auth()
        if error:
            return jsonify({'error': error}), 401
        
        # Return device-specific settings
        return jsonify({
            'device_id': device_id,
            'sync_settings': {
                'auto_sync_enabled': True,
                'sync_interval': 3600,  # 1 hour
                'max_downloads_per_session': 10,
                'wifi_only': True
            },
            'content_preferences': {
                'supported_formats': ['epub', 'pdf', 'mobi', 'txt'],
                'max_file_size': 50 * 1024 * 1024,  # 50MB
                'preferred_categories': ['news', 'books']
            },
            'server_info': {
                'server_time': datetime.utcnow().isoformat(),
                'api_version': '1.0',
                'features': ['books', 'news_digests', 'auto_sync']
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting device info: {e}")
        return jsonify({'error': 'Failed to get device info'}), 500


@kual_api_bp.route('/stats', methods=['GET'])
def get_sync_stats():
    """Get synchronization statistics"""
    try:
        device_id, error = verify_device_auth()
        if error:
            return jsonify({'error': error}), 401
        
        # Get basic statistics
        book_count = Book.query.filter_by(status='available').count()
        article_count = NewsItem.query.filter_by(epub_included=True).count()
        
        recent_articles = NewsItem.query.filter(
            NewsItem.published_at >= datetime.utcnow() - timedelta(hours=24),
            NewsItem.epub_included == True
        ).count()
        
        return jsonify({
            'content_stats': {
                'available_books': book_count,
                'ready_articles': article_count,
                'new_articles_24h': recent_articles
            },
            'sync_stats': {
                'last_sync': datetime.utcnow().isoformat(),
                'total_downloads': 0,  # Would track in production
                'successful_syncs': 0,  # Would track in production
                'failed_syncs': 0      # Would track in production
            },
            'device_id': device_id,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting sync stats: {e}")
        return jsonify({'error': 'Failed to get sync stats'}), 500


# Error handlers for this blueprint
@kual_api_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@kual_api_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Unauthorized - invalid device credentials'}), 401


@kual_api_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500
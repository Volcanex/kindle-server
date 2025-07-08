"""
Kindle sync API endpoints
Handles synchronization between the server and Kindle devices
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import logging

from models import db, Book, SyncLog
from services.kindle_sync import KindleSyncService
from utils.file_handler import FileHandler

sync_bp = Blueprint('sync', __name__)
logger = logging.getLogger(__name__)

@sync_bp.route('/status', methods=['GET'])
def sync_status():
    """Get overall sync status and statistics"""
    try:
        # Get recent sync statistics
        stats = SyncLog.get_stats(days=7)
        
        # Get pending syncs
        pending_books = Book.get_pending_sync()
        pending_retries = SyncLog.get_pending_retries()
        
        return jsonify({
            'status': 'operational',
            'stats': {
                'last_7_days': stats,
                'pending_books': len(pending_books),
                'pending_retries': len(pending_retries)
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        return jsonify({'error': 'Failed to get sync status'}), 500

@sync_bp.route('/book/<book_id>', methods=['POST'])
def sync_book(book_id):
    """Sync a specific book to Kindle"""
    try:
        # Validate request data
        if not request.json or 'kindle_email' not in request.json:
            return jsonify({'error': 'kindle_email is required'}), 400
        
        kindle_email = request.json['kindle_email']
        
        # Validate email format
        if not kindle_email.endswith('@kindle.com'):
            return jsonify({'error': 'Invalid Kindle email format'}), 400
        
        # Get book
        book = Book.query.get_or_404(book_id)
        
        # Check if book is ready for sync
        if book.status != 'available':
            return jsonify({'error': f'Book status is {book.status}, cannot sync'}), 400
        
        # Create sync log
        sync_log = SyncLog.create_sync_log(
            operation_type='book_sync',
            kindle_email=kindle_email,
            book_id=book.id,
            file_name=f"{book.title}.{book.format.lower()}",
            file_size=book.file_size,
            user_agent=request.headers.get('User-Agent'),
            ip_address=request.remote_addr
        )
        
        # Start sync operation
        sync_service = KindleSyncService()
        success = sync_service.sync_book_to_kindle(book, kindle_email, sync_log)
        
        if success:
            book.mark_synced()
            return jsonify({
                'message': 'Book sync initiated successfully',
                'sync_log_id': str(sync_log.id),
                'book_id': str(book.id)
            }), 200
        else:
            return jsonify({
                'error': 'Failed to initiate book sync',
                'sync_log_id': str(sync_log.id)
            }), 500
            
    except Exception as e:
        logger.error(f"Error syncing book {book_id}: {e}")
        return jsonify({'error': 'Failed to sync book'}), 500

@sync_bp.route('/news-digest', methods=['POST'])
def sync_news_digest():
    """Create and sync news digest to Kindle"""
    try:
        # Validate request data
        if not request.json or 'kindle_email' not in request.json:
            return jsonify({'error': 'kindle_email is required'}), 400
        
        kindle_email = request.json['kindle_email']
        digest_title = request.json.get('title', f'News Digest - {datetime.now().strftime("%Y-%m-%d")}')
        max_articles = request.json.get('max_articles', 20)
        min_quality = request.json.get('min_quality', 0.5)
        
        # Validate email format
        if not kindle_email.endswith('@kindle.com'):
            return jsonify({'error': 'Invalid Kindle email format'}), 400
        
        # Generate digest ID
        digest_id = f"news_digest_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Create sync log
        sync_log = SyncLog.create_sync_log(
            operation_type='news_digest',
            kindle_email=kindle_email,
            news_digest_id=digest_id,
            file_name=f"{digest_title}.epub",
            metadata={
                'digest_title': digest_title,
                'max_articles': max_articles,
                'min_quality': min_quality
            },
            user_agent=request.headers.get('User-Agent'),
            ip_address=request.remote_addr
        )
        
        # Start news digest sync
        sync_service = KindleSyncService()
        success = sync_service.sync_news_digest_to_kindle(
            kindle_email, digest_title, max_articles, min_quality, sync_log
        )
        
        if success:
            return jsonify({
                'message': 'News digest sync initiated successfully',
                'sync_log_id': str(sync_log.id),
                'digest_id': digest_id
            }), 200
        else:
            return jsonify({
                'error': 'Failed to initiate news digest sync',
                'sync_log_id': str(sync_log.id)
            }), 500
            
    except Exception as e:
        logger.error(f"Error syncing news digest: {e}")
        return jsonify({'error': 'Failed to sync news digest'}), 500

@sync_bp.route('/batch', methods=['POST'])
def sync_batch():
    """Sync multiple books to Kindle"""
    try:
        # Validate request data
        if not request.json or 'kindle_email' not in request.json or 'book_ids' not in request.json:
            return jsonify({'error': 'kindle_email and book_ids are required'}), 400
        
        kindle_email = request.json['kindle_email']
        book_ids = request.json['book_ids']
        
        # Validate email format
        if not kindle_email.endswith('@kindle.com'):
            return jsonify({'error': 'Invalid Kindle email format'}), 400
        
        # Validate book IDs
        if not isinstance(book_ids, list) or len(book_ids) == 0:
            return jsonify({'error': 'book_ids must be a non-empty list'}), 400
        
        if len(book_ids) > 10:  # Limit batch size
            return jsonify({'error': 'Maximum 10 books per batch sync'}), 400
        
        # Get books
        books = Book.query.filter(Book.id.in_(book_ids)).all()
        
        if len(books) != len(book_ids):
            return jsonify({'error': 'One or more books not found'}), 404
        
        # Check all books are ready for sync
        unavailable_books = [book for book in books if book.status != 'available']
        if unavailable_books:
            return jsonify({
                'error': 'Some books are not available for sync',
                'unavailable_books': [str(book.id) for book in unavailable_books]
            }), 400
        
        # Start batch sync
        sync_service = KindleSyncService()
        sync_results = []
        
        for book in books:
            # Create sync log for each book
            sync_log = SyncLog.create_sync_log(
                operation_type='batch_book_sync',
                kindle_email=kindle_email,
                book_id=book.id,
                file_name=f"{book.title}.{book.format.lower()}",
                file_size=book.file_size,
                user_agent=request.headers.get('User-Agent'),
                ip_address=request.remote_addr
            )
            
            # Sync book
            success = sync_service.sync_book_to_kindle(book, kindle_email, sync_log)
            
            sync_results.append({
                'book_id': str(book.id),
                'sync_log_id': str(sync_log.id),
                'success': success
            })
            
            if success:
                book.mark_synced()
        
        successful_syncs = [r for r in sync_results if r['success']]
        failed_syncs = [r for r in sync_results if not r['success']]
        
        return jsonify({
            'message': f'Batch sync completed: {len(successful_syncs)} successful, {len(failed_syncs)} failed',
            'results': sync_results,
            'summary': {
                'total': len(books),
                'successful': len(successful_syncs),
                'failed': len(failed_syncs)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error in batch sync: {e}")
        return jsonify({'error': 'Failed to perform batch sync'}), 500

@sync_bp.route('/logs', methods=['GET'])
def get_sync_logs():
    """Get sync logs with optional filtering"""
    try:
        # Query parameters
        kindle_email = request.args.get('kindle_email')
        operation_type = request.args.get('operation_type')
        status = request.args.get('status')
        limit = min(int(request.args.get('limit', 50)), 100)  # Max 100
        offset = int(request.args.get('offset', 0))
        
        # Build query
        query = SyncLog.query
        
        if kindle_email:
            query = query.filter(SyncLog.kindle_email == kindle_email)
        
        if operation_type:
            query = query.filter(SyncLog.operation_type == operation_type)
        
        if status:
            query = query.filter(SyncLog.status == status)
        
        # Get logs with pagination
        logs = query.order_by(SyncLog.created_at.desc())\
                   .offset(offset).limit(limit).all()
        
        # Get total count for pagination
        total_count = query.count()
        
        return jsonify({
            'logs': [log.to_dict() for log in logs],
            'pagination': {
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total_count
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting sync logs: {e}")
        return jsonify({'error': 'Failed to get sync logs'}), 500

@sync_bp.route('/logs/<log_id>', methods=['GET'])
def get_sync_log(log_id):
    """Get specific sync log details"""
    try:
        sync_log = SyncLog.query.get_or_404(log_id)
        return jsonify(sync_log.to_dict()), 200
        
    except Exception as e:
        logger.error(f"Error getting sync log {log_id}: {e}")
        return jsonify({'error': 'Failed to get sync log'}), 500

@sync_bp.route('/retry/<log_id>', methods=['POST'])
def retry_sync(log_id):
    """Retry a failed sync operation"""
    try:
        sync_log = SyncLog.query.get_or_404(log_id)
        
        # Check if sync can be retried
        if not sync_log.can_retry():
            return jsonify({
                'error': f'Sync cannot be retried. Status: {sync_log.status}, Retry count: {sync_log.retry_count}'
            }), 400
        
        # Increment retry count
        can_retry = sync_log.retry_operation()
        
        if not can_retry:
            return jsonify({'error': 'Maximum retries exceeded'}), 400
        
        # Retry the operation based on type
        sync_service = KindleSyncService()
        
        if sync_log.operation_type in ['book_sync', 'batch_book_sync']:
            if sync_log.book_id:
                book = Book.query.get(sync_log.book_id)
                if book:
                    success = sync_service.sync_book_to_kindle(book, sync_log.kindle_email, sync_log)
                else:
                    sync_log.complete_failure("Book not found")
                    success = False
            else:
                sync_log.complete_failure("No book ID in sync log")
                success = False
                
        elif sync_log.operation_type == 'news_digest':
            metadata = sync_log.metadata or {}
            success = sync_service.sync_news_digest_to_kindle(
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
            return jsonify({
                'message': 'Sync retry initiated successfully',
                'sync_log_id': str(sync_log.id)
            }), 200
        else:
            return jsonify({
                'error': 'Sync retry failed',
                'sync_log_id': str(sync_log.id)
            }), 500
            
    except Exception as e:
        logger.error(f"Error retrying sync {log_id}: {e}")
        return jsonify({'error': 'Failed to retry sync'}), 500
"""
Articles API endpoints
Handles article syncing and management for Kindle sync
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import logging

from models import db, NewsItem
from services.article_sync_manager import ArticleSyncManager
from services.rss_feed_tester import FeedConfiguration

articles_bp = Blueprint('articles', __name__)
logger = logging.getLogger(__name__)


@articles_bp.route('/sync-sources', methods=['POST'])
def sync_news_sources():
    """Sync articles from news sources"""
    try:
        data = request.get_json() or {}
        sources = data.get('sources', [])
        force_sync = data.get('force', False)
        
        if not sources:
            return jsonify({'error': 'No sources provided'}), 400
        
        # Create sync manager
        sync_manager = ArticleSyncManager()
        
        # Sync sources
        result = sync_manager.sync_all_due_sources(sources, force=force_sync)
        
        return jsonify({
            'message': 'Article sync completed',
            'result': result,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error syncing articles: {e}")
        return jsonify({'error': 'Failed to sync articles'}), 500


@articles_bp.route('/sync-source/<source_id>', methods=['POST'])
def sync_single_source():
    """Sync articles from a single news source"""
    try:
        data = request.get_json() or {}
        
        # This would normally get the source from database
        # For now, expect source data in request
        source = data.get('source')
        if not source:
            return jsonify({'error': 'Source data required'}), 400
        
        # Create sync manager
        sync_manager = ArticleSyncManager()
        
        # Sync single source
        result = sync_manager.sync_source_articles(source)
        
        return jsonify({
            'message': f'Sync completed for {source.get("name", "Unknown")}',
            'result': result,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error syncing source: {e}")
        return jsonify({'error': 'Failed to sync source'}), 500


@articles_bp.route('/for-kindle-sync', methods=['GET'])
def get_articles_for_kindle_sync():
    """Get articles ready for Kindle sync, grouped by source"""
    try:
        # Query parameters
        hours = int(request.args.get('hours', 24))
        max_hours = min(hours, 168)  # Max 1 week
        
        # Create sync manager
        sync_manager = ArticleSyncManager()
        
        # Get articles grouped by source
        articles = sync_manager.get_articles_for_kindle_sync(max_hours)
        
        # Calculate totals
        total_articles = sum(group['article_count'] for group in articles)
        total_sources = len(articles)
        
        return jsonify({
            'articles_by_source': articles,
            'summary': {
                'total_articles': total_articles,
                'total_sources': total_sources,
                'hours_range': max_hours,
                'generated_at': datetime.utcnow().isoformat()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting articles for Kindle sync: {e}")
        return jsonify({'error': 'Failed to get articles for Kindle sync'}), 500


@articles_bp.route('/kindle-sync-items', methods=['GET'])
def get_kindle_sync_items():
    """Get individual articles formatted for sync status display"""
    try:
        # Query parameters
        hours = int(request.args.get('hours', 24))
        limit = min(int(request.args.get('limit', 50)), 100)
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Get articles that are ready for Kindle sync
        articles = NewsItem.query.filter(
            NewsItem.epub_included == True,
            NewsItem.published_at >= cutoff_time,
            NewsItem.quality_score >= 0.3
        ).order_by(
            NewsItem.source_name.asc(),
            NewsItem.published_at.desc()
        ).limit(limit).all()
        
        # Format for sync status display
        sync_items = []
        for article in articles:
            sync_items.append({
                'id': f"article_{article.id}",
                'type': 'article',
                'title': article.title,
                'itemName': article.title,
                'status': 'ready',
                'timestamp': article.published_at.isoformat(),
                'lastSync': None,
                'progress': 100,
                'message': f"Ready to sync to Kindle",
                'source': article.source_name,
                'articleInfo': {
                    'author': article.author,
                    'source_name': article.source_name,
                    'word_count': article.word_count,
                    'reading_time': article.reading_time,
                    'quality_score': article.quality_score,
                    'category': article.category,
                    'published_at': article.published_at.isoformat(),
                    'summary': article.summary[:150] + '...' if article.summary and len(article.summary) > 150 else article.summary
                }
            })
        
        return jsonify(sync_items), 200
        
    except Exception as e:
        logger.error(f"Error getting Kindle sync items: {e}")
        return jsonify({'error': 'Failed to get sync items'}), 500


@articles_bp.route('/stats', methods=['GET'])
def get_article_stats():
    """Get article synchronization statistics"""
    try:
        sync_manager = ArticleSyncManager()
        stats = sync_manager.get_sync_statistics()
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error getting article stats: {e}")
        return jsonify({'error': 'Failed to get article statistics'}), 500


@articles_bp.route('/cleanup', methods=['POST'])
def cleanup_old_articles():
    """Clean up old articles"""
    try:
        data = request.get_json() or {}
        days = data.get('days', 30)
        keep_epub_included = data.get('keep_epub_included', True)
        
        if days < 1 or days > 365:
            return jsonify({'error': 'Days must be between 1 and 365'}), 400
        
        sync_manager = ArticleSyncManager()
        deleted_count = sync_manager.cleanup_old_articles(days, keep_epub_included)
        
        return jsonify({
            'message': f'Cleaned up {deleted_count} old articles',
            'deleted_count': deleted_count,
            'days': days,
            'keep_epub_included': keep_epub_included
        }), 200
        
    except Exception as e:
        logger.error(f"Error cleaning up articles: {e}")
        return jsonify({'error': 'Failed to clean up articles'}), 500


@articles_bp.route('/<article_id>/toggle-sync', methods=['PUT'])
def toggle_article_sync(article_id):
    """Toggle article sync status (include/exclude from Kindle sync)"""
    try:
        article = NewsItem.query.get_or_404(article_id)
        
        if article.epub_included:
            article.exclude_from_epub("Manually excluded")
            message = f'Article "{article.title}" excluded from Kindle sync'
        else:
            article.include_in_epub()
            message = f'Article "{article.title}" included in Kindle sync'
        
        db.session.commit()
        
        return jsonify({
            'message': message,
            'article_id': str(article.id),
            'epub_included': article.epub_included,
            'status': article.status
        }), 200
        
    except Exception as e:
        logger.error(f"Error toggling article sync: {e}")
        return jsonify({'error': 'Failed to toggle article sync'}), 500


@articles_bp.route('/bulk-actions', methods=['POST'])
def bulk_article_actions():
    """Perform bulk actions on articles"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data required'}), 400
        
        action = data.get('action')
        article_ids = data.get('article_ids', [])
        
        if not action or not article_ids:
            return jsonify({'error': 'Action and article_ids required'}), 400
        
        if len(article_ids) > 100:
            return jsonify({'error': 'Maximum 100 articles allowed per bulk action'}), 400
        
        articles = NewsItem.query.filter(NewsItem.id.in_(article_ids)).all()
        
        if not articles:
            return jsonify({'error': 'No articles found'}), 404
        
        processed_count = 0
        
        if action == 'include_in_sync':
            for article in articles:
                article.include_in_epub()
                processed_count += 1
        elif action == 'exclude_from_sync':
            reason = data.get('reason', 'Bulk exclusion')
            for article in articles:
                article.exclude_from_epub(reason)
                processed_count += 1
        elif action == 'delete':
            for article in articles:
                db.session.delete(article)
                processed_count += 1
        else:
            return jsonify({'error': f'Unknown action: {action}'}), 400
        
        db.session.commit()
        
        return jsonify({
            'message': f'Bulk action "{action}" completed',
            'processed_count': processed_count,
            'total_requested': len(article_ids)
        }), 200
        
    except Exception as e:
        logger.error(f"Error performing bulk action: {e}")
        return jsonify({'error': 'Failed to perform bulk action'}), 500


@articles_bp.route('/recent', methods=['GET'])
def get_recent_articles():
    """Get recent articles with pagination"""
    try:
        # Query parameters
        hours = int(request.args.get('hours', 24))
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = int(request.args.get('offset', 0))
        source = request.args.get('source')
        include_content = request.args.get('include_content', 'false').lower() == 'true'
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Build query
        query = NewsItem.query.filter(NewsItem.published_at >= cutoff_time)
        
        if source:
            query = query.filter(NewsItem.source_name == source)
        
        # Apply sorting and pagination
        query = query.order_by(NewsItem.published_at.desc())
        total_count = query.count()
        articles = query.offset(offset).limit(limit).all()
        
        # Format articles
        articles_data = []
        for article in articles:
            article_dict = {
                'id': str(article.id),
                'title': article.title,
                'author': article.author,
                'source_name': article.source_name,
                'category': article.category,
                'published_at': article.published_at.isoformat(),
                'word_count': article.word_count,
                'reading_time': article.reading_time,
                'quality_score': article.quality_score,
                'epub_included': article.epub_included,
                'status': article.status,
                'summary': article.summary
            }
            
            if include_content:
                article_dict['content'] = article.content
            
            articles_data.append(article_dict)
        
        return jsonify({
            'articles': articles_data,
            'pagination': {
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total_count
            },
            'query_info': {
                'hours': hours,
                'source': source,
                'include_content': include_content
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting recent articles: {e}")
        return jsonify({'error': 'Failed to get recent articles'}), 500
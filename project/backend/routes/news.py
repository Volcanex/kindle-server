"""
News API endpoints
Handles RSS news aggregation and management
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import logging

from models import db, NewsItem
from services.news_aggregator import NewsAggregator
from utils.epub_creator import EpubCreator

news_bp = Blueprint('news', __name__)
logger = logging.getLogger(__name__)

@news_bp.route('/', methods=['GET'])
def list_news():
    """List news items with optional filtering and pagination"""
    try:
        # Query parameters
        source = request.args.get('source')
        category = request.args.get('category')
        status = request.args.get('status')
        search = request.args.get('search')
        hours = int(request.args.get('hours', 24))  # Recent news within X hours
        limit = min(int(request.args.get('limit', 50)), 100)  # Max 100
        offset = int(request.args.get('offset', 0))
        include_content = request.args.get('include_content', 'false').lower() == 'true'
        
        # Build query
        query = NewsItem.query
        
        # Apply filters
        if search:
            news_items = NewsItem.search(search, limit=limit)
            total_count = len(news_items)
        else:
            if source:
                query = query.filter(NewsItem.source_name == source)
            
            if category:
                query = query.filter(NewsItem.category == category)
            
            if status:
                query = query.filter(NewsItem.status == status)
            
            # Filter by recency
            if hours > 0:
                cutoff = datetime.utcnow() - timedelta(hours=hours)
                query = query.filter(NewsItem.published_at >= cutoff)
            
            # Apply sorting
            query = query.order_by(NewsItem.published_at.desc())
            
            # Get total count
            total_count = query.count()
            
            # Apply pagination
            news_items = query.offset(offset).limit(limit).all()
        
        # Convert to dict, optionally excluding content for performance
        items_data = []
        for item in news_items:
            item_dict = item.to_dict()
            if not include_content:
                item_dict.pop('content', None)
            items_data.append(item_dict)
        
        return jsonify({
            'news_items': items_data,
            'pagination': {
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total_count
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing news: {e}")
        return jsonify({'error': 'Failed to list news items'}), 500

@news_bp.route('/<news_id>', methods=['GET'])
def get_news_item(news_id):
    """Get specific news item details"""
    try:
        news_item = NewsItem.query.get_or_404(news_id)
        return jsonify(news_item.to_dict()), 200
        
    except Exception as e:
        logger.error(f"Error getting news item {news_id}: {e}")
        return jsonify({'error': 'Failed to get news item'}), 500

@news_bp.route('/aggregate', methods=['POST'])
def aggregate_news():
    """Manually trigger news aggregation"""
    try:
        # Get optional parameters
        force_refresh = request.json.get('force_refresh', False) if request.json else False
        max_articles_per_feed = request.json.get('max_articles_per_feed', 10) if request.json else 10
        
        # Start news aggregation
        aggregator = NewsAggregator()
        results = aggregator.aggregate_all_feeds(force_refresh, max_articles_per_feed)
        
        return jsonify({
            'message': 'News aggregation completed',
            'results': results,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error aggregating news: {e}")
        return jsonify({'error': 'Failed to aggregate news'}), 500

@news_bp.route('/sources', methods=['GET'])
def get_sources():
    """Get list of news sources"""
    try:
        sources = db.session.query(NewsItem.source_name, db.func.count(NewsItem.id))\
                           .group_by(NewsItem.source_name)\
                           .order_by(db.func.count(NewsItem.id).desc()).all()
        
        source_list = [{'name': source[0], 'count': source[1]} for source in sources]
        
        return jsonify({'sources': source_list}), 200
        
    except Exception as e:
        logger.error(f"Error getting sources: {e}")
        return jsonify({'error': 'Failed to get sources'}), 500

@news_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get list of news categories"""
    try:
        categories = db.session.query(NewsItem.category, db.func.count(NewsItem.id))\
                              .filter(NewsItem.category.isnot(None))\
                              .group_by(NewsItem.category)\
                              .order_by(db.func.count(NewsItem.id).desc()).all()
        
        category_list = [{'name': category[0], 'count': category[1]} for category in categories]
        
        return jsonify({'categories': category_list}), 200
        
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        return jsonify({'error': 'Failed to get categories'}), 500

@news_bp.route('/digest', methods=['POST'])
def create_digest():
    """Create news digest EPUB"""
    try:
        # Validate request data
        if not request.json:
            return jsonify({'error': 'JSON data required'}), 400
        
        title = request.json.get('title', f'News Digest - {datetime.now().strftime("%Y-%m-%d")}')
        max_articles = request.json.get('max_articles', 20)
        min_quality = request.json.get('min_quality', 0.5)
        sources = request.json.get('sources', [])  # Filter by specific sources
        categories = request.json.get('categories', [])  # Filter by specific categories
        hours = request.json.get('hours', 24)  # Recent articles within X hours
        
        # Get news items for digest
        query = NewsItem.query.filter(
            NewsItem.epub_included == True,
            NewsItem.quality_score >= min_quality
        )
        
        # Apply filters
        if sources:
            query = query.filter(NewsItem.source_name.in_(sources))
        
        if categories:
            query = query.filter(NewsItem.category.in_(categories))
        
        if hours > 0:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            query = query.filter(NewsItem.published_at >= cutoff)
        
        # Get articles
        articles = query.order_by(NewsItem.published_at.desc()).limit(max_articles).all()
        
        if not articles:
            return jsonify({'error': 'No articles found matching criteria'}), 404
        
        # Create EPUB
        epub_creator = EpubCreator()
        epub_path = epub_creator.create_news_digest(title, articles)
        
        if epub_path:
            return jsonify({
                'message': 'News digest created successfully',
                'epub_path': epub_path,
                'title': title,
                'article_count': len(articles),
                'created_at': datetime.utcnow().isoformat()
            }), 201
        else:
            return jsonify({'error': 'Failed to create news digest'}), 500
            
    except Exception as e:
        logger.error(f"Error creating news digest: {e}")
        return jsonify({'error': 'Failed to create news digest'}), 500

@news_bp.route('/<news_id>/include', methods=['PUT'])
def include_in_epub(news_id):
    """Include news item in EPUB generation"""
    try:
        news_item = NewsItem.query.get_or_404(news_id)
        news_item.include_in_epub()
        
        return jsonify({
            'message': 'News item included in EPUB',
            'news_id': str(news_item.id),
            'epub_included': news_item.epub_included
        }), 200
        
    except Exception as e:
        logger.error(f"Error including news item {news_id} in EPUB: {e}")
        return jsonify({'error': 'Failed to include news item in EPUB'}), 500

@news_bp.route('/<news_id>/exclude', methods=['PUT'])
def exclude_from_epub(news_id):
    """Exclude news item from EPUB generation"""
    try:
        news_item = NewsItem.query.get_or_404(news_id)
        reason = request.json.get('reason') if request.json else None
        
        news_item.exclude_from_epub(reason)
        
        return jsonify({
            'message': 'News item excluded from EPUB',
            'news_id': str(news_item.id),
            'epub_included': news_item.epub_included,
            'reason': reason
        }), 200
        
    except Exception as e:
        logger.error(f"Error excluding news item {news_id} from EPUB: {e}")
        return jsonify({'error': 'Failed to exclude news item from EPUB'}), 500

@news_bp.route('/process-pending', methods=['POST'])
def process_pending():
    """Process pending news items"""
    try:
        pending_items = NewsItem.get_pending_processing()
        
        processed_count = 0
        for item in pending_items:
            try:
                item.process_content()
                processed_count += 1
            except Exception as e:
                logger.error(f"Error processing news item {item.id}: {e}")
                continue
        
        db.session.commit()
        
        return jsonify({
            'message': f'Processed {processed_count} news items',
            'processed_count': processed_count,
            'total_pending': len(pending_items)
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing pending news items: {e}")
        return jsonify({'error': 'Failed to process pending news items'}), 500

@news_bp.route('/stats', methods=['GET'])
def get_news_stats():
    """Get news collection statistics"""
    try:
        stats = {
            'total_items': NewsItem.query.count(),
            'by_status': dict(db.session.query(NewsItem.status, db.func.count(NewsItem.id)).group_by(NewsItem.status).all()),
            'by_source': dict(db.session.query(NewsItem.source_name, db.func.count(NewsItem.id)).group_by(NewsItem.source_name).all()),
            'epub_included': NewsItem.query.filter_by(epub_included=True).count(),
            'recent_24h': NewsItem.query.filter(
                NewsItem.published_at >= datetime.utcnow() - timedelta(hours=24)
            ).count(),
            'average_quality_score': db.session.query(db.func.avg(NewsItem.quality_score)).scalar() or 0,
            'total_word_count': db.session.query(db.func.sum(NewsItem.word_count)).scalar() or 0
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error getting news stats: {e}")
        return jsonify({'error': 'Failed to get news stats'}), 500

@news_bp.route('/cleanup', methods=['POST'])
def cleanup_old_news():
    """Clean up old news items"""
    try:
        days = request.json.get('days', 30) if request.json else 30
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Delete old news items that are not included in EPUB
        deleted_count = NewsItem.query.filter(
            NewsItem.created_at < cutoff,
            NewsItem.epub_included == False
        ).delete()
        
        db.session.commit()
        
        return jsonify({
            'message': f'Cleaned up {deleted_count} old news items',
            'deleted_count': deleted_count,
            'cutoff_date': cutoff.isoformat()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error cleaning up news items: {e}")
        return jsonify({'error': 'Failed to clean up news items'}), 500
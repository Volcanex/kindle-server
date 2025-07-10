"""
RSS Feed Management API endpoints
Handles RSS feed testing, configuration, and management
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import logging
from typing import Dict, List

from services.rss_feed_tester import RSSFeedTester, FeedConfiguration, FeedHealthStatus
from services.news_aggregator import NewsAggregator
from models import db
from utils.validation import validate_json_schema

rss_feeds_bp = Blueprint('rss_feeds', __name__)
logger = logging.getLogger(__name__)

# JSON schemas for validation
RSS_FEED_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {"type": "string", "format": "uri"},
        "name": {"type": "string", "minLength": 1, "maxLength": 100},
        "category": {"type": "string", "maxLength": 50},
        "config": {
            "type": "object",
            "properties": {
                "max_articles": {"type": "integer", "minimum": 1, "maximum": 100},
                "timeout": {"type": "integer", "minimum": 5, "maximum": 120},
                "quality_threshold": {"type": "number", "minimum": 0, "maximum": 1},
                "update_frequency": {"type": "string", "enum": ["hourly", "daily", "weekly"]},
                "content_filters": {"type": "array", "items": {"type": "string"}},
                "custom_headers": {"type": "object"},
                "retry_count": {"type": "integer", "minimum": 1, "maximum": 5}
            },
            "additionalProperties": False
        }
    },
    "required": ["url"],
    "additionalProperties": False
}

FEED_TEST_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {"type": "string", "format": "uri"},
        "config": {
            "type": "object",
            "properties": {
                "max_articles": {"type": "integer", "minimum": 1, "maximum": 50},
                "timeout": {"type": "integer", "minimum": 5, "maximum": 60},
                "quality_threshold": {"type": "number", "minimum": 0, "maximum": 1}
            }
        }
    },
    "required": ["url"],
    "additionalProperties": False
}


@rss_feeds_bp.route('/test', methods=['POST'])
def test_rss_feed():
    """Test a single RSS feed"""
    try:
        # Validate input
        if not validate_json_schema(request.json, FEED_TEST_SCHEMA):
            return jsonify({'error': 'Invalid request data'}), 400
        
        data = request.json
        url = data['url']
        
        # Create configuration
        config_data = data.get('config', {})
        config = FeedConfiguration(
            max_articles=config_data.get('max_articles', 10),
            timeout=config_data.get('timeout', 30),
            quality_threshold=config_data.get('quality_threshold', 0.3)
        )
        
        # Test the feed
        tester = RSSFeedTester()
        result = tester.test_feed(url, config)
        
        # Convert result to dict
        result_dict = {
            'url': result.url,
            'status': result.status.value,
            'success': result.success,
            'title': result.title,
            'description': result.description,
            'article_count': result.article_count,
            'last_updated': result.last_updated.isoformat() if result.last_updated else None,
            'error_message': result.error_message,
            'warnings': result.warnings,
            'metadata': result.metadata,
            'test_duration': result.test_duration,
            'sample_articles': result.sample_articles,
            'tested_at': datetime.utcnow().isoformat()
        }
        
        return jsonify(result_dict), 200
        
    except Exception as e:
        logger.error(f"Error testing RSS feed: {e}")
        return jsonify({'error': 'Failed to test RSS feed'}), 500


@rss_feeds_bp.route('/test/multiple', methods=['POST'])
def test_multiple_rss_feeds():
    """Test multiple RSS feeds at once"""
    try:
        data = request.json
        if not data or 'urls' not in data:
            return jsonify({'error': 'URLs list required'}), 400
        
        urls = data['urls']
        if not isinstance(urls, list) or len(urls) == 0:
            return jsonify({'error': 'Invalid URLs list'}), 400
        
        if len(urls) > 10:  # Limit to prevent abuse
            return jsonify({'error': 'Maximum 10 URLs allowed'}), 400
        
        # Create configuration
        config_data = data.get('config', {})
        config = FeedConfiguration(
            max_articles=config_data.get('max_articles', 5),  # Lower for multiple feeds
            timeout=config_data.get('timeout', 15),  # Lower timeout
            quality_threshold=config_data.get('quality_threshold', 0.3)
        )
        
        # Test all feeds
        tester = RSSFeedTester()
        results = tester.test_multiple_feeds(urls, config)
        
        # Convert results to dict
        results_dict = []
        for result in results:
            results_dict.append({
                'url': result.url,
                'status': result.status.value,
                'success': result.success,
                'title': result.title,
                'description': result.description,
                'article_count': result.article_count,
                'last_updated': result.last_updated.isoformat() if result.last_updated else None,
                'error_message': result.error_message,
                'warnings': result.warnings,
                'test_duration': result.test_duration,
                'sample_articles': result.sample_articles[:3]  # Limit sample articles
            })
        
        # Generate summary
        summary = {
            'total_feeds': len(results),
            'successful_feeds': sum(1 for r in results if r.success),
            'failed_feeds': sum(1 for r in results if not r.success),
            'healthy_feeds': sum(1 for r in results if r.status == FeedHealthStatus.HEALTHY),
            'warning_feeds': sum(1 for r in results if r.status == FeedHealthStatus.WARNING),
            'error_feeds': sum(1 for r in results if r.status == FeedHealthStatus.ERROR),
            'total_articles': sum(r.article_count for r in results),
            'average_test_duration': sum(r.test_duration for r in results) / len(results)
        }
        
        return jsonify({
            'results': results_dict,
            'summary': summary,
            'tested_at': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error testing multiple RSS feeds: {e}")
        return jsonify({'error': 'Failed to test RSS feeds'}), 500


@rss_feeds_bp.route('/validate', methods=['POST'])
def validate_rss_feed():
    """Validate RSS feed before saving"""
    try:
        # Validate input
        if not validate_json_schema(request.json, FEED_TEST_SCHEMA):
            return jsonify({'error': 'Invalid request data'}), 400
        
        data = request.json
        url = data['url']
        
        # Create configuration
        config_data = data.get('config', {})
        config = FeedConfiguration(
            max_articles=config_data.get('max_articles', 10),
            timeout=config_data.get('timeout', 30),
            quality_threshold=config_data.get('quality_threshold', 0.3)
        )
        
        # Validate the feed
        tester = RSSFeedTester()
        is_valid, error_message, metadata = tester.validate_feed_before_save(url, config)
        
        if is_valid:
            return jsonify({
                'valid': True,
                'message': 'RSS feed is valid and ready to be saved',
                'metadata': metadata
            }), 200
        else:
            return jsonify({
                'valid': False,
                'error': error_message,
                'metadata': metadata
            }), 200
        
    except Exception as e:
        logger.error(f"Error validating RSS feed: {e}")
        return jsonify({'error': 'Failed to validate RSS feed'}), 500


@rss_feeds_bp.route('/suggest', methods=['POST'])
def suggest_rss_feeds():
    """Get RSS feed suggestions from website URL"""
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({'error': 'Website URL required'}), 400
        
        url = data['url']
        
        # Get suggestions
        tester = RSSFeedTester()
        suggestions = tester.get_feed_suggestions(url)
        
        # Test suggestions to see which ones work
        if data.get('test_suggestions', False):
            config = FeedConfiguration(max_articles=3, timeout=10)
            tested_suggestions = []
            
            for suggestion in suggestions[:5]:  # Test only first 5 suggestions
                result = tester.test_feed(suggestion, config)
                tested_suggestions.append({
                    'url': suggestion,
                    'success': result.success,
                    'title': result.title,
                    'article_count': result.article_count,
                    'status': result.status.value
                })
            
            return jsonify({
                'suggestions': tested_suggestions,
                'tested': True
            }), 200
        else:
            return jsonify({
                'suggestions': [{'url': url, 'tested': False} for url in suggestions],
                'tested': False
            }), 200
        
    except Exception as e:
        logger.error(f"Error getting RSS feed suggestions: {e}")
        return jsonify({'error': 'Failed to get RSS feed suggestions'}), 500


@rss_feeds_bp.route('/health', methods=['GET'])
def check_feed_health():
    """Check health of configured RSS feeds"""
    try:
        # Get configured feeds from settings
        from config.settings import Config
        feeds = getattr(Config, 'RSS_FEEDS', [])
        
        if not feeds:
            return jsonify({
                'message': 'No RSS feeds configured',
                'feeds': [],
                'summary': {
                    'total': 0,
                    'healthy': 0,
                    'warning': 0,
                    'error': 0
                }
            }), 200
        
        # Check health of all feeds
        aggregator = NewsAggregator()
        health_status = aggregator.get_feed_health()
        
        # Format response
        feed_details = []
        for feed_url in feeds:
            status = health_status['feed_status'].get(feed_url, 'unknown')
            feed_details.append({
                'url': feed_url,
                'status': 'healthy' if status == 'healthy' else 'error',
                'details': status
            })
        
        return jsonify({
            'feeds': feed_details,
            'summary': {
                'total': len(feeds),
                'healthy': health_status['healthy_feeds'],
                'error': health_status['unhealthy_feeds'],
                'warning': 0
            },
            'checked_at': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error checking feed health: {e}")
        return jsonify({'error': 'Failed to check feed health'}), 500


@rss_feeds_bp.route('/config/schema', methods=['GET'])
def get_config_schema():
    """Get RSS feed configuration schema"""
    return jsonify({
        'feed_schema': RSS_FEED_SCHEMA,
        'test_schema': FEED_TEST_SCHEMA,
        'config_options': {
            'max_articles': {
                'type': 'integer',
                'min': 1,
                'max': 100,
                'default': 10,
                'description': 'Maximum number of articles to fetch per feed'
            },
            'timeout': {
                'type': 'integer',
                'min': 5,
                'max': 120,
                'default': 30,
                'description': 'Request timeout in seconds'
            },
            'quality_threshold': {
                'type': 'number',
                'min': 0.0,
                'max': 1.0,
                'default': 0.3,
                'description': 'Minimum quality score for articles (0.0-1.0)'
            },
            'update_frequency': {
                'type': 'string',
                'options': ['hourly', 'daily', 'weekly'],
                'default': 'daily',
                'description': 'How often to update the feed'
            },
            'content_filters': {
                'type': 'array',
                'default': [],
                'description': 'Keywords to filter out from content'
            },
            'retry_count': {
                'type': 'integer',
                'min': 1,
                'max': 5,
                'default': 3,
                'description': 'Number of retry attempts for failed requests'
            }
        }
    }), 200


@rss_feeds_bp.route('/test/quick', methods=['POST'])
def quick_test_rss_feed():
    """Quick test of RSS feed (minimal validation)"""
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({'error': 'URL required'}), 400
        
        url = data['url']
        
        # Quick configuration
        config = FeedConfiguration(
            max_articles=3,
            timeout=10,
            quality_threshold=0.1
        )
        
        # Test the feed
        tester = RSSFeedTester()
        result = tester.test_feed(url, config)
        
        # Return minimal response
        return jsonify({
            'url': url,
            'success': result.success,
            'title': result.title,
            'article_count': result.article_count,
            'status': result.status.value,
            'error_message': result.error_message,
            'test_duration': result.test_duration
        }), 200
        
    except Exception as e:
        logger.error(f"Error in quick RSS feed test: {e}")
        return jsonify({'error': 'Failed to test RSS feed'}), 500


@rss_feeds_bp.route('/preview', methods=['POST'])
def preview_rss_feed():
    """Preview RSS feed content"""
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({'error': 'URL required'}), 400
        
        url = data['url']
        max_articles = data.get('max_articles', 5)
        
        # Configuration for preview
        config = FeedConfiguration(
            max_articles=min(max_articles, 10),
            timeout=20,
            quality_threshold=0.0,  # Include all articles for preview
            content_extraction=True
        )
        
        # Test the feed
        tester = RSSFeedTester()
        result = tester.test_feed(url, config)
        
        if not result.success:
            return jsonify({
                'error': result.error_message,
                'url': url
            }), 400
        
        # Return preview data
        return jsonify({
            'url': url,
            'title': result.title,
            'description': result.description,
            'article_count': result.article_count,
            'last_updated': result.last_updated.isoformat() if result.last_updated else None,
            'articles': result.sample_articles,
            'metadata': {
                'feed_format': result.metadata.get('feed_format'),
                'language': result.metadata.get('language'),
                'generator': result.metadata.get('generator')
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error previewing RSS feed: {e}")
        return jsonify({'error': 'Failed to preview RSS feed'}), 500
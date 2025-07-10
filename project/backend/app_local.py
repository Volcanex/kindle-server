"""
Kindle Content Server - Local Development Flask Application
Simplified version for local testing without Google Cloud dependencies
"""

import os
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

# Import configuration
from config.settings import DevelopmentConfig

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory storage for local development (module level)
uploaded_books = []
news_sources = []

def create_app(config_class=DevelopmentConfig):
    """Create Flask application with simplified configuration"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db = SQLAlchemy()
    db.init_app(app)
    
    # Enable CORS for local development - allow all origins for testing
    CORS(app, 
         origins=['*'],  # Allow all origins for local development
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
         allow_headers=['Content-Type', 'Authorization', 'X-Server-Passcode'],
         supports_credentials=True)
    
    # Optional server passcode (leave blank for no security)
    SERVER_PASSCODE = os.environ.get('SERVER_PASSCODE', '')  # Empty = no passcode required
    
    # Passcode check middleware
    @app.before_request
    def check_passcode():
        if request.method == "OPTIONS":
            response = jsonify({'status': 'ok'})
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add('Access-Control-Allow-Headers', "*")
            response.headers.add('Access-Control-Allow-Methods', "*")
            return response
        
        # Skip passcode check for health endpoints
        if request.path in ['/health', '/', '/api/health']:
            return
            
        # Check passcode if one is set
        if SERVER_PASSCODE:
            provided_passcode = request.headers.get('X-Server-Passcode', '')
            if provided_passcode != SERVER_PASSCODE:
                return jsonify({
                    'error': 'Invalid or missing server passcode',
                    'message': '🔒 Server requires passcode in X-Server-Passcode header'
                }), 401

    # Health check endpoints (both for compatibility)
    @app.route('/health', methods=['GET', 'OPTIONS'])
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'service': 'kindle-content-server',
            'version': '1.0.0-local'
        })
    
    @app.route('/api/health', methods=['GET', 'OPTIONS'])
    def api_health_check():
        """API Health check endpoint (frontend expects this)"""
        from datetime import datetime
        return jsonify({
            'status': 'healthy',
            'service': 'kindle-content-server',
            'version': '1.0.0-local',
            'timestamp': datetime.now().isoformat() + 'Z'
        })
    
    @app.route('/', methods=['GET', 'OPTIONS'])
    def root():
        """Root endpoint with service information"""
        return jsonify({
            'service': 'Kindle Content Server Backend',
            'version': '1.0.0-local',
            'status': 'running',
            'environment': 'development',
            'endpoints': {
                'health': '/health',
                'books': '/api/books',
                'news': '/api/news', 
                'sync': '/api/sync',
                'rss-feeds': '/api/rss-feeds',
                'kual-api': '/api/v1'
            }
        })
    
    
    # Basic API endpoints for testing
    @app.route('/api/books', methods=['GET', 'OPTIONS'])
    def get_books():
        """Get books list"""
        # Return array directly to match frontend expectations
        return jsonify(uploaded_books)
    
    @app.route('/api/books/upload', methods=['POST', 'OPTIONS'])
    def upload_book():
        """Upload book endpoint"""
        logger.info(f"Upload request - Files: {list(request.files.keys())}")
        logger.info(f"Upload request - Form: {list(request.form.keys())}")
        
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        if not file.filename:
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Extract book info
        import uuid
        from datetime import datetime
        
        book_id = str(uuid.uuid4())
        filename = file.filename
        title = filename.rsplit('.', 1)[0]  # Remove extension for title
        author = "Unknown Author"  # In real app, would extract from metadata
        format_type = filename.rsplit('.', 1)[-1].upper() if '.' in filename else 'UNKNOWN'
        
        # Create book record
        book = {
            'id': book_id,
            'title': title,
            'author': author,
            'format': format_type,
            'fileSize': len(file.read()),  # Get file size
            'uploadDate': datetime.now().isoformat(),
            'syncStatus': 'pending',
            'filename': filename
        }
        
        # Reset file pointer after reading size
        file.seek(0)
        
        # Store book (in real app would save to database and file storage)
        uploaded_books.append(book)
        
        return jsonify({
            'success': True,
            'message': f'Successfully uploaded "{filename}"',
            'book': book
        })
    
    # News Sources (match frontend expectations)
    @app.route('/api/news-sources', methods=['GET', 'OPTIONS'])
    def get_news_sources():
        """Get news sources"""
        # Return array directly to match frontend expectations
        return jsonify(news_sources)
    
    @app.route('/api/news-sources', methods=['POST', 'OPTIONS'])
    def create_news_source():
        """Create news source with RSS feed validation"""
        logger.info(f"Create news source request - Method: {request.method}")
        
        if request.method == 'OPTIONS':
            logger.info("Handling OPTIONS request for create")
            response = jsonify({'status': 'ok'})
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add('Access-Control-Allow-Headers', "*")
            response.headers.add('Access-Control-Allow-Methods', "*")
            return response
        
        try:
            data = request.get_json()
            logger.info(f"Create data received: {data}")
            
            if not data:
                logger.error("No data provided in create request")
                return jsonify({
                    'success': False,
                    'error': 'No data provided'
                }), 400
            
            # Validate required fields
            if not data.get('name') or not data.get('url'):
                return jsonify({
                    'success': False,
                    'error': 'Name and URL are required'
                }), 400
            
            # Validate and test RSS feed URL
            from services.rss_feed_tester import RSSFeedTester, FeedConfiguration
            
            rss_url = data.get('url')
            logger.info(f"Testing RSS feed: {rss_url}")
            
            # Quick validation
            tester = RSSFeedTester()
            config = FeedConfiguration(max_articles=3, timeout=10, quality_threshold=0.1)
            
            is_valid, error_message, metadata = tester.validate_feed_before_save(rss_url, config)
            
            if not is_valid:
                logger.warning(f"RSS feed validation failed: {error_message}")
                return jsonify({
                    'success': False,
                    'error': f'RSS feed validation failed: {error_message}',
                    'validation_failed': True
                }), 400
            
            logger.info(f"RSS feed validation passed: {metadata}")
            
            import uuid
            from datetime import datetime
            
            # Create news source record
            news_source = {
                'id': str(uuid.uuid4()),
                'name': data.get('name', ''),
                'url': data.get('url', ''),
                'category': data.get('category', ''),
                'syncFrequency': data.get('syncFrequency', 'daily'),
                'isActive': data.get('isActive', True),
                'createdAt': datetime.now().isoformat(),
                'lastSync': None,
                'syncStatus': 'pending',
                'validationMetadata': metadata,  # Store validation metadata
                'nextSyncDue': datetime.now().isoformat()  # Due for first sync
            }
            
            logger.info(f"Created news source object: {news_source}")
            
            # Store news source
            news_sources.append(news_source)
            logger.info(f"Added to news_sources. Total count: {len(news_sources)}")
            
            response_data = {
                'success': True,
                'message': f'News source "{news_source["name"]}" created successfully (RSS feed validated)',
                'data': news_source,
                'validation_passed': True
            }
            
            logger.info(f"Returning response: {response_data}")
            return jsonify(response_data)
            
        except Exception as e:
            logger.error(f"Error creating news source: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'Server error: {str(e)}',
                'details': traceback.format_exc()
            }), 500
    
    @app.route('/api/news-sources/<id>', methods=['PUT', 'OPTIONS'])
    def update_news_source(id):
        """Update news source"""
        global news_sources
        
        logger.info(f"Update request for news source ID: {id}")
        logger.info(f"Request method: {request.method}")
        
        if request.method == 'OPTIONS':
            logger.info("Handling OPTIONS request for update")
            response = jsonify({'status': 'ok'})
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add('Access-Control-Allow-Headers', "*")
            response.headers.add('Access-Control-Allow-Methods', "*")
            return response
        
        try:
            data = request.get_json()
            logger.info(f"Update data: {data}")
            
            if not data:
                logger.error("No data provided in update request")
                return jsonify({
                    'success': False,
                    'error': 'No data provided'
                }), 400
            
            # Find and update news source
            for i, source in enumerate(news_sources):
                if source['id'] == id:
                    logger.info(f"Found news source to update: {source['name']}")
                    # Update fields
                    news_sources[i].update({
                        'name': data.get('name', source['name']),
                        'url': data.get('url', source['url']),
                        'category': data.get('category', source['category']),
                        'syncFrequency': data.get('syncFrequency', source['syncFrequency']),
                        'isActive': data.get('isActive', source['isActive']),
                    })
                    
                    logger.info(f"Successfully updated news source: {news_sources[i]['name']}")
                    return jsonify({
                        'success': True,
                        'message': f'News source "{news_sources[i]["name"]}" updated successfully',
                        'data': news_sources[i]
                    })
            
            logger.warning(f"News source not found for update: {id}")
            return jsonify({
                'success': False,
                'error': 'News source not found'
            }), 404
            
        except Exception as e:
            logger.error(f"Error updating news source: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'Server error: {str(e)}',
                'details': traceback.format_exc()
            }), 500
    
    @app.route('/api/news-sources/<id>', methods=['DELETE', 'OPTIONS'])
    def delete_news_source(id):
        """Delete news source"""
        global news_sources
        
        logger.info(f"Delete request for news source ID: {id}")
        logger.info(f"Request method: {request.method}")
        
        if request.method == 'OPTIONS':
            logger.info("Handling OPTIONS request for delete")
            response = jsonify({'status': 'ok'})
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add('Access-Control-Allow-Headers', "*")
            response.headers.add('Access-Control-Allow-Methods', "*")
            return response
        
        try:
            logger.info(f"Current news sources: {[s['id'] for s in news_sources]}")
            
            # Find and remove news source
            for source in news_sources:
                if source['id'] == id:
                    news_sources.remove(source)
                    logger.info(f"Successfully deleted news source: {source['name']}")
                    return jsonify({
                        'success': True,
                        'message': f'News source "{source["name"]}" deleted successfully'
                    })
            
            logger.warning(f"News source not found: {id}")
            return jsonify({
                'success': False,
                'error': 'News source not found'
            }), 404
            
        except Exception as e:
            logger.error(f"Error deleting news source: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'Server error: {str(e)}',
                'details': traceback.format_exc()
            }), 500
    
    @app.route('/api/news-sources/<id>/sync', methods=['POST', 'OPTIONS'])
    def sync_news_source(id):
        """Sync news source"""
        return jsonify({
            'success': True,
            'message': f'News source {id} sync triggered - local development mode'
        })
    
    # Sync Status (match frontend expectations)
    @app.route('/api/sync-status', methods=['GET', 'OPTIONS'])
    def get_sync_statuses():
        """Get sync statuses - now shows individual articles ready for sync"""
        sync_statuses = []
        
        # Add uploaded books as sync statuses
        for book in uploaded_books:
            sync_statuses.append({
                'id': book['id'],
                'type': 'book',
                'title': book['title'],
                'itemName': book['title'],
                'status': book.get('syncStatus', 'pending'),
                'timestamp': book['uploadDate'],
                'lastSync': book.get('lastSync'),
                'progress': 0 if book.get('syncStatus') == 'pending' else 100,
                'message': f"Book ready for sync to Kindle" if book.get('syncStatus') == 'pending' else 'Synced successfully',
                'bookInfo': {
                    'author': book['author'],
                    'format': book['format'],
                    'fileSize': book['fileSize'],
                    'filename': book['filename']
                }
            })
        
        # Simulate articles ready for sync based on news sources
        from datetime import datetime, timedelta
        import uuid
        
        current_time = datetime.now()
        
        # Generate sample articles for each active news source
        for source in news_sources:
            if source.get('isActive', True):
                # Simulate 2-5 articles per source ready for sync
                import random
                article_count = random.randint(2, 5)
                
                for i in range(article_count):
                    article_id = str(uuid.uuid4())
                    article_time = current_time - timedelta(hours=random.randint(1, 12))
                    
                    # Sample article titles based on source category
                    category = source.get('category', 'News')
                    if category.lower() == 'technology':
                        titles = [
                            "New AI Breakthrough in Machine Learning",
                            "Latest Software Development Trends",
                            "Cybersecurity Updates and Best Practices",
                            "Cloud Computing Innovations"
                        ]
                    elif category.lower() == 'science':
                        titles = [
                            "Climate Change Research Findings",
                            "Space Exploration Mission Updates",
                            "Medical Research Breakthroughs",
                            "Physics Discovery Announcement"
                        ]
                    else:
                        titles = [
                            "Breaking News Update",
                            "Economic Market Analysis",
                            "Political Development Report",
                            "Global Events Coverage"
                        ]
                    
                    title = f"{random.choice(titles)} - {source['name']}"
                    
                    sync_statuses.append({
                        'id': f"article_{article_id}",
                        'type': 'article',
                        'title': title,
                        'itemName': title,
                        'status': 'ready',
                        'timestamp': article_time.isoformat(),
                        'lastSync': None,
                        'progress': 100,
                        'message': f"Article ready to sync to Kindle",
                        'source': source['name'],
                        'articleInfo': {
                            'source_name': source['name'],
                            'category': category,
                            'word_count': random.randint(300, 1500),
                            'reading_time': random.randint(2, 8),
                            'quality_score': round(random.uniform(0.6, 0.9), 2),
                            'published_at': article_time.isoformat(),
                            'summary': f"Summary of article from {source['name']} in {category} category."
                        }
                    })
        
        return jsonify(sync_statuses)
    
    @app.route('/api/sync-status/<id>', methods=['GET', 'OPTIONS'])
    def get_sync_status(id):
        """Get specific sync status"""
        return jsonify({
            'status': {},
            'message': f'Sync status {id} - local development mode'
        })
    
    # Authentication endpoints (DISABLED FOR LOCAL DEVELOPMENT)
    @app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
    def auth_login():
        """Login endpoint - auto-success for local testing"""
        data = request.get_json() or {}
        email = data.get('email', 'dev@localhost')
        return jsonify({
            'success': True,
            'token': 'dev-token-123',
            'user': {
                'id': 'dev-user-1', 
                'email': email, 
                'name': 'Local Dev User'
            },
            'message': '🔓 AUTH DISABLED - Local development mode (no real authentication)'
        })
    
    @app.route('/api/auth/register', methods=['POST', 'OPTIONS'])
    def auth_register():
        """Register endpoint - auto-success for local testing"""
        data = request.get_json() or {}
        email = data.get('email', 'dev@localhost')
        name = data.get('name', 'Local Dev User')
        return jsonify({
            'success': True,
            'token': 'dev-token-123',
            'user': {
                'id': 'dev-user-1',
                'email': email,
                'name': name
            },
            'message': '🔓 AUTH DISABLED - Registration bypassed for local development'
        })
    
    @app.route('/api/auth/logout', methods=['POST', 'OPTIONS'])
    def auth_logout():
        """Logout endpoint - no-op for local testing"""
        return jsonify({
            'success': True,
            'message': '🔓 AUTH DISABLED - Logout bypassed for local development'
        })
    
    @app.route('/api/auth/me', methods=['GET', 'OPTIONS'])
    def auth_me():
        """Get current user - always returns dev user"""
        return jsonify({
            'user': {
                'id': 'dev-user-1',
                'email': 'dev@localhost', 
                'name': 'Local Dev User'
            },
            'message': '🔓 AUTH DISABLED - Using dev user for local development'
        })
    
    # RSS Feed Testing endpoints
    @app.route('/api/rss-feeds/test', methods=['POST', 'OPTIONS'])
    def test_rss_feed():
        """Test RSS feed endpoint"""
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'ok'})
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add('Access-Control-Allow-Headers', "*")
            response.headers.add('Access-Control-Allow-Methods', "*")
            return response
        
        try:
            data = request.get_json()
            if not data or 'url' not in data:
                return jsonify({'error': 'URL required'}), 400
            
            from services.rss_feed_tester import RSSFeedTester, FeedConfiguration
            from datetime import datetime
            
            url = data['url']
            config_data = data.get('config', {})
            
            config = FeedConfiguration(
                max_articles=config_data.get('max_articles', 10),
                timeout=config_data.get('timeout', 30),
                quality_threshold=config_data.get('quality_threshold', 0.3)
            )
            
            tester = RSSFeedTester()
            result = tester.test_feed(url, config)
            
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
                'test_duration': result.test_duration,
                'sample_articles': result.sample_articles,
                'tested_at': datetime.now().isoformat()
            }
            
            return jsonify(result_dict)
            
        except Exception as e:
            logger.error(f"Error testing RSS feed: {e}")
            return jsonify({'error': f'Failed to test RSS feed: {str(e)}'}), 500
    
    @app.route('/api/rss-feeds/validate', methods=['POST', 'OPTIONS'])
    def validate_rss_feed():
        """Validate RSS feed endpoint"""
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'ok'})
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add('Access-Control-Allow-Headers', "*")
            response.headers.add('Access-Control-Allow-Methods', "*")
            return response
        
        try:
            data = request.get_json()
            if not data or 'url' not in data:
                return jsonify({'error': 'URL required'}), 400
            
            from services.rss_feed_tester import RSSFeedTester, FeedConfiguration
            
            url = data['url']
            config_data = data.get('config', {})
            
            config = FeedConfiguration(
                max_articles=config_data.get('max_articles', 10),
                timeout=config_data.get('timeout', 30),
                quality_threshold=config_data.get('quality_threshold', 0.3)
            )
            
            tester = RSSFeedTester()
            is_valid, error_message, metadata = tester.validate_feed_before_save(url, config)
            
            if is_valid:
                return jsonify({
                    'valid': True,
                    'message': 'RSS feed is valid and ready to be saved',
                    'metadata': metadata
                })
            else:
                return jsonify({
                    'valid': False,
                    'error': error_message,
                    'metadata': metadata
                })
            
        except Exception as e:
            logger.error(f"Error validating RSS feed: {e}")
            return jsonify({'error': f'Failed to validate RSS feed: {str(e)}'}), 500
    
    @app.route('/api/rss-feeds/quick', methods=['POST', 'OPTIONS'])
    def quick_test_rss_feed():
        """Quick test RSS feed endpoint"""
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'ok'})
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add('Access-Control-Allow-Headers', "*")
            response.headers.add('Access-Control-Allow-Methods', "*")
            return response
        
        try:
            data = request.get_json()
            if not data or 'url' not in data:
                return jsonify({'error': 'URL required'}), 400
            
            from services.rss_feed_tester import RSSFeedTester, FeedConfiguration
            
            url = data['url']
            config = FeedConfiguration(max_articles=3, timeout=10, quality_threshold=0.1)
            
            tester = RSSFeedTester()
            result = tester.test_feed(url, config)
            
            return jsonify({
                'url': url,
                'success': result.success,
                'title': result.title,
                'article_count': result.article_count,
                'status': result.status.value,
                'error_message': result.error_message,
                'test_duration': result.test_duration
            })
            
        except Exception as e:
            logger.error(f"Error in quick RSS feed test: {e}")
            return jsonify({'error': f'Failed to test RSS feed: {str(e)}'}), 500
    
    # Article sync endpoints
    @app.route('/api/news-sources/<id>/sync', methods=['POST', 'OPTIONS'])
    def sync_news_source_articles(id):
        """Sync articles from a specific news source"""
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'ok'})
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add('Access-Control-Allow-Headers', "*")
            response.headers.add('Access-Control-Allow-Methods', "*")
            return response
        
        try:
            # Find the news source
            source = None
            for s in news_sources:
                if s['id'] == id:
                    source = s
                    break
            
            if not source:
                return jsonify({
                    'success': False,
                    'error': 'News source not found'
                }), 404
            
            # Simulate article sync
            from services.article_sync_manager import ArticleSyncManager
            from datetime import datetime, timedelta
            sync_manager = ArticleSyncManager()
            
            # For local dev, just update the sync status
            current_time = datetime.now().isoformat()
            
            # Update the source
            for i, s in enumerate(news_sources):
                if s['id'] == id:
                    news_sources[i]['lastSync'] = current_time
                    news_sources[i]['syncStatus'] = 'synced'
                    # Calculate next sync time based on frequency
                    frequency = s.get('syncFrequency', 'daily')
                    if frequency == 'hourly':
                        next_sync = datetime.now() + timedelta(hours=1)
                    elif frequency == 'weekly':
                        next_sync = datetime.now() + timedelta(weeks=1)
                    elif frequency == 'monthly':
                        next_sync = datetime.now() + timedelta(days=30)
                    else:  # daily
                        next_sync = datetime.now() + timedelta(days=1)
                    
                    news_sources[i]['nextSyncDue'] = next_sync.isoformat()
                    break
            
            # Simulate sync result
            import random
            articles_synced = random.randint(3, 8)
            
            return jsonify({
                'success': True,
                'message': f'Successfully synced {articles_synced} articles from {source["name"]}',
                'result': {
                    'source_id': id,
                    'source_name': source['name'],
                    'articles_added': articles_synced,
                    'articles_updated': 0,
                    'articles_total': articles_synced,
                    'last_sync': current_time,
                    'next_sync_due': news_sources[i]['nextSyncDue']
                }
            })
            
        except Exception as e:
            logger.error(f"Error syncing news source: {e}")
            return jsonify({
                'success': False,
                'error': f'Failed to sync news source: {str(e)}'
            }), 500
    
    @app.route('/api/articles/sync-all', methods=['POST', 'OPTIONS'])
    def sync_all_articles():
        """Sync articles from all active news sources"""
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'ok'})
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add('Access-Control-Allow-Headers', "*")
            response.headers.add('Access-Control-Allow-Methods', "*")
            return response
        
        try:
            from datetime import datetime, timedelta
            
            active_sources = [s for s in news_sources if s.get('isActive', True)]
            
            if not active_sources:
                return jsonify({
                    'success': False,
                    'error': 'No active news sources to sync'
                }), 400
            
            current_time = datetime.now()
            synced_sources = 0
            total_articles = 0
            
            # Update all active sources
            for i, source in enumerate(news_sources):
                if source.get('isActive', True):
                    # Simulate article sync
                    import random
                    articles_count = random.randint(2, 6)
                    total_articles += articles_count
                    
                    # Update sync info
                    news_sources[i]['lastSync'] = current_time.isoformat()
                    news_sources[i]['syncStatus'] = 'synced'
                    
                    # Calculate next sync time
                    frequency = source.get('syncFrequency', 'daily')
                    if frequency == 'hourly':
                        next_sync = current_time + timedelta(hours=1)
                    elif frequency == 'weekly':
                        next_sync = current_time + timedelta(weeks=1)
                    elif frequency == 'monthly':
                        next_sync = current_time + timedelta(days=30)
                    else:  # daily
                        next_sync = current_time + timedelta(days=1)
                    
                    news_sources[i]['nextSyncDue'] = next_sync.isoformat()
                    synced_sources += 1
            
            return jsonify({
                'success': True,
                'message': f'Successfully synced {synced_sources} sources with {total_articles} total articles',
                'result': {
                    'sources_synced': synced_sources,
                    'total_articles': total_articles,
                    'sync_completed_at': current_time.isoformat()
                }
            })
            
        except Exception as e:
            logger.error(f"Error syncing all articles: {e}")
            return jsonify({
                'success': False,
                'error': f'Failed to sync articles: {str(e)}'
            }), 500
    
    # Books endpoints (add missing ones)
    @app.route('/api/books/<id>', methods=['GET', 'OPTIONS'])
    def get_book(id):
        """Get specific book"""
        return jsonify({
            'book': {'id': id, 'title': f'Book {id}', 'author': 'Test Author'},
            'message': f'Book {id} - local development mode'
        })
    
    @app.route('/api/books/<id>', methods=['DELETE', 'OPTIONS'])
    def delete_book(id):
        """Delete book"""
        global uploaded_books
        
        # Find and remove book
        book_to_remove = None
        for book in uploaded_books:
            if book['id'] == id:
                book_to_remove = book
                break
        
        if book_to_remove:
            uploaded_books.remove(book_to_remove)
            return jsonify({
                'success': True,
                'message': f'Book "{book_to_remove["title"]}" deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Book not found'
            }), 404
    
    # KUAL API endpoints for Kindle client
    @app.route('/api/v1/health', methods=['GET', 'OPTIONS'])
    def kual_health_check():
        """Health check endpoint for KUAL client"""
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'ok'})
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add('Access-Control-Allow-Headers', "*")
            response.headers.add('Access-Control-Allow-Methods', "*")
            return response
        
        return jsonify({
            'status': 'healthy',
            'service': 'kindle-content-server',
            'version': '1.0.0-local',
            'timestamp': datetime.now().isoformat()
        }), 200
    
    @app.route('/api/v1/auth/device', methods=['POST', 'OPTIONS'])
    def kual_authenticate_device():
        """Authenticate Kindle device - simplified for local dev"""
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'ok'})
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add('Access-Control-Allow-Headers', "*")
            response.headers.add('Access-Control-Allow-Methods', "*")
            return response
        
        try:
            device_id = request.headers.get('X-Device-ID', 'local-device')
            api_key = request.headers.get('X-API-Key', 'local-key')
            
            logger.info(f"KUAL device authentication: {device_id}")
            
            return jsonify({
                'status': 'success',
                'message': 'Device authenticated successfully (local dev mode)',
                'device_id': device_id,
                'device_type': 'kindle',
                'server_time': datetime.now().isoformat(),
                'session_expires': (datetime.now() + timedelta(hours=24)).isoformat()
            }), 200
            
        except Exception as e:
            logger.error(f"Error in KUAL auth: {e}")
            return jsonify({
                'status': 'error',
                'message': 'Authentication failed'
            }), 500
    
    @app.route('/api/v1/content/list', methods=['GET', 'OPTIONS'])
    def kual_get_content_list():
        """Get list of content available for download"""
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'ok'})
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add('Access-Control-Allow-Headers', "*")
            response.headers.add('Access-Control-Allow-Methods', "*")
            return response
        
        try:
            device_id = request.headers.get('X-Device-ID', 'local-device')
            logger.info(f"KUAL content list requested by: {device_id}")
            
            content_items = []
            
            # Add uploaded books
            for book in uploaded_books:
                content_items.append({
                    'id': book['id'],
                    'type': 'book',
                    'title': book['title'],
                    'author': book['author'],
                    'filename': book['filename'],
                    'format': book['format'].lower(),
                    'file_size': book['fileSize'],
                    'upload_date': book['uploadDate'],
                    'description': f"Book by {book['author']}",
                    'ready_for_sync': True
                })
            
            # Add sample news digests
            from datetime import datetime
            import random
            
            for source in news_sources:
                if source.get('isActive', True):
                    content_items.append({
                        'id': f"news_{source['name'].lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}",
                        'type': 'news_digest',
                        'title': f"{source['name']} - {datetime.now().strftime('%Y-%m-%d')}",
                        'author': source['name'],
                        'filename': f"{source['name'].replace(' ', '_')}_digest_{datetime.now().strftime('%Y%m%d')}.epub",
                        'format': 'epub',
                        'file_size': random.randint(100000, 500000),
                        'upload_date': datetime.now().isoformat(),
                        'description': f"News digest from {source['name']}",
                        'article_count': random.randint(3, 8),
                        'source_name': source['name'],
                        'ready_for_sync': True
                    })
            
            return jsonify({
                'content': content_items,
                'total_items': len(content_items),
                'last_updated': datetime.now().isoformat(),
                'device_id': device_id
            }), 200
            
        except Exception as e:
            logger.error(f"Error getting KUAL content list: {e}")
            return jsonify({'error': 'Failed to get content list'}), 500
    
    @app.route('/api/v1/content/download/<content_id>', methods=['GET', 'OPTIONS'])
    def kual_download_content(content_id):
        """Download specific content file - simulated for local dev"""
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'ok'})
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add('Access-Control-Allow-Headers', "*")
            response.headers.add('Access-Control-Allow-Methods', "*")
            return response
        
        try:
            device_id = request.headers.get('X-Device-ID', 'local-device')
            logger.info(f"KUAL download requested: {content_id} by {device_id}")
            
            # Find the content
            content_found = False
            
            # Check books
            for book in uploaded_books:
                if book['id'] == content_id:
                    content_found = True
                    logger.info(f"Simulating download of book: {book['title']}")
                    
                    # For local dev, return a JSON response instead of actual file
                    return jsonify({
                        'status': 'simulated_download',
                        'message': f"Download simulation for book: {book['title']}",
                        'content_id': content_id,
                        'filename': book['filename'],
                        'file_size': book['fileSize'],
                        'note': 'In production, this would return the actual file'
                    }), 200
            
            # Check news digests
            if content_id.startswith('news_'):
                content_found = True
                logger.info(f"Simulating download of news digest: {content_id}")
                
                return jsonify({
                    'status': 'simulated_download',
                    'message': f"Download simulation for news digest: {content_id}",
                    'content_id': content_id,
                    'format': 'epub',
                    'note': 'In production, this would generate and return an EPUB file'
                }), 200
            
            if not content_found:
                return jsonify({'error': 'Content not found'}), 404
                
        except Exception as e:
            logger.error(f"Error downloading KUAL content: {e}")
            return jsonify({'error': 'Failed to download content'}), 500
    
    @app.route('/api/v1/content/sync-status', methods=['POST', 'OPTIONS'])
    def kual_report_sync_status():
        """Receive sync status report from Kindle device"""
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'ok'})
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add('Access-Control-Allow-Headers', "*")
            response.headers.add('Access-Control-Allow-Methods', "*")
            return response
        
        try:
            device_id = request.headers.get('X-Device-ID', 'local-device')
            data = request.get_json() or {}
            
            content_id = data.get('content_id')
            status = data.get('status')
            message = data.get('message', '')
            
            logger.info(f"KUAL sync status from {device_id}: {content_id} - {status}")
            logger.info(f"Sync message: {message}")
            
            # Update book status if it's a book
            for book in uploaded_books:
                if book['id'] == content_id and status == 'success':
                    book['syncStatus'] = 'synced'
                    book['lastSync'] = datetime.now().isoformat()
                    logger.info(f"Marked book {book['title']} as synced")
                    break
            
            return jsonify({
                'status': 'received',
                'message': 'Sync status recorded successfully',
                'content_id': content_id,
                'server_time': datetime.now().isoformat()
            }), 200
            
        except Exception as e:
            logger.error(f"Error recording KUAL sync status: {e}")
            return jsonify({'error': 'Failed to record sync status'}), 500
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Endpoint not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    # Create tables
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
    
    return app

# Create the application
app = create_app()

if __name__ == '__main__':
    logger.info("Starting Kindle Content Server - Local Development Mode")
    logger.info("Database: SQLite (local)")
    logger.info("Mode: Development")
    app.run(host='0.0.0.0', port=8080, debug=True)
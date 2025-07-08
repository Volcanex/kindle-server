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
        return jsonify({
            'status': 'healthy',
            'service': 'kindle-content-server',
            'version': '1.0.0-local',
            'timestamp': '2025-07-08T14:00:00Z'
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
                'sync': '/api/sync'
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
        """Create news source"""
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
                'syncStatus': 'pending'
            }
            
            logger.info(f"Created news source object: {news_source}")
            
            # Store news source
            news_sources.append(news_source)
            logger.info(f"Added to news_sources. Total count: {len(news_sources)}")
            
            response_data = {
                'success': True,
                'message': f'News source "{news_source["name"]}" created successfully',
                'data': news_source
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
        """Get sync statuses"""
        sync_statuses = []
        
        # Add uploaded books as sync statuses
        for book in uploaded_books:
            sync_statuses.append({
                'id': book['id'],
                'type': 'book',
                'title': book['title'],
                'itemName': book['title'],
                'status': book.get('syncStatus', 'pending'),
                'timestamp': book['uploadDate'],  # Use upload date as timestamp
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
        
        # Add news sources as sync statuses (avoid duplicates)
        for source in news_sources:
            sync_statuses.append({
                'id': f"news_{source['id']}",  # Prefix to avoid ID conflicts
                'type': 'news',
                'title': source['name'],
                'itemName': source['name'],
                'status': source.get('syncStatus', 'pending'),
                'timestamp': source['createdAt'],
                'lastSync': source.get('lastSync'),
                'progress': 0 if source.get('syncStatus') == 'pending' else 100,
                'message': f"News source ready for sync" if source.get('syncStatus') == 'pending' else 'Synced successfully',
                'newsInfo': {
                    'url': source['url'],
                    'category': source['category'],
                    'syncFrequency': source['syncFrequency'],
                    'isActive': source['isActive']
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
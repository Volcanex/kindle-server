"""
Kindle Content Server - Production Flask Application
Optimized for Google Cloud deployment with security and performance
"""

import os
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.middleware.proxy_fix import ProxyFix
import google.cloud.logging

# Import route blueprints
from routes.sync import sync_bp
from routes.books import books_bp  
from routes.news import news_bp
from routes.rss_feeds import rss_feeds_bp
from routes.articles import articles_bp
from routes.kual_api import kual_api_bp

# Import models to ensure they're registered
from models import db
from config.settings import ProductionConfig

def create_app():
    """
    Production application factory for Google Cloud deployment
    """
    app = Flask(__name__)
    app.config.from_object(ProductionConfig)
    
    # Configure logging for Google Cloud
    if os.getenv('GOOGLE_CLOUD_PROJECT'):
        client = google.cloud.logging.Client()
        client.setup_logging()
    else:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(levelname)s %(name)s %(message)s'
        )
    
    # Trust proxy headers for Cloud Run
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
    
    # Initialize extensions
    db.init_app(app)
    
    # Configure CORS for production
    allowed_origins = os.getenv('ALLOWED_ORIGINS', '').split(',')
    if not allowed_origins or allowed_origins == ['']:
        # Default production CORS - restrict to specific domains
        allowed_origins = [
            'https://your-frontend-domain.com',
            'https://kindle-content-server.web.app',  # Firebase hosting example
            'https://localhost:3000'  # Local development
        ]
    
    CORS(app, 
         origins=allowed_origins,
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
         allow_headers=['Content-Type', 'Authorization', 'X-Server-Passcode', 'X-Device-ID', 'X-API-Key'],
         supports_credentials=True)
    
    # Security middleware
    @app.before_request
    def security_headers():
        """Add security headers to all responses"""
        # Skip for OPTIONS requests
        if request.method == 'OPTIONS':
            return
        
        # Add security headers
        @app.after_request
        def after_request(response):
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            return response
    
    # Server passcode authentication for API endpoints
    SERVER_PASSCODE = os.environ.get('SERVER_PASSCODE')
    
    @app.before_request
    def check_authentication():
        """Check authentication for protected endpoints"""
        # Skip authentication for health checks and OPTIONS
        if request.method == 'OPTIONS' or request.path in ['/health', '/', '/api/health']:
            return
        
        # Skip authentication for KUAL API (has its own device auth)
        if request.path.startswith('/api/v1/'):
            return
        
        # Check server passcode for other API endpoints
        if request.path.startswith('/api/') and SERVER_PASSCODE:
            provided_passcode = request.headers.get('X-Server-Passcode')
            if not provided_passcode or provided_passcode != SERVER_PASSCODE:
                return jsonify({
                    'error': 'Invalid or missing server passcode',
                    'message': 'Server requires valid authentication'
                }), 401
    
    # Register blueprints
    app.register_blueprint(sync_bp, url_prefix='/api/sync')
    app.register_blueprint(books_bp, url_prefix='/api/books')
    app.register_blueprint(news_bp, url_prefix='/api/news')
    app.register_blueprint(rss_feeds_bp, url_prefix='/api/rss-feeds')
    app.register_blueprint(articles_bp, url_prefix='/api/articles')
    app.register_blueprint(kual_api_bp)  # KUAL API has its own prefix
    
    # Health check endpoint for Cloud Run
    @app.route('/health')
    def health_check():
        """Health check endpoint for Cloud Run load balancer"""
        return jsonify({
            'status': 'healthy',
            'service': 'kindle-content-server',
            'version': os.getenv('SERVICE_VERSION', '1.0.0'),
            'environment': 'production'
        }), 200
    
    # API health check
    @app.route('/api/health')
    def api_health_check():
        """API health check with database connectivity test"""
        try:
            # Test database connection
            db.session.execute('SELECT 1')
            db_status = 'connected'
        except Exception as e:
            logging.error(f"Database health check failed: {e}")
            db_status = 'disconnected'
        
        return jsonify({
            'status': 'healthy',
            'service': 'kindle-content-server-api',
            'version': os.getenv('SERVICE_VERSION', '1.0.0'),
            'database': db_status,
            'environment': 'production'
        }), 200
    
    # Root endpoint
    @app.route('/')
    def root():
        """Root endpoint with service information"""
        return jsonify({
            'service': 'Kindle Content Server',
            'version': os.getenv('SERVICE_VERSION', '1.0.0'),
            'status': 'running',
            'environment': 'production',
            'endpoints': {
                'health': '/health',
                'api_health': '/api/health',
                'books': '/api/books',
                'news': '/api/news',
                'sync': '/api/sync',
                'rss_feeds': '/api/rss-feeds',
                'articles': '/api/articles',
                'kual_api': '/api/v1'
            },
            'documentation': 'https://github.com/your-repo/kindle-content-server'
        })
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Endpoint not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        logging.error(f"Internal server error: {error}")
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({'error': 'Unauthorized access'}), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({'error': 'Forbidden'}), 403
    
    # Create database tables
    with app.app_context():
        try:
            db.create_all()
            logging.info("Database tables created successfully")
        except Exception as e:
            logging.error(f"Failed to create database tables: {e}")
    
    return app

# Create app instance
app = create_app()

if __name__ == '__main__':
    # Production server configuration
    port = int(os.environ.get('PORT', 8080))
    host = os.environ.get('HOST', '0.0.0.0')
    
    logging.info(f"Starting Kindle Content Server on {host}:{port}")
    logging.info("Environment: Production")
    
    app.run(
        host=host,
        port=port,
        debug=False,
        threaded=True
    )
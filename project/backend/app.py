"""
Kindle Content Server - Flask Backend Application
Optimized for Google Cloud Run 2024 deployment
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

# Import models to ensure they're registered
from models import db
from config.settings import Config

def create_app(config_class=Config):
    """
    Application factory pattern for Flask app creation
    Follows Cloud Run 2024 best practices
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Configure logging for Cloud Run
    if os.getenv('GOOGLE_CLOUD_PROJECT'):
        client = google.cloud.logging.Client()
        client.setup_logging()
    else:
        logging.basicConfig(level=logging.INFO)
    
    # Trust proxy headers for Cloud Run
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
    
    # Initialize extensions
    db.init_app(app)
    CORS(app, origins=os.getenv('ALLOWED_ORIGINS', '*').split(','))
    
    # Register blueprints
    app.register_blueprint(sync_bp, url_prefix='/api/sync')
    app.register_blueprint(books_bp, url_prefix='/api/books')
    app.register_blueprint(news_bp, url_prefix='/api/news')
    
    # Health check endpoint for Cloud Run
    @app.route('/health')
    def health_check():
        """Health check endpoint for Cloud Run load balancer"""
        return jsonify({
            'status': 'healthy',
            'service': 'kindle-content-server',
            'version': os.getenv('SERVICE_VERSION', '1.0.0')
        }), 200
    
    # Root endpoint
    @app.route('/')
    def root():
        """Root endpoint with service information"""
        return jsonify({
            'service': 'Kindle Content Server Backend',
            'version': os.getenv('SERVICE_VERSION', '1.0.0'),
            'endpoints': ['/api/sync', '/api/books', '/api/news'],
            'health': '/health'
        })
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Endpoint not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500
    
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
    # Development server - Cloud Run uses Gunicorn in production
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
"""
Books API endpoints
Handles book management operations
"""

from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import logging
import os

from models import db, Book, SyncLog
from services.book_manager import BookManager
from utils.file_handler import FileHandler

books_bp = Blueprint('books', __name__)
logger = logging.getLogger(__name__)

@books_bp.route('/', methods=['GET'])
def list_books():
    """List books with optional filtering and pagination"""
    try:
        # Query parameters
        search = request.args.get('search')
        genre = request.args.get('genre')
        author = request.args.get('author')
        format_filter = request.args.get('format')
        status = request.args.get('status')
        limit = min(int(request.args.get('limit', 50)), 100)  # Max 100
        offset = int(request.args.get('offset', 0))
        sort_by = request.args.get('sort_by', 'created_at')
        order = request.args.get('order', 'desc')
        
        # Build query
        query = Book.query
        
        # Apply filters
        if search:
            books = Book.search(search, limit=limit)
            total_count = len(books)
        else:
            if genre:
                query = query.filter(Book.genre == genre)
            
            if author:
                query = query.filter(Book.author.ilike(f'%{author}%'))
            
            if format_filter:
                query = query.filter(Book.format == format_filter.upper())
            
            if status:
                query = query.filter(Book.status == status)
            
            # Apply sorting
            if sort_by == 'title':
                sort_field = Book.title
            elif sort_by == 'author':
                sort_field = Book.author
            elif sort_by == 'updated_at':
                sort_field = Book.updated_at
            else:
                sort_field = Book.created_at
            
            if order == 'desc':
                sort_field = sort_field.desc()
            
            query = query.order_by(sort_field)
            
            # Get total count
            total_count = query.count()
            
            # Apply pagination
            books = query.offset(offset).limit(limit).all()
        
        return jsonify({
            'books': [book.to_dict() for book in books],
            'pagination': {
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total_count
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing books: {e}")
        return jsonify({'error': 'Failed to list books'}), 500

@books_bp.route('/<book_id>', methods=['GET'])
def get_book(book_id):
    """Get specific book details"""
    try:
        book = Book.query.get_or_404(book_id)
        return jsonify(book.to_dict()), 200
        
    except Exception as e:
        logger.error(f"Error getting book {book_id}: {e}")
        return jsonify({'error': 'Failed to get book'}), 500

@books_bp.route('/', methods=['POST'])
def create_book():
    """Create a new book entry"""
    try:
        # Validate request data
        if not request.json:
            return jsonify({'error': 'JSON data required'}), 400
        
        required_fields = ['title', 'author', 'format', 'file_size', 'gcs_path', 'file_hash']
        for field in required_fields:
            if field not in request.json:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Create book
        book_data = request.json
        book = Book(
            title=book_data['title'],
            author=book_data['author'],
            description=book_data.get('description'),
            isbn=book_data.get('isbn'),
            format=book_data['format'].upper(),
            file_size=book_data['file_size'],
            gcs_path=book_data['gcs_path'],
            file_hash=book_data['file_hash'],
            page_count=book_data.get('page_count'),
            word_count=book_data.get('word_count'),
            language=book_data.get('language', 'en'),
            publisher=book_data.get('publisher'),
            publication_date=datetime.fromisoformat(book_data['publication_date']) if book_data.get('publication_date') else None,
            genre=book_data.get('genre'),
            tags=book_data.get('tags')
        )
        
        db.session.add(book)
        db.session.commit()
        
        logger.info(f"Created new book: {book.title} by {book.author}")
        
        return jsonify({
            'message': 'Book created successfully',
            'book': book.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating book: {e}")
        return jsonify({'error': 'Failed to create book'}), 500

@books_bp.route('/upload', methods=['POST'])
def upload_book():
    """Upload a new book file"""
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get metadata from form
        title = request.form.get('title')
        author = request.form.get('author')
        description = request.form.get('description')
        genre = request.form.get('genre')
        
        if not title or not author:
            return jsonify({'error': 'Title and author are required'}), 400
        
        # Use BookManager to handle upload
        book_manager = BookManager()
        book = book_manager.upload_book(file, title, author, description, genre)
        
        if book:
            return jsonify({
                'message': 'Book uploaded successfully',
                'book': book.to_dict()
            }), 201
        else:
            return jsonify({'error': 'Failed to upload book'}), 500
            
    except Exception as e:
        logger.error(f"Error uploading book: {e}")
        return jsonify({'error': 'Failed to upload book'}), 500

@books_bp.route('/<book_id>', methods=['PUT'])
def update_book(book_id):
    """Update book metadata"""
    try:
        book = Book.query.get_or_404(book_id)
        
        if not request.json:
            return jsonify({'error': 'JSON data required'}), 400
        
        # Update allowed fields
        allowed_fields = [
            'title', 'author', 'description', 'isbn', 'genre', 'tags',
            'language', 'publisher', 'publication_date', 'reading_progress',
            'last_read_position'
        ]
        
        for field in allowed_fields:
            if field in request.json:
                if field == 'publication_date' and request.json[field]:
                    setattr(book, field, datetime.fromisoformat(request.json[field]))
                else:
                    setattr(book, field, request.json[field])
        
        book.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Updated book: {book.title}")
        
        return jsonify({
            'message': 'Book updated successfully',
            'book': book.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating book {book_id}: {e}")
        return jsonify({'error': 'Failed to update book'}), 500

@books_bp.route('/<book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book"""
    try:
        book = Book.query.get_or_404(book_id)
        
        # Use BookManager to handle deletion (includes file cleanup)
        book_manager = BookManager()
        success = book_manager.delete_book(book)
        
        if success:
            return jsonify({'message': 'Book deleted successfully'}), 200
        else:
            return jsonify({'error': 'Failed to delete book'}), 500
            
    except Exception as e:
        logger.error(f"Error deleting book {book_id}: {e}")
        return jsonify({'error': 'Failed to delete book'}), 500

@books_bp.route('/<book_id>/download', methods=['GET'])
def download_book(book_id):
    """Get download URL for a book"""
    try:
        book = Book.query.get_or_404(book_id)
        
        # Use BookManager to generate download URL
        book_manager = BookManager()
        download_url = book_manager.get_download_url(book)
        
        if download_url:
            return jsonify({
                'download_url': download_url,
                'filename': f"{book.title}.{book.format.lower()}",
                'expires_at': (datetime.utcnow() + timedelta(hours=1)).isoformat()
            }), 200
        else:
            return jsonify({'error': 'Failed to generate download URL'}), 500
            
    except Exception as e:
        logger.error(f"Error getting download URL for book {book_id}: {e}")
        return jsonify({'error': 'Failed to get download URL'}), 500

@books_bp.route('/<book_id>/progress', methods=['PUT'])
def update_reading_progress(book_id):
    """Update reading progress for a book"""
    try:
        book = Book.query.get_or_404(book_id)
        
        if not request.json or 'progress' not in request.json:
            return jsonify({'error': 'Progress value required'}), 400
        
        progress = float(request.json['progress'])
        position = request.json.get('position')
        
        # Validate progress
        if not 0.0 <= progress <= 1.0:
            return jsonify({'error': 'Progress must be between 0.0 and 1.0'}), 400
        
        book.update_reading_progress(progress, position)
        
        return jsonify({
            'message': 'Reading progress updated',
            'progress': book.reading_progress,
            'position': book.last_read_position
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating reading progress for book {book_id}: {e}")
        return jsonify({'error': 'Failed to update reading progress'}), 500

@books_bp.route('/stats', methods=['GET'])
def get_book_stats():
    """Get book collection statistics"""
    try:
        stats = {
            'total_books': Book.query.count(),
            'by_format': dict(db.session.query(Book.format, db.func.count(Book.id)).group_by(Book.format).all()),
            'by_genre': dict(db.session.query(Book.genre, db.func.count(Book.id))
                           .filter(Book.genre.isnot(None))
                           .group_by(Book.genre).all()),
            'by_status': dict(db.session.query(Book.status, db.func.count(Book.id)).group_by(Book.status).all()),
            'by_sync_status': dict(db.session.query(Book.sync_status, db.func.count(Book.id)).group_by(Book.sync_status).all()),
            'total_file_size': db.session.query(db.func.sum(Book.file_size)).scalar() or 0,
            'recent_books': len(Book.get_recent(limit=10))
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error getting book stats: {e}")
        return jsonify({'error': 'Failed to get book stats'}), 500

@books_bp.route('/recent', methods=['GET'])
def get_recent_books():
    """Get recently added books"""
    try:
        limit = min(int(request.args.get('limit', 20)), 100)
        books = Book.get_recent(limit=limit)
        
        return jsonify({
            'books': [book.to_dict() for book in books]
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting recent books: {e}")
        return jsonify({'error': 'Failed to get recent books'}), 500

@books_bp.route('/genres', methods=['GET'])
def get_genres():
    """Get list of available genres"""
    try:
        genres = db.session.query(Book.genre)\
                          .filter(Book.genre.isnot(None))\
                          .distinct().all()
        
        genre_list = [genre[0] for genre in genres]
        
        return jsonify({'genres': sorted(genre_list)}), 200
        
    except Exception as e:
        logger.error(f"Error getting genres: {e}")
        return jsonify({'error': 'Failed to get genres'}), 500

@books_bp.route('/<book_id>/sync', methods=['POST'])
def mark_for_sync(book_id):
    """Mark a book for Kindle sync"""
    try:
        book = Book.query.get_or_404(book_id)
        book.mark_for_sync()
        
        return jsonify({
            'message': 'Book marked for sync',
            'book_id': str(book.id),
            'sync_status': book.sync_status
        }), 200
        
    except Exception as e:
        logger.error(f"Error marking book {book_id} for sync: {e}")
        return jsonify({'error': 'Failed to mark book for sync'}), 500
"""
Validation utilities for API requests
"""

import jsonschema
from jsonschema import validate, ValidationError
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def validate_json_schema(data: Any, schema: Dict) -> bool:
    """
    Validate JSON data against a schema
    
    Args:
        data: Data to validate
        schema: JSON schema to validate against
        
    Returns:
        True if valid, False otherwise
    """
    try:
        validate(instance=data, schema=schema)
        return True
    except ValidationError as e:
        logger.warning(f"Schema validation failed: {e.message}")
        return False
    except Exception as e:
        logger.error(f"Unexpected validation error: {e}")
        return False


def validate_url(url: str) -> bool:
    """
    Validate URL format
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid URL, False otherwise
    """
    try:
        from urllib.parse import urlparse
        result = urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except Exception:
        return False


def validate_email(email: str) -> bool:
    """
    Validate email format
    
    Args:
        email: Email to validate
        
    Returns:
        True if valid email, False otherwise
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent directory traversal and other issues
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    import re
    import os
    
    # Remove path components
    filename = os.path.basename(filename)
    
    # Remove dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove control characters
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    
    return filename


def validate_rss_feed_config(config: Dict) -> tuple[bool, Optional[str]]:
    """
    Validate RSS feed configuration
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Required fields
        if 'url' not in config:
            return False, "URL is required"
        
        if not validate_url(config['url']):
            return False, "Invalid URL format"
        
        # Optional field validation
        if 'max_articles' in config:
            max_articles = config['max_articles']
            if not isinstance(max_articles, int) or max_articles < 1 or max_articles > 100:
                return False, "max_articles must be an integer between 1 and 100"
        
        if 'timeout' in config:
            timeout = config['timeout']
            if not isinstance(timeout, int) or timeout < 5 or timeout > 120:
                return False, "timeout must be an integer between 5 and 120"
        
        if 'quality_threshold' in config:
            quality_threshold = config['quality_threshold']
            if not isinstance(quality_threshold, (int, float)) or quality_threshold < 0 or quality_threshold > 1:
                return False, "quality_threshold must be a number between 0 and 1"
        
        if 'update_frequency' in config:
            update_frequency = config['update_frequency']
            if update_frequency not in ['hourly', 'daily', 'weekly']:
                return False, "update_frequency must be 'hourly', 'daily', or 'weekly'"
        
        if 'content_filters' in config:
            content_filters = config['content_filters']
            if not isinstance(content_filters, list):
                return False, "content_filters must be a list"
            
            for filter_item in content_filters:
                if not isinstance(filter_item, str):
                    return False, "content_filters must contain only strings"
        
        if 'retry_count' in config:
            retry_count = config['retry_count']
            if not isinstance(retry_count, int) or retry_count < 1 or retry_count > 5:
                return False, "retry_count must be an integer between 1 and 5"
        
        return True, None
        
    except Exception as e:
        logger.error(f"Error validating RSS feed config: {e}")
        return False, f"Validation error: {str(e)}"


def validate_news_source_data(data: Dict) -> tuple[bool, Optional[str]]:
    """
    Validate news source data
    
    Args:
        data: News source data dictionary
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Required fields
        required_fields = ['name', 'url']
        for field in required_fields:
            if field not in data:
                return False, f"{field} is required"
            
            if not isinstance(data[field], str) or not data[field].strip():
                return False, f"{field} must be a non-empty string"
        
        # Validate URL
        if not validate_url(data['url']):
            return False, "Invalid URL format"
        
        # Validate name length
        if len(data['name']) > 100:
            return False, "Name must be 100 characters or less"
        
        # Optional fields
        if 'category' in data:
            if not isinstance(data['category'], str) or len(data['category']) > 50:
                return False, "Category must be a string of 50 characters or less"
        
        if 'syncFrequency' in data:
            if data['syncFrequency'] not in ['hourly', 'daily', 'weekly']:
                return False, "syncFrequency must be 'hourly', 'daily', or 'weekly'"
        
        if 'isActive' in data:
            if not isinstance(data['isActive'], bool):
                return False, "isActive must be a boolean"
        
        return True, None
        
    except Exception as e:
        logger.error(f"Error validating news source data: {e}")
        return False, f"Validation error: {str(e)}"


def validate_book_upload_data(data: Dict) -> tuple[bool, Optional[str]]:
    """
    Validate book upload data
    
    Args:
        data: Book upload data dictionary
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Optional fields with validation
        if 'title' in data:
            if not isinstance(data['title'], str) or len(data['title']) > 500:
                return False, "Title must be a string of 500 characters or less"
        
        if 'author' in data:
            if not isinstance(data['author'], str) or len(data['author']) > 200:
                return False, "Author must be a string of 200 characters or less"
        
        if 'category' in data:
            if not isinstance(data['category'], str) or len(data['category']) > 100:
                return False, "Category must be a string of 100 characters or less"
        
        if 'description' in data:
            if not isinstance(data['description'], str) or len(data['description']) > 2000:
                return False, "Description must be a string of 2000 characters or less"
        
        return True, None
        
    except Exception as e:
        logger.error(f"Error validating book upload data: {e}")
        return False, f"Validation error: {str(e)}"


def validate_pagination_params(offset: int, limit: int) -> tuple[bool, Optional[str]]:
    """
    Validate pagination parameters
    
    Args:
        offset: Pagination offset
        limit: Pagination limit
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        if not isinstance(offset, int) or offset < 0:
            return False, "Offset must be a non-negative integer"
        
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            return False, "Limit must be an integer between 1 and 100"
        
        return True, None
        
    except Exception as e:
        logger.error(f"Error validating pagination params: {e}")
        return False, f"Validation error: {str(e)}"
"""
RSS Feed Testing and Validation Service
Tests RSS feeds before saving and provides configuration options
"""

import feedparser
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from urllib.parse import urlparse, urljoin
import time
import html2text
import re
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class FeedHealthStatus(Enum):
    """RSS Feed health status"""
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    TIMEOUT = "timeout"
    INVALID = "invalid"


@dataclass
class FeedTestResult:
    """Result of RSS feed testing"""
    url: str
    status: FeedHealthStatus
    success: bool
    title: str
    description: str
    article_count: int
    last_updated: Optional[datetime]
    error_message: Optional[str]
    warnings: List[str]
    metadata: Dict
    test_duration: float
    sample_articles: List[Dict]


@dataclass
class FeedConfiguration:
    """Configuration options for RSS feeds"""
    max_articles: int = 10
    content_extraction: bool = True
    include_images: bool = False
    custom_headers: Dict[str, str] = None
    timeout: int = 30
    retry_count: int = 3
    content_filters: List[str] = None  # Keywords to filter content
    category_mapping: Dict[str, str] = None  # Custom category mapping
    quality_threshold: float = 0.3
    update_frequency: str = "daily"  # daily, hourly, weekly


class RSSFeedTester:
    """Service for testing and validating RSS feeds"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Kindle Content Server/1.0 RSS Feed Tester (+https://kindle-content-server.com/bot)'
        })
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = True
    
    def test_feed(self, url: str, config: FeedConfiguration = None) -> FeedTestResult:
        """
        Test an RSS feed comprehensively
        
        Args:
            url: RSS feed URL to test
            config: Optional configuration for testing
            
        Returns:
            FeedTestResult with comprehensive test results
        """
        if config is None:
            config = FeedConfiguration()
        
        start_time = time.time()
        warnings = []
        
        try:
            # Step 1: Basic URL validation
            if not self._validate_url(url):
                return FeedTestResult(
                    url=url,
                    status=FeedHealthStatus.INVALID,
                    success=False,
                    title="",
                    description="",
                    article_count=0,
                    last_updated=None,
                    error_message="Invalid URL format",
                    warnings=[],
                    metadata={},
                    test_duration=time.time() - start_time,
                    sample_articles=[]
                )
            
            # Step 2: Fetch feed with custom headers and timeout
            headers = config.custom_headers or {}
            response = self.session.get(
                url, 
                timeout=config.timeout,
                headers=headers
            )
            response.raise_for_status()
            
            # Step 3: Parse feed
            feed = feedparser.parse(response.content)
            
            # Step 4: Validate feed structure
            if feed.bozo:
                warnings.append(f"Feed parsing warning: {feed.bozo_exception}")
            
            if not hasattr(feed, 'feed') or not hasattr(feed, 'entries'):
                return FeedTestResult(
                    url=url,
                    status=FeedHealthStatus.ERROR,
                    success=False,
                    title="",
                    description="",
                    article_count=0,
                    last_updated=None,
                    error_message="Invalid RSS feed structure",
                    warnings=warnings,
                    metadata={},
                    test_duration=time.time() - start_time,
                    sample_articles=[]
                )
            
            # Step 5: Extract feed metadata
            feed_title = getattr(feed.feed, 'title', self._extract_domain(url))
            feed_description = getattr(feed.feed, 'description', '')
            feed_updated = self._extract_feed_updated(feed.feed)
            
            # Step 6: Test articles
            articles = []
            article_count = len(feed.entries)
            
            # Process sample articles (up to config.max_articles)
            for i, entry in enumerate(feed.entries[:config.max_articles]):
                article_result = self._test_article(entry, config)
                if article_result:
                    articles.append(article_result)
            
            # Step 7: Determine overall health status
            status = self._determine_feed_status(feed, articles, warnings)
            
            # Step 8: Generate metadata
            metadata = self._generate_metadata(feed, response, config)
            
            return FeedTestResult(
                url=url,
                status=status,
                success=True,
                title=feed_title,
                description=feed_description,
                article_count=article_count,
                last_updated=feed_updated,
                error_message=None,
                warnings=warnings,
                metadata=metadata,
                test_duration=time.time() - start_time,
                sample_articles=articles
            )
            
        except requests.exceptions.Timeout:
            return FeedTestResult(
                url=url,
                status=FeedHealthStatus.TIMEOUT,
                success=False,
                title="",
                description="",
                article_count=0,
                last_updated=None,
                error_message=f"Request timeout after {config.timeout} seconds",
                warnings=warnings,
                metadata={},
                test_duration=time.time() - start_time,
                sample_articles=[]
            )
        except requests.exceptions.RequestException as e:
            return FeedTestResult(
                url=url,
                status=FeedHealthStatus.ERROR,
                success=False,
                title="",
                description="",
                article_count=0,
                last_updated=None,
                error_message=f"HTTP error: {str(e)}",
                warnings=warnings,
                metadata={},
                test_duration=time.time() - start_time,
                sample_articles=[]
            )
        except Exception as e:
            return FeedTestResult(
                url=url,
                status=FeedHealthStatus.ERROR,
                success=False,
                title="",
                description="",
                article_count=0,
                last_updated=None,
                error_message=f"Unexpected error: {str(e)}",
                warnings=warnings,
                metadata={},
                test_duration=time.time() - start_time,
                sample_articles=[]
            )
    
    def test_multiple_feeds(self, urls: List[str], config: FeedConfiguration = None) -> List[FeedTestResult]:
        """Test multiple RSS feeds"""
        results = []
        for url in urls:
            result = self.test_feed(url, config)
            results.append(result)
        return results
    
    def validate_feed_before_save(self, url: str, config: FeedConfiguration = None) -> Tuple[bool, str, Dict]:
        """
        Validate RSS feed before saving to database
        
        Args:
            url: RSS feed URL
            config: Configuration for testing
            
        Returns:
            Tuple of (is_valid, error_message, metadata)
        """
        result = self.test_feed(url, config)
        
        if not result.success:
            return False, result.error_message, {}
        
        # Additional validation criteria for saving
        if result.article_count == 0:
            return False, "Feed contains no articles", {}
        
        if result.status == FeedHealthStatus.ERROR:
            return False, "Feed failed health check", {}
        
        # Check if feed is too old
        if result.last_updated and result.last_updated < datetime.utcnow() - timedelta(days=30):
            return False, "Feed appears to be inactive (no updates in 30 days)", {}
        
        return True, "", result.metadata
    
    def get_feed_suggestions(self, url: str) -> List[str]:
        """
        Get suggestions for RSS feed URLs based on website URL
        
        Args:
            url: Website URL
            
        Returns:
            List of potential RSS feed URLs
        """
        suggestions = []
        
        try:
            # Common RSS feed paths
            common_paths = [
                '/rss',
                '/rss.xml',
                '/feed',
                '/feed.xml',
                '/feeds/all.atom.xml',
                '/atom.xml',
                '/index.xml',
                '/rss/index.xml',
                '/feed/index.xml'
            ]
            
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            for path in common_paths:
                suggestion = urljoin(base_url, path)
                suggestions.append(suggestion)
            
            # Try to find RSS feeds in HTML
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                
                # Look for RSS/Atom feed links in HTML
                html_content = response.text
                feed_patterns = [
                    r'<link[^>]*type=["\']application/rss\+xml["\'][^>]*href=["\']([^"\']*)["\']',
                    r'<link[^>]*type=["\']application/atom\+xml["\'][^>]*href=["\']([^"\']*)["\']',
                    r'<link[^>]*href=["\']([^"\']*)["\'][^>]*type=["\']application/rss\+xml["\']',
                    r'<link[^>]*href=["\']([^"\']*)["\'][^>]*type=["\']application/atom\+xml["\']'
                ]
                
                for pattern in feed_patterns:
                    matches = re.finditer(pattern, html_content, re.IGNORECASE)
                    for match in matches:
                        feed_url = match.group(1)
                        if feed_url.startswith('/'):
                            feed_url = urljoin(base_url, feed_url)
                        suggestions.append(feed_url)
                        
            except Exception as e:
                logger.warning(f"Could not parse HTML for RSS suggestions: {e}")
            
        except Exception as e:
            logger.error(f"Error generating RSS suggestions: {e}")
        
        # Remove duplicates and return
        return list(set(suggestions))
    
    def _validate_url(self, url: str) -> bool:
        """Validate URL format"""
        try:
            result = urlparse(url)
            return all([result.scheme in ['http', 'https'], result.netloc])
        except:
            return False
    
    def _test_article(self, entry, config: FeedConfiguration) -> Optional[Dict]:
        """Test a single article entry"""
        try:
            # Extract basic information
            title = entry.get('title', '').strip()
            if not title:
                return None
            
            # Extract content
            content = self._extract_content(entry)
            if not content:
                return None
            
            # Extract metadata
            author = self._extract_author(entry)
            published_at = self._extract_published_date(entry)
            category = self._extract_category(entry)
            source_url = entry.get('link', '')
            
            # Calculate metrics
            word_count = len(content.split())
            estimated_reading_time = max(1, word_count // 200)  # 200 words per minute
            
            # Apply content filters if configured
            if config.content_filters:
                content_lower = content.lower()
                for filter_term in config.content_filters:
                    if filter_term.lower() in content_lower:
                        return None  # Filtered out
            
            # Calculate quality score
            quality_score = self._calculate_article_quality(title, content, author, word_count)
            
            # Check quality threshold
            if quality_score < config.quality_threshold:
                return None
            
            return {
                'title': title,
                'content': content[:500] + '...' if len(content) > 500 else content,  # Truncate for testing
                'author': author,
                'published_at': published_at.isoformat() if published_at else None,
                'category': category,
                'source_url': source_url,
                'word_count': word_count,
                'reading_time': estimated_reading_time,
                'quality_score': quality_score
            }
            
        except Exception as e:
            logger.error(f"Error testing article: {e}")
            return None
    
    def _extract_content(self, entry) -> str:
        """Extract and clean article content"""
        content_fields = ['content', 'summary', 'description']
        
        for field in content_fields:
            if hasattr(entry, field):
                content_data = getattr(entry, field)
                
                if isinstance(content_data, list) and content_data:
                    content_html = content_data[0].get('value', '')
                elif isinstance(content_data, str):
                    content_html = content_data
                else:
                    continue
                
                if content_html:
                    clean_content = self._clean_html_to_text(content_html)
                    if clean_content:
                        return clean_content
        
        return ''
    
    def _clean_html_to_text(self, html_content: str) -> str:
        """Clean HTML content and convert to readable text"""
        try:
            # Remove problematic HTML elements/attributes that cause "Unknown Operation"
            html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            html_content = re.sub(r'<noscript[^>]*>.*?</noscript>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            
            # Remove common problematic attributes
            html_content = re.sub(r'\s(onclick|onload|onerror|onmouseover|onmouseout)="[^"]*"', '', html_content, flags=re.IGNORECASE)
            html_content = re.sub(r'\s(onclick|onload|onerror|onmouseover|onmouseout)=\'[^\']*\'', '', html_content, flags=re.IGNORECASE)
            
            # Remove data attributes that might cause issues
            html_content = re.sub(r'\sdata-[a-zA-Z0-9-]+="[^"]*"', '', html_content)
            html_content = re.sub(r'\sdata-[a-zA-Z0-9-]+=\'[^\']*\'', '', html_content)
            
            # Convert HTML to clean text
            clean_content = self.html_converter.handle(html_content)
            
            # Remove "Unknown Operation" and similar artifacts
            clean_content = re.sub(r'Unknown Operation', '', clean_content, flags=re.IGNORECASE)
            clean_content = re.sub(r'\[Unknown[^\]]*\]', '', clean_content, flags=re.IGNORECASE)
            
            # Clean up whitespace
            clean_content = re.sub(r'\n\s*\n', '\n\n', clean_content.strip())
            clean_content = re.sub(r'\n{3,}', '\n\n', clean_content)
            
            return clean_content.strip()
            
        except Exception as e:
            logger.warning(f"Error cleaning HTML content: {e}")
            # Fallback: try to extract plain text from HTML
            try:
                import html
                # Remove all HTML tags and decode entities
                text_content = re.sub(r'<[^>]+>', '', html_content)
                text_content = html.unescape(text_content)
                text_content = re.sub(r'\s+', ' ', text_content.strip())
                return text_content
            except:
                return ''
    
    def _extract_author(self, entry) -> Optional[str]:
        """Extract author from entry"""
        if hasattr(entry, 'author') and entry.author:
            return entry.author.strip()
        
        if hasattr(entry, 'author_detail') and entry.author_detail:
            return entry.author_detail.get('name', '').strip()
        
        return None
    
    def _extract_published_date(self, entry) -> Optional[datetime]:
        """Extract published date from entry"""
        date_fields = ['published_parsed', 'updated_parsed']
        
        for field in date_fields:
            if hasattr(entry, field):
                date_tuple = getattr(entry, field)
                if date_tuple:
                    try:
                        return datetime(*date_tuple[:6])
                    except (TypeError, ValueError):
                        continue
        
        return None
    
    def _extract_category(self, entry) -> Optional[str]:
        """Extract category from entry"""
        if hasattr(entry, 'tags') and entry.tags:
            if entry.tags and len(entry.tags) > 0:
                return entry.tags[0].get('term', '').strip()
        
        if hasattr(entry, 'category') and entry.category:
            return entry.category.strip()
        
        return None
    
    def _extract_feed_updated(self, feed) -> Optional[datetime]:
        """Extract feed last updated date"""
        if hasattr(feed, 'updated_parsed') and feed.updated_parsed:
            try:
                return datetime(*feed.updated_parsed[:6])
            except (TypeError, ValueError):
                pass
        
        return None
    
    def _calculate_article_quality(self, title: str, content: str, author: str, word_count: int) -> float:
        """Calculate article quality score"""
        score = 0.5  # Base score
        
        # Title quality
        if title and len(title.strip()) > 10:
            score += 0.1
        
        # Content length
        if 100 <= word_count <= 2000:
            score += 0.2
        elif word_count > 2000:
            score += 0.1
        
        # Has author
        if author and len(author.strip()) > 0:
            score += 0.1
        
        # Content quality (basic checks)
        if content:
            # Check for duplicate content patterns
            sentences = content.split('.')
            if len(sentences) > 3:
                score += 0.1
        
        return min(1.0, score)
    
    def _determine_feed_status(self, feed, articles: List[Dict], warnings: List[str]) -> FeedHealthStatus:
        """Determine overall feed health status"""
        if not articles:
            return FeedHealthStatus.ERROR
        
        if len(warnings) > 0:
            return FeedHealthStatus.WARNING
        
        # Check article quality
        avg_quality = sum(article['quality_score'] for article in articles) / len(articles)
        if avg_quality < 0.4:
            return FeedHealthStatus.WARNING
        
        return FeedHealthStatus.HEALTHY
    
    def _generate_metadata(self, feed, response, config: FeedConfiguration) -> Dict:
        """Generate metadata about the feed"""
        metadata = {
            'feed_format': 'rss' if 'rss' in response.headers.get('content-type', '').lower() else 'atom',
            'content_type': response.headers.get('content-type', ''),
            'content_length': response.headers.get('content-length', ''),
            'server': response.headers.get('server', ''),
            'cache_control': response.headers.get('cache-control', ''),
            'etag': response.headers.get('etag', ''),
            'last_modified': response.headers.get('last-modified', ''),
            'encoding': getattr(feed, 'encoding', ''),
            'bozo': getattr(feed, 'bozo', False),
            'bozo_exception': str(getattr(feed, 'bozo_exception', '')),
            'generator': getattr(feed.feed, 'generator', ''),
            'language': getattr(feed.feed, 'language', ''),
            'ttl': getattr(feed.feed, 'ttl', ''),
            'config_used': {
                'max_articles': config.max_articles,
                'timeout': config.timeout,
                'quality_threshold': config.quality_threshold
            }
        }
        
        return metadata
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain name from URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain.replace('.', ' ').title()
        except:
            return 'Unknown Source'
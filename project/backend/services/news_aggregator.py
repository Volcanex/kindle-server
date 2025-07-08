"""
News Aggregator Service
Handles RSS feed aggregation and content processing
"""

import feedparser
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import hashlib
import html2text
from urllib.parse import urljoin, urlparse
import re

from models import db, NewsItem
from config.settings import Config

logger = logging.getLogger(__name__)

class NewsAggregator:
    """Service for aggregating news from RSS feeds"""
    
    def __init__(self):
        self.feeds = Config.RSS_FEEDS
        self.max_articles_per_feed = Config.RSS_MAX_ARTICLES_PER_FEED
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Kindle Content Server/1.0 (+https://kindle-content-server.com/bot)'
        })
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = True
    
    def aggregate_all_feeds(self, force_refresh: bool = False, max_articles_per_feed: int = None) -> Dict:
        """
        Aggregate content from all configured RSS feeds
        
        Args:
            force_refresh: If True, ignore cache and fetch fresh content
            max_articles_per_feed: Override default max articles per feed
            
        Returns:
            Dictionary with aggregation results
        """
        if max_articles_per_feed is None:
            max_articles_per_feed = self.max_articles_per_feed
        
        results = {
            'feeds_processed': 0,
            'articles_found': 0,
            'articles_added': 0,
            'articles_updated': 0,
            'errors': []
        }
        
        for feed_url in self.feeds:
            try:
                logger.info(f"Processing feed: {feed_url}")
                feed_result = self.aggregate_feed(feed_url, force_refresh, max_articles_per_feed)
                
                results['feeds_processed'] += 1
                results['articles_found'] += feed_result['articles_found']
                results['articles_added'] += feed_result['articles_added']
                results['articles_updated'] += feed_result['articles_updated']
                
            except Exception as e:
                error_msg = f"Error processing feed {feed_url}: {str(e)}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
        
        # Process new articles
        self.process_new_articles()
        
        logger.info(f"Aggregation completed: {results}")
        return results
    
    def aggregate_feed(self, feed_url: str, force_refresh: bool = False, max_articles: int = None) -> Dict:
        """
        Aggregate content from a single RSS feed
        
        Args:
            feed_url: URL of the RSS feed
            force_refresh: If True, ignore cache and fetch fresh content
            max_articles: Maximum number of articles to process
            
        Returns:
            Dictionary with feed processing results
        """
        if max_articles is None:
            max_articles = self.max_articles_per_feed
        
        result = {
            'articles_found': 0,
            'articles_added': 0,
            'articles_updated': 0
        }
        
        try:
            # Fetch and parse feed
            logger.info(f"Fetching feed: {feed_url}")
            response = self.session.get(feed_url, timeout=30)
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            
            if feed.bozo and feed.bozo_exception:
                logger.warning(f"Feed parsing warning for {feed_url}: {feed.bozo_exception}")
            
            # Get feed metadata
            feed_title = getattr(feed.feed, 'title', self._extract_domain(feed_url))
            feed_description = getattr(feed.feed, 'description', '')
            
            # Process articles
            articles_processed = 0
            for entry in feed.entries:
                if articles_processed >= max_articles:
                    break
                
                try:
                    article_result = self.process_article(entry, feed_url, feed_title)
                    if article_result == 'added':
                        result['articles_added'] += 1
                    elif article_result == 'updated':
                        result['articles_updated'] += 1
                    
                    result['articles_found'] += 1
                    articles_processed += 1
                    
                except Exception as e:
                    logger.error(f"Error processing article from {feed_url}: {e}")
                    continue
            
            logger.info(f"Processed {articles_processed} articles from {feed_title}")
            
        except Exception as e:
            logger.error(f"Error fetching feed {feed_url}: {e}")
            raise
        
        return result
    
    def process_article(self, entry, feed_url: str, source_name: str) -> str:
        """
        Process a single article entry from RSS feed
        
        Args:
            entry: Feedparser entry object
            feed_url: URL of the RSS feed
            source_name: Name of the news source
            
        Returns:
            'added', 'updated', or 'skipped'
        """
        # Extract article data
        title = entry.get('title', '').strip()
        if not title:
            return 'skipped'
        
        # Generate GUID for deduplication
        guid = entry.get('id') or entry.get('link') or title
        guid_hash = hashlib.md5(f"{feed_url}:{guid}".encode()).hexdigest()
        
        # Check if article already exists
        existing_article = NewsItem.query.filter_by(guid=guid_hash).first()
        
        # Extract content
        content = self._extract_content(entry)
        summary = self._extract_summary(entry, content)
        
        # Extract metadata
        author = self._extract_author(entry)
        published_at = self._extract_published_date(entry)
        category = self._extract_category(entry)
        source_url = entry.get('link', '')
        
        # Calculate word count
        word_count = len(content.split()) if content else 0
        
        if existing_article:
            # Update existing article if content has changed
            if (existing_article.content != content or 
                existing_article.title != title):
                
                existing_article.title = title
                existing_article.content = content
                existing_article.summary = summary
                existing_article.author = author
                existing_article.word_count = word_count
                existing_article.updated_at = datetime.utcnow()
                
                db.session.commit()
                return 'updated'
            else:
                return 'skipped'
        else:
            # Create new article
            news_item = NewsItem(
                title=title,
                content=content,
                summary=summary,
                source_name=source_name,
                source_url=source_url,
                feed_url=feed_url,
                author=author,
                category=category,
                published_at=published_at,
                guid=guid_hash,
                word_count=word_count,
                status='pending'
            )
            
            db.session.add(news_item)
            db.session.commit()
            return 'added'
    
    def process_new_articles(self):
        """Process newly added articles to calculate quality scores and reading times"""
        pending_articles = NewsItem.get_pending_processing()
        
        for article in pending_articles:
            try:
                article.process_content()
                
                # Auto-include high-quality articles in EPUB
                if article.quality_score >= 0.7:
                    article.include_in_epub()
                elif article.quality_score < 0.3:
                    article.exclude_from_epub("Low quality score")
                
            except Exception as e:
                logger.error(f"Error processing article {article.id}: {e}")
                continue
        
        db.session.commit()
        logger.info(f"Processed {len(pending_articles)} new articles")
    
    def _extract_content(self, entry) -> str:
        """Extract and clean article content from entry"""
        # Try different content fields in order of preference
        content_fields = ['content', 'summary', 'description']
        
        for field in content_fields:
            if hasattr(entry, field):
                content_data = getattr(entry, field)
                
                if isinstance(content_data, list) and content_data:
                    # Handle content list (usually from content field)
                    content_html = content_data[0].get('value', '')
                elif isinstance(content_data, str):
                    content_html = content_data
                else:
                    continue
                
                if content_html:
                    # Convert HTML to clean text
                    clean_content = self.html_converter.handle(content_html)
                    # Remove excessive whitespace
                    clean_content = re.sub(r'\n\s*\n', '\n\n', clean_content.strip())
                    return clean_content
        
        return ''
    
    def _extract_summary(self, entry, content: str) -> str:
        """Extract or generate article summary"""
        # Try to get explicit summary
        if hasattr(entry, 'summary') and entry.summary:
            summary_html = entry.summary
            summary = self.html_converter.handle(summary_html).strip()
            
            # If summary is too long, truncate it
            if len(summary) > 500:
                summary = summary[:497] + '...'
            
            return summary
        
        # Generate summary from content
        if content:
            sentences = content.split('. ')
            if len(sentences) > 0:
                # Take first 2-3 sentences as summary
                summary_sentences = sentences[:min(3, len(sentences))]
                summary = '. '.join(summary_sentences)
                
                if len(summary) > 500:
                    summary = summary[:497] + '...'
                
                return summary
        
        return ''
    
    def _extract_author(self, entry) -> Optional[str]:
        """Extract author from entry"""
        # Try different author fields
        if hasattr(entry, 'author') and entry.author:
            return entry.author.strip()
        
        if hasattr(entry, 'author_detail') and entry.author_detail:
            return entry.author_detail.get('name', '').strip()
        
        if hasattr(entry, 'authors') and entry.authors:
            authors = [author.get('name', '') for author in entry.authors if author.get('name')]
            if authors:
                return ', '.join(authors[:2])  # Max 2 authors
        
        return None
    
    def _extract_published_date(self, entry) -> datetime:
        """Extract published date from entry"""
        # Try different date fields
        date_fields = ['published_parsed', 'updated_parsed']
        
        for field in date_fields:
            if hasattr(entry, field):
                date_tuple = getattr(entry, field)
                if date_tuple:
                    try:
                        return datetime(*date_tuple[:6])
                    except (TypeError, ValueError):
                        continue
        
        # Fallback to current time
        return datetime.utcnow()
    
    def _extract_category(self, entry) -> Optional[str]:
        """Extract category/tags from entry"""
        if hasattr(entry, 'tags') and entry.tags:
            # Get first tag as category
            if entry.tags and len(entry.tags) > 0:
                return entry.tags[0].get('term', '').strip()
        
        if hasattr(entry, 'category') and entry.category:
            return entry.category.strip()
        
        return None
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain name from URL for use as source name"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Capitalize first letter
            return domain.replace('.', ' ').title()
            
        except Exception:
            return 'Unknown Source'
    
    def cleanup_old_articles(self, days: int = 30):
        """
        Clean up old articles that are not included in EPUB
        
        Args:
            days: Number of days to keep articles
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        deleted_count = NewsItem.query.filter(
            NewsItem.created_at < cutoff_date,
            NewsItem.epub_included == False
        ).delete()
        
        db.session.commit()
        
        logger.info(f"Cleaned up {deleted_count} old articles older than {days} days")
        return deleted_count
    
    def get_feed_health(self) -> Dict:
        """
        Check health of all configured RSS feeds
        
        Returns:
            Dictionary with feed health status
        """
        health_status = {
            'healthy_feeds': 0,
            'unhealthy_feeds': 0,
            'feed_status': {}
        }
        
        for feed_url in self.feeds:
            try:
                response = self.session.head(feed_url, timeout=10)
                if response.status_code == 200:
                    health_status['healthy_feeds'] += 1
                    health_status['feed_status'][feed_url] = 'healthy'
                else:
                    health_status['unhealthy_feeds'] += 1
                    health_status['feed_status'][feed_url] = f'error_{response.status_code}'
                    
            except Exception as e:
                health_status['unhealthy_feeds'] += 1
                health_status['feed_status'][feed_url] = f'error_{str(e)[:50]}'
        
        return health_status
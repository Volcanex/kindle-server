"""
Article Sync Manager
Handles syncing articles from RSS feeds based on frequency and storing them for Kindle sync
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy import and_, or_
from sqlalchemy.orm import sessionmaker

from models import db, NewsItem
from services.news_aggregator import NewsAggregator
from services.rss_feed_tester import RSSFeedTester, FeedConfiguration

logger = logging.getLogger(__name__)


class ArticleSyncManager:
    """Manages article syncing from RSS feeds with frequency control"""
    
    def __init__(self):
        self.aggregator = NewsAggregator()
        self.tester = RSSFeedTester()
    
    def should_sync_source(self, source: Dict, force: bool = False) -> bool:
        """
        Determine if a news source should be synced based on frequency and last sync
        
        Args:
            source: News source dictionary with sync frequency and last sync info
            force: If True, sync regardless of frequency
            
        Returns:
            True if source should be synced
        """
        if force:
            return True
        
        if not source.get('isActive', True):
            return False
        
        last_sync = source.get('lastSync')
        if not last_sync:
            return True  # Never synced before
        
        try:
            last_sync_dt = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return True  # Invalid last sync date, sync anyway
        
        now = datetime.utcnow()
        frequency = source.get('syncFrequency', 'daily')
        
        # Calculate next sync time based on frequency
        if frequency == 'hourly':
            next_sync = last_sync_dt + timedelta(hours=1)
        elif frequency == 'daily':
            next_sync = last_sync_dt + timedelta(days=1)
        elif frequency == 'weekly':
            next_sync = last_sync_dt + timedelta(weeks=1)
        elif frequency == 'monthly':
            next_sync = last_sync_dt + timedelta(days=30)
        else:
            next_sync = last_sync_dt + timedelta(days=1)  # Default to daily
        
        return now >= next_sync
    
    def sync_source_articles(self, source: Dict, config: FeedConfiguration = None) -> Dict:
        """
        Sync articles from a single news source
        
        Args:
            source: News source dictionary
            config: Optional RSS feed configuration
            
        Returns:
            Dictionary with sync results
        """
        if config is None:
            # Default configuration based on frequency
            frequency = source.get('syncFrequency', 'daily')
            if frequency == 'hourly':
                max_articles = 5
            elif frequency == 'daily':
                max_articles = 10
            elif frequency == 'weekly':
                max_articles = 20
            else:  # monthly
                max_articles = 30
            
            config = FeedConfiguration(
                max_articles=max_articles,
                timeout=30,
                quality_threshold=0.3
            )
        
        result = {
            'source_id': source.get('id'),
            'source_name': source.get('name'),
            'url': source.get('url'),
            'success': False,
            'articles_added': 0,
            'articles_updated': 0,
            'articles_total': 0,
            'error_message': None,
            'sync_duration': 0,
            'last_sync': None
        }
        
        start_time = datetime.utcnow()
        
        try:
            # Validate feed first
            is_valid, error_message, metadata = self.tester.validate_feed_before_save(
                source['url'], config
            )
            
            if not is_valid:
                result['error_message'] = f"Feed validation failed: {error_message}"
                return result
            
            # Sync articles from this feed
            sync_result = self.aggregator.aggregate_feed(
                source['url'], 
                force_refresh=True, 
                max_articles=config.max_articles
            )
            
            result.update({
                'success': True,
                'articles_added': sync_result['articles_added'],
                'articles_updated': sync_result['articles_updated'],
                'articles_total': sync_result['articles_found'],
                'last_sync': start_time.isoformat()
            })
            
            # Mark articles for kindle sync
            self._mark_articles_for_kindle_sync(source, start_time)
            
        except Exception as e:
            logger.error(f"Error syncing source {source.get('name', 'Unknown')}: {e}")
            result['error_message'] = str(e)
        
        finally:
            result['sync_duration'] = (datetime.utcnow() - start_time).total_seconds()
        
        return result
    
    def sync_all_due_sources(self, sources: List[Dict], force: bool = False) -> Dict:
        """
        Sync all news sources that are due for syncing
        
        Args:
            sources: List of news source dictionaries
            force: If True, sync all sources regardless of frequency
            
        Returns:
            Dictionary with overall sync results
        """
        overall_result = {
            'total_sources': len(sources),
            'sources_synced': 0,
            'sources_skipped': 0,
            'sources_failed': 0,
            'total_articles_added': 0,
            'total_articles_updated': 0,
            'sync_results': [],
            'started_at': datetime.utcnow().isoformat(),
            'completed_at': None,
            'duration': 0
        }
        
        start_time = datetime.utcnow()
        
        for source in sources:
            try:
                if not self.should_sync_source(source, force):
                    overall_result['sources_skipped'] += 1
                    continue
                
                logger.info(f"Syncing source: {source.get('name', 'Unknown')}")
                sync_result = self.sync_source_articles(source)
                overall_result['sync_results'].append(sync_result)
                
                if sync_result['success']:
                    overall_result['sources_synced'] += 1
                    overall_result['total_articles_added'] += sync_result['articles_added']
                    overall_result['total_articles_updated'] += sync_result['articles_updated']
                else:
                    overall_result['sources_failed'] += 1
                
            except Exception as e:
                logger.error(f"Error processing source {source.get('name', 'Unknown')}: {e}")
                overall_result['sources_failed'] += 1
                overall_result['sync_results'].append({
                    'source_id': source.get('id'),
                    'source_name': source.get('name'),
                    'success': False,
                    'error_message': str(e)
                })
        
        overall_result['completed_at'] = datetime.utcnow().isoformat()
        overall_result['duration'] = (datetime.utcnow() - start_time).total_seconds()
        
        return overall_result
    
    def get_articles_for_kindle_sync(self, hours: int = 24) -> List[Dict]:
        """
        Get articles that should be synced to Kindle devices
        
        Args:
            hours: Number of hours to look back for recent articles
            
        Returns:
            List of article dictionaries grouped by source
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Get articles that are:
        # 1. Included in EPUB (marked for sync)
        # 2. Recent (within specified hours)
        # 3. Good quality
        articles = NewsItem.query.filter(
            and_(
                NewsItem.epub_included == True,
                NewsItem.published_at >= cutoff_time,
                NewsItem.quality_score >= 0.3
            )
        ).order_by(
            NewsItem.source_name.asc(),
            NewsItem.published_at.desc()
        ).all()
        
        # Group articles by source
        grouped_articles = {}
        for article in articles:
            source_name = article.source_name
            if source_name not in grouped_articles:
                grouped_articles[source_name] = {
                    'source_name': source_name,
                    'article_count': 0,
                    'articles': []
                }
            
            grouped_articles[source_name]['articles'].append({
                'id': str(article.id),
                'title': article.title,
                'author': article.author,
                'published_at': article.published_at.isoformat(),
                'word_count': article.word_count,
                'reading_time': article.reading_time,
                'quality_score': article.quality_score,
                'summary': article.summary[:200] + '...' if article.summary and len(article.summary) > 200 else article.summary,
                'category': article.category,
                'source_url': article.source_url
            })
            grouped_articles[source_name]['article_count'] += 1
        
        # Convert to list and sort by article count (most articles first)
        result = list(grouped_articles.values())
        result.sort(key=lambda x: x['article_count'], reverse=True)
        
        return result
    
    def _mark_articles_for_kindle_sync(self, source: Dict, sync_time: datetime):
        """
        Mark recently synced articles from this source for Kindle sync
        
        Args:
            source: News source dictionary
            sync_time: Time when sync started
        """
        try:
            # Mark articles from the last hour as ready for sync
            cutoff_time = sync_time - timedelta(hours=1)
            
            articles_to_sync = NewsItem.query.filter(
                and_(
                    NewsItem.source_name == source.get('name'),
                    NewsItem.created_at >= cutoff_time,
                    NewsItem.quality_score >= 0.3,
                    NewsItem.epub_included == False
                )
            ).all()
            
            for article in articles_to_sync:
                article.include_in_epub()
            
            db.session.commit()
            
            if articles_to_sync:
                logger.info(f"Marked {len(articles_to_sync)} articles from {source.get('name')} for Kindle sync")
                
        except Exception as e:
            logger.error(f"Error marking articles for sync: {e}")
            db.session.rollback()
    
    def get_sync_statistics(self) -> Dict:
        """
        Get statistics about article syncing
        
        Returns:
            Dictionary with sync statistics
        """
        now = datetime.utcnow()
        
        # Articles synced in last 24 hours
        last_24h = now - timedelta(hours=24)
        articles_24h = NewsItem.query.filter(
            NewsItem.created_at >= last_24h
        ).count()
        
        # Articles marked for Kindle sync
        articles_for_sync = NewsItem.query.filter(
            NewsItem.epub_included == True
        ).count()
        
        # Articles by source in last 24 hours
        articles_by_source = db.session.query(
            NewsItem.source_name,
            db.func.count(NewsItem.id).label('count')
        ).filter(
            NewsItem.created_at >= last_24h
        ).group_by(NewsItem.source_name).all()
        
        # Quality score distribution
        avg_quality = db.session.query(
            db.func.avg(NewsItem.quality_score)
        ).scalar() or 0
        
        return {
            'articles_last_24h': articles_24h,
            'articles_for_kindle_sync': articles_for_sync,
            'articles_by_source': [
                {'source': source, 'count': count} 
                for source, count in articles_by_source
            ],
            'average_quality_score': round(avg_quality, 2),
            'total_articles': NewsItem.query.count(),
            'sources_with_articles': len(articles_by_source)
        }
    
    def cleanup_old_articles(self, days: int = 30, keep_epub_included: bool = True) -> int:
        """
        Clean up old articles
        
        Args:
            days: Number of days to keep articles
            keep_epub_included: If True, keep articles marked for EPUB even if old
            
        Returns:
            Number of articles deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = NewsItem.query.filter(NewsItem.created_at < cutoff_date)
        
        if keep_epub_included:
            query = query.filter(NewsItem.epub_included == False)
        
        deleted_count = query.delete()
        db.session.commit()
        
        logger.info(f"Cleaned up {deleted_count} old articles older than {days} days")
        return deleted_count
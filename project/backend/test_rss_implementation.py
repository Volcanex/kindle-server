#!/usr/bin/env python3
"""
Test script for RSS feed implementation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.rss_feed_tester import RSSFeedTester, FeedConfiguration
import json

def test_rss_implementation():
    """Test RSS feed implementation with various scenarios"""
    print("🧪 Testing RSS Feed Implementation")
    print("=" * 50)
    
    # Test feeds
    test_feeds = [
        {
            'name': 'BBC News',
            'url': 'https://feeds.bbci.co.uk/news/rss.xml',
            'expected_status': 'healthy'
        },
        {
            'name': 'NPR News',
            'url': 'https://feeds.npr.org/1001/rss.xml',
            'expected_status': 'healthy'
        },
        {
            'name': 'Invalid Feed',
            'url': 'https://invalid-feed-test.com/rss.xml',
            'expected_status': 'error'
        },
        {
            'name': 'Non-RSS URL',
            'url': 'https://www.google.com',
            'expected_status': 'error'
        }
    ]
    
    tester = RSSFeedTester()
    
    # Test with different configurations
    configs = [
        {
            'name': 'Quick Test',
            'config': FeedConfiguration(max_articles=3, timeout=10, quality_threshold=0.1)
        },
        {
            'name': 'Thorough Test',
            'config': FeedConfiguration(max_articles=10, timeout=30, quality_threshold=0.3)
        },
        {
            'name': 'High Quality',
            'config': FeedConfiguration(max_articles=5, timeout=15, quality_threshold=0.7)
        }
    ]
    
    results = []
    
    for config_info in configs:
        print(f"\n🔧 Testing with {config_info['name']} configuration")
        print("-" * 40)
        
        config = config_info['config']
        config_results = []
        
        for feed in test_feeds:
            print(f"Testing: {feed['name']}")
            try:
                result = tester.test_feed(feed['url'], config)
                
                test_result = {
                    'feed_name': feed['name'],
                    'url': feed['url'],
                    'status': result.status.value,
                    'success': result.success,
                    'title': result.title,
                    'article_count': result.article_count,
                    'test_duration': result.test_duration,
                    'error_message': result.error_message,
                    'warnings': result.warnings,
                    'sample_articles': len(result.sample_articles)
                }
                
                config_results.append(test_result)
                
                # Display results
                status_emoji = "✅" if result.success else "❌"
                print(f"  {status_emoji} Status: {result.status.value}")
                print(f"  📊 Articles: {result.article_count}")
                print(f"  ⏱️  Duration: {result.test_duration:.2f}s")
                
                if result.error_message:
                    print(f"  ⚠️  Error: {result.error_message[:100]}...")
                    
                if result.warnings:
                    print(f"  ⚠️  Warnings: {len(result.warnings)}")
                
            except Exception as e:
                print(f"  ❌ Exception: {e}")
                test_result = {
                    'feed_name': feed['name'],
                    'url': feed['url'],
                    'status': 'exception',
                    'success': False,
                    'error_message': str(e)
                }
                config_results.append(test_result)
        
        results.append({
            'config_name': config_info['name'],
            'results': config_results
        })
    
    # Test validation functionality
    print(f"\n🔍 Testing Validation Functionality")
    print("-" * 40)
    
    validation_tests = [
        'https://feeds.bbci.co.uk/news/rss.xml',
        'https://feeds.npr.org/1001/rss.xml',
        'https://invalid-feed-test.com/rss.xml'
    ]
    
    for feed_url in validation_tests:
        print(f"Validating: {feed_url}")
        try:
            is_valid, error_message, metadata = tester.validate_feed_before_save(
                feed_url, 
                FeedConfiguration(max_articles=3, timeout=10, quality_threshold=0.3)
            )
            
            emoji = "✅" if is_valid else "❌"
            print(f"  {emoji} Valid: {is_valid}")
            
            if error_message:
                print(f"  ⚠️  Error: {error_message[:100]}...")
            
            if metadata:
                print(f"  📋 Format: {metadata.get('feed_format', 'unknown')}")
                print(f"  🌐 Language: {metadata.get('language', 'unknown')}")
                
        except Exception as e:
            print(f"  ❌ Exception: {e}")
    
    # Test RSS feed suggestions
    print(f"\n🔍 Testing RSS Feed Suggestions")
    print("-" * 40)
    
    suggestion_tests = [
        'https://www.bbc.com/news',
        'https://www.npr.org',
        'https://www.techcrunch.com'
    ]
    
    for website_url in suggestion_tests:
        print(f"Getting suggestions for: {website_url}")
        try:
            suggestions = tester.get_feed_suggestions(website_url)
            print(f"  📝 Found {len(suggestions)} suggestions")
            for i, suggestion in enumerate(suggestions[:3]):
                print(f"    {i+1}. {suggestion}")
                
        except Exception as e:
            print(f"  ❌ Exception: {e}")
    
    # Summary
    print(f"\n📊 Test Summary")
    print("=" * 50)
    
    total_tests = sum(len(r['results']) for r in results)
    successful_tests = sum(1 for r in results for test in r['results'] if test.get('success', False))
    
    print(f"Total tests: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Failed: {total_tests - successful_tests}")
    print(f"Success rate: {successful_tests/total_tests*100:.1f}%")
    
    return results

if __name__ == "__main__":
    test_rss_implementation()
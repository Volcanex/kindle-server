"""
EPUB Creator Utility
Creates EPUB files from news articles and content
"""

import os
import tempfile
import uuid
from datetime import datetime
from typing import List, Optional
import logging

# EPUB creation libraries
import ebooklib
from ebooklib import epub
import html
import re

from models import NewsItem

logger = logging.getLogger(__name__)

class EpubCreator:
    """Utility class for creating EPUB files"""
    
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
    
    def create_news_digest(self, title: str, articles: List[NewsItem], 
                          author: str = "Kindle Content Server") -> Optional[str]:
        """
        Create an EPUB file from news articles
        
        Args:
            title: Title of the news digest
            articles: List of NewsItem objects
            author: Author name for the EPUB
            
        Returns:
            Path to created EPUB file, or None if failed
        """
        try:
            if not articles:
                logger.error("No articles provided for EPUB creation")
                return None
            
            # Create EPUB book
            book = epub.EpubBook()
            
            # Set metadata
            book.set_identifier(str(uuid.uuid4()))
            book.set_title(title)
            book.set_language('en')
            book.add_author(author)
            book.add_metadata('DC', 'description', f'News digest containing {len(articles)} articles')
            book.add_metadata('DC', 'publisher', 'Kindle Content Server')
            book.add_metadata('DC', 'date', datetime.utcnow().isoformat())
            
            # Add cover page
            cover_html = self._create_cover_page(title, articles)
            cover_chapter = epub.EpubHtml(
                title='Cover',
                file_name='cover.xhtml',
                content=cover_html
            )
            book.add_item(cover_chapter)
            
            # Add table of contents chapter
            toc_html = self._create_table_of_contents(articles)
            toc_chapter = epub.EpubHtml(
                title='Table of Contents',
                file_name='toc.xhtml',
                content=toc_html
            )
            book.add_item(toc_chapter)
            
            # Add articles as chapters
            chapters = [cover_chapter, toc_chapter]
            
            for i, article in enumerate(articles, 1):
                chapter_html = self._create_article_chapter(article, i)
                chapter = epub.EpubHtml(
                    title=article.title[:100],  # Truncate long titles
                    file_name=f'article_{i:03d}.xhtml',
                    content=chapter_html
                )
                book.add_item(chapter)
                chapters.append(chapter)
            
            # Create table of contents
            book.toc = (
                epub.Link("cover.xhtml", "Cover", "cover"),
                epub.Link("toc.xhtml", "Table of Contents", "toc"),
                (
                    epub.Section('Articles'),
                    [
                        epub.Link(f"article_{i:03d}.xhtml", article.title[:50], f"article_{i}")
                        for i, article in enumerate(articles, 1)
                    ]
                )
            )
            
            # Add spine
            book.spine = ['nav'] + chapters
            
            # Add navigation
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            
            # Add CSS
            css_content = self._get_epub_css()
            nav_css = epub.EpubItem(
                uid="nav_css",
                file_name="style/nav.css",
                media_type="text/css",
                content=css_content
            )
            book.add_item(nav_css)
            
            # Generate filename
            safe_title = re.sub(r'[^\w\s-]', '', title)
            safe_title = re.sub(r'[-\s]+', '_', safe_title)
            epub_filename = f"{safe_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.epub"
            epub_path = os.path.join(self.temp_dir, epub_filename)
            
            # Write EPUB file
            epub.write_epub(epub_path, book, {})
            
            logger.info(f"Created EPUB: {epub_path} with {len(articles)} articles")
            return epub_path
            
        except Exception as e:
            logger.error(f"Error creating EPUB: {e}")
            return None
    
    def _create_cover_page(self, title: str, articles: List[NewsItem]) -> str:
        """Create HTML content for cover page"""
        sources = list(set(article.source_name for article in articles))
        sources_text = ', '.join(sources[:5])
        if len(sources) > 5:
            sources_text += f' and {len(sources) - 5} more'
        
        cover_html = f'''<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE html PUBLIC '-//W3C//DTD XHTML 1.1//EN' 'http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd'>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{html.escape(title)}</title>
    <link rel="stylesheet" type="text/css" href="style/nav.css"/>
</head>
<body>
    <div class="cover">
        <h1>{html.escape(title)}</h1>
        <div class="cover-info">
            <p><strong>Articles:</strong> {len(articles)}</p>
            <p><strong>Sources:</strong> {html.escape(sources_text)}</p>
            <p><strong>Generated:</strong> {datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')}</p>
        </div>
        <div class="cover-description">
            <p>This digest contains {len(articles)} carefully selected articles from various news sources. 
            Each article has been processed and formatted for optimal reading on your Kindle device.</p>
        </div>
    </div>
</body>
</html>'''
        return cover_html
    
    def _create_table_of_contents(self, articles: List[NewsItem]) -> str:
        """Create HTML content for table of contents"""
        toc_items = []
        
        for i, article in enumerate(articles, 1):
            reading_time = article.reading_time or 1
            pub_date = article.published_at.strftime('%m/%d') if article.published_at else 'Unknown'
            
            toc_items.append(f'''
            <li>
                <a href="article_{i:03d}.xhtml">
                    <div class="toc-item">
                        <div class="toc-title">{html.escape(article.title)}</div>
                        <div class="toc-meta">
                            <span class="toc-source">{html.escape(article.source_name)}</span>
                            <span class="toc-date">{pub_date}</span>
                            <span class="toc-reading-time">{reading_time} min</span>
                        </div>
                    </div>
                </a>
            </li>''')
        
        toc_html = f'''<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE html PUBLIC '-//W3C//DTD XHTML 1.1//EN' 'http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd'>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Table of Contents</title>
    <link rel="stylesheet" type="text/css" href="style/nav.css"/>
</head>
<body>
    <div class="toc">
        <h1>Table of Contents</h1>
        <ul class="toc-list">
            {''.join(toc_items)}
        </ul>
    </div>
</body>
</html>'''
        return toc_html
    
    def _create_article_chapter(self, article: NewsItem, chapter_number: int) -> str:
        """Create HTML content for an article chapter"""
        # Clean and format content
        content = self._clean_article_content(article.content)
        
        # Format metadata
        pub_date = article.published_at.strftime('%B %d, %Y at %H:%M UTC') if article.published_at else 'Unknown date'
        author_info = f" by {html.escape(article.author)}" if article.author else ""
        reading_time = article.reading_time or 1
        
        # Add quality indicator
        quality_indicator = ""
        if article.quality_score:
            if article.quality_score >= 0.8:
                quality_indicator = " ⭐⭐⭐"
            elif article.quality_score >= 0.6:
                quality_indicator = " ⭐⭐"
            elif article.quality_score >= 0.4:
                quality_indicator = " ⭐"
        
        article_html = f'''<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE html PUBLIC '-//W3C//DTD XHTML 1.1//EN' 'http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd'>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{html.escape(article.title)}</title>
    <link rel="stylesheet" type="text/css" href="style/nav.css"/>
</head>
<body>
    <div class="article">
        <div class="article-header">
            <h1 class="article-title">{html.escape(article.title)}{quality_indicator}</h1>
            <div class="article-meta">
                <div class="article-source">
                    <strong>{html.escape(article.source_name)}</strong>{author_info}
                </div>
                <div class="article-date">{pub_date}</div>
                <div class="article-stats">
                    Reading time: {reading_time} minute{'s' if reading_time != 1 else ''}
                    {f" • {article.word_count} words" if article.word_count else ""}
                </div>
            </div>
        </div>
        
        <div class="article-content">
            {content}
        </div>
        
        <div class="article-footer">
            <hr/>
            <p class="source-link">
                Original article: <a href="{html.escape(article.source_url)}">{html.escape(article.source_name)}</a>
            </p>
        </div>
    </div>
</body>
</html>'''
        return article_html
    
    def _clean_article_content(self, content: str) -> str:
        """Clean and format article content for EPUB"""
        if not content:
            return "<p>No content available.</p>"
        
        # Convert markdown-style formatting to HTML
        content = html.escape(content)
        
        # Convert line breaks to paragraphs
        paragraphs = content.split('\n\n')
        formatted_paragraphs = []
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if paragraph:
                # Handle lists
                if paragraph.startswith('- ') or paragraph.startswith('* '):
                    list_items = paragraph.split('\n')
                    list_html = '<ul>'
                    for item in list_items:
                        item = item.strip()
                        if item.startswith(('- ', '* ')):
                            list_html += f'<li>{item[2:]}</li>'
                        else:
                            list_html += f'<li>{item}</li>'
                    list_html += '</ul>'
                    formatted_paragraphs.append(list_html)
                else:
                    # Regular paragraph
                    # Convert single line breaks to <br> within paragraphs
                    paragraph = paragraph.replace('\n', '<br/>')
                    formatted_paragraphs.append(f'<p>{paragraph}</p>')
        
        return '\n'.join(formatted_paragraphs)
    
    def _get_epub_css(self) -> str:
        """Get CSS styles for EPUB"""
        return '''
/* EPUB Styles for Kindle Content Server */

body {
    font-family: "Times New Roman", serif;
    font-size: 1em;
    line-height: 1.6;
    margin: 0;
    padding: 1em;
    color: #333;
}

/* Cover Page */
.cover {
    text-align: center;
    padding: 2em 1em;
}

.cover h1 {
    font-size: 2.5em;
    margin-bottom: 1em;
    color: #2c3e50;
    border-bottom: 3px solid #3498db;
    padding-bottom: 0.5em;
}

.cover-info {
    background-color: #f8f9fa;
    padding: 1em;
    margin: 2em 0;
    border-radius: 5px;
    border-left: 4px solid #3498db;
}

.cover-info p {
    margin: 0.5em 0;
    font-size: 1.1em;
}

.cover-description {
    font-style: italic;
    margin-top: 2em;
    padding: 1em;
    background-color: #f0f0f0;
    border-radius: 5px;
}

/* Table of Contents */
.toc h1 {
    color: #2c3e50;
    border-bottom: 2px solid #3498db;
    padding-bottom: 0.5em;
    margin-bottom: 1em;
}

.toc-list {
    list-style: none;
    padding: 0;
}

.toc-list li {
    margin-bottom: 1em;
    border-bottom: 1px solid #eee;
    padding-bottom: 0.5em;
}

.toc-list a {
    text-decoration: none;
    color: inherit;
}

.toc-item {
    padding: 0.5em 0;
}

.toc-title {
    font-weight: bold;
    font-size: 1.1em;
    margin-bottom: 0.3em;
    color: #2c3e50;
}

.toc-meta {
    font-size: 0.9em;
    color: #666;
}

.toc-source {
    font-weight: bold;
    color: #3498db;
}

.toc-date, .toc-reading-time {
    margin-left: 0.5em;
}

/* Article Styles */
.article {
    max-width: 100%;
    margin: 0 auto;
}

.article-header {
    margin-bottom: 2em;
    border-bottom: 2px solid #eee;
    padding-bottom: 1em;
}

.article-title {
    font-size: 2em;
    line-height: 1.3;
    margin-bottom: 0.5em;
    color: #2c3e50;
}

.article-meta {
    color: #666;
    font-size: 0.9em;
    line-height: 1.4;
}

.article-source {
    font-weight: bold;
    color: #3498db;
    margin-bottom: 0.3em;
}

.article-date {
    margin-bottom: 0.3em;
}

.article-stats {
    font-style: italic;
}

.article-content {
    margin-bottom: 2em;
}

.article-content p {
    margin-bottom: 1em;
    text-align: justify;
}

.article-content h2 {
    color: #2c3e50;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    font-size: 1.4em;
}

.article-content h3 {
    color: #34495e;
    margin-top: 1.2em;
    margin-bottom: 0.4em;
    font-size: 1.2em;
}

.article-content ul, .article-content ol {
    margin-left: 1.5em;
    margin-bottom: 1em;
}

.article-content li {
    margin-bottom: 0.3em;
}

.article-content blockquote {
    border-left: 4px solid #3498db;
    padding-left: 1em;
    margin: 1em 0;
    font-style: italic;
    color: #555;
}

.article-footer {
    border-top: 1px solid #eee;
    padding-top: 1em;
    margin-top: 2em;
    font-size: 0.9em;
    color: #666;
}

.source-link {
    margin: 0;
}

.source-link a {
    color: #3498db;
    text-decoration: none;
}

/* Responsive adjustments for Kindle */
@media screen and (max-width: 600px) {
    body {
        padding: 0.5em;
    }
    
    .cover h1 {
        font-size: 2em;
    }
    
    .article-title {
        font-size: 1.6em;
    }
}
'''
    
    def create_single_article_epub(self, article: NewsItem, 
                                 title: str = None, author: str = "Kindle Content Server") -> Optional[str]:
        """
        Create an EPUB file from a single news article
        
        Args:
            article: NewsItem object
            title: Override title for the EPUB
            author: Author name for the EPUB
            
        Returns:
            Path to created EPUB file, or None if failed
        """
        try:
            epub_title = title or article.title
            
            # Create EPUB book
            book = epub.EpubBook()
            
            # Set metadata
            book.set_identifier(str(uuid.uuid4()))
            book.set_title(epub_title)
            book.set_language('en')
            book.add_author(author)
            book.add_metadata('DC', 'description', article.summary or 'Single article from Kindle Content Server')
            book.add_metadata('DC', 'publisher', 'Kindle Content Server')
            book.add_metadata('DC', 'date', datetime.utcnow().isoformat())
            
            # Create article chapter
            chapter_html = self._create_article_chapter(article, 1)
            chapter = epub.EpubHtml(
                title=article.title,
                file_name='article.xhtml',
                content=chapter_html
            )
            book.add_item(chapter)
            
            # Create table of contents
            book.toc = [epub.Link("article.xhtml", article.title, "article")]
            
            # Add spine
            book.spine = ['nav', chapter]
            
            # Add navigation
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            
            # Add CSS
            css_content = self._get_epub_css()
            nav_css = epub.EpubItem(
                uid="nav_css",
                file_name="style/nav.css",
                media_type="text/css",
                content=css_content
            )
            book.add_item(nav_css)
            
            # Generate filename
            safe_title = re.sub(r'[^\w\s-]', '', epub_title)
            safe_title = re.sub(r'[-\s]+', '_', safe_title)
            epub_filename = f"{safe_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.epub"
            epub_path = os.path.join(self.temp_dir, epub_filename)
            
            # Write EPUB file
            epub.write_epub(epub_path, book, {})
            
            logger.info(f"Created single article EPUB: {epub_path}")
            return epub_path
            
        except Exception as e:
            logger.error(f"Error creating single article EPUB: {e}")
            return None
-- Database initialization script for Kindle Content Server

-- Create additional databases for different environments
CREATE DATABASE kindle_test;
CREATE DATABASE kindle_staging;

-- Create application user with limited privileges
CREATE USER kindle_user WITH PASSWORD 'kindle_password';

-- Grant necessary privileges
GRANT CONNECT ON DATABASE kindle_dev TO kindle_user;
GRANT CONNECT ON DATABASE kindle_test TO kindle_user;
GRANT CONNECT ON DATABASE kindle_staging TO kindle_user;

-- Switch to kindle_dev database
\c kindle_dev;

-- Create schema
CREATE SCHEMA IF NOT EXISTS app;

-- Grant schema privileges
GRANT USAGE ON SCHEMA app TO kindle_user;
GRANT CREATE ON SCHEMA app TO kindle_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA app TO kindle_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA app TO kindle_user;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT ALL ON TABLES TO kindle_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT ALL ON SEQUENCES TO kindle_user;

-- Install extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create basic tables structure (these will be managed by SQLAlchemy migrations)
-- This is just a placeholder for initial structure

-- Users table
CREATE TABLE IF NOT EXISTS app.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Books table
CREATE TABLE IF NOT EXISTS app.books (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    author VARCHAR(255),
    file_path VARCHAR(1000),
    file_size BIGINT,
    mime_type VARCHAR(100),
    uploaded_by UUID REFERENCES app.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- News sources table
CREATE TABLE IF NOT EXISTS app.news_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    url VARCHAR(1000) NOT NULL,
    rss_url VARCHAR(1000) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    fetch_interval INTEGER DEFAULT 3600, -- seconds
    last_fetched TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- News articles table
CREATE TABLE IF NOT EXISTS app.news_articles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES app.news_sources(id),
    title VARCHAR(500) NOT NULL,
    content TEXT,
    url VARCHAR(1000),
    published_at TIMESTAMP WITH TIME ZONE,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Kindle devices table  
CREATE TABLE IF NOT EXISTS app.kindle_devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES app.users(id),
    device_name VARCHAR(255) NOT NULL,
    device_serial VARCHAR(255) UNIQUE,
    last_sync TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Sync history table
CREATE TABLE IF NOT EXISTS app.sync_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID REFERENCES app.kindle_devices(id),
    sync_type VARCHAR(50) NOT NULL, -- 'books', 'news', 'full'
    items_synced INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'completed', -- 'completed', 'failed', 'partial'
    error_message TEXT,
    sync_duration INTEGER, -- milliseconds
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_books_uploaded_by ON app.books(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_books_created_at ON app.books(created_at);
CREATE INDEX IF NOT EXISTS idx_news_articles_source_id ON app.news_articles(source_id);
CREATE INDEX IF NOT EXISTS idx_news_articles_published_at ON app.news_articles(published_at);
CREATE INDEX IF NOT EXISTS idx_kindle_devices_user_id ON app.kindle_devices(user_id);
CREATE INDEX IF NOT EXISTS idx_sync_history_device_id ON app.sync_history(device_id);
CREATE INDEX IF NOT EXISTS idx_sync_history_created_at ON app.sync_history(created_at);

-- Full text search indexes
CREATE INDEX IF NOT EXISTS idx_books_title_search ON app.books USING gin(to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_books_author_search ON app.books USING gin(to_tsvector('english', author));
CREATE INDEX IF NOT EXISTS idx_news_articles_title_search ON app.news_articles USING gin(to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_news_articles_content_search ON app.news_articles USING gin(to_tsvector('english', content));

-- Grant privileges on the created tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA app TO kindle_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA app TO kindle_user;

-- Insert sample data for development
INSERT INTO app.users (email, password_hash) VALUES 
('test@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3QJK.nEkNO'), -- password: 'password'
('admin@kindle.dev', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3QJK.nEkNO'); -- password: 'password'

INSERT INTO app.news_sources (name, url, rss_url) VALUES 
('BBC News', 'https://www.bbc.com/news', 'http://feeds.bbci.co.uk/news/rss.xml'),
('Reuters', 'https://www.reuters.com', 'https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best'),
('TechCrunch', 'https://techcrunch.com', 'https://techcrunch.com/feed/');

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to tables with updated_at columns
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON app.users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_books_updated_at BEFORE UPDATE ON app.books FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_news_sources_updated_at BEFORE UPDATE ON app.news_sources FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_kindle_devices_updated_at BEFORE UPDATE ON app.kindle_devices FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMIT;
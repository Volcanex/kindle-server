"""
KUAL Client Integration Tests
Tests the KUAL API endpoints and simulates Kindle device behavior
"""

import pytest
import json
import tempfile
import os
import subprocess
import time
from datetime import datetime
from unittest.mock import patch, MagicMock

from app_local import create_app
from models import db


class TestKUALClientSimulation:
    """Test suite that simulates KUAL client behavior"""
    
    @pytest.fixture
    def app(self):
        """Create test app instance"""
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            yield app
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    @pytest.fixture
    def device_headers(self):
        """Standard device headers for KUAL requests"""
        return {
            'X-Device-ID': 'TEST_KINDLE_12345',
            'X-API-Key': 'test-api-key',
            'Content-Type': 'application/json'
        }
    
    def test_kual_health_check(self, client):
        """Test KUAL health endpoint"""
        response = client.get('/api/v1/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert data['service'] == 'kindle-content-server'
        assert 'timestamp' in data
    
    def test_device_authentication(self, client, device_headers):
        """Test device authentication endpoint"""
        auth_data = {
            'device_id': 'TEST_KINDLE_12345',
            'device_type': 'kindle'
        }
        
        response = client.post('/api/v1/auth/device', 
                             headers=device_headers,
                             json=auth_data)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert data['device_id'] == 'TEST_KINDLE_12345'
        assert 'server_time' in data
        assert 'session_expires' in data
    
    def test_content_list_empty(self, client, device_headers):
        """Test content list when no content is available"""
        response = client.get('/api/v1/content/list', headers=device_headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'content' in data
        assert 'total_items' in data
        assert 'device_id' in data
        assert data['device_id'] == 'TEST_KINDLE_12345'
    
    def test_content_list_with_books(self, client, device_headers):
        """Test content list with uploaded books"""
        # Simulate uploaded book
        with client.application.app_context():
            from app_local import uploaded_books
            uploaded_books.append({
                'id': 'book-123',
                'title': 'Test Book',
                'author': 'Test Author',
                'format': 'EPUB',
                'filename': 'test_book.epub',
                'fileSize': 1024000,
                'uploadDate': datetime.now().isoformat(),
                'syncStatus': 'pending'
            })
        
        response = client.get('/api/v1/content/list', headers=device_headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['total_items'] > 0
        
        # Find our test book
        test_book = None
        for item in data['content']:
            if item['id'] == 'book-123':
                test_book = item
                break
        
        assert test_book is not None
        assert test_book['type'] == 'book'
        assert test_book['title'] == 'Test Book'
        assert test_book['format'] == 'epub'
        assert test_book['ready_for_sync'] is True
    
    def test_content_download_simulation(self, client, device_headers):
        """Test content download simulation"""
        # Add a test book
        with client.application.app_context():
            from app_local import uploaded_books
            uploaded_books.clear()
            uploaded_books.append({
                'id': 'book-456',
                'title': 'Download Test Book',
                'author': 'Test Author',
                'format': 'PDF',
                'filename': 'download_test.pdf',
                'fileSize': 2048000,
                'uploadDate': datetime.now().isoformat(),
                'syncStatus': 'pending'
            })
        
        response = client.get('/api/v1/content/download/book-456', headers=device_headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'simulated_download'
        assert data['content_id'] == 'book-456'
        assert 'filename' in data
        assert 'note' in data
    
    def test_sync_status_reporting(self, client, device_headers):
        """Test sync status reporting"""
        # Add a test book first
        with client.application.app_context():
            from app_local import uploaded_books
            uploaded_books.clear()
            uploaded_books.append({
                'id': 'book-789',
                'title': 'Sync Test Book',
                'author': 'Test Author',
                'format': 'EPUB',
                'filename': 'sync_test.epub',
                'fileSize': 1500000,
                'uploadDate': datetime.now().isoformat(),
                'syncStatus': 'pending'
            })
        
        # Report successful sync
        status_data = {
            'content_id': 'book-789',
            'status': 'success',
            'message': 'Download completed successfully',
            'download_time': 15.5,
            'file_size': 1500000
        }
        
        response = client.post('/api/v1/content/sync-status',
                              headers=device_headers,
                              json=status_data)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'received'
        assert data['content_id'] == 'book-789'
        
        # Verify book status was updated
        with client.application.app_context():
            from app_local import uploaded_books
            book = next((b for b in uploaded_books if b['id'] == 'book-789'), None)
            assert book is not None
            assert book['syncStatus'] == 'synced'
            assert 'lastSync' in book
    
    def test_full_sync_workflow(self, client, device_headers):
        """Test complete sync workflow from authentication to status reporting"""
        # 1. Health check
        health_response = client.get('/api/v1/health')
        assert health_response.status_code == 200
        
        # 2. Authentication
        auth_data = {'device_id': 'TEST_KINDLE_12345', 'device_type': 'kindle'}
        auth_response = client.post('/api/v1/auth/device',
                                   headers=device_headers,
                                   json=auth_data)
        assert auth_response.status_code == 200
        
        # 3. Add test content
        with client.application.app_context():
            from app_local import uploaded_books, news_sources
            uploaded_books.clear()
            news_sources.clear()
            
            # Add test book
            uploaded_books.append({
                'id': 'workflow-book-1',
                'title': 'Workflow Test Book',
                'author': 'Workflow Author',
                'format': 'EPUB',
                'filename': 'workflow_test.epub',
                'fileSize': 800000,
                'uploadDate': datetime.now().isoformat(),
                'syncStatus': 'pending'
            })
            
            # Add test news source
            news_sources.append({
                'id': 'news-source-1',
                'name': 'Test News',
                'url': 'https://test.com/rss',
                'category': 'Technology',
                'isActive': True
            })
        
        # 4. Get content list
        content_response = client.get('/api/v1/content/list', headers=device_headers)
        assert content_response.status_code == 200
        
        content_data = json.loads(content_response.data)
        assert content_data['total_items'] >= 1
        
        # Find content to download
        book_item = None
        news_item = None
        for item in content_data['content']:
            if item['type'] == 'book':
                book_item = item
            elif item['type'] == 'news_digest':
                news_item = item
        
        assert book_item is not None
        assert news_item is not None
        
        # 5. Download book content
        download_response = client.get(f'/api/v1/content/download/{book_item["id"]}',
                                      headers=device_headers)
        assert download_response.status_code == 200
        
        # 6. Download news content
        news_download_response = client.get(f'/api/v1/content/download/{news_item["id"]}',
                                           headers=device_headers)
        assert news_download_response.status_code == 200
        
        # 7. Report sync status for book
        book_status_data = {
            'content_id': book_item['id'],
            'status': 'success',
            'message': 'Book downloaded successfully',
            'download_time': 12.3,
            'file_size': book_item['file_size']
        }
        
        book_status_response = client.post('/api/v1/content/sync-status',
                                          headers=device_headers,
                                          json=book_status_data)
        assert book_status_response.status_code == 200
        
        # 8. Report sync status for news
        news_status_data = {
            'content_id': news_item['id'],
            'status': 'success',
            'message': 'News digest downloaded successfully',
            'download_time': 8.7,
            'file_size': news_item['file_size']
        }
        
        news_status_response = client.post('/api/v1/content/sync-status',
                                          headers=device_headers,
                                          json=news_status_data)
        assert news_status_response.status_code == 200


class TestKUALClientScriptSimulation:
    """Test KUAL client shell script functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp(prefix='kual_test_')
        self.plugin_dir = os.path.join(self.test_dir, 'extensions', 'kindle_sync')
        os.makedirs(self.plugin_dir, exist_ok=True)
        os.makedirs(os.path.join(self.plugin_dir, 'config'), exist_ok=True)
        os.makedirs(os.path.join(self.plugin_dir, 'logs'), exist_ok=True)
        os.makedirs(os.path.join(self.plugin_dir, 'bin'), exist_ok=True)
    
    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def create_test_config(self, server_url="http://localhost:8080"):
        """Create test configuration file"""
        config = {
            "server_url": server_url,
            "api_key": "test-api-key",
            "sync_interval": 60,
            "device_settings": {
                "auto_sync": True,
                "wifi_only": False,
                "download_limit": 10,
                "content_types": ["epub", "pdf"],
                "storage_path": os.path.join(self.test_dir, "documents")
            },
            "network_settings": {
                "timeout": 10,
                "retry_attempts": 2,
                "retry_delay": 1
            }
        }
        
        config_path = os.path.join(self.plugin_dir, 'config', 'config.json')
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        return config_path
    
    def create_mock_sync_client(self):
        """Create a mock sync client script for testing"""
        client_script = f'''#!/bin/bash
        
# Mock KUAL sync client for testing
PLUGIN_DIR="{self.plugin_dir}"
CONFIG_FILE="$PLUGIN_DIR/config/config.json"
LOG_FILE="$PLUGIN_DIR/logs/sync.log"
PID_FILE="$PLUGIN_DIR/logs/sync.pid"

log_message() {{
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
    echo "$1"
}}

case "${{1:-sync}}" in
    "sync")
        echo $$ > "$PID_FILE"
        log_message "Starting mock sync"
        
        # Mock authentication
        log_message "Authenticating device: MOCK_DEVICE_123"
        sleep 1
        
        # Mock content list download
        log_message "Downloading content list"
        sleep 1
        
        # Mock content download
        log_message "Downloading content: Mock Book.epub"
        sleep 2
        log_message "Successfully downloaded: Mock Book.epub"
        
        # Mock status reporting
        log_message "Reporting sync status"
        sleep 1
        
        log_message "Sync completed successfully"
        rm -f "$PID_FILE"
        ;;
    "status")
        if [ -f "$PID_FILE" ]; then
            echo "Sync is running (PID: $(cat "$PID_FILE"))"
        else
            echo "Sync is not running"
        fi
        ;;
    "stop")
        if [ -f "$PID_FILE" ]; then
            kill "$(cat "$PID_FILE")" 2>/dev/null && echo "Sync stopped"
            rm -f "$PID_FILE"
        else
            echo "Sync is not running"
        fi
        ;;
esac
'''
        
        client_path = os.path.join(self.plugin_dir, 'bin', 'sync_client')
        with open(client_path, 'w') as f:
            f.write(client_script)
        
        os.chmod(client_path, 0o755)
        return client_path
    
    def test_config_creation(self):
        """Test configuration file creation"""
        config_path = self.create_test_config()
        assert os.path.exists(config_path)
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        assert config['server_url'] == 'http://localhost:8080'
        assert config['api_key'] == 'test-api-key'
        assert 'device_settings' in config
        assert 'network_settings' in config
    
    def test_mock_sync_client_sync(self):
        """Test mock sync client execution"""
        self.create_test_config()
        client_path = self.create_mock_sync_client()
        
        # Test sync operation
        result = subprocess.run([client_path, 'sync'], 
                               capture_output=True, text=True, timeout=10)
        
        assert result.returncode == 0
        assert 'Starting mock sync' in result.stdout
        assert 'Sync completed successfully' in result.stdout
        
        # Check log file was created
        log_path = os.path.join(self.plugin_dir, 'logs', 'sync.log')
        assert os.path.exists(log_path)
        
        with open(log_path, 'r') as f:
            log_content = f.read()
        
        assert 'Authenticating device' in log_content
        assert 'Downloading content list' in log_content
        assert 'Successfully downloaded' in log_content
    
    def test_mock_sync_client_status(self):
        """Test sync client status checking"""
        self.create_test_config()
        client_path = self.create_mock_sync_client()
        
        # Test status when not running
        result = subprocess.run([client_path, 'status'], 
                               capture_output=True, text=True)
        
        assert result.returncode == 0
        assert 'Sync is not running' in result.stdout
    
    def test_directory_structure(self):
        """Test that required directory structure exists"""
        self.create_test_config()
        
        required_dirs = [
            'config',
            'logs',
            'bin'
        ]
        
        for dir_name in required_dirs:
            dir_path = os.path.join(self.plugin_dir, dir_name)
            assert os.path.exists(dir_path)
            assert os.path.isdir(dir_path)


class TestKUALClientWithServer:
    """Integration tests with actual server running"""
    
    @pytest.fixture
    def server_app(self):
        """Start test server"""
        app = create_app()
        app.config['TESTING'] = True
        return app
    
    def test_end_to_end_with_server(self, server_app):
        """Test KUAL client against running server"""
        with server_app.test_client() as client:
            # Simulate device headers
            headers = {
                'X-Device-ID': 'E2E_TEST_DEVICE',
                'X-API-Key': 'e2e-test-key',
                'Content-Type': 'application/json'
            }
            
            # Test complete workflow
            steps = [
                # Health check
                ('GET', '/api/v1/health', None, 200),
                
                # Authentication
                ('POST', '/api/v1/auth/device', 
                 {'device_id': 'E2E_TEST_DEVICE', 'device_type': 'kindle'}, 200),
                
                # Content list
                ('GET', '/api/v1/content/list', None, 200),
                
                # Sync status report
                ('POST', '/api/v1/content/sync-status',
                 {'content_id': 'test-123', 'status': 'success', 'message': 'Test'}, 200)
            ]
            
            for method, endpoint, data, expected_status in steps:
                if method == 'GET':
                    response = client.get(endpoint, headers=headers)
                else:
                    response = client.post(endpoint, headers=headers, json=data)
                
                assert response.status_code == expected_status, f"Failed on {method} {endpoint}"
                
                # Verify JSON response
                response_data = json.loads(response.data)
                assert isinstance(response_data, dict)


class TestKUALClientPerformance:
    """Performance and load testing for KUAL client"""
    
    def test_concurrent_requests(self):
        """Test handling multiple concurrent device requests"""
        import threading
        import queue
        
        app = create_app()
        app.config['TESTING'] = True
        
        results = queue.Queue()
        
        def make_request(device_id):
            with app.test_client() as client:
                headers = {
                    'X-Device-ID': f'PERF_TEST_{device_id}',
                    'X-API-Key': 'perf-test-key'
                }
                
                start_time = time.time()
                response = client.get('/api/v1/content/list', headers=headers)
                end_time = time.time()
                
                results.put({
                    'device_id': device_id,
                    'status_code': response.status_code,
                    'response_time': end_time - start_time
                })
        
        # Start multiple concurrent requests
        threads = []
        num_devices = 5
        
        for i in range(num_devices):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Analyze results
        all_results = []
        while not results.empty():
            all_results.append(results.get())
        
        assert len(all_results) == num_devices
        
        # All requests should succeed
        for result in all_results:
            assert result['status_code'] == 200
            assert result['response_time'] < 5.0  # Should respond within 5 seconds
        
        # Calculate average response time
        avg_response_time = sum(r['response_time'] for r in all_results) / len(all_results)
        print(f"Average response time: {avg_response_time:.3f}s")
        
        assert avg_response_time < 2.0  # Average should be under 2 seconds


# Test runner function
def run_kual_tests():
    """Run all KUAL client tests"""
    print("🧪 Running KUAL Client Tests...")
    print("=" * 50)
    
    # Run pytest with verbose output
    import pytest
    result = pytest.main([
        __file__,
        '-v',
        '--tb=short',
        '--color=yes'
    ])
    
    return result == 0


if __name__ == '__main__':
    run_kual_tests()
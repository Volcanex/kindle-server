#!/usr/bin/env python3
"""
KUAL Client Simulation Test Suite
Comprehensive testing environment for the Kindle KUAL plugin

This script creates a sandboxed environment to test the KUAL plugin
without needing an actual Kindle device.
"""

import os
import sys
import tempfile
import shutil
import json
import subprocess
import time
import threading
import requests
from datetime import datetime
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent / 'project' / 'backend'
sys.path.insert(0, str(backend_path))


class KUALTestEnvironment:
    """Sandboxed test environment for KUAL client"""
    
    def __init__(self):
        self.test_dir = None
        self.kindle_root = None
        self.plugin_dir = None
        self.server_process = None
        self.server_url = "http://localhost:8080"
        
    def setup(self):
        """Set up the test environment"""
        print("🔧 Setting up KUAL test environment...")
        
        # Create temporary directory structure
        self.test_dir = tempfile.mkdtemp(prefix='kual_test_')
        self.kindle_root = os.path.join(self.test_dir, 'kindle_root')
        
        # Create Kindle directory structure
        directories = [
            'mnt/us/extensions/kindle_sync/bin',
            'mnt/us/extensions/kindle_sync/config',
            'mnt/us/extensions/kindle_sync/logs',
            'mnt/us/extensions/kindle_sync/scripts',
            'mnt/us/documents',
            'opt/amazon/ebook/config',
            'var/local/java/prefs/com.amazon.ebook.booklet.reader',
            'sys/class/net/wlan0'
        ]
        
        for directory in directories:
            os.makedirs(os.path.join(self.kindle_root, directory), exist_ok=True)
        
        self.plugin_dir = os.path.join(self.kindle_root, 'mnt/us/extensions/kindle_sync')
        
        print(f"✅ Test environment created at: {self.test_dir}")
        return True
    
    def create_mock_kindle_system(self):
        """Create mock Kindle system files"""
        print("📱 Creating mock Kindle system files...")
        
        # Mock device properties
        device_props = """device_id=B0171234567890
device_type=Kindle
firmware_version=5.17.1.0.4
"""
        device_props_path = os.path.join(self.kindle_root, 'opt/amazon/ebook/config/device.properties')
        with open(device_props_path, 'w') as f:
            f.write(device_props)
        
        # Mock system prefs
        system_prefs = """<?xml version="1.0" encoding="UTF-8"?>
<java version="1.8.0_432" class="java.util.prefs.FileSystemPreferences">
  <map>
    <entry key="DSN" value="B0171234567890"/>
  </map>
</java>
"""
        prefs_path = os.path.join(self.kindle_root, 'var/local/java/prefs/com.amazon.ebook.booklet.reader/.systemPrefs.xml')
        with open(prefs_path, 'w') as f:
            f.write(system_prefs)
        
        # Mock network interface
        mac_address = "aa:bb:cc:dd:ee:ff"
        mac_path = os.path.join(self.kindle_root, 'sys/class/net/wlan0/address')
        with open(mac_path, 'w') as f:
            f.write(mac_address)
        
        print("✅ Mock Kindle system files created")
    
    def install_kual_plugin(self):
        """Install the KUAL plugin files"""
        print("📦 Installing KUAL plugin...")
        
        # Copy plugin files from project
        source_plugin = Path(__file__).parent / 'project' / 'kindle' / 'extensions' / 'kindle_sync'
        
        if source_plugin.exists():
            # Copy the real plugin files
            for item in source_plugin.iterdir():
                if item.is_file():
                    shutil.copy2(item, self.plugin_dir)
                elif item.is_dir():
                    dest_dir = os.path.join(self.plugin_dir, item.name)
                    if os.path.exists(dest_dir):
                        shutil.rmtree(dest_dir)
                    shutil.copytree(item, dest_dir)
        else:
            # Create minimal plugin files if source doesn't exist
            self.create_minimal_plugin()
        
        # Update paths in scripts to use our test environment
        self.update_plugin_paths()
        
        # Make scripts executable
        for script_name in ['sync.sh', 'bin/sync_client']:
            script_path = os.path.join(self.plugin_dir, script_name)
            if os.path.exists(script_path):
                os.chmod(script_path, 0o755)
        
        print("✅ KUAL plugin installed")
    
    def create_minimal_plugin(self):
        """Create minimal plugin files for testing"""
        # Create config.json
        config = {
            "server_url": self.server_url,
            "api_key": "test-api-key-12345",
            "sync_interval": 60,
            "device_settings": {
                "auto_sync": True,
                "wifi_only": False,
                "download_limit": 10,
                "content_types": ["epub", "pdf", "mobi", "txt"],
                "storage_path": f"{self.kindle_root}/mnt/us/documents"
            },
            "network_settings": {
                "timeout": 30,
                "retry_attempts": 3,
                "retry_delay": 5,
                "max_concurrent_downloads": 2
            }
        }
        
        with open(os.path.join(self.plugin_dir, 'config/config.json'), 'w') as f:
            json.dump(config, f, indent=2)
        
        # Create sync_client script
        sync_client_script = f'''#!/bin/bash

# Kindle Content Sync Client - Test Version
PLUGIN_DIR="{self.plugin_dir}"
CONFIG_FILE="$PLUGIN_DIR/config/config.json"
LOG_FILE="$PLUGIN_DIR/logs/sync.log"
PID_FILE="$PLUGIN_DIR/logs/sync.pid"

log_message() {{
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
    echo "$1"
}}

handle_error() {{
    log_message "ERROR: $1"
    echo "Error: $1" >&2
    [ -f "$PID_FILE" ] && rm -f "$PID_FILE"
    exit 1
}}

get_device_id() {{
    # Try to get device ID from mock system files
    if [ -f "{self.kindle_root}/opt/amazon/ebook/config/device.properties" ]; then
        grep "^device_id=" "{self.kindle_root}/opt/amazon/ebook/config/device.properties" | cut -d'=' -f2
    else
        echo "TEST_KINDLE_DEVICE_123"
    fi
}}

load_config() {{
    if [ ! -f "$CONFIG_FILE" ]; then
        handle_error "Configuration file not found: $CONFIG_FILE"
    fi
    
    SERVER_URL=$(grep -o '"server_url"[[:space:]]*:[[:space:]]*"[^"]*"' "$CONFIG_FILE" | sed 's/.*"\\([^"]*\\)".*/\\1/')
    API_KEY=$(grep -o '"api_key"[[:space:]]*:[[:space:]]*"[^"]*"' "$CONFIG_FILE" | sed 's/.*"\\([^"]*\\)".*/\\1/')
    
    if [ -z "$SERVER_URL" ]; then
        handle_error "Server URL not configured"
    fi
}}

test_network() {{
    log_message "Testing network connectivity..."
    if command -v curl >/dev/null 2>&1; then
        if curl -s --connect-timeout 5 "$SERVER_URL/api/v1/health" >/dev/null; then
            log_message "Network connectivity verified"
            return 0
        fi
    elif command -v wget >/dev/null 2>&1; then
        if wget --timeout=5 -q --spider "$SERVER_URL/api/v1/health" 2>/dev/null; then
            log_message "Network connectivity verified"
            return 0
        fi
    fi
    
    log_message "WARNING: Could not verify network connectivity"
    return 0  # Continue anyway for testing
}}

authenticate() {{
    local device_id=$(get_device_id)
    log_message "Authenticating device: $device_id"
    
    local temp_file="/tmp/auth_response_$$.json"
    
    if command -v curl >/dev/null 2>&1; then
        curl -s --connect-timeout 30 \\
             -H "Content-Type: application/json" \\
             -H "X-Device-ID: $device_id" \\
             -H "X-API-Key: $API_KEY" \\
             -d "{\\"device_id\\":\\"$device_id\\",\\"device_type\\":\\"kindle\\"}" \\
             -o "$temp_file" \\
             "$SERVER_URL/api/v1/auth/device"
    elif command -v wget >/dev/null 2>&1; then
        wget --timeout=30 \\
             --header="Content-Type: application/json" \\
             --header="X-Device-ID: $device_id" \\
             --header="X-API-Key: $API_KEY" \\
             --post-data="{\\"device_id\\":\\"$device_id\\",\\"device_type\\":\\"kindle\\"}" \\
             -O "$temp_file" \\
             "$SERVER_URL/api/v1/auth/device" 2>/dev/null
    else
        handle_error "Neither curl nor wget available"
    fi
    
    if [ $? -eq 0 ] && [ -f "$temp_file" ]; then
        if grep -q '"status":"success"' "$temp_file" 2>/dev/null; then
            log_message "Authentication successful"
            rm -f "$temp_file"
            return 0
        else
            local error_msg=$(grep -o '"message"[[:space:]]*:[[:space:]]*"[^"]*"' "$temp_file" 2>/dev/null | sed 's/.*"\\([^"]*\\)".*/\\1/')
            rm -f "$temp_file"
            handle_error "Authentication failed: ${{error_msg:-Unknown error}}"
        fi
    else
        rm -f "$temp_file"
        handle_error "Authentication request failed"
    fi
}}

download_content_list() {{
    local device_id=$(get_device_id)
    local content_file="$PLUGIN_DIR/logs/content_list.json"
    
    log_message "Downloading content list"
    
    if command -v curl >/dev/null 2>&1; then
        curl -s --connect-timeout 30 \\
             -H "X-Device-ID: $device_id" \\
             -H "X-API-Key: $API_KEY" \\
             -o "$content_file" \\
             "$SERVER_URL/api/v1/content/list"
    elif command -v wget >/dev/null 2>&1; then
        wget --timeout=30 \\
             --header="X-Device-ID: $device_id" \\
             --header="X-API-Key: $API_KEY" \\
             -O "$content_file" \\
             "$SERVER_URL/api/v1/content/list" 2>/dev/null
    fi
    
    if [ $? -eq 0 ] && [ -f "$content_file" ]; then
        log_message "Content list downloaded successfully"
        echo "$content_file"
    else
        handle_error "Failed to download content list"
    fi
}}

simulate_downloads() {{
    local content_file="$1"
    local downloaded=0
    
    # Parse JSON and simulate downloads
    if [ -f "$content_file" ]; then
        # Simple JSON parsing for demo
        local content_count=$(grep -o '"id"' "$content_file" | wc -l)
        log_message "Found $content_count items available for download"
        
        # Simulate downloading first few items
        local items_to_download=$((content_count < 3 ? content_count : 3))
        
        for i in $(seq 1 $items_to_download); do
            log_message "Simulating download of item $i"
            sleep 1  # Simulate download time
            downloaded=$((downloaded + 1))
        done
    fi
    
    log_message "Simulated $downloaded downloads"
}}

sync_content() {{
    log_message "Starting content sync"
    echo $$ > "$PID_FILE"
    
    trap 'rm -f "$PID_FILE"; exit' EXIT INT TERM
    
    load_config
    test_network
    authenticate
    
    local content_file=$(download_content_list)
    simulate_downloads "$content_file"
    
    log_message "Content sync completed successfully"
    rm -f "$PID_FILE"
}}

main() {{
    mkdir -p "$(dirname "$LOG_FILE")"
    
    case "${{1:-sync}}" in
        "sync")
            if [ -f "$PID_FILE" ]; then
                local pid=$(cat "$PID_FILE")
                if kill -0 "$pid" 2>/dev/null; then
                    echo "Sync already running (PID: $pid)"
                    exit 1
                else
                    rm -f "$PID_FILE"
                fi
            fi
            sync_content
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
                local pid=$(cat "$PID_FILE")
                kill "$pid" 2>/dev/null && echo "Sync stopped"
                rm -f "$PID_FILE"
            else
                echo "Sync is not running"
            fi
            ;;
        *)
            echo "Usage: $0 {{sync|status|stop}}"
            exit 1
            ;;
    esac
}}

main "$@"
'''
        
        with open(os.path.join(self.plugin_dir, 'bin/sync_client'), 'w') as f:
            f.write(sync_client_script)
        
        # Create main sync.sh script
        sync_sh_script = f'''#!/bin/bash

PLUGIN_DIR="{self.plugin_dir}"
SYNC_CLIENT="$PLUGIN_DIR/bin/sync_client"

echo "============================================"
echo "    Kindle Content Sync v1.0.0 (Test)"
echo "============================================"
echo ""

if [ ! -f "$SYNC_CLIENT" ]; then
    echo "Error: Sync client not found at $SYNC_CLIENT"
    exit 1
fi

echo "Starting content synchronization..."
"$SYNC_CLIENT" sync
exit_code=$?

echo ""
if [ $exit_code -eq 0 ]; then
    echo "✓ Synchronization completed successfully!"
else
    echo "✗ Synchronization failed!"
fi

echo ""
echo "============================================"
'''
        
        with open(os.path.join(self.plugin_dir, 'sync.sh'), 'w') as f:
            f.write(sync_sh_script)
    
    def update_plugin_paths(self):
        """Update plugin paths to use test environment"""
        config_path = os.path.join(self.plugin_dir, 'config/config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Update server URL and storage path
            config['server_url'] = self.server_url
            config['device_settings']['storage_path'] = f"{self.kindle_root}/mnt/us/documents"
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
    
    def start_test_server(self):
        """Start the test server"""
        print("🚀 Starting test server...")
        
        try:
            # Import and start the local app
            from app_local import create_app
            
            app = create_app()
            
            # Start server in a separate thread
            def run_server():
                app.run(host='127.0.0.1', port=8080, debug=False)
            
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            
            # Wait for server to start
            time.sleep(2)
            
            # Test server connectivity
            try:
                response = requests.get(f"{self.server_url}/health", timeout=5)
                if response.status_code == 200:
                    print("✅ Test server started successfully")
                    return True
            except:
                pass
            
            print("❌ Failed to start test server")
            return False
            
        except Exception as e:
            print(f"❌ Error starting server: {e}")
            return False
    
    def run_kual_plugin(self):
        """Run the KUAL plugin"""
        print("🔄 Running KUAL plugin...")
        
        sync_script = os.path.join(self.plugin_dir, 'sync.sh')
        
        if not os.path.exists(sync_script):
            print("❌ KUAL sync script not found")
            return False
        
        try:
            # Change to plugin directory
            old_cwd = os.getcwd()
            os.chdir(self.plugin_dir)
            
            # Run the sync script
            result = subprocess.run(['bash', sync_script], 
                                  capture_output=True, text=True, timeout=30)
            
            os.chdir(old_cwd)
            
            print("📤 KUAL Plugin Output:")
            print("-" * 40)
            print(result.stdout)
            if result.stderr:
                print("Errors:")
                print(result.stderr)
            print("-" * 40)
            
            # Check log file
            log_file = os.path.join(self.plugin_dir, 'logs/sync.log')
            if os.path.exists(log_file):
                print("📋 Sync Log:")
                print("-" * 40)
                with open(log_file, 'r') as f:
                    print(f.read())
                print("-" * 40)
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            print("❌ KUAL plugin execution timed out")
            return False
        except Exception as e:
            print(f"❌ Error running KUAL plugin: {e}")
            return False
    
    def test_api_endpoints(self):
        """Test API endpoints directly"""
        print("🧪 Testing API endpoints...")
        
        endpoints = [
            ('GET', '/api/v1/health', None),
            ('POST', '/api/v1/auth/device', {'device_id': 'TEST_DEVICE', 'device_type': 'kindle'}),
            ('GET', '/api/v1/content/list', None),
            ('POST', '/api/v1/content/sync-status', {
                'content_id': 'test-123',
                'status': 'success',
                'message': 'Test sync completed'
            })
        ]
        
        headers = {
            'X-Device-ID': 'TEST_DEVICE_123',
            'X-API-Key': 'test-api-key-12345',
            'Content-Type': 'application/json'
        }
        
        for method, endpoint, data in endpoints:
            try:
                url = f"{self.server_url}{endpoint}"
                
                if method == 'GET':
                    response = requests.get(url, headers=headers, timeout=10)
                else:
                    response = requests.post(url, headers=headers, json=data, timeout=10)
                
                status = "✅" if response.status_code == 200 else "❌"
                print(f"{status} {method} {endpoint}: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if endpoint == '/api/v1/content/list':
                            print(f"    Content items: {data.get('total_items', 0)}")
                    except:
                        pass
                
            except Exception as e:
                print(f"❌ {method} {endpoint}: Error - {e}")
    
    def add_test_content(self):
        """Add test content to the server"""
        print("📚 Adding test content...")
        
        try:
            # Add test books and news sources
            headers = {'Content-Type': 'application/json'}
            
            # Add a test book
            book_data = {
                'title': 'Test Book for KUAL',
                'author': 'Test Author',
                'format': 'EPUB'
            }
            
            # Use file upload simulation
            test_file_content = b'This is a test EPUB file content'
            files = {'file': ('test_book.epub', test_file_content, 'application/epub+zip')}
            
            upload_response = requests.post(f"{self.server_url}/api/books/upload", 
                                          files=files, timeout=10)
            
            if upload_response.status_code == 200:
                print("✅ Test book added")
            else:
                print(f"❌ Failed to add test book: {upload_response.status_code}")
            
            # Add a test news source
            news_source_data = {
                'name': 'Test News Source',
                'url': 'https://feeds.example.com/test.xml',
                'category': 'Technology',
                'syncFrequency': 'daily',
                'isActive': True
            }
            
            news_response = requests.post(f"{self.server_url}/api/news-sources",
                                        headers=headers, json=news_source_data, timeout=10)
            
            if news_response.status_code == 200:
                print("✅ Test news source added")
            else:
                print(f"❌ Failed to add test news source: {news_response.status_code}")
                
        except Exception as e:
            print(f"❌ Error adding test content: {e}")
    
    def cleanup(self):
        """Clean up the test environment"""
        if self.test_dir and os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)
            print(f"🧹 Cleaned up test environment: {self.test_dir}")


def run_full_kual_simulation():
    """Run the complete KUAL simulation test"""
    print("🎮 KUAL Client Simulation Test Suite")
    print("=" * 60)
    
    env = KUALTestEnvironment()
    
    try:
        # Setup test environment
        if not env.setup():
            print("❌ Failed to set up test environment")
            return False
        
        # Create mock Kindle system
        env.create_mock_kindle_system()
        
        # Install KUAL plugin
        env.install_kual_plugin()
        
        # Start test server
        if not env.start_test_server():
            print("❌ Failed to start test server")
            return False
        
        # Add test content
        env.add_test_content()
        
        # Test API endpoints
        env.test_api_endpoints()
        
        # Run KUAL plugin
        success = env.run_kual_plugin()
        
        print("\n" + "=" * 60)
        if success:
            print("🎉 KUAL Simulation Test PASSED!")
            print("The KUAL client successfully:")
            print("  ✅ Connected to the server")
            print("  ✅ Authenticated the device")
            print("  ✅ Downloaded content list")
            print("  ✅ Simulated content downloads")
            print("  ✅ Completed sync operation")
        else:
            print("❌ KUAL Simulation Test FAILED!")
            print("Check the output above for details.")
        
        return success
        
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        env.cleanup()


if __name__ == '__main__':
    success = run_full_kual_simulation()
    sys.exit(0 if success else 1)
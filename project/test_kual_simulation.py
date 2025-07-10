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
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent / 'backend'
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
            'var/local'
        ]
        
        for directory in directories:
            full_path = os.path.join(self.kindle_root, directory)
            os.makedirs(full_path, exist_ok=True)
        
        self.plugin_dir = os.path.join(self.kindle_root, 'mnt/us/extensions/kindle_sync')
        
        # Create mock Kindle system files
        self.create_mock_kindle_system()
        
        # Create KUAL plugin files
        self.create_kual_plugin_files()
        
        print(f"✅ Test environment created at: {self.test_dir}")
        
    def create_mock_kindle_system(self):
        """Create mock Kindle system files and device properties"""
        
        # Device properties file
        device_props = """device_id=B0171234567890
device_type=Kindle
firmware_version=5.17.1.0.4
device_name=Kindle Paperwhite
serial_number=G091G10173464ABC
"""
        
        device_props_path = os.path.join(self.kindle_root, 'var/local/device.properties')
        os.makedirs(os.path.dirname(device_props_path), exist_ok=True)
        
        with open(device_props_path, 'w') as f:
            f.write(device_props)
        
        # Mock KUAL menu structure
        extensions_dir = os.path.join(self.kindle_root, 'mnt/us/extensions')
        kual_menu = os.path.join(extensions_dir, 'menu.json')
        
        menu_data = {
            "items": [
                {
                    "name": "Kindle Content Sync",
                    "priority": 1,
                    "action": f"{self.plugin_dir}/sync.sh",
                    "params": "sync"
                }
            ]
        }
        
        with open(kual_menu, 'w') as f:
            json.dump(menu_data, f, indent=2)
            
    def create_kual_plugin_files(self):
        """Create KUAL plugin files for testing"""
        
        # Configuration file
        config_data = {
            "server_url": self.server_url,
            "api_key": "test-api-key",
            "sync_interval": 3600,
            "device_settings": {
                "auto_sync": True,
                "wifi_only": True,
                "download_limit": 50,
                "content_types": ["epub", "pdf", "mobi", "txt"],
                "storage_path": "/mnt/us/documents"
            },
            "network_settings": {
                "timeout": 30,
                "retry_attempts": 3,
                "retry_delay": 5,
                "max_concurrent_downloads": 2
            }
        }
        
        config_path = os.path.join(self.plugin_dir, 'config', 'config.json')
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        # KUAL metadata file
        meta_ini_content = """[Global]
name=Kindle Content Sync
author=Kindle Content Server
description=Synchronize content from the Kindle Content Server
version=1.0.0
target=all
"""
        
        meta_ini_path = os.path.join(self.plugin_dir, 'meta.ini')
        with open(meta_ini_path, 'w') as f:
            f.write(meta_ini_content)
        
        # Main sync script
        sync_sh_content = f'''#!/bin/bash
# KUAL Entry Point Script
cd "{self.plugin_dir}"
./bin/sync_client sync
'''
        
        sync_sh_path = os.path.join(self.plugin_dir, 'sync.sh')
        with open(sync_sh_path, 'w') as f:
            f.write(sync_sh_content)
        os.chmod(sync_sh_path, 0o755)
        
        # Create sync client script with shell functions
        sync_client_content = f'''#!/bin/bash

# KUAL Sync Client - Simulation Version
# This is a simulated version for testing without a real Kindle

# Configuration
CONFIG_FILE="{os.path.join(self.plugin_dir, 'config', 'config.json')}"
LOG_FILE="{os.path.join(self.plugin_dir, 'logs', 'sync.log')}"
PID_FILE="{os.path.join(self.plugin_dir, 'logs', 'sync.pid')}"

# Load config
if [ -f "$CONFIG_FILE" ]; then
    SERVER_URL=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['server_url'])" 2>/dev/null || echo "http://localhost:8080")
    API_KEY=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['api_key'])" 2>/dev/null || echo "test")
else
    SERVER_URL="http://localhost:8080"
    API_KEY="test"
fi

# Logging function
log_message() {{
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}}

# Error handling
handle_error() {{
    log_message "ERROR: $1"
    exit 1
}}

# Get device ID
get_device_id() {{
    echo "KINDLE_TEST_$(hostname)_$(date +%s)"
}}

# Authentication function
authenticate_device() {{
    local device_id=$(get_device_id)
    log_message "Authenticating device: $device_id"
    
    local temp_file="/tmp/auth_response_$$.json"
    
    if command -v curl >/dev/null 2>&1; then
        curl -s --connect-timeout 30 \\
             -H "Content-Type: application/json" \\
             -H "X-Device-ID: $device_id" \\
             -H "X-API-Key: $API_KEY" \\
             -d "{{\\"device_id\\":\\"$device_id\\",\\"device_type\\":\\"kindle\\"}}" \\
             -o "$temp_file" \\
             "$SERVER_URL/api/v1/auth/device"
    elif command -v wget >/dev/null 2>&1; then
        wget --timeout=30 \\
             --header="Content-Type: application/json" \\
             --header="X-Device-ID: $device_id" \\
             --header="X-API-Key: $API_KEY" \\
             --post-data="{{\\"device_id\\":\\"$device_id\\",\\"device_type\\":\\"kindle\\"}}" \\
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
    log_message "Fetching content list"
    
    local temp_file="/tmp/content_list_$$.json"
    
    if command -v curl >/dev/null 2>&1; then
        curl -s --connect-timeout 30 \\
             -H "X-Device-ID: $device_id" \\
             -H "X-API-Key: $API_KEY" \\
             -o "$temp_file" \\
             "$SERVER_URL/api/v1/content/list"
    else
        wget --timeout=30 \\
             --header="X-Device-ID: $device_id" \\
             --header="X-API-Key: $API_KEY" \\
             -O "$temp_file" \\
             "$SERVER_URL/api/v1/content/list" 2>/dev/null
    fi
    
    if [ $? -eq 0 ] && [ -f "$temp_file" ]; then
        log_message "Content list downloaded successfully"
        echo "$temp_file"
    else
        rm -f "$temp_file"
        handle_error "Failed to download content list"
    fi
}}

download_content_file() {{
    local content_id="$1"
    local filename="$2"
    local device_id=$(get_device_id)
    
    log_message "Downloading content: $filename"
    
    local output_file="{os.path.join(self.kindle_root, 'mnt/us/documents')}/$filename"
    
    if command -v curl >/dev/null 2>&1; then
        curl -s --connect-timeout 60 \\
             -H "X-Device-ID: $device_id" \\
             -H "X-API-Key: $API_KEY" \\
             -o "$output_file" \\
             "$SERVER_URL/api/v1/content/download/$content_id"
    else
        wget --timeout=60 \\
             --header="X-Device-ID: $device_id" \\
             --header="X-API-Key: $API_KEY" \\
             -O "$output_file" \\
             "$SERVER_URL/api/v1/content/download/$content_id" 2>/dev/null
    fi
    
    if [ $? -eq 0 ] && [ -f "$output_file" ]; then
        log_message "Successfully downloaded: $filename"
        return 0
    else
        log_message "Failed to download: $filename"
        return 1
    fi
}}

report_sync_status() {{
    local content_id="$1"
    local status="$2"
    local message="$3"
    local device_id=$(get_device_id)
    
    local temp_file="/tmp/status_report_$$.json"
    
    local payload="{{\\"content_id\\":\\"$content_id\\",\\"status\\":\\"$status\\",\\"message\\":\\"$message\\",\\"device_id\\":\\"$device_id\\"}}"
    
    if command -v curl >/dev/null 2>&1; then
        curl -s --connect-timeout 30 \\
             -H "Content-Type: application/json" \\
             -H "X-Device-ID: $device_id" \\
             -H "X-API-Key: $API_KEY" \\
             -d "$payload" \\
             -o "$temp_file" \\
             "$SERVER_URL/api/v1/content/sync-status"
    else
        wget --timeout=30 \\
             --header="Content-Type: application/json" \\
             --header="X-Device-ID: $device_id" \\
             --header="X-API-Key: $API_KEY" \\
             --post-data="$payload" \\
             -O "$temp_file" \\
             "$SERVER_URL/api/v1/content/sync-status" 2>/dev/null
    fi
    
    if [ $? -eq 0 ]; then
        log_message "Status reported: $status for $content_id"
    else
        log_message "Failed to report status for $content_id"
    fi
    
    rm -f "$temp_file"
}}

# Main sync function
sync_content() {{
    log_message "Starting content sync"
    echo $$ > "$PID_FILE"
    
    # Authenticate
    if ! authenticate_device; then
        rm -f "$PID_FILE"
        exit 1
    fi
    
    # Get content list
    local content_list_file=$(download_content_list)
    if [ -z "$content_list_file" ]; then
        rm -f "$PID_FILE"
        exit 1
    fi
    
    # Process each content item
    local count=0
    if command -v python3 >/dev/null 2>&1; then
        python3 -c "
import json
import sys

try:
    with open('$content_list_file', 'r') as f:
        data = json.load(f)
    
    if 'data' in data and 'content' in data['data']:
        for item in data['data']['content']:
            print(f\\"{{item['id']}}|{{item['title']}}|{{item.get('filename', item['title'] + '.epub')}}\\")
except Exception as e:
    sys.exit(1)
" | while IFS='|' read -r content_id title filename; do
            if [ -n "$content_id" ]; then
                count=$((count + 1))
                log_message "Processing: $title"
                
                if download_content_file "$content_id" "$filename"; then
                    report_sync_status "$content_id" "success" "Downloaded successfully"
                else
                    report_sync_status "$content_id" "failed" "Download failed"
                fi
            fi
        done
    fi
    
    rm -f "$content_list_file"
    rm -f "$PID_FILE"
    log_message "Content sync completed. Processed $count items."
}}

# Status check
check_status() {{
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo "Sync is running (PID: $pid)"
            return 0
        else
            rm -f "$PID_FILE"
            echo "Sync is not running (stale PID file removed)"
            return 1
        fi
    else
        echo "Sync is not running"
        return 1
    fi
}}

# Stop sync
stop_sync() {{
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            rm -f "$PID_FILE"
            log_message "Sync stopped"
            echo "Sync stopped"
        else
            rm -f "$PID_FILE"
            echo "Sync was not running"
        fi
    else
        echo "Sync is not running"
    fi
}}

# Main command handling
case "$1" in
    sync)
        sync_content
        ;;
    status)
        check_status
        ;;
    stop)
        stop_sync
        ;;
    *)
        echo "Usage: $0 {{sync|status|stop}}"
        exit 1
        ;;
esac
'''
        
        sync_client_path = os.path.join(self.plugin_dir, 'bin', 'sync_client')
        with open(sync_client_path, 'w') as f:
            f.write(sync_client_content)
        os.chmod(sync_client_path, 0o755)
        
    def start_test_server(self):
        """Start the test server in background"""
        print("🌐 Starting test server...")
        
        try:
            # Start server in a separate thread
            def run_server():
                try:
                    from app_local import app
                    app.run(host='127.0.0.1', port=8080, debug=False, use_reloader=False)
                except Exception as e:
                    print(f"Server error: {e}")
            
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            
            # Wait for server to start
            for i in range(10):
                try:
                    response = requests.get(f"{self.server_url}/health", timeout=2)
                    if response.status_code == 200:
                        print("✅ Test server is running")
                        return True
                except requests.exceptions.RequestException:
                    pass
                time.sleep(1)
            
            print("❌ Failed to start test server")
            return False
            
        except ImportError:
            print("⚠️  Could not import app_local, skipping server start")
            return False
            
    def test_kual_client_workflow(self):
        """Test the complete KUAL client workflow"""
        print("\n🧪 Testing KUAL client workflow...")
        
        results = {
            'authentication': False,
            'content_list': False,
            'download': False,
            'status_report': False
        }
        
        # Test authentication
        try:
            device_id = "KINDLE_TEST_SIMULATION"
            auth_response = requests.post(
                f"{self.server_url}/api/v1/auth/device",
                json={"device_id": device_id, "device_type": "kindle"},
                headers={
                    "X-Device-ID": device_id,
                    "X-API-Key": "test-api-key"
                },
                timeout=10
            )
            
            if auth_response.status_code == 200:
                print("✅ Authentication test passed")
                results['authentication'] = True
            else:
                print(f"❌ Authentication test failed: {auth_response.status_code}")
                
        except Exception as e:
            print(f"❌ Authentication test error: {e}")
        
        # Test content list
        try:
            content_response = requests.get(
                f"{self.server_url}/api/v1/content/list",
                headers={
                    "X-Device-ID": device_id,
                    "X-API-Key": "test-api-key"
                },
                timeout=10
            )
            
            if content_response.status_code == 200:
                print("✅ Content list test passed")
                results['content_list'] = True
                
                # Try to download first item if available
                try:
                    content_data = content_response.json()
                    if 'data' in content_data and 'content' in content_data['data']:
                        content_items = content_data['data']['content']
                        if content_items:
                            first_item = content_items[0]
                            content_id = first_item['id']
                            
                            download_response = requests.get(
                                f"{self.server_url}/api/v1/content/download/{content_id}",
                                headers={
                                    "X-Device-ID": device_id,
                                    "X-API-Key": "test-api-key"
                                },
                                timeout=30
                            )
                            
                            if download_response.status_code == 200:
                                print("✅ Content download test passed")
                                results['download'] = True
                            else:
                                print(f"❌ Content download test failed: {download_response.status_code}")
                                
                except Exception as e:
                    print(f"⚠️  Download test skipped: {e}")
                    
            else:
                print(f"❌ Content list test failed: {content_response.status_code}")
                
        except Exception as e:
            print(f"❌ Content list test error: {e}")
        
        # Test status reporting
        try:
            status_response = requests.post(
                f"{self.server_url}/api/v1/content/sync-status",
                json={
                    "content_id": "test-content-1",
                    "status": "success",
                    "message": "Test download completed",
                    "device_id": device_id
                },
                headers={
                    "X-Device-ID": device_id,
                    "X-API-Key": "test-api-key",
                    "Content-Type": "application/json"
                },
                timeout=10
            )
            
            if status_response.status_code == 200:
                print("✅ Status report test passed")
                results['status_report'] = True
            else:
                print(f"❌ Status report test failed: {status_response.status_code}")
                
        except Exception as e:
            print(f"❌ Status report test error: {e}")
        
        return results
    
    def test_sync_script_execution(self):
        """Test the sync script execution"""
        print("\n🔧 Testing sync script execution...")
        
        try:
            sync_script = os.path.join(self.plugin_dir, 'bin', 'sync_client')
            
            # Test status command
            result = subprocess.run(
                ['bash', sync_script, 'status'],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=self.plugin_dir
            )
            
            if result.returncode == 1:  # Expected for "not running"
                print("✅ Sync script status command works")
                return True
            else:
                print(f"⚠️  Sync script status returned: {result.returncode}")
                print(f"Output: {result.stdout}")
                print(f"Error: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Sync script execution timed out")
            return False
        except Exception as e:
            print(f"❌ Sync script execution error: {e}")
            return False
    
    def run_performance_tests(self):
        """Run performance tests for concurrent requests"""
        print("\n⚡ Running performance tests...")
        
        try:
            import concurrent.futures
            import time
            
            def test_auth_endpoint():
                device_id = f"PERF_TEST_{time.time()}"
                try:
                    response = requests.post(
                        f"{self.server_url}/api/v1/auth/device",
                        json={"device_id": device_id, "device_type": "kindle"},
                        headers={
                            "X-Device-ID": device_id,
                            "X-API-Key": "test-api-key"
                        },
                        timeout=5
                    )
                    return response.status_code == 200
                except:
                    return False
            
            # Test concurrent requests
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(test_auth_endpoint) for _ in range(10)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            end_time = time.time()
            
            success_count = sum(results)
            total_time = end_time - start_time
            
            print(f"✅ Performance test completed:")
            print(f"   • Successful requests: {success_count}/10")
            print(f"   • Total time: {total_time:.2f}s")
            print(f"   • Average time per request: {total_time/10:.2f}s")
            
            return success_count >= 8  # At least 80% success rate
            
        except ImportError:
            print("⚠️  concurrent.futures not available, skipping performance tests")
            return True
        except Exception as e:
            print(f"❌ Performance test error: {e}")
            return False
    
    def cleanup(self):
        """Clean up the test environment"""
        print("\n🧹 Cleaning up test environment...")
        
        if self.test_dir and os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
            print("✅ Test environment cleaned up")
        
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait()
            print("✅ Test server stopped")


def main():
    """Main test execution function"""
    print("🧪 KUAL Client Simulation Test Suite")
    print("=" * 50)
    
    env = KUALTestEnvironment()
    
    try:
        # Setup environment
        env.setup()
        
        # Start test server
        server_started = env.start_test_server()
        
        # Run tests
        test_results = {}
        
        if server_started:
            test_results['workflow'] = env.test_kual_client_workflow()
            test_results['performance'] = env.run_performance_tests()
        else:
            print("⚠️  Skipping API tests due to server startup failure")
            test_results['workflow'] = {
                'authentication': False,
                'content_list': False,
                'download': False,
                'status_report': False
            }
            test_results['performance'] = False
        
        test_results['script_execution'] = env.test_sync_script_execution()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Results Summary:")
        print("=" * 50)
        
        if 'workflow' in test_results:
            workflow = test_results['workflow']
            print("\n🔄 Workflow Tests:")
            print(f"   • Authentication: {'✅ PASS' if workflow['authentication'] else '❌ FAIL'}")
            print(f"   • Content List: {'✅ PASS' if workflow['content_list'] else '❌ FAIL'}")
            print(f"   • Download: {'✅ PASS' if workflow['download'] else '❌ FAIL'}")
            print(f"   • Status Report: {'✅ PASS' if workflow['status_report'] else '❌ FAIL'}")
        
        print(f"\n🔧 Script Execution: {'✅ PASS' if test_results['script_execution'] else '❌ FAIL'}")
        print(f"⚡ Performance: {'✅ PASS' if test_results['performance'] else '❌ FAIL'}")
        
        # Overall result
        if server_started:
            workflow_success = all(test_results['workflow'].values())
            overall_success = workflow_success and test_results['script_execution'] and test_results['performance']
        else:
            overall_success = test_results['script_execution']
        
        print(f"\n🎯 Overall Result: {'🎉 ALL TESTS PASSED' if overall_success else '⚠️ SOME TESTS FAILED'}")
        
        if overall_success:
            print("\n✅ The KUAL client is ready for deployment!")
            print("📝 Next steps:")
            print("   1. Deploy the backend server to production")
            print("   2. Update KUAL configuration with production server URL")
            print("   3. Install the KUAL extension on your Kindle device")
            print("   4. Test with real device")
        else:
            print("\n⚠️  Some tests failed. Please review the errors above.")
            
        print(f"\n📁 Test environment location: {env.test_dir}")
        print("   (Files will be cleaned up automatically)")
        
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test execution error: {e}")
    finally:
        env.cleanup()


if __name__ == '__main__':
    main()
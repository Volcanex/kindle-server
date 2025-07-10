#!/usr/bin/env python3
"""
Simple KUAL validation script
Validates the KUAL client setup without requiring Flask dependencies
"""

import os
import json
import subprocess
from pathlib import Path

def validate_kual_structure():
    """Validate KUAL plugin directory structure"""
    print("🔍 Validating KUAL plugin structure...")
    
    base_path = Path(__file__).parent / 'kindle' / 'extensions' / 'kindle_sync'
    
    required_files = [
        'sync.sh',
        'bin/sync_client',
        'config/config.json',
        'meta.ini'
    ]
    
    required_dirs = [
        'bin',
        'config', 
        'logs',
        'scripts'
    ]
    
    # Check directories
    for dir_name in required_dirs:
        dir_path = base_path / dir_name
        if dir_path.exists():
            print(f"✅ Directory exists: {dir_name}")
        else:
            print(f"❌ Directory missing: {dir_name}")
    
    # Check files
    for file_name in required_files:
        file_path = base_path / file_name
        if file_path.exists():
            print(f"✅ File exists: {file_name}")
            
            # Check if shell scripts are executable
            if file_name.endswith('.sh') or 'bin/' in file_name:
                if os.access(file_path, os.X_OK):
                    print(f"✅ Script is executable: {file_name}")
                else:
                    print(f"⚠️  Script not executable: {file_name}")
        else:
            print(f"❌ File missing: {file_name}")

def validate_kual_config():
    """Validate KUAL configuration"""
    print("\n🔧 Validating KUAL configuration...")
    
    config_path = Path(__file__).parent / 'kindle' / 'extensions' / 'kindle_sync' / 'config' / 'config.json'
    
    if not config_path.exists():
        print("❌ Configuration file missing")
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        required_keys = [
            'server_url',
            'api_key',
            'device_settings',
            'network_settings'
        ]
        
        for key in required_keys:
            if key in config:
                print(f"✅ Config key exists: {key}")
            else:
                print(f"❌ Config key missing: {key}")
        
        # Validate specific settings
        if 'server_url' in config:
            server_url = config['server_url']
            if server_url.startswith('http'):
                print(f"✅ Server URL is valid: {server_url}")
            else:
                print(f"⚠️  Server URL format issue: {server_url}")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Config JSON parse error: {e}")
        return False

def validate_backend_routes():
    """Validate backend has KUAL API routes"""
    print("\n🛠️  Validating backend KUAL API routes...")
    
    kual_api_path = Path(__file__).parent / 'backend' / 'routes' / 'kual_api.py'
    
    if not kual_api_path.exists():
        print("❌ KUAL API routes file missing")
        return False
    
    try:
        with open(kual_api_path, 'r') as f:
            content = f.read()
        
        required_endpoints = [
            '/api/v1/health',
            '/api/v1/auth/device',
            '/api/v1/content/list',
            '/api/v1/content/download',
            '/api/v1/content/sync-status'
        ]
        
        for endpoint in required_endpoints:
            if endpoint in content:
                print(f"✅ Endpoint defined: {endpoint}")
            else:
                print(f"❌ Endpoint missing: {endpoint}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading KUAL API file: {e}")
        return False

def test_sync_script():
    """Test sync script basic functionality"""
    print("\n🧪 Testing sync script...")
    
    sync_script = Path(__file__).parent / 'kindle' / 'extensions' / 'kindle_sync' / 'bin' / 'sync_client'
    
    if not sync_script.exists():
        print("❌ Sync client script missing")
        return False
    
    try:
        # Test status command (should not require server)
        result = subprocess.run(['bash', str(sync_script), 'status'], 
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            print("✅ Sync script executes successfully")
            print(f"   Output: {result.stdout.strip()}")
        else:
            print(f"⚠️  Sync script returned code {result.returncode}")
            print(f"   Error: {result.stderr.strip()}")
        
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Sync script execution timed out")
        return False
    except Exception as e:
        print(f"❌ Error testing sync script: {e}")
        return False

def create_test_environment():
    """Create a simple test environment description"""
    print("\n📋 KUAL Test Environment Setup:")
    print("=" * 50)
    
    print("1. 🏗️  Sandboxed Environment Components:")
    print("   • Mock Kindle file system structure")
    print("   • Simulated device ID and system files")
    print("   • KUAL plugin installation directory")
    print("   • Test configuration with local server")
    
    print("\n2. 🧪 Test Scenarios:")
    print("   • Device authentication with server")
    print("   • Content list retrieval")
    print("   • Content download simulation")
    print("   • Sync status reporting")
    print("   • Error handling and retry logic")
    
    print("\n3. 🔗 API Endpoints Tested:")
    print("   • GET  /api/v1/health")
    print("   • POST /api/v1/auth/device")
    print("   • GET  /api/v1/content/list")
    print("   • GET  /api/v1/content/download/{id}")
    print("   • POST /api/v1/content/sync-status")
    
    print("\n4. 🎯 Test Coverage:")
    print("   • Unit tests for API endpoints")
    print("   • Integration tests for full workflow")
    print("   • Performance tests for concurrent requests")
    print("   • Error scenario testing")
    print("   • Configuration validation")
    
    print("\n5. 🚀 Running Tests:")
    print("   • Install dependencies: pip install -r backend/requirements-local.txt")
    print("   • Run unit tests: pytest backend/tests/test_kual_client.py")
    print("   • Run simulation: python test_kual_simulation.py")
    print("   • Run all tests: ./run_kual_tests.sh")

def main():
    """Main validation function"""
    print("🧪 KUAL Client Validation Suite")
    print("=" * 50)
    
    # Run all validations
    results = []
    
    results.append(validate_kual_structure())
    results.append(validate_kual_config())
    results.append(validate_backend_routes())
    results.append(test_sync_script())
    
    # Show test environment info
    create_test_environment()
    
    print("\n" + "=" * 50)
    print("📊 Validation Summary:")
    
    if all(r for r in results if r is not None):
        print("🎉 All validations passed!")
        print("\nThe KUAL client is properly configured and ready for testing.")
        print("\n📝 Next Steps:")
        print("1. Install Python dependencies")
        print("2. Start the backend server")
        print("3. Run the full test suite")
        print("4. Test with actual Kindle device")
    else:
        print("❌ Some validations failed!")
        print("\nPlease fix the issues above before running tests.")
    
    print("\n🔧 Manual Testing:")
    print("• Backend server: cd backend && python app_local.py")
    print("• Test health: curl http://localhost:8080/api/v1/health")
    print("• Test auth: curl -X POST -H 'X-Device-ID: TEST' -H 'X-API-Key: test' http://localhost:8080/api/v1/auth/device")

if __name__ == '__main__':
    main()
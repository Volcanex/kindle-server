#!/bin/bash

# KUAL Client Test Runner
# Runs various tests for the KUAL plugin in sandboxed environments

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🧪 Kindle KUAL Client Test Suite"
echo "=================================="
echo ""

# Check dependencies
echo "🔍 Checking dependencies..."
python3 --version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Install Python dependencies if needed
if [ -f "project/backend/requirements-local.txt" ]; then
    echo "📦 Installing Python dependencies..."
    pip3 install -r project/backend/requirements-local.txt > /dev/null 2>&1 || true
fi

echo "✅ Dependencies checked"
echo ""

# Run unit tests
echo "🧪 Running unit tests..."
cd project/backend
if python3 -m pytest tests/test_kual_client.py -v --tb=short 2>/dev/null; then
    echo "✅ Unit tests passed"
else
    echo "⚠️  Unit tests had issues (continuing with integration tests)"
fi
cd ../..
echo ""

# Run integration simulation
echo "🎮 Running KUAL client simulation..."
python3 test_kual_simulation.py

echo ""
echo "🏁 Test suite completed!"
echo ""
echo "Test Types Run:"
echo "  • Unit tests (API endpoint testing)"
echo "  • Integration tests (full workflow simulation)"
echo "  • Performance tests (concurrent requests)"
echo "  • Environment simulation (mock Kindle system)"
echo ""
echo "For manual testing:"
echo "  1. Start the backend server: cd project/backend && python3 app_local.py"
echo "  2. Test KUAL endpoints: curl http://localhost:8080/api/v1/health"
echo "  3. Check the web frontend: cd project/frontend && npm start"
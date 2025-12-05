#!/bin/bash

# Load Testing Runner for CV-Job Matching System
# Usage: ./scripts/run_load_tests.sh [scenario]

set -e

HOST="${HOST:-http://localhost:8000}"
SCRIPT="scripts/locust_load_test_new.py"

echo "============================================"
echo "CV-Job Matching Load Test Runner"
echo "Host: $HOST"
echo "============================================"
echo ""

# Check if locust is installed
if ! command -v locust &> /dev/null; then
    echo "❌ Locust is not installed"
    echo "Install with: pip install locust"
    exit 1
fi

# Check if API is running
if ! curl -s "$HOST/docs" > /dev/null; then
    echo "❌ API is not running at $HOST"
    echo "Start the API server first"
    exit 1
fi

echo "✓ Locust is installed"
echo "✓ API is accessible at $HOST"
echo ""

SCENARIO="${1:-help}"

case $SCENARIO in
    web)
        echo "🌐 Starting Web UI..."
        echo "Open http://localhost:8089 in your browser"
        locust -f "$SCRIPT" --host="$HOST"
        ;;
    
    quick)
        echo "⚡ Quick Test (10 users, 1 min)"
        locust -f "$SCRIPT" --host="$HOST" --headless \
            -u 10 -r 2 -t 60s MixedTraffic
        ;;
    
    standard)
        echo "📊 Standard Test (50 users, 5 min)"
        locust -f "$SCRIPT" --host="$HOST" --headless \
            -u 50 -r 5 -t 300s MixedTraffic
        ;;
    
    load)
        echo "🔥 Load Test (100 users, 10 min)"
        locust -f "$SCRIPT" --host="$HOST" --headless \
            -u 100 -r 10 -t 600s MixedTraffic
        ;;
    
    burst)
        echo "💥 Burst Test (200 users, rapid spawn)"
        locust -f "$SCRIPT" --host="$HOST" --headless \
            -u 200 -r 20 -t 300s BurstTraffic
        ;;
    
    heavy)
        echo "🏋️ Heavy Load (500 users, 15 min)"
        locust -f "$SCRIPT" --host="$HOST" --headless \
            -u 500 -r 25 -t 900s HeavyLoad
        ;;
    
    endurance)
        echo "⏱️ Endurance Test (50 users, 30 min)"
        locust -f "$SCRIPT" --host="$HOST" --headless \
            -u 50 -r 5 -t 1800s MixedTraffic
        ;;
    
    candidates)
        echo "👤 Candidate Flow Only (100 users, 5 min)"
        locust -f "$SCRIPT" --host="$HOST" --headless \
            -u 100 -r 10 -t 300s CandidateUser
        ;;
    
    hirers)
        echo "🏢 Hirer Flow Only (50 users, 5 min)"
        locust -f "$SCRIPT" --host="$HOST" --headless \
            -u 50 -r 5 -t 300s HirerUser
        ;;
    
    admin)
        echo "🔍 Admin Monitoring (10 users, 5 min)"
        locust -f "$SCRIPT" --host="$HOST" --headless \
            -u 10 -r 2 -t 300s AdminUser
        ;;
    
    help|*)
        echo "Available scenarios:"
        echo ""
        echo "  web          - Interactive Web UI (default)"
        echo "  quick        - Quick test (10 users, 1 min)"
        echo "  standard     - Standard test (50 users, 5 min)"
        echo "  load         - Load test (100 users, 10 min)"
        echo "  burst        - Burst test (200 users, rapid)"
        echo "  heavy        - Heavy load (500 users, 15 min)"
        echo "  endurance    - Endurance test (50 users, 30 min)"
        echo "  candidates   - Candidate flow only"
        echo "  hirers       - Hirer flow only"
        echo "  admin        - Admin monitoring only"
        echo ""
        echo "Usage:"
        echo "  ./scripts/run_load_tests.sh [scenario]"
        echo ""
        echo "Examples:"
        echo "  ./scripts/run_load_tests.sh web"
        echo "  ./scripts/run_load_tests.sh quick"
        echo "  ./scripts/run_load_tests.sh load"
        echo "  HOST=http://production.com ./scripts/run_load_tests.sh standard"
        ;;
esac

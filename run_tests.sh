#!/bin/bash

# Test Runner Script for CV Matching API
# This script provides convenient commands for running tests

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}CV Matching API - Test Runner${NC}\n"

# Function to print section headers
print_header() {
    echo -e "\n${GREEN}=== $1 ===${NC}\n"
}

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${YELLOW}pytest not found. Installing test dependencies...${NC}"
    pip install pytest pytest-cov pytest-mock pytest-asyncio httpx
fi

# Parse command line arguments
case "${1:-all}" in
    all)
        print_header "Running All Tests"
        pytest tests/ -v
        ;;
    
    candidate)
        print_header "Running Candidate Router Tests"
        pytest tests/test_candidate_router.py -v
        ;;
    
    hirer)
        print_header "Running Hirer Router Tests"
        pytest tests/test_hirer_router.py -v
        ;;
    
    interactions)
        print_header "Running Interactions Router Tests"
        pytest tests/test_interactions_router.py -v
        ;;
    
    coverage)
        print_header "Running Tests with Coverage"
        pytest tests/ --cov=api.routers --cov-report=html --cov-report=term
        echo -e "\n${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        ;;
    
    quick)
        print_header "Running Quick Test (No Verbose)"
        pytest tests/ -q
        ;;
    
    failed)
        print_header "Re-running Failed Tests"
        pytest tests/ --lf -v
        ;;
    
    markers)
        print_header "Available Test Markers"
        pytest --markers
        ;;
    
    help)
        echo "Usage: ./run_tests.sh [command]"
        echo ""
        echo "Commands:"
        echo "  all           - Run all tests (default)"
        echo "  candidate     - Run candidate router tests only"
        echo "  hirer         - Run hirer router tests only"
        echo "  interactions  - Run interactions router tests only"
        echo "  coverage      - Run tests with coverage report"
        echo "  quick         - Run tests without verbose output"
        echo "  failed        - Re-run only failed tests"
        echo "  markers       - Show available test markers"
        echo "  help          - Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./run_tests.sh all"
        echo "  ./run_tests.sh coverage"
        echo "  ./run_tests.sh candidate"
        ;;
    
    *)
        echo -e "${YELLOW}Unknown command: $1${NC}"
        echo "Run './run_tests.sh help' for usage information"
        exit 1
        ;;
esac

echo -e "\n${GREEN}✓ Done!${NC}\n"

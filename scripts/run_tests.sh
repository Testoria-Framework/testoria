#!/bin/bash

# API Testing Framework - Test Runner Script

set -e  # Exit on error

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Set default values
LANGUAGE="all"
TEST_TYPE="functional"
ENV="dev"
REPORT=false
PARALLEL=false
VERBOSE=false

# Script root directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Export environment variable
export ENVIRONMENT="$ENV"

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -l|--language)
            LANGUAGE="$2"
            shift 2
            ;;
        -t|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -e|--env)
            ENV="$2"
            shift 2
            ;;
        -r|--report)
            REPORT=true
            shift
            ;;
        -p|--parallel)
            PARALLEL=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Run the tests
cd "$PROJECT_ROOT"
echo -e "${BLUE}Starting API tests with:${NC}"
echo -e "  ${YELLOW}Language:${NC} $LANGUAGE"
echo -e "  ${YELLOW}Test Type:${NC} $TEST_TYPE"
echo -e "  ${YELLOW}Environment:${NC} $ENV"
echo ""

# Create report directories
mkdir -p "$PROJECT_ROOT/reports/allure-results/$LANGUAGE/$TEST_TYPE"

# Run Java tests
if [[ "$LANGUAGE" == "all" || "$LANGUAGE" == "java" ]]; then
    echo -e "${BLUE}Running Java tests: $TEST_TYPE${NC}"
    ./mvnw clean test
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Java tests passed successfully${NC}"
    else
        echo -e "${RED}Java tests failed${NC}"
        if [[ "$LANGUAGE" == "java" ]]; then
            exit 1
        fi
    fi
fi

# Run Python tests
if [[ "$LANGUAGE" == "all" || "$LANGUAGE" == "python" ]]; then
    echo -e "${BLUE}Running Python tests: $TEST_TYPE${NC}"
    
    # Check if Python is installed
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Error: Python is not installed${NC}"
        if [[ "$LANGUAGE" == "python" ]]; then
            exit 1
        fi
    else
        # Run the tests using pytest
        PYTEST_ARGS=""
        if [[ "$TEST_TYPE" == "functional" ]]; then
            PYTEST_ARGS="-m functional"
        elif [[ "$TEST_TYPE" == "integration" ]]; then
            PYTEST_ARGS="-m integration"
        elif [[ "$TEST_TYPE" == "security" ]]; then
            PYTEST_ARGS="-m security"
        fi
        
        python3 -m pytest tests/${TEST_TYPE}_tests/python/ $PYTEST_ARGS --alluredir="$PROJECT_ROOT/reports/allure-results/python/$TEST_TYPE" -v
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}Python tests passed successfully${NC}"
        else
            echo -e "${RED}Python tests failed${NC}"
            if [[ "$LANGUAGE" == "python" ]]; then
                exit 1
            fi
        fi
    fi
fi

# Run JavaScript tests
if [[ "$LANGUAGE" == "all" || "$LANGUAGE" == "javascript" ]]; then
    echo -e "${BLUE}Running JavaScript tests: $TEST_TYPE${NC}"
    
    # Check if Node.js is installed
    if ! command -v node &> /dev/null; then
        echo -e "${RED}Error: Node.js is not installed${NC}"
        if [[ "$LANGUAGE" == "javascript" ]]; then
            exit 1
        fi
    else
        # Run the tests using Jest
        TEST_PATH="tests/${TEST_TYPE}_tests/javascript/"
        
        npx jest $TEST_PATH --testPathPattern="${TEST_TYPE}" --reporters=default --reporters=jest-allure
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}JavaScript tests passed successfully${NC}"
        else
            echo -e "${RED}JavaScript tests failed${NC}"
            if [[ "$LANGUAGE" == "javascript" ]]; then
                exit 1
            fi
        fi
        
        # Copy Allure results
        mkdir -p "$PROJECT_ROOT/reports/allure-results/javascript/$TEST_TYPE"
        cp -r "$PROJECT_ROOT/allure-results"/* "$PROJECT_ROOT/reports/allure-results/javascript/$TEST_TYPE/" 2>/dev/null || true
    fi
fi

# Generate and open Allure report if requested
if [ "$REPORT" = true ]; then
    if command -v allure &> /dev/null; then
        cd "$PROJECT_ROOT"
        allure generate "$PROJECT_ROOT/reports/allure-results/$LANGUAGE/$TEST_TYPE" -o "$PROJECT_ROOT/reports/allure-report/$LANGUAGE/$TEST_TYPE" --clean
    else
        echo -e "${YELLOW}Allure not installed. Skipping report generation.${NC}"
    fi
fi

echo -e "${GREEN}All tests completed successfully!${NC}"
exit 0
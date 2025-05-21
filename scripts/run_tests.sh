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

# Run the tests using Maven wrapper
cd "$PROJECT_ROOT"
echo -e "${BLUE}Starting API tests with:${NC}"
echo -e "  ${YELLOW}Language:${NC} $LANGUAGE"
echo -e "  ${YELLOW}Test Type:${NC} $TEST_TYPE"
echo -e "  ${YELLOW}Environment:${NC} $ENV"
echo ""

# Run Java tests
if [[ "$LANGUAGE" == "all" || "$LANGUAGE" == "java" ]]; then
    echo -e "${BLUE}Running Java tests: *Functional*${NC}"
    ./mvnw clean test
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Java tests passed successfully${NC}"
    else
        echo -e "${RED}Java tests failed${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}All tests completed successfully!${NC}"
exit 0
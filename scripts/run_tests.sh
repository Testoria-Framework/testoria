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
SKIP_DEPS_CHECK=false

# Script root directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Function to display help
show_help() {
    echo -e "${BLUE}API Testing Framework - Test Runner${NC}"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -l, --language LANG    Specify language (python, javascript, java, all). Default: all"
    echo "  -t, --type TYPE        Specify test type (functional, integration, security, performance, all). Default: functional"
    echo "  -e, --env ENV          Specify environment (dev, test, staging, prod). Default: dev"
    echo "  -r, --report           Generate and open Allure report"
    echo "  -p, --parallel         Run tests in parallel"
    echo "  -v, --verbose          Enable verbose output"
    echo "  -h, --help             Show this help message"
    echo ""
}

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
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Validate inputs
validate_input() {
    local input="$1"
    local valid_options="$2"
    
    if [[ ! "$input" =~ ^($valid_options)$ ]]; then
        echo -e "${RED}Error: Invalid input '$input'.${NC}"
        exit 1
    fi
}

# Validate language
validate_input "$LANGUAGE" "python|javascript|java|all"

# Validate test type
validate_input "$TEST_TYPE" "functional|integration|security|performance|all"

# Validate environment
validate_input "$ENV" "dev|test|staging|prod"

# Verbose mode shows commands being executed
if [ "$VERBOSE" = true ]; then
    set -x
fi

# Export environment variable
export ENVIRONMENT="$ENV"

# Create report directories
mkdir -p "$PROJECT_ROOT/reports/allure-results"

# Function to run Java tests
run_java_tests() {
    local test_pattern="$1"
    echo -e "${BLUE}Running Java tests: $test_pattern${NC}"
    
    # Check if Java is installed
    if ! command -v java &> /dev/null; then
        echo -e "${RED}Error: Java is not installed${NC}"
        return 1
    fi
    
    # Check if Maven is installed
    if ! command -v mvn &> /dev/null; then
        echo -e "${RED}Error: Maven is not installed${NC}"
        return 1
    fi
    
    # Run the tests
    cd "$PROJECT_ROOT"
    mvn test -Dtest="$test_pattern"
    
    local result=$?
    if [ $result -eq 0 ]; then
        echo -e "${GREEN}Java tests passed successfully${NC}"
    else
        echo -e "${RED}Java tests failed${NC}"
    fi
    
    # Copy Allure results
    mkdir -p "$PROJECT_ROOT/reports/allure-results"
    cp -r "$PROJECT_ROOT/target/allure-results"/* "$PROJECT_ROOT/reports/allure-results/" || true
    
    return $result
}

# Main function to run tests
run_tests() {
    local status=0
    
    echo -e "${BLUE}Starting API tests with:${NC}"
    echo -e "  ${YELLOW}Language:${NC} $LANGUAGE"
    echo -e "  ${YELLOW}Test Type:${NC} $TEST_TYPE"
    echo -e "  ${YELLOW}Environment:${NC} $ENV"
    echo ""
    
    # Run Java tests
    if [[ "$LANGUAGE" == "all" || "$LANGUAGE" == "java" ]]; then
        if [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "functional" ]]; then
            run_java_tests "*Functional*" || status=1
        fi
    fi
    
    # Generate and open Allure report if requested
    if [ "$REPORT" = true ]; then
        if command -v allure &> /dev/null; then
            cd "$PROJECT_ROOT"
            allure generate "$PROJECT_ROOT/reports/allure-results" -o "$PROJECT_ROOT/reports/allure-report" --clean
        else
            echo -e "${YELLOW}Allure not installed. Skipping report generation.${NC}"
        fi
    fi
    
    return $status
}

# Execute the main function
run_tests
exit_status=$?

if [ $exit_status -eq 0 ]; then
    echo -e "${GREEN}All tests completed successfully!${NC}"
else
    echo -e "${RED}Some tests failed. Check the logs for details.${NC}"
fi

exit $exit_status
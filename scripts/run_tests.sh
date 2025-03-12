#!/bin/bash

# API Testing Framework - Test Runner Script
# This script simplifies running tests from different languages and types

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
    echo "Examples:"
    echo "  $0 --language python --type functional --env dev"
    echo "  $0 --language all --type all --report"
    echo "  $0 -l javascript -t integration -r -v"
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
if [[ ! "$LANGUAGE" =~ ^(python|javascript|java|all)$ ]]; then
    echo -e "${RED}Error: Invalid language '$LANGUAGE'. Use python, javascript, java, or all.${NC}"
    exit 1
fi

if [[ ! "$TEST_TYPE" =~ ^(functional|integration|security|performance|all)$ ]]; then
    echo -e "${RED}Error: Invalid test type '$TEST_TYPE'. Use functional, integration, security, performance, or all.${NC}"
    exit 1
fi

if [[ ! "$ENV" =~ ^(dev|test|staging|prod)$ ]]; then
    echo -e "${RED}Error: Invalid environment '$ENV'. Use dev, test, staging, or prod.${NC}"
    exit 1
fi

# Verbose mode shows commands being executed
if [ "$VERBOSE" = true ]; then
    set -x
fi

# Export environment variable
export ENVIRONMENT="$ENV"

# Create report directories
mkdir -p "$PROJECT_ROOT/reports/allure-results"

# Function to run Python tests
run_python_tests() {
    local test_path="$1"
    echo -e "${BLUE}Running Python tests: $test_path${NC}"
    
    # Check if Python is installed
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Error: Python 3 is not installed${NC}"
        return 1
    fi
    
    # Check if pytest is installed
    if ! python3 -c "import pytest" &> /dev/null; then
        echo -e "${YELLOW}Warning: pytest is not installed. Installing...${NC}"
        pip install pytest pytest-cov allure-pytest
    fi
    
    # Install requirements if they exist
    if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
        pip install -r "$PROJECT_ROOT/requirements.txt"
    fi
    
    # Run the tests
    cd "$PROJECT_ROOT"
    python3 -m pytest "$test_path" -v --alluredir="$PROJECT_ROOT/reports/allure-results"
    
    local result=$?
    if [ $result -eq 0 ]; then
        echo -e "${GREEN}Python tests passed successfully${NC}"
    else
        echo -e "${RED}Python tests failed${NC}"
    fi
    return $result
}

# Function to run JavaScript tests
run_javascript_tests() {
    local test_type="$1"
    echo -e "${BLUE}Running JavaScript $test_type tests${NC}"
    
    # Check if Node.js is installed
    if ! command -v node &> /dev/null; then
        echo -e "${RED}Error: Node.js is not installed${NC}"
        return 1
    fi
    
    # Check if npm is installed
    if ! command -v npm &> /dev/null; then
        echo -e "${RED}Error: npm is not installed${NC}"
        return 1
    fi
    
    # Install dependencies
    cd "$PROJECT_ROOT"
    npm ci
    
    # Run the tests
    npm run "test:$test_type"
    
    local result=$?
    if [ $result -eq 0 ]; then
        echo -e "${GREEN}JavaScript tests passed successfully${NC}"
    else
        echo -e "${RED}JavaScript tests failed${NC}"
    fi
    return $result
}

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

# Function to run performance tests
run_performance_tests() {
    echo -e "${BLUE}Running Performance tests${NC}"
    
    # Check if JMeter is installed or available
    if ! command -v jmeter &> /dev/null; then
        echo -e "${YELLOW}Warning: JMeter not found in PATH${NC}"
        
        # Try to find or download JMeter
        if [ ! -d "$PROJECT_ROOT/apache-jmeter" ]; then
            echo -e "${YELLOW}Downloading Apache JMeter...${NC}"
            cd "$PROJECT_ROOT"
            wget https://dlcdn.apache.org//jmeter/binaries/apache-jmeter-5.5.tgz
            tar -xzf apache-jmeter-5.5.tgz
            mv apache-jmeter-5.5 apache-jmeter
            rm apache-jmeter-5.5.tgz
        fi
        
        JMETER_PATH="$PROJECT_ROOT/apache-jmeter/bin/jmeter"
    else
        JMETER_PATH="jmeter"
    fi
    
    # Create performance test results directory
    mkdir -p "$PROJECT_ROOT/reports/performance"
    
    # Run JMeter tests
    cd "$PROJECT_ROOT"
    $JMETER_PATH -n -t "tests/performance_tests/jmeter_scripts/api_load_test.jmx" \
        -l "$PROJECT_ROOT/reports/performance/results.jtl" \
        -e -o "$PROJECT_ROOT/reports/performance/dashboard"
    
    local result=$?
    if [ $result -eq 0 ]; then
        echo -e "${GREEN}Performance tests completed successfully${NC}"
        echo -e "${BLUE}Performance test report available at: ${NC}$PROJECT_ROOT/reports/performance/dashboard/index.html"
    else
        echo -e "${RED}Performance tests failed${NC}"
    fi
    return $result
}

# Function to generate and open Allure report
generate_report() {
    echo -e "${BLUE}Generating Allure report...${NC}"
    
    # Check if Allure is installed
    if ! command -v allure &> /dev/null; then
        echo -e "${YELLOW}Warning: Allure is not installed. Installing...${NC}"
        
        # Try to install Allure
        if command -v npm &> /dev/null; then
            npm install -g allure-commandline
        else
            echo -e "${RED}Error: Cannot install Allure. Please install it manually${NC}"
            return 1
        fi
    fi
    
    # Generate the report
    cd "$PROJECT_ROOT"
    allure generate "$PROJECT_ROOT/reports/allure-results" -o "$PROJECT_ROOT/reports/allure-report" --clean
    
    # Open the report
    allure open "$PROJECT_ROOT/reports/allure-report"
}

# Main function to run tests
run_tests() {
    local status=0
    
    echo -e "${BLUE}Starting API tests with:${NC}"
    echo -e "  ${YELLOW}Language:${NC} $LANGUAGE"
    echo -e "  ${YELLOW}Test Type:${NC} $TEST_TYPE"
    echo -e "  ${YELLOW}Environment:${NC} $ENV"
    echo ""
    
    # Run the appropriate tests
    if [ "$PARALLEL" = true ]; then
        echo -e "${YELLOW}Running tests in parallel mode${NC}"
        
        # Launch tests in background processes
        if [[ "$LANGUAGE" == "all" || "$LANGUAGE" == "python" ]] && [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "functional" ]]; then
            run_python_tests "tests/functional_tests/python/" &
        fi
        
        if [[ "$LANGUAGE" == "all" || "$LANGUAGE" == "python" ]] && [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "integration" ]]; then
            run_python_tests "tests/integration_tests/python/" &
        fi
        
        if [[ "$LANGUAGE" == "all" || "$LANGUAGE" == "python" ]] && [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "security" ]]; then
            run_python_tests "tests/security_tests/python/" &
        fi
        
        if [[ "$LANGUAGE" == "all" || "$LANGUAGE" == "javascript" ]] && [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "functional" ]]; then
            run_javascript_tests "functional" &
        fi
        
        if [[ "$LANGUAGE" == "all" || "$LANGUAGE" == "javascript" ]] && [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "integration" ]]; then
            run_javascript_tests "integration" &
        fi
        
        if [[ "$LANGUAGE" == "all" || "$LANGUAGE" == "javascript" ]] && [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "security" ]]; then
            run_javascript_tests "security" &
        fi
        
        if [[ "$LANGUAGE" == "all" || "$LANGUAGE" == "java" ]] && [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "functional" ]]; then
            run_java_tests "*Functional*" &
        fi
        
        if [[ "$LANGUAGE" == "all" || "$LANGUAGE" == "java" ]] && [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "integration" ]]; then
            run_java_tests "*Integration*" &
        fi
        
        if [[ "$LANGUAGE" == "all" || "$LANGUAGE" == "java" ]] && [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "security" ]]; then
            run_java_tests "*Security*" &
        fi
        
        if [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "performance" ]]; then
            run_performance_tests &
        fi
        
        # Wait for all background processes to finish
        wait
        
        # Check if any process failed
        for job in $(jobs -p); do
            wait $job || status=1
        done
    else
        # Run tests sequentially
        if [[ "$LANGUAGE" == "all" || "$LANGUAGE" == "python" ]]; then
            if [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "functional" ]]; then
                run_python_tests "tests/functional_tests/python/" || status=1
            fi
            
            if [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "integration" ]]; then
                run_python_tests "tests/integration_tests/python/" || status=1
            fi
            
            if [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "security" ]]; then
                run_python_tests "tests/security_tests/python/" || status=1
            fi
        fi
        
        if [[ "$LANGUAGE" == "all" || "$LANGUAGE" == "javascript" ]]; then
            if [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "functional" ]]; then
                run_javascript_tests "functional" || status=1
            fi
            
            if [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "integration" ]]; then
                run_javascript_tests "integration" || status=1
            fi
            
            if [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "security" ]]; then
                run_javascript_tests "security" || status=1
            fi
        fi
        
        if [[ "$LANGUAGE" == "all" || "$LANGUAGE" == "java" ]]; then
            if [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "functional" ]]; then
                run_java_tests "*Functional*" || status=1
            fi
            
            if [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "integration" ]]; then
                run_java_tests "*Integration*" || status=1
            fi
            
            if [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "security" ]]; then
                run_java_tests "*Security*" || status=1
            fi
        fi
        
        if [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "performance" ]]; then
            run_performance_tests || status=1
        fi
    fi
    
    # Generate and open Allure report if requested
    if [ "$REPORT" = true ]; then
        generate_report
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

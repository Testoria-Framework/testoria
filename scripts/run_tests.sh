#!/bin/bash

# API Testing Framework - Test Runner Script
# Enhanced version with additional error handling and flexibility

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

# Script and project directories
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Logging function
log() {
    local level="$1"
    local message="$2"
    local color=""

    case "$level" in
        "INFO")
            color="${BLUE}"
            ;;
        "SUCCESS")
            color="${GREEN}"
            ;;
        "WARNING")
            color="${YELLOW}"
            ;;
        "ERROR")
            color="${RED}"
            ;;
        *)
            color="${NC}"
            ;;
    esac

    echo -e "${color}[${level}] ${message}${NC}"
}

# Function to check and install dependencies
install_dependencies() {
    if [ "$SKIP_DEPS_CHECK" = true ]; then
        log "INFO" "Skipping dependency checks"
        return 0
    }

    log "INFO" "Checking and installing dependencies..."

    # Python dependencies
    if command -v python3 &> /dev/null; then
        log "INFO" "Installing Python dependencies"
        pip install -r "$PROJECT_ROOT/requirements.txt" || \
            log "WARNING" "Failed to install Python dependencies"
    fi

    # JavaScript dependencies
    if command -v npm &> /dev/null; then
        log "INFO" "Installing Node.js dependencies"
        npm ci || log "WARNING" "Failed to install Node.js dependencies"
    fi

    # Java dependencies
    if command -v mvn &> /dev/null; then
        log "INFO" "Installing Java dependencies"
        mvn clean install -DskipTests || \
            log "WARNING" "Failed to install Java dependencies"
    fi
}

# Enhanced error handling wrapper
run_with_error_handling() {
    local command="$1"
    local error_message="${2:-Command failed}"

    set +e  # Temporarily disable exit on error
    eval "$command"
    local result=$?
    set -e

    if [ $result -ne 0 ]; then
        log "ERROR" "$error_message"
        return $result
    fi
    return 0
}

# Remaining functions and script logic stay the same as in the previous version...

# Add a new option for skipping dependency checks
while [[ $# -gt 0 ]]; do
    case $1 in
        # ... (existing options)
        --skip-deps)
            SKIP_DEPS_CHECK=true
            shift
            ;;
        *)
            # ... (existing argument handling)
            ;;
    esac
done

# Main execution
main() {
    log "INFO" "Starting API Testing Framework"
    
    # Validate and set up environment
    export ENVIRONMENT="$ENV"
    
    # Install dependencies
    install_dependencies
    
    # Run tests with error handling
    run_with_error_handling "run_tests" "Test execution failed"
    
    log "SUCCESS" "Test execution completed"
}

# Call main function
main

exit 0
# Performance Tests

This directory contains performance tests for the API Testing Framework. These tests are designed to measure the performance characteristics of the API under various load conditions.

## Test Types

- **Load Tests**: Measure system behavior under expected load
- **Stress Tests**: Measure system behavior under extreme load
- **Endurance Tests**: Measure system behavior under sustained load
- **Spike Tests**: Measure system behavior under sudden increases in load

## Tools

The framework supports multiple performance testing tools:

- **JMeter**: Primary tool for comprehensive performance testing
- **k6**: JavaScript-based performance testing tool for developers
- **Locust**: Python-based performance testing tool

## Directory Structure

```
performance_tests/
├── jmeter_scripts/       # JMeter test scripts
├── k6_scripts/           # k6 test scripts
├── locust_scripts/       # Locust test scripts
├── data/                 # Test data files
└── README.md             # This file
```

## Running Tests

### JMeter Tests

```bash
# Run JMeter tests using the run_tests script
./scripts/run_tests.sh --type performance

# Run JMeter tests directly with specific parameters
jmeter -n -t tests/performance_tests/jmeter_scripts/api_load_test.jmx \
    -l results.jtl \
    -e -o reports/performance/dashboard \
    -Jbase_url=https://api-dev.example.com \
    -Jusers=50 \
    -Jramp_up=10 \
    -Jduration=60 \
    -Jthink_time=1000
```

### k6 Tests

```bash
# Install k6 if not already installed
# For macOS
brew install k6

# For Linux
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6

# Run k6 tests
k6 run tests/performance_tests/k6_scripts/api_load_test.js

# Run with custom options
k6 run --vus 50 --duration 60s tests/performance_tests/k6_scripts/api_load_test.js
```

### Locust Tests

```bash
# Install Locust if not already installed
pip install locust

# Run Locust tests (web UI mode)
cd tests/performance_tests/locust_scripts
locust -f api_load_test.py

# Run Locust tests (headless mode)
locust -f api_load_test.py --headless -u 50 -r 5 -t 1m
```

## Configuration

Each performance testing tool has its own configuration options:

### JMeter Configuration

JMeter tests can be configured using the following system properties:

- `base_url`: Base URL of the API (default: https://api-dev.example.com)
- `users`: Number of concurrent users (default: 50)
- `ramp_up`: Ramp-up period in seconds (default: 10)
- `duration`: Test duration in seconds (default: 60)
- `think_time`: Think time between requests in milliseconds (default: 1000)

### k6 Configuration

k6 tests can be configured using environment variables or command-line options:

```bash
# Using environment variables
BASE_URL=https://api-dev.example.com k6 run tests/performance_tests/k6_scripts/api_load_test.js

# Using command-line options
k6 run --vus 50 --duration 60s --env BASE_URL=https://api-dev.example.com tests/performance_tests/k6_scripts/api_load_test.js
```

### Locust Configuration

Locust can be configured through its web UI or using command-line options:

```bash
locust -f api_load_test.py --host https://api-dev.example.com --users 50 --spawn-rate 5 --run-time 1m
```

## Analyzing Results

Performance test results can be analyzed in different ways:

### JMeter Reports

JMeter automatically generates HTML reports with detailed metrics:

```bash
# View JMeter dashboard report
open reports/performance/dashboard/index.html
```

### k6 Reports

k6 provides built-in support for various output formats:

```bash
# Output to JSON for further analysis
k6 run --out json=results.json tests/performance_tests/k6_scripts/api_load_test.js

# Output to InfluxDB for real-time visualization with Grafana
k6 run --out influxdb=http://localhost:8086/k6 tests/performance_tests/k6_scripts/api_load_test.js
```

### Locust Reports

Locust provides a web UI with real-time metrics and can export test results to CSV:

```bash
# Export Locust results to CSV
locust -f api_load_test.py --headless -u 50 -r 5 -t 1m --csv=locust_results
```

## Performance Test Criteria

The following performance criteria are used to evaluate the API:

- **Response Time**: Average response time should be less than 1 second
- **Throughput**: System should handle at least 100 requests per second
- **Error Rate**: Error rate should be less than 1%
- **CPU Usage**: Server CPU usage should not exceed 70%
- **Memory Usage**: Server memory usage should not exceed 80%

These criteria should be adjusted based on specific API requirements and environment capabilities.

# API Testing Framework

A comprehensive multi-language API Testing Framework to facilitate automated testing for RESTful APIs. The framework supports functional, integration, security, and performance tests across Python, JavaScript, and Java.

## Features

- **Multi-language support**: Write tests in Python, JavaScript, or Java
- **Multiple test types**:
  - Functional testing
  - Integration/E2E testing
  - Performance/Load testing
  - Security testing
- **Robust reporting**: Unified reporting with Allure
- **CI/CD integration**: Ready-to-use configurations for GitHub Actions, GitLab CI/CD, and Jenkins
- **Parallel execution**: Run tests in parallel for faster feedback
- **Environment configurations**: Easily switch between environments (dev, test, staging, prod)
- **Cross-platform**: Works on Windows, macOS, and Linux

## Project Structure

```
api_testing_framework/
├── core/
│   ├── clients/            # Base API clients for different languages
│   ├── assertions/         # Assertion utilities
│   ├── config/             # Configuration management
│   ├── utils/              # Common helper functions
│   └── reporting/          # Reporting utilities
│
├── tests/
│   ├── functional_tests/   # Functional tests
│   ├── integration_tests/  # Integration tests
│   ├── performance_tests/  # Performance tests
│   └── security_tests/     # Security tests
│
├── mocks/                  # Mock server configurations
├── ci_cd/                  # CI/CD configuration files
├── reports/                # Test reports
├── scripts/                # Utility scripts
│
├── requirements.txt        # Python dependencies
├── package.json            # JavaScript dependencies
└── pom.xml                 # Java dependencies
```

## Getting Started

### Prerequisites

Depending on which language you want to use, you'll need:

- **Python**: Python 3.8+ and pip
- **JavaScript**: Node.js 14+ and npm
- **Java**: JDK 11+ and Maven

### Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/api-testing-framework.git
cd api-testing-framework
```

2. Install dependencies for your preferred language:

**Python**:
```bash
pip install -r requirements.txt
```

**JavaScript**:
```bash
npm install
```

**Java**:
```bash
mvn install
```

### Running Tests

Use the provided script to run tests:

```bash
# Run all functional tests in all languages
./scripts/run_tests.sh --type functional

# Run Python integration tests
./scripts/run_tests.sh --language python --type integration

# Run JavaScript security tests with report generation
./scripts/run_tests.sh --language javascript --type security --report

# Run performance tests
./scripts/run_tests.sh --type performance

# Run all tests in parallel
./scripts/run_tests.sh --language all --type all --parallel
```

#### Command Line Options

- `-l, --language`: Specify language (python, javascript, java, all)
- `-t, --type`: Specify test type (functional, integration, security, performance, all)
- `-e, --env`: Specify environment (dev, test, staging, prod)
- `-r, --report`: Generate and open Allure report
- `-p, --parallel`: Run tests in parallel
- `-v, --verbose`: Enable verbose output
- `-h, --help`: Show help message

## Writing Tests

### Python Example

```python
import pytest
from core.clients.base_api_client import BaseApiClient
from core.assertions.python_assertions import ApiAssertions

def test_get_user_by_id():
    # Initialize client
    client = BaseApiClient("https://api.example.com")
    
    # Make request
    response = client.get("/users/1")
    
    # Assert response
    ApiAssertions.assert_status_code(response, 200)
    ApiAssertions.assert_json_content_type(response)
    
    json_data = ApiAssertions.assert_json_body(response)
    ApiAssertions.assert_json_has_keys(json_data, ['id', 'name', 'email'])
```

### JavaScript Example

```javascript
const { describe, it } = require('mocha');
const BaseApiClient = require('../../../core/clients/base_api_client');
const ApiAssertions = require('../../../core/assertions/js_assertions');

describe('User API', function() {
  it('should get user by ID', async function() {
    // Initialize client
    const client = new BaseApiClient('https://api.example.com');
    
    // Make request
    const response = await client.get('/users/1');
    
    // Assert response
    ApiAssertions.assertStatusCode(response, 200);
    ApiAssertions.assertJsonContentType(response);
    ApiAssertions.assertJsonHasKeys(response.data, ['id', 'name', 'email']);
  });
});
```

### Java Example

```java
import core.clients.BaseApiClient;
import core.assertions.JavaAssertions;
import io.restassured.response.Response;
import org.json.JSONObject;
import org.junit.jupiter.api.*;

public class UserApiTest {
    @Test
    public void testGetUserById() {
        // Initialize client
        BaseApiClient client = new BaseApiClient("https://api.example.com");
        
        // Make request
        Response response = client.get("/users/1");
        
        // Assert response
        JavaAssertions.assertStatusCode(response, 200);
        JavaAssertions.assertJsonContentType(response);
        
        JSONObject json = JavaAssertions.getResponseAsJsonObject(response);
        Assertions.assertTrue(json.has("id"));
        Assertions.assertTrue(json.has("name"));
        Assertions.assertTrue(json.has("email"));
    }
}
```

## Configuration

Configuration is managed through the `core/config/config.json` file and environment variables. You can specify different settings for each environment (dev, test, staging, prod).

Example configuration:

```json
{
  "environments": {
    "dev": {
      "base_url": "https://api-dev.example.com",
      "timeout": 30000
    },
    "test": {
      "base_url": "https://api-test.example.com",
      "timeout": 30000
    }
  }
}
```

Environment variables can be used in the configuration by using the syntax `${VARIABLE_NAME}`.

## Reporting

The framework uses Allure for unified reporting across all languages. Reports can be generated using the `--report` flag when running tests:

```bash
./scripts/run_tests.sh --type functional --report
```

This will generate and open an HTML report with detailed test results, including:

- Test status (passed/failed)
- Test duration
- Request/response details
- Error messages
- Screenshots (if available)
- Trending and history

## CI/CD Integration

The framework includes pre-configured files for:

- GitHub Actions: `.github/workflows/main.yml`
- GitLab CI/CD: `.gitlab-ci.yml`
- Jenkins: `Jenkinsfile`

These configurations will run tests, generate reports, and upload artifacts.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

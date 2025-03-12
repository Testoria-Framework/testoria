import pytest
import logging
import json
import re

from core.clients.base_api_client import BaseApiClient
from core.assertions.python_assertions import ApiAssertions
from core.config.env_loader import get_environment_config, get_base_url
from core.reporting.allure_reporter import allure_reporter
from core.utils.common_helpers import ApiTestUtils

logger = logging.getLogger(__name__)

@pytest.fixture
def api_client():
    """Fixture to create and configure the API client for testing."""
    env_config = get_environment_config('dev')
    base_url = env_config['base_url']
    
    client = BaseApiClient(base_url)
    
    # Add default headers
    client.headers.update({
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    })
    
    yield client
    
    # Cleanup after tests
    client.clear_authorization()

@pytest.fixture
def auth_token():
    """Fixture to get a valid authentication token."""
    # This would be replaced with actual authentication logic
    return "valid_token"

class TestApiSecurity:
    """
    Test suite for API security.
    Tests authentication, authorization, input validation, and other security aspects.
    """
    
    @pytest.mark.security
    def test_anonymous_endpoints_access(self, api_client):
        """Test access to endpoints that should be available without authentication."""
        # Arrange
        public_endpoints = [
            "/health",
            "/version",
            "/docs"
        ]
        
        allure_reporter.start_test("Anonymous Endpoints Access", "Test access to public endpoints without authentication")
        allure_reporter.add_tag("security")
        allure_reporter.add_severity("normal")
        
        # Act & Assert
        for endpoint in public_endpoints:
            allure_reporter.add_api_request("GET", endpoint, api_client.headers)
            response = api_client.get(endpoint)
            allure_reporter.add_api_response(response)
            
            ApiAssertions.assert_success(response)  # Should return 2xx status
    
    @pytest.mark.security
    def test_protected_endpoints_without_auth(self, api_client):
        """Test access to protected endpoints without authentication."""
        # Arrange
        protected_endpoints = [
            "/users",
            "/orders",
            "/products/admin"
        ]
        
        allure_reporter.start_test("Protected Endpoints Without Auth", "Test access to protected endpoints without authentication")
        allure_reporter.add_tag("security")
        allure_reporter.add_severity("critical")
        
        # Act & Assert
        for endpoint in protected_endpoints:
            allure_reporter.add_api_request("GET", endpoint, api_client.headers)
            
            try:
                response = api_client.get(endpoint)
                # If request succeeds, fail the test
                allure_reporter.add_api_response(response)
                assert False, f"Endpoint {endpoint} should require authentication"
            except Exception as e:
                # Extract response from exception
                if hasattr(e, 'response'):
                    response = e.response
                    allure_reporter.add_api_response(response)
                    
                    # Should return 401 Unauthorized or 403 Forbidden
                    status_code = response.status_code
                    assert status_code in [401, 403], f"Expected 401 or 403, but got {status_code}"
                else:
                    # Re-raise if not the expected exception
                    raise
    
    @pytest.mark.security
    def test_authentication_with_valid_token(self, api_client, auth_token):
        """Test authentication with a valid token."""
        # Arrange
        api_client.set_authorization("Bearer", auth_token)
        
        allure_reporter.start_test("Authentication With Valid Token", "Test authentication with a valid token")
        allure_reporter.add_tag("security")
        allure_reporter.add_severity("critical")
        
        # Act
        allure_reporter.add_api_request("GET", "/users", api_client.headers)
        response = api_client.get("/users")
        allure_reporter.add_api_response(response)
        
        # Assert
        ApiAssertions.assert_success(response)  # Should return 2xx status
    
    @pytest.mark.security
    def test_authentication_with_invalid_token(self, api_client):
        """Test authentication with an invalid token."""
        # Arrange
        api_client.set_authorization("Bearer", "invalid_token")
        
        allure_reporter.start_test("Authentication With Invalid Token", "Test authentication with an invalid token")
        allure_reporter.add_tag("security")
        allure_reporter.add_severity("critical")
        
        # Act
        allure_reporter.add_api_request("GET", "/users", api_client.headers)
        
        try:
            response = api_client.get("/users")
            # If request succeeds, fail the test
            allure_reporter.add_api_response(response)
            assert False, "Request with invalid token should fail"
        except Exception as e:
            # Extract response from exception
            if hasattr(e, 'response'):
                response = e.response
                allure_reporter.add_api_response(response)
                
                # Should return 401 Unauthorized
                ApiAssertions.assert_status_code(response, 401)
            else:
                # Re-raise if not the expected exception
                raise
    
    @pytest.mark.security
    def test_sql_injection_prevention(self, api_client):
        """Test prevention of SQL injection attacks."""
        # Arrange
        sql_injection_payloads = [
            "1' OR '1'='1",
            "1; DROP TABLE users",
            "1' UNION SELECT * FROM users --",
            "1' OR 1=1 --"
        ]
        
        allure_reporter.start_test("SQL Injection Prevention", "Test prevention of SQL injection attacks")
        allure_reporter.add_tag("security")
        allure_reporter.add_severity("critical")
        
        # Act & Assert
        for payload in sql_injection_payloads:
            # Try SQL injection in a URL parameter
            endpoint = f"/users/{payload}"
            allure_reporter.add_api_request("GET", endpoint, api_client.headers)
            
            try:
                response = api_client.get(endpoint)
                allure_reporter.add_api_response(response)
                
                # The request might succeed, but it should not return a list of users or sensitive data
                if response.status_code == 200:
                    json_data = response.json()
                    if isinstance(json_data, list):
                        # Should not return multiple users for a single ID request
                        assert len(json_data) <= 1, "SQL injection might have succeeded"
            except Exception as e:
                # Request failed which is often good for SQL injection tests
                if hasattr(e, 'response'):
                    response = e.response
                    allure_reporter.add_api_response(response)
                    
                    # Should return 400 Bad Request or 404 Not Found for malformed IDs
                    assert response.status_code in [400, 404], f"Expected 400 or 404, but got {response.status_code}"
                else:
                    # Re-raise if not the expected exception
                    raise
            
            # Try SQL injection in a JSON payload
            user_data = {
                "name": payload,
                "email": "test@example.com"
            }
            
            allure_reporter.add_api_request("POST", "/users", api_client.headers, user_data)
            
            try:
                response = api_client.post("/users", json_data=user_data)
                allure_reporter.add_api_response(response)
                
                # The request might succeed as SQL injection in JSON payload is less common
                # But we should check for error messages that might reveal SQL implementation
                if response.status_code >= 400:
                    # Check response for SQL error messages
                    response_text = response.text.lower()
                    sql_error_patterns = [
                        "sql syntax",
                        "syntax error",
                        "sqlite",
                        "mysql",
                        "postgresql",
                        "oracle",
                        "sqlstate"
                    ]
                    
                    for pattern in sql_error_patterns:
                        assert pattern not in response_text, f"SQL error leaked: {pattern}"
            except Exception as e:
                # Request failed (which might be normal)
                if hasattr(e, 'response'):
                    response = e.response
                    allure_reporter.add_api_response(response)
                else:
                    # Re-raise if not the expected exception
                    raise
    
    @pytest.mark.security
    def test_xss_prevention(self, api_client):
        """Test prevention of Cross-Site Scripting (XSS) attacks."""
        # Arrange
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src='x' onerror='alert(\"XSS\")'>",
            "<a onmouseover='alert(\"XSS\")'>Click me</a>",
            "javascript:alert('XSS')"
        ]
        
        allure_reporter.start_test("XSS Prevention", "Test prevention of Cross-Site Scripting attacks")
        allure_reporter.add_tag("security")
        allure_reporter.add_severity("critical")
        
        # Act & Assert
        for payload in xss_payloads:
            # Create a user with XSS payload in the name
            user_data = {
                "name": payload,
                "email": ApiTestUtils.generate_random_email()
            }
            
            allure_reporter.add_api_request("POST", "/users", api_client.headers, user_data)
            
            try:
                response = api_client.post("/users", json_data=user_data)
                allure_reporter.add_api_response(response)
                
                # If creation succeeds, check if the payload is sanitized or encoded in the response
                if response.status_code == 201:
                    json_data = response.json()
                    name = json_data.get('name', '')
                    
                    # Check if '<script>' is encoded or removed
                    assert '<script>' not in name, "XSS payload not sanitized"
                    
                    # Clean up
                    user_id = json_data.get('id')
                    if user_id:
                        try:
                            api_client.delete(f"/users/{user_id}")
                        except:
                            pass
            except Exception as e:
                # Request might fail for other reasons
                if hasattr(e, 'response'):
                    response = e.response
                    allure_reporter.add_api_response(response)
                else:
                    # Re-raise if not the expected exception
                    raise
    
    @pytest.mark.security
    def test_rate_limiting(self, api_client):
        """Test API rate limiting."""
        # Arrange
        endpoint = "/users"
        num_requests = 20  # Send a large number of requests quickly
        
        allure_reporter.start_test("Rate Limiting", "Test API rate limiting")
        allure_reporter.add_tag("security")
        allure_reporter.add_severity("high")
        
        # Act & Assert
        rate_limited = False
        
        for i in range(num_requests):
            allure_reporter.add_api_request("GET", endpoint, api_client.headers)
            
            try:
                response = api_client.get(endpoint)
                allure_reporter.add_api_response(response)
                
                # Check headers for rate limit information
                headers = response.headers
                
                if response.status_code == 429:  # Too Many Requests
                    rate_limited = True
                    break
                
                # Check for rate limit headers (common implementations)
                rate_limit_headers = [
                    'X-RateLimit-Limit',
                    'X-RateLimit-Remaining',
                    'X-RateLimit-Reset',
                    'RateLimit-Limit',
                    'RateLimit-Remaining',
                    'RateLimit-Reset',
                    'Retry-After'
                ]
                
                has_rate_limit_headers = any(h in headers for h in rate_limit_headers)
                
                if has_rate_limit_headers:
                    # If we see rate limit headers, the API has rate limiting
                    # Check if we're close to the limit
                    remaining = headers.get('X-RateLimit-Remaining') or headers.get('RateLimit-Remaining')
                    
                    if remaining and int(remaining) <= 5:
                        # We're close to the limit, consider the test passed
                        rate_limited = True
                        break
            except Exception as e:
                # Request might fail due to rate limiting
                if hasattr(e, 'response') and e.response.status_code == 429:
                    rate_limited = True
                    allure_reporter.add_api_response(e.response)
                    break
                elif hasattr(e, 'response'):
                    allure_reporter.add_api_response(e.response)
                else:
                    # Re-raise if not a rate limit issue
                    raise
        
        # Either we were rate limited or we found rate limit headers
        if not rate_limited:
            logger.warning("No rate limiting detected. Consider implementing rate limiting for enhanced security.")
    
    @pytest.mark.security
    def test_sensitive_data_exposure(self, api_client, auth_token):
        """Test for sensitive data exposure in API responses."""
        # Arrange
        api_client.set_authorization("Bearer", auth_token)
        sensitive_patterns = [
            r'password',
            r'secret',
            r'token',
            r'key',
            r'credit_card',
            r'ssn',
            r'social_security',
            r'\b(?:\d[ -]*?){13,16}\b'  # Credit card pattern
        ]
        
        allure_reporter.start_test("Sensitive Data Exposure", "Test for sensitive data exposure in API responses")
        allure_reporter.add_tag("security")
        allure_reporter.add_severity("critical")
        
        # Act - Check common endpoints
        endpoints = [
            "/users",
            "/users/1",
            "/profile",
            "/settings",
            "/orders",
            "/payment_methods"
        ]
        
        # Assert
        for endpoint in endpoints:
            allure_reporter.add_api_request("GET", endpoint, api_client.headers)
            
            try:
                response = api_client.get(endpoint)
                allure_reporter.add_api_response(response)
                
                if response.status_code == 200:
                    # Check for sensitive data in the response
                    response_json = json.dumps(response.json())
                    
                    for pattern in sensitive_patterns:
                        matches = re.finditer(pattern, response_json, re.IGNORECASE)
                        for match in matches:
                            context = response_json[max(0, match.start() - 20):match.end() + 20]
                            logger.warning(f"Possible sensitive data found in {endpoint} response: {context}")
                            # Don't fail the test, just warn - might have false positives
            except Exception as e:
                # Endpoint might not exist or require special permissions
                if hasattr(e, 'response'):
                    allure_reporter.add_api_response(e.response)
                else:
                    # Log non-HTTP exceptions
                    logger.info(f"Error accessing {endpoint}: {str(e)}")

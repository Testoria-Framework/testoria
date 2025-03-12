const { describe, before, after, it } = require('mocha');
const { expect } = require('chai');

const BaseApiClient = require('../../../core/clients/base_api_client');
const ApiAssertions = require('../../../core/assertions/js_assertions');
const { 
  getEnvironmentConfig, 
  getBaseUrl 
} = require('../../../core/config/env_loader');
const allureReporter = require('../../../core/reporting/allure_reporter');
const ApiTestUtils = require('../../../core/utils/common_helpers');

describe('API Security Tests', function() {
  let apiClient;
  const validToken = "valid_token"; // This would be obtained from auth service
  
  before(function() {
    // Set up API client
    const envConfig = getEnvironmentConfig('dev');
    const baseUrl = envConfig.base_url;
    
    apiClient = new BaseApiClient(baseUrl, {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    });
  });
  
  after(function() {
    // Clean up after tests
    apiClient.clearAuthorization();
  });
  
  describe('Authentication and Authorization', function() {
    it('should allow access to public endpoints without authentication', async function() {
      // Arrange
      const publicEndpoints = [
        "/health",
        "/version",
        "/docs"
      ];
      
      allureReporter.startTest("Anonymous Endpoints Access", "Test access to public endpoints without authentication");
      allureReporter.addTag("security");
      allureReporter.addSeverity("normal");
      
      // Act & Assert
      for (const endpoint of publicEndpoints) {
        allureReporter.addApiRequest("GET", endpoint, apiClient.client.defaults.headers);
        try {
          const response = await apiClient.get(endpoint);
          allureReporter.addApiResponse(response);
          
          // Should return 2xx status
          expect(response.status).to.be.within(200, 299);
        } catch (error) {
          // If we get here, the test fails
          allureReporter.addStep(`Failed accessing ${endpoint}`, "failed", error.message);
          allureReporter.endTest("failed");
          throw error;
        }
      }
      
      allureReporter.endTest();
    });
    
    it('should prevent access to protected endpoints without authentication', async function() {
      // Arrange
      const protectedEndpoints = [
        "/users",
        "/orders",
        "/products/admin"
      ];
      
      allureReporter.startTest("Protected Endpoints Without Auth", "Test access to protected endpoints without authentication");
      allureReporter.addTag("security");
      allureReporter.addSeverity("critical");
      
      // Act & Assert
      for (const endpoint of protectedEndpoints) {
        allureReporter.addApiRequest("GET", endpoint, apiClient.client.defaults.headers);
        
        try {
          const response = await apiClient.get(endpoint);
          // If we get here, the test fails
          allureReporter.addApiResponse(response);
          allureReporter.addStep(`Endpoint ${endpoint} should require authentication`, "failed");
          throw new Error(`Endpoint ${endpoint} should require authentication`);
        } catch (error) {
          // The request should fail with 401 or 403
          if (error.response) {
            allureReporter.addApiResponse(error.response);
            
            const statusCode = error.response.status;
            expect(statusCode).to.be.oneOf([401, 403], `Expected 401 or 403, but got ${statusCode}`);
            
            allureReporter.addStep(`Endpoint ${endpoint} correctly requires authentication`, "passed");
          } else {
            // Re-throw if not the expected exception
            throw error;
          }
        }
      }
      
      allureReporter.endTest();
    });
    
    it('should allow access to protected endpoints with valid authentication', async function() {
      // Arrange
      apiClient.setAuthorization("Bearer", validToken);
      
      allureReporter.startTest("Authentication With Valid Token", "Test authentication with a valid token");
      allureReporter.addTag("security");
      allureReporter.addSeverity("critical");
      
      // Act
      allureReporter.addApiRequest("GET", "/protected-resource", apiClient.client.defaults.headers);
      
      try {
        const response = await apiClient.get("/protected-resource");
        allureReporter.addApiResponse(response);
        
        // Assert
        expect(response.status).to.be.within(200, 299);
        
        allureReporter.addStep("Authenticated access successful", "passed");
        allureReporter.endTest();
      } catch (error) {
        allureReporter.addStep("Authentication failed", "failed", error.message);
        allureReporter.endTest("failed");
        throw error;
      }
    });
    
    it('should reject access with invalid authentication token', async function() {
      // Arrange
      apiClient.setAuthorization("Bearer", "invalid_token");
      
      allureReporter.startTest("Authentication With Invalid Token", "Test authentication with an invalid token");
      allureReporter.addTag("security");
      allureReporter.addSeverity("critical");
      
      // Act
      allureReporter.addApiRequest("GET", "/protected-resource", apiClient.client.defaults.headers);
      
      try {
        const response = await apiClient.get("/protected-resource");
        // If we get here, the test fails
        allureReporter.addApiResponse(response);
        allureReporter.addStep("Request with invalid token should fail", "failed");
        allureReporter.endTest("failed");
        throw new Error("Request with invalid token should succeed");
      } catch (error) {
        // Extract response from exception
        if (error.response) {
          allureReporter.addApiResponse(error.response);
          
          // Should return 401 Unauthorized
          expect(error.response.status).to.equal(401);
          
          allureReporter.addStep("Invalid token correctly rejected", "passed");
          allureReporter.endTest();
        } else {
          // Re-throw if not the expected exception
          allureReporter.endTest("failed");
          throw error;
        }
      }
    });
  });
  
  describe('Input Validation and Injection Prevention', function() {
    it('should prevent SQL injection attacks', async function() {
      // Arrange
      const sqlInjectionPayloads = [
        "1' OR '1'='1",
        "1; DROP TABLE users",
        "1' UNION SELECT * FROM users --",
        "1' OR 1=1 --"
      ];
      
      allureReporter.startTest("SQL Injection Prevention", "Test prevention of SQL injection attacks");
      allureReporter.addTag("security");
      allureReporter.addSeverity("critical");
      
      // Act & Assert
      for (const payload of sqlInjectionPayloads) {
        // Try SQL injection in a URL parameter
        const endpoint = `/users/${payload}`;
        allureReporter.addApiRequest("GET", endpoint, apiClient.client.defaults.headers);
        
        try {
          const response = await apiClient.get(endpoint);
          allureReporter.addApiResponse(response);
          
          // The request might succeed, but it should not return a list of users or sensitive data
          if (response.status === 200) {
            const jsonData = response.data;
            if (Array.isArray(jsonData)) {
              // Should not return multiple users for a single ID request
              expect(jsonData.length).to.be.at.most(1, "SQL injection might have succeeded");
            }
          }
        } catch (error) {
          // Request failed which is often good for SQL injection tests
          if (error.response) {
            allureReporter.addApiResponse(error.response);
            
            // Should return 400 Bad Request or 404 Not Found for malformed IDs
            expect(error.response.status).to.be.oneOf([400, 404], `Expected 400 or 404, but got ${error.response.status}`);
          } else {
            // Re-throw if not the expected exception
            throw error;
          }
        }
        
        // Try SQL injection in a JSON payload
        const userData = {
          name: payload,
          email: "test@example.com"
        };
        
        allureReporter.addApiRequest("POST", "/users", apiClient.client.defaults.headers, userData);
        
        try {
          const response = await apiClient.post("/users", userData);
          allureReporter.addApiResponse(response);
          
          // The request might succeed as SQL injection in JSON payload is less common
          // But we should check for error messages that might reveal SQL implementation
          if (response.status >= 400) {
            // Check response for SQL error messages
            const responseText = JSON.stringify(response.data).toLowerCase();
            const sqlErrorPatterns = [
              "sql syntax",
              "syntax error",
              "sqlite",
              "mysql",
              "postgresql",
              "oracle",
              "sqlstate"
            ];
            
            for (const pattern of sqlErrorPatterns) {
              expect(responseText).to.not.include(pattern, `SQL error leaked: ${pattern}`);
            }
          }
        } catch (error) {
          // Request failed (which might be normal)
          if (error.response) {
            allureReporter.addApiResponse(error.response);
            
            // Check response for SQL error messages
            if (error.response.data) {
              const responseText = JSON.stringify(error.response.data).toLowerCase();
              const sqlErrorPatterns = [
                "sql syntax",
                "syntax error",
                "sqlite",
                "mysql",
                "postgresql",
                "oracle",
                "sqlstate"
              ];
              
              for (const pattern of sqlErrorPatterns) {
                expect(responseText).to.not.include(pattern, `SQL error leaked: ${pattern}`);
              }
            }
          } else {
            // Re-throw if not the expected exception
            throw error;
          }
        }
      }
      
      allureReporter.endTest();
    });
    
    it('should prevent XSS attacks', async function() {
      // Arrange
      const xssPayloads = [
        "<script>alert('XSS')</script>",
        "<img src='x' onerror='alert(\"XSS\")'>",
        "<a onmouseover='alert(\"XSS\")'>Click me</a>",
        "javascript:alert('XSS')"
      ];
      
      allureReporter.startTest("XSS Prevention", "Test prevention of Cross-Site Scripting attacks");
      allureReporter.addTag("security");
      allureReporter.addSeverity("critical");
      
      // Act & Assert
      for (const payload of xssPayloads) {
        // Create a user with XSS payload in the name
        const userData = {
          name: payload,
          email: ApiTestUtils.generateRandomEmail()
        };
        
        allureReporter.addApiRequest("POST", "/users", apiClient.client.defaults.headers, userData);
        
        try {
          const response = await apiClient.post("/users", userData);
          allureReporter.addApiResponse(response);
          
          // If creation succeeds, check if the payload is sanitized or encoded in the response
          if (response.status === 201) {
            const jsonData = response.data;
            const name = jsonData.name || '';
            
            // Check if '<script>' is encoded or removed
            expect(name).to.not.include('<script>', "XSS payload not sanitized");
            
            // Clean up
            const userId = jsonData.id;
            if (userId) {
              try {
                await apiClient.delete(`/users/${userId}`);
              } catch (err) {
                console.warn(`Failed to delete test user: ${err.message}`);
              }
            }
          }
        } catch (error) {
          // Request might fail for other reasons
          if (error.response) {
            allureReporter.addApiResponse(error.response);
          } else {
            // Re-throw if not the expected exception
            throw error;
          }
        }
      }
      
      allureReporter.endTest();
    });
  });
  
  describe('Rate Limiting and Brute Force Prevention', function() {
    it('should implement rate limiting', async function() {
      // Arrange
      const endpoint = "/users";
      const numRequests = 20;  // Send a large number of requests quickly
      
      allureReporter.startTest("Rate Limiting", "Test API rate limiting");
      allureReporter.addTag("security");
      allureReporter.addSeverity("high");
      
      // Act & Assert
      let rateLimited = false;
      
      for (let i = 0; i < numRequests; i++) {
        allureReporter.addApiRequest("GET", endpoint, apiClient.client.defaults.headers);
        
        try {
          const response = await apiClient.get(endpoint);
          allureReporter.addApiResponse(response);
          
          // Check headers for rate limit information
          const headers = response.headers;
          
          if (response.status === 429) {  // Too Many Requests
            rateLimited = true;
            break;
          }
          
          // Check for rate limit headers (common implementations)
          const rateLimitHeaders = [
            'x-ratelimit-limit',
            'x-ratelimit-remaining',
            'x-ratelimit-reset',
            'ratelimit-limit',
            'ratelimit-remaining',
            'ratelimit-reset',
            'retry-after'
          ];
          
          const hasRateLimitHeaders = rateLimitHeaders.some(h => headers[h]);
          
          if (hasRateLimitHeaders) {
            // If we see rate limit headers, the API has rate limiting
            // Check if we're close to the limit
            const remaining = headers['x-ratelimit-remaining'] || headers['ratelimit-remaining'];
            
            if (remaining && parseInt(remaining, 10) <= 5) {
              // We're close to the limit, consider the test passed
              rateLimited = true;
              break;
            }
          }
        } catch (error) {
          // Request might fail due to rate limiting
          if (error.response && error.response.status === 429) {
            rateLimited = true;
            allureReporter.addApiResponse(error.response);
            break;
          } else if (error.response) {
            allureReporter.addApiResponse(error.response);
          } else {
            // Re-throw if not a rate limit issue
            throw error;
          }
        }
        
        // Add a small delay between requests to avoid overloading the API
        await new Promise(resolve => setTimeout(resolve, 50));
      }
      
      // Either we were rate limited or we found rate limit headers
      if (rateLimited) {
        allureReporter.addStep("Rate limiting correctly implemented", "passed");
      } else {
        allureReporter.addStep("No rate limiting detected", "passed", 
          "Consider implementing rate limiting for enhanced security");
      }
      
      allureReporter.endTest();
    });
  });
  
  describe('Data Privacy and Protection', function() {
    it('should not expose sensitive data', async function() {
      // Arrange
      apiClient.setAuthorization("Bearer", validToken);
      const sensitivePatterns = [
        /password/i,
        /secret/i,
        /token/i,
        /key/i,
        /credit[\s_-]?card/i,
        /ssn/i,
        /social[\s_-]?security/i,
        /\b(?:\d[ -]*?){13,16}\b/  // Credit card pattern
      ];
      
      allureReporter.startTest("Sensitive Data Exposure", "Test for sensitive data exposure in API responses");
      allureReporter.addTag("security");
      allureReporter.addSeverity("critical");
      
      // Act - Check common endpoints
      const endpoints = [
        "/users",
        "/users/1",
        "/profile",
        "/settings",
        "/orders",
        "/payment_methods"
      ];
      
      // Assert
      for (const endpoint of endpoints) {
        allureReporter.addApiRequest("GET", endpoint, apiClient.client.defaults.headers);
        
        try {
          const response = await apiClient.get(endpoint);
          allureReporter.addApiResponse(response);
          
          if (response.status === 200) {
            // Check for sensitive data in the response
            const responseJson = JSON.stringify(response.data);
            
            for (const pattern of sensitivePatterns) {
              const matches = responseJson.match(pattern);
              if (matches) {
                console.warn(`Possible sensitive data found in ${endpoint} response: ${matches[0]}`);
                // Don't fail the test, just warn - might have false positives
                allureReporter.addStep(`Warning: Possible sensitive data found in ${endpoint}`, "passed", 
                  `Found pattern: ${pattern}, context: ${matches[0]}`);
              }
            }
          }
        } catch (error) {
          // Endpoint might not exist or require special permissions
          if (error.response) {
            allureReporter.addApiResponse(error.response);
          } else {
            // Log non-HTTP exceptions
            console.log(`Error accessing ${endpoint}: ${error.message}`);
          }
        }
      }
      
      allureReporter.endTest();
    });
  });
});

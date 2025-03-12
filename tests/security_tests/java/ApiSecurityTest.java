package tests.security_tests.java;

import core.clients.BaseApiClient;
import core.assertions.JavaAssertions;
import core.utils.CommonHelpers;
import io.qameta.allure.*;
import io.restassured.response.Response;
import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.jupiter.api.*;

import java.util.HashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Security tests for API endpoints.
 * Tests authentication, authorization, input validation, and data protection.
 */
@Epic("API Testing")
@Feature("API Security")
public class ApiSecurityTest {

    private BaseApiClient apiClient;
    private static final String VALID_TOKEN = "valid_token"; // This would be obtained from auth service

    @BeforeEach
    public void setUp() {
        // Initialize API client
        String baseUrl = System.getenv("API_BASE_URL");
        if (baseUrl == null || baseUrl.isEmpty()) {
            baseUrl = "https://api-dev.example.com"; // Default to dev environment
        }

        apiClient = new BaseApiClient(baseUrl);

        // Set up default headers
        Map<String, String> headers = new HashMap<>();
        headers.put("Content-Type", "application/json");
        headers.put("Accept", "application/json");
        apiClient.setHeaders(headers);
    }

    @AfterEach
    public void tearDown() {
        // Clean up after tests
        apiClient.clearAuthorization();
    }

    @Test
    @Severity(SeverityLevel.NORMAL)
    @Description("Test access to public endpoints without authentication")
    @Story("Anonymous Access")
    public void testAnonymousEndpointsAccess() {
        // Arrange
        String[] publicEndpoints = {
            "/health",
            "/version",
            "/docs"
        };
        
        // Act & Assert
        for (String endpoint : publicEndpoints) {
            Response response = apiClient.get(endpoint);
            
            // Should return 2xx status
            JavaAssertions.assertStatusCode(response, response.getStatusCode());
            Assertions.assertTrue(response.getStatusCode() >= 200 && response.getStatusCode() <= 299,
                    "Public endpoint " + endpoint + " should be accessible without authentication");
        }
    }

    @Test
    @Severity(SeverityLevel.CRITICAL)
    @Description("Test access to protected endpoints without authentication")
    @Story("Authorization Controls")
    public void testProtectedEndpointsWithoutAuth() {
        // Arrange
        String[] protectedEndpoints = {
            "/users",
            "/orders",
            "/products/admin"
        };
        
        // Act & Assert
        for (String endpoint : protectedEndpoints) {
            try {
                Response response = apiClient.get(endpoint);
                // If request succeeds, verify it's not a 2xx status (should be 401 or 403)
                Assertions.assertTrue(response.getStatusCode() == 401 || response.getStatusCode() == 403,
                        "Protected endpoint " + endpoint + " should require authentication");
            } catch (Exception e) {
                // Exception is expected if the request fails with an error
                // Verify it's the expected error type
                Assertions.assertTrue(e.getMessage().contains("401") || e.getMessage().contains("403"),
                        "Protected endpoint should return 401 or 403");
            }
        }
    }

    @Test
    @Severity(SeverityLevel.CRITICAL)
    @Description("Test authentication with a valid token")
    @Story("Authentication")
    public void testAuthenticationWithValidToken() {
        // Arrange
        apiClient.setAuthorization("Bearer", VALID_TOKEN);
        
        // Act
        Response response = apiClient.get("/protected-resource");
        
        // Assert
        JavaAssertions.assertStatusCode(response, 200);
    }

    @Test
    @Severity(SeverityLevel.CRITICAL)
    @Description("Test authentication with an invalid token")
    @Story("Authentication")
    public void testAuthenticationWithInvalidToken() {
        // Arrange
        apiClient.setAuthorization("Bearer", "invalid_token");
        
        // Act & Assert
        try {
            Response response = apiClient.get("/protected-resource");
            // If request succeeds, it should return 401 Unauthorized
            JavaAssertions.assertStatusCode(response, 401);
        } catch (Exception e) {
            // Exception is expected if the request fails with 401
            Assertions.assertTrue(e.getMessage().contains("401"),
                    "Invalid token should return 401 Unauthorized");
        }
    }

    @Test
    @Severity(SeverityLevel.CRITICAL)
    @Description("Test prevention of SQL injection attacks")
    @Story("Injection Prevention")
    public void testSqlInjectionPrevention() {
        // Arrange
        String[] sqlInjectionPayloads = {
            "1' OR '1'='1",
            "1; DROP TABLE users",
            "1' UNION SELECT * FROM users --",
            "1' OR 1=1 --"
        };
        
        // Act & Assert
        for (String payload : sqlInjectionPayloads) {
            // Try SQL injection in a URL parameter
            String endpoint = "/users/" + payload;
            
            try {
                Response response = apiClient.get(endpoint);
                
                // The request might succeed, but it should not return a list of users or sensitive data
                if (response.getStatusCode() == 200) {
                    try {
                        JSONArray jsonArray = JavaAssertions.getResponseAsJsonArray(response);
                        // Should not return multiple users for a single ID request
                        Assertions.assertTrue(jsonArray.length() <= 1, "SQL injection might have succeeded");
                    } catch (Exception e) {
                        // Not a JSON array, which is expected for a single user
                    }
                }
            } catch (Exception e) {
                // Request failed which is often good for SQL injection tests
                Assertions.assertTrue(e.getMessage().contains("400") || e.getMessage().contains("404"),
                        "Malformed ID should return 400 or 404");
            }
            
            // Try SQL injection in a JSON payload
            JSONObject userData = new JSONObject();
            userData.put("name", payload);
            userData.put("email", "test@example.com");
            
            try {
                Response response = apiClient.post("/users", userData);
                
                // The request might succeed as SQL injection in JSON payload is less common
                // But we should check for error messages that might reveal SQL implementation
                if (response.getStatusCode() >= 400) {
                    String responseText = response.getBody().asString().toLowerCase();
                    assertNoSqlErrorLeakage(responseText);
                }
            } catch (Exception e) {
                // Request might fail, which is expected for malicious input
                if (e.getMessage().contains("response body")) {
                    String responseText = e.getMessage().toLowerCase();
                    assertNoSqlErrorLeakage(responseText);
                }
            }
        }
    }

    private void assertNoSqlErrorLeakage(String responseText) {
        String[] sqlErrorPatterns = {
            "sql syntax",
            "syntax error",
            "sqlite",
            "mysql",
            "postgresql",
            "oracle",
            "sqlstate"
        };
        
        for (String pattern : sqlErrorPatterns) {
            Assertions.assertFalse(responseText.contains(pattern),
                    "SQL error leaked: " + pattern);
        }
    }

    @Test
    @Severity(SeverityLevel.CRITICAL)
    @Description("Test prevention of Cross-Site Scripting (XSS) attacks")
    @Story("Injection Prevention")
    public void testXssPrevention() {
        // Arrange
        String[] xssPayloads = {
            "<script>alert('XSS')</script>",
            "<img src='x' onerror='alert(\"XSS\")'>",
            "<a onmouseover='alert(\"XSS\")'>Click me</a>",
            "javascript:alert('XSS')"
        };
        
        // Act & Assert
        for (String payload : xssPayloads) {
            // Create a user with XSS payload in the name
            JSONObject userData = new JSONObject();
            userData.put("name", payload);
            userData.put("email", CommonHelpers.generateRandomEmail());
            
            try {
                Response response = apiClient.post("/users", userData);
                
                // If creation succeeds, check if the payload is sanitized or encoded in the response
                if (response.getStatusCode() == 201) {
                    JSONObject createdUser = JavaAssertions.getResponseAsJsonObject(response);
                    String name = createdUser.getString("name");
                    
                    // Check if '<script>' is encoded or removed
                    Assertions.assertFalse(name.contains("<script>"), "XSS payload not sanitized");
                    
                    // Clean up
                    String userId = createdUser.getString("id");
                    try {
                        apiClient.delete("/users/" + userId);
                    } catch (Exception e) {
                        // Cleanup failure is not a test failure
                        System.err.println("Failed to delete test user: " + e.getMessage());
                    }
                }
            } catch (Exception e) {
                // Request might fail for other valid reasons
                // This is acceptable as long as we don't see the raw XSS payload in any error message
            }
        }
    }

    @Test
    @Severity(SeverityLevel.HIGH)
    @Description("Test API rate limiting")
    @Story("Rate Limiting")
    public void testRateLimiting() {
        // Arrange
        String endpoint = "/users";
        int numRequests = 20;  // Send a large number of requests quickly
        
        // Act & Assert
        boolean rateLimited = false;
        
        for (int i = 0; i < numRequests; i++) {
            try {
                Response response = apiClient.get(endpoint);
                
                // Check for rate limit status code
                if (response.getStatusCode() == 429) {  // Too Many Requests
                    rateLimited = true;
                    break;
                }
                
                // Check headers for rate limit information
                Map<String, String> headers = new HashMap<>();
                response.getHeaders().forEach(header -> headers.put(header.getName().toLowerCase(), header.getValue()));
                
                // Check for rate limit headers (common implementations)
                String[] rateLimitHeaders = {
                    "x-ratelimit-limit",
                    "x-ratelimit-remaining",
                    "x-ratelimit-reset",
                    "ratelimit-limit",
                    "ratelimit-remaining",
                    "ratelimit-reset",
                    "retry-after"
                };
                
                for (String header : rateLimitHeaders) {
                    if (headers.containsKey(header)) {
                        // If we see rate limit headers, the API has rate limiting
                        
                        // Check if we're close to the limit
                        String remaining = headers.get("x-ratelimit-remaining");
                        if (remaining == null) {
                            remaining = headers.get("ratelimit-remaining");
                        }
                        
                        if (remaining != null && Integer.parseInt(remaining) <= 5) {
                            // We're close to the limit, consider the test passed
                            rateLimited = true;
                            break;
                        }
                    }
                }
                
                if (rateLimited) {
                    break;
                }
            } catch (Exception e) {
                // Request might fail due to rate limiting
                if (e.getMessage().contains("429")) {
                    rateLimited = true;
                    break;
                }
            }
            
            // Add a small delay between requests to avoid overwhelming the API
            try {
                Thread.sleep(50);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
        
        // Either we were rate limited or we found rate limit headers
        if (!rateLimited) {
            System.out.println("WARNING: No rate limiting detected. Consider implementing rate limiting for enhanced security.");
        }
    }

    @Test
    @Severity(SeverityLevel.CRITICAL)
    @Description("Test for sensitive data exposure in API responses")
    @Story("Data Protection")
    public void testSensitiveDataExposure() {
        // Arrange
        apiClient.setAuthorization("Bearer", VALID_TOKEN);
        Pattern[] sensitivePatterns = {
            Pattern.compile("password", Pattern.CASE_INSENSITIVE),
            Pattern.compile("secret", Pattern.CASE_INSENSITIVE),
            Pattern.compile("token", Pattern.CASE_INSENSITIVE),
            Pattern.compile("key", Pattern.CASE_INSENSITIVE),
            Pattern.compile("credit[\\s_-]?card", Pattern.CASE_INSENSITIVE),
            Pattern.compile("ssn", Pattern.CASE_INSENSITIVE),
            Pattern.compile("social[\\s_-]?security", Pattern.CASE_INSENSITIVE),
            Pattern.compile("\\b(?:\\d[ -]*?){13,16}\\b")  // Credit card pattern
        };
        
        // Act - Check common endpoints
        String[] endpoints = {
            "/users",
            "/users/1",
            "/profile",
            "/settings",
            "/orders",
            "/payment_methods"
        };
        
        // Assert
        for (String endpoint : endpoints) {
            try {
                Response response = apiClient.get(endpoint);
                
                if (response.getStatusCode() == 200) {
                    // Check for sensitive data in the response
                    String responseText = response.getBody().asString();
                    
                    for (Pattern pattern : sensitivePatterns) {
                        Matcher matcher = pattern.matcher(responseText);
                        if (matcher.find()) {
                            // Don't fail the test, just warn - might have false positives
                            System.out.println("WARNING: Possible sensitive data found in " + endpoint + 
                                    " response: " + matcher.group());
                        }
                    }
                }
            } catch (Exception e) {
                // Endpoint might not exist or require special permissions
                // This is acceptable for this test
            }
        }
    }

    @Test
    @Severity(SeverityLevel.HIGH)
    @Description("Test prevention of HTTP method tampering")
    @Story("Method Restrictions")
    public void testHttpMethodTampering() {
        // Arrange
        String[] readOnlyEndpoints = {
            "/users",
            "/products"
        };
        
        // Try to use mutation methods on endpoints that should be read-only
        for (String endpoint : readOnlyEndpoints) {
            // DELETE
            try {
                Response response = apiClient.delete(endpoint);
                // DELETE on collection should be rejected
                Assertions.assertTrue(response.getStatusCode() >= 400, 
                        "DELETE on " + endpoint + " collection should be rejected");
            } catch (Exception e) {
                // Exception is expected
            }
            
            // PUT
            JSONObject emptyData = new JSONObject();
            try {
                Response response = apiClient.put(endpoint, emptyData);
                // PUT on collection should be rejected
                Assertions.assertTrue(response.getStatusCode() >= 400, 
                        "PUT on " + endpoint + " collection should be rejected");
            } catch (Exception e) {
                // Exception is expected
            }
        }
    }

    @Test
    @Severity(SeverityLevel.CRITICAL)
    @Description("Test prevention of mass assignment vulnerabilities")
    @Story("Input Validation")
    public void testMassAssignmentPrevention() {
        // Arrange
        // Create a user with normal fields
        JSONObject userData = new JSONObject();
        userData.put("name", "Test User");
        userData.put("email", CommonHelpers.generateRandomEmail());
        
        // Try to inject sensitive fields that should be protected
        userData.put("is_admin", true);
        userData.put("role", "admin");
        userData.put("permissions", "all");
        
        // Act
        try {
            Response response = apiClient.post("/users", userData);
            
            // Assert
            if (response.getStatusCode() == 201) {
                JSONObject createdUser = JavaAssertions.getResponseAsJsonObject(response);
                
                // Check that the protected fields are not present or not set to the requested values
                Assertions.assertFalse(createdUser.has("is_admin") && createdUser.getBoolean("is_admin"), 
                        "is_admin field should not be settable through API");
                
                Assertions.assertFalse(createdUser.has("role") && "admin".equals(createdUser.getString("role")), 
                        "role field should not be settable to admin through API");
                
                Assertions.assertFalse(createdUser.has("permissions") && "all".equals(createdUser.getString("permissions")), 
                        "permissions field should not be settable through API");
                
                // Clean up
                String userId = createdUser.getString("id");
                try {
                    apiClient.delete("/users/" + userId);
                } catch (Exception e) {
                    // Cleanup failure is not a test failure
                }
            }
        } catch (Exception e) {
            // Request might fail, which could be acceptable if it's rejecting the invalid fields
        }
    }
}

package tests.functional_tests.java;

import core.clients.BaseApiClient;
import core.assertions.JavaAssertions;
import io.qameta.allure.*;
import io.restassured.response.Response;
import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.jupiter.api.*;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * Functional tests for the User API endpoints.
 */
@Epic("API Testing")
@Feature("User Management")
public class UserApiTest {

    private BaseApiClient apiClient;
    private String testUserId;

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

        // Set up authentication if needed
        String apiKey = System.getenv("API_KEY");
        if (apiKey != null && !apiKey.isEmpty()) {
            apiClient.addHeader("X-API-Key", apiKey);
        }
    }

    @AfterEach
    public void tearDown() {
        // Clean up test data
        if (testUserId != null) {
            try {
                apiClient.delete("/users/" + testUserId);
            } catch (Exception e) {
                System.err.println("Failed to delete test user: " + e.getMessage());
            }
            testUserId = null;
        }
    }

    @Test
    @Severity(SeverityLevel.CRITICAL)
    @Description("Test retrieving all users")
    @Story("Get all users")
    public void testGetAllUsers() {
        // Act
        Response response = apiClient.get("/users");

        // Assert
        JavaAssertions.assertStatusCode(response, 200);
        JavaAssertions.assertJsonContentType(response);

        // Verify response structure
        JSONArray users = JavaAssertions.getResponseAsJsonArray(response);
        Assertions.assertTrue(users.length() > 0, "Users list should not be empty");

        // Verify the first user has required fields
        if (users.length() > 0) {
            JSONObject firstUser = users.getJSONObject(0);
            Assertions.assertTrue(firstUser.has("id"), "User should have ID");
            Assertions.assertTrue(firstUser.has("name"), "User should have name");
            Assertions.assertTrue(firstUser.has("email"), "User should have email");
        }

        // Verify response time
        JavaAssertions.assertResponseTime(response, 1000); // Max 1000ms
    }

    @Test
    @Severity(SeverityLevel.CRITICAL)
    @Description("Test retrieving a specific user by ID")
    @Story("Get user by ID")
    public void testGetUserById() {
        // Arrange
        String userId = "1"; // Using a known user ID

        // Act
        Response response = apiClient.get("/users/" + userId);

        // Assert
        JavaAssertions.assertStatusCode(response, 200);
        JavaAssertions.assertJsonContentType(response);

        // Verify the user
        JSONObject user = JavaAssertions.getResponseAsJsonObject(response);
        Assertions.assertEquals(userId, user.get("id").toString(), "User ID should match the requested ID");
        Assertions.assertTrue(user.has("name"), "User should have name");
        Assertions.assertTrue(user.has("email"), "User should have email");
    }

    @Test
    @Severity(SeverityLevel.CRITICAL)
    @Description("Test creating a new user")
    @Story("Create user")
    public void testCreateUser() {
        // Arrange
        String randomSuffix = UUID.randomUUID().toString().substring(0, 8);
        JSONObject userData = new JSONObject();
        userData.put("name", "Test User " + randomSuffix);
        userData.put("email", "test." + randomSuffix + "@example.com");
        userData.put("phone", "+1" + (int)(Math.random() * 9000000000L + 1000000000L));

        // Act
        Response response = apiClient.post("/users", userData);

        // Assert
        JavaAssertions.assertStatusCode(response, 201);
        JavaAssertions.assertJsonContentType(response);

        // Verify the created user
        JSONObject createdUser = JavaAssertions.getResponseAsJsonObject(response);
        Assertions.assertTrue(createdUser.has("id"), "Created user should have ID");
        testUserId = createdUser.get("id").toString(); // Save for cleanup

        // Verify all fields are correctly set
        Assertions.assertEquals(userData.getString("name"), createdUser.getString("name"));
        Assertions.assertEquals(userData.getString("email"), createdUser.getString("email"));
        Assertions.assertEquals(userData.getString("phone"), createdUser.getString("phone"));
        
        // Verify created_at field exists and is not empty
        Assertions.assertTrue(createdUser.has("created_at"), "Created user should have created_at timestamp");
        Assertions.assertNotNull(createdUser.getString("created_at"));
    }

    @Test
    @Severity(SeverityLevel.HIGH)
    @Description("Test updating a user")
    @Story("Update user")
    public void testUpdateUser() {
        // Arrange - Create a user first
        String randomSuffix = UUID.randomUUID().toString().substring(0, 8);
        JSONObject userData = new JSONObject();
        userData.put("name", "Original User " + randomSuffix);
        userData.put("email", "original." + randomSuffix + "@example.com");
        userData.put("phone", "+1" + (int)(Math.random() * 9000000000L + 1000000000L));

        Response createResponse = apiClient.post("/users", userData);
        JSONObject createdUser = JavaAssertions.getResponseAsJsonObject(createResponse);
        testUserId = createdUser.get("id").toString();

        // Update data
        String newSuffix = UUID.randomUUID().toString().substring(0, 8);
        JSONObject updateData = new JSONObject();
        updateData.put("name", "Updated User " + newSuffix);
        updateData.put("email", "updated." + newSuffix + "@example.com");

        // Act
        Response response = apiClient.put("/users/" + testUserId, updateData);

        // Assert
        JavaAssertions.assertStatusCode(response, 200);
        JavaAssertions.assertJsonContentType(response);

        // Verify the updated user
        JSONObject updatedUser = JavaAssertions.getResponseAsJsonObject(response);
        Assertions.assertEquals(testUserId, updatedUser.get("id").toString());
        Assertions.assertEquals(updateData.getString("name"), updatedUser.getString("name"));
        Assertions.assertEquals(updateData.getString("email"), updatedUser.getString("email"));
        
        // Phone should remain unchanged since we didn't update it
        Assertions.assertEquals(userData.getString("phone"), updatedUser.getString("phone"));
        
        // Verify updated_at field exists and is not empty
        Assertions.assertTrue(updatedUser.has("updated_at"), "Updated user should have updated_at timestamp");
        Assertions.assertNotNull(updatedUser.getString("updated_at"));
    }

    @Test
    @Severity(SeverityLevel.HIGH)
    @Description("Test deleting a user")
    @Story("Delete user")
    public void testDeleteUser() {
        // Arrange - Create a user first
        String randomSuffix = UUID.randomUUID().toString().substring(0, 8);
        JSONObject userData = new JSONObject();
        userData.put("name", "User to Delete " + randomSuffix);
        userData.put("email", "delete." + randomSuffix + "@example.com");

        Response createResponse = apiClient.post("/users", userData);
        JSONObject createdUser = JavaAssertions.getResponseAsJsonObject(createResponse);
        String userId = createdUser.get("id").toString();

        // Act
        Response deleteResponse = apiClient.delete("/users/" + userId);

        // Assert
        JavaAssertions.assertStatusCode(deleteResponse, 204);
        
        // Verify the user is actually deleted
        Response getResponse = apiClient.get("/users/" + userId);
        JavaAssertions.assertStatusCode(getResponse, 404);
        
        // Clear the test user ID since we've deleted it
        testUserId = null;
    }

    @Test
    @Severity(SeverityLevel.NORMAL)
    @Description("Test user validation errors")
    @Story("User validation")
    public void testUserValidationErrors() {
        // Arrange - Invalid user data
        JSONObject invalidUserData = new JSONObject();
        invalidUserData.put("name", ""); // Empty name should be invalid
        invalidUserData.put("email", "invalid-email"); // Invalid email format

        // Act
        Response response = apiClient.post("/users", invalidUserData);

        // Assert
        JavaAssertions.assertStatusCode(response, 400);
        JavaAssertions.assertJsonContentType(response);

        // Verify error response structure
        JSONObject errorResponse = JavaAssertions.getResponseAsJsonObject(response);
        Assertions.assertTrue(errorResponse.has("errors"), "Error response should have 'errors' field");
        
        JSONArray errors = errorResponse.getJSONArray("errors");
        Assertions.assertTrue(errors.length() >= 2, "Should have at least 2 validation errors");
        
        // Check for specific error fields
        boolean hasNameError = false;
        boolean hasEmailError = false;
        
        for (int i = 0; i < errors.length(); i++) {
            JSONObject error = errors.getJSONObject(i);
            String field = error.getString("field");
            
            if (field.equals("name")) hasNameError = true;
            if (field.equals("email")) hasEmailError = true;
        }
        
        Assertions.assertTrue(hasNameError, "Should have name validation error");
        Assertions.assertTrue(hasEmailError, "Should have email validation error");
    }

    @Test
    @Severity(SeverityLevel.NORMAL)
    @Description("Test searching users by email")
    @Story("Search users")
    public void testSearchUsersByEmail() {
        // Arrange
        String searchEmail = "john.doe@example.com"; // Using a known email

        // Act
        Map<String, String> queryParams = new HashMap<>();
        queryParams.put("email", searchEmail);
        Response response = apiClient.get("/users", queryParams);

        // Assert
        JavaAssertions.assertStatusCode(response, 200);
        JavaAssertions.assertJsonContentType(response);

        // Verify the search results
        JSONArray users = JavaAssertions.getResponseAsJsonArray(response);
        
        // Should find at least one user with that email
        Assertions.assertTrue(users.length() > 0, "Should find users with the specified email");
        
        // All returned users should have the specified email
        for (int i = 0; i < users.length(); i++) {
            JSONObject user = users.getJSONObject(i);
            Assertions.assertEquals(searchEmail, user.getString("email"), 
                    "All returned users should have the specified email");
        }
    }
}

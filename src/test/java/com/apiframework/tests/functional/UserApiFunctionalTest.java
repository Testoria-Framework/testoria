package com.apiframework.tests.functional;

import io.qameta.allure.*;
import io.restassured.RestAssured;
import io.restassured.http.ContentType;
import io.restassured.response.Response;
import org.junit.jupiter.api.*;

import java.util.HashMap;
import java.util.Map;

import static io.restassured.RestAssured.*;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Functional tests for the User API endpoints.
 */
@Epic("API Testing")
@Feature("User Management")
public class UserApiFunctionalTest {
    private static String baseUrl;
    private static String authToken;
    private String createdUserId;

    @BeforeAll
    public static void setup() {
        // Load configuration
        baseUrl = System.getenv().getOrDefault("API_BASE_URL", "https://api.example.com");
        RestAssured.baseURI = baseUrl;

        // Authenticate and get token
        Map<String, String> authPayload = new HashMap<>();
        authPayload.put("username", "testuser");
        authPayload.put("password", "securePassword123");

        try {
            Response authResponse = given()
                    .contentType(ContentType.JSON)
                    .body(authPayload)
                    .when()
                    .post("/auth/login")
                    .then()
                    .extract().response();

            if (authResponse.statusCode() == 200) {
                authToken = authResponse.jsonPath().getString("token");
            } else {
                System.out.println("Authentication failed, tests will run without auth token");
                authToken = "";
            }
        } catch (Exception e) {
            System.out.println("Error during authentication: " + e.getMessage());
            authToken = "";
        }
    }

    @AfterEach
    public void tearDown() {
        // Clean up test data
        if (createdUserId != null) {
            try {
                given()
                        .contentType(ContentType.JSON)
                        .header("Authorization", "Bearer " + authToken)
                        .when()
                        .delete("/users/" + createdUserId);
            } catch (Exception e) {
                System.err.println("Failed to delete test user: " + e.getMessage());
            }
            createdUserId = null;
        }
    }

    @Test
    @DisplayName("Create New User - Successful")
    @Severity(SeverityLevel.CRITICAL)
    @Description("Test creating a new user with valid data")
    @Story("User Creation")
    public void testCreateUser() {
        // Prepare user data
        Map<String, Object> userData = new HashMap<>();
        userData.put("username", "newuser_" + System.currentTimeMillis());
        userData.put("email", "newuser_" + System.currentTimeMillis() + "@example.com");
        userData.put("first_name", "John");
        userData.put("last_name", "Doe");
        userData.put("age", 30);

        // Create user
        Response createResponse = given()
                .contentType(ContentType.JSON)
                .header("Authorization", "Bearer " + authToken)
                .body(userData)
                .when()
                .post("/users")
                .then()
                .statusCode(201)
                .extract().response();

        // Validate response
        createdUserId = createResponse.jsonPath().getString("id");
        assertNotNull(createdUserId, "User ID should be generated");
        assertEquals(userData.get("username"), createResponse.jsonPath().getString("username"));
        assertEquals(userData.get("email"), createResponse.jsonPath().getString("email"));
    }

    @Test
    @DisplayName("Get User Details - Existing User")
    @Severity(SeverityLevel.NORMAL)
    @Description("Test retrieving details of an existing user")
    @Story("User Retrieval")
    public void testGetUserDetails() {
        // First create a user to get
        Map<String, Object> userData = new HashMap<>();
        userData.put("username", "getuser_" + System.currentTimeMillis());
        userData.put("email", "getuser_" + System.currentTimeMillis() + "@example.com");
        userData.put("first_name", "Jane");
        userData.put("last_name", "Smith");

        Response createResponse = given()
                .contentType(ContentType.JSON)
                .header("Authorization", "Bearer " + authToken)
                .body(userData)
                .when()
                .post("/users")
                .then()
                .extract().response();

        if (createResponse.statusCode() == 201) {
            createdUserId = createResponse.jsonPath().getString("id");

            // Now get the user details
            Response userResponse = given()
                    .contentType(ContentType.JSON)
                    .header("Authorization", "Bearer " + authToken)
                    .when()
                    .get("/users/" + createdUserId)
                    .then()
                    .statusCode(200)
                    .extract().response();

            // Validate user details
            assertEquals(createdUserId, userResponse.jsonPath().getString("id"));
            assertEquals(userData.get("username"), userResponse.jsonPath().getString("username"));
            assertEquals(userData.get("email"), userResponse.jsonPath().getString("email"));
        } else {
            // Skip test if user creation failed
            System.out.println("Skipping test as user creation failed");
            Assumptions.assumeTrue(false, "User creation failed");
        }
    }

    @Test
    @DisplayName("Update User Profile - Successful")
    @Severity(SeverityLevel.NORMAL)
    @Description("Test updating an existing user's profile")
    @Story("User Update")
    public void testUpdateUserProfile() {
        // First create a user to update
        Map<String, Object> userData = new HashMap<>();
        userData.put("username", "updateuser_" + System.currentTimeMillis());
        userData.put("email", "updateuser_" + System.currentTimeMillis() + "@example.com");
        userData.put("first_name", "Original");
        userData.put("last_name", "Name");

        Response createResponse = given()
                .contentType(ContentType.JSON)
                .header("Authorization", "Bearer " + authToken)
                .body(userData)
                .when()
                .post("/users")
                .then()
                .extract().response();

        if (createResponse.statusCode() == 201) {
            createdUserId = createResponse.jsonPath().getString("id");

            // Prepare update data
            Map<String, Object> updateData = new HashMap<>();
            updateData.put("first_name", "UpdatedFirstName");
            updateData.put("last_name", "UpdatedLastName");
            updateData.put("age", 35);

            Response updateResponse = given()
                    .contentType(ContentType.JSON)
                    .header("Authorization", "Bearer " + authToken)
                    .body(updateData)
                    .when()
                    .put("/users/" + createdUserId)
                    .then()
                    .statusCode(200)
                    .extract().response();

            // Validate update
            assertEquals("UpdatedFirstName", updateResponse.jsonPath().getString("first_name"));
            assertEquals("UpdatedLastName", updateResponse.jsonPath().getString("last_name"));
            assertEquals(35, updateResponse.jsonPath().getInt("age"));
        } else {
            // Skip test if user creation failed
            System.out.println("Skipping test as user creation failed");
            Assumptions.assumeTrue(false, "User creation failed");
        }
    }
}
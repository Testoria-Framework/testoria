package com.apiframework.tests.functional;

import io.restassured.RestAssured;
import io.restassured.http.ContentType;
import io.restassured.response.Response;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import static org.junit.jupiter.api.Assertions.*;
import static io.restassured.RestAssured.*;

import java.util.HashMap;
import java.util.Map;

public class UserApiFunctionalTest {
    private static String baseUrl;
    private static String authToken;

    @BeforeAll
    public static void setup() {
        // Load configuration
        baseUrl = System.getenv().getOrDefault("API_BASE_URL", "https://api.example.com");
        RestAssured.baseURI = baseUrl;

        // Authenticate and get token
        Map<String, String> authPayload = new HashMap<>();
        authPayload.put("username", "testuser");
        authPayload.put("password", "securePassword123");

        Response authResponse = given()
                .contentType(ContentType.JSON)
                .body(authPayload)
                .when()
                .post("/auth/login")
                .then()
                .statusCode(200)
                .extract().response();

        authToken = authResponse.jsonPath().getString("token");
    }

    @Test
    @DisplayName("Create New User - Successful")
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
        String userId = createResponse.jsonPath().getString("id");
        assertNotNull(userId, "User ID should be generated");
        assertEquals(userData.get("username"), createResponse.jsonPath().getString("username"));
        assertEquals(userData.get("email"), createResponse.jsonPath().getString("email"));
    }

    @Test
    @DisplayName("Get User Details - Existing User")
    public void testGetUserDetails() {
        // Assume we have a known user ID for testing
        String knownUserId = "existing-user-123";

        Response userResponse = given()
                .contentType(ContentType.JSON)
                .header("Authorization", "Bearer " + authToken)
                .when()
                .get("/users/" + knownUserId)
                .then()
                .statusCode(200)
                .extract().response();

        // Validate user details
        assertNotNull(userResponse.jsonPath().getString("id"));
        assertNotNull(userResponse.jsonPath().getString("username"));
        assertNotNull(userResponse.jsonPath().getString("email"));
    }

    @Test
    @DisplayName("Update User Profile - Successful")
    public void testUpdateUserProfile() {
        // Assume we have a known user ID for testing
        String knownUserId = "existing-user-123";

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
                .put("/users/" + knownUserId)
                .then()
                .statusCode(200)
                .extract().response();

        // Validate update
        assertEquals("UpdatedFirstName", updateResponse.jsonPath().getString("first_name"));
        assertEquals("UpdatedLastName", updateResponse.jsonPath().getString("last_name"));
        assertEquals(35, updateResponse.jsonPath().getInt("age"));
    }

    @Test
    @DisplayName("Delete User - Successful")
    public void testDeleteUser() {
        // Create a user to delete
        Map<String, Object> userData = new HashMap<>();
        userData.put("username", "user_to_delete_" + System.currentTimeMillis());
        userData.put("email", "delete_" + System.currentTimeMillis() + "@example.com");

        Response createResponse = given()
                .contentType(ContentType.JSON)
                .header("Authorization", "Bearer " + authToken)
                .body(userData)
                .when()
                .post("/users")
                .then()
                .statusCode(201)
                .extract().response();

        String userIdToDelete = createResponse.jsonPath().getString("id");

        // Delete the user
        given()
                .contentType(ContentType.JSON)
                .header("Authorization", "Bearer " + authToken)
                .when()
                .delete("/users/" + userIdToDelete)
                .then()
                .statusCode(204);

        // Verify user is deleted
        given()
                .contentType(ContentType.JSON)
                .header("Authorization", "Bearer " + authToken)
                .when()
                .get("/users/" + userIdToDelete)
                .then()
                .statusCode(404);
    }

    @Test
    @DisplayName("Create User - Invalid Input")
    public void testCreateUserWithInvalidData() {
        // Prepare invalid user data
        Map<String, Object> invalidUserData = new HashMap<>();
        invalidUserData.put("username", ""); // Empty username
        invalidUserData.put("email", "invalid-email"); // Invalid email format

        given()
                .contentType(ContentType.JSON)
                .header("Authorization", "Bearer " + authToken)
                .body(invalidUserData)
                .when()
                .post("/users")
                .then()
                .statusCode(400); // Expect bad request
    }
}
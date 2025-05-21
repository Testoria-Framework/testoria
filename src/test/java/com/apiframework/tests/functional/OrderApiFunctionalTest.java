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
 * Functional tests for the Order API endpoints.
 */
@Epic("API Testing")
@Feature("Order Management")
public class OrderApiFunctionalTest {

    private static String baseUrl;
    private static String authToken;
    private String testOrderId;

    @BeforeAll
    public static void setupClass() {
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

    @BeforeEach
    public void setUp() {
        // Additional setup if needed
    }

    @AfterEach
    public void tearDown() {
        // Clean up test data
        if (testOrderId != null) {
            try {
                given()
                        .contentType(ContentType.JSON)
                        .header("Authorization", "Bearer " + authToken)
                        .when()
                        .delete("/orders/" + testOrderId);
            } catch (Exception e) {
                System.err.println("Failed to delete test order: " + e.getMessage());
            }
            testOrderId = null;
        }
    }

    @Test
    @Severity(SeverityLevel.CRITICAL)
    @Description("Test retrieving all orders")
    @Story("Get all orders")
    public void testGetAllOrders() {
        // Act
        Response response = given()
                .contentType(ContentType.JSON)
                .header("Authorization", "Bearer " + authToken)
                .when()
                .get("/orders")
                .then()
                .extract().response();

        // Assert
        assertEquals(200, response.statusCode(), "Should return 200 OK status");
        assertTrue(response.contentType().contains("application/json"), "Should return JSON content");

        // Verify response structure if there are orders
        if (!response.body().asString().equals("[]")) {
            assertNotNull(response.jsonPath().getList("id"), "Orders should have IDs");
        }
    }

    @Test
    @Severity(SeverityLevel.CRITICAL)
    @Description("Test creating a new order")
    @Story("Create order")
    public void testCreateOrder() {
        // Arrange
        Map<String, Object> orderData = new HashMap<>();
        orderData.put("customer_id", 123);

        Map<String, Object> item1 = new HashMap<>();
        item1.put("product_id", 1);
        item1.put("quantity", 2);
        item1.put("price", 10.99);

        Map<String, Object> item2 = new HashMap<>();
        item2.put("product_id", 2);
        item2.put("quantity", 1);
        item2.put("price", 24.99);

        orderData.put("items", new Object[] { item1, item2 });

        Map<String, String> shippingAddress = new HashMap<>();
        shippingAddress.put("street", "123 Main St");
        shippingAddress.put("city", "Test City");
        shippingAddress.put("state", "TS");
        shippingAddress.put("zip", "12345");
        shippingAddress.put("country", "Test Country");
        orderData.put("shipping_address", shippingAddress);

        // Act
        Response response = given()
                .contentType(ContentType.JSON)
                .header("Authorization", "Bearer " + authToken)
                .body(orderData)
                .when()
                .post("/orders")
                .then()
                .extract().response();

        // Assert
        assertEquals(201, response.statusCode(), "Should return 201 Created status");
        assertTrue(response.contentType().contains("application/json"), "Should return JSON content");

        // Save order ID for cleanup
        testOrderId = response.jsonPath().getString("id");
        assertNotNull(testOrderId, "Created order should have ID");

        // Verify customer ID matches
        assertEquals(orderData.get("customer_id"), response.jsonPath().getInt("customer_id"),
                "Customer ID should match");
    }

    @Test
    @Severity(SeverityLevel.NORMAL)
    @Description("Test order not found error")
    @Story("Order not found")
    public void testOrderNotFound() {
        // Arrange
        String nonExistentOrderId = "999999999";

        // Act
        Response response = given()
                .contentType(ContentType.JSON)
                .header("Authorization", "Bearer " + authToken)
                .when()
                .get("/orders/" + nonExistentOrderId)
                .then()
                .extract().response();

        // Assert
        assertEquals(404, response.statusCode(), "Should return 404 Not Found status");
        assertTrue(response.contentType().contains("application/json"), "Should return JSON content");
        assertNotNull(response.jsonPath().getString("error"), "Should have error message");
    }
}
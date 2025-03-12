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
 * Functional tests for the Order API endpoints.
 */
@Epic("API Testing")
@Feature("Order Management")
public class OrderApiTest {

    private BaseApiClient apiClient;
    private String testOrderId;

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
        if (testOrderId != null) {
            try {
                apiClient.delete("/orders/" + testOrderId);
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
        Response response = apiClient.get("/orders");

        // Assert
        JavaAssertions.assertStatusCode(response, 200);
        JavaAssertions.assertJsonContentType(response);

        // Verify response structure
        JSONArray orders = JavaAssertions.getResponseAsJsonArray(response);
        
        if (orders.length() > 0) {
            // Verify the first order has required fields
            JSONObject firstOrder = orders.getJSONObject(0);
            Assertions.assertTrue(firstOrder.has("id"), "Order should have ID");
            Assertions.assertTrue(firstOrder.has("customer_id"), "Order should have customer_id");
            Assertions.assertTrue(firstOrder.has("items"), "Order should have items");
            Assertions.assertTrue(firstOrder.has("total"), "Order should have total");
            Assertions.assertTrue(firstOrder.has("status"), "Order should have status");
        }

        // Verify response time
        JavaAssertions.assertResponseTime(response, 1000); // Max 1000ms
    }

    @Test
    @Severity(SeverityLevel.CRITICAL)
    @Description("Test creating a new order")
    @Story("Create order")
    public void testCreateOrder() {
        // Arrange
        JSONObject orderData = new JSONObject();
        orderData.put("customer_id", 123);
        
        JSONArray items = new JSONArray();
        JSONObject item1 = new JSONObject();
        item1.put("product_id", 1);
        item1.put("quantity", 2);
        item1.put("price", 10.99);
        items.put(item1);
        
        JSONObject item2 = new JSONObject();
        item2.put("product_id", 2);
        item2.put("quantity", 1);
        item2.put("price", 24.99);
        items.put(item2);
        
        orderData.put("items", items);
        
        JSONObject shippingAddress = new JSONObject();
        shippingAddress.put("street", "123 Main St");
        shippingAddress.put("city", "Test City");
        shippingAddress.put("state", "TS");
        shippingAddress.put("zip", "12345");
        shippingAddress.put("country", "Test Country");
        orderData.put("shipping_address", shippingAddress);

        // Act
        Response response = apiClient.post("/orders", orderData);

        // Assert
        JavaAssertions.assertStatusCode(response, 201);
        JavaAssertions.assertJsonContentType(response);

        // Verify the created order
        JSONObject createdOrder = JavaAssertions.getResponseAsJsonObject(response);
        Assertions.assertTrue(createdOrder.has("id"), "Created order should have ID");
        testOrderId = createdOrder.getString("id"); // Save for cleanup

        // Verify all fields are correctly set
        Assertions.assertEquals(orderData.getInt("customer_id"), createdOrder.getInt("customer_id"));
        Assertions.assertEquals("pending", createdOrder.getString("status"), "New order should have pending status");
        
        // Verify items
        JSONArray responseItems = createdOrder.getJSONArray("items");
        Assertions.assertEquals(items.length(), responseItems.length(), "Order should have same number of items");
        
        // Calculate expected total
        double expectedTotal = 0;
        for (int i = 0; i < items.length(); i++) {
            JSONObject item = items.getJSONObject(i);
            expectedTotal += item.getDouble("price") * item.getInt("quantity");
        }
        Assertions.assertEquals(expectedTotal, createdOrder.getDouble("total"), 0.01, "Order total should match calculation");
        
        // Verify created_at field exists and is not empty
        Assertions.assertTrue(createdOrder.has("created_at"), "Created order should have created_at timestamp");
        Assertions.assertNotNull(createdOrder.getString("created_at"));
    }

    @Test
    @Severity(SeverityLevel.CRITICAL)
    @Description("Test retrieving a specific order by ID")
    @Story("Get order by ID")
    public void testGetOrderById() {
        // Arrange - Create an order first
        JSONObject orderData = new JSONObject();
        orderData.put("customer_id", 123);
        
        JSONArray items = new JSONArray();
        JSONObject item = new JSONObject();
        item.put("product_id", 1);
        item.put("quantity", 1);
        item.put("price", 10.99);
        items.put(item);
        
        orderData.put("items", items);

        Response createResponse = apiClient.post("/orders", orderData);
        JSONObject createdOrder = JavaAssertions.getResponseAsJsonObject(createResponse);
        testOrderId = createdOrder.getString("id");

        // Act
        Response response = apiClient.get("/orders/" + testOrderId);

        // Assert
        JavaAssertions.assertStatusCode(response, 200);
        JavaAssertions.assertJsonContentType(response);

        // Verify the retrieved order
        JSONObject retrievedOrder = JavaAssertions.getResponseAsJsonObject(response);
        Assertions.assertEquals(testOrderId, retrievedOrder.getString("id"));
        Assertions.assertEquals(orderData.getInt("customer_id"), retrievedOrder.getInt("customer_id"));
        
        // Verify items
        JSONArray responseItems = retrievedOrder.getJSONArray("items");
        Assertions.assertEquals(items.length(), responseItems.length(), "Order should have same number of items");
    }

    @Test
    @Severity(SeverityLevel.HIGH)
    @Description("Test updating an order status")
    @Story("Update order status")
    public void testUpdateOrderStatus() {
        // Arrange - Create an order first
        JSONObject orderData = new JSONObject();
        orderData.put("customer_id", 123);
        
        JSONArray items = new JSONArray();
        JSONObject item = new JSONObject();
        item.put("product_id", 1);
        item.put("quantity", 1);
        item.put("price", 10.99);
        items.put(item);
        
        orderData.put("items", items);

        Response createResponse = apiClient.post("/orders", orderData);
        JSONObject createdOrder = JavaAssertions.getResponseAsJsonObject(createResponse);
        testOrderId = createdOrder.getString("id");

        // Update data
        JSONObject updateData = new JSONObject();
        updateData.put("status", "shipped");
        updateData.put("tracking_number", "TRACK123456");

        // Act
        Response response = apiClient.patch("/orders/" + testOrderId, updateData);

        // Assert
        JavaAssertions.assertStatusCode(response, 200);
        JavaAssertions.assertJsonContentType(response);

        // Verify the updated order
        JSONObject updatedOrder = JavaAssertions.getResponseAsJsonObject(response);
        Assertions.assertEquals(testOrderId, updatedOrder.getString("id"));
        Assertions.assertEquals(updateData.getString("status"), updatedOrder.getString("status"));
        Assertions.assertEquals(updateData.getString("tracking_number"), updatedOrder.getString("tracking_number"));
        
        // Verify updated_at field exists and is not empty
        Assertions.assertTrue(updatedOrder.has("updated_at"), "Updated order should have updated_at timestamp");
        Assertions.assertNotNull(updatedOrder.getString("updated_at"));
    }

    @Test
    @Severity(SeverityLevel.HIGH)
    @Description("Test cancelling an order")
    @Story("Cancel order")
    public void testCancelOrder() {
        // Arrange - Create an order first
        JSONObject orderData = new JSONObject();
        orderData.put("customer_id", 123);
        
        JSONArray items = new JSONArray();
        JSONObject item = new JSONObject();
        item.put("product_id", 1);
        item.put("quantity", 1);
        item.put("price", 10.99);
        items.put(item);
        
        orderData.put("items", items);

        Response createResponse = apiClient.post("/orders", orderData);
        JSONObject createdOrder = JavaAssertions.getResponseAsJsonObject(createResponse);
        testOrderId = createdOrder.getString("id");

        // Cancel data
        JSONObject cancelData = new JSONObject();
        cancelData.put("cancellation_reason", "Customer request");

        // Act
        Response response = apiClient.patch("/orders/" + testOrderId + "/cancel", cancelData);

        // Assert
        JavaAssertions.assertStatusCode(response, 200);
        JavaAssertions.assertJsonContentType(response);

        // Verify the cancelled order
        JSONObject cancelledOrder = JavaAssertions.getResponseAsJsonObject(response);
        Assertions.assertEquals(testOrderId, cancelledOrder.getString("id"));
        Assertions.assertEquals("cancelled", cancelledOrder.getString("status"));
        Assertions.assertEquals(cancelData.getString("cancellation_reason"), cancelledOrder.getString("cancellation_reason"));
        
        // Verify cancelled_at field exists and is not empty
        Assertions.assertTrue(cancelledOrder.has("cancelled_at"), "Cancelled order should have cancelled_at timestamp");
        Assertions.assertNotNull(cancelledOrder.getString("cancelled_at"));
    }

    @Test
    @Severity(SeverityLevel.NORMAL)
    @Description("Test order not found error")
    @Story("Order not found")
    public void testOrderNotFound() {
        // Arrange
        String nonExistentOrderId = "999999999";

        // Act
        Response response = apiClient.get("/orders/" + nonExistentOrderId);

        // Assert
        JavaAssertions.assertStatusCode(response, 404);
        JavaAssertions.assertJsonContentType(response);

        // Verify error response structure
        JSONObject errorResponse = JavaAssertions.getResponseAsJsonObject(response);
        Assertions.assertTrue(errorResponse.has("error"), "Error response should have 'error' field");
        Assertions.assertEquals("Order not found", errorResponse.getString("error"));
    }

    @Test
    @Severity(SeverityLevel.NORMAL)
    @Description("Test order validation errors")
    @Story("Order validation")
    public void testOrderValidationErrors() {
        // Arrange - Invalid order data
        JSONObject invalidOrderData = new JSONObject();
        // Missing required customer_id
        invalidOrderData.put("items", new JSONArray()); // Empty items array

        // Act
        Response response = apiClient.post("/orders", invalidOrderData);

        // Assert
        JavaAssertions.assertStatusCode(response, 400);
        JavaAssertions.assertJsonContentType(response);

        // Verify error response structure
        JSONObject errorResponse = JavaAssertions.getResponseAsJsonObject(response);
        Assertions.assertTrue(errorResponse.has("errors"), "Error response should have 'errors' field");
        
        JSONArray errors = errorResponse.getJSONArray("errors");
        Assertions.assertTrue(errors.length() >= 2, "Should have at least 2 validation errors");
        
        // Check for specific error fields
        boolean hasCustomerIdError = false;
        boolean hasItemsError = false;
        
        for (int i = 0; i < errors.length(); i++) {
            JSONObject error = errors.getJSONObject(i);
            String field = error.getString("field");
            
            if (field.equals("customer_id")) hasCustomerIdError = true;
            if (field.equals("items")) hasItemsError = true;
        }
        
        Assertions.assertTrue(hasCustomerIdError, "Should have customer_id validation error");
        Assertions.assertTrue(hasItemsError, "Should have items validation error");
    }

    @Test
    @Severity(SeverityLevel.NORMAL)
    @Description("Test filtering orders by status")
    @Story("Filter orders")
    public void testFilterOrdersByStatus() {
        // Arrange
        String targetStatus = "shipped";

        // Act
        Map<String, String> queryParams = new HashMap<>();
        queryParams.put("status", targetStatus);
        Response response = apiClient.get("/orders", queryParams);

        // Assert
        JavaAssertions.assertStatusCode(response, 200);
        JavaAssertions.assertJsonContentType(response);

        // Verify all returned orders have the specified status
        JSONArray orders = JavaAssertions.getResponseAsJsonArray(response);
        
        if (orders.length() > 0) {
            for (int i = 0; i < orders.length(); i++) {
                JSONObject order = orders.getJSONObject(i);
                String status = order.getString("status");
                Assertions.assertEquals(targetStatus, status, 
                        "All returned orders should have the specified status");
            }
        }
    }
}

package tests.integration_tests.java;

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

/**
 * Integration tests for API endpoints.
 * Tests end-to-end flows across multiple APIs.
 */
@Epic("API Testing")
@Feature("API Integration")
public class ApiIntegrationTest {

    private BaseApiClient apiClient;
    private String testUserId;
    private String testProductId;
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
        }

        if (testProductId != null) {
            try {
                apiClient.delete("/products/" + testProductId);
            } catch (Exception e) {
                System.err.println("Failed to delete test product: " + e.getMessage());
            }
        }

        if (testUserId != null) {
            try {
                apiClient.delete("/users/" + testUserId);
            } catch (Exception e) {
                System.err.println("Failed to delete test user: " + e.getMessage());
            }
        }
    }

    @Test
    @Severity(SeverityLevel.CRITICAL)
    @Description("Test a complete user-order flow")
    @Story("Complete Order Flow")
    public void testCompleteOrderFlow() {
        // Step 1: Create a user
        JSONObject userData = new JSONObject();
        userData.put("name", "Test Integration User");
        userData.put("email", CommonHelpers.generateRandomEmail());
        userData.put("phone", CommonHelpers.generateRandomPhone());

        Response createUserResponse = apiClient.post("/users", userData);
        
        // Assert user creation
        JavaAssertions.assertStatusCode(createUserResponse, 201);
        JSONObject user = JavaAssertions.getResponseAsJsonObject(createUserResponse);
        testUserId = user.getString("id");

        // Step 2: Get available products
        Response getProductsResponse = apiClient.get("/products");
        
        // Assert products response
        JavaAssertions.assertStatusCode(getProductsResponse, 200);
        JSONArray products = JavaAssertions.getResponseAsJsonArray(getProductsResponse);
        
        // Ensure we have products to order
        Assertions.assertTrue(products.length() > 0, "No products available for ordering");
        
        // Select first two products or just the first if only one is available
        JSONArray selectedProducts = new JSONArray();
        int numProductsToSelect = Math.min(products.length(), 2);
        for (int i = 0; i < numProductsToSelect; i++) {
            selectedProducts.put(products.getJSONObject(i));
        }
        
        // Step 3: Create an order for the user
        JSONArray orderItems = new JSONArray();
        for (int i = 0; i < selectedProducts.length(); i++) {
            JSONObject product = selectedProducts.getJSONObject(i);
            JSONObject orderItem = new JSONObject();
            orderItem.put("product_id", product.getString("id"));
            orderItem.put("quantity", 1);
            orderItem.put("price", product.getDouble("price"));
            orderItems.put(orderItem);
        }
        
        JSONObject shippingAddress = new JSONObject();
        shippingAddress.put("street", "123 Integration St");
        shippingAddress.put("city", "Test City");
        shippingAddress.put("state", "TS");
        shippingAddress.put("zip", "12345");
        shippingAddress.put("country", "Test Country");
        
        JSONObject orderData = new JSONObject();
        orderData.put("customer_id", testUserId);
        orderData.put("items", orderItems);
        orderData.put("shipping_address", shippingAddress);
        
        Response createOrderResponse = apiClient.post("/orders", orderData);
        
        // Assert order creation
        JavaAssertions.assertStatusCode(createOrderResponse, 201);
        JSONObject order = JavaAssertions.getResponseAsJsonObject(createOrderResponse);
        testOrderId = order.getString("id");
        
        // Step 4: Update order status to processing
        JSONObject updateData = new JSONObject();
        updateData.put("status", "processing");
        
        Response updateOrderResponse = apiClient.patch("/orders/" + testOrderId, updateData);
        
        // Assert order update
        JavaAssertions.assertStatusCode(updateOrderResponse, 200);
        JSONObject updatedOrder = JavaAssertions.getResponseAsJsonObject(updateOrderResponse);
        Assertions.assertEquals("processing", updatedOrder.getString("status"));
        
        // Step 5: Update order status to shipped
        try {
            Thread.sleep(1000); // Simulate time passing
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        
        JSONObject shippingData = new JSONObject();
        shippingData.put("status", "shipped");
        shippingData.put("tracking_number", "TRACK-" + CommonHelpers.generateRandomString(10));
        
        Response shipOrderResponse = apiClient.patch("/orders/" + testOrderId, shippingData);
        
        // Assert order shipped
        JavaAssertions.assertStatusCode(shipOrderResponse, 200);
        JSONObject shippedOrder = JavaAssertions.getResponseAsJsonObject(shipOrderResponse);
        Assertions.assertEquals("shipped", shippedOrder.getString("status"));
        Assertions.assertEquals(shippingData.getString("tracking_number"), shippedOrder.getString("tracking_number"));
        
        // Step 6: Get user's orders
        Response getUserOrdersResponse = apiClient.get("/users/" + testUserId + "/orders");
        
        // Assert user orders
        JavaAssertions.assertStatusCode(getUserOrdersResponse, 200);
        JSONArray userOrders = JavaAssertions.getResponseAsJsonArray(getUserOrdersResponse);
        
        // Verify the order is in the user's orders
        boolean orderFound = false;
        for (int i = 0; i < userOrders.length(); i++) {
            JSONObject userOrder = userOrders.getJSONObject(i);
            if (userOrder.getString("id").equals(testOrderId)) {
                orderFound = true;
                break;
            }
        }
        Assertions.assertTrue(orderFound, "Created order not found in user's orders");
        
        // Step 7: Update order status to delivered
        try {
            Thread.sleep(1000); // Simulate time passing
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        
        JSONObject deliveryData = new JSONObject();
        deliveryData.put("status", "delivered");
        deliveryData.put("delivery_date", CommonHelpers.getIsoTimestamp());
        
        Response deliverOrderResponse = apiClient.patch("/orders/" + testOrderId, deliveryData);
        
        // Assert order delivered
        JavaAssertions.assertStatusCode(deliverOrderResponse, 200);
        JSONObject deliveredOrder = JavaAssertions.getResponseAsJsonObject(deliverOrderResponse);
        Assertions.assertEquals("delivered", deliveredOrder.getString("status"));
    }

    @Test
    @Severity(SeverityLevel.HIGH)
    @Description("Test product inventory management")
    @Story("Product Inventory Flow")
    public void testProductInventoryFlow() {
        // Step 1: Create a product
        JSONObject productData = new JSONObject();
        productData.put("name", "Test Product " + CommonHelpers.generateRandomString(5));
        productData.put("description", "A test product created during integration testing");
        productData.put("price", 99.99);
        productData.put("category", "test-integration");
        productData.put("stock", 100);
        productData.put("sku", "TEST-" + CommonHelpers.generateRandomString(8));
        
        Response createProductResponse = apiClient.post("/products", productData);
        
        // Assert product creation
        JavaAssertions.assertStatusCode(createProductResponse, 201);
        JSONObject product = JavaAssertions.getResponseAsJsonObject(createProductResponse);
        testProductId = product.getString("id");
        
        // Step 2: Create an order that includes this product
        JSONArray orderItems = new JSONArray();
        JSONObject orderItem = new JSONObject();
        orderItem.put("product_id", testProductId);
        orderItem.put("quantity", 5);
        orderItem.put("price", productData.getDouble("price"));
        orderItems.put(orderItem);
        
        JSONObject orderData = new JSONObject();
        orderData.put("customer_id", 123); // Could create a real user first
        orderData.put("items", orderItems);
        
        Response createOrderResponse = apiClient.post("/orders", orderData);
        
        // Assert order creation
        JavaAssertions.assertStatusCode(createOrderResponse, 201);
        JSONObject order = JavaAssertions.getResponseAsJsonObject(createOrderResponse);
        String orderIdForCleanup = order.getString("id");
        
        // Step 3: Check if inventory was updated
        Response getProductResponse = apiClient.get("/products/" + testProductId);
        
        // Assert product inventory update
        JavaAssertions.assertStatusCode(getProductResponse, 200);
        JSONObject updatedProduct = JavaAssertions.getResponseAsJsonObject(getProductResponse);
        
        // Verify inventory reduced by the ordered quantity
        int expectedStock = productData.getInt("stock") - orderItem.getInt("quantity");
        Assertions.assertEquals(expectedStock, updatedProduct.getInt("stock"));
        
        // Step 4: Update the product stock manually
        JSONObject stockUpdateData = new JSONObject();
        stockUpdateData.put("stock", 200); // Set to new value
        
        Response updateStockResponse = apiClient.patch("/products/" + testProductId, stockUpdateData);
        
        // Assert manual stock update
        JavaAssertions.assertStatusCode(updateStockResponse, 200);
        JSONObject stockUpdatedProduct = JavaAssertions.getResponseAsJsonObject(updateStockResponse);
        Assertions.assertEquals(stockUpdateData.getInt("stock"), stockUpdatedProduct.getInt("stock"));
        
        // Cleanup the order created in this test
        try {
            apiClient.delete("/orders/" + orderIdForCleanup);
        } catch (Exception e) {
            System.err.println("Failed to delete order: " + e.getMessage());
        }
    }

    @Test
    @Severity(SeverityLevel.HIGH)
    @Description("Test payment processing flow")
    @Story("Payment Processing Flow")
    public void testPaymentProcessingFlow() {
        // Step 1: Create a user
        JSONObject userData = new JSONObject();
        userData.put("name", "Test Payment User");
        userData.put("email", CommonHelpers.generateRandomEmail());
        
        Response createUserResponse = apiClient.post("/users", userData);
        JavaAssertions.assertStatusCode(createUserResponse, 201);
        JSONObject user = JavaAssertions.getResponseAsJsonObject(createUserResponse);
        testUserId = user.getString("id");
        
        // Step 2: Create a payment method for the user
        JSONObject paymentMethodData = new JSONObject();
        paymentMethodData.put("user_id", testUserId);
        paymentMethodData.put("type", "credit_card");
        paymentMethodData.put("card_last4", "4242");
        paymentMethodData.put("card_brand", "visa");
        paymentMethodData.put("expiry_month", 12);
        paymentMethodData.put("expiry_year", 2025);
        
        Response createPaymentMethodResponse = apiClient.post("/payment_methods", paymentMethodData);
        JavaAssertions.assertStatusCode(createPaymentMethodResponse, 201);
        JSONObject paymentMethod = JavaAssertions.getResponseAsJsonObject(createPaymentMethodResponse);
        String paymentMethodId = paymentMethod.getString("id");
        
        // Step 3: Create an order
        JSONObject orderData = new JSONObject();
        orderData.put("customer_id", testUserId);
        
        JSONArray orderItems = new JSONArray();
        JSONObject orderItem = new JSONObject();
        orderItem.put("product_id", "P001"); // Using a known product ID
        orderItem.put("quantity", 1);
        orderItem.put("price", 99.99);
        orderItems.put(orderItem);
        
        orderData.put("items", orderItems);
        
        Response createOrderResponse = apiClient.post("/orders", orderData);
        JavaAssertions.assertStatusCode(createOrderResponse, 201);
        JSONObject order = JavaAssertions.getResponseAsJsonObject(createOrderResponse);
        testOrderId = order.getString("id");
        
        // Step 4: Process payment for the order
        JSONObject paymentData = new JSONObject();
        paymentData.put("order_id", testOrderId);
        paymentData.put("payment_method_id", paymentMethodId);
        paymentData.put("amount", order.getDouble("total"));
        paymentData.put("currency", "USD");
        
        Response processPaymentResponse = apiClient.post("/payments", paymentData);
        JavaAssertions.assertStatusCode(processPaymentResponse, 201);
        JSONObject payment = JavaAssertions.getResponseAsJsonObject(processPaymentResponse);
        Assertions.assertEquals("succeeded", payment.getString("status"));
        
        // Step 5: Verify order status is updated to 'paid'
        Response getOrderResponse = apiClient.get("/orders/" + testOrderId);
        JavaAssertions.assertStatusCode(getOrderResponse, 200);
        JSONObject updatedOrder = JavaAssertions.getResponseAsJsonObject(getOrderResponse);
        Assertions.assertEquals("paid", updatedOrder.getString("status"));
        
        // Step 6: Get user's payment history
        Response paymentHistoryResponse = apiClient.get("/users/" + testUserId + "/payments");
        JavaAssertions.assertStatusCode(paymentHistoryResponse, 200);
        JSONArray payments = JavaAssertions.getResponseAsJsonArray(paymentHistoryResponse);
        
        // Verify the payment is in the user's history
        boolean paymentFound = false;
        for (int i = 0; i < payments.length(); i++) {
            JSONObject historyPayment = payments.getJSONObject(i);
            if (historyPayment.getString("order_id").equals(testOrderId)) {
                paymentFound = true;
                break;
            }
        }
        Assertions.assertTrue(paymentFound, "Payment not found in user's payment history");
        
        // Clean up - delete the payment method
        try {
            apiClient.delete("/payment_methods/" + paymentMethodId);
        } catch (Exception e) {
            System.err.println("Failed to delete payment method: " + e.getMessage());
        }
    }
}

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
 * Functional tests for the Product API endpoints.
 */
@Epic("API Testing")
@Feature("Product Management")
public class ProductApiTest {

    private BaseApiClient apiClient;
    private String testProductId;

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
        if (testProductId != null) {
            try {
                apiClient.delete("/products/" + testProductId);
            } catch (Exception e) {
                System.err.println("Failed to delete test product: " + e.getMessage());
            }
            testProductId = null;
        }
    }

    @Test
    @Severity(SeverityLevel.CRITICAL)
    @Description("Test retrieving all products")
    @Story("Get all products")
    public void testGetAllProducts() {
        // Act
        Response response = apiClient.get("/products");

        // Assert
        JavaAssertions.assertStatusCode(response, 200);
        JavaAssertions.assertJsonContentType(response);

        // Verify response structure
        JSONArray products = JavaAssertions.getResponseAsJsonArray(response);
        Assertions.assertTrue(products.length() > 0, "Products list should not be empty");

        // Verify the first product has required fields
        if (products.length() > 0) {
            JSONObject firstProduct = products.getJSONObject(0);
            Assertions.assertTrue(firstProduct.has("id"), "Product should have ID");
            Assertions.assertTrue(firstProduct.has("name"), "Product should have name");
            Assertions.assertTrue(firstProduct.has("price"), "Product should have price");
            Assertions.assertTrue(firstProduct.has("category"), "Product should have category");
        }

        // Verify response time
        JavaAssertions.assertResponseTime(response, 1000); // Max 1000ms
    }

    @Test
    @Severity(SeverityLevel.CRITICAL)
    @Description("Test creating a new product")
    @Story("Create product")
    public void testCreateProduct() {
        // Arrange
        String randomSuffix = UUID.randomUUID().toString().substring(0, 8);
        JSONObject productData = new JSONObject();
        productData.put("name", "Test Product " + randomSuffix);
        productData.put("description", "A test product created via API tests");
        productData.put("price", 99.99);
        productData.put("category", "test");
        productData.put("stock", 100);
        productData.put("sku", "TEST-" + randomSuffix);

        // Act
        Response response = apiClient.post("/products", productData);

        // Assert
        JavaAssertions.assertStatusCode(response, 201);
        JavaAssertions.assertJsonContentType(response);

        // Verify the created product
        JSONObject createdProduct = JavaAssertions.getResponseAsJsonObject(response);
        Assertions.assertTrue(createdProduct.has("id"), "Created product should have ID");
        testProductId = createdProduct.getString("id"); // Save for cleanup

        // Verify all fields are correctly set
        Assertions.assertEquals(productData.getString("name"), createdProduct.getString("name"));
        Assertions.assertEquals(productData.getString("description"), createdProduct.getString("description"));
        Assertions.assertEquals(productData.getDouble("price"), createdProduct.getDouble("price"));
        Assertions.assertEquals(productData.getString("category"), createdProduct.getString("category"));
        Assertions.assertEquals(productData.getInt("stock"), createdProduct.getInt("stock"));
        Assertions.assertEquals(productData.getString("sku"), createdProduct.getString("sku"));
        
        // Verify created_at field exists and is not empty
        Assertions.assertTrue(createdProduct.has("created_at"), "Created product should have created_at timestamp");
        Assertions.assertNotNull(createdProduct.getString("created_at"));
    }

    @Test
    @Severity(SeverityLevel.CRITICAL)
    @Description("Test retrieving a specific product by ID")
    @Story("Get product by ID")
    public void testGetProductById() {
        // Arrange - Create a product first
        String randomSuffix = UUID.randomUUID().toString().substring(0, 8);
        JSONObject productData = new JSONObject();
        productData.put("name", "Test Product " + randomSuffix);
        productData.put("price", 99.99);
        productData.put("category", "test");

        Response createResponse = apiClient.post("/products", productData);
        JSONObject createdProduct = JavaAssertions.getResponseAsJsonObject(createResponse);
        testProductId = createdProduct.getString("id");

        // Act
        Response response = apiClient.get("/products/" + testProductId);

        // Assert
        JavaAssertions.assertStatusCode(response, 200);
        JavaAssertions.assertJsonContentType(response);

        // Verify the retrieved product
        JSONObject retrievedProduct = JavaAssertions.getResponseAsJsonObject(response);
        Assertions.assertEquals(testProductId, retrievedProduct.getString("id"));
        Assertions.assertEquals(productData.getString("name"), retrievedProduct.getString("name"));
        Assertions.assertEquals(productData.getDouble("price"), retrievedProduct.getDouble("price"));
        Assertions.assertEquals(productData.getString("category"), retrievedProduct.getString("category"));
    }

    @Test
    @Severity(SeverityLevel.HIGH)
    @Description("Test updating a product")
    @Story("Update product")
    public void testUpdateProduct() {
        // Arrange - Create a product first
        String randomSuffix = UUID.randomUUID().toString().substring(0, 8);
        JSONObject productData = new JSONObject();
        productData.put("name", "Original Product " + randomSuffix);
        productData.put("price", 99.99);
        productData.put("category", "test");
        productData.put("stock", 100);

        Response createResponse = apiClient.post("/products", productData);
        JSONObject createdProduct = JavaAssertions.getResponseAsJsonObject(createResponse);
        testProductId = createdProduct.getString("id");

        // Update data
        JSONObject updateData = new JSONObject();
        updateData.put("name", "Updated Product " + randomSuffix);
        updateData.put("price", 149.99);
        updateData.put("stock", 50);

        // Act
        Response response = apiClient.put("/products/" + testProductId, updateData);

        // Assert
        JavaAssertions.assertStatusCode(response, 200);
        JavaAssertions.assertJsonContentType(response);

        // Verify the updated product
        JSONObject updatedProduct = JavaAssertions.getResponseAsJsonObject(response);
        Assertions.assertEquals(testProductId, updatedProduct.getString("id"));
        Assertions.assertEquals(updateData.getString("name"), updatedProduct.getString("name"));
        Assertions.assertEquals(updateData.getDouble("price"), updatedProduct.getDouble("price"));
        Assertions.assertEquals(updateData.getInt("stock"), updatedProduct.getInt("stock"));
        
        // Category should remain unchanged
        Assertions.assertEquals(productData.getString("category"), updatedProduct.getString("category"));
        
        // Verify updated_at field exists and is not empty
        Assertions.assertTrue(updatedProduct.has("updated_at"), "Updated product should have updated_at timestamp");
        Assertions.assertNotNull(updatedProduct.getString("updated_at"));
    }

    @Test
    @Severity(SeverityLevel.HIGH)
    @Description("Test deleting a product")
    @Story("Delete product")
    public void testDeleteProduct() {
        // Arrange - Create a product first
        String randomSuffix = UUID.randomUUID().toString().substring(0, 8);
        JSONObject productData = new JSONObject();
        productData.put("name", "Product to Delete " + randomSuffix);
        productData.put("price", 99.99);
        productData.put("category", "test");

        Response createResponse = apiClient.post("/products", productData);
        JSONObject createdProduct = JavaAssertions.getResponseAsJsonObject(createResponse);
        String productId = createdProduct.getString("id");

        // Act
        Response deleteResponse = apiClient.delete("/products/" + productId);

        // Assert
        JavaAssertions.assertStatusCode(deleteResponse, 204);
        
        // Verify the product is actually deleted
        Response getResponse = apiClient.get("/products/" + productId);
        JavaAssertions.assertStatusCode(getResponse, 404);
        
        // Clear the test product ID since we've deleted it
        testProductId = null;
    }

    @Test
    @Severity(SeverityLevel.NORMAL)
    @Description("Test product validation errors")
    @Story("Product validation")
    public void testProductValidationErrors() {
        // Arrange - Invalid product data
        JSONObject invalidProductData = new JSONObject();
        invalidProductData.put("name", ""); // Empty name should be invalid
        invalidProductData.put("price", -50); // Negative price should be invalid
        invalidProductData.put("category", ""); // Empty category should be invalid

        // Act
        Response response = apiClient.post("/products", invalidProductData);

        // Assert
        JavaAssertions.assertStatusCode(response, 400);
        JavaAssertions.assertJsonContentType(response);

        // Verify error response structure
        JSONObject errorResponse = JavaAssertions.getResponseAsJsonObject(response);
        Assertions.assertTrue(errorResponse.has("errors"), "Error response should have 'errors' field");
        
        JSONArray errors = errorResponse.getJSONArray("errors");
        Assertions.assertTrue(errors.length() >= 3, "Should have at least 3 validation errors");
        
        // Check for specific error fields
        boolean hasNameError = false;
        boolean hasPriceError = false;
        boolean hasCategoryError = false;
        
        for (int i = 0; i < errors.length(); i++) {
            JSONObject error = errors.getJSONObject(i);
            String field = error.getString("field");
            
            if (field.equals("name")) hasNameError = true;
            if (field.equals("price")) hasPriceError = true;
            if (field.equals("category")) hasCategoryError = true;
        }
        
        Assertions.assertTrue(hasNameError, "Should have name validation error");
        Assertions.assertTrue(hasPriceError, "Should have price validation error");
        Assertions.assertTrue(hasCategoryError, "Should have category validation error");
    }

    @Test
    @Severity(SeverityLevel.NORMAL)
    @Description("Test filtering products by category")
    @Story("Filter products")
    public void testFilterProductsByCategory() {
        // Arrange
        String targetCategory = "electronics";

        // Act
        Map<String, String> queryParams = new HashMap<>();
        queryParams.put("category", targetCategory);
        Response response = apiClient.get("/products", queryParams);

        // Assert
        JavaAssertions.assertStatusCode(response, 200);
        JavaAssertions.assertJsonContentType(response);

        // Verify all returned products have the specified category
        JSONArray products = JavaAssertions.getResponseAsJsonArray(response);
        
        for (int i = 0; i < products.length(); i++) {
            JSONObject product = products.getJSONObject(i);
            String category = product.getString("category");
            Assertions.assertEquals(targetCategory, category, 
                    "All returned products should have the specified category");
        }
    }
}

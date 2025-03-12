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

describe('API Integration Tests', function() {
  this.timeout(10000); // Integration tests may take longer
  let apiClient;
  
  // Test data for tracking across tests
  let testUserId;
  let testProductId;
  let testOrderId;
  
  before(function() {
    // Set up API client
    const envConfig = getEnvironmentConfig('dev');
    const baseUrl = envConfig.base_url;
    
    apiClient = new BaseApiClient(baseUrl, {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    });
    
    // Set up authentication if needed
    const authConfig = envConfig.auth || {};
    if (authConfig.type === 'oauth2') {
      // Implementation would depend on the actual auth flow
      // This is a simplified example
      const token = "test_token";  // Would be obtained from auth service
      apiClient.setAuthorization('Bearer', token);
    }
  });
  
  after(function() {
    // Clean up after tests
    apiClient.clearAuthorization();
    
    // Clean up test data
    if (testOrderId) {
      apiClient.delete(`/orders/${testOrderId}`)
        .catch(err => console.warn(`Failed to delete test order: ${err.message}`));
    }
    
    if (testProductId) {
      apiClient.delete(`/products/${testProductId}`)
        .catch(err => console.warn(`Failed to delete test product: ${err.message}`));
    }
    
    if (testUserId) {
      apiClient.delete(`/users/${testUserId}`)
        .catch(err => console.warn(`Failed to delete test user: ${err.message}`));
    }
  });
  
  describe('Complete Order Flow', function() {
    it('should complete an end-to-end user-order flow', async function() {
      // Step 1: Create a user
      const userData = {
        name: 'Test Integration User',
        email: ApiTestUtils.generateRandomEmail(),
        phone: ApiTestUtils.generateRandomPhone()
      };
      
      allureReporter.startTest("Complete Order Flow", "Test a complete user-order flow");
      allureReporter.addTag("integration");
      allureReporter.addSeverity("critical");
      
      allureReporter.addStep("Creating a user", "passed");
      allureReporter.addApiRequest("POST", "/users", apiClient.client.defaults.headers, userData);
      const createUserResponse = await apiClient.post("/users", userData);
      allureReporter.addApiResponse(createUserResponse);
      
      ApiAssertions.assertStatusCode(createUserResponse, 201);
      const user = createUserResponse.data;
      testUserId = user.id;
      
      // Step 2: Get available products
      allureReporter.addStep("Retrieving available products", "passed");
      allureReporter.addApiRequest("GET", "/products", apiClient.client.defaults.headers);
      const getProductsResponse = await apiClient.get("/products");
      allureReporter.addApiResponse(getProductsResponse);
      
      ApiAssertions.assertStatusCode(getProductsResponse, 200);
      const products = getProductsResponse.data;
      
      // Ensure we have products to order
      expect(products.length).to.be.gt(0, "No products available for ordering");
      
      // Select first two products or just the first if only one is available
      const selectedProducts = products.length >= 2 ? products.slice(0, 2) : products.slice(0, 1);
      
      // Step 3: Create an order for the user
      const orderItems = selectedProducts.map(product => ({
        product_id: product.id,
        quantity: 1,
        price: product.price
      }));
      
      const orderData = {
        customer_id: testUserId,
        items: orderItems,
        shipping_address: {
          street: "123 Integration St",
          city: "Test City",
          state: "TS",
          zip: "12345",
          country: "Test Country"
        }
      };
      
      allureReporter.addStep("Creating an order", "passed");
      allureReporter.addApiRequest("POST", "/orders", apiClient.client.defaults.headers, orderData);
      const createOrderResponse = await apiClient.post("/orders", orderData);
      allureReporter.addApiResponse(createOrderResponse);
      
      ApiAssertions.assertStatusCode(createOrderResponse, 201);
      const order = createOrderResponse.data;
      testOrderId = order.id;
      
      // Step 4: Update order status to processing
      const updateData = {
        status: 'processing'
      };
      
      allureReporter.addStep("Updating order status to processing", "passed");
      allureReporter.addApiRequest("PATCH", `/orders/${testOrderId}`, apiClient.client.defaults.headers, updateData);
      const updateOrderResponse = await apiClient.patch(`/orders/${testOrderId}`, updateData);
      allureReporter.addApiResponse(updateOrderResponse);
      
      ApiAssertions.assertStatusCode(updateOrderResponse, 200);
      const updatedOrder = updateOrderResponse.data;
      ApiAssertions.assertJsonValue(updatedOrder, 'status', 'processing');
      
      // Step 5: Update order status to shipped
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate time passing
      
      const shippingData = {
        status: 'shipped',
        tracking_number: `TRACK-${ApiTestUtils.generateRandomString(10)}`
      };
      
      allureReporter.addStep("Updating order status to shipped", "passed");
      allureReporter.addApiRequest("PATCH", `/orders/${testOrderId}`, apiClient.client.defaults.headers, shippingData);
      const shipOrderResponse = await apiClient.patch(`/orders/${testOrderId}`, shippingData);
      allureReporter.addApiResponse(shipOrderResponse);
      
      ApiAssertions.assertStatusCode(shipOrderResponse, 200);
      const shippedOrder = shipOrderResponse.data;
      ApiAssertions.assertJsonValue(shippedOrder, 'status', 'shipped');
      ApiAssertions.assertJsonValue(shippedOrder, 'tracking_number', shippingData.tracking_number);
      
      // Step 6: Get user's orders
      allureReporter.addStep("Retrieving user's orders", "passed");
      allureReporter.addApiRequest("GET", `/users/${testUserId}/orders`, apiClient.client.defaults.headers);
      const getUserOrdersResponse = await apiClient.get(`/users/${testUserId}/orders`);
      allureReporter.addApiResponse(getUserOrdersResponse);
      
      ApiAssertions.assertStatusCode(getUserOrdersResponse, 200);
      const userOrders = getUserOrdersResponse.data;
      
      // Verify the order is in the user's orders
      const orderFound = userOrders.some(o => o.id === testOrderId);
      expect(orderFound).to.be.true;
      
      // Step 7: Update order status to delivered
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate time passing
      
      const deliveryData = {
        status: 'delivered',
        delivery_date: ApiTestUtils.getIsoTimestamp()
      };
      
      allureReporter.addStep("Updating order status to delivered", "passed");
      allureReporter.addApiRequest("PATCH", `/orders/${testOrderId}`, apiClient.client.defaults.headers, deliveryData);
      const deliverOrderResponse = await apiClient.patch(`/orders/${testOrderId}`, deliveryData);
      allureReporter.addApiResponse(deliverOrderResponse);
      
      ApiAssertions.assertStatusCode(deliverOrderResponse, 200);
      const deliveredOrder = deliverOrderResponse.data;
      ApiAssertions.assertJsonValue(deliveredOrder, 'status', 'delivered');
      
      allureReporter.addStep("End-to-end flow completed successfully", "passed");
      allureReporter.endTest();
    });
  });
  
  describe('Product Inventory Flow', function() {
    it('should correctly manage product inventory', async function() {
      // Step 1: Create a product
      const productData = {
        name: `Test Product ${ApiTestUtils.generateRandomString(5)}`,
        description: 'A test product created during integration testing',
        price: 99.99,
        category: 'test-integration',
        stock: 100,
        sku: `TEST-${ApiTestUtils.generateRandomString(8)}`
      };
      
      allureReporter.startTest("Product Inventory Flow", "Test product inventory management");
      allureReporter.addTag("integration");
      allureReporter.addSeverity("high");
      
      allureReporter.addStep("Creating a product", "passed");
      allureReporter.addApiRequest("POST", "/products", apiClient.client.defaults.headers, productData);
      const createProductResponse = await apiClient.post("/products", productData);
      allureReporter.addApiResponse(createProductResponse);
      
      ApiAssertions.assertStatusCode(createProductResponse, 201);
      const product = createProductResponse.data;
      testProductId = product.id;
      
      // Step 2: Create an order that includes this product
      const orderData = {
        customer_id: 123,  // Could create a real user first
        items: [
          {
            product_id: testProductId,
            quantity: 5,
            price: productData.price
          }
        ]
      };
      
      allureReporter.addStep("Creating an order with the product", "passed");
      allureReporter.addApiRequest("POST", "/orders", apiClient.client.defaults.headers, orderData);
      const createOrderResponse = await apiClient.post("/orders", orderData);
      allureReporter.addApiResponse(createOrderResponse);
      
      ApiAssertions.assertStatusCode(createOrderResponse, 201);
      const order = createOrderResponse.data;
      const orderIdForCleanup = order.id;
      
      // Step 3: Check if inventory was updated
      allureReporter.addStep("Checking product inventory", "passed");
      allureReporter.addApiRequest("GET", `/products/${testProductId}`, apiClient.client.defaults.headers);
      const getProductResponse = await apiClient.get(`/products/${testProductId}`);
      allureReporter.addApiResponse(getProductResponse);
      
      ApiAssertions.assertStatusCode(getProductResponse, 200);
      const updatedProduct = getProductResponse.data;
      
      // Verify inventory reduced by the ordered quantity
      const expectedStock = productData.stock - orderData.items[0].quantity;
      ApiAssertions.assertJsonValue(updatedProduct, 'stock', expectedStock);
      
      // Step 4: Update the product stock manually
      const stockUpdateData = {
        stock: 200  // Set to new value
      };
      
      allureReporter.addStep("Updating product stock", "passed");
      allureReporter.addApiRequest("PATCH", `/products/${testProductId}`, apiClient.client.defaults.headers, stockUpdateData);
      const updateStockResponse = await apiClient.patch(`/products/${testProductId}`, stockUpdateData);
      allureReporter.addApiResponse(updateStockResponse);
      
      ApiAssertions.assertStatusCode(updateStockResponse, 200);
      const stockUpdatedProduct = updateStockResponse.data;
      ApiAssertions.assertJsonValue(stockUpdatedProduct, 'stock', stockUpdateData.stock);
      
      // Cleanup the order created in this test
      try {
        await apiClient.delete(`/orders/${orderIdForCleanup}`);
      } catch (err) {
        console.warn(`Failed to delete order: ${err.message}`);
      }
      
      allureReporter.addStep("Inventory flow completed successfully", "passed");
      allureReporter.endTest();
    });
  });
});

const { describe, beforeEach, afterEach, it } = require('mocha');
const { expect } = require('chai');

const BaseApiClient = require('../../../core/clients/base_api_client');
const ApiAssertions = require('../../../core/assertions/js_assertions');
const { 
  getEnvironmentConfig, 
  getBaseUrl 
} = require('../../../core/config/env_loader');
const allureReporter = require('../../../core/reporting/allure_reporter');
const ApiTestUtils = require('../../../core/utils/common_helpers');

describe('Order API Tests', function() {
  let apiClient;
  let testOrderId;
  
  beforeEach(function() {
    // Set up API client for each test
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
  
  afterEach(function() {
    // Clean up after each test
    apiClient.clearAuthorization();
    
    // Delete test order if it was created
    if (testOrderId) {
      apiClient.delete(`/orders/${testOrderId}`)
        .catch(err => console.warn(`Failed to delete test order: ${err.message}`));
      testOrderId = null;
    }
  });
  
  it('should get all orders', async function() {
    // Arrange
    const testName = "Get All Orders";
    
    allureReporter.startTest(testName, "Test retrieving all orders");
    allureReporter.addTag("order_api");
    allureReporter.addSeverity("normal");
    
    // Act
    allureReporter.addApiRequest("GET", "/orders", apiClient.client.defaults.headers);
    const response = await apiClient.get("/orders");
    allureReporter.addApiResponse(response);
    
    // Assert
    ApiAssertions.assertStatusCode(response, 200);
    ApiAssertions.assertJsonContentType(response);
    
    const responseData = response.data;
    expect(responseData).to.be.an('array');
    
    if (responseData.length > 0) {
      const firstOrder = responseData[0];
      ApiAssertions.assertJsonHasKeys(firstOrder, ['id', 'customer_id', 'items', 'total', 'status', 'created_at']);
    }
    
    // Log test completion
    allureReporter.addStep("Test completed", "passed");
    allureReporter.endTest();
  });
  
  it('should create a new order', async function() {
    // Arrange
    const testName = "Create Order";
    
    const orderData = {
      customer_id: 123,
      items: [
        { product_id: 1, quantity: 2, price: 10.99 },
        { product_id: 2, quantity: 1, price: 24.99 }
      ],
      shipping_address: {
        street: "123 Main St",
        city: "Test City",
        state: "TS",
        zip: "12345",
        country: "Test Country"
      }
    };
    
    allureReporter.startTest(testName, "Test creating a new order");
    allureReporter.addTag("order_api");
    allureReporter.addSeverity("critical");
    
    // Act
    allureReporter.addApiRequest("POST", "/orders", apiClient.client.defaults.headers, orderData);
    const response = await apiClient.post("/orders", orderData);
    allureReporter.addApiResponse(response);
    
    // Save order ID for cleanup
    testOrderId = response.data.id;
    
    // Assert
    ApiAssertions.assertStatusCode(response, 201);
    ApiAssertions.assertJsonContentType(response);
    
    const createdOrder = response.data;
    ApiAssertions.assertJsonHasKeys(createdOrder, ['id', 'customer_id', 'items', 'total', 'status', 'created_at']);
    ApiAssertions.assertJsonValue(createdOrder, 'customer_id', orderData.customer_id);
    ApiAssertions.assertJsonValue(createdOrder, 'status', 'pending');
    
    // Verify order items
    expect(createdOrder.items).to.be.an('array').with.lengthOf(orderData.items.length);
    expect(createdOrder.total).to.be.a('number');
    
    // Calculate expected total (sum of item price * quantity)
    const expectedTotal = orderData.items.reduce(
      (sum, item) => sum + (item.price * item.quantity), 
      0
    );
    expect(createdOrder.total).to.equal(expectedTotal);
    
    // Log test completion
    allureReporter.addStep("Test completed", "passed");
    allureReporter.endTest();
  });
  
  it('should get order by ID', async function() {
    // Arrange - First create an order to retrieve
    const orderData = {
      customer_id: 123,
      items: [
        { product_id: 1, quantity: 1, price: 10.99 }
      ]
    };
    
    const createResponse = await apiClient.post("/orders", orderData);
    testOrderId = createResponse.data.id;
    
    const testName = "Get Order By ID";
    allureReporter.startTest(testName, "Test retrieving an order by ID");
    allureReporter.addTag("order_api");
    allureReporter.addSeverity("critical");
    
    // Act
    allureReporter.addApiRequest("GET", `/orders/${testOrderId}`, apiClient.client.defaults.headers);
    const response = await apiClient.get(`/orders/${testOrderId}`);
    allureReporter.addApiResponse(response);
    
    // Assert
    ApiAssertions.assertStatusCode(response, 200);
    ApiAssertions.assertJsonContentType(response);
    
    const order = response.data;
    ApiAssertions.assertJsonHasKeys(order, ['id', 'customer_id', 'items', 'total', 'status', 'created_at']);
    ApiAssertions.assertJsonValue(order, 'id', testOrderId);
    ApiAssertions.assertJsonValue(order, 'customer_id', orderData.customer_id);
    
    // Verify response time
    if (response.config && response.config.metadata && response.config.metadata.responseTime) {
      expect(response.config.metadata.responseTime).to.be.at.most(1000); // Max 1000ms
    }
    
    // Log test completion
    allureReporter.addStep("Test completed", "passed");
    allureReporter.endTest();
  });
  
  it('should update order status', async function() {
    // Arrange - First create an order to update
    const orderData = {
      customer_id: 123,
      items: [
        { product_id: 1, quantity: 1, price: 10.99 }
      ]
    };
    
    const createResponse = await apiClient.post("/orders", orderData);
    testOrderId = createResponse.data.id;
    
    const updateData = {
      status: 'shipped',
      tracking_number: 'TRACK123456'
    };
    
    const testName = "Update Order Status";
    allureReporter.startTest(testName, "Test updating an order status");
    allureReporter.addTag("order_api");
    allureReporter.addSeverity("normal");
    
    // Act
    allureReporter.addApiRequest("PATCH", `/orders/${testOrderId}`, apiClient.client.defaults.headers, updateData);
    const response = await apiClient.patch(`/orders/${testOrderId}`, updateData);
    allureReporter.addApiResponse(response);
    
    // Assert
    ApiAssertions.assertStatusCode(response, 200);
    ApiAssertions.assertJsonContentType(response);
    
    const updatedOrder = response.data;
    ApiAssertions.assertJsonValue(updatedOrder, 'status', updateData.status);
    ApiAssertions.assertJsonValue(updatedOrder, 'tracking_number', updateData.tracking_number);
    ApiAssertions.assertJsonHasKey(updatedOrder, 'updated_at');
    
    // Log test completion
    allureReporter.addStep("Test completed", "passed");
    allureReporter.endTest();
  });
  
  it('should cancel an order', async function() {
    // Arrange - First create an order to cancel
    const orderData = {
      customer_id: 123,
      items: [
        { product_id: 1, quantity: 1, price: 10.99 }
      ]
    };
    
    const createResponse = await apiClient.post("/orders", orderData);
    testOrderId = createResponse.data.id;
    
    const cancelData = {
      status: 'cancelled',
      cancellation_reason: 'Customer request'
    };
    
    const testName = "Cancel Order";
    allureReporter.startTest(testName, "Test cancelling an order");
    allureReporter.addTag("order_api");
    allureReporter.addSeverity("normal");
    
    // Act
    allureReporter.addApiRequest("PATCH", `/orders/${testOrderId}/cancel`, apiClient.client.defaults.headers, cancelData);
    const response = await apiClient.patch(`/orders/${testOrderId}/cancel`, cancelData);
    allureReporter.addApiResponse(response);
    
    // Assert
    ApiAssertions.assertStatusCode(response, 200);
    ApiAssertions.assertJsonContentType(response);
    
    const cancelledOrder = response.data;
    ApiAssertions.assertJsonValue(cancelledOrder, 'status', 'cancelled');
    ApiAssertions.assertJsonValue(cancelledOrder, 'cancellation_reason', cancelData.cancellation_reason);
    ApiAssertions.assertJsonHasKey(cancelledOrder, 'cancelled_at');
    
    // Log test completion
    allureReporter.addStep("Test completed", "passed");
    allureReporter.endTest();
  });
  
  it('should return 404 for non-existent order', async function() {
    // Arrange
    const nonExistentOrderId = '999999999';
    
    const testName = "Get Non-Existent Order";
    allureReporter.startTest(testName, "Test retrieving a non-existent order by ID");
    allureReporter.addTag("order_api");
    allureReporter.addTag("negative");
    allureReporter.addSeverity("normal");
    
    // Act
    allureReporter.addApiRequest("GET", `/orders/${nonExistentOrderId}`, apiClient.client.defaults.headers);
    
    try {
      await apiClient.get(`/orders/${nonExistentOrderId}`);
      // If we get here, the test fails
      allureReporter.addStep("Test failed: Expected 404 error", "failed");
      allureReporter.endTest("failed");
      throw new Error("Expected 404 error but got success response");
    } catch (error) {
      // Assert
      const response = error.response;
      allureReporter.addApiResponse(response);
      
      ApiAssertions.assertStatusCode(response, 404);
      ApiAssertions.assertJsonContentType(response);
      
      const errorData = response.data;
      ApiAssertions.assertJsonHasKey(errorData, 'error');
      ApiAssertions.assertJsonValue(errorData, 'error', 'Order not found');
      
      // Log test completion
      allureReporter.addStep("Test completed", "passed");
      allureReporter.endTest("passed");
    }
  });
  
  it('should validate required fields when creating an order', async function() {
    // Arrange
    const testName = "Order Validation Error";
    
    const invalidOrderData = {
      // Missing required customer_id
      items: [] // Empty items array
    };
    
    allureReporter.startTest(testName, "Test validation error when creating an order with invalid data");
    allureReporter.addTag("order_api");
    allureReporter.addTag("validation");
    allureReporter.addSeverity("normal");
    
    // Act
    allureReporter.addApiRequest("POST", "/orders", apiClient.client.defaults.headers, invalidOrderData);
    
    try {
      await apiClient.post("/orders", invalidOrderData);
      // If we get here, the test fails
      allureReporter.addStep("Test failed: Expected 400 error", "failed");
      allureReporter.endTest("failed");
      throw new Error("Expected 400 error but got success response");
    } catch (error) {
      // Assert
      const response = error.response;
      allureReporter.addApiResponse(response);
      
      ApiAssertions.assertStatusCode(response, 400);
      ApiAssertions.assertJsonContentType(response);
      
      const errorData = response.data;
      ApiAssertions.assertJsonHasKey(errorData, 'errors');
      
      const errors = errorData.errors;
      expect(errors).to.be.an('array');
      
      // Check for specific validation errors
      const hasCustomerIdError = errors.some(err => err.field === 'customer_id');
      const hasItemsError = errors.some(err => err.field === 'items');
      
      expect(hasCustomerIdError).to.be.true;
      expect(hasItemsError).to.be.true;
      
      // Log test completion
      allureReporter.addStep("Test completed", "passed");
      allureReporter.endTest("passed");
    }
  });
});

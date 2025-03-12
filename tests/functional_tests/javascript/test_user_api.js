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

describe('User API Tests', function() {
  let apiClient;
  let testUserId;
  
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
    
    // Delete test user if it was created
    if (testUserId) {
      apiClient.delete(`/users/${testUserId}`)
        .catch(err => console.warn(`Failed to delete test user: ${err.message}`));
      testUserId = null;
    }
  });
  
  it('should get all users', async function() {
    // Arrange
    const testName = "Get All Users";
    
    allureReporter.startTest(testName, "Test retrieving all users");
    allureReporter.addTag("user_api");
    allureReporter.addSeverity("normal");
    
    // Act
    allureReporter.addApiRequest("GET", "/users", apiClient.client.defaults.headers);
    const response = await apiClient.get("/users");
    allureReporter.addApiResponse(response);
    
    // Assert
    ApiAssertions.assertStatusCode(response, 200);
    ApiAssertions.assertJsonContentType(response);
    
    const responseData = response.data;
    expect(responseData).to.be.an('array');
    
    if (responseData.length > 0) {
      const firstUser = responseData[0];
      ApiAssertions.assertJsonHasKeys(firstUser, ['id', 'name', 'email']);
    }
    
    // Log test completion
    allureReporter.addStep("Test completed", "passed");
    allureReporter.endTest();
  });
  
  it('should get user by ID', async function() {
    // Arrange
    const testName = "Get User By ID";
    allureReporter.startTest(testName, "Test retrieving a user by ID");
    allureReporter.addTag("user_api");
    allureReporter.addSeverity("critical");
    
    // Act
    allureReporter.addApiRequest("GET", "/users/1", apiClient.client.defaults.headers);
    const response = await apiClient.get("/users/1");
    allureReporter.addApiResponse(response);
    
    // Assert
    ApiAssertions.assertStatusCode(response, 200);
    ApiAssertions.assertJsonContentType(response);
    
    const user = response.data;
    ApiAssertions.assertJsonHasKeys(user, ['id', 'name', 'email']);
    ApiAssertions.assertJsonValue(user, 'id', 1);
    
    // Verify response time
    if (response.config && response.config.metadata && response.config.metadata.responseTime) {
      expect(response.config.metadata.responseTime).to.be.at.most(1000); // Max 1000ms
    }
    
    // Log test completion
    allureReporter.addStep("Test completed", "passed");
    allureReporter.endTest();
  });
  
  it('should create a new user', async function() {
    // Arrange
    const testName = "Create User";
    
    const userData = {
      name: 'Test User',
      email: ApiTestUtils.generateRandomEmail(),
      phone: ApiTestUtils.generateRandomPhone()
    };
    
    allureReporter.startTest(testName, "Test creating a new user");
    allureReporter.addTag("user_api");
    allureReporter.addSeverity("critical");
    
    // Act
    allureReporter.addApiRequest("POST", "/users", apiClient.client.defaults.headers, userData);
    const response = await apiClient.post("/users", userData);
    allureReporter.addApiResponse(response);
    
    // Save user ID for cleanup
    testUserId = response.data.id;
    
    // Assert
    ApiAssertions.assertStatusCode(response, 201);
    ApiAssertions.assertJsonContentType(response);
    
    const createdUser = response.data;
    ApiAssertions.assertJsonHasKeys(createdUser, ['id', 'name', 'email', 'created_at']);
    ApiAssertions.assertJsonValue(createdUser, 'name', userData.name);
    ApiAssertions.assertJsonValue(createdUser, 'email', userData.email);
    
    // Verify user ID is assigned
    expect(createdUser.id).to.not.be.undefined;
    
    // Log test completion
    allureReporter.addStep("Test completed", "passed");
    allureReporter.endTest();
  });
  
  it('should update an existing user', async function() {
    // Arrange - First create a user to update
    const userData = {
      name: 'User to Update',
      email: ApiTestUtils.generateRandomEmail()
    };
    
    const createResponse = await apiClient.post("/users", userData);
    testUserId = createResponse.data.id;
    
    const updateData = {
      name: 'Updated User Name',
      email: ApiTestUtils.generateRandomEmail()
    };
    
    const testName = "Update User";
    allureReporter.startTest(testName, "Test updating an existing user");
    allureReporter.addTag("user_api");
    allureReporter.addSeverity("normal");
    
    // Act
    allureReporter.addApiRequest("PUT", `/users/${testUserId}`, apiClient.client.defaults.headers, updateData);
    const response = await apiClient.put(`/users/${testUserId}`, updateData);
    allureReporter.addApiResponse(response);
    
    // Assert
    ApiAssertions.assertStatusCode(response, 200);
    ApiAssertions.assertJsonContentType(response);
    
    const updatedUser = response.data;
    ApiAssertions.assertJsonHasKeys(updatedUser, ['id', 'name', 'email', 'updated_at']);
    ApiAssertions.assertJsonValue(updatedUser, 'name', updateData.name);
    ApiAssertions.assertJsonValue(updatedUser, 'email', updateData.email);
    ApiAssertions.assertJsonValue(updatedUser, 'id', testUserId);
    
    // Log test completion
    allureReporter.addStep("Test completed", "passed");
    allureReporter.endTest();
  });
  
  it('should delete a user', async function() {
    // Arrange - First create a user to delete
    const userData = {
      name: 'User to Delete',
      email: ApiTestUtils.generateRandomEmail()
    };
    
    const createResponse = await apiClient.post("/users", userData);
    const userIdToDelete = createResponse.data.id;
    
    const testName = "Delete User";
    allureReporter.startTest(testName, "Test deleting a user");
    allureReporter.addTag("user_api");
    allureReporter.addSeverity("normal");
    
    // Act
    allureReporter.addApiRequest("DELETE", `/users/${userIdToDelete}`, apiClient.client.defaults.headers);
    const response = await apiClient.delete(`/users/${userIdToDelete}`);
    allureReporter.addApiResponse(response);
    
    // Assert
    ApiAssertions.assertStatusCode(response, 204);
    
    // Verify user is actually deleted
    try {
      const verifyResponse = await apiClient.get(`/users/${userIdToDelete}`);
      // If we get here, the test fails
      expect.fail('Expected 404 error but got success response');
    } catch (error) {
      expect(error.response.status).to.equal(404);
    }
    
    // Clear test user ID since we've deleted it
    testUserId = null;
    
    // Log test completion
    allureReporter.addStep("Test completed", "passed");
    allureReporter.endTest();
  });
  
  it('should return validation errors for invalid user data', async function() {
    // Arrange
    const testName = "User Validation Error";
    
    const invalidUserData = {
      name: '',  // Empty name should be invalid
      email: 'invalid-email'  // Invalid email format
    };
    
    allureReporter.startTest(testName, "Test validation error when creating a user with invalid data");
    allureReporter.addTag("user_api");
    allureReporter.addTag("validation");
    allureReporter.addSeverity("normal");
    
    // Act
    allureReporter.addApiRequest("POST", "/users", apiClient.client.defaults.headers, invalidUserData);
    
    try {
      await apiClient.post("/users", invalidUserData);
      // If we get here, the test fails
      allureReporter.addStep("Test failed: Expected 400 error", "failed");
      allureReporter.endTest("failed");
      expect.fail('Expected 400 error but got success response');
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
      const hasNameError = errors.some(err => err.field === 'name');
      const hasEmailError = errors.some(err => err.field === 'email');
      
      expect(hasNameError).to.be.true;
      expect(hasEmailError).to.be.true;
      
      // Log test completion
      allureReporter.addStep("Test completed", "passed");
      allureReporter.endTest("passed");
    }
  });
});

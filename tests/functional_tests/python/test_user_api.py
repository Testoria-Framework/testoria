import pytest
import logging

from core.clients.base_api_client import BaseApiClient
from core.assertions.python_assertions import ApiAssertions
from core.config.env_loader import get_environment_config, get_base_url
from core.reporting.allure_reporter import allure_reporter
from core.utils.common_helpers import ApiTestUtils

logger = logging.getLogger(__name__)

@pytest.fixture
def api_client():
    """Fixture to create and configure the API client for testing."""
    env_config = get_environment_config('dev')
    base_url = env_config['base_url']
    
    client = BaseApiClient(base_url)
    
    # Add default headers
    client.headers.update({
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    })
    
    # Set up authentication if needed
    auth_config = env_config.get('auth', {})
    if auth_config.get('type') == 'oauth2':
        # Implementation would depend on the actual auth flow
        # This is a simplified example
        token = "test_token"  # Would be obtained from auth service
        client.set_authorization('Bearer', token)
    
    yield client
    
    # Cleanup after tests
    client.clear_authorization()

class TestUserApi:
    """
    Test suite for User API endpoints.
    Tests the basic CRUD operations and validation rules.
    """
    
    @pytest.mark.functional
    def test_get_user_by_id(self, api_client):
        """Test retrieving a user by ID."""
        # Arrange
        user_id = 1
        test_name = "Get User By ID"
        
        allure_reporter.start_test(test_name, "Test retrieving a user by ID")
        allure_reporter.add_tag("user_api")
        allure_reporter.add_severity("critical")
        
        # Act
        allure_reporter.add_api_request("GET", f"/users/{user_id}", api_client.headers)
        response = api_client.get(f"/users/{user_id}")
        allure_reporter.add_api_response(response)
        
        # Assert
        ApiAssertions.assert_status_code(response, 200)
        ApiAssertions.assert_json_content_type(response)
        
        json_data = ApiAssertions.assert_json_body(response)
        ApiAssertions.assert_json_has_keys(json_data, ['id', 'name', 'email'])
        ApiAssertions.assert_json_value(json_data, 'id', user_id)
        
        # Validate response time
        ApiAssertions.assert_response_time(response, 1000)  # Max 1000ms
    
    @pytest.mark.functional
    def test_create_user(self, api_client):
        """Test creating a new user."""
        # Arrange
        test_name = "Create User"
        
        user_data = {
            'name': 'Test User',
            'email': ApiTestUtils.generate_random_email(),
            'phone': ApiTestUtils.generate_random_phone()
        }
        
        allure_reporter.start_test(test_name, "Test creating a new user")
        allure_reporter.add_tag("user_api")
        allure_reporter.add_severity("critical")
        
        # Act
        allure_reporter.add_api_request("POST", "/users", api_client.headers, user_data)
        response = api_client.post("/users", json_data=user_data)
        allure_reporter.add_api_response(response)
        
        # Assert
        ApiAssertions.assert_status_code(response, 201)
        ApiAssertions.assert_json_content_type(response)
        
        json_data = ApiAssertions.assert_json_body(response)
        ApiAssertions.assert_json_has_keys(json_data, ['id', 'name', 'email', 'phone', 'created_at'])
        ApiAssertions.assert_json_value(json_data, 'name', user_data['name'])
        ApiAssertions.assert_json_value(json_data, 'email', user_data['email'])
        
        # Verify created user has an ID
        assert json_data['id'] is not None, "User ID should be assigned"
    
    @pytest.mark.functional
    def test_update_user(self, api_client):
        """Test updating an existing user."""
        # Arrange
        user_id = 1
        test_name = "Update User"
        
        update_data = {
            'name': 'Updated User Name',
            'email': ApiTestUtils.generate_random_email()
        }
        
        allure_reporter.start_test(test_name, "Test updating an existing user")
        allure_reporter.add_tag("user_api")
        allure_reporter.add_severity("normal")
        
        # Act
        allure_reporter.add_api_request("PUT", f"/users/{user_id}", api_client.headers, update_data)
        response = api_client.put(f"/users/{user_id}", json_data=update_data)
        allure_reporter.add_api_response(response)
        
        # Assert
        ApiAssertions.assert_status_code(response, 200)
        ApiAssertions.assert_json_content_type(response)
        
        json_data = ApiAssertions.assert_json_body(response)
        ApiAssertions.assert_json_has_keys(json_data, ['id', 'name', 'email', 'updated_at'])
        ApiAssertions.assert_json_value(json_data, 'name', update_data['name'])
        ApiAssertions.assert_json_value(json_data, 'email', update_data['email'])
        ApiAssertions.assert_json_value(json_data, 'id', user_id)
    
    @pytest.mark.functional
    def test_delete_user(self, api_client):
        """Test deleting a user."""
        # Arrange
        # First create a user to delete
        user_data = {
            'name': 'User to Delete',
            'email': ApiTestUtils.generate_random_email()
        }
        
        create_response = api_client.post("/users", json_data=user_data)
        user_id = create_response.json()['id']
        
        test_name = "Delete User"
        allure_reporter.start_test(test_name, "Test deleting a user")
        allure_reporter.add_tag("user_api")
        allure_reporter.add_severity("normal")
        
        # Act
        allure_reporter.add_api_request("DELETE", f"/users/{user_id}", api_client.headers)
        response = api_client.delete(f"/users/{user_id}")
        allure_reporter.add_api_response(response)
        
        # Assert
        ApiAssertions.assert_status_code(response, 204)
        
        # Verify user is actually deleted
        verify_response = api_client.get(f"/users/{user_id}")
        ApiAssertions.assert_status_code(verify_response, 404)
    
    @pytest.mark.functional
    def test_user_validation_error(self, api_client):
        """Test validation error when creating a user with invalid data."""
        # Arrange
        test_name = "User Validation Error"
        
        invalid_user_data = {
            'name': '',  # Empty name should be invalid
            'email': 'invalid-email'  # Invalid email format
        }
        
        allure_reporter.start_test(test_name, "Test validation error when creating a user with invalid data")
        allure_reporter.add_tag("user_api")
        allure_reporter.add_tag("validation")
        allure_reporter.add_severity("normal")
        
        # Act
        allure_reporter.add_api_request("POST", "/users", api_client.headers, invalid_user_data)
        response = api_client.post("/users", json_data=invalid_user_data)
        allure_reporter.add_api_response(response)
        
        # Assert
        ApiAssertions.assert_status_code(response, 400)
        ApiAssertions.assert_json_content_type(response)
        
        json_data = ApiAssertions.assert_json_body(response)
        ApiAssertions.assert_json_has_key(json_data, 'errors')
        
        # Check that both field errors are reported
        errors = json_data['errors']
        assert any(error['field'] == 'name' for error in errors), "Should have name validation error"
        assert any(error['field'] == 'email' for error in errors), "Should have email validation error"

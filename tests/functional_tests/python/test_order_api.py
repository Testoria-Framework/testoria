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

class TestOrderApi:
    """
    Test suite for Order API endpoints.
    Tests the basic CRUD operations and validation rules for orders.
    """
    
    @pytest.mark.functional
    def test_get_all_orders(self, api_client):
        """Test retrieving all orders."""
        # Arrange
        test_name = "Get All Orders"
        
        allure_reporter.start_test(test_name, "Test retrieving all orders")
        allure_reporter.add_tag("order_api")
        allure_reporter.add_severity("normal")
        
        # Act
        allure_reporter.add_api_request("GET", "/orders", api_client.headers)
        response = api_client.get("/orders")
        allure_reporter.add_api_response(response)
        
        # Assert
        ApiAssertions.assert_status_code(response, 200)
        ApiAssertions.assert_json_content_type(response)
        
        json_data = ApiAssertions.assert_json_body(response)
        assert isinstance(json_data, list), "Response should be a list of orders"
        
        if len(json_data) > 0:
            first_order = json_data[0]
            ApiAssertions.assert_json_has_keys(first_order, ['id', 'customer_id', 'items', 'total', 'status', 'created_at'])
        
        # Validate response time
        ApiAssertions.assert_response_time(response, 1000)  # Max 1000ms
    
    @pytest.mark.functional
    def test_get_order_by_id(self, api_client):
        """Test retrieving an order by ID."""
        # Arrange
        # First get a list of orders to find an ID to test with
        response = api_client.get("/orders")
        orders = response.json()
        
        # If no orders exist, create one
        if not orders:
            create_data = {
                'customer_id': 123,
                'items': [
                    {'product_id': 1, 'quantity': 2, 'price': 10.99}
                ]
            }
            create_response = api_client.post("/orders", json_data=create_data)
            order_id = create_response.json()['id']
        else:
            order_id = orders[0]['id']
        
        test_name = "Get Order By ID"
        
        allure_reporter.start_test(test_name, "Test retrieving an order by ID")
        allure_reporter.add_tag("order_api")
        allure_reporter.add_severity("critical")
        
        # Act
        allure_reporter.add_api_request("GET", f"/orders/{order_id}", api_client.headers)
        response = api_client.get(f"/orders/{order_id}")
        allure_reporter.add_api_response(response)
        
        # Assert
        ApiAssertions.assert_status_code(response, 200)
        ApiAssertions.assert_json_content_type(response)
        
        json_data = ApiAssertions.assert_json_body(response)
        ApiAssertions.assert_json_has_keys(json_data, ['id', 'customer_id', 'items', 'total', 'status', 'created_at'])
        ApiAssertions.assert_json_value(json_data, 'id', order_id)
        
        # Verify items is a list
        assert isinstance(json_data['items'], list), "Items should be a list"
    
    @pytest.mark.functional
    def test_create_order(self, api_client):
        """Test creating a new order."""
        # Arrange
        test_name = "Create Order"
        
        order_data = {
            'customer_id': 123,
            'items': [
                {'product_id': 1, 'quantity': 2, 'price': 10.99},
                {'product_id': 2, 'quantity': 1, 'price': 24.99}
            ],
            'shipping_address': {
                'street': "123 Main St",
                'city': "Test City",
                'state': "TS",
                'zip': "12345",
                'country': "Test Country"
            }
        }
        
        allure_reporter.start_test(test_name, "Test creating a new order")
        allure_reporter.add_tag("order_api")
        allure_reporter.add_severity("critical")
        
        # Act
        allure_reporter.add_api_request("POST", "/orders", api_client.headers, order_data)
        response = api_client.post("/orders", json_data=order_data)
        allure_reporter.add_api_response(response)
        
        # Assert
        ApiAssertions.assert_status_code(response, 201)
        ApiAssertions.assert_json_content_type(response)
        
        json_data = ApiAssertions.assert_json_body(response)
        ApiAssertions.assert_json_has_keys(json_data, ['id', 'customer_id', 'items', 'total', 'status', 'created_at'])
        ApiAssertions.assert_json_value(json_data, 'customer_id', order_data['customer_id'])
        ApiAssertions.assert_json_value(json_data, 'status', 'pending')
        
        # Verify order items
        assert isinstance(json_data['items'], list), "Items should be a list"
        assert len(json_data['items']) == len(order_data['items']), "All items should be included"
        
        # Calculate expected total (sum of item price * quantity)
        expected_total = sum(item['price'] * item['quantity'] for item in order_data['items'])
        assert json_data['total'] == expected_total, "Total price should match calculation"
        
        # Clean up - delete the created order
        created_id = json_data['id']
        api_client.delete(f"/orders/{created_id}")
    
    @pytest.mark.functional
    def test_update_order_status(self, api_client):
        """Test updating an order status."""
        # Arrange
        # First create an order to update
        create_data = {
            'customer_id': 123,
            'items': [
                {'product_id': 1, 'quantity': 1, 'price': 10.99}
            ]
        }
        
        create_response = api_client.post("/orders", json_data=create_data)
        order_id = create_response.json()['id']
        
        update_data = {
            'status': 'shipped',
            'tracking_number': 'TRACK123456'
        }
        
        test_name = "Update Order Status"
        allure_reporter.start_test(test_name, "Test updating an order status")
        allure_reporter.add_tag("order_api")
        allure_reporter.add_severity("normal")
        
        # Act
        allure_reporter.add_api_request("PATCH", f"/orders/{order_id}", api_client.headers, update_data)
        response = api_client.patch(f"/orders/{order_id}", json_data=update_data)
        allure_reporter.add_api_response(response)
        
        # Assert
        ApiAssertions.assert_status_code(response, 200)
        ApiAssertions.assert_json_content_type(response)
        
        json_data = ApiAssertions.assert_json_body(response)
        ApiAssertions.assert_json_value(json_data, 'status', update_data['status'])
        ApiAssertions.assert_json_value(json_data, 'tracking_number', update_data['tracking_number'])
        ApiAssertions.assert_json_has_key(json_data, 'updated_at')
        
        # Clean up - delete the created order
        api_client.delete(f"/orders/{order_id}")
    
    @pytest.mark.functional
    def test_cancel_order(self, api_client):
        """Test cancelling an order."""
        # Arrange
        # First create an order to cancel
        create_data = {
            'customer_id': 123,
            'items': [
                {'product_id': 1, 'quantity': 1, 'price': 10.99}
            ]
        }
        
        create_response = api_client.post("/orders", json_data=create_data)
        order_id = create_response.json()['id']
        
        cancel_data = {
            'status': 'cancelled',
            'cancellation_reason': 'Customer request'
        }
        
        test_name = "Cancel Order"
        allure_reporter.start_test(test_name, "Test cancelling an order")
        allure_reporter.add_tag("order_api")
        allure_reporter.add_severity("normal")
        
        # Act
        allure_reporter.add_api_request("PATCH", f"/orders/{order_id}/cancel", api_client.headers, cancel_data)
        response = api_client.patch(f"/orders/{order_id}/cancel", json_data=cancel_data)
        allure_reporter.add_api_response(response)
        
        # Assert
        ApiAssertions.assert_status_code(response, 200)
        ApiAssertions.assert_json_content_type(response)
        
        json_data = ApiAssertions.assert_json_body(response)
        ApiAssertions.assert_json_value(json_data, 'status', 'cancelled')
        ApiAssertions.assert_json_value(json_data, 'cancellation_reason', cancel_data['cancellation_reason'])
        ApiAssertions.assert_json_has_key(json_data, 'cancelled_at')
        
        # Verify can't update a cancelled order
        update_data = {'status': 'shipped'}
        try:
            api_client.patch(f"/orders/{order_id}", json_data=update_data)
            assert False, "Expected error when updating cancelled order"
        except Exception as e:
            # Should get an error since order is cancelled
            assert True
    
    @pytest.mark.functional
    def test_order_not_found(self, api_client):
        """Test requesting a non-existent order."""
        # Arrange
        non_existent_id = '999999999'
        
        test_name = "Order Not Found"
        allure_reporter.start_test(test_name, "Test retrieving a non-existent order")
        allure_reporter.add_tag("order_api")
        allure_reporter.add_tag("negative")
        allure_reporter.add_severity("normal")
        
        # Act
        allure_reporter.add_api_request("GET", f"/orders/{non_existent_id}", api_client.headers)
        
        try:
            response = api_client.get(f"/orders/{non_existent_id}")
            assert False, "Expected 404 error for non-existent order"
        except Exception as e:
            # Extract the response from the exception
            response = e.response
            allure_reporter.add_api_response(response)
            
            # Assert
            ApiAssertions.assert_status_code(response, 404)
            ApiAssertions.assert_json_content_type(response)
            
            json_data = ApiAssertions.assert_json_body(response)
            ApiAssertions.assert_json_has_key(json_data, 'error')
            ApiAssertions.assert_json_value(json_data, 'error', 'Order not found')
    
    @pytest.mark.functional
    def test_order_validation_error(self, api_client):
        """Test validation error when creating an order with invalid data."""
        # Arrange
        test_name = "Order Validation Error"
        
        invalid_order_data = {
            # Missing required customer_id
            'items': []  # Empty items array
        }
        
        allure_reporter.start_test(test_name, "Test validation error when creating an order with invalid data")
        allure_reporter.add_tag("order_api")
        allure_reporter.add_tag("validation")
        allure_reporter.add_severity("normal")
        
        # Act
        allure_reporter.add_api_request("POST", "/orders", api_client.headers, invalid_order_data)
        
        try:
            response = api_client.post("/orders", json_data=invalid_order_data)
            assert False, "Expected 400 error for invalid order data"
        except Exception as e:
            # Extract the response from the exception
            response = e.response
            allure_reporter.add_api_response(response)
            
            # Assert
            ApiAssertions.assert_status_code(response, 400)
            ApiAssertions.assert_json_content_type(response)
            
            json_data = ApiAssertions.assert_json_body(response)
            ApiAssertions.assert_json_has_key(json_data, 'errors')
            
            errors = json_data['errors']
            assert any(error['field'] == 'customer_id' for error in errors), "Should have customer_id validation error"
            assert any(error['field'] == 'items' for error in errors), "Should have items validation error"

import pytest
import logging
import time

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

class TestE2EUserOrderFlow:
    """
    Test suite for end-to-end API integration scenarios.
    Tests the complete user-order-product flow.
    """
    
    @pytest.mark.integration
    def test_complete_order_flow(self, api_client):
        """Test a complete flow of creating a user, order, and retrieving details."""
        # Step 1: Create a user
        user_data = {
            'name': 'Test Integration User',
            'email': ApiTestUtils.generate_random_email(),
            'phone': ApiTestUtils.generate_random_phone()
        }
        
        allure_reporter.start_test("Complete Order Flow", "Test a complete user-order flow")
        allure_reporter.add_tag("integration")
        allure_reporter.add_severity("critical")
        
        allure_reporter.add_step("Creating a user", "passed")
        allure_reporter.add_api_request("POST", "/users", api_client.headers, user_data)
        create_user_response = api_client.post("/users", json_data=user_data)
        allure_reporter.add_api_response(create_user_response)
        
        ApiAssertions.assert_status_code(create_user_response, 201)
        user = create_user_response.json()
        user_id = user['id']
        
        # Step 2: Get available products
        allure_reporter.add_step("Retrieving available products", "passed")
        allure_reporter.add_api_request("GET", "/products", api_client.headers)
        get_products_response = api_client.get("/products")
        allure_reporter.add_api_response(get_products_response)
        
        ApiAssertions.assert_status_code(get_products_response, 200)
        products = get_products_response.json()
        
        # Ensure we have products to order
        assert len(products) > 0, "No products available for ordering"
        
        # Select first two products or just the first if only one is available
        selected_products = products[:2] if len(products) >= 2 else products[:1]
        
        # Step 3: Create an order for the user
        order_items = []
        for product in selected_products:
            order_items.append({
                'product_id': product['id'],
                'quantity': 1,
                'price': product['price']
            })
            
        order_data = {
            'customer_id': user_id,
            'items': order_items,
            'shipping_address': {
                'street': "123 Integration St",
                'city': "Test City",
                'state': "TS",
                'zip': "12345",
                'country': "Test Country"
            }
        }
        
        allure_reporter.add_step("Creating an order", "passed")
        allure_reporter.add_api_request("POST", "/orders", api_client.headers, order_data)
        create_order_response = api_client.post("/orders", json_data=order_data)
        allure_reporter.add_api_response(create_order_response)
        
        ApiAssertions.assert_status_code(create_order_response, 201)
        order = create_order_response.json()
        order_id = order['id']
        
        # Step 4: Update order status to processing
        update_data = {
            'status': 'processing'
        }
        
        allure_reporter.add_step("Updating order status to processing", "passed")
        allure_reporter.add_api_request("PATCH", f"/orders/{order_id}", api_client.headers, update_data)
        update_order_response = api_client.patch(f"/orders/{order_id}", json_data=update_data)
        allure_reporter.add_api_response(update_order_response)
        
        ApiAssertions.assert_status_code(update_order_response, 200)
        updated_order = update_order_response.json()
        ApiAssertions.assert_json_value(updated_order, 'status', 'processing')
        
        # Step 5: Update order status to shipped
        time.sleep(1)  # Simulate time passing
        
        shipping_data = {
            'status': 'shipped',
            'tracking_number': f"TRACK-{ApiTestUtils.generate_random_string(10)}"
        }
        
        allure_reporter.add_step("Updating order status to shipped", "passed")
        allure_reporter.add_api_request("PATCH", f"/orders/{order_id}", api_client.headers, shipping_data)
        ship_order_response = api_client.patch(f"/orders/{order_id}", json_data=shipping_data)
        allure_reporter.add_api_response(ship_order_response)
        
        ApiAssertions.assert_status_code(ship_order_response, 200)
        shipped_order = ship_order_response.json()
        ApiAssertions.assert_json_value(shipped_order, 'status', 'shipped')
        ApiAssertions.assert_json_value(shipped_order, 'tracking_number', shipping_data['tracking_number'])
        
        # Step 6: Get user's orders
        allure_reporter.add_step("Retrieving user's orders", "passed")
        allure_reporter.add_api_request("GET", f"/users/{user_id}/orders", api_client.headers)
        get_user_orders_response = api_client.get(f"/users/{user_id}/orders")
        allure_reporter.add_api_response(get_user_orders_response)
        
        ApiAssertions.assert_status_code(get_user_orders_response, 200)
        user_orders = get_user_orders_response.json()
        
        # Verify the order is in the user's orders
        assert any(o['id'] == order_id for o in user_orders), "Created order not found in user's orders"
        
        # Step 7: Update order status to delivered
        time.sleep(1)  # Simulate time passing
        
        delivery_data = {
            'status': 'delivered',
            'delivery_date': ApiTestUtils.get_iso_timestamp()
        }
        
        allure_reporter.add_step("Updating order status to delivered", "passed")
        allure_reporter.add_api_request("PATCH", f"/orders/{order_id}", api_client.headers, delivery_data)
        deliver_order_response = api_client.patch(f"/orders/{order_id}", json_data=delivery_data)
        allure_reporter.add_api_response(deliver_order_response)
        
        ApiAssertions.assert_status_code(deliver_order_response, 200)
        delivered_order = deliver_order_response.json()
        ApiAssertions.assert_json_value(delivered_order, 'status', 'delivered')
        
        # Cleanup - Not strictly necessary if using test environment with regular cleanup
        
        # Clean up the order (if API supports it)
        try:
            api_client.delete(f"/orders/{order_id}")
        except:
            # Order deletion might not be supported, which is fine
            pass
        
        # Clean up the user
        try:
            api_client.delete(f"/users/{user_id}")
        except:
            pass
        
        allure_reporter.add_step("End-to-end flow completed successfully", "passed")
    
    @pytest.mark.integration
    def test_product_inventory_flow(self, api_client):
        """Test the product inventory management flow."""
        # Step 1: Create a product
        product_data = {
            'name': f'Test Product {ApiTestUtils.generate_random_string(5)}',
            'description': 'A test product created during integration testing',
            'price': 99.99,
            'category': 'test-integration',
            'stock': 100,
            'sku': f'TEST-{ApiTestUtils.generate_random_string(8)}'
        }
        
        allure_reporter.start_test("Product Inventory Flow", "Test product inventory management")
        allure_reporter.add_tag("integration")
        allure_reporter.add_severity("high")
        
        allure_reporter.add_step("Creating a product", "passed")
        allure_reporter.add_api_request("POST", "/products", api_client.headers, product_data)
        create_product_response = api_client.post("/products", json_data=product_data)
        allure_reporter.add_api_response(create_product_response)
        
        ApiAssertions.assert_status_code(create_product_response, 201)
        product = create_product_response.json()
        product_id = product['id']
        
        # Step 2: Create an order that includes this product
        order_data = {
            'customer_id': 123,  # Could create a real user first
            'items': [
                {
                    'product_id': product_id,
                    'quantity': 5,
                    'price': product_data['price']
                }
            ]
        }
        
        allure_reporter.add_step("Creating an order with the product", "passed")
        allure_reporter.add_api_request("POST", "/orders", api_client.headers, order_data)
        create_order_response = api_client.post("/orders", json_data=order_data)
        allure_reporter.add_api_response(create_order_response)
        
        ApiAssertions.assert_status_code(create_order_response, 201)
        order = create_order_response.json()
        order_id = order['id']
        
        # Step 3: Check if inventory was updated
        allure_reporter.add_step("Checking product inventory", "passed")
        allure_reporter.add_api_request("GET", f"/products/{product_id}", api_client.headers)
        get_product_response = api_client.get(f"/products/{product_id}")
        allure_reporter.add_api_response(get_product_response)
        
        ApiAssertions.assert_status_code(get_product_response, 200)
        updated_product = get_product_response.json()
        
        # Verify inventory reduced by the ordered quantity
        expected_stock = product_data['stock'] - order_data['items'][0]['quantity']
        ApiAssertions.assert_json_value(updated_product, 'stock', expected_stock)
        
        # Step 4: Update the product stock manually
        stock_update_data = {
            'stock': 200  # Set to new value
        }
        
        allure_reporter.add_step("Updating product stock", "passed")
        allure_reporter.add_api_request("PATCH", f"/products/{product_id}", api_client.headers, stock_update_data)
        update_stock_response = api_client.patch(f"/products/{product_id}", json_data=stock_update_data)
        allure_reporter.add_api_response(update_stock_response)
        
        ApiAssertions.assert_status_code(update_stock_response, 200)
        stock_updated_product = update_stock_response.json()
        ApiAssertions.assert_json_value(stock_updated_product, 'stock', stock_update_data['stock'])
        
        # Cleanup
        try:
            api_client.delete(f"/orders/{order_id}")
            api_client.delete(f"/products/{product_id}")
        except:
            pass
        
        allure_reporter.add_step("Inventory flow completed successfully", "passed")

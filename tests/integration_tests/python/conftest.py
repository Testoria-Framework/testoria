import pytest
import json
import os
from unittest.mock import patch, MagicMock

# Mock response class
class MockResponse:
    def __init__(self, status_code, json_data, headers=None):
        self.status_code = status_code
        self._json_data = json_data
        self.headers = headers or {"Content-Type": "application/json"}
        self.text = json.dumps(json_data)
        
    def json(self):
        return self._json_data

# Mock the BaseApiClient to avoid actual HTTP requests
@pytest.fixture(autouse=True)
def mock_api_client(monkeypatch):
    # Mock responses for different endpoints
    mock_users = [{"id": "user123", "name": "Test User", "email": "test@example.com"}]
    mock_products = [
        {"id": "prod1", "name": "Product 1", "price": 10.99, "stock": 100},
        {"id": "prod2", "name": "Product 2", "price": 20.99, "stock": 50}
    ]
    mock_orders = [{"id": "order1", "customer_id": "user123", "status": "pending"}]
    
    # Mock POST requests
    def mock_post(self, endpoint, json_data=None, **kwargs):
        if endpoint == "/users":
            response_data = {"id": "user123", "name": json_data.get("name"), "email": json_data.get("email")}
            return MockResponse(201, response_data)
        elif endpoint == "/orders":
            response_data = {
                "id": "order1", 
                "customer_id": json_data.get("customer_id"),
                "items": json_data.get("items", []),
                "total": sum(item.get("price", 0) * item.get("quantity", 0) for item in json_data.get("items", [])),
                "status": "pending",
                "created_at": "2023-01-01T00:00:00Z"
            }
            return MockResponse(201, response_data)
        elif endpoint == "/products":
            response_data = {
                "id": "prod-new",
                "name": json_data.get("name"),
                "price": json_data.get("price"),
                "stock": json_data.get("stock"),
                "category": json_data.get("category")
            }
            return MockResponse(201, response_data)
        return MockResponse(404, {"error": "Not found"})
    
    # Mock GET requests
    def mock_get(self, endpoint, params=None, **kwargs):
        if endpoint == "/users":
            return MockResponse(200, mock_users)
        elif endpoint.startswith("/users/") and endpoint.endswith("/orders"):
            return MockResponse(200, mock_orders)
        elif endpoint == "/products":
            return MockResponse(200, mock_products)
        elif endpoint.startswith("/products/"):
            product_id = endpoint.split("/")[-1]
            for product in mock_products:
                if product["id"] == product_id:
                    return MockResponse(200, product)
        elif endpoint.startswith("/orders/"):
            order_id = endpoint.split("/")[-1]
            if order_id == "order1":
                return MockResponse(200, mock_orders[0])
        return MockResponse(404, {"error": "Not found"})
    
    # Mock PATCH requests
    def mock_patch(self, endpoint, json_data=None, **kwargs):
        if endpoint.startswith("/orders/"):
            response_data = {
                "id": "order1",
                "customer_id": "user123",
                "status": json_data.get("status", "pending"),
                "tracking_number": json_data.get("tracking_number"),
                "updated_at": "2023-01-01T01:00:00Z"
            }
            return MockResponse(200, response_data)
        elif endpoint.startswith("/products/"):
            product_id = endpoint.split("/")[-1]
            response_data = {
                "id": product_id,
                "name": "Updated Product",
                "stock": json_data.get("stock", 100)
            }
            return MockResponse(200, response_data)
        return MockResponse(404, {"error": "Not found"})
    
    # Mock DELETE requests
    def mock_delete(self, endpoint, **kwargs):
        return MockResponse(204, {})
    
    # Apply the mocks
    monkeypatch.setattr("core.clients.base_api_client.BaseApiClient.post", mock_post)
    monkeypatch.setattr("core.clients.base_api_client.BaseApiClient.get", mock_get)
    monkeypatch.setattr("core.clients.base_api_client.BaseApiClient.patch", mock_patch)
    monkeypatch.setattr("core.clients.base_api_client.BaseApiClient.delete", mock_delete)
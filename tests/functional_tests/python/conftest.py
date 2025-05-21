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
    mock_orders = [
        {"id": "order1", "customer_id": "user123", "status": "pending", "items": [], "total": 0, "created_at": "2023-01-01T00:00:00Z"}
    ]
    
    # Mock POST requests
    def mock_post(self, endpoint, json_data=None, **kwargs):
        if endpoint == "/orders":
            response_data = {
                "id": "order-new", 
                "customer_id": json_data.get("customer_id"),
                "items": json_data.get("items", []),
                "total": sum(item.get("price", 0) * item.get("quantity", 0) for item in json_data.get("items", [])),
                "status": "pending",
                "created_at": "2023-01-01T00:00:00Z"
            }
            return MockResponse(201, response_data)
        return MockResponse(404, {"error": "Not found"})
    
    # Mock GET requests
    def mock_get(self, endpoint, params=None, **kwargs):
        if endpoint == "/orders":
            return MockResponse(200, mock_orders)
        elif endpoint.startswith("/orders/"):
            order_id = endpoint.split("/")[-1]
            if order_id == "order1":
                return MockResponse(200, mock_orders[0])
            else:
                return MockResponse(404, {"error": "Order not found"})
        return MockResponse(404, {"error": "Not found"})
    
    # Mock PATCH requests
    def mock_patch(self, endpoint, json_data=None, **kwargs):
        if endpoint.startswith("/orders/"):
            if endpoint.endswith("/cancel"):
                response_data = {
                    "id": "order1",
                    "status": "cancelled",
                    "cancellation_reason": json_data.get("cancellation_reason"),
                    "cancelled_at": "2023-01-01T01:00:00Z"
                }
            else:
                response_data = {
                    "id": "order1",
                    "status": json_data.get("status", "pending"),
                    "tracking_number": json_data.get("tracking_number"),
                    "updated_at": "2023-01-01T01:00:00Z"
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
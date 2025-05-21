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
    # Mock responses for security tests
    
    # Mock POST requests
    def mock_post(self, endpoint, json_data=None, **kwargs):
        if endpoint == "/auth/login":
            if json_data.get("username") == "admin" and json_data.get("password") == "password123":
                return MockResponse(200, {"token": "valid-token"})
            else:
                return MockResponse(401, {"error": "Invalid credentials"})
        return MockResponse(404, {"error": "Not found"})
    
    # Mock GET requests
    def mock_get(self, endpoint, params=None, **kwargs):
        headers = getattr(self, "headers", {})
        auth_header = headers.get("Authorization", "")
        
        if endpoint == "/users/me" and auth_header.startswith("Bearer valid-token"):
            return MockResponse(200, {"id": "user123", "role": "admin"})
        elif not auth_header or not auth_header.startswith("Bearer valid-token"):
            return MockResponse(401, {"error": "Unauthorized"})
        return MockResponse(404, {"error": "Not found"})
    
    # Apply the mocks
    monkeypatch.setattr("core.clients.base_api_client.BaseApiClient.post", mock_post)
    monkeypatch.setattr("core.clients.base_api_client.BaseApiClient.get", mock_get)
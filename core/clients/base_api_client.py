import requests
import json
import logging
from typing import Dict, Any, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BaseApiClient:
    """
    Base API client for making HTTP requests to REST APIs.
    Provides common functionality for all API interactions.
    """
    
    def __init__(self, base_url: str, headers: Optional[Dict[str, str]] = None):
        """
        Initialize the BaseApiClient with base URL and optional default headers.
        
        Args:
            base_url: The base URL for the API (e.g., https://api.example.com)
            headers: Optional default headers to include in all requests
        """
        self.base_url = base_url.rstrip('/')
        self.headers = headers or {}
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.last_response = None
    
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """
        Send a GET request to the specified API endpoint.
        
        Args:
            endpoint: The API endpoint to call (will be appended to base_url)
            params: Optional query parameters
            headers: Optional headers to override default headers for this request
            
        Returns:
            The Response object
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        merged_headers = {**self.headers, **(headers or {})}
        
        logger.info(f"Making GET request to {url}")
        if params:
            logger.debug(f"With params: {params}")
        
        self.last_response = self.session.get(url, params=params, headers=merged_headers)
        logger.debug(f"Response status code: {self.last_response.status_code}")
        return self.last_response
    
    def post(self, endpoint: str, data: Optional[Union[Dict[str, Any], str]] = None, 
             json_data: Optional[Dict[str, Any]] = None, 
             headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """
        Send a POST request to the specified API endpoint.
        
        Args:
            endpoint: The API endpoint to call (will be appended to base_url)
            data: Optional data payload as form data or string
            json_data: Optional JSON data payload
            headers: Optional headers to override default headers for this request
            
        Returns:
            The Response object
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        merged_headers = {**self.headers, **(headers or {})}
        
        logger.info(f"Making POST request to {url}")
        
        self.last_response = self.session.post(url, data=data, json=json_data, headers=merged_headers)
        logger.debug(f"Response status code: {self.last_response.status_code}")
        return self.last_response
    
    def put(self, endpoint: str, data: Optional[Union[Dict[str, Any], str]] = None, 
            json_data: Optional[Dict[str, Any]] = None, 
            headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """
        Send a PUT request to the specified API endpoint.
        
        Args:
            endpoint: The API endpoint to call (will be appended to base_url)
            data: Optional data payload as form data or string
            json_data: Optional JSON data payload
            headers: Optional headers to override default headers for this request
            
        Returns:
            The Response object
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        merged_headers = {**self.headers, **(headers or {})}
        
        logger.info(f"Making PUT request to {url}")
        
        self.last_response = self.session.put(url, data=data, json=json_data, headers=merged_headers)
        logger.debug(f"Response status code: {self.last_response.status_code}")
        return self.last_response
    
    def delete(self, endpoint: str, params: Optional[Dict[str, Any]] = None, 
               headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """
        Send a DELETE request to the specified API endpoint.
        
        Args:
            endpoint: The API endpoint to call (will be appended to base_url)
            params: Optional query parameters
            headers: Optional headers to override default headers for this request
            
        Returns:
            The Response object
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        merged_headers = {**self.headers, **(headers or {})}
        
        logger.info(f"Making DELETE request to {url}")
        
        self.last_response = self.session.delete(url, params=params, headers=merged_headers)
        logger.debug(f"Response status code: {self.last_response.status_code}")
        return self.last_response
    
    def patch(self, endpoint: str, data: Optional[Union[Dict[str, Any], str]] = None, 
              json_data: Optional[Dict[str, Any]] = None, 
              headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """
        Send a PATCH request to the specified API endpoint.
        
        Args:
            endpoint: The API endpoint to call (will be appended to base_url)
            data: Optional data payload as form data or string
            json_data: Optional JSON data payload
            headers: Optional headers to override default headers for this request
            
        Returns:
            The Response object
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        merged_headers = {**self.headers, **(headers or {})}
        
        logger.info(f"Making PATCH request to {url}")
        
        self.last_response = self.session.patch(url, data=data, json=json_data, headers=merged_headers)
        logger.debug(f"Response status code: {self.last_response.status_code}")
        return self.last_response
    
    def get_response_json(self) -> Dict[str, Any]:
        """
        Get the JSON response body from the last request, if available.
        
        Returns:
            The response body as a dictionary
        
        Raises:
            ValueError: If the response body is not valid JSON
        """
        if not self.last_response:
            raise ValueError("No response available. Make a request first.")
        
        try:
            return self.last_response.json()
        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON from response: {self.last_response.text}")
            raise ValueError("Response body is not valid JSON")
    
    def get_response_text(self) -> str:
        """
        Get the text response body from the last request, if available.
        
        Returns:
            The response body as a string
        
        Raises:
            ValueError: If no response is available
        """
        if not self.last_response:
            raise ValueError("No response available. Make a request first.")
        
        return self.last_response.text
    
    def get_response_status_code(self) -> int:
        """
        Get the status code from the last request, if available.
        
        Returns:
            The HTTP status code
        
        Raises:
            ValueError: If no response is available
        """
        if not self.last_response:
            raise ValueError("No response available. Make a request first.")
        
        return self.last_response.status_code
    
    def get_response_headers(self) -> Dict[str, str]:
        """
        Get the headers from the last request, if available.
        
        Returns:
            The response headers as a dictionary
        
        Raises:
            ValueError: If no response is available
        """
        if not self.last_response:
            raise ValueError("No response available. Make a request first.")
        
        return dict(self.last_response.headers)
    
    def set_authorization(self, auth_type: str, token: str) -> None:
        """
        Set the Authorization header.
        
        Args:
            auth_type: The authorization type (e.g., 'Bearer', 'Basic')
            token: The authorization token
        """
        self.headers['Authorization'] = f"{auth_type} {token}"
        self.session.headers.update(self.headers)
        
    def clear_authorization(self) -> None:
        """
        Clear the Authorization header.
        """
        if 'Authorization' in self.headers:
            del self.headers['Authorization']
            self.session.headers.pop('Authorization', None)

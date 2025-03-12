import json
import re
from typing import Any, Dict, List, Union, Optional
from assertpy import assert_that
import jsonschema
import requests

class ApiAssertions:
    """
    Utility class for API testing assertions.
    Provides methods to validate API responses, headers, status codes, and more.
    """
    
    @staticmethod
    def assert_status_code(response: requests.Response, expected_code: int) -> None:
        """
        Assert that the response has the expected status code.
        
        Args:
            response: The response object
            expected_code: Expected HTTP status code
            
        Raises:
            AssertionError: If the assertion fails
        """
        assert_that(response.status_code).is_equal_to(expected_code)
    
    @staticmethod
    def assert_success(response: requests.Response) -> None:
        """
        Assert that the response has a successful status code (2xx).
        
        Args:
            response: The response object
            
        Raises:
            AssertionError: If the assertion fails
        """
        assert_that(response.status_code).is_between(200, 299)
    
    @staticmethod
    def assert_client_error(response: requests.Response) -> None:
        """
        Assert that the response has a client error status code (4xx).
        
        Args:
            response: The response object
            
        Raises:
            AssertionError: If the assertion fails
        """
        assert_that(response.status_code).is_between(400, 499)
    
    @staticmethod
    def assert_server_error(response: requests.Response) -> None:
        """
        Assert that the response has a server error status code (5xx).
        
        Args:
            response: The response object
            
        Raises:
            AssertionError: If the assertion fails
        """
        assert_that(response.status_code).is_between(500, 599)
    
    @staticmethod
    def assert_header_exists(response: requests.Response, header_name: str) -> None:
        """
        Assert that the response contains the specified header.
        
        Args:
            response: The response object
            header_name: Header name to check
            
        Raises:
            AssertionError: If the assertion fails
        """
        assert_that(response.headers).contains_key(header_name)
    
    @staticmethod
    def assert_header_value(response: requests.Response, header_name: str, expected_value: str) -> None:
        """
        Assert that the response header has the expected value.
        
        Args:
            response: The response object
            header_name: Header name to check
            expected_value: Expected header value
            
        Raises:
            AssertionError: If the assertion fails
        """
        assert_that(response.headers).contains_key(header_name)
        assert_that(response.headers[header_name]).is_equal_to(expected_value)
    
    @staticmethod
    def assert_content_type(response: requests.Response, expected_content_type: str) -> None:
        """
        Assert that the response has the expected Content-Type header.
        
        Args:
            response: The response object
            expected_content_type: Expected Content-Type
            
        Raises:
            AssertionError: If the assertion fails
        """
        assert_that(response.headers).contains_key('Content-Type')
        assert_that(response.headers['Content-Type']).contains(expected_content_type)
    
    @staticmethod
    def assert_json_content_type(response: requests.Response) -> None:
        """
        Assert that the response has a JSON Content-Type header.
        
        Args:
            response: The response object
            
        Raises:
            AssertionError: If the assertion fails
        """
        ApiAssertions.assert_content_type(response, 'application/json')
    
    @staticmethod
    def assert_body_contains(response: requests.Response, expected_content: str) -> None:
        """
        Assert that the response body contains the expected content.
        
        Args:
            response: The response object
            expected_content: Expected content
            
        Raises:
            AssertionError: If the assertion fails
        """
        assert_that(response.text).contains(expected_content)
    
    @staticmethod
    def assert_json_body(response: requests.Response) -> Dict[str, Any]:
        """
        Assert that the response body is valid JSON and return the parsed JSON.
        
        Args:
            response: The response object
            
        Returns:
            The parsed JSON object
            
        Raises:
            AssertionError: If the assertion fails
        """
        try:
            json_data = response.json()
            assert_that(json_data).is_not_none()
            return json_data
        except json.JSONDecodeError:
            assert_that(False).is_true().described_as("Response body is not valid JSON")
            return {}  # For type checking, will never be reached
    
    @staticmethod
    def assert_json_has_key(json_data: Dict[str, Any], key: str) -> None:
        """
        Assert that the JSON object has the specified key.
        
        Args:
            json_data: The JSON object
            key: Key to check
            
        Raises:
            AssertionError: If the assertion fails
        """
        assert_that(json_data).contains_key(key)
    
    @staticmethod
    def assert_json_has_keys(json_data: Dict[str, Any], keys: List[str]) -> None:
        """
        Assert that the JSON object has all the specified keys.
        
        Args:
            json_data: The JSON object
            keys: List of keys to check
            
        Raises:
            AssertionError: If the assertion fails
        """
        for key in keys:
            assert_that(json_data).contains_key(key)
    
    @staticmethod
    def assert_json_value(json_data: Dict[str, Any], key: str, expected_value: Any) -> None:
        """
        Assert that the JSON object has the specified key with the expected value.
        
        Args:
            json_data: The JSON object
            key: Key to check
            expected_value: Expected value
            
        Raises:
            AssertionError: If the assertion fails
        """
        assert_that(json_data).contains_key(key)
        assert_that(json_data[key]).is_equal_to(expected_value)
    
    @staticmethod
    def assert_json_values(json_data: Dict[str, Any], key_values: Dict[str, Any]) -> None:
        """
        Assert that the JSON object has the specified keys with the expected values.
        
        Args:
            json_data: The JSON object
            key_values: Dictionary of key-value pairs to check
            
        Raises:
            AssertionError: If the assertion fails
        """
        for key, value in key_values.items():
            ApiAssertions.assert_json_value(json_data, key, value)
    
    @staticmethod
    def assert_json_matches_schema(json_data: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """
        Assert that the JSON object matches the specified schema.
        
        Args:
            json_data: The JSON object
            schema: JSON schema to validate against
            
        Raises:
            AssertionError: If the assertion fails
        """
        try:
            jsonschema.validate(instance=json_data, schema=schema)
        except jsonschema.exceptions.ValidationError as e:
            assert_that(False).is_true().described_as(f"JSON does not match schema: {str(e)}")
    
    @staticmethod
    def assert_response_time(response: requests.Response, max_time_ms: int) -> None:
        """
        Assert that the response time is below the maximum allowed time.
        
        Args:
            response: The response object
            max_time_ms: Maximum allowed response time in milliseconds
            
        Raises:
            AssertionError: If the assertion fails
        """
        # Response time is in seconds, convert to milliseconds
        response_time_ms = response.elapsed.total_seconds() * 1000
        assert_that(response_time_ms).is_less_than_or_equal_to(max_time_ms)
    
    @staticmethod
    def assert_json_list_length(json_data: Union[Dict[str, Any], List[Any]], path: str, expected_length: int) -> None:
        """
        Assert that a list in the JSON object has the expected length.
        
        Args:
            json_data: The JSON object
            path: Path to the list (e.g., 'data.items')
            expected_length: Expected length of the list
            
        Raises:
            AssertionError: If the assertion fails
        """
        parts = path.split('.')
        data = json_data
        
        for part in parts:
            if isinstance(data, dict):
                assert_that(data).contains_key(part)
                data = data[part]
            else:
                assert_that(False).is_true().described_as(f"Path '{path}' is invalid")
        
        assert_that(data).is_instance_of(list)
        assert_that(len(data)).is_equal_to(expected_length)
    
    @staticmethod
    def assert_json_list_contains_object(json_data: Union[Dict[str, Any], List[Any]], path: str, 
                                         key_value_pairs: Dict[str, Any]) -> None:
        """
        Assert that a list in the JSON object contains an object with the specified key-value pairs.
        
        Args:
            json_data: The JSON object
            path: Path to the list (e.g., 'data.items')
            key_value_pairs: Key-value pairs that the object should contain
            
        Raises:
            AssertionError: If the assertion fails
        """
        parts = path.split('.')
        data = json_data
        
        for part in parts:
            if isinstance(data, dict):
                assert_that(data).contains_key(part)
                data = data[part]
            else:
                assert_that(False).is_true().described_as(f"Path '{path}' is invalid")
        
        assert_that(data).is_instance_of(list)
        
        found = False
        for item in data:
            if all(item.get(key) == value for key, value in key_value_pairs.items()):
                found = True
                break
        
        assert_that(found).is_true().described_as(
            f"List doesn't contain an object with the specified key-value pairs: {key_value_pairs}")
    
    @staticmethod
    def assert_regex_match(text: str, regex_pattern: str) -> None:
        """
        Assert that the text matches the specified regex pattern.
        
        Args:
            text: Text to check
            regex_pattern: Regex pattern to match
            
        Raises:
            AssertionError: If the assertion fails
        """
        assert_that(bool(re.match(regex_pattern, text))).is_true().described_as(
            f"Text does not match pattern '{regex_pattern}'")

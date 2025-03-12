import time
import json
import random
import string
import logging
import datetime
import uuid
from typing import Dict, Any, List, Union, Optional
import requests
import jwt

logger = logging.getLogger(__name__)

class ApiTestUtils:
    """
    A collection of utility functions for API testing.
    """
    
    @staticmethod
    def generate_random_string(length: int = 10) -> str:
        """
        Generate a random string of specified length.
        
        Args:
            length: Length of the string to generate
            
        Returns:
            A random string
        """
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    @staticmethod
    def generate_random_email() -> str:
        """
        Generate a random email address.
        
        Returns:
            A random email address
        """
        username = ApiTestUtils.generate_random_string(8)
        domain = ApiTestUtils.generate_random_string(6)
        return f"{username}@{domain}.com"
    
    @staticmethod
    def generate_random_phone() -> str:
        """
        Generate a random phone number.
        
        Returns:
            A random phone number
        """
        return f"+1{random.randint(2, 9)}{random.randint(0, 9)}{''.join(str(random.randint(0, 9)) for _ in range(8))}"
    
    @staticmethod
    def generate_uuid() -> str:
        """
        Generate a UUID.
        
        Returns:
            A UUID string
        """
        return str(uuid.uuid4())
    
    @staticmethod
    def get_timestamp() -> int:
        """
        Get the current UNIX timestamp.
        
        Returns:
            Current UNIX timestamp in seconds
        """
        return int(time.time())
    
    @staticmethod
    def get_iso_timestamp() -> str:
        """
        Get the current timestamp in ISO 8601 format.
        
        Returns:
            Current timestamp in ISO 8601 format
        """
        return datetime.datetime.now().isoformat()
    
    @staticmethod
    def load_json_file(file_path: str) -> Dict[str, Any]:
        """
        Load a JSON file.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            The loaded JSON as a dictionary
            
        Raises:
            FileNotFoundError: If the file does not exist
            json.JSONDecodeError: If the file is not valid JSON
        """
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            raise
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in file: {file_path}")
            raise
    
    @staticmethod
    def save_json_file(data: Any, file_path: str) -> None:
        """
        Save data to a JSON file.
        
        Args:
            data: Data to save
            file_path: Path to the JSON file
            
        Raises:
            IOError: If the file cannot be written
        """
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError:
            logger.error(f"Error writing to file: {file_path}")
            raise
    
    @staticmethod
    def parse_jwt(token: str) -> Dict[str, Any]:
        """
        Parse a JWT token.
        
        Args:
            token: JWT token
            
        Returns:
            The decoded JWT payload
            
        Raises:
            jwt.InvalidTokenError: If the token is invalid
        """
        try:
            # Decode without verification (for testing purposes)
            return jwt.decode(token, options={"verify_signature": False})
        except jwt.InvalidTokenError:
            logger.error("Invalid JWT token")
            raise
    
    @staticmethod
    def wait_for_condition(condition_func, timeout: int = 30, interval: int = 1) -> bool:
        """
        Wait for a condition to be true.
        
        Args:
            condition_func: Function that returns True when the condition is met
            timeout: Maximum time to wait in seconds
            interval: Interval between checks in seconds
            
        Returns:
            True if the condition was met, False if the timeout was reached
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if condition_func():
                return True
            time.sleep(interval)
        return False
    
    @staticmethod
    def retry_on_failure(func, retries: int = 3, delay: int = 1, backoff: int = 2, 
                        expected_exceptions: tuple = (Exception,)):
        """
        Retry a function on failure.
        
        Args:
            func: Function to retry
            retries: Number of retries
            delay: Initial delay between retries in seconds
            backoff: Backoff multiplier for the delay
            expected_exceptions: Exceptions to catch and retry on
            
        Returns:
            The result of the function
            
        Raises:
            The last exception if all retries fail
        """
        retry_count = 0
        current_delay = delay
        
        while True:
            try:
                return func()
            except expected_exceptions as e:
                retry_count += 1
                if retry_count > retries:
                    logger.error(f"All {retries} retries failed. Last error: {str(e)}")
                    raise
                
                logger.warning(f"Retry {retry_count}/{retries} after error: {str(e)}")
                time.sleep(current_delay)
                current_delay *= backoff
    
    @staticmethod
    def compare_json_objects(obj1: Dict[str, Any], obj2: Dict[str, Any], 
                          ignore_keys: Optional[List[str]] = None) -> bool:
        """
        Compare two JSON objects for equality, optionally ignoring certain keys.
        
        Args:
            obj1: First JSON object
            obj2: Second JSON object
            ignore_keys: Keys to ignore in the comparison
            
        Returns:
            True if the objects are equal, False otherwise
        """
        if ignore_keys is None:
            ignore_keys = []
            
        # Create copies to avoid modifying the originals
        obj1_copy = obj1.copy()
        obj2_copy = obj2.copy()
        
        # Remove ignored keys
        for key in ignore_keys:
            obj1_copy.pop(key, None)
            obj2_copy.pop(key, None)
            
        return obj1_copy == obj2_copy
    
    @staticmethod
    def extract_nested_value(obj: Union[Dict[str, Any], List[Any]], path: str) -> Any:
        """
        Extract a value from a nested object using a path.
        
        Args:
            obj: Object to extract from
            path: Path to the value (e.g., 'data.items[0].id')
            
        Returns:
            The extracted value
            
        Raises:
            ValueError: If the path is invalid
        """
        parts = path.replace('[', '.').replace(']', '').split('.')
        current = obj
        
        for part in parts:
            if not part:  # Skip empty parts
                continue
                
            if isinstance(current, dict):
                if part not in current:
                    raise ValueError(f"Key '{part}' not found in path '{path}'")
                current = current[part]
            elif isinstance(current, list):
                try:
                    index = int(part)
                    if index >= len(current):
                        raise ValueError(f"Index {index} out of range in path '{path}'")
                    current = current[index]
                except ValueError:
                    raise ValueError(f"Invalid list index '{part}' in path '{path}'")
            else:
                raise ValueError(f"Cannot navigate further from {type(current)} in path '{path}'")
                
        return current
    
    @staticmethod
    def mask_sensitive_data(data: Union[Dict[str, Any], List[Any], str], 
                          sensitive_keys: List[str], mask: str = '******') -> Union[Dict[str, Any], List[Any], str]:
        """
        Mask sensitive data in an object.
        
        Args:
            data: Data to mask
            sensitive_keys: Keys to mask
            mask: Mask to use
            
        Returns:
            The masked data
        """
        if isinstance(data, dict):
            masked_data = {}
            for key, value in data.items():
                if key in sensitive_keys:
                    masked_data[key] = mask
                else:
                    masked_data[key] = ApiTestUtils.mask_sensitive_data(value, sensitive_keys, mask)
            return masked_data
        elif isinstance(data, list):
            return [ApiTestUtils.mask_sensitive_data(item, sensitive_keys, mask) for item in data]
        else:
            return data
    
    @staticmethod
    def get_base_url_from_request(request_url: str) -> str:
        """
        Extract the base URL from a request URL.
        
        Args:
            request_url: Request URL
            
        Returns:
            The base URL
        """
        parsed_url = requests.utils.urlparse(request_url)
        return f"{parsed_url.scheme}://{parsed_url.netloc}"
    
    @staticmethod
    def merge_dictionaries(dict1: Dict[str, Any], dict2: Dict[str, Any], 
                          overwrite: bool = True) -> Dict[str, Any]:
        """
        Merge two dictionaries.
        
        Args:
            dict1: First dictionary
            dict2: Second dictionary
            overwrite: Whether to overwrite values in dict1 with values from dict2
            
        Returns:
            The merged dictionary
        """
        result = dict1.copy()
        
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ApiTestUtils.merge_dictionaries(result[key], value, overwrite)
            elif key not in result or overwrite:
                result[key] = value
                
        return result

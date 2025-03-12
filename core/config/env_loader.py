import json
import os
import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ConfigLoader:
    """
    A utility class for loading and parsing configuration settings.
    Supports environment variable substitution and environment-specific configs.
    """
    
    def __init__(self, config_path: str = "core/config/config.json"):
        """
        Initialize the ConfigLoader with the path to the config file.
        
        Args:
            config_path: Path to the JSON configuration file
        """
        self.config_path = config_path
        self._config = None
        self._env_pattern = re.compile(r'\${(.*?)}')
    
    def load_config(self) -> Dict[str, Any]:
        """
        Load the configuration from the JSON file and process environment variables.
        
        Returns:
            The processed configuration dictionary
        
        Raises:
            FileNotFoundError: If the configuration file does not exist
            json.JSONDecodeError: If the configuration file is not valid JSON
        """
        if self._config is not None:
            return self._config
        
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                
            # Process environment variables in the configuration
            self._config = self._process_env_vars(config)
            return self._config
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            raise
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in configuration file: {self.config_path}")
            raise
    
    def get_environment_config(self, env: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the configuration for the specified environment.
        If no environment is specified, it uses the ENVIRONMENT environment variable,
        or falls back to 'dev'.
        
        Args:
            env: Optional environment name (default: None)
            
        Returns:
            The environment-specific configuration dictionary
            
        Raises:
            ValueError: If the specified environment does not exist in the configuration
        """
        if env is None:
            env = os.environ.get('ENVIRONMENT', 'dev')
        
        config = self.load_config()
        
        if 'environments' not in config or env not in config['environments']:
            logger.error(f"Environment '{env}' not found in configuration")
            raise ValueError(f"Environment '{env}' not found in configuration")
        
        return config['environments'][env]
    
    def get_test_settings(self, test_type: str) -> Dict[str, Any]:
        """
        Get the test settings for the specified test type.
        
        Args:
            test_type: Test type (e.g., 'functional', 'integration', 'performance', 'security')
            
        Returns:
            The test-type-specific settings dictionary
            
        Raises:
            ValueError: If the specified test type does not exist in the configuration
        """
        config = self.load_config()
        
        if 'test_settings' not in config or test_type not in config['test_settings']:
            logger.error(f"Test type '{test_type}' not found in configuration")
            raise ValueError(f"Test type '{test_type}' not found in configuration")
        
        return config['test_settings'][test_type]
    
    def get_reporting_config(self) -> Dict[str, Any]:
        """
        Get the reporting configuration.
        
        Returns:
            The reporting configuration dictionary
            
        Raises:
            ValueError: If reporting configuration is not found
        """
        config = self.load_config()
        
        if 'reporting' not in config:
            logger.error("Reporting configuration not found")
            raise ValueError("Reporting configuration not found")
        
        return config['reporting']
    
    def get_mock_config(self, mock_type: str) -> Dict[str, Any]:
        """
        Get the configuration for the specified mock type.
        
        Args:
            mock_type: Mock type (e.g., 'wiremock', 'mockserver')
            
        Returns:
            The mock-type-specific configuration dictionary
            
        Raises:
            ValueError: If the specified mock type does not exist in the configuration
        """
        config = self.load_config()
        
        if 'mocks' not in config or mock_type not in config['mocks']:
            logger.error(f"Mock type '{mock_type}' not found in configuration")
            raise ValueError(f"Mock type '{mock_type}' not found in configuration")
        
        return config['mocks'][mock_type]
    
    def get_logging_config(self) -> Dict[str, Any]:
        """
        Get the logging configuration.
        
        Returns:
            The logging configuration dictionary
            
        Raises:
            ValueError: If logging configuration is not found
        """
        config = self.load_config()
        
        if 'logging' not in config:
            logger.error("Logging configuration not found")
            raise ValueError("Logging configuration not found")
        
        return config['logging']
    
    def _process_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively process the configuration dictionary and substitute environment variables.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            The processed configuration dictionary with environment variables substituted
        """
        if isinstance(config, dict):
            return {k: self._process_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._process_env_vars(v) for v in config]
        elif isinstance(config, str):
            return self._substitute_env_vars(config)
        else:
            return config
    
    def _substitute_env_vars(self, value: str) -> str:
        """
        Substitute environment variables in a string.
        
        Args:
            value: String containing environment variable references (e.g., "${VAR_NAME}")
            
        Returns:
            The string with environment variables substituted
        """
        def _get_env_var(match):
            env_var_name = match.group(1)
            env_var_value = os.environ.get(env_var_name)
            
            if env_var_value is None:
                logger.warning(f"Environment variable '{env_var_name}' not found")
                return match.group(0)  # Return the original reference if not found
            
            return env_var_value
        
        return self._env_pattern.sub(_get_env_var, value)


# Singleton instance for global use
config_loader = ConfigLoader()

def get_config() -> Dict[str, Any]:
    """
    Get the full processed configuration.
    
    Returns:
        The processed configuration dictionary
    """
    return config_loader.load_config()

def get_environment_config(env: Optional[str] = None) -> Dict[str, Any]:
    """
    Get the configuration for the specified environment.
    
    Args:
        env: Optional environment name (default: None)
        
    Returns:
        The environment-specific configuration dictionary
    """
    return config_loader.get_environment_config(env)

def get_test_settings(test_type: str) -> Dict[str, Any]:
    """
    Get the test settings for the specified test type.
    
    Args:
        test_type: Test type (e.g., 'functional', 'integration', 'performance', 'security')
        
    Returns:
        The test-type-specific settings dictionary
    """
    return config_loader.get_test_settings(test_type)

def get_reporting_config() -> Dict[str, Any]:
    """
    Get the reporting configuration.
    
    Returns:
        The reporting configuration dictionary
    """
    return config_loader.get_reporting_config()

def get_base_url(env: Optional[str] = None) -> str:
    """
    Get the base URL for the specified environment.
    
    Args:
        env: Optional environment name (default: None)
        
    Returns:
        The base URL for the environment
    """
    env_config = get_environment_config(env)
    return env_config.get('base_url', '')

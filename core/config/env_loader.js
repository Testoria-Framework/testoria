const fs = require('fs');
const path = require('path');
const dotenv = require('dotenv');

// Load environment variables from .env file
dotenv.config();

/**
 * A utility class for loading and parsing configuration settings.
 * Supports environment variable substitution and environment-specific configs.
 */
class ConfigLoader {
  /**
   * Initialize the ConfigLoader with the path to the config file.
   * 
   * @param {string} configPath - Path to the JSON configuration file
   */
  constructor(configPath = 'core/config/config.json') {
    this.configPath = configPath;
    this._config = null;
    this._envPattern = /\${(.*?)}/g;
  }

  /**
   * Load the configuration from the JSON file and process environment variables.
   * 
   * @returns {Object} The processed configuration object
   * @throws {Error} If the configuration file cannot be read or parsed
   */
  loadConfig() {
    if (this._config !== null) {
      return this._config;
    }

    try {
      const configFile = fs.readFileSync(path.resolve(this.configPath), 'utf8');
      const config = JSON.parse(configFile);
      
      // Process environment variables in the configuration
      this._config = this._processEnvVars(config);
      return this._config;
    } catch (error) {
      console.error(`Error loading configuration: ${error.message}`);
      throw error;
    }
  }

  /**
   * Get the configuration for the specified environment.
   * If no environment is specified, it uses the ENVIRONMENT environment variable,
   * or falls back to 'dev'.
   * 
   * @param {string} [env] - Optional environment name
   * @returns {Object} The environment-specific configuration object
   * @throws {Error} If the specified environment does not exist in the configuration
   */
  getEnvironmentConfig(env) {
    if (!env) {
      env = process.env.ENVIRONMENT || 'dev';
    }

    const config = this.loadConfig();

    if (!config.environments || !config.environments[env]) {
      const error = new Error(`Environment '${env}' not found in configuration`);
      console.error(error.message);
      throw error;
    }

    return config.environments[env];
  }

  /**
   * Get the test settings for the specified test type.
   * 
   * @param {string} testType - Test type (e.g., 'functional', 'integration', 'performance', 'security')
   * @returns {Object} The test-type-specific settings object
   * @throws {Error} If the specified test type does not exist in the configuration
   */
  getTestSettings(testType) {
    const config = this.loadConfig();

    if (!config.test_settings || !config.test_settings[testType]) {
      const error = new Error(`Test type '${testType}' not found in configuration`);
      console.error(error.message);
      throw error;
    }

    return config.test_settings[testType];
  }

  /**
   * Get the reporting configuration.
   * 
   * @returns {Object} The reporting configuration object
   * @throws {Error} If reporting configuration is not found
   */
  getReportingConfig() {
    const config = this.loadConfig();

    if (!config.reporting) {
      const error = new Error('Reporting configuration not found');
      console.error(error.message);
      throw error;
    }

    return config.reporting;
  }

  /**
   * Get the configuration for the specified mock type.
   * 
   * @param {string} mockType - Mock type (e.g., 'wiremock', 'mockserver')
   * @returns {Object} The mock-type-specific configuration object
   * @throws {Error} If the specified mock type does not exist in the configuration
   */
  getMockConfig(mockType) {
    const config = this.loadConfig();

    if (!config.mocks || !config.mocks[mockType]) {
      const error = new Error(`Mock type '${mockType}' not found in configuration`);
      console.error(error.message);
      throw error;
    }

    return config.mocks[mockType];
  }

  /**
   * Get the logging configuration.
   * 
   * @returns {Object} The logging configuration object
   * @throws {Error} If logging configuration is not found
   */
  getLoggingConfig() {
    const config = this.loadConfig();

    if (!config.logging) {
      const error = new Error('Logging configuration not found');
      console.error(error.message);
      throw error;
    }

    return config.logging;
  }

  /**
   * Recursively process the configuration object and substitute environment variables.
   * 
   * @param {*} config - Configuration object or value
   * @returns {*} The processed configuration with environment variables substituted
   * @private
   */
  _processEnvVars(config) {
    if (typeof config === 'object' && config !== null) {
      if (Array.isArray(config)) {
        return config.map(item => this._processEnvVars(item));
      } else {
        const result = {};
        for (const key in config) {
          if (Object.prototype.hasOwnProperty.call(config, key)) {
            result[key] = this._processEnvVars(config[key]);
          }
        }
        return result;
      }
    } else if (typeof config === 'string') {
      return this._substituteEnvVars(config);
    } else {
      return config;
    }
  }

  /**
   * Substitute environment variables in a string.
   * 
   * @param {string} value - String containing environment variable references (e.g., "${VAR_NAME}")
   * @returns {string} The string with environment variables substituted
   * @private
   */
  _substituteEnvVars(value) {
    return value.replace(this._envPattern, (match, envVarName) => {
      const envVarValue = process.env[envVarName];
      
      if (envVarValue === undefined) {
        console.warn(`Environment variable '${envVarName}' not found`);
        return match; // Return the original reference if not found
      }
      
      return envVarValue;
    });
  }
}

// Singleton instance for global use
const configLoader = new ConfigLoader();

/**
 * Get the full processed configuration.
 * 
 * @returns {Object} The processed configuration object
 */
function getConfig() {
  return configLoader.loadConfig();
}

/**
 * Get the configuration for the specified environment.
 * 
 * @param {string} [env] - Optional environment name
 * @returns {Object} The environment-specific configuration object
 */
function getEnvironmentConfig(env) {
  return configLoader.getEnvironmentConfig(env);
}

/**
 * Get the test settings for the specified test type.
 * 
 * @param {string} testType - Test type (e.g., 'functional', 'integration', 'performance', 'security')
 * @returns {Object} The test-type-specific settings object
 */
function getTestSettings(testType) {
  return configLoader.getTestSettings(testType);
}

/**
 * Get the reporting configuration.
 * 
 * @returns {Object} The reporting configuration object
 */
function getReportingConfig() {
  return configLoader.getReportingConfig();
}

/**
 * Get the base URL for the specified environment.
 * 
 * @param {string} [env] - Optional environment name
 * @returns {string} The base URL for the environment
 */
function getBaseUrl(env) {
  const envConfig = getEnvironmentConfig(env);
  return envConfig.base_url || '';
}

/**
 * Get the timeout setting for the specified environment.
 * 
 * @param {string} [env] - Optional environment name
 * @returns {number} The timeout in milliseconds
 */
function getTimeout(env) {
  const envConfig = getEnvironmentConfig(env);
  return envConfig.timeout || 30000;
}

/**
 * Get the retry settings for the specified environment.
 * 
 * @param {string} [env] - Optional environment name
 * @returns {Object} The retry settings object with attempts and delay
 */
function getRetrySettings(env) {
  const envConfig = getEnvironmentConfig(env);
  return {
    attempts: envConfig.retry_attempts || 0,
    delay: envConfig.retry_delay || 1000
  };
}

module.exports = {
  getConfig,
  getEnvironmentConfig,
  getTestSettings,
  getReportingConfig,
  getBaseUrl,
  getTimeout,
  getRetrySettings
};

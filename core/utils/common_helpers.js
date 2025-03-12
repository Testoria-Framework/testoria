const fs = require('fs').promises;
const path = require('path');
const jwt = require('jsonwebtoken');
const _ = require('lodash');
const url = require('url');

/**
 * A collection of utility functions for API testing.
 */
class ApiTestUtils {
  /**
   * Generate a random string of specified length.
   * 
   * @param {number} [length=10] - Length of the string to generate
   * @returns {string} A random string
   */
  static generateRandomString(length = 10) {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < length; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
  }

  /**
   * Generate a random email address.
   * 
   * @returns {string} A random email address
   */
  static generateRandomEmail() {
    const username = this.generateRandomString(8);
    const domain = this.generateRandomString(6);
    return `${username}@${domain}.com`;
  }

  /**
   * Generate a random phone number.
   * 
   * @returns {string} A random phone number
   */
  static generateRandomPhone() {
    const areaCode = Math.floor(Math.random() * 800) + 200;
    const prefix = Math.floor(Math.random() * 900) + 100;
    const lineNumber = Math.floor(Math.random() * 9000) + 1000;
    return `+1${areaCode}${prefix}${lineNumber}`;
  }

  /**
   * Generate a UUID.
   * 
   * @returns {string} A UUID string
   */
  static generateUuid() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  /**
   * Get the current UNIX timestamp.
   * 
   * @returns {number} Current UNIX timestamp in seconds
   */
  static getTimestamp() {
    return Math.floor(Date.now() / 1000);
  }

  /**
   * Get the current timestamp in ISO 8601 format.
   * 
   * @returns {string} Current timestamp in ISO 8601 format
   */
  static getIsoTimestamp() {
    return new Date().toISOString();
  }

  /**
   * Load a JSON file.
   * 
   * @param {string} filePath - Path to the JSON file
   * @returns {Promise<Object>} The loaded JSON
   * @throws {Error} If the file does not exist or is not valid JSON
   */
  static async loadJsonFile(filePath) {
    try {
      const data = await fs.readFile(path.resolve(filePath), 'utf8');
      return JSON.parse(data);
    } catch (error) {
      console.error(`Error loading JSON file: ${error.message}`);
      throw error;
    }
  }

  /**
   * Save data to a JSON file.
   * 
   * @param {*} data - Data to save
   * @param {string} filePath - Path to the JSON file
   * @returns {Promise<void>}
   * @throws {Error} If the file cannot be written
   */
  static async saveJsonFile(data, filePath) {
    try {
      const dirPath = path.dirname(filePath);
      await fs.mkdir(dirPath, { recursive: true });
      await fs.writeFile(path.resolve(filePath), JSON.stringify(data, null, 2));
    } catch (error) {
      console.error(`Error saving JSON file: ${error.message}`);
      throw error;
    }
  }

  /**
   * Parse a JWT token.
   * 
   * @param {string} token - JWT token
   * @returns {Object} The decoded JWT payload
   * @throws {Error} If the token is invalid
   */
  static parseJwt(token) {
    try {
      // Decode without verification (for testing purposes)
      return jwt.decode(token);
    } catch (error) {
      console.error(`Invalid JWT token: ${error.message}`);
      throw error;
    }
  }

  /**
   * Wait for a condition to be true.
   * 
   * @param {Function} conditionFunc - Function that returns a promise resolving to true when the condition is met
   * @param {number} [timeout=30000] - Maximum time to wait in milliseconds
   * @param {number} [interval=1000] - Interval between checks in milliseconds
   * @returns {Promise<boolean>} True if the condition was met, false if the timeout was reached
   */
  static async waitForCondition(conditionFunc, timeout = 30000, interval = 1000) {
    const startTime = Date.now();
    while (Date.now() - startTime < timeout) {
      if (await conditionFunc()) {
        return true;
      }
      await new Promise(resolve => setTimeout(resolve, interval));
    }
    return false;
  }

  /**
   * Retry a function on failure.
   * 
   * @param {Function} func - Function to retry that returns a promise
   * @param {Object} [options] - Retry options
   * @param {number} [options.retries=3] - Number of retries
   * @param {number} [options.delay=1000] - Initial delay between retries in milliseconds
   * @param {number} [options.backoff=2] - Backoff multiplier for the delay
   * @returns {Promise<*>} The result of the function
   * @throws {Error} The last error if all retries fail
   */
  static async retryOnFailure(func, { retries = 3, delay = 1000, backoff = 2 } = {}) {
    let retryCount = 0;
    let currentDelay = delay;
    
    while (true) {
      try {
        return await func();
      } catch (error) {
        retryCount++;
        if (retryCount > retries) {
          console.error(`All ${retries} retries failed. Last error: ${error.message}`);
          throw error;
        }
        
        console.warn(`Retry ${retryCount}/${retries} after error: ${error.message}`);
        await new Promise(resolve => setTimeout(resolve, currentDelay));
        currentDelay *= backoff;
      }
    }
  }

  /**
   * Compare two JSON objects for equality, optionally ignoring certain keys.
   * 
   * @param {Object} obj1 - First JSON object
   * @param {Object} obj2 - Second JSON object
   * @param {Array<string>} [ignoreKeys=[]] - Keys to ignore in the comparison
   * @returns {boolean} True if the objects are equal, false otherwise
   */
  static compareJsonObjects(obj1, obj2, ignoreKeys = []) {
    // Create deep clones to avoid modifying the originals
    const obj1Copy = _.cloneDeep(obj1);
    const obj2Copy = _.cloneDeep(obj2);
    
    // Remove ignored keys
    ignoreKeys.forEach(key => {
      _.unset(obj1Copy, key);
      _.unset(obj2Copy, key);
    });
    
    return _.isEqual(obj1Copy, obj2Copy);
  }

  /**
   * Extract a value from a nested object using a path.
   * 
   * @param {Object|Array} obj - Object to extract from
   * @param {string} path - Path to the value (e.g., 'data.items[0].id')
   * @returns {*} The extracted value
   * @throws {Error} If the path is invalid
   */
  static extractNestedValue(obj, path) {
    try {
      return _.get(obj, path);
    } catch (error) {
      throw new Error(`Failed to extract value at path '${path}': ${error.message}`);
    }
  }

  /**
   * Mask sensitive data in an object.
   * 
   * @param {*} data - Data to mask
   * @param {Array<string>} sensitiveKeys - Keys to mask
   * @param {string} [mask='******'] - Mask to use
   * @returns {*} The masked data
   */
  static maskSensitiveData(data, sensitiveKeys, mask = '******') {
    if (!data) return data;
    
    if (Array.isArray(data)) {
      return data.map(item => this.maskSensitiveData(item, sensitiveKeys, mask));
    }
    
    if (typeof data === 'object') {
      const result = {};
      
      for (const [key, value] of Object.entries(data)) {
        if (sensitiveKeys.includes(key)) {
          result[key] = mask;
        } else if (typeof value === 'object' && value !== null) {
          result[key] = this.maskSensitiveData(value, sensitiveKeys, mask);
        } else {
          result[key] = value;
        }
      }
      
      return result;
    }
    
    return data;
  }

  /**
   * Extract the base URL from a request URL.
   * 
   * @param {string} requestUrl - Request URL
   * @returns {string} The base URL
   */
  static getBaseUrlFromRequest(requestUrl) {
    const parsedUrl = new URL(requestUrl);
    return `${parsedUrl.protocol}//${parsedUrl.host}`;
  }

  /**
   * Merge two objects deeply.
   * 
   * @param {Object} obj1 - First object
   * @param {Object} obj2 - Second object
   * @param {boolean} [overwrite=true] - Whether to overwrite values in obj1 with values from obj2
   * @returns {Object} The merged object
   */
  static mergeObjects(obj1, obj2, overwrite = true) {
    if (overwrite) {
      return _.merge({}, obj1, obj2);
    } else {
      return _.merge({}, obj2, obj1);
    }
  }

  /**
   * Sleep for a specified duration.
   * 
   * @param {number} ms - Duration in milliseconds
   * @returns {Promise<void>}
   */
  static sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Format a date according to the specified format.
   * 
   * @param {Date|string|number} date - Date to format
   * @param {string} format - Format string (e.g., 'YYYY-MM-DD')
   * @returns {string} The formatted date
   */
  static formatDate(date, format) {
    const d = new Date(date);
    
    const formatMap = {
      YYYY: d.getFullYear(),
      MM: String(d.getMonth() + 1).padStart(2, '0'),
      DD: String(d.getDate()).padStart(2, '0'),
      HH: String(d.getHours()).padStart(2, '0'),
      mm: String(d.getMinutes()).padStart(2, '0'),
      ss: String(d.getSeconds()).padStart(2, '0')
    };
    
    let result = format;
    for (const [key, value] of Object.entries(formatMap)) {
      result = result.replace(key, value);
    }
    
    return result;
  }
}

module.exports = ApiTestUtils;

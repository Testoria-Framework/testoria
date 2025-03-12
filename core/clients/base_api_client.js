const axios = require('axios');
const axiosRetry = require('axios-retry');

/**
 * Base API client for making HTTP requests to REST APIs.
 * Provides common functionality for all API interactions.
 */
class BaseApiClient {
  /**
   * Initialize the BaseApiClient with base URL and optional default headers.
   * 
   * @param {string} baseUrl - The base URL for the API (e.g., https://api.example.com)
   * @param {Object} [headers={}] - Optional default headers to include in all requests
   * @param {Object} [config={}] - Optional axios configuration
   */
  constructor(baseUrl, headers = {}, config = {}) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.headers = headers;
    
    // Create an axios instance with default configuration
    this.client = axios.create({
      baseURL: this.baseUrl,
      headers: this.headers,
      ...config
    });
    
    // Add retry capability
    axiosRetry(this.client, { 
      retries: 3,
      retryDelay: axiosRetry.exponentialDelay 
    });
    
    this.lastResponse = null;
    
    // Add response interceptor to store the last response
    this.client.interceptors.response.use(
      (response) => {
        this.lastResponse = response;
        return response;
      },
      (error) => {
        this.lastResponse = error.response;
        return Promise.reject(error);
      }
    );
  }
  
  /**
   * Join the endpoint to the base URL, handling slashes correctly
   * 
   * @param {string} endpoint - The API endpoint
   * @returns {string} The complete URL
   * @private
   */
  _buildUrl(endpoint) {
    return `${this.baseUrl}/${endpoint.replace(/^\//, '')}`;
  }
  
  /**
   * Merge the default headers with the provided request-specific headers
   * 
   * @param {Object} headers - Request-specific headers
   * @returns {Object} Merged headers
   * @private
   */
  _mergeHeaders(headers = {}) {
    return { ...this.headers, ...headers };
  }
  
  /**
   * Log request information
   * 
   * @param {string} method - HTTP method
   * @param {string} url - Request URL
   * @param {Object} [data] - Request data
   * @private
   */
  _logRequest(method, url, data) {
    console.log(`Making ${method.toUpperCase()} request to ${url}`);
    if (data) {
      console.debug('With data:', data);
    }
  }
  
  /**
   * Send a GET request to the specified API endpoint.
   * 
   * @param {string} endpoint - The API endpoint to call (will be appended to baseUrl)
   * @param {Object} [params] - Optional query parameters
   * @param {Object} [headers] - Optional headers to override default headers for this request
   * @returns {Promise<Object>} The axios response
   */
  async get(endpoint, params = {}, headers = {}) {
    const url = this._buildUrl(endpoint);
    const mergedHeaders = this._mergeHeaders(headers);
    
    this._logRequest('GET', url, params);
    
    try {
      return await this.client.get(endpoint, {
        params,
        headers: mergedHeaders
      });
    } catch (error) {
      console.error(`GET request to ${url} failed:`, error.message);
      throw error;
    }
  }
  
  /**
   * Send a POST request to the specified API endpoint.
   * 
   * @param {string} endpoint - The API endpoint to call (will be appended to baseUrl)
   * @param {Object|string} [data] - Optional data payload
   * @param {Object} [headers] - Optional headers to override default headers for this request
   * @returns {Promise<Object>} The axios response
   */
  async post(endpoint, data = {}, headers = {}) {
    const url = this._buildUrl(endpoint);
    const mergedHeaders = this._mergeHeaders(headers);
    
    this._logRequest('POST', url, data);
    
    try {
      return await this.client.post(endpoint, data, {
        headers: mergedHeaders
      });
    } catch (error) {
      console.error(`POST request to ${url} failed:`, error.message);
      throw error;
    }
  }
  
  /**
   * Send a PUT request to the specified API endpoint.
   * 
   * @param {string} endpoint - The API endpoint to call (will be appended to baseUrl)
   * @param {Object|string} [data] - Optional data payload
   * @param {Object} [headers] - Optional headers to override default headers for this request
   * @returns {Promise<Object>} The axios response
   */
  async put(endpoint, data = {}, headers = {}) {
    const url = this._buildUrl(endpoint);
    const mergedHeaders = this._mergeHeaders(headers);
    
    this._logRequest('PUT', url, data);
    
    try {
      return await this.client.put(endpoint, data, {
        headers: mergedHeaders
      });
    } catch (error) {
      console.error(`PUT request to ${url} failed:`, error.message);
      throw error;
    }
  }
  
  /**
   * Send a DELETE request to the specified API endpoint.
   * 
   * @param {string} endpoint - The API endpoint to call (will be appended to baseUrl)
   * @param {Object} [params] - Optional query parameters
   * @param {Object} [headers] - Optional headers to override default headers for this request
   * @returns {Promise<Object>} The axios response
   */
  async delete(endpoint, params = {}, headers = {}) {
    const url = this._buildUrl(endpoint);
    const mergedHeaders = this._mergeHeaders(headers);
    
    this._logRequest('DELETE', url, params);
    
    try {
      return await this.client.delete(endpoint, {
        params,
        headers: mergedHeaders
      });
    } catch (error) {
      console.error(`DELETE request to ${url} failed:`, error.message);
      throw error;
    }
  }
  
  /**
   * Send a PATCH request to the specified API endpoint.
   * 
   * @param {string} endpoint - The API endpoint to call (will be appended to baseUrl)
   * @param {Object|string} [data] - Optional data payload
   * @param {Object} [headers] - Optional headers to override default headers for this request
   * @returns {Promise<Object>} The axios response
   */
  async patch(endpoint, data = {}, headers = {}) {
    const url = this._buildUrl(endpoint);
    const mergedHeaders = this._mergeHeaders(headers);
    
    this._logRequest('PATCH', url, data);
    
    try {
      return await this.client.patch(endpoint, data, {
        headers: mergedHeaders
      });
    } catch (error) {
      console.error(`PATCH request to ${url} failed:`, error.message);
      throw error;
    }
  }
  
  /**
   * Get response data from the last request, if available.
   * 
   * @returns {Object|string} The response data
   * @throws {Error} If no response is available
   */
  getResponseData() {
    if (!this.lastResponse) {
      throw new Error('No response available. Make a request first.');
    }
    
    return this.lastResponse.data;
  }
  
  /**
   * Get the status code from the last request, if available.
   * 
   * @returns {number} The HTTP status code
   * @throws {Error} If no response is available
   */
  getResponseStatusCode() {
    if (!this.lastResponse) {
      throw new Error('No response available. Make a request first.');
    }
    
    return this.lastResponse.status;
  }
  
  /**
   * Get the headers from the last request, if available.
   * 
   * @returns {Object} The response headers
   * @throws {Error} If no response is available
   */
  getResponseHeaders() {
    if (!this.lastResponse) {
      throw new Error('No response available. Make a request first.');
    }
    
    return this.lastResponse.headers;
  }
  
  /**
   * Set the Authorization header.
   * 
   * @param {string} authType - The authorization type (e.g., 'Bearer', 'Basic')
   * @param {string} token - The authorization token
   */
  setAuthorization(authType, token) {
    this.headers.Authorization = `${authType} ${token}`;
    this.client.defaults.headers.common.Authorization = `${authType} ${token}`;
  }
  
  /**
   * Clear the Authorization header.
   */
  clearAuthorization() {
    delete this.headers.Authorization;
    delete this.client.defaults.headers.common.Authorization;
  }
  
  /**
   * Set a request timeout.
   * 
   * @param {number} timeout - Timeout in milliseconds
   */
  setTimeout(timeout) {
    this.client.defaults.timeout = timeout;
  }
}

module.exports = BaseApiClient;

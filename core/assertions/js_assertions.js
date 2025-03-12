const Ajv = require('ajv');
const chai = require('chai');
const expect = chai.expect;
const chaiJsonSchema = require('chai-json-schema');
const _ = require('lodash');

chai.use(chaiJsonSchema);
const ajv = new Ajv();

/**
 * Utility class for API testing assertions in JavaScript.
 * Provides methods to validate API responses, headers, status codes, and more.
 */
class ApiAssertions {
  /**
   * Assert that the response has the expected status code.
   * 
   * @param {Object} response - The Axios response object
   * @param {number} expectedCode - Expected HTTP status code
   * @throws {AssertionError} If the assertion fails
   */
  static assertStatusCode(response, expectedCode) {
    expect(response.status).to.equal(expectedCode);
  }
  
  /**
   * Assert that the response has a successful status code (2xx).
   * 
   * @param {Object} response - The Axios response object
   * @throws {AssertionError} If the assertion fails
   */
  static assertSuccess(response) {
    expect(response.status).to.be.within(200, 299);
  }
  
  /**
   * Assert that the response has a client error status code (4xx).
   * 
   * @param {Object} response - The Axios response object
   * @throws {AssertionError} If the assertion fails
   */
  static assertClientError(response) {
    expect(response.status).to.be.within(400, 499);
  }
  
  /**
   * Assert that the response has a server error status code (5xx).
   * 
   * @param {Object} response - The Axios response object
   * @throws {AssertionError} If the assertion fails
   */
  static assertServerError(response) {
    expect(response.status).to.be.within(500, 599);
  }
  
  /**
   * Assert that the response contains the specified header.
   * 
   * @param {Object} response - The Axios response object
   * @param {string} headerName - Header name to check (case-insensitive)
   * @throws {AssertionError} If the assertion fails
   */
  static assertHeaderExists(response, headerName) {
    const normalizedHeaderName = headerName.toLowerCase();
    const headers = Object.keys(response.headers).map(h => h.toLowerCase());
    expect(headers).to.include(normalizedHeaderName);
  }
  
  /**
   * Assert that the response header has the expected value.
   * 
   * @param {Object} response - The Axios response object
   * @param {string} headerName - Header name to check (case-insensitive)
   * @param {string} expectedValue - Expected header value
   * @throws {AssertionError} If the assertion fails
   */
  static assertHeaderValue(response, headerName, expectedValue) {
    const normalizedHeaderName = headerName.toLowerCase();
    const headers = response.headers;
    
    // Find the actual header name with the correct case
    const actualHeaderName = Object.keys(headers).find(
      h => h.toLowerCase() === normalizedHeaderName
    );
    
    expect(actualHeaderName).to.not.be.undefined;
    expect(headers[actualHeaderName]).to.equal(expectedValue);
  }
  
  /**
   * Assert that the response has the expected Content-Type header.
   * 
   * @param {Object} response - The Axios response object
   * @param {string} expectedContentType - Expected Content-Type
   * @throws {AssertionError} If the assertion fails
   */
  static assertContentType(response, expectedContentType) {
    this.assertHeaderExists(response, 'content-type');
    const contentType = response.headers['content-type'] || '';
    expect(contentType).to.include(expectedContentType);
  }
  
  /**
   * Assert that the response has a JSON Content-Type header.
   * 
   * @param {Object} response - The Axios response object
   * @throws {AssertionError} If the assertion fails
   */
  static assertJsonContentType(response) {
    this.assertContentType(response, 'application/json');
  }
  
  /**
   * Assert that the response body contains the expected content.
   * 
   * @param {Object} response - The Axios response object
   * @param {string} expectedContent - Expected content
   * @throws {AssertionError} If the assertion fails
   */
  static assertBodyContains(response, expectedContent) {
    let responseBody;
    
    if (typeof response.data === 'object') {
      responseBody = JSON.stringify(response.data);
    } else {
      responseBody = String(response.data);
    }
    
    expect(responseBody).to.include(expectedContent);
  }
  
  /**
   * Assert that the JSON response has the specified key.
   * 
   * @param {Object} response - The Axios response object or JSON object
   * @param {string} key - Key to check
   * @throws {AssertionError} If the assertion fails
   */
  static assertJsonHasKey(response, key) {
    const data = response.data || response;
    expect(data).to.have.property(key);
  }
  
  /**
   * Assert that the JSON response has all the specified keys.
   * 
   * @param {Object} response - The Axios response object or JSON object
   * @param {Array<string>} keys - List of keys to check
   * @throws {AssertionError} If the assertion fails
   */
  static assertJsonHasKeys(response, keys) {
    const data = response.data || response;
    keys.forEach(key => {
      expect(data).to.have.property(key);
    });
  }
  
  /**
   * Assert that the JSON response has the specified key with the expected value.
   * 
   * @param {Object} response - The Axios response object or JSON object
   * @param {string} key - Key to check
   * @param {*} expectedValue - Expected value
   * @throws {AssertionError} If the assertion fails
   */
  static assertJsonValue(response, key, expectedValue) {
    const data = response.data || response;
    expect(data).to.have.property(key);
    expect(data[key]).to.deep.equal(expectedValue);
  }
  
  /**
   * Assert that the JSON response has the specified keys with the expected values.
   * 
   * @param {Object} response - The Axios response object or JSON object
   * @param {Object} keyValues - Dictionary of key-value pairs to check
   * @throws {AssertionError} If the assertion fails
   */
  static assertJsonValues(response, keyValues) {
    const data = response.data || response;
    Object.entries(keyValues).forEach(([key, value]) => {
      this.assertJsonValue(data, key, value);
    });
  }
  
  /**
   * Assert that the JSON response matches the specified schema.
   * 
   * @param {Object} response - The Axios response object or JSON object
   * @param {Object} schema - JSON schema to validate against
   * @throws {AssertionError} If the assertion fails
   */
  static assertJsonMatchesSchema(response, schema) {
    const data = response.data || response;
    expect(data).to.be.jsonSchema(schema);
  }
  
  /**
   * Get a value from a nested path in an object.
   * 
   * @param {Object} obj - The object to traverse
   * @param {string} path - Path to the value (e.g., 'data.items')
   * @returns {*} The value at the path
   * @private
   */
  static _getValueAtPath(obj, path) {
    return _.get(obj, path);
  }
  
  /**
   * Assert that a list in the JSON response has the expected length.
   * 
   * @param {Object} response - The Axios response object or JSON object
   * @param {string} path - Path to the list (e.g., 'data.items')
   * @param {number} expectedLength - Expected length of the list
   * @throws {AssertionError} If the assertion fails
   */
  static assertJsonListLength(response, path, expectedLength) {
    const data = response.data || response;
    const list = this._getValueAtPath(data, path);
    
    expect(list).to.be.an('array');
    expect(list).to.have.lengthOf(expectedLength);
  }
  
  /**
   * Assert that a list in the JSON response contains an object with the specified key-value pairs.
   * 
   * @param {Object} response - The Axios response object or JSON object
   * @param {string} path - Path to the list (e.g., 'data.items')
   * @param {Object} keyValuePairs - Key-value pairs that the object should contain
   * @throws {AssertionError} If the assertion fails
   */
  static assertJsonListContainsObject(response, path, keyValuePairs) {
    const data = response.data || response;
    const list = this._getValueAtPath(data, path);
    
    expect(list).to.be.an('array');
    
    const found = list.some(item => {
      return Object.entries(keyValuePairs).every(([key, value]) => {
        return _.get(item, key) === value;
      });
    });
    
    expect(found).to.be.true;
  }
  
  /**
   * Assert that the text matches the specified regex pattern.
   * 
   * @param {string} text - Text to check
   * @param {string|RegExp} regexPattern - Regex pattern to match
   * @throws {AssertionError} If the assertion fails
   */
  static assertRegexMatch(text, regexPattern) {
    const regex = typeof regexPattern === 'string' ? new RegExp(regexPattern) : regexPattern;
    expect(text).to.match(regex);
  }
  
  /**
   * Assert that the response time is below the maximum allowed time.
   * 
   * @param {Object} response - The Axios response object
   * @param {number} maxTimeMs - Maximum allowed response time in milliseconds
   * @throws {AssertionError} If the assertion fails
   */
  static assertResponseTime(response, maxTimeMs) {
    if (!response.config || !response.config.metadata || !response.config.metadata.responseTime) {
      throw new Error('Response time is not available. Make sure you configure Axios to track response time.');
    }
    
    const responseTimeMs = response.config.metadata.responseTime;
    expect(responseTimeMs).to.be.at.most(maxTimeMs);
  }
  
  /**
   * Assert that two JSONs are equivalent (same structure and values, regardless of order).
   * 
   * @param {Object} actual - The actual JSON object
   * @param {Object} expected - The expected JSON object
   * @throws {AssertionError} If the assertion fails
   */
  static assertJsonEquivalent(actual, expected) {
    expect(actual).to.deep.equal(expected);
  }
  
  /**
   * Assert that the response body is not empty.
   * 
   * @param {Object} response - The Axios response object
   * @throws {AssertionError} If the assertion fails
   */
  static assertNonEmptyResponse(response) {
    const data = response.data;
    
    if (typeof data === 'string') {
      expect(data.trim()).to.not.be.empty;
    } else if (Array.isArray(data)) {
      expect(data.length).to.be.greaterThan(0);
    } else if (typeof data === 'object' && data !== null) {
      expect(Object.keys(data)).to.have.lengthOf.greaterThan(0);
    } else {
      expect(data).to.not.be.undefined;
      expect(data).to.not.be.null;
    }
  }
}

module.exports = ApiAssertions;

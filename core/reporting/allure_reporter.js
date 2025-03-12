const allure = require('allure-js-commons');
const { createHash } = require('crypto');
const fs = require('fs').promises;
const path = require('path');

const { getReportingConfig } = require('../config/env_loader');

/**
 * A utility class for reporting API test results to Allure.
 */
class AllureReporter {
  /**
   * Initialize the AllureReporter with the reporting configuration.
   */
  constructor() {
    const reportConfig = getReportingConfig().allure || {};
    this.enabled = reportConfig.enabled !== false;
    this.reportDir = reportConfig.report_dir || 'reports/allure-results';
    
    if (!this.enabled) {
      console.info('Allure reporting is disabled');
      return;
    }
    
    this.runtime = new allure.AllureRuntime({ resultsDir: this.reportDir });
    this.writer = new allure.FileSystemResultWriter(this.reportDir);
    this.currentTest = null;
    this.currentExecutable = null;
    
    // Make sure the report directory exists
    this._ensureReportDir();
  }
  
  /**
   * Ensure that the report directory exists.
   * 
   * @private
   */
  async _ensureReportDir() {
    if (!this.enabled) return;
    
    try {
      await fs.mkdir(this.reportDir, { recursive: true });
    } catch (error) {
      console.error(`Failed to create Allure report directory: ${error.message}`);
    }
  }
  
  /**
   * Start a test case.
   * 
   * @param {string} testName - Name of the test
   * @param {string} [description] - Optional description of the test
   */
  startTest(testName, description) {
    if (!this.enabled) return;
    
    // Generate a unique UUID for the test
    const uuid = createHash('md5').update(`${testName}-${Date.now()}`).digest('hex');
    
    this.currentTest = new allure.TestResult(uuid);
    this.currentTest.name = testName;
    this.currentTest.historyId = createHash('md5').update(testName).digest('hex');
    this.currentTest.fullName = testName;
    this.currentTest.start = Date.now();
    
    if (description) {
      this.currentTest.description = description;
    }
    
    this.currentExecutable = this.currentTest;
  }
  
  /**
   * End a test case.
   * 
   * @param {string} [status='passed'] - Test status (passed, failed, broken, skipped)
   * @param {Error} [error] - Error object if the test failed
   */
  endTest(status = 'passed', error) {
    if (!this.enabled || !this.currentTest) return;
    
    this.currentTest.status = status;
    this.currentTest.stage = allure.Stage.FINISHED;
    this.currentTest.stop = Date.now();
    
    if (error) {
      this.currentTest.statusDetails = {
        message: error.message,
        trace: error.stack
      };
    }
    
    this.runtime.writeTest(this.currentTest);
    this.currentTest = null;
    this.currentExecutable = null;
  }
  
  /**
   * Add a step to the current test.
   * 
   * @param {string} name - Name of the step
   * @param {string} [status='passed'] - Status of the step (passed, failed, broken, skipped)
   * @param {string} [details] - Optional details of the step
   */
  addStep(name, status = 'passed', details) {
    if (!this.enabled || !this.currentExecutable) return;
    
    const step = new allure.StepResult(name);
    step.status = status;
    step.stage = allure.Stage.FINISHED;
    
    if (details) {
      this.runtime.writeAttachment(
        details,
        'Step Details',
        'text/plain'
      );
    }
    
    this.currentExecutable.steps.push(step);
  }
  
  /**
   * Add an API request to the current test.
   * 
   * @param {string} method - HTTP method
   * @param {string} url - Request URL
   * @param {Object} [headers] - Request headers
   * @param {Object|string} [body] - Request body
   */
  addApiRequest(method, url, headers, body) {
    if (!this.enabled || !this.currentExecutable) return;
    
    const stepName = `${method} ${url}`;
    this.addStep(stepName);
    
    // Attach headers
    if (headers) {
      const sanitizedHeaders = this._sanitizeHeaders(headers);
      this.runtime.writeAttachment(
        JSON.stringify(sanitizedHeaders, null, 2),
        'Request Headers',
        'application/json'
      );
    }
    
    // Attach body
    if (body) {
      const bodyContent = typeof body === 'object' ? JSON.stringify(body, null, 2) : String(body);
      this.runtime.writeAttachment(
        bodyContent,
        'Request Body',
        typeof body === 'object' ? 'application/json' : 'text/plain'
      );
    }
  }
  
  /**
   * Add an API response to the current test.
   * 
   * @param {Object} response - Axios response object
   * @param {number} [elapsedTime] - Optional elapsed time in milliseconds
   */
  addApiResponse(response, elapsedTime) {
    if (!this.enabled || !this.currentExecutable) return;
    
    const stepName = `Response: ${response.status}`;
    this.addStep(stepName);
    
    // Attach status and elapsed time
    let statusInfo = `Status: ${response.status}\n`;
    if (elapsedTime !== undefined) {
      statusInfo += `Time: ${elapsedTime.toFixed(2)} ms`;
    } else if (response.config && response.config.metadata && response.config.metadata.responseTime) {
      statusInfo += `Time: ${response.config.metadata.responseTime.toFixed(2)} ms`;
    }
    
    this.runtime.writeAttachment(
      statusInfo,
      'Response Status',
      'text/plain'
    );
    
    // Attach headers
    const sanitizedHeaders = this._sanitizeHeaders(response.headers);
    this.runtime.writeAttachment(
      JSON.stringify(sanitizedHeaders, null, 2),
      'Response Headers',
      'application/json'
    );
    
    // Attach body
    const responseData = response.data;
    if (responseData) {
      const isJson = typeof responseData === 'object';
      this.runtime.writeAttachment(
        isJson ? JSON.stringify(responseData, null, 2) : String(responseData),
        'Response Body',
        isJson ? 'application/json' : 'text/plain'
      );
    }
  }
  
  /**
   * Add an attachment to the current test.
   * 
   * @param {string} name - Name of the attachment
   * @param {string|Buffer} content - Content of the attachment
   * @param {string} [mimeType='text/plain'] - MIME type of the attachment
   */
  addAttachment(name, content, mimeType = 'text/plain') {
    if (!this.enabled || !this.currentExecutable) return;
    
    this.runtime.writeAttachment(content, name, mimeType);
  }
  
  /**
   * Add a link to the current test.
   * 
   * @param {string} url - URL
   * @param {string} [name] - Optional name of the link
   * @param {string} [type='link'] - Type of the link (link, issue, tms)
   */
  addLink(url, name, type = 'link') {
    if (!this.enabled || !this.currentTest) return;
    
    const link = {
      name: name || url,
      url,
      type
    };
    
    this.currentTest.links.push(link);
  }
  
  /**
   * Set the description of the current test.
   * 
   * @param {string} description - Description of the test
   * @param {boolean} [isHtml=false] - Whether the description is HTML
   */
  setDescription(description, isHtml = false) {
    if (!this.enabled || !this.currentTest) return;
    
    if (isHtml) {
      this.currentTest.descriptionHtml = description;
    } else {
      this.currentTest.description = description;
    }
  }
  
  /**
   * Add a parameter to the current test.
   * 
   * @param {string} name - Name of the parameter
   * @param {*} value - Value of the parameter
   */
  addParameter(name, value) {
    if (!this.enabled || !this.currentTest) return;
    
    this.currentTest.parameters.push({
      name,
      value: String(value)
    });
  }
  
  /**
   * Add a label to the current test.
   * 
   * @param {string} name - Name of the label
   * @param {string} value - Value of the label
   */
  addLabel(name, value) {
    if (!this.enabled || !this.currentTest) return;
    
    this.currentTest.labels.push({
      name,
      value
    });
  }
  
  /**
   * Add a tag to the current test.
   * 
   * @param {string} tag - Tag to add
   */
  addTag(tag) {
    if (!this.enabled || !this.currentTest) return;
    
    this.addLabel('tag', tag);
  }
  
  /**
   * Add a suite name to the current test.
   * 
   * @param {string} suiteName - Name of the suite
   */
  addSuite(suiteName) {
    if (!this.enabled || !this.currentTest) return;
    
    this.addLabel('suite', suiteName);
  }
  
  /**
   * Add a severity level to the current test.
   * 
   * @param {string} severity - Severity level (trivial, minor, normal, critical, blocker)
   */
  addSeverity(severity) {
    if (!this.enabled || !this.currentTest) return;
    
    this.addLabel('severity', severity);
  }
  
  /**
   * Add an epic to the current test.
   * 
   * @param {string} epic - Epic name
   */
  addEpic(epic) {
    if (!this.enabled || !this.currentTest) return;
    
    this.addLabel('epic', epic);
  }
  
  /**
   * Add a feature to the current test.
   * 
   * @param {string} feature - Feature name
   */
  addFeature(feature) {
    if (!this.enabled || !this.currentTest) return;
    
    this.addLabel('feature', feature);
  }
  
  /**
   * Add a story to the current test.
   * 
   * @param {string} story - Story name
   */
  addStory(story) {
    if (!this.enabled || !this.currentTest) return;
    
    this.addLabel('story', story);
  }
  
  /**
   * Sanitize headers by masking sensitive information.
   * 
   * @param {Object} headers - Headers to sanitize
   * @returns {Object} Sanitized headers
   * @private
   */
  _sanitizeHeaders(headers) {
    const sanitized = {...headers};
    const sensitiveHeaders = ['authorization', 'x-api-key', 'cookie'];
    
    Object.keys(sanitized).forEach(header => {
      if (sensitiveHeaders.includes(header.toLowerCase())) {
        sanitized[header] = '*****';
      }
    });
    
    return sanitized;
  }
}

// Singleton instance for global use
const allureReporter = new AllureReporter();

module.exports = allureReporter;

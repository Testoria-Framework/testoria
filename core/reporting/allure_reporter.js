const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const { getReportingConfig } = require('../config/env_loader');

const SENSITIVE_HEADERS = ['authorization', 'proxy-authorization', 'x-api-key', 'cookie', 'set-cookie'];
const EXTENSIONS = { 'application/json': 'json', 'text/plain': 'txt', 'text/html': 'html', 'text/xml': 'xml' };

/**
 * Writes Allure 2 result files (`*-result.json` plus attachments) without depending on
 * a specific allure-js-commons version. Every method is a safe no-op when reporting is
 * disabled or no test is active, so tests never fail because of reporting.
 */
class AllureReporter {
  constructor() {
    let reportConfig = {};
    try {
      reportConfig = getReportingConfig().allure || {};
    } catch (error) {
      reportConfig = {};
    }
    this.enabled = reportConfig.enabled !== false && process.env.ALLURE_DISABLED !== 'true';
    const root = path.resolve(__dirname, '..', '..');
    this.reportDir = path.resolve(root, process.env.ALLURE_RESULTS_DIR || reportConfig.report_dir || 'reports/allure-results',
      process.env.ALLURE_SUBDIR || 'javascript');
    this.currentTest = null;
  }

  _ensureDir() {
    fs.mkdirSync(this.reportDir, { recursive: true });
  }

  _attach(name, content, mimeType = 'text/plain') {
    if (!this.enabled || !this.currentTest) return;
    try {
      this._ensureDir();
      const ext = EXTENSIONS[mimeType] || 'txt';
      const source = `${crypto.randomUUID()}-attachment.${ext}`;
      fs.writeFileSync(path.join(this.reportDir, source), content === undefined ? '' : content);
      const target = this.currentTest.steps.length ? this.currentTest.steps[this.currentTest.steps.length - 1] : this.currentTest;
      target.attachments.push({ name, source, type: mimeType });
    } catch (error) {
      console.warn(`Allure attachment failed: ${error.message}`);
    }
  }

  startTest(testName, description) {
    if (!this.enabled) return;
    if (this.currentTest) this.endTest('passed');
    this.currentTest = {
      uuid: crypto.randomUUID(),
      historyId: crypto.createHash('md5').update(testName).digest('hex'),
      name: testName,
      fullName: testName,
      description: description || '',
      status: 'passed',
      stage: 'running',
      start: Date.now(),
      steps: [],
      attachments: [],
      parameters: [],
      links: [],
      labels: [{ name: 'language', value: 'javascript' }, { name: 'framework', value: 'mocha' }]
    };
  }

  endTest(status = 'passed', error) {
    if (!this.enabled || !this.currentTest) return;
    const test = this.currentTest;
    test.status = status;
    test.stage = 'finished';
    test.stop = Date.now();
    if (error) {
      test.statusDetails = { message: error.message, trace: error.stack };
    }
    try {
      this._ensureDir();
      fs.writeFileSync(path.join(this.reportDir, `${test.uuid}-result.json`), JSON.stringify(test, null, 2));
    } catch (err) {
      console.warn(`Allure result write failed: ${err.message}`);
    }
    this.currentTest = null;
  }

  addStep(name, status = 'passed', details) {
    if (!this.enabled || !this.currentTest) return;
    const now = Date.now();
    this.currentTest.steps.push({ name, status, stage: 'finished', start: now, stop: now, steps: [], attachments: [], parameters: [] });
    if (details) this._attach('Details', String(details));
  }

  addApiRequest(method, url, headers, body) {
    if (!this.enabled || !this.currentTest) return;
    this.addStep(`Request: ${method} ${url}`);
    if (headers) this._attach('Request Headers', JSON.stringify(this._sanitizeHeaders(headers), null, 2), 'application/json');
    if (body !== undefined && body !== null) {
      const isObject = typeof body === 'object';
      this._attach('Request Body', isObject ? JSON.stringify(body, null, 2) : String(body), isObject ? 'application/json' : 'text/plain');
    }
  }

  addApiResponse(response, elapsedTime) {
    if (!this.enabled || !this.currentTest || !response) return;
    this.addStep(`Response: ${response.status}`);
    let statusInfo = `Status: ${response.status}\n`;
    const time = elapsedTime !== undefined ? elapsedTime : response.config && response.config.metadata && response.config.metadata.responseTime;
    if (time !== undefined) statusInfo += `Time: ${Number(time).toFixed(2)} ms`;
    this._attach('Response Status', statusInfo);
    if (response.headers) this._attach('Response Headers', JSON.stringify(this._sanitizeHeaders(response.headers), null, 2), 'application/json');
    if (response.data !== undefined && response.data !== '') {
      const isObject = typeof response.data === 'object';
      this._attach('Response Body', isObject ? JSON.stringify(response.data, null, 2) : String(response.data), isObject ? 'application/json' : 'text/plain');
    }
  }

  addAttachment(name, content, mimeType = 'text/plain') {
    this._attach(name, content, mimeType);
  }

  addLink(url, name, type = 'link') {
    if (!this.enabled || !this.currentTest) return;
    this.currentTest.links.push({ url, name: name || url, type });
  }

  setDescription(description, isHtml = false) {
    if (!this.enabled || !this.currentTest) return;
    if (isHtml) this.currentTest.descriptionHtml = description;
    else this.currentTest.description = description;
  }

  addParameter(name, value) {
    if (!this.enabled || !this.currentTest) return;
    this.currentTest.parameters.push({ name, value: typeof value === 'object' ? JSON.stringify(value) : String(value) });
  }

  addLabel(name, value) {
    if (!this.enabled || !this.currentTest) return;
    this.currentTest.labels.push({ name, value });
  }

  addTag(tag) { this.addLabel('tag', tag); }
  addSuite(suiteName) { this.addLabel('suite', suiteName); }
  addSeverity(severity) { this.addLabel('severity', severity); }
  addEpic(epic) { this.addLabel('epic', epic); }
  addFeature(feature) { this.addLabel('feature', feature); }
  addStory(story) { this.addLabel('story', story); }

  _sanitizeHeaders(headers) {
    const sanitized = { ...(headers || {}) };
    Object.keys(sanitized).forEach((header) => {
      if (SENSITIVE_HEADERS.includes(header.toLowerCase())) sanitized[header] = '*****';
    });
    return sanitized;
  }
}

module.exports = new AllureReporter();
module.exports.AllureReporter = AllureReporter;

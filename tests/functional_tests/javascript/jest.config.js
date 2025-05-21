module.exports = {
  testEnvironment: 'node',
  testMatch: ['**/*.js'],
  setupFilesAfterEnv: ['./setup.js'],
  reporters: ['default', 'jest-allure'],
  testTimeout: 30000,
  verbose: true
};
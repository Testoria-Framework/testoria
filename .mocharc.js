module.exports = {
  require: ['tests/support/demo_api_hook.js'],
  timeout: 60000,
  reporter: process.env.MOCHA_REPORTER || 'spec',
  exit: true
};

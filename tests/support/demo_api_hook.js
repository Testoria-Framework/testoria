/**
 * Mocha root hook: starts the bundled Testoria demo API (Python) on a free port
 * unless API_BASE_URL already points at a real deployment.
 */
const { spawn, spawnSync } = require('child_process');
const net = require('net');
const path = require('path');
const http = require('http');

const ROOT = path.resolve(__dirname, '..', '..');
let child = null;

function pickPython() {
  const candidates = [process.env.TESTORIA_PYTHON, path.join(ROOT, '.venv', 'bin', 'python'),
    path.join(ROOT, '.venv', 'Scripts', 'python.exe'), 'python3', 'python'].filter(Boolean);
  for (const c of candidates) {
    const r = spawnSync(c, ['-c', 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)'], { stdio: 'ignore' });
    if (r.status === 0) return c;
  }
  return null;
}

function freePort() {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.unref();
    srv.on('error', reject);
    srv.listen(0, '127.0.0.1', () => {
      const { port } = srv.address();
      srv.close(() => resolve(port));
    });
  });
}

function waitForHealth(url, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  return new Promise((resolve, reject) => {
    const attempt = () => {
      http.get(`${url}/health`, (res) => {
        res.resume();
        if (res.statusCode === 200) return resolve();
        retry();
      }).on('error', retry);
    };
    const retry = () => (Date.now() > deadline ? reject(new Error(`Demo API did not start at ${url}`)) : setTimeout(attempt, 200));
    attempt();
  });
}

exports.mochaHooks = {
  async beforeAll() {
    if (process.env.API_BASE_URL) return;
    this.timeout(120000);
    const python = pickPython();
    if (!python) throw new Error('Python 3.8+ is required to start the demo API (or set API_BASE_URL).');
    const port = await freePort();
    child = spawn(python, ['-m', 'testoria', 'demo-api', '--port', String(port)], {
      cwd: ROOT, stdio: ['ignore', 'ignore', 'inherit'], env: { ...process.env, PYTHONPATH: ROOT }
    });
    process.env.API_BASE_URL = `http://127.0.0.1:${port}`;
    await waitForHealth(process.env.API_BASE_URL, 110000);
  },
  afterAll() {
    if (child) {
      child.kill();
      child = null;
    }
  }
};

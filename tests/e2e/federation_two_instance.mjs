/**
 * ODYSSEY Phase 426-427: two ws_bridge processes + two Playwright pages.
 *
 * Page A consumes A as LIVE and renders B as adjacent-airspace ghosts.
 * Page B consumes B as LIVE and renders A as adjacent-airspace ghosts.
 */
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import { createServer } from 'node:http';
import net from 'node:net';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(SCRIPT_DIR, '..', '..');
const PYTHON = process.env.SDACS_PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
const PAGE_TIMEOUT_MS = process.platform === 'win32' ? 120_000 : 60_000;

const MIME = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.wasm': 'application/wasm',
};

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address();
      server.close(() => resolve(port));
    });
  });
}

function waitForPort(child, port, timeoutMs = 30_000) {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + timeoutMs;
    let settled = false;
    const finish = (error) => {
      if (settled) return;
      settled = true;
      clearInterval(timer);
      if (error) reject(error);
      else resolve();
    };
    child.once('exit', (code) => {
      finish(new Error(`ws_bridge port ${port} exited early (${code})\n${child.output}`));
    });
    const timer = setInterval(() => {
      if (Date.now() >= deadline) {
        finish(new Error(`ws_bridge port ${port} did not become ready\n${child.output}`));
        return;
      }
      const socket = net.createConnection({ host: '127.0.0.1', port });
      socket.once('connect', () => {
        socket.destroy();
        finish();
      });
      socket.once('error', () => socket.destroy());
    }, 100);
  });
}

async function startBridge(port, drones, seed) {
  const child = spawn(
    PYTHON,
    [
      path.join(ROOT, 'simulation', 'ws_bridge.py'),
      '--host', '127.0.0.1',
      '--port', String(port),
      '--drones', String(drones),
      '--seed', String(seed),
    ],
    {
      cwd: ROOT,
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    },
  );
  child.output = '';
  child.stdout.on('data', (chunk) => { child.output += chunk.toString('utf8'); });
  child.stderr.on('data', (chunk) => { child.output += chunk.toString('utf8'); });
  await waitForPort(child, port);
  return child;
}

async function startStaticServer() {
  const server = createServer(async (request, response) => {
    try {
      const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
      const relative = pathname === '/' ? 'swarm_3d_simulator.html' : pathname.slice(1);
      const target = path.resolve(ROOT, relative);
      if (target !== ROOT && !target.startsWith(`${ROOT}${path.sep}`)) {
        response.writeHead(403).end('Forbidden');
        return;
      }
      const info = await stat(target);
      if (!info.isFile()) throw new Error('Not a file');
      response.writeHead(200, {
        'Content-Type': MIME[path.extname(target)] || 'application/octet-stream',
        'Cache-Control': 'no-store',
      });
      createReadStream(target).pipe(response);
    } catch {
      response.writeHead(404).end('Not found');
    }
  });
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  return server;
}

function simulatorUrl(baseUrl, ownPort, peerPort, instance, peerInstance, peerOffsetX) {
  const query = new URLSearchParams({
    live: '1',
    ws: `ws://127.0.0.1:${ownPort}`,
    federationPeer: `ws://127.0.0.1:${peerPort}`,
    instance,
    peerInstance,
    peerOffsetX: String(peerOffsetX),
    peerOffsetZ: '0',
  });
  return `${baseUrl}/swarm_3d_simulator.html?${query}`;
}

async function stopChild(child) {
  if (!child || child.exitCode !== null) return;
  child.kill();
  await Promise.race([
    new Promise((resolve) => child.once('exit', resolve)),
    new Promise((resolve) => setTimeout(resolve, 5_000)),
  ]);
  if (child.exitCode === null) child.kill('SIGKILL');
}

async function main() {
  let bridgeA;
  let bridgeB;
  let server;
  let browser;
  try {
    const portA = await freePort();
    let portB = await freePort();
    while (portB === portA) portB = await freePort();
    bridgeA = await startBridge(portA, 4, 426);
    bridgeB = await startBridge(portB, 6, 427);
    server = await startStaticServer();
    const baseUrl = `http://127.0.0.1:${server.address().port}`;

    browser = await chromium.launch({
      headless: true,
      args: [
        '--use-angle=swiftshader',
        '--enable-unsafe-swiftshader',
        '--ignore-gpu-blocklist',
      ],
    });
    const context = await browser.newContext({ viewport: { width: 1400, height: 900 } });
    const pageA = await context.newPage();
    const pageB = await context.newPage();
    const errors = { A: [], B: [] };
    pageA.on('pageerror', (error) => errors.A.push(String(error)));
    pageB.on('pageerror', (error) => errors.B.push(String(error)));

    await Promise.all([
      pageA.goto(simulatorUrl(baseUrl, portA, portB, 'A', 'B', 10_000), {
        waitUntil: 'load',
        timeout: PAGE_TIMEOUT_MS,
      }),
      pageB.goto(simulatorUrl(baseUrl, portB, portA, 'B', 'A', -10_000), {
        waitUntil: 'load',
        timeout: PAGE_TIMEOUT_MS,
      }),
    ]);
    await Promise.all([
      pageA.waitForFunction(
        () => window._sdacs?.wsConnected
          && window._sdacs?.federationPeerConnected
          && window._sdacs?.federationGhostCount === 6,
        null,
        { timeout: PAGE_TIMEOUT_MS },
      ),
      pageB.waitForFunction(
        () => window._sdacs?.wsConnected
          && window._sdacs?.federationPeerConnected
          && window._sdacs?.federationGhostCount === 4,
        null,
        { timeout: PAGE_TIMEOUT_MS },
      ),
    ]);

    const infoA = await pageA.evaluate(() => window._sdacs.federationInfo);
    const infoB = await pageB.evaluate(() => window._sdacs.federationInfo);
    const ghostsA = await pageA.evaluate(() => window._sdacs.federationGhosts);
    const ghostsB = await pageB.evaluate(() => window._sdacs.federationGhosts);

    assert.equal(infoA.instance, 'A');
    assert.equal(infoA.peerInstance, 'B');
    assert.equal(infoA.connected, true);
    assert.equal(infoA.ghosts, 6);
    assert.deepEqual(infoA.offset, [10_000, 0]);
    assert.ok(infoA.frames > 0);
    assert.equal(infoB.instance, 'B');
    assert.equal(infoB.peerInstance, 'A');
    assert.equal(infoB.connected, true);
    assert.equal(infoB.ghosts, 4);
    assert.deepEqual(infoB.offset, [-10_000, 0]);
    assert.ok(infoB.frames > 0);
    assert.ok(ghostsA.every(
      (ghost) => ghost.renderedPosition[0] - ghost.peerPosition[0] === 10_000,
    ));
    assert.ok(ghostsB.every(
      (ghost) => ghost.renderedPosition[0] - ghost.peerPosition[0] === -10_000,
    ));
    assert.equal(
      await pageA.evaluate(() => window._sdacs.apiMaturity('federationGhosts')),
      'beta',
    );
    assert.deepEqual(errors, { A: [], B: [] });

    console.log(
      `PASS federation two-instance E2E: A<-B ${infoA.ghosts}, B<-A ${infoB.ghosts}`,
    );
    await context.close();
  } finally {
    if (browser) await browser.close();
    if (server) await new Promise((resolve) => server.close(resolve));
    await stopChild(bridgeA);
    await stopChild(bridgeB);
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

// SDACS Backend Bridge — Electron ↔ Python 자식 프로세스 관리
//
// 역할:
//   - Python Dash 백엔드(sdacs-backend.exe 또는 python desktop/backend_launcher.py) 를 자식으로 spawn
//   - 포트 폴링으로 준비 상태 감지 (최대 30초)
//   - Electron 종료 시 자식 프로세스 정리 (좀비 방지)
//   - 실패 시 이유 반환 → main.js 가 폴백(HTML-only 모드) 결정
//
// 실행 모드 분기:
//   - dev (app.isPackaged === false): python desktop/backend_launcher.py 로 직접 실행
//   - prod: process.resourcesPath/sdacs-backend/sdacs-backend.exe 실행

const { spawn } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');
const net = require('node:net');

const READY_SENTINEL = 'SDACS_BACKEND_READY';
const DEFAULT_PORT = 8050;
const BOOT_TIMEOUT_MS = 30_000;
const POLL_INTERVAL_MS = 400;

let backendChild = null;
let readyPromise = null;
let stdoutBuf = '';

/**
 * @typedef {Object} BackendConfig
 * @property {boolean} isPackaged
 * @property {string}  repoRoot
 * @property {number}  [port]
 * @property {number}  [drones]
 * @property {string}  [host]
 */

/**
 * 백엔드 실행 파일/명령 결정
 * @param {BackendConfig} cfg
 * @returns {{cmd: string, args: string[], cwd: string} | null}
 */
function _resolveBackendCommand(cfg) {
  const port = cfg.port ?? DEFAULT_PORT;
  const drones = cfg.drones ?? 30;
  const host = cfg.host ?? '127.0.0.1';
  const commonArgs = ['--port', String(port), '--drones', String(drones), '--host', host];

  if (cfg.isPackaged) {
    // 프로덕션: dist-python 이 extraResources 로 번들되어 resources/sdacs-backend/ 에 위치
    const exePath = path.join(process.resourcesPath, 'sdacs-backend', 'sdacs-backend.exe');
    if (!fs.existsSync(exePath)) return null;
    return { cmd: exePath, args: commonArgs, cwd: path.dirname(exePath) };
  }

  // 개발: 시스템 Python 으로 backend_launcher.py 실행
  const script = path.join(cfg.repoRoot, 'desktop', 'backend_launcher.py');
  if (!fs.existsSync(script)) return null;
  // Windows: py 런처 우선, 없으면 python
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
  return { cmd: pythonCmd, args: [script, ...commonArgs], cwd: cfg.repoRoot };
}

/**
 * 포트에 TCP 연결 시도 → 열려있으면 resolve(true)
 * @param {string} host
 * @param {number} port
 * @returns {Promise<boolean>}
 */
function _probePort(host, port) {
  return new Promise((resolve) => {
    const sock = net.createConnection({ host, port });
    let done = false;
    const finish = (ok) => { if (done) return; done = true; sock.destroy(); resolve(ok); };
    sock.once('connect', () => finish(true));
    sock.once('error', () => finish(false));
    sock.setTimeout(500, () => finish(false));
  });
}

/**
 * 백엔드 시작 + 준비 대기
 * @param {BackendConfig} cfg
 * @returns {Promise<{ok: boolean, port: number, reason?: string}>}
 */
async function startBackend(cfg) {
  if (readyPromise) return readyPromise;

  const port = cfg.port ?? DEFAULT_PORT;
  const host = cfg.host ?? '127.0.0.1';

  const resolved = _resolveBackendCommand(cfg);
  if (!resolved) {
    return { ok: false, port, reason: 'backend-executable-not-found' };
  }

  // 이미 다른 프로세스가 8050 을 잡고 있으면 그걸 재사용 (개발 편의)
  if (await _probePort(host, port)) {
    console.log('[backend] 기존 서버 감지 (재사용):', `${host}:${port}`);
    return { ok: true, port, reason: 'reused-existing-server' };
  }

  console.log('[backend] spawn:', resolved.cmd, resolved.args.join(' '));

  try {
    backendChild = spawn(resolved.cmd, resolved.args, {
      cwd: resolved.cwd,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    });
  } catch (e) {
    return { ok: false, port, reason: `spawn-failed: ${e.message}` };
  }

  backendChild.stdout.on('data', (chunk) => {
    const s = chunk.toString('utf8');
    stdoutBuf += s;
    // 콘솔에도 흘려 디버깅 편하게
    process.stdout.write(`[backend/stdout] ${s}`);
  });
  backendChild.stderr.on('data', (chunk) => {
    process.stderr.write(`[backend/stderr] ${chunk.toString('utf8')}`);
  });

  let exited = false;
  let exitCode = null;
  backendChild.on('exit', (code, signal) => {
    exited = true;
    exitCode = code;
    console.log(`[backend] exited code=${code} signal=${signal}`);
  });

  readyPromise = (async () => {
    const deadline = Date.now() + BOOT_TIMEOUT_MS;
    while (Date.now() < deadline) {
      if (exited) {
        return { ok: false, port, reason: `backend-exited-early code=${exitCode}` };
      }
      // READY sentinel 감지되었으면서 포트도 열려있는지 확인
      if (stdoutBuf.includes(READY_SENTINEL) && (await _probePort(host, port))) {
        return { ok: true, port };
      }
      await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
    }
    return { ok: false, port, reason: 'boot-timeout' };
  })();

  return readyPromise;
}

/**
 * 백엔드 정리 (before-quit 훅에서 호출)
 */
async function stopBackend() {
  if (!backendChild || backendChild.exitCode !== null) return;
  return new Promise((resolve) => {
    const child = backendChild;
    const done = () => resolve();
    child.once('exit', done);

    try {
      if (process.platform === 'win32') {
        // Windows: SIGTERM 이 안 먹힘. taskkill 로 트리 종료.
        spawn('taskkill', ['/pid', String(child.pid), '/f', '/t'], { windowsHide: true });
      } else {
        child.kill('SIGTERM');
      }
    } catch (e) {
      console.warn('[backend] stop 실패, 무시:', e.message);
      done();
      return;
    }

    // 5초 안에 안 죽으면 강제
    setTimeout(() => {
      try { if (child.exitCode === null) child.kill('SIGKILL'); } catch (_) {}
      done();
    }, 5000);
  });
}

function isBackendRunning() {
  return backendChild !== null && backendChild.exitCode === null;
}

module.exports = { startBackend, stopBackend, isBackendRunning, DEFAULT_PORT };

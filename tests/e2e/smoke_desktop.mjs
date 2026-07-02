// SDACS Desktop Smoke Test — backend_bridge + Dash 부팅 통합 검증
// 실행: node tests/e2e/smoke_desktop.mjs [--exe]
//   --exe: dist-python/sdacs-backend/sdacs-backend.exe 를 spawn (프로덕션 모드 시뮬레이션)
//   기본: python desktop/backend_launcher.py 를 spawn (개발 모드)
//
// 검증 성공 기준:
//   1. 30초 안에 SDACS_BACKEND_READY sentinel 이 stdout 에 나타남
//   2. Dash HTTP 서버가 127.0.0.1:<port>/ 에서 200 응답
//   3. stopBackend() 호출 시 자식 프로세스가 완전 종료됨

import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const bridge = require('../../desktop/backend_bridge.js');

const useExe = process.argv.includes('--exe');
const PORT = 8060;
const HOST = '127.0.0.1';

async function probe(url) {
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), 3000);
  try {
    const r = await fetch(url, { signal: controller.signal });
    return r.status;
  } catch {
    return null;
  } finally {
    clearTimeout(t);
  }
}

async function main() {
  console.log(`[smoke] mode=${useExe ? 'exe' : 'dev'} port=${PORT}`);
  const t0 = Date.now();

  const result = await bridge.startBackend({
    isPackaged: useExe,
    repoRoot: process.cwd(),
    port: PORT,
    host: HOST,
    drones: 10,
  });

  const bootMs = Date.now() - t0;
  console.log(`[smoke] startBackend → ${JSON.stringify(result)} (${bootMs} ms)`);

  if (!result.ok) {
    console.error(`[smoke] FAIL: backend did not become ready`);
    process.exit(1);
  }

  const status = await probe(`http://${HOST}:${PORT}/`);
  console.log(`[smoke] HTTP probe → ${status}`);

  await bridge.stopBackend();
  const running = bridge.isBackendRunning();
  console.log(`[smoke] stopBackend → running=${running}`);

  const ok = status === 200 && !running;
  console.log(`[smoke] ${ok ? 'PASS' : 'FAIL'} — total ${Date.now() - t0} ms`);
  process.exit(ok ? 0 : 1);
}

main().catch((e) => {
  console.error('[smoke] error:', e);
  process.exit(2);
});

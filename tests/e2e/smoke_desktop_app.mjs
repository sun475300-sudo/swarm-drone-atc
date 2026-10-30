// SDACS Electron GUI smoke test.
// Usage:
//   node tests/e2e/smoke_desktop_app.mjs
//   node tests/e2e/smoke_desktop_app.mjs --packaged
//   node tests/e2e/smoke_desktop_app.mjs --portable
//   node tests/e2e/smoke_desktop_app.mjs --exe=C:\path\to\SDACS Simulator.exe

import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { execFileSync, spawn, spawnSync } from 'node:child_process';
import { setTimeout as delay } from 'node:timers/promises';
import { _electron as electron } from 'playwright';

const portable = process.argv.includes('--portable');
const executableArg = process.argv.find((arg) => arg.startsWith('--exe='));
const customExecutable = executableArg ? executableArg.slice('--exe='.length) : null;
const packaged = process.argv.includes('--packaged') || portable || Boolean(customExecutable);
const repoRoot = process.cwd();
const packageVersion = JSON.parse(fs.readFileSync(path.join(repoRoot, 'package.json'), 'utf8')).version;
const packagedExe = customExecutable
  ? path.resolve(customExecutable)
  : portable
    ? path.join(repoRoot, 'dist-desktop', `SDACS-Simulator-${packageVersion}-portable.exe`)
    : path.join(
        repoRoot,
        'dist-desktop',
        'win-unpacked',
        process.platform === 'win32' ? 'SDACS Simulator.exe' : 'sdacs-simulator',
      );
const outputDir = path.join(repoRoot, 'output', 'playwright');
const gpuArgs = [
  '--use-angle=swiftshader',
  '--enable-unsafe-swiftshader',
  '--ignore-gpu-blocklist',
];

function assert(condition, message) {
  if (!condition) throw new Error(message);
  console.log(`PASS  ${message}`);
}

if (packaged && !fs.existsSync(packagedExe)) {
  throw new Error(`Packaged executable not found: ${packagedExe}`);
}

fs.mkdirSync(outputDir, { recursive: true });

async function smokePortableWrapper() {
  if (process.platform !== 'win32') {
    throw new Error('Portable EXE smoke is only supported on Windows.');
  }

  const countAppProcesses = () => {
    const output = execFileSync('tasklist.exe', [
      '/FI',
      'IMAGENAME eq SDACS Simulator.exe',
      '/FO',
      'CSV',
      '/NH',
    ], { encoding: 'utf8' });
    return output
      .split(/\r?\n/)
      .filter((line) => line.toLowerCase().startsWith('"sdacs simulator.exe"'))
      .length;
  };

  if (countAppProcesses() > 0) {
    throw new Error('Close existing SDACS Simulator processes before portable smoke testing.');
  }

  // electron-builder의 portable 타깃은 압축 해제 래퍼이므로 Playwright가
  // 래퍼 자체에 연결할 수 없다. 실제 Electron 자식 프로세스 생성 여부를
  // 확인하고, UI/WebGL 검증은 설치형 또는 win-unpacked 경로에서 수행한다.
  const wrapper = spawn(packagedExe, gpuArgs, { cwd: repoRoot, stdio: 'ignore' });
  let spawnError = null;
  wrapper.once('error', (error) => { spawnError = error; });

  try {
    let childCount = 0;
    for (let attempt = 0; attempt < 30; attempt += 1) {
      await delay(1_000);
      if (spawnError) throw spawnError;
      if (wrapper.exitCode !== null) {
        throw new Error(`Portable wrapper exited early with code ${wrapper.exitCode}`);
      }

      childCount = countAppProcesses();
      if (childCount > 0) break;
    }

    assert(childCount > 0, 'Portable wrapper launches the SDACS Electron process');
    console.log('PASS  SDACS desktop portable process smoke test');
  } finally {
    if (wrapper.pid) {
      spawnSync('taskkill.exe', ['/PID', String(wrapper.pid), '/T', '/F'], { stdio: 'ignore' });
    }
  }
}

if (portable) {
  await smokePortableWrapper();
  process.exit(0);
}

const launchOptions = packaged
  ? { executablePath: packagedExe, args: gpuArgs, cwd: repoRoot }
  : { args: ['.', ...gpuArgs], cwd: repoRoot };

const app = await electron.launch(launchOptions);

try {
  const page = await app.firstWindow();
  const pageErrors = [];
  const consoleErrors = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });

  await page.waitForFunction(() => Boolean(window._sdacs), null, { timeout: 60_000 });
  await page.waitForTimeout(1_500);

  const state = await page.evaluate(() => ({
    electron: Boolean(window.sdacs && window.sdacs.isElectron),
    url: location.href,
    guardVisible: document.body.innerText.includes('로컬 서버가 필요합니다'),
    canvasCount: document.querySelectorAll('canvas').length,
    droneCount: window._sdacs.droneCount,
    drawCalls: window._sdacs.renderer.info.render.calls,
    screenshotLength: window._sdacs.captureScreenshot().length,
    simTime: window._sdacs.simTime,
  }));

  assert(state.electron, 'Electron preload API available');
  assert(state.url.endsWith('/swarm_3d_simulator.html'), 'Canonical simulator is the first app screen');
  assert(!state.guardVisible, 'Browser-only file protocol guard is hidden in Electron');
  assert(state.canvasCount >= 1, `Simulator canvases rendered (${state.canvasCount})`);
  assert(state.droneCount > 0, `Scenario initialized (${state.droneCount} drones)`);
  assert(state.drawCalls > 0, `WebGL draw calls active (${state.drawCalls})`);
  assert(state.screenshotLength > 5_000, `WebGL capture is nonblank (${state.screenshotLength} bytes)`);

  await page.evaluate(() => window._sdacs.startSim());
  await page.waitForTimeout(1_200);
  const advancedTime = await page.evaluate(() => window._sdacs.simTime);
  assert(advancedTime > state.simTime, `Simulation clock advances (${state.simTime.toFixed(2)} -> ${advancedTime.toFixed(2)})`);
  assert(pageErrors.length === 0, `No page errors (${pageErrors.length})`);

  // Packaged paths use app.asar. Exercise both menu callbacks so a broken
  // process.resourcesPath/app assumption cannot regress unnoticed.
  await app.evaluate(({ Menu }, label) => {
    const root = Menu.getApplicationMenu();
    const find = (items) => {
      for (const item of items) {
        if (item.label === label) return item;
        const nested = item.submenu ? find(item.submenu.items) : null;
        if (nested) return nested;
      }
      return null;
    };
    const item = root ? find(root.items) : null;
    if (!item) throw new Error(`Menu item not found: ${label}`);
    item.click();
  }, '해양 소형선 감지');
  await page.waitForURL(/maritime_detection_simulator\.html$/, { timeout: 15_000 });
  await page.waitForFunction(() => document.querySelectorAll('canvas').length > 0);
  assert(await page.evaluate(() => Boolean(window.sdacs?.isElectron)), 'Maritime simulator menu navigation works');

  await app.evaluate(({ Menu }, label) => {
    const root = Menu.getApplicationMenu();
    const find = (items) => {
      for (const item of items) {
        if (item.label === label) return item;
        const nested = item.submenu ? find(item.submenu.items) : null;
        if (nested) return nested;
      }
      return null;
    };
    const item = root ? find(root.items) : null;
    if (!item) throw new Error(`Menu item not found: ${label}`);
    item.click();
  }, '군집 드론 시뮬레이터');
  await page.waitForURL(/swarm_3d_simulator\.html$/, { timeout: 15_000 });
  await page.waitForFunction(() => Boolean(window._sdacs));
  assert(true, 'Canonical simulator menu navigation works');

  await page.screenshot({
    path: path.join(
      outputDir,
      customExecutable
        ? 'desktop-installed-smoke.png'
        : packaged
            ? 'desktop-packaged-smoke.png'
            : 'desktop-dev-smoke.png',
    ),
    fullPage: true,
  });

  if (consoleErrors.length) {
    console.log(`WARN  Console errors: ${consoleErrors.slice(0, 5).join(' | ')}`);
  }
  console.log(`PASS  SDACS desktop ${packaged ? 'packaged' : 'development'} smoke test`);
} finally {
  await app.close();
}

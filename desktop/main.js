// SDACS Simulator — Electron 메인 프로세스 (HYPER Phase 12)
// 멀티 윈도우 지원 + IPC 시간축 동기
// - 단일 모드: 홈 → 시뮬레이터 카드 선택
// - 분할 모드: 군집 + 해양 동시 표시, IPC 브로드캐스트로 sim time 동기
const { app, BrowserWindow, Menu, shell, ipcMain, screen } = require('electron');
const path = require('node:path');

const isDev = !app.isPackaged;
const repoRoot = isDev ? path.join(__dirname, '..') : path.join(process.resourcesPath, 'app');

let mainWin = null;
let secondaryWin = null;     // HYPER Phase 12: 분할 모드용
const allWins = new Set();   // IPC 브로드캐스트 대상

function _wpOpts(extra) {
  return Object.assign({
    preload: path.join(__dirname, 'preload.js'),
    contextIsolation: true,
    nodeIntegration: false,
    sandbox: true,
  }, extra || {});
}

function _baseFile(rel) {
  if (rel === 'home.html') return path.join(__dirname, 'home.html');
  return path.join(repoRoot, rel);
}

function createWindow(opts) {
  opts = opts || {};
  const win = new BrowserWindow({
    width: opts.width || 1500,
    height: opts.height || 900,
    x: opts.x,
    y: opts.y,
    minWidth: 1024,
    minHeight: 700,
    backgroundColor: '#02060d',
    title: opts.title || 'SDACS Simulator',
    webPreferences: _wpOpts(),
  });
  win.loadFile(opts.file || path.join(__dirname, 'home.html'));
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http')) { shell.openExternal(url); return { action: 'deny' }; }
    return { action: 'allow' };
  });
  allWins.add(win);
  win.on('closed', () => {
    allWins.delete(win);
    if (win === mainWin) mainWin = null;
    if (win === secondaryWin) secondaryWin = null;
  });
  if (isDev) win.webContents.openDevTools({ mode: 'detach' });
  return win;
}

function loadPage(rel) {
  if (!mainWin) return;
  if (rel === 'home.html') {
    mainWin.loadFile(_baseFile('home.html'));
  } else {
    mainWin.loadFile(_baseFile(rel));
  }
}

// HYPER Phase 12 — 분할 모드 시작/중지
function openSplitMode() {
  if (!mainWin) return;
  // 메인 → 군집, 보조 → 해양
  const display = screen.getPrimaryDisplay();
  const { width: dw, height: dh } = display.workAreaSize;
  const halfW = Math.floor(dw / 2);
  // 메인 → 좌측 절반
  mainWin.setBounds({ x: 0, y: 0, width: halfW, height: dh });
  mainWin.loadFile(_baseFile('swarm_3d_simulator.html'));
  // 보조 윈도우 (해양) → 우측 절반
  if (secondaryWin && !secondaryWin.isDestroyed()) {
    secondaryWin.focus();
    return;
  }
  secondaryWin = createWindow({
    width: halfW,
    height: dh,
    x: halfW,
    y: 0,
    title: 'SDACS — Maritime',
    file: _baseFile('maritime_detection_simulator.html'),
  });
  // 분할 모드 IPC 알림 (양쪽 윈도우에 broadcast)
  _broadcastIPC('split-mode', { enabled: true });
}

function closeSplitMode() {
  if (secondaryWin && !secondaryWin.isDestroyed()) {
    secondaryWin.close();
    secondaryWin = null;
  }
  if (mainWin) {
    mainWin.setSize(1500, 900);
    mainWin.center();
  }
  _broadcastIPC('split-mode', { enabled: false });
}

// HYPER Phase 12 — IPC 시간축 동기 브로드캐스트
function _broadcastIPC(channel, payload) {
  for (const w of allWins) {
    if (w && !w.isDestroyed()) {
      try { w.webContents.send(channel, payload); } catch (e) { /* ignore */ }
    }
  }
}

// 시간축 동기: 한 윈도우가 'sim-time-tick' 보내면 나머지에 broadcast
ipcMain.on('sim-time-tick', (event, payload) => {
  for (const w of allWins) {
    if (w && !w.isDestroyed() && w.webContents !== event.sender) {
      try { w.webContents.send('sim-time-sync', payload); } catch (e) {}
    }
  }
});

// ATC 명령 브로드캐스트 (한쪽에서 발행 → 양쪽 동기)
ipcMain.on('atc-broadcast', (event, payload) => {
  for (const w of allWins) {
    if (w && !w.isDestroyed() && w.webContents !== event.sender) {
      try { w.webContents.send('atc-broadcast-recv', payload); } catch (e) {}
    }
  }
});

// 윈도우 개수 query
ipcMain.handle('windows-count', () => allWins.size);

function buildMenu() {
  return Menu.buildFromTemplate([
    {
      label: 'SDACS',
      submenu: [
        { label: '홈 / Home', accelerator: 'CmdOrCtrl+H', click: () => loadPage('home.html') },
        { label: '군집 드론 시뮬레이터', accelerator: 'CmdOrCtrl+1', click: () => loadPage('swarm_3d_simulator.html') },
        { label: '해양 소형선 감지', accelerator: 'CmdOrCtrl+2', click: () => loadPage('maritime_detection_simulator.html') },
        { type: 'separator' },
        { label: '🪟 분할 모드 (군집+해양 동시)', accelerator: 'CmdOrCtrl+Shift+S', click: openSplitMode },
        { label: '🪟 단일 모드 복귀', accelerator: 'CmdOrCtrl+Shift+W', click: closeSplitMode },
        { type: 'separator' },
        { role: 'quit', label: '종료 / Quit' },
      ],
    },
    {
      label: '보기 / View',
      submenu: [
        { role: 'reload', label: '새로 고침' },
        { role: 'forceReload', label: '강제 새로 고침' },
        { role: 'toggleDevTools', label: '개발자 도구' },
        { type: 'separator' },
        { role: 'resetZoom', label: '줌 초기화' },
        { role: 'zoomIn', label: '확대' },
        { role: 'zoomOut', label: '축소' },
        { role: 'togglefullscreen', label: '전체 화면' },
      ],
    },
    {
      label: '도움말 / Help',
      submenu: [
        { label: 'GitHub 저장소', click: () => shell.openExternal('https://github.com/sun475300-sudo/swarm-drone-atc') },
        { label: '랜딩 페이지(Live)', click: () => shell.openExternal('https://sun475300-sudo.github.io/swarm-drone-atc/') },
        { type: 'separator' },
        { label: '버전 정보', click: () => shell.openExternal('https://github.com/sun475300-sudo/swarm-drone-atc/releases') },
      ],
    },
  ]);
}

function createMainWindow() {
  mainWin = createWindow({ title: 'SDACS Simulator' });
  Menu.setApplicationMenu(buildMenu());
}

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on('second-instance', () => { if (mainWin) { if (mainWin.isMinimized()) mainWin.restore(); mainWin.focus(); } });
  app.whenReady().then(createMainWindow);
  app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createMainWindow(); });
}

// 노출용 (테스트 및 외부 디버깅)
module.exports = { createWindow, openSplitMode, closeSplitMode };

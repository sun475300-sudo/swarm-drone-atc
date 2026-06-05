// SDACS Simulator — Electron 메인 프로세스
// 홈 화면 + 멀티 윈도우(군집·해양 동시 표시) + 윈도우 타일 정렬(다중 모니터 자동 분산)
// + 윈도우 간 시뮬 시간 동기(IPC 브로드캐스트).
const { app, BrowserWindow, Menu, shell, ipcMain, screen } = require('electron');
const path = require('node:path');
const { computeTileBounds } = require('./layout');

const isDev = !app.isPackaged;
const wins = new Set(); // 열린 모든 윈도우
let mainWin = null;     // 홈/메인 윈도우

// 시뮬레이터 HTML 경로 해석 (개발 시 repo 루트, 패키징 시 resources/app)
function resolvePage(rel) {
  if (rel === 'home.html') return path.join(__dirname, 'home.html');
  const base = isDev ? path.join(__dirname, '..') : path.join(process.resourcesPath, 'app');
  return path.join(base, rel);
}

function newWindow(rel, opts = {}) {
  const win = new BrowserWindow({
    width: opts.width ?? 1500,
    height: opts.height ?? 900,
    x: opts.x,
    y: opts.y,
    minWidth: 1024,
    minHeight: 700,
    backgroundColor: '#02060d',
    title: 'SDACS Simulator',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  win.loadFile(resolvePage(rel));
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http')) { shell.openExternal(url); return { action: 'deny' }; }
    return { action: 'allow' };
  });
  win.on('closed', () => { wins.delete(win); if (win === mainWin) mainWin = null; });

  wins.add(win);
  return win;
}

// 홈 윈도우에서 페이지 전환 (없으면 새로 생성)
function loadPage(rel) {
  if (!mainWin || mainWin.isDestroyed()) { mainWin = newWindow(rel); return; }
  mainWin.loadFile(resolvePage(rel));
  mainWin.focus();
}

// 열린 모든 윈도우를 타일 정렬 — 다중 모니터면 모니터별, 단일이면 작업영역 분할
function tileWindows(mode) {
  const list = [...wins].filter((w) => !w.isDestroyed());
  if (list.length === 0) return;
  const displays = screen.getAllDisplays().map((d) => ({ workArea: d.workArea }));
  const bounds = computeTileBounds(displays, list.length, mode);
  list.forEach((w, i) => w.setBounds(bounds[i]));
}

// 윈도우 간 시뮬 시간 동기 + 새 창 열기 IPC
function registerIpc() {
  ipcMain.on('sdacs:sim-time', (event, simTime) => {
    if (typeof simTime !== 'number' || !Number.isFinite(simTime)) return;
    for (const w of wins) {
      if (!w.isDestroyed() && w.webContents.id !== event.sender.id) {
        w.webContents.send('sdacs:sim-time', simTime);
      }
    }
  });
  ipcMain.on('sdacs:open-window', (_event, rel) => {
    if (rel === 'swarm_3d_simulator.html' || rel === 'maritime_detection_simulator.html') {
      newWindow(rel).focus();
    }
  });
}

function buildMenu() {
  const menu = Menu.buildFromTemplate([
    {
      label: 'SDACS',
      submenu: [
        { label: '홈 / Home', accelerator: 'CmdOrCtrl+H', click: () => loadPage('home.html') },
        { label: '군집 드론 시뮬레이터', accelerator: 'CmdOrCtrl+1', click: () => loadPage('swarm_3d_simulator.html') },
        { label: '해양 소형선 감지', accelerator: 'CmdOrCtrl+2', click: () => loadPage('maritime_detection_simulator.html') },
        { type: 'separator' },
        { role: 'quit', label: '종료 / Quit' },
      ],
    },
    {
      label: '창 / Window',
      submenu: [
        { label: '새 창: 군집 드론 / New Swarm Window', accelerator: 'CmdOrCtrl+Shift+1', click: () => newWindow('swarm_3d_simulator.html').focus() },
        { label: '새 창: 해양 감지 / New Maritime Window', accelerator: 'CmdOrCtrl+Shift+2', click: () => newWindow('maritime_detection_simulator.html').focus() },
        { type: 'separator' },
        { label: '가로 정렬 / Tile Horizontally', click: () => tileWindows('horizontal') },
        { label: '세로 정렬 / Tile Vertically', click: () => tileWindows('vertical') },
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
  Menu.setApplicationMenu(menu);
}

function createWindow() {
  mainWin = newWindow('home.html');
  buildMenu();
  if (isDev) mainWin.webContents.openDevTools({ mode: 'detach' });
}

// 단일 인스턴스
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on('second-instance', () => { if (mainWin) { if (mainWin.isMinimized()) mainWin.restore(); mainWin.focus(); } });
  app.whenReady().then(() => { registerIpc(); createWindow(); });
  app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
}

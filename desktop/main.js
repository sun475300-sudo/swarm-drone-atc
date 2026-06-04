// SDACS Simulator — Electron 메인 프로세스
// 단일 BrowserWindow에 홈 화면을 띄우고, 사용자가 카드 클릭으로 시뮬레이터 전환.
const { app, BrowserWindow, Menu, shell } = require('electron');
const path = require('node:path');

const isDev = !app.isPackaged;
let mainWin = null;

function createWindow() {
  mainWin = new BrowserWindow({
    width: 1500,
    height: 900,
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

  mainWin.loadFile(path.join(__dirname, 'home.html'));
  mainWin.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http')) { shell.openExternal(url); return { action: 'deny' }; }
    return { action: 'allow' };
  });

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

  if (isDev) mainWin.webContents.openDevTools({ mode: 'detach' });
}

function loadPage(rel) {
  if (!mainWin) return;
  const repoRoot = isDev ? path.join(__dirname, '..') : path.join(process.resourcesPath, 'app');
  // 패키징 시: app/ 디렉터리 아래 home.html과 시뮬레이터 HTML이 모두 위치
  const base = isDev ? repoRoot : path.join(process.resourcesPath, 'app');
  if (rel === 'home.html') {
    mainWin.loadFile(path.join(__dirname, 'home.html'));
  } else {
    mainWin.loadFile(path.join(base, rel));
  }
}

// 단일 인스턴스
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on('second-instance', () => { if (mainWin) { if (mainWin.isMinimized()) mainWin.restore(); mainWin.focus(); } });
  app.whenReady().then(createWindow);
  app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
}

// SDACS Auto Updater — electron-updater 얇은 래퍼
//
// 정책:
//   - package.json > build > publish (github, draft) 를 그대로 사용
//   - 앱 시작 5초 후 조용히 확인 (부팅 UX 방해 안 함)
//   - 업데이트 감지 시 사용자에게 다이얼로그 표시, 취소 가능
//   - 다운로드 완료 시 재시작 여부 재확인
//   - 실패는 로그만 남기고 앱 진행에 지장 없음
//
// 미서명 정책:
//   - Windows SmartScreen 우회 없음 — 사용자가 매 업데이트마다 승인해야 함
//   - electron-updater 는 NSIS 설치 관리자 서명 여부에 관계없이 동작하나
//     서명 없는 업데이트는 Windows 가 신뢰 경고를 표시

const { app, dialog } = require('electron');

let autoUpdater = null;
let mainWinRef = null;

function _loadUpdater() {
  if (autoUpdater) return autoUpdater;
  try {
    ({ autoUpdater } = require('electron-updater'));
    autoUpdater.autoDownload = false;           // 사용자 확인 후 다운로드
    autoUpdater.autoInstallOnAppQuit = true;    // 종료 시 자동 설치
    autoUpdater.logger = {
      info: (m) => console.log('[updater]', m),
      warn: (m) => console.warn('[updater]', m),
      error: (m) => console.error('[updater]', m),
      debug: () => {},
    };
    return autoUpdater;
  } catch (e) {
    console.warn('[updater] electron-updater 로드 실패:', e.message);
    return null;
  }
}

function _bindEvents(u) {
  u.on('checking-for-update', () => console.log('[updater] checking...'));
  u.on('update-not-available', () => console.log('[updater] up-to-date'));
  u.on('error', (err) => console.warn('[updater] error:', err && err.message));

  u.on('update-available', async (info) => {
    console.log('[updater] available:', info && info.version);
    const win = mainWinRef;
    if (!win || win.isDestroyed()) return;
    const { response } = await dialog.showMessageBox(win, {
      type: 'info',
      buttons: ['다운로드', '나중에'],
      defaultId: 0,
      cancelId: 1,
      title: 'SDACS 업데이트 사용 가능',
      message: `새 버전 ${info && info.version} 이(가) 나왔습니다.`,
      detail: '지금 다운로드하시겠습니까? 다운로드 후 재시작 시 설치됩니다.',
    });
    if (response === 0) {
      u.downloadUpdate().catch((e) => console.warn('[updater] download 실패:', e.message));
    }
  });

  u.on('download-progress', (p) => {
    console.log(`[updater] download ${Math.round(p.percent || 0)}%`);
  });

  u.on('update-downloaded', async (info) => {
    console.log('[updater] downloaded:', info && info.version);
    const win = mainWinRef;
    if (!win || win.isDestroyed()) return;
    const { response } = await dialog.showMessageBox(win, {
      type: 'question',
      buttons: ['지금 재시작', '나중에'],
      defaultId: 0,
      cancelId: 1,
      title: '업데이트 다운로드 완료',
      message: `SDACS ${info && info.version} 준비 완료.`,
      detail: '지금 재시작하여 새 버전을 설치하시겠습니까?',
    });
    if (response === 0) u.quitAndInstall(false, true);
  });
}

/**
 * 자동 업데이트 시작 (dev 모드에서는 no-op)
 * @param {Electron.BrowserWindow} mainWin
 */
function initAutoUpdater(mainWin) {
  if (!app.isPackaged) {
    console.log('[updater] dev 모드 — 자동 업데이트 비활성');
    return;
  }
  const u = _loadUpdater();
  if (!u) return;
  mainWinRef = mainWin;
  _bindEvents(u);

  // 앱 부팅 후 5초 뒤 조용히 첫 체크
  setTimeout(() => {
    u.checkForUpdates().catch((e) => console.warn('[updater] check 실패:', e.message));
  }, 5000);
}

/**
 * 수동 업데이트 확인 (메뉴에서 호출)
 * @param {Electron.BrowserWindow} mainWin
 */
async function checkForUpdatesManually(mainWin) {
  mainWinRef = mainWin;
  if (!app.isPackaged) {
    if (mainWin && !mainWin.isDestroyed()) {
      dialog.showMessageBox(mainWin, {
        type: 'info',
        message: '개발 모드',
        detail: '자동 업데이트는 설치 버전에서만 동작합니다.',
      });
    }
    return;
  }
  const u = _loadUpdater();
  if (!u) return;
  _bindEvents(u);
  try {
    const result = await u.checkForUpdates();
    if (result && result.updateInfo && result.updateInfo.version === app.getVersion()) {
      if (mainWin && !mainWin.isDestroyed()) {
        dialog.showMessageBox(mainWin, {
          type: 'info',
          message: '최신 버전 사용 중',
          detail: `현재 버전 ${app.getVersion()} 이 최신입니다.`,
        });
      }
    }
  } catch (e) {
    if (mainWin && !mainWin.isDestroyed()) {
      dialog.showMessageBox(mainWin, {
        type: 'warning',
        message: '업데이트 확인 실패',
        detail: e && e.message,
      });
    }
  }
}

module.exports = { initAutoUpdater, checkForUpdatesManually };

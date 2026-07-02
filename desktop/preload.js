// SDACS preload — HYPER Phase 12 IPC 시간축 동기 + 분할 모드
const { contextBridge, ipcRenderer } = require('electron');

// 보안: contextIsolation + sandbox 활성화 상태에서 노출 가능한 안전한 API만
contextBridge.exposeInMainWorld('sdacs', {
  version: '1.1.0',
  isElectron: true,

  // Phase 12 — 시간축 동기 (분할 모드 양쪽 윈도우)
  sendTimeTick: (simTime, simSpeed) => ipcRenderer.send('sim-time-tick', { simTime, simSpeed, ts: Date.now() }),
  onTimeSync: (cb) => ipcRenderer.on('sim-time-sync', (_e, p) => cb(p)),

  // Phase 12 — ATC 명령 브로드캐스트
  sendAtcBroadcast: (cmd, target, params) =>
    ipcRenderer.send('atc-broadcast', { cmd, target, params, ts: Date.now() }),
  onAtcBroadcast: (cb) => ipcRenderer.on('atc-broadcast-recv', (_e, p) => cb(p)),

  // Phase 12 — 분할 모드 상태 알림
  onSplitMode: (cb) => ipcRenderer.on('split-mode', (_e, p) => cb(p)),

  // 윈도우 수 query
  windowsCount: () => ipcRenderer.invoke('windows-count'),

  // 백엔드 부팅 상태 (splash.html 이 구독)
  onBackendStatus: (cb) => ipcRenderer.on('backend-status', (_e, p) => cb(p)),

  // 백엔드 정보 조회 (홈에서 Dash URL 링크 표시용)
  backendInfo: () => ipcRenderer.invoke('backend-info'),
});

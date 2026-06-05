// 보안 격리된 preload — 윈도우 간 시뮬 시간 동기 + 새 창 열기 IPC를 렌더러에 노출.
// 시뮬레이터(순수 클라이언트 JS)는 window.sdacs.emitSimTime/onSimTime 로 다중 윈도우 동기화 가능.
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('sdacs', {
  version: '1.1.0',
  isElectron: true,
  // 현재 윈도우의 시뮬 시간(초)을 다른 윈도우로 브로드캐스트
  emitSimTime: (simTime) => ipcRenderer.send('sdacs:sim-time', simTime),
  // 다른 윈도우의 시뮬 시간 수신. cb(simTime) 호출. 해제 함수 반환.
  onSimTime: (cb) => {
    const handler = (_event, simTime) => cb(simTime);
    ipcRenderer.on('sdacs:sim-time', handler);
    return () => ipcRenderer.removeListener('sdacs:sim-time', handler);
  },
  // 시뮬레이터를 새 창에서 열기 (swarm_3d_simulator.html | maritime_detection_simulator.html)
  openWindow: (rel) => ipcRenderer.send('sdacs:open-window', rel),
});

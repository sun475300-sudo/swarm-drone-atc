// 보안 격리된 preload — 현재는 노출할 IPC 없음(시뮬레이터는 순수 클라이언트 JS).
// 추후 파일 저장/로드(IPC) 등이 필요할 때 확장한다.
const { contextBridge } = require('electron');
contextBridge.exposeInMainWorld('sdacs', { version: '1.0.0', isElectron: true });

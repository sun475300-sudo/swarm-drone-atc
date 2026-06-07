# ⚡ SDACS Quick Start — 1줄 실행

*MEGA + HYPER + STELLAR + ULTIMATE + POST-UNIVERSE = 200 Phase 통합 (v1.5.0)*

## 🚀 즉시 실행 (3 가지 방법)

### A) 웹 (가장 빠름, 설치 불필요)

브라우저로 바로 접속:
```
https://sun475300-sudo.github.io/swarm-drone-atc/swarm_3d_simulator.html
```

### B) 로컬 단독 HTML (오프라인 가능)

1. [`swarm_3d_simulator.html`](../swarm_3d_simulator.html) 다운로드
2. 더블 클릭 → 기본 브라우저에서 즉시 실행
3. 인터넷 연결 시 Three.js CDN 자동 로드

### C) 데스크탑 앱 (Win/Mac/Linux)

[GitHub Releases v1.5.0](https://github.com/sun475300-sudo/swarm-drone-atc/releases/tag/v1.5.0) 에서 OS별 파일 다운로드:
- Windows: `SDACS-Simulator-1.5.0-Setup.exe`
- macOS: `SDACS-Simulator-1.5.0-x64.dmg` 또는 `*-arm64.dmg`
- Linux: `SDACS-Simulator-1.5.0-x86_64.AppImage`

## 🎬 200 Phase 자동 데모 (60초)

브라우저로 시뮬레이터 연 뒤 콘솔(F12) 열고 한 줄:
```javascript
fetch('https://raw.githubusercontent.com/sun475300-sudo/swarm-drone-atc/main/docs/demo/all_phases_showcase.js').then(r=>r.text()).then(eval);
```

→ ATC 명령부터 Phase 200 Unity 도달까지 자동 시연 + 30초 화면 녹화.

## 🎮 핵심 5 명령 (초보자)

콘솔에 차례로 입력:
```javascript
// 1. 시뮬레이션 시작
window._sdacs.startSim();

// 2. 첫 드론 선택 + 정지 명령
const id = window._sdacs.selectDrone(0);
window._sdacs.atcCommand(id, 'HOLD');

// 3. 시네마틱 모드 (태양 + 비)
window._sdacs.setSunCycle(true);
window._sdacs.setRain(true, 0.5);

// 4. AI Copilot (한국어 자연어)
const plan = window._sdacs.copilotPlan('모든 드론 귀환');
window._sdacs.copilotExecute(plan);

// 5. 적대 드론 + 방어 동시 시연
window._sdacs.spawnAdversarial('decoy');
window._sdacs.enableCuas(true);
window._sdacs.setCuasMode('rf_jam');
```

## 🎯 Phase 200 = Unity 도달

```javascript
window._sdacs.p200UnityAchieved();
// → { phase: 200, message: 'SDACS = 𝟏 (Unity). All Phases Complete.' }
```

## 📚 다음 단계

| 목적 | 문서 |
|---|---|
| 388 API 전체 보기 | [SDACS_API.md](SDACS_API.md) |
| Phase 매트릭스 시각 인덱스 | [phase_matrix.html](phase_matrix.html) |
| TypeScript 타입 정의 (IDE autocomplete) | [sdacs.d.ts](sdacs.d.ts) |
| 모든 Phase 단계별 설명 | [SIMULATOR_MEGA_PLAN.md](SIMULATOR_MEGA_PLAN.md) ~ [POST_UNIVERSE_PLAN](SIMULATOR_POST_UNIVERSE_PLAN.md) |
| 데스크탑 v1.5.0 직접 빌드 | [RELEASE_GUIDE.md](RELEASE_GUIDE.md) |
| 졸업 심사 보고서 | [SDACS_Capstone_Report_v200.docx](report/SDACS_Capstone_Report_v200.docx) |
| IROS 2026 §4-§7 | [SDACS_IROS_2026_sections_4to7.pdf](paper/SDACS_IROS_2026_sections_4to7.pdf) |

## ❓ 트러블슈팅

- **흰 화면**: 인터넷 연결 없음 → 로컬 HTTP 서버 사용 (`python -m http.server 8000`)
- **WebGL 안 됨**: 브라우저 hardware acceleration 활성화
- **콘솔 명령 안 먹음**: `window._sdacs` 가 `undefined` 라면 시뮬 초기화 완료 대기 (2-3초)
- **VR 모드 안 보임**: WebXR 미지원 브라우저 → Chrome/Edge + HTTPS 환경 필요

---

SDACS = 𝟏 (Unity). All 200 Phases Complete.

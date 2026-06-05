# 🚀 SDACS Desktop Simulator v1.2.0 — Release Notes

*Release date: 2026-06-05*
*Build: Electron 32.3.3 + electron-builder 25.1.8*

## 🎉 50 Phase 통합 완료 — MEGA 9 + HYPER 41

### 💎 핵심 신규 (v1.1 → v1.2 차이)

#### 통신·인프라
- 🛰 **Satellite Constellation** (Phase 32) — Starlink/OneWeb/Kuiper LEO 가시성 + handoff
- 📡 **5G MEC Edge Computing** (Phase 35) — 노드 부하 기반 워크로드 할당
- 🔁 **UTM Federation** (Phase 30, 기존) + **Cross-Border** (Phase 48, 신규) — 국가 간 공역 통과
- 🐠 **UUV 수중 드론** (Phase 33) — 음파 통신 1 kbps

#### AI·자동화
- 🧪 **Sensor Fusion Workbench** (Phase 34) — LiDAR/Radar/EO/IR/RF + Kalman/EKF/Particle
- 🧠 **Federated Learning** (Phase 36) — DP epsilon 소진 + convex avg
- 🎤 **Voice Command Macros** (Phase 43) — 시퀀스 등록 + 실행
- 👁 **Eye-Tracking Heatmap** (Phase 42) — 시선 분포 분석

#### 운영·제어
- 🔧 **HITL Cluster** (Phase 45) — 다중 Pixhawk
- 🛩 **Digital Twin Pixhawk** (Phase 22, 기존) — MAVLink GPI 28바이트 파서
- 🌐 **Multi-Domain** (Phase 37) — 공중+지상 UGV+해양 inter-domain handoff
- ⏩ **Time Compression** (Phase 44) — 0.1× ~ 10000×

#### 비주얼·환경
- 🔊 **Doppler Audio** (Phase 38) — 343 m/s 음속 기반 주파수 shift
- 🏗 **Procedural City Generation** (Phase 41) — 랜덤 빌딩 분포
- 🏙 **Photogrammetry Replay** (Phase 39) — 외부 3D import
- 🪐 **Planetary Operation** (Phase 49) — Earth/Moon/Mars 중력+대기

#### 정책·사용자
- 🇰🇷 **National Airspace 1:1** (Phase 46) — 한국 6 공항 ICAO
- 🌱 **Climate Impact** (Phase 47) — 0.434 kg CO2/kWh, 250W
- 🎮 **Esports Mode** (Phase 40) — PvP defender vs attacker
- 🏆 **Public Demo** (Phase 50) — leaderboard + daily challenge

## 📊 측정값

| 항목 | v1.1.0 | **v1.2.0** | 증가 |
|---|:-:|:-:|:-:|
| 시뮬레이터 코드 | 9,793 line | **10,735 line** | +942 |
| `_sdacs` API | 170+ | **231개** | +61 |
| Playwright E2E | 171/172 | **193/194** | +22 |
| 회귀 pytest | 4,140 | 4,140 | — |
| **종합 통과** | 4,311 | **4,333** | +22 |
| Phase 완료 | 30 | **50** | +20 |
| AppImage 크기 | 105 MB | 105 MB | — |
| ASAR 내부 | 546 KB | ~600 KB | +50 KB |

## 🔧 빌드 검증

| Platform | Target | Status |
|---|---|---|
| Linux x64 | AppImage | ✅ **로컬 빌드 완료** (`dist-desktop/SDACS-Simulator-1.2.0-x86_64.AppImage`) |
| Windows x64 | NSIS .exe | 🔄 `v1.2.0` 태그 푸시 시 자동 |
| macOS x64/arm64 | DMG | 🔄 `v1.2.0` 태그 푸시 시 자동 |

## 🚀 설치 방법

### Linux
```bash
chmod +x SDACS-Simulator-1.2.0-x86_64.AppImage
./SDACS-Simulator-1.2.0-x86_64.AppImage
```

### Windows / macOS
v1.2.0 태그 푸시 → `desktop-build.yml` 워크플로우 자동 실행 → GitHub Releases 발행 대기

자세한 절차: [`docs/RELEASE_GUIDE.md`](RELEASE_GUIDE.md)

## 📚 새 문서

- [`docs/SIMULATOR_HYPER_PLAN.md`](SIMULATOR_HYPER_PLAN.md) — Phase 11-50 마스터 (HYPER 플랜)
- [`docs/SDACS_API.md`](SDACS_API.md) — 231개 `_sdacs` API 자동 추출
- [`docs/paper/SDACS_50_Phases_Results.tex`](paper/SDACS_50_Phases_Results.tex) — 논문 §Results 직접 삽입용

## 🔄 마이그레이션 (v1.1.0 → v1.2.0)

- API 100% 하위 호환
- 기존 코드 변경 불필요
- 신규 19개 API 자동 노출 (선택 사용)

## 🙏 감사

목포대학교 드론기계공학과 캡스톤 2026 — 본 릴리스로 **MEGA 9 + HYPER 41 = 50 Phase** 전부 완료.

세계 최초 50 Phase 통합 학생 캡스톤 시뮬레이터.

## 🔗 링크

- GitHub: https://github.com/sun475300-sudo/swarm-drone-atc
- Live demo: https://sun475300-sudo.github.io/swarm-drone-atc/
- 라이브 시뮬: https://sun475300-sudo.github.io/swarm-drone-atc/swarm_3d_simulator.html

<div align="center">

# SDACS
## Swarm Drone Airspace Control System

군집드론 공역통제 자동화 시스템 · 국립목포대학교 드론기계공학과 캡스톤 디자인

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![CI](https://github.com/sun475300-sudo/swarm-drone-atc/actions/workflows/ci.yml/badge.svg)](https://github.com/sun475300-sudo/swarm-drone-atc/actions/workflows/ci.yml)
[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-live-22c55e?style=for-the-badge&logo=github)](https://sun475300-sudo.github.io/swarm-drone-atc/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

[라이브 사이트](https://sun475300-sudo.github.io/swarm-drone-atc/) · [3D 시뮬레이터](https://sun475300-sudo.github.io/swarm-drone-atc/simulator.html) · [해양 탐지 시뮬레이터](https://sun475300-sudo.github.io/swarm-drone-atc/maritime_detection_simulator.html) · [문서 색인](docs/INDEX.md) · [English](README.en.md)

</div>

> **성격과 범위**: SDACS는 SimPy 기반 이산 이벤트 시뮬레이터와 브라우저 3D 시각화 도구를 중심으로 한 연구·교육용 프로젝트입니다. 여기의 성능 수치와 시나리오는 시뮬레이션 검증값이며, 실제 비행 안전 인증·운항 승인·상용 관제 서비스의 근거가 아닙니다.

## 현재 상태

마지막 저장소 점검일은 **2026-07-30 (KST)** 입니다. 정확한 최신 커밋은 `git log -1 --oneline origin/main`으로 확인합니다.

| 항목 | 확인 결과 |
|---|---|
| 기본 브랜치 | `main` — 로컬과 `origin/main` 동기화 상태에서 점검 |
| GitHub Actions | 최신 `main` 푸시의 CI, Security Audit, Canonical Hash Verification, Pages 배포 모두 성공 |
| GitHub Pages | 루트, 3D 시뮬레이터, 해양 시뮬레이터 HTTP 200 확인 |
| 정적 시뮬레이터 산출물 | `python scripts/build_simulator.py` 및 `--check` 성공. `build/simulator/` 생성 확인 |
| Python 회귀 | 최신 CI가 Python 3.10 / 3.11 / 3.12 매트릭스에서 성공. 린트·mypy·커버리지 80% 게이트 포함 |
| 데스크톱 앱 | Electron 빌드 설정과 3-OS GitHub Actions 워크플로는 존재하지만, 현재 GitHub Releases에는 SDACS 앱 설치 파일이 공개되어 있지 않음 |

## 시스템 구성

SDACS는 하나의 제품 서버가 아니라, 공통 시나리오와 모델을 공유하는 여러 실행 표면으로 구성됩니다.

| 영역 | 역할 | 대표 경로 |
|---|---|---|
| 시뮬레이션 엔진 | SimPy 환경, 드론 에이전트, 충돌 회피, 공역 제어, 날씨·통신·고장 주입 | [simulation/simulator.py](simulation/simulator.py), [simulation/drone_agent.py](simulation/drone_agent.py), [src/airspace_control](src/airspace_control) |
| CLI·실험 | 단일 실행, 시나리오, Monte Carlo, 벤치마크, 운영 리포트 | [main.py](main.py), [config/scenario_params](config/scenario_params) |
| 웹 시뮬레이터 | 메인 Three.js 군집드론 시뮬레이터와 해양 소형선 감지 시뮬레이터 | [swarm_3d_simulator.html](swarm_3d_simulator.html), [maritime_detection_simulator.html](maritime_detection_simulator.html) |
| Dash 시각화 | Python 기반 3D 대시보드 | [visualization/simulator_3d.py](visualization/simulator_3d.py) |
| API | FastAPI 기반 스냅샷·시나리오·운영 실행·WebSocket 실험 백엔드 | [api/fastapi_server.py](api/fastapi_server.py) |
| 데스크톱 래퍼 | Electron으로 두 브라우저 시뮬레이터를 패키징 | [desktop/main.js](desktop/main.js), [package.json](package.json) |
| 재현·검증 | 테스트, 벤치마크, 정적 빌드, GitHub Actions | [tests](tests), [benchmarks](benchmarks), [scripts/build_simulator.py](scripts/build_simulator.py), [.github/workflows](.github/workflows) |

### 메인 3D 시뮬레이터의 정본 규칙

루트의 [`swarm_3d_simulator.html`](swarm_3d_simulator.html)이 정본입니다. 아래 파일은 빌드 스크립트가 정본과 동기화합니다.

- `visualization/swarm_3d_simulator.html`
- `docs/swarm_3d_simulator.html`
- `docs/simulator.html`
- `build/simulator/`의 정적 배포 산출물

수동 복사 대신 항상 `python scripts/build_simulator.py`를 사용합니다.

## 빠른 시작

### 1. Python 시뮬레이션

```bash
git clone https://github.com/sun475300-sudo/swarm-drone-atc.git
cd swarm-drone-atc
python -m pip install -e ".[dev]"

# 60초, 20대 기본 시뮬레이션
python main.py simulate --duration 60 --drones 20

# 사용 가능한 명령과 옵션 확인
python main.py --help
```

주요 CLI 명령은 `simulate`, `scenario`, `monte-carlo`, `benchmark`, `visualize`, `visualize-3d`, `api`, `ops-report`입니다.

### 2. 브라우저 시뮬레이터

```bash
# 저장소 루트를 HTTP로 서빙하고 기본 브라우저 열기
python scripts/serve.py

# 해양 소형선 감지 시뮬레이터
python scripts/serve.py --page maritime
```

`file://`로 HTML을 직접 열면 ES module과 브라우저 CORS 정책 때문에 Three.js가 로드되지 않을 수 있습니다. 위 서버, GitHub Pages, 또는 Electron 앱으로 실행하세요.

### 3. Dash 대시보드와 API

```bash
python main.py visualize   # Dash 대시보드
python main.py api         # FastAPI 백엔드
```

API는 연구·통합 실험용입니다. 현재 구현은 인메모리 상태를 사용하므로, 다중 인스턴스 운영과 영속화가 필요한 배포에는 Redis/PostgreSQL 등 별도 저장소와 운영 구성이 필요합니다.

## 시뮬레이터만 빌드·배포하기

```bash
# 정본 동기화 + 정적 배포 산출물 생성
python scripts/build_simulator.py

# 산출물과 동기화 상태 확인
python scripts/build_simulator.py --check

# 생성된 산출물 미리보기
python -m http.server 8123 --directory build/simulator
```

브라우저에서 `http://localhost:8123/`를 열면 `simulator.html`로 이동합니다. `build/simulator/`는 메인 시뮬레이터·manifest·service worker·로컬 Three.js vendor 파일을 함께 포함하므로 정적 호스팅 대상 디렉터리로 사용할 수 있습니다.

GitHub Pages는 `main`의 `docs/`를 배포합니다. `.github/workflows/deploy-pages.yml`이 정본 시뮬레이터와 Three.js vendor 파일을 `docs/`에 동기화한 뒤 배포합니다.

## 데스크톱 앱 빌드

```bash
npm ci
npm run build:simulator

# 패키징 구조만 검증
npm run pack

# Windows 설치 파일과 portable 실행 파일 생성
npm run dist:win
```

macOS와 Linux는 해당 OS에서 `npm run dist:mac`, `npm run dist:linux`를 실행합니다. 산출물은 `dist-desktop/`에 생성되며 Git에서 제외됩니다.

릴리스 발행은 `v*` 태그를 `origin`에 푸시하면 [Desktop Build workflow](.github/workflows/desktop-build.yml)가 Windows·macOS·Linux 빌드와 GitHub Release 업로드를 수행하도록 구성돼 있습니다. 실제 태그 발행 전에는 각 플랫폼 빌드와 코드 서명 정책을 별도로 확인하세요.

## 검증 방법

```bash
# Python 품질 게이트
ruff check src/ simulation/
mypy src/
python -m pytest tests/ -q

# 메인 시뮬레이터 산출물 정합성
npm run build:simulator:check

# 브라우저 스모크 테스트 (Playwright/Chromium 설치 후)
python -m http.server 8123
# 새 터미널에서:
# PowerShell: $env:SIM_URL='http://localhost:8123/swarm_3d_simulator.html'; node tests/e2e/smoke_sim.mjs
```

CI는 Python 3.10·3.11·3.12에서 테스트, `ruff`, `mypy src/`, 커버리지 80% 기준, 메인 브랜치 벤치마크를 수행합니다. 시뮬레이터 변경은 별도의 Node/Playwright 스모크 워크플로에서 확인합니다.

## 문서와 연구 자산

| 목적 | 문서 |
|---|---|
| 전체 문서 색인 | [docs/INDEX.md](docs/INDEX.md) |
| 웹 시뮬레이터 API와 성숙도 | [docs/SDACS_API.md](docs/SDACS_API.md) |
| 저장소 점검 기록 | [docs/HEALTH_CHECK.md](docs/HEALTH_CHECK.md) |
| 실기 하드웨어 계획 | [docs/hardware/README.md](docs/hardware/README.md) |
| 논문 기여와 투고 준비 | [docs/paper/contribution_outline.md](docs/paper/contribution_outline.md) |
| 사업화·산학 트랙 | [docs/track_f/README.md](docs/track_f/README.md) |
| 장기 로드맵 | [ROADMAP.md](ROADMAP.md) |
| 변경 이력 | [CHANGELOG.md](CHANGELOG.md) |

`window._sdacs` API 문서에는 production, beta, mock, speculative 등 성숙도 표기가 포함됩니다. API 이름 또는 Phase 번호만으로 실환경 적용 가능성을 판단하지 말고 해당 성숙도와 테스트 근거를 확인하세요.

## 현재 남은 작업

아래 항목은 2026-07-30 기준 `main`과 GitHub 운영 상태를 점검해 정리한 실제 후속 작업입니다.

| 우선순위 | 작업 | 상태·이유 |
|---|---|---|
| 높음 | 의존성 업데이트 PR 검토·병합 | Dependabot PR [#512](https://github.com/sun475300-sudo/swarm-drone-atc/pull/512)~[#518](https://github.com/sun475300-sudo/swarm-drone-atc/pulls?q=is%3Aopen%20is%3Apr) 대기. `numpy`·Playwright·GitHub Actions는 CI/E2E 재검증 후 병합 필요 |
| 높음 | 데스크톱 공개 릴리스 발행 | 빌드 설정은 있으나 현재 Releases에는 SDACS 앱 설치 파일이 없음. 태그 기반 3-OS 빌드와 산출물 검증 필요 |
| 높음 | `main` 브랜치 보호 설정 | GitHub API 기준 branch protection 미설정. 필수 CI·리뷰·관리자 우회 정책을 결정해야 함 |
| 중간 | FastAPI 운영화 | 인메모리 상태를 Redis/PostgreSQL, 인증 키 관리, 관측성, 배포 환경으로 교체 또는 범위 제한을 문서화해야 함 |
| 중간 | 실기·HITL·현장 데이터 검증 | 하드웨어 계획 문서는 있으나 Pixhawk·Jetson·RTK·실비행·외부 기관 연동은 소프트웨어 CI로 대체할 수 없음 |
| 중간 | 문서 정합성 정리 | 오래된 Phase/릴리스 수치를 포함한 보조 문서와 초안 PR [#510](https://github.com/sun475300-sudo/swarm-drone-atc/pull/510)을 현재 README 기준으로 검토·정리해야 함 |
| 낮음 | 오래된 운영 이슈 정리 | [#409](https://github.com/sun475300-sudo/swarm-drone-atc/issues/409)는 2026-06-21의 수동 점검 이슈로, 현재 상태 확인 후 종료 또는 갱신 필요 |

## 기여와 보안

- 기여 절차: [CONTRIBUTING.md](CONTRIBUTING.md)
- 보안 취약점 신고: [SECURITY.md](SECURITY.md)
- 라이선스: [MIT License](LICENSE)

이 저장소의 자동화와 시뮬레이터는 연구·교육·프로토타이핑에 적합합니다. 사람·항공기·재산에 영향을 줄 수 있는 실제 운용에는 독립적인 안전성 검증, 규제 승인, 운영 책임 체계가 필요합니다.

# 🔧 유지보수 최소 모드 명세 (GENESIS Phase 389)

*Created: 2026-06-12 · 대상: 후속 캡스톤·유지보수자·1인 운영자*

> **문제**: SDACS는 200+ Phase 매트릭스, 11,800줄 단일 시뮬레이터, 800+ 파일.
> 후속 기수·1인 유지보수자가 **전부 이해할 필요는 없다**. 본 문서는 "최소 작동 핵심"을 정의해
> 나머지를 보조 자산으로 분류한다.

## 1. 코어 서브셋 (반드시 유지 — 빌드/테스트가 의존)

| 영역 | 파일 | 이유 |
|---|---|---|
| **시뮬 코어 (Python)** | `simulation/swarm_simulator.py`·`simulation/drone_agent.py` | SimPy 엔진. 회귀 4,180건 기반 |
| **공역 관제 (Python)** | `src/airspace_control/controller/` | 1Hz 충돌 감지/해결 |
| **메트릭스 (Python)** | `src/analytics/metrics.py` | NMR·MSD·PE 8종 공식 정의 |
| **웹 시뮬 (단일 HTML)** | `swarm_3d_simulator.html` | 데모·교육 핵심. 4 사본 md5 일치 강제 |
| **해양 시뮬 (단일 HTML)** | `maritime_detection_simulator.html` | 별도 도메인 |
| **CLI 진입점** | `main.py` | 사용자 1줄 명령 |
| **설정** | `config/default_simulation.yaml`·`config/scenario_params/*.yaml` | 9 시나리오 |
| **CI 워크플로** | `.github/workflows/{ci,sim-smoke,security}.yml` | 회귀·E2E·보안 |
| **정직성 게이트** | `scripts/extract_sdacs_api.py` | 문서-실측 일치 강제 |

## 2. 코어 테스트 (최소 회귀)

```bash
# 1) Python 회귀 (e2e 제외, 3분, GREEN 필수)
python -m pytest tests/ --ignore=tests/e2e -q --no-cov

# 2) 시뮬 JS 구문 (10초)
python -c "import re; s=open('swarm_3d_simulator.html').read(); m=re.search(r'<script type=\"module\">(.*?)</script>', s, re.DOTALL); open('/tmp/x.mjs','w').write(m.group(1))"
node --check /tmp/x.mjs

# 3) 4 사본 md5 일치 (1초)
md5sum swarm_3d_simulator.html visualization/swarm_3d_simulator.html docs/simulator.html docs/swarm_3d_simulator.html | awk '{print $1}' | sort -u | wc -l  # == 1

# 4) API 문서 정합성 (1분, Chromium 필요)
python scripts/extract_sdacs_api.py --check
```

위 4건이 GREEN이면 **시스템은 유지보수 가능 상태**다.

## 3. 보조 자산 (참조용 — 직접 손대지 말 것)

| 영역 | 위치 | 권장 |
|---|---|---|
| Phase 51-200 mock/speculative 구현 | `swarm_3d_simulator.html` 후반부 | maturity 분류만 갱신, 코드 손대지 말 것 (실 격상 계획은 TRANSCENDENCE 221+) |
| 다중 언어 (Track 611-660) | 각 언어별 파일 | 시연용. 실제 빌드에 미포함 |
| 디지털 트윈·연합 학습 모듈 | `src/digital_twin/`·`src/federated/` | PoC. 실 운영 미사용 |
| 슬라이드·포스터·논문 LaTeX | `docs/slides/`·`docs/poster/`·`docs/paper/` | 산출물. 직접 변경 시 보고서 v200 정합성 주의 |

## 4. 유지보수 워크플로 (1인 기준)

### 일상 (주 1회)
- [ ] `git pull origin main && python -m pytest tests/ --ignore=tests/e2e -q --no-cov` GREEN
- [ ] GitHub Actions main 워크플로 전부 success
- [ ] `dependabot.yml` 자동 PR 처리 (보안 패치만 즉시 머지)

### 변경 발생 시
- [ ] 작업 브랜치 생성 (`feat/<topic>`)
- [ ] 시뮬 코드 변경 시 **반드시 4 사본 동시 갱신** (sync script 또는 수동 cp)
- [ ] `extract_sdacs_api.py` 재생성 + `--check` GREEN
- [ ] PR + CI green 확인 후 main 머지

### 분기 (3개월 1회)
- [ ] `requirements.txt` minor 버전 검토 (메이저는 별도 PR)
- [ ] Electron LTS 정렬 (현 32→39 교훈: 1년 1회 업그레이드)
- [ ] Three.js 버전 모니터 (현 r162 — 메이저 업그레이드 시 호환 셰임 필요)

### 연 (1년 1회)
- [ ] 신규 컨테이너 독립 재현 검증 (`scripts/independent_reproduction.sh`)
- [ ] 보고서 v200 → 갱신본 발행 (수치 부분만)
- [ ] 캡스톤 후속 기수 인수인계 미팅

## 5. 비상 절차

| 상황 | 조치 |
|---|---|
| CI 빨강 + 회귀 GREEN | 일시적 인프라 문제일 가능성. 24h 대기 후 재실행 |
| CI 빨강 + 회귀 빨강 | 즉시 직전 GREEN 커밋으로 revert 검토. 원인 디버깅은 사후 |
| 4 사본 md5 불일치 | 누가 한쪽만 편집함. `cp swarm_3d_simulator.html visualization/... docs/...` 로 정렬 |
| 외부 의존 패키지 폐기 | `pyproject.toml` pinning → 대안 검토 → 점진 교체 |

## 6. 인수인계 체크리스트 (졸업 시)

- [ ] 본 문서 + [`presentation/DEFENSE_KIT.md`](presentation/DEFENSE_KIT.md) 후임에게 walkthrough
- [ ] CONTRIBUTING.md + [`track_f/p754_mentoring.md`](track_f/p754_mentoring.md) 공유
- [ ] GitHub 권한 이양 (Maintainer 권한)
- [ ] CI secrets 갱신 (없을 경우 명시)
- [ ] 1년간 분기별 점검 약속 (Issue 라벨 `legacy-checkin`)

## 🔗 관련
- [`SIMULATOR_GENESIS_PLAN.md`](SIMULATOR_GENESIS_PLAN.md) — Phase 389 정의 근거
- [`certification/RTM_5LAYER_COVERAGE.md`](certification/RTM_5LAYER_COVERAGE.md) — 21건 추적 매트릭스
- [`presentation/DEFENSE_KIT.md`](presentation/DEFENSE_KIT.md) — 심사 대비
- [`track_f/p754_mentoring.md`](track_f/p754_mentoring.md) — 후속 캡스톤 멘토링

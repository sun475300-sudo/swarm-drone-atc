# Changelog

이 프로젝트의 모든 주요 변경 사항을 기록합니다.
형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/)를 기반으로 합니다.

## [Unreleased] - 2026-05-03

### 추가 (feat)

- `FormationPattern.DIAMOND` (5번째 편대 패턴) — 영상 컨셉 4방향 외곽 확장 (`a222b08`, PR #23)
- `swarm_autonomous_no_preplan` 시나리오 — 사전 경로 없이 자율 탐색 데모 (`4c67eac`, PR #23)
- `docs/MASTER_TODO_ATC.md` — 통합 백로그 (A0~A4 트랙 + Phase 691~720) (PR #19)
- `docs/REGRESSION_NOTES_2026-04-26.md` — torch DLL fallback + build-backend 회귀 노트 (PR #19)
- `docs/OPS_TRAFFIC_RED_ANALYSIS_2026-05-03.md` — ops_report traffic RED 의도된 동작 분석 (PR #26)
- `docs/faq.md` — 캡스톤 발표 Q&A 20문항 (PR #22)
- `docs/roadmap_public.md` — Phase 691~720 공개 로드맵 (PR #22)
- `CONTRIBUTING.md` — 학술 프로젝트용 기여 가이드 (PR #22)
- `SECURITY.md` — 책임 있는 신고 정책 (PR #19)

### 수정 (fix)

- torch import OSError 처리 — Windows DLL 차단 시 simulator graceful CPU fallback (PR #19, `0d4dafa`+`c13f72d`)
- `pyproject.toml` build-backend 오타 수정 (`setuptools.backends.legacy:build` → `setuptools.build_meta`) — CI 의존성 설치 단계 복구 (PR #19, `a59fd48`)
- `src/hardware/onboard_bridge.py` mypy 4건 회귀 — `[tool.mypy.overrides]` 에 `src.hardware.*` 추가 (PR #19, `d6b437f`)
- `python-app.yml` deprecated 빈 워크플로 — manual-dispatch 격리, 매 푸시 0초 fail 노이즈 제거 (PR #22)
- README 테스트 수 동기화 (2,722+ → 3,330+) (PR #19)

### 의존성 (deps)

- jinja2 3.1.4 → 3.1.6 (sandbox breakout 3건 patch, dependabot) (PR #21, `a73cd9b`)
- pytest 8.x 명시 핀 (`pytest>=8.4,<9`) — pytest 9 메이저 자동 PR 차단 (PR #24)
- imgur 외부 의존 제거 — 12개 이미지 `docs/images/imgur/` 로 로컬화 (1.9MB) (PR #25)

### 테스트 (test)

- `tests/test_apf_engine_fallback.py` — torch fallback 회귀 방지 4건 (PR #19)
- `tests/test_main_cli.py` — argparse 회귀 방어 8건 (PR #22)
- `tests/test_formation.py` — 5 패턴 30 회귀 (DIAMOND 신규 포함) (PR #23)
- `tests/test_e2e_reporter_traffic_thresholds.py` — traffic 임계 경계 8건 (PR #26)

### 외부 작업 (main 직접 푸시, Phase B 트랙)

- P701 paper topic 확정 — AIAA SciTech 2027 D-39 (`c54829f`)
- P702 prior-work survey 30 references (MAPF / Reactive / UTM / Swarm 4 buckets) (`b7fb88b`)
- P704 Reproducibility — centralized RNG + lock file (`f0ec08c`)
- P707 paper draft (Add) + MAVLink adapter 개선 (`155e2a1`)

### CI/배포

- 본 라운드 6 PR 머지 + 1 PR close (#19/#21/#22/#23/#24/#25 머지, #20 close)
- 열린 PR 0개 → main 깔끔한 상태 (2026-04-27 시점)

## [1.0.0] - 2026-04-13

### 추가 (feat)

- 12개 고급 확장 일괄 완료 (`0a43a9a`)
- PPO 강화학습 충돌 회피 에이전트 추가 (`04cda85`)
- ONNX 모델 내보내기 + GNN 드론 통신 네트워크 (`967a675`)
- 12개 확장 작업 일괄 완료 (`d0edbc5`)
- PyTorch 기반 ML 충돌 예측 모델 추가 (`ef92cbe`)
- FastAPI REST API 서버 추가 (`0cc2548`)
- WebSocket 실시간 브릿지 + GitHub Pages 링크 + MC 워커 호환성 (`d6e00e8`)
- 충돌해결률 97.5% 달성 + Docker GPU + 벤치마크 + 시나리오 대시보드 (`a624098`)
- Docker GPU 이미지 설정 (nvidia-docker) (`a0c8eae`)
- GPU 텐서 캐싱 + FP16 + CI 파이프라인 + Dash GPU 패널 (`b5f5bba`)
- 3D 시뮬레이터 HUD에 GPU 상태 표시 + DeprecationWarning 수정 (`94416f7`)
- CBS 충돌탐지 + Voronoi 공역분할 GPU 가속 추가 (`cb09562`)
- PyTorch CUDA GPU 가속 APF 엔진 추가 (`3103041`)

### 수정 (fix)

- waypoint_optimizer np.cross 2D DeprecationWarning 수정 (`42a3f89`)
- 20개 테스트 실패 수정 + deadlock 해결 → 2,722 전체 통과 (`3870551`)
- estimate_power_w ZeroDivisionError 방지 + ATC 드론 UI 크기 확대 (`91a8f7c`)

### 테스트 (test)

- airspace_controller 커버리지 강화 (11→29개) + flaky test 안정화 (`587eaf4`)

### 문서 (docs)

- README GPU 가속 가이드 및 테스트 현황 업데이트 (`00613e2`)
- 공모용 아이디어 상세설명 텍스트 추가 (`5a0c2de`)

### 기타

- Merge pull request #16 (`ae6d533`)

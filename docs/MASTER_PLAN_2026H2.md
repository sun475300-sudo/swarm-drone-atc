# 🧭 SDACS 마스터플랜 2026 H2 — 통합 실행 로드맵

*Created: 2026-06-12 — 전체 README·로드맵·소스코드 종합 감사 직후*

> 기존 계획 문서들의 **실행 우선순위·일정·검증 기준을 단일 문서로 통합**한다.
> 신규 비전 추가가 아니라, 이미 수립된 계획(울트라플랜 Phase 0-5 + TRANSCENDENCE 201-300)을
> **실측 검증 가능한 스프린트**로 변환하는 것이 목적이다.

---

## 📊 2026-06-12 종합 감사 결과 (실측 기준선)

| 지표 | 문서 표기 (감사 전) | 실측 값 | 조치 |
|---|:-:|:-:|---|
| `_sdacs` API | 391 | **402** (분류 400 + 헬퍼 2) | ✅ README·VERSION·SDACS_API·d.ts 정정 |
| Maturity 분포 | 89/98/110/103 | **89/98/110/103** (일치) | ✅ 검증 완료 |
| 시뮬레이터 코드 | 11,695~11,723 line | **11,836 line** | ✅ 정정 |
| 회귀 pytest (e2e 제외) | 4,140/4,140 | **4,180 pass / 8 skip / 0 fail** | ✅ 정정 |
| Playwright E2E | 248/249 | 255/256 (본 PR CI 참조) | ✅ 정정 |
| SDACS_API.md maturity 컬럼 | "포함" 주장, 실제 없음 | **402행 maturity 컬럼 재생성** | ✅ 수정 |
| sdacs.d.ts | 394~396 멤버 | **402 멤버 재생성** | ✅ 수정 |
| Electron | 32.3.3 | 32.3.3 (v1.5.0 빌드) / ^39.8.5 (차기) | ✅ VERSION 주석 |

**교훈 → 거버넌스 규칙**: 문서 수치는 손으로 쓰지 않는다. 라이브 페이지 실측 추출(아래 G-1)로 자동화한다.

---

## 🗂 트랙 구성 (4개 실행 트랙 + 1개 거버넌스 트랙)

### Track Ⅰ — 시각화 완성 (울트라플랜 Phase 1-5 잔여) · ~2026-07

기반: `swarm_3d_simulator.html` (11,836 line, 4 사본 md5 동기화)

| 스프린트 | 작업 | 검증 기준 |
|---|---|---|
| Ⅰ-1 | CPA 예측선 고도화 — TTC 라벨·위험도 색상 (Q2 동기화 완료분 위에) | E2E: `_cvLabelData` 위험쌍 표시 assert |
| Ⅰ-2 | 어드바이저리 빌보드 — CLIMB/DESCEND/TURN/EVADE/HOLD 아이콘 점멸 | E2E: advisory 발생 시 빌보드 visible |
| Ⅰ-3 | 리플레이 스크러버 마감 — 라이브↔리플레이 멀티뷰 커서 동기(P734 위) | E2E: replayIdx ↔ 차트 커서 일치 |
| Ⅰ-4 | 리포트 내보내기 KPI를 `gen_report_v6/v7.py` 정의와 1:1 일치 | CSV 컬럼 diff = 0 |
| Ⅰ-5 | mega_swarm 1k/5k 시나리오 FPS 실측 표 문서화 | 성능 HUD 수치 캡처 |

### Track Ⅱ — Maturity 격상 (TRANSCENDENCE 203-220) · ~2026-08

| 스프린트 | 작업 | 검증 기준 |
|---|---|---|
| Ⅱ-1 | Phase 203 Mock Detector — mock API 호출 시 console.warn | E2E: warn 카운트 assert |
| Ⅱ-2 | Phase 206 `experimental.*` 네임스페이스 — speculative 103종 격리 (기존 호출 호환 유지) | E2E: 직접 호출 + experimental 경유 동등성 |
| Ⅱ-3 | Phase 204-205 production 핵심 12종 + beta 회귀 강화 | 신규 회귀 30+건 |
| Ⅱ-4 | Phase 209-210 Deprecation Policy + SemVer 문서 | docs 추가 |
| Ⅱ-5 | mock → production 격상 1차 (WebGPU WGSL 실 컴파일·CRDT Yjs) | 실측 벤치 수치 |

### Track Ⅲ — 다중 사용자·서비스 실증 (TRANSCENDENCE 241-260) · ~2026-09

기존 자산 재사용: `api/fastapi_server.py`(JWT/RBAC), `simulation/ws_bridge.py`, `helm/sdacs/`, TimescaleDB

| 스프린트 | 작업 | 검증 기준 |
|---|---|---|
| Ⅲ-1 | 시뮬 LIVE 토글 ↔ ws_bridge 실데이터 왕복 E2E | Playwright + ws 서버 fixture |
| Ⅲ-2 | 2-브라우저 협업 E2E (Playwright 다중 컨텍스트) | 동시 선택/명령 충돌 해소 assert |
| Ⅲ-3 | 부하 테스트 100 동시 사용자 (`scripts/load_test.py` 확장) | p99 < 100ms |
| Ⅲ-4 | 베타 파일럿 온보딩 (KARI·해수부·산림청 — `docs/beta/`) | NPS 파이프라인 가동 |

### Track Ⅳ — 학술·실기 (TRANSCENDENCE 261-300) · ~2026-12 *(일부 사용자 환경 의존)*

| 스프린트 | 작업 | 의존성 |
|---|---|---|
| Ⅳ-1 | Ablation 자동화 — 5계층 안전망 계층별 제거 효과 (Phase 286) | sandbox 가능 |
| Ⅳ-2 | 비교 실험 통계 유의성 자동 리포트 (ORCA/VO/CBS) | sandbox 가능 |
| Ⅳ-3 | IROS 2026 투고 패키지 (P707 실측 그래프 통합) | 사용자 투고 |
| Ⅳ-4 | Pixhawk HITL 실증 (Phase 261-270) | 사용자 HW |
| Ⅳ-5 | 벤치마크 Zenodo DOI + K-UTM 표준 제안 초안 | 사용자 계정 |

### Track G — 문서 정합성 거버넌스 (상시)

이번 감사에서 발견된 **수치 드리프트 재발 방지**:

- **G-1** `scripts/extract_sdacs_api.py` 신설 — 라이브 페이지에서 API 목록+maturity를 추출해 `SDACS_API.md`·`sdacs.d.ts` 재생성 (이번 감사의 임시 스크립트를 영구화)
- **G-2** CI 잡 — README의 API 수·line 수가 실측과 다르면 경고 (sim-smoke.yml 확장)
- **G-3** 모든 수치 갱신 PR은 추출 스크립트 산출물 diff 첨부
- **G-4** 4 사본 md5 일치 검사를 CI gate로 (이미 build_simulator.py --check 존재 → 잡 연결)

---

## 📅 마일스톤 요약

| 시점 | 마일스톤 | 핵심 지표 |
|---|---|---|
| 2026-07 | Track Ⅰ 완료 + v1.6.0 | 시각화 5종 마감, E2E 280+ |
| 2026-08 | Track Ⅱ 완료 | production API 89 → 120+, mock detector 가동 |
| 2026-09 | Track Ⅲ 완료 + v1.7.0 | 다중 사용자 실증, 부하 100명 |
| 2026-12 | Track Ⅳ 1차 | IROS 결과 + HITL 실증 + v2.0.0 후보 |

## 🔁 거버넌스 (공통 게이트)

1. 회귀 4,180+ pass / 0 fail 보존 (2026-06-12 실측 기준선)
2. 4 사본 md5 일치 (군집) + 3 사본 (해양)
3. 신규 기능은 E2E 1건 이상 동반
4. 문서 수치는 실측 추출만 허용 (G-1)
5. mock 격상 시 실측 근거(벤치마크/외부 데이터) 필수

## 📚 관련 문서

- [`SIMULATOR_TRANSCENDENCE_PLAN.md`](SIMULATOR_TRANSCENDENCE_PLAN.md) — Phase 201-300 상세
- [`SIMULATOR_MEGA_PLAN.md`](SIMULATOR_MEGA_PLAN.md) ~ [`SIMULATOR_POST_UNIVERSE_PLAN.md`](SIMULATOR_POST_UNIVERSE_PLAN.md) — Phase 1-200 (완료)
- [`../ROADMAP.md`](../ROADMAP.md) — Track A-G 전체 현황
- [`SDACS_API.md`](SDACS_API.md) — 402 API maturity 레퍼런스

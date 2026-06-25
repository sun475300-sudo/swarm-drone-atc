# SDACS 4대 소프트웨어 계획서 (DO-178C §4.3, GENESIS Phase 320)

> DO-178C §4.3 이 요구하는 4대 소프트웨어 계획서(SDP·SVP·SCMP·SQAP)를 SDACS
> 의 **실제 개발 프로세스**에 근거해 명문화한다. 연구용 시뮬레이터(DAL-D 가정)
> 수준의 정직한 계획서이며, 각 계획은 리포지토리에 실재하는 산출물을 근거로
> 한다. 존재·준비도 자동 점검은 Phase 314(`simulation/airworthiness_checklist.py`)
> PLANNING 영역이 수행한다.
>
> **정직성 공시**: 본 계획서는 전담 인증팀·독립 검증조직이 없는 학생 캡스톤의
> 실제 운영을 기술한다 — 격상하거나 보유하지 않은 프로세스를 주장하지 않는다.

---

## 1. SDP — 소프트웨어 개발 계획 (Software Development Plan)

**목적**: SDACS 소프트웨어의 개발 생명주기·표준·환경을 정의한다.

| 항목 | SDACS 실제 |
|---|---|
| 생명주기 | 반복적(iterative) — Phase 단위 증분 개발, 단일 `main` 브랜치 |
| 아키텍처 | 4계층(드론 10Hz · 제어 1Hz · 시뮬 · UI) + 5계층 안전망 (`CLAUDE.md` §7) |
| 개발 표준 | PEP 8 · 타입 어노테이션 · `ruff`/`black` (`.claude/rules/python-coding-style.md`) |
| 언어/런타임 | Python 3.10–3.12 (SimPy·NumPy·SciPy), JS(시뮬레이터 HTML) |
| 개발 환경 | `pyproject.toml` 의존성 핀 · Docker(`docker/`) · Electron 데스크탑 |
| 추적성 | 요구사항↔설계↔구현↔검증 RTM 5계층 (`simulation/rtm_generator.py`, `docs/certification/RTM_5LAYER_COVERAGE.md`) |
| 로드맵 | `ROADMAP.md` (Phase 1-755 + 시뮬 201-500) |

## 2. SVP — 소프트웨어 검증 계획 (Software Verification Plan)

**목적**: 검증 활동(리뷰·분석·테스트)과 커버리지 목표를 정의한다.

| 항목 | SDACS 실제 |
|---|---|
| 검증 방법 | 단위·통합·E2E 테스트(pytest) + 정적분석(`ruff`) + 속성기반(Hypothesis) |
| 테스트 프레임워크 | pytest (`pyproject.toml` `[tool.pytest.ini_options]`) |
| 커버리지 목표 | **≥ 80%** (`--cov-fail-under=80`, CI 강제) |
| 회귀 게이트 | 머지 전 전체 회귀 CI 통과 필수 (`.github/workflows/ci.yml`, Py 3.10/3.11/3.12 매트릭스) |
| 결정성 검증 | `np.random.default_rng(seed)` 시드 고정 · 대표 시뮬 KPI 재현(seed 42) |
| 검증 단계 | 테스트 계획→설계→실행→커버리지 분석→검토·보고 (Phase 319 `test_procedures.py` 5단계 점검) |
| 독립성 | 자동화 CI 게이트가 독립 검증 역할 — 전담 검증조직은 없음(정직 공시) |

## 3. SCMP — 소프트웨어 형상관리 계획 (Software Configuration Management Plan)

**목적**: 형상 식별·변경통제·베이스라인·감사를 정의한다.

| 항목 | SDACS 실제 |
|---|---|
| 형상 식별 | git 버전관리 · 의존성 핀(`pyproject.toml`) · `.gitignore` 빌드 산출물 격리 |
| 변경통제 | GitHub PR/Issue 단일 채널 + CCB 게이트 (Phase 318 `ccb_change_control.py`) |
| 베이스라인 | git 태그 + **Canonical Hash 검증** (`.github/workflows/canonical_hash.yml`) |
| 변경 추적 | CR↔변경↔검증 RTM 5계층 + `CHANGELOG.md` 단일 이력 |
| 빌드/릴리스 | Electron 3-OS 빌드(`.github/workflows/desktop-build.yml`, `v*` 태그 트리거) |
| 감사 추적 | `CHANGELOG.md` + git 이력(사유·일자·범위) |

## 4. SQAP — 소프트웨어 품질보증 계획 (Software Quality Assurance Plan)

**목적**: 프로세스 준수·품질 게이트·결함 관리를 정의한다.

| 항목 | SDACS 실제 |
|---|---|
| 품질 게이트 | CI: 회귀 통과 + 커버리지 ≥80% + `ruff`(E9/F/W/I) + `bandit` 보안 + Canonical Hash |
| 보안 보증 | `.github/workflows/security.yml`(Bandit·Trivy·pip-audit CVE) |
| 코드 리뷰 | PR 리뷰 + code-reviewer 어드바이저 반영(HIGH/MEDIUM/LOW) |
| 결함 관리 | GitHub Issue/PR + 회귀 테스트로 재발 방지(고정 시 재현 테스트 추가) |
| 프로세스 준수 | 본 4대 계획서 + RTM + 인증 적합성 게이트(301-319) 자가 점검 |
| 정직성 보증 | API Maturity 분류(production/beta/mock/speculative) · 기술부채 대장(`docs/TECH_DEBT_LEDGER.md`) — 미완·mock 을 숨기지 않음 |

---

## 적용 한계 (정직 공시)

- SDACS 는 **연구용 시뮬레이터**다. 본 계획서는 DO-178C 의 *형식과 의도*를 학습·정렬한 것으로, 실제 형식 인증(DER·SOI 심사)을 받은 것이 아니다.
- DAL-D 가정은 *교육 목적*이며, 안전-결정권은 항상 결정적 APF+CBS 5계층 안전망이 보유한다(ML 은 자문만).
- 갭 분석은 Phase 305 [`DO178C_GAP_ANALYSIS.md`](DO178C_GAP_ANALYSIS.md) 참조.

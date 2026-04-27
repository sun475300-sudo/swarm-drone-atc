# SDACS Master TODO — 통합 백로그 (2026-04-26)

> 최종 점검: 2026-04-26 (Phase 660 완료, Phase 691-720 미처리, 발표 종료)
> 출처: `ROADMAP.md`, `docs/AUDIT_2026-04-20.md`, `docs/TASK_LIST_2026-04-25.md`,
> `docs/_RESUME_STATUS_20260421.md`, 코드 grep, CI 로그, ops_report.

## 우선순위 정의

| Level | 의미 | 처리 시점 |
|-------|------|----------|
| **P0** | 회귀/CI 실패/시뮬 기동 차단 | 즉시 |
| **P1** | 실제 사용자/심사위원이 마주칠 가능성 | 4월 내 |
| **P2** | 품질·정합성 향상 | 5월 내 |
| **P3** | 장기 / Phase 711+ 로드맵 | 백로그 |

자동화 가능 표시: ✅ Claude 단독 가능 / ⚠️ 사용자 협조 필요 / ❌ 외부 의존(하드웨어·기관·승인)

---

## A0 — 회귀 / CI / 차단 이슈

| ID | 항목 | 출처 | P | 자동 | 변경 범위 | 상태 |
|----|------|------|---|------|----------|------|
| A0-01 | torch import OSError fallback | 본 세션 | P0 | ✅ | apf_engine, cbs_planner, voronoi_airspace, heatmap_generator (7파일) | **DONE** (commit 0d4dafa, c13f72d) |
| A0-02 | pyproject build-backend 오타 | CI run 24931567631 | P0 | ✅ | pyproject.toml 1라인 | **DONE** (commit a59fd48) |
| A0-03 | CI 재실행 후 녹색 확인 | 추후 | P0 | ✅ | — | 푸시 후 검증 필요 |

## A1 — 시뮬레이션 안정성 / 테스트 커버리지

| ID | 항목 | 출처 | P | 자동 | 변경 범위 |
|----|------|------|---|------|----------|
| A1-01 | apf_engine torch fallback 회귀 방지 테스트 추가 | 본 세션 | P1 | ✅ | tests/test_apf_engine_fallback.py (신규) |
| A1-02 | ops_report Traffic 섹션 RED 원인 조사 | data/e2e_reports/ops_report-seed42.md | P1 | ✅ | 분석만 |
| A1-03 | broad except 17건 점진 축소 (critical path 우선) | grep | P2 | ✅ | airspace_controller, voronoi_partition 등 |
| A1-04 | tests/test_e2e_quick.py:58 skip 가드 — config 존재 시 진짜 skip 발생 안 함 (확인 완료) | 백로그 audit | P3 | ✅ | 오탐, 작업 불필요 |
| A1-05 | pytest 수집 테스트 수 README와 동기화 (2,722+ → 3,330) | grep | P1 | ✅ | README.md 2곳 |
| A1-06 | scenarios `weather_disturbance` 등 60s smoke run | scenario list | P2 | ✅ | 결과만 기록 |

## A2 — 코드 품질 / 리팩터 / 문서

| ID | 항목 | 출처 | P | 자동 | 변경 범위 |
|----|------|------|---|------|----------|
| A2-01 | SECURITY.md 추가 | AUDIT G-03 | P1 | ✅ | 신규 1파일 |
| A2-02 | visualization/simulator_3d.py 1769 라인 분해 | wc -l | P2 | ⚠️ | 큰 변경, 별도 PR |
| A2-03 | simulation/simulator.py 861 라인 → drone agent 분리 | wc -l | P2 | ⚠️ | 큰 변경, 별도 PR |
| A2-04 | logger/print 혼용 정리 (활성 모듈만) | grep | P2 | ✅ | 소규모 |
| A2-05 | api/fastapi_server.py:250 TODO 처리 — wire to airspace_manager | grep TODO | P2 | ⚠️ | 필요 시 |
| A2-06 | src/hardware/onboard_bridge.py:162-175 TODO 3건 (MAVLink 핸들러 매핑) | grep TODO | P2 | ❌ | 실기 검증 필요 |
| A2-07 | chatbot/engine/llm_engine.py:28 NotImplementedError | grep | P3 | ⚠️ | vLLM 서비스 필요 |

## A3 — 사이트 / 배포 / 발견성

| ID | 항목 | 출처 | P | 자동 | 변경 범위 |
|----|------|------|---|------|----------|
| A3-01 | imgur 외부 의존 10건 → docs/images 로컬화 | README grep | P1 | ⚠️ | 이미지 다운로드 + 경로 교체 |
| A3-02 | docs/index.html 시크릿 창 재확인 | _RESUME_STATUS | P1 | ❌ | 사용자 작업 |
| A3-03 | sdacs-site-improved.zip Netlify Drop 업로드 | _RESUME_STATUS | P1 | ❌ | 사용자 작업 |
| A3-04 | favicon SVG 추가 (AUDIT A-03) | AUDIT A-03 | P2 | ✅ | docs/favicon.svg |
| A3-05 | docs/404.html 브랜디드 (AUDIT A-05) | AUDIT A-05 | P2 | ✅ | 신규 1파일 |
| A3-06 | OG cover 1200×630 PNG 생성 (AUDIT A-07) | AUDIT A-07 | P2 | ⚠️ | 디자인 도구 필요 |
| A3-07 | Search Console / Bing Webmaster 등록 | AUDIT A-12 | P3 | ❌ | 사용자 작업 |

## A4 — 가이드 / 문서 / 메타

| ID | 항목 | 출처 | P | 자동 | 변경 범위 |
|----|------|------|---|------|----------|
| A4-01 | MASTER_TODO_ATC.md 작성 | 본 세션 | P0 | ✅ | **DONE** (이 문서) |
| A4-02 | docs/REGRESSION_NOTES_2026-04-26.md (torch fallback + CI 픽스) | 본 세션 | P1 | ✅ | 신규 1파일 |
| A4-03 | CHANGELOG.md 업데이트 (이번 세션 변경) | git log | P1 | ✅ | 1파일 |
| A4-04 | CONTRIBUTING.md (AUDIT E-08) | AUDIT E-08 | P3 | ✅ | 신규 |
| A4-05 | docs/faq.md 캡스톤 Q&A (AUDIT E-06) | AUDIT E-06 | P2 | ✅ | 신규 |
| A4-06 | docs/roadmap_public.md (AUDIT E-07) | AUDIT E-07 | P2 | ✅ | 신규 |

---

## Phase 691~720 (장기 트랙)

| 트랙 | 범위 | 자동화 가능 비율 | 외부 의존 |
|------|------|-----------------|----------|
| **A. 하드웨어** (P691-P700) | 10작업 | 30% (스켈레톤·문서) | 하드웨어, 비행 허가, 시설 |
| **B. 논문** (P701-P710) | 10작업 | 70% (서베이·메트릭·도커) | 지도교수, 학회 일정 |
| **C. 배포** (P711-P720) | 10작업 | 80% (PoC·아키텍처) | 인프라, 파일럿 기관 |

전체 우선 트랙: **B(논문)** 부터 시작 권장 — 다음 모든 단계의 framing 결정.

---

## 즉시 실행 권장 (이번 세션 자동화)

| ID | 항목 | 예상 시간 |
|----|------|----------|
| A0-03 | CI 재실행 후 녹색 확인 (push 후) | 5분 |
| A1-01 | apf_engine fallback 회귀 방지 테스트 | 10분 |
| A1-05 | README 테스트 수 동기화 (2,722→3,330) | 2분 |
| A2-01 | SECURITY.md 추가 | 5분 |
| A4-02 | REGRESSION_NOTES_2026-04-26.md | 10분 |
| A4-03 | CHANGELOG 업데이트 | 5분 |

**총 예상: 약 40분**, 모두 별도 커밋, 단일 PR로 묶어서 제출.

---

## 다음 세션으로 미루는 항목

1. visualization/simulator_3d.py 분해 (큰 PR, 별도 검토)
2. simulator.py 드론 에이전트 분리 (큰 PR)
3. imgur → 로컬 자산 이전 (중규모, 이미지 다운로드 필요)
4. P701~P710 논문 트랙 (사용자 의사 결정 필요)

---

*Last updated: 2026-04-26 by Claude Opus 4.7 (1M context)*

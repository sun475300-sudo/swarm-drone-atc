# 🧭 SDACS Phase 200 이후 — 4가지 가능한 진행 방향

*Created: 2026-06-05 — Phase 200 (Unity) + 247 E2E 도달 직후*

## 트랙 ① — 캡스톤 보고서 자동 생성

졸업 심사용 PDF/DOCX 자동 빌드 파이프라인.

**산출물:**
- `scripts/generate_capstone_report.py` — 200 Phase 통계 + 시뮬 메트릭 자동 추출 → DOCX
- 표지 + 목차 + 1-12장 (서론·관련연구·아키텍처·구현·실험·결론) 자동 채움
- `docs/paper/SDACS_50_Phases_Results.tex` 통합

**예상 작업:** 2-3 PR (1주)

## 트랙 ② — IROS 2026 논문 §Discussion 자동 채우기

`docs/paper/latex/sections_4to7.tex`의 미완 §Discussion 자동 생성.

**산출물:**
- 200 Phase × 실험 결과 매트릭스 → §6 Discussion
- 5계층 안전망 robustness 정량 분석
- Phase 21 적대 ↔ Phase 27 C-UAS 통계 표
- 향후 연구 (Phase 201+ STELLAR 가능성)

**예상 작업:** 1 PR (3일)

## 트랙 ③ — 실 Pixhawk HITL 검증 (Phase 22 격상)

`src/digital_twin/sync_engine.py` 와 시뮬레이터 dtwin 통합.

**산출물:**
- Pixhawk SITL → WebSocket → `_sdacs.dtwinApplyGPI` 실시간 매핑
- HITL E2E 테스트 (10 Hz 텔레메트리, p99 < 100ms)
- `docs/hardware/pixhawk_sdacs_hitl.md` 단계별 가이드

**예상 작업:** 2 PR (2주, 실 HW 의존)

## 트랙 ④ — 라이브 베타 운영 (Phase 50 격상)

`docs/beta/README.md` 의 3 파일럿 기관 실 운영.

**산출물:**
- React MVP (`frontend/`) 완성 — PR #87 검토 후 머지
- Helm 차트 사내 K8s 배포 (`helm/sdacs/`)
- TimescaleDB 30일 보존 + Grafana 대시보드
- 3 파일럿 NPS 설문 자동 수집

**예상 작업:** 3-5 PR (1개월, 사용자 환경 의존)

---

## 즉시 실행 가능 (sandbox 내부에서)

- **트랙 ①** 캡스톤 보고서 — 100% sandbox 가능 (DOCX 생성 라이브러리만 필요)
- **트랙 ②** §Discussion — 100% sandbox 가능 (LaTeX 텍스트)
- 트랙 ③ — HW 필요
- 트랙 ④ — 사용자 환경 필요

**우선순위 추천:** 트랙 ② (논문 §Discussion) → 트랙 ① (보고서)

다음 사이클 진행 시 트랙 ②부터 시작 권장.

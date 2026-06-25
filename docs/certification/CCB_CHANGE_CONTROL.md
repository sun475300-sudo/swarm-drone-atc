# CCB 변경통제 적합성 (GENESIS Phase 318)

> SDACS 의 실제 변경 관리 절차가 형상관리 표준(ISO 10007 · DO-178C §7 SCM ·
> SCMP 변경통제)의 **변경통제위원회(CCB)** 요건을 어디까지 충족하는가를
> 결정적으로 자가 평가한다. 구현: [`simulation/change_control_board.py`](../../simulation/change_control_board.py),
> 테스트: [`tests/test_change_control_board.py`](../../tests/test_change_control_board.py) (27건 PASS).

## 현 판정: **부분 적합 (PARTIAL, 75.0%)**

핵심(critical) 기준 미충족은 0건이나, 전담 CCB 조직·형식 영향분석·긴급변경
절차가 없어 CONFORMANT(≥80%) 에는 미달 — **격상 없이 정직 공시**한다.

| 기준 | 심각도 | 상태 | 근거 산출물 |
|---|---|---|---|
| CCB-01 변경 요청(CR) 단일 채널 | critical | ✅ MET | GitHub PR/Issue + `CHANGELOG.md` |
| CCB-02 변경 영향 분석 | critical | 🟡 PARTIAL | `docs/certification/RTM_5LAYER_COVERAGE.md` (형식 IA 템플릿 미비) |
| CCB-03 검토·승인 권한 게이트 | critical | 🟡 PARTIAL | PR 리뷰/머지 (전담 CCB 역할·정족수·서명 부재) |
| CCB-04 베이스라인 형상 통제 | critical | ✅ MET | `.github/workflows/canonical_hash.yml` |
| CCB-05 변경 추적성 | critical | ✅ MET | RTM 5계층 (REQ↔DSN↔IMP↔VER) |
| CCB-06 변경 전 회귀 검증 게이트 | critical | ✅ MET | `.github/workflows/ci.yml` |
| CCB-07 긴급 변경 절차 | recommended | 🔴 GAP | (형식 절차 부재) |
| CCB-08 변경 이력·감사 로그 | recommended | ✅ MET | `CHANGELOG.md` + git |

## 정직성 결속

- `MET`/`PARTIAL` 기준은 **반드시 실재하는 증거 산출물**을 인용하며,
  테스트(`test_cited_evidence_all_exist`)가 디스크 실재를 강제한다 — 허위 충족 차단.
- `UNMET`(CCB-07) 은 증거를 인용하지 않는다(생성자가 강제).

## 보완 로드맵 (CONFORMANT 도달 경로)

1. **CCB-02/03**: CR 영향분석 템플릿 + 리뷰어 정족수(≥2)·승인 서명 기록 도입.
2. **CCB-07**: 긴급변경 절차(사후 승인·롤백 기준) 문서화.

## CLI

```bash
python -m simulation.change_control_board --matrix   # 기준별 판정
python -m simulation.change_control_board --report   # 종합 요약
python -m simulation.change_control_board --gaps     # 미충족·부분 기준
python -m simulation.change_control_board --json     # JSON 매니페스트
```

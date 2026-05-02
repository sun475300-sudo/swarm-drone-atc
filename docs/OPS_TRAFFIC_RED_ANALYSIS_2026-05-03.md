# A1-03 ops_report Traffic 섹션 RED — 원인 분석

**작성일**: 2026-05-03
**대상 파일**: `data/e2e_reports/ops_report-seed42.md`, `simulation/e2e_reporter.py`
**분류**: 분석 (시뮬 동작 기대치 명시), 코드 동작 변경 없음

## 증상

`ops_report-seed42.md` 가 전체 Status `GREEN` (Health 0.88) 임에도 traffic 섹션만 `RED`:

```
| Traffic Pressure | 1.0000 |
- Blockers: `traffic`
| traffic | `RED` |
```

## 평가 로직 위치

`simulation/e2e_reporter.py:317-318`:

```python
congestion = float(traffic.get("avg_congestion", 0.0))
traffic_state = "GREEN" if congestion < 0.5 else ("YELLOW" if congestion < 0.8 else "RED")
```

| 구간 | state |
|------|-------|
| `congestion < 0.5` | GREEN |
| `0.5 ≤ congestion < 0.8` | YELLOW |
| `congestion ≥ 0.8` | RED |

## 근본 원인

**시뮬레이션 시나리오 자체의 의도된 결과** — 회귀 / 버그 아님.

- `ops_report` 시나리오는 운영 보고서 산출용으로 **공역 포화 한계 검증**이 목적.
- seed=42 + 기본 ops_report 파라미터에서 평균 혼잡도 (`avg_congestion`) 가 **1.0** (100% 포화) 으로 설정됨.
- 평가 임계 (0.8) 가 정상 작동해서 `RED` 표시.
- Health Score 는 `traffic_penalty = min(0.12, congestion * 0.12)` 만큼 감점되어 0.88 (12% 감점). 전체 보고서 Status 는 `GREEN` 유지 — 의도된 다층 게이팅.

## 왜 즉시 수정이 부적절한가

세 가지 옵션을 검토:

| 옵션 | 변경 | 위험 |
|------|------|------|
| A. 임계 완화 (0.8 → 0.95) | `e2e_reporter.py:318` | 100% 포화도 GREEN 표시 — 운영자가 위험 신호 놓침 |
| B. 시나리오 파라미터 완화 (drone 수↓ / area↑) | `config/scenario_params/ops_report.yaml` | ops_report 시나리오의 본래 목적 (포화 한계 검증) 훼손 |
| C. avg_congestion 계산 정규화 변경 | `simulation/scenario_runner.py` | 모든 시나리오에 영향, 회귀 위험 큼 |

→ **현 상태는 의도된 동작**. 사용자 / 운영자에게 *"100% 포화 ≈ traffic RED"* 신호가 정확히 전달되는 것이 안전한 보고 시스템의 본질.

## 본 PR 변경 사항 (코드 동작 0)

1. **`simulation/e2e_reporter.py`**: 임계 라인에 단계별 명시 주석 추가 — 미래 수정자가 의도를 즉시 이해할 수 있도록.
2. **`tests/test_e2e_reporter_traffic_thresholds.py` (신규)**: 0.5 / 0.8 경계 회귀 테스트 4건. 임계가 무심코 바뀌면 즉시 잡힘.
3. 본 분석 문서 — RED 발견 시 첫 참조 자료.

## 운영자 가이드

`ops_report` Status 가 `RED` (Section traffic) 일 때:

| Health Score | 권장 조치 |
|--------------|----------|
| ≥ 0.85 | **정상** — 시뮬이 한계 검증 중. 시나리오 의도된 동작. |
| 0.70 ~ 0.85 | **모니터링** — 다른 KPI 와 결합 분석 (success_rate, violations) |
| < 0.70 | **개입 필요** — 시뮬 파라미터 / 시드 / 시나리오 재검토 |

## 후속 (별도 PR / 별도 사이클)

- 시나리오별 임계 차등 (`ops_report` 만 0.95, 일반 시나리오 0.8) — 사용자 결정 필요
- `avg_congestion` 정의 문서 (시간 가중 vs 공간 가중) — `docs/architecture.md` 보강
- 100% 포화 도달 시점·지속 시간 추적 — 새 KPI

---

*Last updated: 2026-05-03.* 본 분석으로 ops_report-seed42.md의 traffic RED 는 **회귀 아님 / 의도된 동작** 으로 결론. 코드 임계 변경 보류.

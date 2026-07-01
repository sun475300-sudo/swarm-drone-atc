# 연 1회 건전성 리허설 케이던스 정책 (ODYSSEY Phase 486)

> 10년 지속 가능성(Continuum 트랙). 신규 컨테이너 독립 재현 하니스
> (`scripts/independent_reproduction.sh`)가 *언제 다시 필요한가* 와 *온전한가*
> 를 결정적 정책으로 명문화한다. 본 문서는 규칙을 **서술**할 뿐, 유일한 실행
> 가능 명세는 `simulation/rehearsal_cadence.py` 다(중복 로직 없음 — 테스트가
> 일치 강제).

## 위치

- 정책 엔진: [`simulation/rehearsal_cadence.py`](../../simulation/rehearsal_cadence.py)
- 테스트: [`tests/test_rehearsal_cadence.py`](../../tests/test_rehearsal_cadence.py)
- 리허설 하니스: [`scripts/independent_reproduction.sh`](../../scripts/independent_reproduction.sh)
- 위임: [`simulation/legacy_readiness.py`](../../simulation/legacy_readiness.py) (Phase 490 — 디지털 유산 체크리스트의 재현성 차원)

## 배경 — 왜 연 1회 리허설인가

졸업 후 10년, 손이 뜸해진 뒤에도 프로젝트가 *신규 컨테이너에서 그대로 재현
되는가* 는 시간이 지나며 조용히 깨진다(상류 패키지 삭제·OS 베이스 이미지
변경·툴체인 표류). 적어도 1년에 한 번은 깨끗한 환경에서 독립 재현을 돌려
녹색 기준선을 갱신해야 한다. 본 정책은 그 리허설이 *언제 다시 필요한가* 를
사람의 직관 대신 결정적으로 판정한다.

## 자문이지 집행 아님

본 정책은 리허설을 **권고**할 뿐, 스크립트를 실행하거나 빌드를 막지
않는다(부수효과 0). 사람/CI 가 실제 `independent_reproduction.sh` 를 돌린다.
같은 (마지막 리허설 기록, 기준일, 하니스 상태) 는 항상 같은 권고를 낸다
(무작위성 0).

## 입력

| 필드 | 의미 |
|---|---|
| `record.last_run` | 마지막 리허설 실행일 (없으면 `None`) |
| `record.result` | `PASS`(녹색 기준선) 또는 그 외(실패 — 기준선 미확립) |
| `today` | 평가 기준일 |
| `harness_intact` | 리허설 하니스 4개 자산이 모두 실재하는가 |

## 케이던스 (연 1회)

| 상수 | 값 | 의미 |
|---|:-:|---|
| `ANNUAL_INTERVAL_DAYS` | 365 | 리허설 만기 주기 |
| `DUE_SOON_LEAD_DAYS` | 30 | 만기 전 예고 창 |
| `OVERDUE_GRACE_DAYS` | 30 | 만기 후 유예(이후 OVERDUE) |

## 케이던스 등급 · 권고 (PASS + 하니스 온전 가정)

| 경과일 | 등급 | 권고 | 의미 |
|:-:|---|---|---|
| `< 335` | `CURRENT` | `WITHIN_CADENCE` | 케이던스 내부 — 조치 불필요 |
| `335 ~ 364` | `DUE_SOON` | `SCHEDULE` | 만기 임박 — 리허설 일정 예약 |
| `365 ~ 394` | `DUE` | `RUN_NOW` | 만기 도래(유예 내) — 리허설 실행 |
| `≥ 395` | `OVERDUE` | `RUN_NOW` | 만기 + 유예 초과 — 즉시 실행 |

## 권고 우선순위 (`assess`)

1. **하니스 손상** → `REVIEW` — 재현 불가, 케이던스보다 하니스(스크립트/락/
   컨테이너) 복구가 먼저.
2. **기록 없음** → `RUN_NOW` (`NEVER_RUN`) — 녹색 기준선 미수립.
3. **미래 날짜**(경과 음수) → `REVIEW` — 시계/데이터 이상.
4. **마지막 결과 비-PASS** → `RUN_NOW` — 시간과 무관하게 녹색 기준선 미확립.
5. 그 외 → 케이던스 등급에 따른 시간 전용 권고(위 표).

## 리허설 하니스 (무결성)

다음 4개 자산이 모두 실재해야 하니스 온전(INTACT):

- `scripts/independent_reproduction.sh` — 신규 컨테이너 독립 재현 스크립트
- `Dockerfile.reproducible` — 재현 컨테이너
- `requirements.lock.txt` — 의존성 핀 락
- `docs/REPRODUCIBILITY.md` — 재현 절차 문서

## 마지막 리허설 스냅샷 (정직성)

리포에 기계가 읽을 리허설 로그가 없으므로 마지막 *실제* 리허설은 수동 스냅샷
상수(`LAST_REHEARSAL_DATE` / `LAST_REHEARSAL_RESULT`)로 둔다 — 일일 점검의
독립 재현이 곧 리허설이며, 그 최신 실측을 있는 그대로 기록한다(갱신 시 날짜·
결과를 함께 고친다). 일일 점검이 연 1회보다 훨씬 잦으므로 현 판정은
`WITHIN_CADENCE` 이며, 이는 케이던스를 포장한 것이 아니라 실제 리허설 빈도를
정직히 반영한 것이다.

## CLI

```bash
python -m simulation.rehearsal_cadence --policy    # 케이던스 매트릭스
python -m simulation.rehearsal_cadence --status    # 리포 현 상태 판정
python -m simulation.rehearsal_cadence --demo      # 예시 평가
python -m simulation.rehearsal_cadence --manifest  # 정책 매니페스트(JSON)
```

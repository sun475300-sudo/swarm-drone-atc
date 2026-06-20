# 유지보수자 승계 규약 — BDFL → 위원회 거버넌스 정책

> ODYSSEY Phase 487 (Continuum 트랙). 실행 가능 명세: [`simulation/governance_succession.py`](../../simulation/governance_succession.py)

## 목적

졸업 후 10년, 프로젝트가 **원저자 한 사람에게 묶여** 있으면 그 한 사람이
손을 떼는 순간(졸업·이직·사고) 머지·릴리스·보안 대응이 전부 멈춘다(bus
factor 1). "현재 거버넌스가 원저자(BDFL)를 넘어 위원회로 승계될 준비가
됐는가"를 매번 직관으로 판단하면 일관성이 없다. 본 정책은 그 판단을
**결정적 규칙**으로 명문화한다.

이 문서는 규칙을 *서술*할 뿐이며, **유일한 권위 있는 명세는
`simulation/governance_succession.py` 의 `assess_succession()`** 다. 본 문서와
코드가 어긋나면 코드가 옳고, 테스트(`tests/test_governance_succession.py`)가
둘의 일치를 강제한다.

## 핵심 원칙

1. **자문이지 집행이 아님** — 본 모듈은 *현 상태를 판정*할 뿐 실제로
   유지보수자를 임명하거나 권한을 부여하지 않는다(부수효과 0). 실제 승계는
   사람/조직이 집행한다.
2. **연속성 보유자만 센다(bus factor)** — 머지 권한과 관리자(admin) 접근을
   *둘 다* 가진 활성 유지보수자만 "그 한 사람이 사라져도 프로젝트를
   독립적으로 이어갈 수 있는 사람"으로 집계한다. 이름만 올린 기여자·권한
   없는 명예(emeritus) 유지보수자는 연속성에 기여하지 않는다(정직성).
3. **문서가 사람을 대체하지 않음** — 연속성 보유자가 1인이면 승계 문서가
   아무리 완비돼도 그 한 사람이 사라지면 멈추므로 `BUS_FACTOR_RISK` 다.
4. **위원회 우선** — 단일 BDFL 은 한 사람의 사정으로 전체가 멈추는 단일
   실패점이다. 승계 준비 완료(`COMMITTEE_READY`)는 *서로 다른* 연속성 보유자
   최소 3인(투표·교착 해소 가능) + 승계 거버넌스 문서 완비를 요구한다.

## 유지보수자 역할

| 역할 | 의미 | 연속성 기여 |
|---|---|---|
| `principal` | 원저자/주 유지보수자(BDFL 자리) | 권한 충족 시 집계 |
| `co_maintainer` | 공동 유지보수자(동등 권한) | 권한 충족 시 집계 |
| `reserve` | 지명된 승계 후보(권한 일부) | 보통 admin 없음 → 미집계 |
| `emeritus` | 명예(은퇴) — 권한 없음 | 미집계 |

연속성 보유자 = **활성** AND **머지 권한** AND **관리자 접근**. 셋 중
하나라도 빠지면(예: 머지 권한만 있고 키·계정 복구 admin 이 없으면) 릴리스·키
관리를 단독 수행할 수 없으므로 연속성 보유자가 아니다.

## 거버넌스 단계(현 구조 서술)

| 연속성 보유자 | 단계 | 의미 |
|---|---|---|
| 0 | `ABANDONED` | 머지·릴리스·보안 대응 주체 없음(방치) |
| 1 | `BDFL` | 단일 실패점 |
| 2 | `DUAL_CONTROL` | 이중 통제 — 교착 해소 불가 |
| ≥3 | `COMMITTEE` | 위원회 가능(투표·교착 해소) |

## 판정 매트릭스

| 연속성 보유자 | 문서 완비 | 판정 |
|---|:---:|---|
| 0 | — | `ABANDONED` |
| 1 | — | `BUS_FACTOR_RISK` |
| 2 | False/True | `TRANSITIONAL` |
| ≥3 | False | `TRANSITIONAL` |
| ≥3 | True | `COMMITTEE_READY` |

`COMMITTEE_READY` 조건: 연속성 보유자 ≥3인 + 승계 거버넌스 문서 완비.

## 승계 거버넌스 문서

`--status` 가 디스크 실재를 검증하는 문서:

- `docs/standards/MAINTAINER_SUCCESSION_PROTOCOL.md` (본 문서 — 승계 절차)
- `CONTRIBUTING.md` (기여·머지 절차)
- `SECURITY.md` (보안 대응 책임)

## 현 상태 정직 공시

본 프로젝트는 목포대학교 캡스톤으로 **원저자 1인이 머지·릴리스·관리자
접근을 단독 보유**한다(BDFL). 공동 유지보수자·지명 승계 후보가 아직 없어
연속성 보유자는 1인이며, 따라서 정직한 현 판정은 **`BUS_FACTOR_RISK`** 다.

```
$ python -m simulation.governance_succession --status
판정: BUS_FACTOR_RISK: 연속성 보유자 1인(principal-maintainer) — 단일 실패점(bus factor 1)
```

문서가 완비돼도(본 Phase 로 문서는 완비) 1인 구조이므로 판정은 바뀌지
않는다 — 문서가 사람을 대체하지 않기 때문이다. 둘째 연속성 보유자가
추가되면 회귀 핀(`shipped_maintainers` 1인 가정)이 *의도적으로* 깨져 본 명단·
로드맵 갱신을 강제한다.

## 승계 로드맵(자문)

`BUS_FACTOR_RISK → COMMITTEE_READY` 로 가려면:

1. **공동 유지보수자 2인 확보** — 머지 권한 + 관리자 접근(리포·PyPI/npm
   레지스트리·도메인) 부여. (`BDFL → COMMITTEE` 정족 충족)
2. **의사결정 절차 문서화** — 합의·투표·교착 해소 규칙(`CONTRIBUTING.md` 확장).
3. **자격증명 인벤토리** — 누가 어떤 키·계정·도메인을 보유하는지 명문화
   (`SECURITY.md` 연계).

## CLI

```bash
python -m simulation.governance_succession --policy     # 정책 매트릭스
python -m simulation.governance_succession --demo       # 예시 평가
python -m simulation.governance_succession --status     # 리포 현 상태 판정
python -m simulation.governance_succession --manifest   # 정책 매니페스트(JSON)
```

# Centennial 선언 정책 (ODYSSEY Phase 500)

> 본 문서는 규칙을 **서술**할 뿐이다. 유일한 권위 있는 실행 명세는
> [`simulation/centennial_declaration.py`](../../simulation/centennial_declaration.py)
> 이며, 테스트가 문서 ↔ 코드 일치를 강제한다. 본 문서와 코드가 어긋나면
> **코드가 정본**이다.

## 1. 목적

Continuum 트랙(Phase 481-500)의 *마지막 칸*이자 전체 500-Phase 프로그램의
종착 선언이다. "이 프로젝트는 원저자·현 세대를 넘어 **100년 단위**로 살아남을
준비가 되었는가"를 사람이 매번 직관으로 선언하지 않도록 **결정적 종합
게이트**로 명문화한다 — 같은 리포 상태는 항상 같은 판정을 낸다.

Centennial 선언은 *새 판정 기준을 발명하지 않는다*. 100년 생존은 이미 결정적
정책으로 명문화된 네 기둥의 **합**이며, 본 게이트는 그 기둥들을 *호출만* 한다
(DRY — 판정 로직 복제 0).

## 2. 네 기둥 (Pillars)

| 기둥 | 위임 Phase | 충족 조건(자매 게이트 종착 상태) |
|---|---|---|
| `legacy_readiness` | 490 | `assess_legacy_readiness` → **READY** |
| `archive_durability` | 489 | `assess_redundancy` → **REDUNDANT** |
| `governance_succession` | 487 | `assess_succession` → **COMMITTEE_READY** |
| `generational_handover` | 492 | `select_track` → **HANDOFF_READY** (491 공모 → 492 선정 파이프라인의 종착) |

각 기둥의 판정 규칙은 해당 자매 모듈에 **한 번씩만** 적혀 있다. 본 모듈은
그 게이트의 결과(`is_ready()`/`is_durable()`/`is_handoff_ready()`)만 읽는다.

## 3. 판정 규칙 (all-or-nothing)

Centennial 선언은 *마일스톤*이다. 네 기둥은 모두 100년 생존의 **필요조건**
이므로:

- **DECLARED** — 네 기둥 *전부* 충족.
- **NOT_DECLARED** — 한 기둥이라도 미충족.

진척(`progress`)은 `충족 기둥 수 / 4`(소수 넷째 자리 반올림)로 **정직한
공시용일 뿐 선언을 앞당기지 않는다**. 75% 도 NOT_DECLARED 다.

## 4. 정직 공시 (현 리포 상태)

`python -m simulation.centennial_declaration --status` 실측:

```
  MISS legacy_readiness        UNMET   Phase 490 → NOT_READY
  MISS archive_durability      UNMET   Phase 489 → AT_RISK
  MISS governance_succession   UNMET   Phase 487 → BUS_FACTOR_RISK
  MISS generational_handover   UNMET   Phase 492 → AWAITING_PROPOSALS

판정: NOT_DECLARED (0.0%): 미충족 기둥 4/4
```

현 리포는 네 기둥 모두 미충족이다 — 이는 *실패가 아니라 정직*이다. 100년
선언의 잔여 조건이 무엇인지(LICENSE 전문·DOI 발급·위원회 승계·2027+ 차세대
기수 형성)를 그대로 드러낸다. 어느 기둥이 채워지면 자매 모듈의 회귀 핀이
*의도적으로* 깨져 본 선언 갱신을 강제한다.

## 5. 설계 불변식

- **종합이지 재정의 아님(DRY)**: 자매 게이트 판정 로직 복제 0.
- **자문이지 집행 아님**: 현 상태를 *판정*할 뿐 누락 자산을 만들지 않는다
  (부수효과 0).
- **결정적**: 무작위성 0 — 같은 입력은 항상 같은 판정.
- **순수 추가**: 기존 파일 무수정.

## 6. CLI

```bash
python -m simulation.centennial_declaration --pillars    # 기둥 매트릭스
python -m simulation.centennial_declaration --status     # 리포 현 선언 판정
python -m simulation.centennial_declaration --manifest   # 매니페스트(JSON)
```

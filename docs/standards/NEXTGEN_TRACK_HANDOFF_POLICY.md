# 차세대 트랙 공모·선정 정책

> ODYSSEY Phase 492 (Continuum 트랙). 실행 가능 명세: [`simulation/track_handoff_readiness.py`](../../simulation/track_handoff_readiness.py)
>
> **선행 단계:** [Phase 491 세대 이양 검토 게이트](GENERATIONAL_HANDOVER_POLICY.md)가
> *개별 제안의 이양 수용 가능성*(ACCEPT/REVISE/DEFER/REJECT)을 판정한다면, 본
> Phase 492 는 그 다음 단계인 *공모 전체에서 적격 제안을 가려 하나를 선정* 하는
> 문제를 다룬다(독립 기준: 491 = 수용 가능성, 492 = 적격 제안 간 우선순위).

## 목적

로드맵은 Continuum 트랙의 Phase 491-499 를 **차세대(2027+ 기수) 주도 신규
트랙 공모·선정·이양**으로, Phase 500 을 Centennial 선언으로 비워 두었다.
원저자가 손을 뗀 뒤 프로젝트가 한 세대를 넘어 이어지려면, 다음 기수가 *스스로
주도할 신규 트랙*을 공모받아 적격한 것을 선정해 이양해야 한다. "이 제안이
이양 대상으로 적격한가, 적격 제안 중 무엇을 고를 것인가"를 매번 직관으로
판단하면 일관성이 없다. 본 정책은 그 판단을 **결정적 규칙**으로 명문화한다 —
같은 입력은 항상 같은 판정·선정을 낸다.

이 문서는 규칙을 *서술*할 뿐이며, **유일한 권위 있는 명세는
`simulation/track_handoff_readiness.py`** 다. 본 문서와 코드가 어긋나면 코드가
옳고, 테스트(`tests/test_track_handoff_readiness.py`)가 둘의 일치를 강제한다.

## 핵심 원칙

1. **자문이지 집행이 아님** — 본 모듈은 *제안의 적격성을 판정*하고 *선정
   후보를 지목*할 뿐, 트랙을 개설하거나 권한을 이양하지 않는다(부수효과 0).
   실제 이양은 사람/위원회가 집행한다.
2. **이양의 핵심은 독립성** — 차세대 트랙은 *원저자 없이 차세대 기수가 독립
   추진*할 수 있어야 한다. 원저자에게 다시 묶이는 제안은 이양이 아니라
   위임이므로 필수 기준 미충족이다([Phase 487 bus factor](MAINTAINER_SUCCESSION_PROTOCOL.md)
   정직성과 정합).
3. **목표 주도** — 적격 제안은 트랙 헌장(스코프)과 *검증 가능한 성공 기준*을
   둘 다 갖춰야 한다([`CLAUDE.md` §4](../../CLAUDE.md)). "되게 해줘" 류 약한
   기준은 공모 보완 대상(`NEEDS_WORK`)이다.
4. **트랙 규모** — 이양 대상은 단일 기여가 아니라 한 블록(최소 10 Phase)을
   계획해야 한다. 기존 트랙 블록(예: 481-490, 421-440)의 10 Phase 케이던스와
   정합.
5. **선정 동률은 안정 해시로 분리** — 적격 제안이 복수면 *부가 강점*(멘토
   약속·재원 식별) 점수로 우선하고, 동점은 `sha256(proposal_id)` 안정 해시로
   분리한다([Phase 424 연합 충돌 협상](../../simulation/federation_conflict_resolution.py)과
   동일 idiom — 무작위성 0).

## 제안 적격 판정 (SSoT)

각 제안은 `(주체 지정, 범위 버킷, 필수 기준 완비)` 세 축으로 판정된다.

| 축 | 의미 |
|---|---|
| `has_champion` | 트랙을 주도할 차세대 기수 책임자 핸들 지정(빈/공백 = 미지정) |
| `scope` | 계획 Phase 규모 — `none`(≤0)·`small`(1..9)·`track`(≥10) |
| `musts_complete` | 헌장 · 검증 가능한 성공 기준 · 원저자 독립성 · 선행 의존성 *전부* |

### 정책 매트릭스

| has_champion | scope | musts_complete | 판정 |
|:-:|:-:|:-:|:-:|
| False | (any) | (any) | `REJECTED` |
| True | `none` | (any) | `REJECTED` |
| True | `small` | (any) | `NEEDS_WORK` |
| True | `track` | False | `NEEDS_WORK` |
| True | `track` | True | `ELIGIBLE` |

- `REJECTED` — 주체가 없거나 범위가 없어 공모 자체가 성립하지 않는다.
- `NEEDS_WORK` — 주체·범위는 있으나 트랙 규모 미달이거나 필수 기준 미충족 —
  공모 보완 대상.
- `ELIGIBLE` — 모든 필수 기준 완비 — 선정 후보.

## 선정 (공모 전체)

`select_track(proposals)` 는 접수 제안을 다음 결정적 규칙으로 처리한다.

| 코호트 판정 | 조건 |
|---|---|
| `AWAITING_PROPOSALS` | 접수 제안 0 — 공모 대기 |
| `NO_ELIGIBLE` | 제안은 있으나 적격(`ELIGIBLE`) 0 — 전부 보완·결격 |
| `HANDOFF_READY` | 적격 제안 ≥1 — 부가 강점 점수 최고를 선정(동점은 안정 해시) |

부가 강점 점수 = `mentor_committed`(멘토 지속 약속) + `funding_identified`(재원
식별), 0..2. 이는 필수 기준이 아니라, 동등하게 적격인 제안 중 *무엇을 먼저
선정할지*만 가른다.

## 현 리포 상태 (정직 공시)

본 프로젝트는 목포대 캡스톤으로 아직 차세대(2027+ 기수)가 형성되지 않았고,
이양 대상 신규 트랙 제안이 접수된 바 없다 → **`AWAITING_PROPOSALS`**. 공모를
"준비됨"으로 포장하지 않는다(Phase 487/490 자매 패턴). 실제 차세대 제안이
접수되면 회귀 핀(`test_shipped_pin_breaks_when_proposal_added`)이 *의도적으로*
깨져 로드맵·`shipped_proposals()` 갱신을 강제한다.

```bash
python -m simulation.track_handoff_readiness --policy     # 정책 매트릭스
python -m simulation.track_handoff_readiness --demo       # 예시 공모·선정
python -m simulation.track_handoff_readiness --status     # 리포 현 상태 판정
python -m simulation.track_handoff_readiness --manifest   # 정책 매니페스트(JSON)
```

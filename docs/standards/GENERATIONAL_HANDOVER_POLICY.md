# 세대 이양 검토 게이트 정책 (Generational Handover Review Gate)

> ODYSSEY Phase 491 · Continuum 트랙(481-500) · 10년 지속 가능성
>
> **실행 가능 명세(SSoT):** [`simulation/track_handover_policy.py`](../../simulation/track_handover_policy.py)
> — 본 문서는 규칙을 *서술* 할 뿐이며, 판정은 항상 모듈의 `assess_handover()` 가
> 내린다(테스트가 `POLICY_MATRIX` ↔ `assess` 일치를 강제).

## 배경

ODYSSEY 거버넌스 게이트 **#4** 는 다음과 같이 규정한다:

> **세대 이양:** Phase 491+ 신규 트랙은 *차세대(2027+ 기수) 주도*, 현 세대는
> *리뷰만* 한다.

즉 현 세대(원저자)는 새 트랙을 직접 만들지 않는다. 차세대 기수가 신규 트랙
제안을 제출하면, 현 세대는 그 제안을 **이양해도 되는가** 만 검토한다. 본 정책은
그 검토 판단을 사람이 매번 직관으로 내리지 않도록 *결정적 규칙* 으로 명문화한다.

## 판정(Verdict)

| 판정 | 의미 | 후속 조치 |
|---|---|---|
| **ACCEPT** | 차세대 주도 트랙 이양 수용 | 트랙 등록·로드맵 편입 |
| **REVISE** | 고칠 수 있는 결함(헌장·범위·sandbox) | 제안 보완 후 재제출 |
| **DEFER** | 현 세대 리뷰 미완(게이트 #4 절차) | 현 세대 리뷰 진행 |
| **REJECT** | 차세대 소유자 부재(구조적 결격) | 소유자 확보 전 반려 |

## 판정 규칙 (우선순위)

서로소 단계로, 위에서부터 먼저 맞는 단계가 판정을 결정한다:

1. **차세대 소유자 부재 → REJECT.** 연속성 보유 의지를 가진 2027+ 기수
   소유자가 없으면, 그 트랙은 현 세대가 떠안아야만 굴러간다 — 세대 이양의
   *정의 자체* 에 어긋난다. 헌장이 아무리 좋아도 소유자가 사람을 대체하지
   못한다(정직성). 리뷰·헌장 충족과 무관하게 우선 반려.
2. **현 세대 리뷰 미완 → DEFER.** 게이트 #4 의 절차로, 리뷰가 끝나기 전에는
   어떤 긍정 판정도 내리지 않는다. (단, 미검토 단계에서도 눈에 보이는 보완
   사항은 미리 표면화해 재제출 비용을 줄인다.)
3. **보완형 결함 → REVISE.** 다음 중 하나라도 미충족이면 보완 요청:
   - **헌장 부재** — 범위·목표·산출물·종료 기준이 명문화되지 않음.
   - **기존 트랙과 범위 중복** — 아래 5개 기존 트랙과 본질적으로 같은 범위.
   - **sandbox 재현 미검증** — 외부 HW/비밀키 없이 재현 가능함이 확인되지 않음.
4. **그 외 → ACCEPT.**

## 정책 매트릭스

`(차세대 소유자, 리뷰 완료, 결함 없음)` → 판정. (`결함 없음 = is_clean`)

| 소유자 | 리뷰 | 결함없음 | 판정 |
|:-:|:-:|:-:|---|
| ✗ | – | – | REJECT |
| ✓ | ✗ | – | DEFER |
| ✓ | ✓ | ✗ | REVISE |
| ✓ | ✓ | ✓ | ACCEPT |

(`–` = 해당 단계에서 판정에 영향을 주지 않음. 전수 8칸은 모듈
`POLICY_MATRIX` 와 테스트에서 확인.)

## 범위 중복 기준 — 기존 ODYSSEY 트랙

신규 제안이 다음 5개 트랙과 본질적으로 같은 범위면 중복으로 본다:

| 아이콘 | 트랙 | Phase |
|:-:|---|---|
| 🌏 | Global Expansion | 401-420 |
| 🛰 | Federation Operations | 421-440 |
| 🔬 | Formal & Research Frontier | 441-460 |
| 🏛 | Standards & Policy | 461-480 |
| ♾️ | Continuum | 481-500 |

## 현 리포 상태 (정직 공시)

2027+ 차세대 기수가 아직 형성되지 않아 **등록된 신규 트랙 제안은 0건**이다.
프로그램 상태는 `AWAITING_PROPOSALS`. 첫 제안이 등록되면 `shipped_proposals()`
회귀 핀이 *의도적으로* 깨져 본 문서·로드맵 갱신을 강제한다.

```bash
python -m simulation.track_handover_policy --policy     # 정책 매트릭스
python -m simulation.track_handover_policy --demo       # 예시 4판정
python -m simulation.track_handover_policy --status     # 현 상태(AWAITING_PROPOSALS)
python -m simulation.track_handover_policy --manifest   # JSON 매니페스트
```

## 자문이지 집행 아님

본 모듈은 제안의 이양 준비 상태를 *판정* 할 뿐, 실제로 트랙을 등록하거나 권한을
이양하지 않는다(부수효과 0). 실제 이양은 사람/위원회(Phase 487 승계 규약)가
집행한다.

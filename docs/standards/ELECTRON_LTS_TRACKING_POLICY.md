# Electron LTS 추적 정책 (ODYSSEY Phase 484)

> 10년 지속 가능성(Continuum 트랙). 데스크탑 앱이 의존하는 Electron 런타임이
> *언제 보안 지원 창을 벗어나는가* 를 결정적 정책으로 명문화한다. 본 문서는
> 규칙을 **서술**할 뿐, 유일한 실행 가능 명세는
> `simulation/electron_lts_policy.py` 다(중복 로직 없음 — 테스트가 일치 강제).

## 위치

- 정책 엔진: [`simulation/electron_lts_policy.py`](../../simulation/electron_lts_policy.py)
- 테스트: [`tests/test_electron_lts_policy.py`](../../tests/test_electron_lts_policy.py)
- 핀 출처: [`package.json`](../../package.json) (`devDependencies.electron`)
- 자매 정책: [`simulation/dependency_gate.py`](../../simulation/dependency_gate.py) (Phase 481 — 의존성 자동 머지)

## 배경 — Electron 지원 정책

Electron 은 상류 공시상 **최신 3개 stable major** 에만 보안 패치를 백포트하며,
약 **8주** 주기로 새 major 를 출시한다(Chromium 케이던스 정렬). 즉 핀이 최신
대비 3 major 이상 뒤처지면 *보안 백포트가 끊긴* 런타임으로 배포된다.

## 자문이지 집행 아님

본 정책은 업그레이드를 **권고**할 뿐, 핀을 실제로 올리거나 빌드를 막지
않는다(부수효과 0). 사람/CI 가 결정을 집행한다. 같은 입력은 항상 같은 결정을
낸다(무작위성 0).

## 입력

| 필드 | 의미 |
|---|---|
| `pinned_major` | 리포가 고정한 Electron major (`package.json` 핀에서 파싱) |
| `latest_stable_major` | 상류 최신 stable major (수동 스냅샷 상수) |

`lag = latest_stable_major − pinned_major`.

## 지원 등급 · 권고 (window = 3)

| lag | 등급 | 권고 | 의미 |
|:-:|---|---|---|
| `< 0` | `AHEAD` | `REVIEW` | 핀이 스냅샷보다 앞섬 — 스냅샷 stale/프리릴리스 확인 |
| `0` | `CURRENT` | `WITHIN_SLA` | 최신 stable |
| `1` | `SUPPORTED` | `WITHIN_SLA` | 지원 창 내부 |
| `2` | `ENDING` | `PLAN_UPGRADE` | 창의 마지막 칸 — 다음 상류 major 출시 시 EOL |
| `≥ 3` | `EOL` | `UPGRADE_NOW` | 지원 창 밖 — 보안 백포트 종료 |

경계는 `SUPPORT_WINDOW_MAJORS` 값과 무관하게 명확하다(`ENDING` 을 `EOL`
*앞에서* 검사).

## 상류 최신 스냅샷 (정직성)

리포에는 상류 릴리스 캘린더가 없으므로 최신 major 는 *수동 스냅샷 상수* 로
둔다. 이를 최신으로 *포장*하지 않고 날짜를 함께 명시한다.

- `OBSERVED_LATEST_STABLE_MAJOR = 42` (`OBSERVED_LATEST_AS_OF = 2026-06-19`)
- 근거: 리포 Dependabot PR #277 이 electron `39 → 42` 를 제안 중 = 상류가 42 를
  내놓았다는 실측 증거.

상류가 새 major 를 내면 본 상수와 날짜를 함께 갱신한다.

## 정직 공시 (현 상태)

`python -m simulation.electron_lts_policy --status` 판정 **`UPGRADE_NOW (EOL, lag=3)`**:

- 현 핀 `^39.8.5`(major 39) 은 스냅샷 최신 42 대비 3 major 뒤 → 지원 창(3) 밖.
- 즉 현재 데스크탑 빌드 타깃은 **보안 백포트가 끊긴 EOL 런타임**이다.
- 적체 Dependabot PR #277(`electron 39 → 42`)을 회귀 게이트(Phase 481) 통과
  확인 후 머지하면 `CURRENT` 로 복귀한다.

### 교훈 — 32 → 39 표류

v1.5.0 데스크탑 빌드는 Electron 32 로 동결되었고, 핀은 그 뒤 39 로 점프했다.
32 는 39 출시 시점에 이미 *7 major* 뒤(`assess(ElectronRuntime(32, 39))` →
`EOL, lag=7`)였다 — 지원 창의 두 배 이상으로, 오랜 기간 EOL 런타임으로
빌드된 셈이다. 본 정책은 그 표류가 *조용히* 일어나지 않도록, 핀이 창 끝에
닿는 순간(`ENDING`) `PLAN_UPGRADE`, 창을 벗어나면(`EOL`) `UPGRADE_NOW` 를
결정적으로 권고한다.

## CLI

```bash
python -m simulation.electron_lts_policy --policy    # 정책 매트릭스
python -m simulation.electron_lts_policy --status    # 리포 핀 실측 판정
python -m simulation.electron_lts_policy --demo      # 예시 평가
python -m simulation.electron_lts_policy --manifest  # 정책 매니페스트(JSON)
```

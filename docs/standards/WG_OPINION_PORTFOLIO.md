# 국제 워킹그룹 의견서 포트폴리오 추적기 (ODYSSEY Phase 473)

> Standards & Policy 트랙(Phase 461-480) · 밴드 471-480("국내 KS 제안 1건 +
> **국제 워킹그룹 의견서 3건**")의 *국제 의견서 3건* 목표 추적 칸.
> 실행 가능 명세: [`simulation/wg_opinion_portfolio.py`](../../simulation/wg_opinion_portfolio.py)
> (본 문서는 규칙을 *서술*만 하며 판정 로직을 중복하지 않습니다 — 의견서별
> 적합성 판정의 유일 권위 출처는 Phase 472 게이트의 `assess` 이고, 본 모듈은
> 그 결과를 *집계*만 합니다.)

## 1. 목적

밴드 471-480 은 국제 워킹그룹 의견서를 **3건** 산출하는 것을 목표로 명시합니다.
Phase 472(`intl_wg_opinion_gate`)가 *의견서 한 건*의 제출 적합성을 판정하는
게이트라면, 본 모듈은 그 게이트를 목표 수(3건)의 후보 의견서 포트폴리오에
적용하여 **"3건 목표에 얼마나 도달했는가, 무엇이 가장 흔히 발목을 잡는가"** 를
결정적으로 집계합니다. 같은 포트폴리오 상태는 항상 같은 집계를 산출합니다.

### 인접 모듈과의 경계 (중복 회피)

| 모듈 | 평가 대상 | 한 줄 |
|---|---|---|
| Phase 470 `standardization_tracker` | SDACS 발신 기고들의 진행 *상태* | "어디까지 갔나" |
| Phase 471 `ks_standard_proposal` | *국내* KS 신규 제정 제안 준비도 | "KS 제정 제안 가능한가" |
| Phase 472 `intl_wg_opinion_gate` | 의견서 *한 건*의 형식·근거 | "이 의견을 지금 보내도 되나" |
| **Phase 473 `wg_opinion_portfolio`** | 밴드 *3건 목표* 대비 포트폴리오 완성도 | "3건 목표에 얼마나 도달했나" |

## 2. 설계 원칙

- **판정 위임(DRY)**: 의견서별 적합성은 전적으로 Phase 472 `assess` 가 결정하며,
  본 모듈은 판정 로직을 복제하지 않습니다. 첫 후보(JARUS SORA)는 Phase 472
  `shipped_letter()` 를 그대로 *재사용*합니다(복제 0) — 472 는 작성 모듈
  `jarus_sora_opinion` 의 문서 증거 도출에 위임합니다.
- **정직한 자가 공시**: `portfolio()` 는 현재 준비 중인 실제 3건 후보를 격상
  없이 등록합니다. 따라서 현 진행도는 의도적으로 낮게 표면화됩니다.
- **발목 요건 롤업**: 제출 불가 후보들에서 어떤 기준이 가장 흔히 미완인지
  집계하여, 보완 노력을 어디에 집중할지 결정적으로 안내합니다.
- **자문이지 집행 아님**: 의견서를 *제출하지 않습니다*. 부수효과 0 · 무작위성 0 ·
  기존 모듈 무수정 순수 추가.

## 3. 후보 의견서 3건 (현 포트폴리오)

| # | 대상 | 판정(Phase 472) | 출처 |
|---|---|---|---|
| 1 | JARUS SORA — 군집 운용 보완 의견 | `NEEDS_WORK` | Phase 472 `shipped_letter` 재사용 → `jarus_sora_opinion` 위임(작성 완료) |
| 2 | EUROCAE WG-105 — 군집 ConOps 부속 의견 | `NEEDS_WORK` | Phase 474 `eurocae_wg105_opinion` 위임(작성 완료) |
| 3 | ISO/TC 20/SC 16 — 23629 시리즈 의견 | `NEEDS_WORK` | `iso_tc20_sc16_opinion` 위임(작성 완료) |

**현 밴드 진행도: `진행 중 (0.0%)` — 제출 가능 0/3.** 세 건 모두 실행 가능한
제안 변경(WG-02) redline 까지 작성 완료(각 0.95)이나, 공식 회람·체계적 검토
*기한*(WG-06)이 외부 일정에 의존해 PARTIAL 상한으로 고정됩니다(준비도 ≠
제출). `READY_TO_SUBMIT` 은 외부 기한 확정 후에만 가능합니다.

### 발목 잡는 요건 (제출 불가 후보 기준 미완 빈도)

| 기준 | 심각도 | 발목 건수 |
|---|---|:-:|
| WG-06 NB 채널·기한 | RECOMMENDED | 3 |

→ **제출 채널·기한(WG-06)이 세 후보 공통의 유일한 잔여 발목**이나 외부 일정
의존으로 sandbox 에서 해소 불가(정직 천장)입니다 — sandbox 에서 보완 가능한
발목은 더 이상 없습니다(3건 redline 전부 작성 완료).

## 4. CLI

```bash
python -m simulation.wg_opinion_portfolio --portfolio  # 후보별 판정
python -m simulation.wg_opinion_portfolio --report     # 밴드 진행 요약
python -m simulation.wg_opinion_portfolio --blockers   # 발목 요건 롤업
python -m simulation.wg_opinion_portfolio --manifest   # JSON 매니페스트
```

## 5. 검증

`tests/test_wg_opinion_portfolio.py` 27건이 판정 위임(복제 0)·밴드 집계 정확성·
진행도 캡·발목 롤업 정렬·결정론·매니페스트 정합·CLI·현 포트폴리오 정직성을
강제합니다.

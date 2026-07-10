# 국제 워킹그룹 의견서 적합성 게이트 (ODYSSEY Phase 472)

> Standards & Policy 트랙(Phase 461-480) · 밴드 471-480("국내 KS 제안 1건 +
> 국제 워킹그룹 의견서 3건")의 한 칸.
> 실행 가능 명세: [`simulation/intl_wg_opinion_gate.py`](../../simulation/intl_wg_opinion_gate.py)
> (본 문서는 규칙을 *서술*만 하며 판정 로직을 중복하지 않는다 — 진리표·요건의
> 유일 권위 출처는 모듈의 `CRITERIA`·`POLICY_MATRIX` 이고 테스트가 일치를 강제한다.)

## 1. 목적

SDACS 가 국제 표준 워킹그룹(JARUS·EUROCAE WG-105·ISO/TC 20/SC 16 등)이
회람하는 초안 문서에 **의견서(comment / opinion letter)** 를 제출할 때, 그 의견이
*채택되어 처리될* 형식·근거 요건을 갖췄는지를 사람이 매번 직관으로 점검하지
않도록 **결정적 게이트**로 명문화한다. 같은 의견서 상태는 항상 같은 판정을 낸다.

### 인접 모듈과의 경계 (중복 회피)

| 모듈 | 평가 대상 | 한 줄 |
|---|---|---|
| Phase 470 `standardization_tracker` | SDACS 발신 기고들의 진행 *상태* | "어디까지 갔나" |
| Phase 471 `ks_standard_proposal` | *국내* KS 신규 제정 제안 준비도 | "KS 제정 제안 가능한가" |
| **Phase 472 `intl_wg_opinion_gate`** | *국제* WG 초안에 다는 개별 의견의 형식·근거 | "이 의견을 지금 보내도 되나" |

## 2. 요건 6종 (필수 4 · 권장 2)

각 기준은 추측이 아니라 국제 표준 의견 처리 규약에서 도출하고 명문 근거를 결속한다.

| ID | 심각도 | 요건 | 권위 근거 |
|---|---|---|---|
| **WG-01** | CRITICAL | 대상 문서·버전·절(clause)/줄 지정 | ISO/IEC Directives Part 1 Annex(의견은 대상 절/줄 명시); EUROCAE/JARUS RoP(특정 문서 버전 대상) |
| **WG-02** | CRITICAL | 제안 변경(proposed change) 문안 — 실행 가능한 redline | ISO/IEC Directives: proposed change 없는 의견은 처리 대상이 아닐 수 있음 |
| **WG-03** | CRITICAL | 기술 근거(SDACS 실측·시뮬 데이터) 결속 | te(technical) 의견은 관찰을 뒷받침할 기술적 정당화 요구 |
| **WG-04** | CRITICAL | 의견 유형 분류 `ge`/`te`/`ed` | ISO/IEC Directives Part 1 comment template: 유형 분류 칸 필수 |
| **WG-05** | RECOMMENDED | 기여자 소속·이해관계 공개 | JARUS/EUROCAE 참여 규약: 소속·이해상충 공개 |
| **WG-06** | RECOMMENDED | 제출 기한·공식 채널(National Body 라우팅) 확인 | ISO 의견은 회원국 표준화기구(NB) 경유 기한 내 제출 |

각 기준의 충족 상태는 `MET` · `PARTIAL` · `UNMET` 셋 중 하나다.

## 3. 판정 규칙 (우선순위)

`assess(letter)` 는 다음 우선순위로 단일 판정을 낸다:

1. CRITICAL 이 하나라도 `UNMET` → **`NOT_READY`** (제출 부적합 — 처리 거부 위험)
2. CRITICAL 이 `PARTIAL` → **`NEEDS_WORK`** (보완 후 제출)
3. CRITICAL 은 모두 충족하나 어떤 기준이든 `MET` 미만 → **`NEEDS_WORK`**
4. 전 기준 `MET` → **`READY_TO_SUBMIT`**

점수는 가중 충족 비율(`CRITICAL` 가중 2 · `RECOMMENDED` 가중 1, `PARTIAL` = 절반)을
소수 넷째 자리에서 반올림한 값(결정적)이다.

진리표 `(critical_unmet, critical_partial, any_incomplete) → verdict` 는 모듈의
`POLICY_MATRIX` 가 유일 권위 출처이며, `--policy` 로 출력한다. CRITICAL UNMET/
PARTIAL 은 `any_incomplete=True` 를 강제하므로 모순 조합은 표에서 제외된다.

## 4. 정직한 자가 공시

현재 준비 중인 실제 후보 의견서(`shipped_letter()`)는 SDACS 가 **JARUS SORA**
초안에 다는 군집 운용(swarm operation) 보완 의견이다. 상태는 작성 모듈
(`jarus_sora_opinion`)의 동봉 문서
([`JARUS_SORA_SWARM_OPINION.md`](JARUS_SORA_SWARM_OPINION.md)) 디스크 증거로부터
위임 도출한다(하드코딩 스냅샷 0). 격상 없이 판정하면:

```
판정: NEEDS_WORK (95.0%)
  WG-01 MET · WG-02 MET · WG-03 MET · WG-04 MET · WG-05 MET · WG-06 PARTIAL
  → 부분 권장: WG-06(회원기관 채널 문서화 ○ · 회람 기한 외부 의존 ✗)
```

redline(WG-02) 완성으로 산문 초안(80.0%) 대비 정직하게 격상되었으나, 공식
회람 *기한* 이 JARUS WG 일정에 의존하므로 **제출 전 보완 필요**(외부 기한
확정 대기)임을 정직히 드러낸다.

## 5. 성격

- **자문이지 집행 아님**: 의견서를 *제출하지 않는다*. 현 초안의 적합성만 판정한다
  (부수효과 0).
- **결정적**: 무작위성 0. 같은 입력은 항상 같은 판정.
- **순수 추가**: 기존 모듈 무수정. `legacy_readiness`·`standardization_tracker`
  와 로직을 공유하지 않는다.

## 6. CLI

```bash
python -m simulation.intl_wg_opinion_gate --criteria   # 요건 매트릭스
python -m simulation.intl_wg_opinion_gate --status     # 현 후보 의견서 판정
python -m simulation.intl_wg_opinion_gate --policy     # 판정 진리표
python -m simulation.intl_wg_opinion_gate --manifest   # JSON 매니페스트
```

# KS 국가표준 제안 적합성 게이트 (ODYSSEY Phase 471)

> SDACS 군집 드론 공역통제 접근을 한국산업표준(KS)으로 제안할 준비가 됐는지를
> **결정적으로 판정**하는 자문 게이트. 구현: [`simulation/ks_standard_proposal.py`](../../simulation/ks_standard_proposal.py)

## 1. 목적

Standards & Policy 트랙(Phase 461-480)의 "국내 표준(KS) 제안 1건" 항목을
실현한다. Phase 470(`standardization_tracker`)이 SDACS 가 *발신하는* 기고의
진행 상태를 추적한다면, 본 모듈은 KS 제안 한 건이 KATS(국가기술표준원)에
접수되기 위한 **제안 요건**을 충족하는지 판정한다.

본 모듈은 **자문이지 집행이 아니다**. 준비도를 판정만 하며 어떤 파일도
변경하지 않는다(부수효과 0). 실제 제안서 작성·접수는 사람의 일이다.

## 2. 제안 요건 (6개 기준)

요건은 산업표준화법 시행령(표준안·제안 사유)과 WTO/TBT 협정 제2.4조(국제표준
부합 원칙)에서 도출했다. 추측이 아니라 명문 근거를 기준 설명에 담는다.

| ID | 요건 | 필수 | 근거 |
|---|---|:-:|---|
| KS-01 | 표준안 본문 | ● | 산업표준화법 시행령 §11(표준안 제출) |
| KS-02 | 제안 사유·필요성 | ● | 산업표준화법 시행령 §11(제안 사유) |
| KS-03 | 국제표준 부합성 검토 | ● | WTO/TBT 협정 §2.4(국제표준 기반 원칙) |
| KS-04 | 기존 KS 중복성 검토 | ● | KS 운영요령(중복 제정 금지) |
| KS-05 | 기술적 타당성 근거 | ○ | KS 운영요령(기술 근거 첨부) |
| KS-06 | 이해관계자 의견수렴 | ○ | 산업표준화법 §5(예고고시 60일) |

`●` = 필수(미충족 시 제안 반려) · `○` = 권장.

## 3. 기준 충족 상태

각 요건은 4개 상태 중 하나로 판정한다.

| 상태 | 의미 | 점수 가중 |
|---|---|:-:|
| `MET` | 요건을 완전히 충족 | 1.0 |
| `PARTIAL` | 부분 충족(보강 필요) | 0.5 |
| `UNMET` | 미충족 | 0.0 |
| `N/A` | 비적용(게이트·점수 분모에서 제외) | — |

명시되지 않은 요건은 보수적으로 `UNMET` 으로 간주한다.

## 4. 판정 우선순위

`assess()` 는 다음 우선순위로 단일 판정을 도출한다.

1. CRITICAL 기준이 하나라도 `UNMET` → **`NOT_READY`**
2. CRITICAL 기준이 하나라도 `PARTIAL` → **`NEEDS_WORK`**
3. (비-CRITICAL 포함) `UNMET`/`PARTIAL` 이 남으면 → **`NEEDS_WORK`**
4. 그 외(전부 `MET` 또는 `N/A`) → **`READY_TO_PROPOSE`**

### 결정 매트릭스

`POLICY_MATRIX` 가 (CRITICAL 최악 상태, 그 외 미완 존재) → 판정의 6칸을
명시하며, 테스트가 `assess()` 와의 정확 일치를 강제한다.

| CRITICAL 최악 | 그 외 미완 | 판정 |
|---|:-:|---|
| `UNMET` | 유 | `NOT_READY` |
| `UNMET` | 무 | `NOT_READY` |
| `PARTIAL` | 유 | `NEEDS_WORK` |
| `PARTIAL` | 무 | `NEEDS_WORK` |
| `MET` | 유 | `NEEDS_WORK` |
| `MET` | 무 | `READY_TO_PROPOSE` |

## 5. 현 리포 후보 — 정직한 자가 공시

후보: **"군집 드론 공역통제 시스템 — 안전 요구사항 및 시험 방법"** KS 제안.
격상 없이 현 자산 상태를 그대로 반영한다.

| 요건 | 상태 | 근거 |
|---|:-:|---|
| KS-01 표준안 본문 | `PARTIAL` | 5계층 안전망 백서·벤치마크 스위트 존재, KS 형식 표준안 본문 미작성 |
| KS-02 제안 사유 | `PARTIAL` | 로드맵·산학 문서에 산재, 단일 제안서 미정리 |
| KS-03 국제표준 부합성 | `MET` | ICAO/ISO 부합성 추적 모듈(Phase 407·462) |
| KS-04 중복성 검토 | `UNMET` | 기존 KS 중복성 공식 검토 미수행 |
| KS-05 기술 근거 | `MET` | 4,443 검증 자산·표준 벤치마크 스위트 |
| KS-06 의견수렴 | `UNMET` | 외부 이해관계자 의견수렴 미착수(사용자 환경 의존) |

**판정: `NOT_READY` (50.0%)** — 결격 1건: KS-04(중복성 검토).

다음 단계: ① KS-04 기존 KS 중복성 검토 수행 → ② KS-01/02 단일 제안서로 정리
→ ③ KS-06 이해관계자 의견수렴. CRITICAL 4종 충족 후 `READY_TO_PROPOSE` 격상.

## 6. CLI

```bash
python -m simulation.ks_standard_proposal --criteria   # 제안 요건 목록
python -m simulation.ks_standard_proposal --status     # 현 후보 판정
python -m simulation.ks_standard_proposal --policy     # 결정 매트릭스
python -m simulation.ks_standard_proposal --manifest   # 매니페스트(JSON)
```

## 7. 설계 불변식

- **결정적**: 무작위성 0. 동일 입력 → 동일 판정.
- **자문**: 부수효과 0. 파일 무변경.
- **순수 추가**: 기존 모듈 무수정.
- **정직성**: 미충족은 미충족으로 표면화. 격상 없음.

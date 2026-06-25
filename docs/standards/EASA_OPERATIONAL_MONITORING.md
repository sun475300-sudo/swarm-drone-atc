# EASA AI 운영 모니터링·드리프트 대응 적합성 게이트 — ODYSSEY Phase 457

SDACS 의 *학습 기반(ML)* 구성요소가 **운용 중(in-operation)** 자신의 운용 설계 영역
(Operational Design Domain, ODD)을 벗어나는지 감시하고, 벗어났을 때 결정적 안전망으로
안전하게 폴백하는가를 **운영 모니터링 축** 으로 정렬해 평가한 기준 문서입니다. 정본
데이터는 `simulation/easa_operational_monitoring.py` 가 보유하며, 본 문서는 그 요약과
활용 맥락을 제공합니다. ODYSSEY Track 🔬 Formal & Research Frontier(451-460,
"RL 일반화 연구 + 인증 가능 ML 조사")의 후속 산출물입니다.

Phase 451(`easa_ai_conformance`)이 *설계 시점(design-time)* 의 러닝 어슈어런스를
평가하는 자매편이라면, 본 모듈은 그 *운영 시점(operation-time)* 대응물 — **추론 모델이
배포 후 훈련 분포를 벗어날 때 무슨 일이 일어나는가** — 를 평가합니다.

> **정직 공시**: 본 평가는 *기능적 자가 평가* 이며 EASA 공식 적합성 인증이 아닙니다.
> SDACS 의 ML 은 **연구 수준** 이므로 본 평가는 의도적으로 보수적입니다 — 가중 점수가
> 낮은 것이 곧 정직함입니다. SDACS 의 강점은 드리프트 *탐지* 가 아니라 out-of-ODD
> *폴백* 에 있으며, 온라인 드리프트/노벨티 탐지는 솔직히 갭입니다.

## 근거 (권위 있는 출처)

- **EASA Concept Paper — "Guidance for Level 1 & 2 machine learning applications"**
  (Issue 02, 2024) — 운영 단계 요구로 ODD 모니터링·입력 데이터 적합성 감시·out-of-ODD
  안전 전이·운영 데이터 기록을 제시.
- **EASA Artificial Intelligence Roadmap 2.0** (2023) — 학습 구성요소의 *지속적 적합성
  보증* 개념을 운영 모니터링·드리프트 대응의 근거로 차용.
- **EASA "AI assurance — runtime monitoring"** — 추론 모델 출력을 결정적 모니터로
  경계(bounding)하는 *runtime assurance* 아키텍처 권고. SDACS 의 "ML 자문 + 결정적
  권한" 구조가 이 권고에 대응.

## 모니터링 카테고리 (5종)

| 카테고리 id | 라벨 |
|---|---|
| `odd_monitoring` | ODD 경계 정의·실시간 준수 감시 |
| `drift_detection` | 입력·개념 분포 이탈 탐지 |
| `confidence_gating` | 불확실성 기반 자문 한정 |
| `fallback` | out-of-ODD 시 결정적 안전망 전이 |
| `operational_recording` | 운영 데이터 기록·사후 분석 |

## 적합성 상태 (3값)

- `conformant` (가중 1.0) — 완전 충족, 실재 모듈 근거 필수
- `partial` (가중 0.5) — 부분 충족, 실재 모듈 근거 필수
- `gap` (가중 0.0) — 미충족, **근거 모듈 없음(None)**

`gap` ⟺ `sdacs_module is None` 정직성 결속을 dataclass `__post_init__` 가 강제하며,
인용한 모든 경로의 디스크 실재를 테스트(`test_cited_modules_exist_on_disk`)가 강제합니다.

## 현 리포 판정 (스냅샷)

| 지표 | 값 |
|---|---|
| 가중 점수 | **56%** (충족 5 · 부분 9 · 갭 3 / 총 17) |
| 기반(필수) 목표 | **5/11** 완전 충족 (45%) |

카테고리별 (충족/부분/갭):

| 카테고리 | 충족 | 부분 | 갭 |
|---|:-:|:-:|:-:|
| odd_monitoring | 1 | 2 | 0 |
| drift_detection | 0 | 2 | 2 |
| confidence_gating | 1 | 2 | 0 |
| fallback | **3** | 0 | 0 |
| operational_recording | 0 | 3 | 1 |

## 핵심 해석

- **SDACS 의 강점은 out-of-ODD 폴백에 있습니다.** 근접 위협이 ML 의 신뢰 영역(안전
  임계)을 벗어나면 `src/autonomy/hybrid_collision_avoidance.py` 가 `safety_override`
  로 *순수 결정적 APF* 로 전환하고, 5계층 안전망
  (`simulation/safety_net_invariant.py`)이 안전-결정권을 보유합니다. "ML 을 신뢰할 수
  없는 순간 ML 을 쓰지 않음" 이라는 아키텍처 선택이 `fallback` 카테고리 3개 항목이 모두
  충족인 근거입니다.
- **가장 솔직한 약점은 드리프트 탐지입니다.** 운영 중 입력 분포 이탈을 *온라인* 으로
  탐지하는 검출기(`input_distribution_drift`)와 개념 드리프트 운영자 경보
  (`concept_drift_alerting`)가 없습니다. 분포 격차는 오프라인(`sim_real_gap`)으로만
  측정됩니다 — 이는 인증 경로의 핵심 갭이며 후속 연구 과제입니다.
- **운영 중 모델 갱신은 의도적 미채택 영역**(`online_model_update_management`)입니다.
  지속 학습의 형상 관리·검증 부담을 피하고자 SDACS 는 추론 모델을 동결 운용하며, 이
  갭은 결함이 아니라 보수적 설계 선택의 정직한 기록입니다.

## CLI

```bash
python simulation/easa_operational_monitoring.py --report             # 적합성 요약
python simulation/easa_operational_monitoring.py --matrix             # 전체 매트릭스
python simulation/easa_operational_monitoring.py --category fallback  # 카테고리별 목표
python simulation/easa_operational_monitoring.py --gaps               # 미충족(갭) 목표
python simulation/easa_operational_monitoring.py --foundational       # 기반(필수) 목표
```

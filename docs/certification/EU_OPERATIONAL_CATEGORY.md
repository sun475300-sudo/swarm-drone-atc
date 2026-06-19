# EU 2019/947 운영 카테고리 판정 (Open / Specific / Certified)

> Phase 403 (ODYSSEY · Track 🌏 Global Expansion)
> 구현: [`simulation/sora_category.py`](../../simulation/sora_category.py) · 테스트: [`tests/test_sora_category.py`](../../tests/test_sora_category.py)

## 1. 목적

GENESIS Phase 302 의 `soraAssess`(시뮬레이터 JS, JARUS SORA 2.0 표 기반)는 **Specific**
카테고리의 SAIL 등급만 산정한다. 본 모듈은 그 위에 EU 위임규정 **2019/947** 의 세 운영
카테고리(Open / Specific / Certified)와 Open 하위 분류(A1·A2·A3)를 결정적으로 판정하는
계층을 얹어, "이 군집 운용은 어느 규제 체계로 비행 가능한가" 에 답한다.

K-드론 체계(국토부)·FAA UTM 정렬을 넘어 EASA U-space 3대 체계 동시 호환(Phase 401·406·408)을
완성하는 마지막 규제 분류 축이다.

## 2. 판정 순서

```
1) Certified 강제 트리거
   ├─ 인원 수송              → CERTIFIED
   ├─ 고위험 위험물 운송      → CERTIFIED
   └─ 군중 상공 + 치수 ≥3 m  → CERTIFIED
2) Open 적격 (하드 제약 전부 충족 + 유효 하위분류)
   ├─ MTOM < 25 kg
   ├─ VLOS
   ├─ 고도 ≤ 120 m AGL
   ├─ 군중 상공 아님 · 위험물 없음
   └─ A1 / A2 / A3 중 하나 부합  → OPEN (허가 불요)
3) 그 외                        → SPECIFIC (SORA 산정)
   └─ SORA 최종 GRC > 7         → CERTIFIED 격상
```

## 3. Open 하위 분류 (UAS.OPEN.020/030/040)

| 하위 | C-class | 조건 | 근거 |
|---|---|---|---|
| **A1** | C0 / C1 | 비관여 인원 근접 허용(군중 제외) | UAS.OPEN.020 |
| **A2** | C2 | 수평 이격 ≥ 30 m (저속 모드 ≥ 5 m) | UAS.OPEN.030 |
| **A3** | C2 / C3 / C4 | 비관여 인원 부재 환경(controlled/sparse), 시가지 원거리 | UAS.OPEN.040 |

C-class 는 EU 위임규정 **2019/945** 의 질량 게이트로 파생한다(C0<0.25kg, C1<0.9kg,
C2<4kg, C3<25kg). `c_class` 명시 시 그 값을 우선한다.

## 4. SORA 2.0 표 (시뮬레이터 JS 정합)

본 모듈의 `SORA_IGRC`·`SORA_SAIL_TABLE` 은 `swarm_3d_simulator.html` 의 `soraAssess` 와
**동일**하다(수치 불일치 금지 규약).

**iGRC** (인구밀도 × VLOS/BVLOS):

| 밀도 | VLOS | BVLOS |
|---|:-:|:-:|
| controlled | 1 | 2 |
| sparse | 2 | 3 |
| populated | 3 | 4 |
| assembly | 7 | 8 |

**완화**: M1 전략적 지오펜스(NFZ) −1, M3 ERP(failsafe+착륙 시퀀스) −1, GRC ≥ 1 클램프.
**ARC**: populated/assembly → ARC-c 후보, 전술 완화(TMPR: CPA 90초 + APF + ATC 5계층) c→b 1단계 경감.
**SAIL**: 최종 GRC × ARC 표 조회. 최종 GRC > 7 이면 Specific 범위 초과 → CERTIFIED.

## 5. 정직 공시 (범위·한계)

- `vlos` 는 **기본 False(BVLOS)** 다 — 본 시스템의 군집 자동 운용 및 시뮬레이터 JS `soraAssess`
  (`bvlos !== false`)와 정합. 동일 입력 시 JS 와 같은 iGRC 를 내며, 위험을 과소평가하지 않는다.
  VLOS 단일 운용은 `vlos=True` 를 명시한다.
- C-class 파생은 **질량 게이트만** 사용한다(C0-C3). 속도·운동에너지·클래스 마킹 전자요건(원격
  ID·지오인식 능동요구 등)은 본 결정적 모델 범위 밖이며, 정확한 분류는 `c_class` 명시로 보완한다.
  **C5/C6/C7 클래스는 범위 밖**(EU 2019/947 Art. 4(1)(b) Certified 자동 격상 대상이나 미구현 —
  `c_class='C5'` 등은 `ValueError`).
- 군중 상공(`over_assembly`)은 전술 완화(TMPR)로도 지상위험을 충분히 낮출 수 없어 ARC-c 를
  유지한다(소형 기체 <3 m 의 Specific 분기에서 SAIL 이 인구밀도 단독 산정보다 보수적으로 상향).
- "위험물"은 사고 시 **고위험**으로 보아 Certified 로 분류한다. 저위험 위험물 운송의 Specific
  분기는 다루지 않는다(EU 2019/947 Art. 4(1)(c) 보수적 채택).
- SORA 산정은 SORA **2.0** 표 기반이다(시뮬레이터 정합 목적). SORA 2.5 의 정량 인구밀도
  iGRC·OSO 세분은 후속 격상 대상이다.
- 무작위성 0 · 기존 모듈 무수정 순수 추가 · 외부 호출 없음.

## 6. API 요약

```python
from simulation.sora_category import OperationProfile, assess_category, summary

# vlos 는 기본 False(BVLOS, 군집 운용·JS soraAssess 정합) — Open 판정엔 명시 필요
profile = OperationProfile(mtom_kg=3.0, population_density="populated",
                           horizontal_distance_to_people_m=30.0, vlos=True)
result = assess_category(profile)
print(summary(result))   # "OPEN (A2) — 허가 불요"
```

| 함수 | 반환 | 설명 |
|---|---|---|
| `derive_c_class(mtom_kg)` | `str \| None` | 질량 → C0-C3 (≥25kg = None) |
| `assess_sora(profile)` | `SoraResult` | iGRC·완화·ARC·SAIL |
| `assess_category(profile)` | `CategoryAssessment` | Open/Specific/Certified + 하위분류 |
| `summary(assessment)` | `str` | 한 줄 요약 |

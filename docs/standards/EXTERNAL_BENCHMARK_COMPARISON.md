# SDACS-SBS-10 외부 벤치마크 구조 비교 (BlueSky · U-TRAFMAN)

> ODYSSEY **Phase 405** — 국제 벤치마크 제출
> 구현: [`simulation/benchmark_external_compare.py`](../../simulation/benchmark_external_compare.py)
> 전제 스위트: ODYSSEY Phase 465 [`simulation/standard_scenarios.py`](../../simulation/standard_scenarios.py) — `SDACS-SBS-10`

## 목적

SDACS 공개 표준 시나리오 스위트 `SDACS-SBS-10`(10종)을 공개 항공/UTM 시뮬레이터
**BlueSky** 와 **U-TRAFMAN** 의 모델링 역량에 **구조적으로** 대응시킨다. "SDACS 표준
시나리오를 외부 도구로 교차 비교·제출하려면 각 시나리오가 외부 도구에서 어떻게(또는
*어디까지만*) 표현되는가" 를 답한다.

## 정직 공시 (CLAUDE.md)

- 본 문서·모듈은 외부 도구의 **구조적 표현 가능성**(어떤 운용 차원을 모델링하는가)에
  대한 *기능적 요약* 이며, **성능 수치(벤치마크 결과)를 산출하거나 인용하지 않는다.**
  외부 도구 역량은 각 도구의 **공개 문서/논문 기준**(스냅샷 `as_of` = 2026-06)이다.
- `status` 3값 — `direct`(외부 도구가 해당 축을 1차 모델링) · `partial`(스크립팅/우회로
  부분 표현) · `none`(표현 모델 부재). **정직성 결속**: `status=='none'` ⟺ 대응(`analog`)
  없음. 없는 대응을 있다고 주장하는 것을 구조적으로 금지한다.
- 비교 대상 식별자·통제 축은 Phase 465 가 **유일 출처(SSoT)** 이며 복제하지 않고 참조한다.

## 외부 도구 근거

| 도구 | 성격 | 근거 |
|---|---|---|
| **BlueSky** | 오픈소스 항공교통(ATM) 시뮬레이터 (TU Delft CNS/ATM) | Hoekstra & Ellerbroek, "BlueSky ATC Simulator Project: an Open Data and Open Source Approach", ICRAT 2016. github.com/TUDelft-CNS-ATM/bluesky. 전통 ATM·상태기반 충돌탐지/해소(MVP·SSD)·바람장·시나리오(.scn) 스크립팅 1차 모델링. |
| **U-TRAFMAN** | UAS Traffic Management 연구 시뮬레이터 (에이전트 기반) | UTM 운용 흐름·전략적 디컨플릭션·다중 운영자 모델링(공개 문서 기준). |

## 비교 매트릭스

| ID | 통제 축 | BlueSky | U-TRAFMAN |
|---|---|:-:|:-:|
| B01 | traffic_density | direct | direct |
| B02 | in_flight_failure | partial | partial |
| B03 | launch_surge | partial | partial |
| B04 | deconfliction | direct | direct |
| B05 | lost_link | **none** | partial |
| B06 | wind_robustness | direct | partial |
| B07 | intrusion_security | **none** | **none** |
| B08 | multi_region | **none** | partial |
| B09 | autonomous_formation | **none** | **none** |
| B10 | nominal_baseline | direct | direct |

## 비교 가능성 집계 (direct 1.0 · partial 0.5 · none 0.0)

| 도구 | direct | partial | none | 비교 가능성 |
|---|:-:|:-:|:-:|:-:|
| BlueSky | 4 | 2 | 4 | **50.0%** |
| U-TRAFMAN | 3 | 5 | 2 | **55.0%** |

## 핵심 시사점 (정직한 한계)

- **B07(적대적 침입·보안)·B09(군집 자율 편대)** 는 양 외부 도구 모두 표현 불가(`none`).
  SDACS-SBS-10 이 통상의 ATM/UTM 교통 시뮬레이터 범위를 **초과** 하는 운용 차원을
  포함함을 의미한다 — 외부 교차 비교는 *부분적* 으로만 가능하며, 보안·군집 자율 축은
  SDACS 자체 검증으로만 평가된다.
- 따라서 외부 벤치마크 제출 시 직접 비교 가능 축(B01·B04·B10 등)에 한정하고, 표현 불가
  축은 비교에서 제외·정직 표기하는 것이 올바른 제출 형식이다.

## CLI

```bash
python -m simulation.benchmark_external_compare --matrix        # 전체 비교 매트릭스
python -m simulation.benchmark_external_compare --report        # 도구별 비교 가능성 집계
python -m simulation.benchmark_external_compare --tool bluesky  # 도구별 대응 상세
python -m simulation.benchmark_external_compare --gaps          # 표현 불가(none) 축
python -m simulation.benchmark_external_compare --manifest      # 제출 매니페스트(JSON)
```

단위 테스트 37건 PASS — [`tests/test_benchmark_external_compare.py`](../../tests/test_benchmark_external_compare.py)

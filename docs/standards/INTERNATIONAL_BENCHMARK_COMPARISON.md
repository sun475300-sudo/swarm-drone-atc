# 국제 벤치마크 제출 — BlueSky·U-TRAFMAN 비교 시나리오

> ODYSSEY Phase 405 · Track 🌏 International Expansion
> 산출물: [`simulation/international_benchmark.py`](../../simulation/international_benchmark.py) ·
> 테스트 [`tests/test_international_benchmark.py`](../../tests/test_international_benchmark.py) (54 PASS)

## 1. 목적

SDACS는 이미 공개 벤치마크 스위트([`benchmarks/`](../../benchmarks/README.md), P703 —
10개 표준/스트레스 시나리오 + 14개 지표 + 4개 baseline, CC-BY-4.0)를 보유한다.
본 문서는 그 공개 시나리오를 국제적으로 널리 쓰이는 외부 공개 시뮬레이터의 *비교
가능 역량*에 결정적으로 대응시켜, **어떤 SDACS 시나리오가 외부 플랫폼으로 교차
검증 가능한가**를 정리한다. Phase 409(다국 규제 대조)의 자매편으로, 거기서는
*관할*을, 여기서는 *시뮬레이터 플랫폼*을 비교 축으로 같은 자산을 재정렬한다.

본 매핑은 공개 자료에 근거한 **기능적 요약**이며 외부 플랫폼의 공식 채택·동등성
보증이 아니다(`comparable` 판단은 프로젝트 해석).

## 2. 외부 비교 대상(공개 시뮬레이터)

| 코드 | 플랫폼 |
|---|---|
| **bluesky** | BlueSky Open ATM Simulator — TU Delft CNS/ATM(오픈소스 `github.com/TUDelft-CNS-ATM/bluesky`; Hoekstra & Ellerbroek, ICRAT 2016). 고속 이산 시뮬레이션 + CD&R(ASAS) + 바람장. |
| **utrafman** | U-TRAFMAN UAS Traffic Management Simulator — 공개 UTM 연구 시뮬레이터. U-space 운영·UTM 트래픽 관리 초점. |

## 3. 교차 검증 상태(정직 공시)

- **교차 검증 가능(cross-validatable)** — 해당 시나리오와 비교 가능한 역량이 외부
  플랫폼에 존재(`comparable` ≥ 1).
- **SDACS 고유(gap)** — 외부 표준 기준선이 없는 시나리오(`comparable == ()`).
  외부 교차 검증 불가를 정직히 표면화한다.

**정직성 결속**: 각 시나리오의 `manifest`는 디스크에 실재하는 공개 매니페스트
경로이며, 테스트 `test_cited_manifests_exist_on_disk`가 실재를 결정적으로 강제한다.
모듈/시나리오 없는 비교 주장을 구조적으로 금지한다.

## 4. 비교 매트릭스

| 시나리오 | 범주 | 주 지표 | 비교 가능 플랫폼 |
|---|---|---|---|
| 01 Corridor Crossing | CDR | MSD | bluesky, utrafman |
| 02 Dense Intersection | DENS | NMR | bluesky, utrafman |
| 03 Emergency Landing | FAIL | MS | utrafman |
| 04 No-Fly Zone Avoidance | REG | geofence_violations | bluesky, utrafman |
| 05 Weather Diversion | ENV | PE | bluesky |
| 06 Priority Aircraft | CDR | FT | bluesky, utrafman |
| 07 Communication Loss | FAIL | RID-CR | utrafman |
| 08 High Density Stress | DENS | AU | bluesky, utrafman |
| 09 Failure Cascade Stress | FAIL | MSD | — (SDACS 고유) |
| 10 Adversarial Swarm Stress | ADV | NMR | — (SDACS 고유) |

## 5. 커버리지 요약

| 지표 | 값 |
|---|:-:|
| 전체 시나리오 | 10 |
| 교차 검증 가능 | 8 |
| SDACS 고유(기준선 없음) | 2 |
| **교차 검증 커버리지** | **80%** |
| bluesky 비교 가능 | 6 |
| utrafman 비교 가능 | 7 |

연쇄 장애 주입(09)·적대적 군집(10) 스트레스는 외부 표준 벤치마크에 동등한 공개
기준선이 없어 **SDACS 고유**로 정직히 표면화한다.

## 6. CLI

```bash
python simulation/international_benchmark.py --matrix          # 전체 비교 매트릭스
python simulation/international_benchmark.py --report          # 교차검증 커버리지 요약
python simulation/international_benchmark.py --category CDR     # 범주별 시나리오
python simulation/international_benchmark.py --platform bluesky # 플랫폼 비교 가능 시나리오
python simulation/international_benchmark.py --unique           # SDACS 고유(외부 기준선 없음)
python simulation/international_benchmark.py --platforms         # 외부 플랫폼 목록
```

## 7. 한계

- `comparable`은 공개 자료 기반의 기능적 비교 가능성에 대한 *프로젝트 해석*이며
  외부 플랫폼 운영진의 확인·동등성 보증이 아니다.
- 실제 수치 결과의 동등 재현은 각 플랫폼의 시나리오 변환·지표 정의 정렬이
  선행되어야 한다(본 모듈은 *비교 가능성 매핑*까지를 범위로 한다).

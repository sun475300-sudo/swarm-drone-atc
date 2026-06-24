# 국제 벤치마크 비교 (SDACS · BlueSky · U-TRAFMAN) — ODYSSEY Phase 405

SDACS 를 공개된 두 오픈소스 항공/무인 교통 시뮬레이터와 **동일한 비교 축(axis)** 으로
정렬해, SDACS 의 좌표를 학계·산업 도구 지형 위에 정직하게 자리매김한 기준 문서입니다.
정본 데이터는 `simulation/benchmark_comparison.py` 가 보유하며, 본 문서는 그 요약과
활용 맥락을 제공합니다.

> **정직 공시**: 본 비교는 세 도구의 *기능적 위치 설정* 이며 성능 우열 주장이
> 아닙니다. 각 축의 값은 권위 있는 공개 문서를 인용하고, SDACS 의 능력 주장은
> 실재하는 리포 모듈/산출물을 근거(`evidence`)로 가리켜 디스크 실재를 강제합니다.
> 외부 도구(BlueSky·U-TRAFMAN)는 본 리포에서 검증할 수 없으므로 근거가 없으며,
> 그 비대칭을 정직하게 표면화합니다. 외부 도구의 능력은 공개 문헌이 기술하는
> *설계 초점* 에 한정해 보수적으로 요약했습니다(미검증 수치·우열 단정 금지).

## 비교 대상 (공개 근거)

| 도구 | 개발 주체 | 라이선스 | 1차 공개 근거 |
|---|---|---|---|
| **SDACS** (본 프로젝트) | swarm-drone-atc | 공개 리포(학술 재현) | 4계층 아키텍처 — SimPy + Dash 3D |
| **BlueSky** | TU Delft (CNS/ATM) | GNU GPL v3 | Hoekstra & Ellerbroek, *BlueSky ATC Simulator Project*, ICRAT 2016 |
| **U-TRAFMAN** | Univ. Castilla-La Mancha (I3A-NavSys) | GNU GPL v3 | Jover, Casado & Bermúdez, *U-TRAFMAN*, SoftwareX 2025 |

- BlueSky: `github.com/TUDelft-CNS-ATM/bluesky` (Python 3, numpy, Qt/pygame)
- U-TRAFMAN: `github.com/I3A-NavSys/utrafman_sim` (ROS + Gazebo + Matlab)

## 비교 축 (8종)

| 축 id | 라벨 |
|---|---|
| `domain` | 대상 도메인 |
| `license` | 라이선스·공개성 |
| `conflict_method` | 충돌 탐지·해결(CD&R) 방식 |
| `traffic_model` | 교통·기체 모델 입도 |
| `swarm_support` | 군집/다중에이전트 지원 |
| `weather_model` | 기상·바람 모델 |
| `federation` | 연합·다중 USS 운영 |
| `reproducibility` | 재현성·시나리오 정의 |

## 핵심 대조 포인트

- **도메인 분업**: BlueSky 는 *유인 ATM*(고정익·en-route/TMA), U-TRAFMAN 과 SDACS 는
  *무인 UTM* 에 초점합니다. SDACS 는 그중에서도 **군집 드론**의 저고도 분리·충돌
  해결 자동화에 특화됩니다.
- **충돌 해결 방식**: BlueSky 는 ASAS 플러그형 *상태기반 CD&R*(MVP·SSD 등 알고리즘
  비교 평가), U-TRAFMAN 은 *UTM 서비스 수준 전략적 디컨플릭션*, SDACS 는 *APF+CBS
  하이브리드* 에 강풍 모드 자동전환을 결합합니다.
- **군집 지원**: SDACS 의 군무·자율 비계획 편대 시나리오는 군집 자율성 자체를
  통제 변인으로 다루는 점이 두 비교 도구와 구별됩니다.
- **연합 운영**: BlueSky·U-TRAFMAN 은 단일 시뮬/중앙 서비스 모델이 설계 초점이며,
  SDACS 는 다중 인스턴스 연합(inter-USS, HLC 워터마크 인과-안정 배달)을 명시적으로
  다룹니다.
- **재현성**: 세 도구 모두 결정적 재현을 지향합니다 — BlueSky 의 `.scn` 스크립트,
  U-TRAFMAN 의 ROS/Matlab 설정, SDACS 의 `np.random.default_rng(seed)` + YAML
  시나리오 + Monte Carlo 스윕.

## SDACS 능력 근거 (디스크 실재 강제)

`test_sdacs_evidence_exists_on_disk` 가 아래 경로의 실재를 강제합니다. 근거 보유
**7/8 축(88%)** — `domain` 축은 단일 모듈로 환원되지 않아 근거 없음으로 정직 공시.

| 축 | 근거 경로 |
|---|---|
| `license` | `CITATION.cff` |
| `conflict_method` | `src/autonomy/hybrid_collision_avoidance.py` |
| `traffic_model` | `simulation/drone_agent.py` |
| `swarm_support` | `config/scenario_params/swarm_autonomous_no_preplan.yaml` |
| `weather_model` | `simulation/weather.py` |
| `federation` | `simulation/federation_causal_delivery.py` |
| `reproducibility` | `simulation/monte_carlo.py` |

## 벤치마크 제출 (SDACS-IBC-1)

`submission_manifest()` 는 Phase 465 가 큐레이션한 공개 표준 스위트
**`SDACS-SBS-10`** (10종 시나리오)을 본 비교 매트릭스와 함께 하나의 제출 단위
(`SDACS-IBC-1`)로 묶습니다. 제출 단위에는 **외부 도구의 결과 수치를 담지 않습니다**
— 제출하는 것은 *스위트 정의* 와 *기능적 위치 설정* 이며, 누구나 같은 10개
시나리오를 같은 정의로 돌려 자신의 도구와 비교할 수 있게 하는 것이 목적입니다.

## CLI

```bash
python -m simulation.benchmark_comparison --matrix                    # 전체 비교 매트릭스
python -m simulation.benchmark_comparison --tool sdacs                # 도구별 프로파일
python -m simulation.benchmark_comparison --dimension conflict_method # 축별 대조
python -m simulation.benchmark_comparison --evidence                  # SDACS 근거 커버리지
python -m simulation.benchmark_comparison --submission                # 제출 매니페스트(JSON)
```

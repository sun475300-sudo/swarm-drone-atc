# SDACS 표준 벤치마크 스위트 (SDACS-SBS-10)

*ODYSSEY Phase 465 — 공역 통합 시뮬레이션 표준 시나리오 셋 (10종 공개)*

**식별자:** `SDACS-SBS-10` · **버전:** 1.0 · **상태:** 공개 제안(Public Proposal)

---

## 1. 목적

군집 드론 공역 통제 시뮬레이터를 **서로 다른 도구 간에 동일한 정의로 비교**하기
위한 공통 시나리오 기준선을 제안한다. Phase 405(BlueSky·U-TRAFMAN 비교)와
Phase 410(GUTMA 기고)이 전제하는 "같은 10개 시나리오를 같은 입력으로 돌려
지표를 비교한다" 는 합의 기반을 제공한다.

각 시나리오는 **단일 운용 차원(통제 축)** 하나씩을 변화시킨다. 한 번에 하나의
축만 통제하므로, 도구별 성능 차이를 그 축에 귀속해 해석할 수 있다.

## 2. 스위트 구성 (10종)

| ID | 통제 축 (axis) | 범주 | 소스 시나리오 | 표제 KPI |
|----|----------------|------|----------------|----------|
| **B01** | traffic_density | throughput | `high_density.yaml` (s01) | conflict_resolution_rate_min |
| **B02** | in_flight_failure | safety | `emergency_failure.yaml` (s02) | emergency_response_p99_s |
| **B03** | launch_surge | throughput | `mass_takeoff.yaml` (s03) | separation_violation_count |
| **B04** | deconfliction | safety | `route_conflict.yaml` (s04) | conflict_resolution_rate_min |
| **B05** | lost_link | resilience | `comms_loss.yaml` (s05) | lost_link_recovery_rate_min |
| **B06** | wind_robustness | resilience | `weather_disturbance.yaml` (s06) | route_efficiency_max |
| **B07** | intrusion_security | security | `adversarial_intrusion.yaml` (s07) | detection_rate_min |
| **B08** | multi_region | federation | `multi_city.yaml` (s08) | handover_success_rate_min |
| **B09** | autonomous_formation | autonomy | `swarm_autonomous_no_preplan.yaml` (s09) | conflict_resolution_rate_min |
| **B10** | nominal_baseline | control | `nominal_baseline.yaml` (s10) | conflict_resolution_rate_min |

**B10 공칭 저밀도 기준선**은 충돌·충돌위험이 거의 발생하지 않는 가장 단순한
운용으로, 모든 도구가 통과해야 하는 하한선이자 나머지 9종 지표를 정규화하는
**대조(control) 케이스**다.

> **표제 KPI 주의.** 위 표의 *표제 KPI* 열은 공개 스펙상의 표제 지표 이름이며,
> 10종 중 5종(B03·B04·B05·B06·B08)은 해당 키를 소스 YAML 의 `success_criteria`
> 에 명시하지 않는다(런너가 측정하는 파생 지표). 매니페스트 JSON 은 이 괴리를
> `primary_kpi_in_criteria` 플래그로 기계 판독 가능하게 드러낸다 — 자동화
> 소비자는 `primary_kpi` 를 `success_criteria` 키로 가정하지 말 것.

## 3. 설계 원칙

- **중복 없는 큐레이션 계층.** 시나리오 *정의* 는 `config/scenario_params/*.yaml`
  이 유일 출처(SSoT)다. 큐레이션 모듈 `simulation/standard_scenarios.py` 는
  정의를 복제하지 않고, 통제 축·범주·표제 KPI 메타데이터를 덧붙여 YAML 을
  가리킬 뿐이다.
- **스키마 적합 보장.** 10종 전부 `simulation/scenario_schema.py`
  (GENESIS Phase 322) 의 마켓플레이스 계약을 충족함을 `validate_suite()` 가
  결정적으로 재검증한다 — 즉, 어느 도구든 표준 러너 계약으로 적재할 수 있다.
- **단일 통제 축.** 10개 축은 상호 배타적이다(밀도·장애·이륙 서지·경로 충돌·
  통신 두절·기상·침입·다지역·자율 편대·공칭 기준선).
- **결정적.** 무작위성 0, 항목 순서 고정(B01..B10).

## 4. 사용법

```bash
python -m simulation.standard_scenarios --list       # 10종 요약 표
python -m simulation.standard_scenarios --validate   # 스키마 적합 재검증
python -m simulation.standard_scenarios --manifest   # 공개 매니페스트(JSON)
```

매니페스트(JSON)는 도구 간 교차 벤치마크 교환 포맷이며, 각 항목에 통제 축·범주·
표제 KPI·스키마 적합 여부와 소스 YAML 의 `scenario` 이름·`success_criteria` 를
함께 싣는다.

## 5. 한계 (정직 공시)

- 표제 KPI 열은 *공개 스펙상의 표제 지표 이름* 이며, 일부 소스 YAML 은
  해당 키를 `success_criteria` 에 명시하지 않을 수 있다(런너가 측정하는
  파생 지표). 매니페스트는 YAML 에 존재하는 `success_criteria` 만 그대로
  surface 한다.
- 본 스위트는 *시나리오 정의* 의 표준화이지, 도구별 *측정 방법론* 의
  표준화가 아니다. 측정 절차 합의는 후속 표준화 항목(Phase 470 추적
  대시보드)에서 다룬다.
- B05(`comms_loss.yaml`) 소스 YAML 의 `*_range` 필드(trigger_time·affected_count·
  duration)는 SDACS 런너에서 무시되며 고정 `comms_loss_rate=0.05` 로 변환된다
  (런너 수준 결정적). 호환 런너는 표준 비교를 위해 동일하게 범위를 샘플링하지
  말고 고정 비율을 사용해야 한다.

---

*관련: [`docs/SIMULATOR_ODYSSEY_PLAN.md`](../SIMULATOR_ODYSSEY_PLAN.md) Track 🏛 ·
구현 `simulation/standard_scenarios.py` · 테스트 `tests/test_standard_scenarios.py`*

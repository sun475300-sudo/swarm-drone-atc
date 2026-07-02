# 외부 시뮬레이터 어댑터 스펙 (GENESIS Phase 323)

SDACS 시나리오를 공개 ATM/UTM 시뮬레이터(**BlueSky**·**U-TRAFMAN**)와 양방향으로
교환하기 위한 호환 import/export 규약. 구현: `simulation/external_sim_adapter.py`,
검증: `tests/test_external_sim_adapter.py`.

> **Phase 405 와의 분담** — `simulation/benchmark_comparison.py` (ODYSSEY 405) 는
> 세 시스템의 **기능 범위**를 동일 축으로 비교한다. 본 어댑터는 그 위에서 **실 시나리오
> 데이터를 변환**한다. 비교(405)와 교환(323)은 상호 보완 관계다.

## 1. 설계 — 중립 교환 모델(IR)

포맷마다 N×M 변환기를 두는 대신 단일 중립 표현 `ScenarioExchange` 를 경유한다.
각 포맷은 `IR ↔ 자기 포맷` 변환기 1쌍만 제공한다.

```
   SDACS yaml ──┐                          ┌── BlueSky .scn
                ├──  ScenarioExchange  ──┤
   BlueSky .scn ─┘   (위경도·항공기 집합)   └── U-TRAFMAN JSON
```

`ScenarioExchange` 필드: `name`, `description`, `duration_s`, `ref_lat`, `ref_lon`,
`area_km2`, `aircraft[]`. 각 `ExchangeAircraft`: `acid`, `type_code`, `lat`, `lon`,
`hdg_deg`, `alt_m`, `spd_ms`, `dest_lat`, `dest_lon`.

## 2. 좌표 변환 — 등거리 직사각 투영

SDACS 시나리오는 면적(`area_km2`)·도착률 기반 **통계형**이라 항공기별 위경도가
없다. 어댑터는 기준 원점(기본 목포항 권역 **34.79N / 126.39E**)을 중심으로 한
정사각 영역에 항공기를 배치한다.

```
dlat = y_km / 111.32
dlon = x_km / (111.32 · cos(ref_lat))
```

`local_km_to_latlon` / `latlon_to_local_km` 는 왕복 항등(roundtrip identity)을 만족한다.

## 3. 결정적 물질화(materialization)

`sdacs_to_exchange(scenario, *, ref_lat, ref_lon, seed)` 는 `drone_count` 개 항공기의
출발/목적지를 `np.random.default_rng(seed)` 로 **결정적**으로 배치한다.

- 같은 `(scenario, seed)` → 항상 동일 결과 (재현성, `random.random()` 미사용)
- `drone_profile_distribution` → 결정적 타입 라벨 시퀀스 (키 정렬 후 가중 추출)
- 고도 100 m · 속도 15 m/s 기본값 (통계형 시나리오엔 항공기별 값이 없음)

## 4. BlueSky `.scn` 포맷

BlueSky(Hoekstra & Ellerbroek, *ICRAT 2016*, GPLv3) 스택 명령 규약:

```
00:00:00.00>CRE <acid>,<type>,<lat>,<lon>,<hdg>,<alt_ft>,<spd_kt>
00:00:00.00>DEST <acid>,<dest_lat>,<dest_lon>
```

- 시각 프리픽스 `HH:MM:SS.ss>` — 즉시 생성은 `00:00:00.00>`
- 고도는 **피트**(× 3.280840), 속도는 **노트**(× 1.943844)로 변환
- `#` 주석·빈 줄은 import 시 무시, `CRE` 등장 순서 보존
- `DEST` 없는 항공기는 목적지를 출발점으로 둔다

왕복(`bluesky_to_exchange(exchange_to_bluesky(ex))`)은 좌표 `1e-5°`, 고도 `0.1 m`,
속도 `0.05 m/s` 이내로 복원된다.

## 5. U-TRAFMAN 비행계획 JSON

U-TRAFMAN(멀티에이전트 UAS 교통관리 연구 시뮬레이터)은 비행계획 중심이다.
공개 문서 기반 호환 포맷:

```json
{
  "format": "u-trafman/flight-plan",
  "version": "1.0",
  "scenario": "...",
  "reference_origin": [34.79, 126.39],
  "area_km2": 64.0,
  "duration_s": 600.0,
  "flight_plans": [
    {
      "flight_id": "SD0000",
      "aircraft_type": "MULTIROTOR",
      "origin": [34.79, 126.39],
      "destination": [34.80, 126.40],
      "cruise_alt_m": 100.0,
      "cruise_speed_ms": 15.0,
      "departure_s": 0.0
    }
  ]
}
```

왕복(`utrafman_to_exchange(exchange_to_utrafman(ex))`)은 항공기·기준 원점을 보존한다.

## 6. SDACS 역변환

`exchange_to_sdacs(ex)` 는 IR 을 SDACS 시나리오 dict 으로 되돌리며, 출력은 항상
`scenario_schema.validate_scenario` (GENESIS 322) 계약을 만족한다
(`schema_version: "2.0"`, `drone_count`, `area_km2`, `simulation_duration_s`).

## 7. CLI

```bash
python simulation/external_sim_adapter.py --to-bluesky config/scenario_params/high_density.yaml
python simulation/external_sim_adapter.py --to-utrafman config/scenario_params/high_density.yaml
python simulation/external_sim_adapter.py --from-bluesky out.scn   # → SDACS 시나리오 JSON
```

## 8. 한계 (maturity honesty)

- 물질화 좌표는 **합성**(synthetic)이다 — 실 측량(해도·RTK)·실 항적이 아니다.
- 통계형 시나리오의 도착률·라우팅 규칙은 출발/목적지 쌍으로 단순화된다(웨이포인트·
  시간분산 미반영). 정밀 교환이 필요하면 IR 에 `ADDWPT`·`departure_s` 분산을 확장한다.
- BlueSky/U-TRAFMAN 포맷 규약은 공개 문서·논문 기술 기반이며, 실 실행 검증이 아니라
  포맷 호환을 목표로 한다.
- 새 의존성 없이 동작한다 — 결정적·오프라인.

# 외부 시뮬레이터 어댑터 스펙 (GENESIS Phase 323)

> SDACS 시나리오 ↔ 공개 ATM/UTM 시뮬레이터(BlueSky·U-TRAFMAN) **상호 변환** 포맷.
> 구현: [`simulation/external_sim_adapter.py`](../../simulation/external_sim_adapter.py) ·
> 테스트: [`tests/test_external_sim_adapter.py`](../../tests/test_external_sim_adapter.py)

## 1. 목적

SDACS 시나리오를 다른 오픈소스 시뮬레이터로 내보내거나(import/export), 그쪽
시나리오를 SDACS 로 들여오기 위한 **결정적 포맷 변환 계층**을 정의한다. 생태계
상호운용(Phase 321 플러그인 SDK · Phase 322 `.sdacs-scenario` 마켓플레이스 포맷)
연장선이다.

## 2. 정직성 공시 (Honesty Disclosure)

이 어댑터는 **포맷 변환기**다. 외부 시뮬레이터를 실제로 구동·검증하지 않는다.

- **BlueSky** 측은 공개 문서화된 `.scn` 스택 명령 문법(`CRE`/`ADDWPT`)의 **부분집합**을
  대상으로 한다. BlueSky(TU Delft, GPLv3; Hoekstra & Ellerbroek, ICRAT 2016)가 더
  강한 축(유인 통합·대규모 스케일)은 본 어댑터 범위 밖이다.
- **U-TRAFMAN** 측은 공개 단일 정규 스키마가 없으므로, U-TRAFMAN 의 *운항(operation)·
  비행계획(flight plan)* 개념에 정렬한 **SDACS 호환 JSON 교환 포맷**을 정의한다.
  특정 릴리스의 바이트 동일 복제가 아니라 개념 정렬 교환 포맷이다.

핵심 보증: **왕복 항등**(SDACS→외부→SDACS 시 의미 보존)·**결정성**(무작위성·부수효과 0).

## 3. 정규 표현 (Canonical Representation)

측지좌표(WGS84 `lat`/`lon`/`alt`) + SI 단위. BlueSky·U-TRAFMAN 양쪽이 측지계를 쓴다.

| 타입 | 필드 |
|---|---|
| `Waypoint` | `lat_deg`, `lon_deg`, `alt_m`, `spd_mps?`(레그 속도, 선택) |
| `Aircraft` | `acid`(식별자), `actype`(기종), `lat_deg`, `lon_deg`, `alt_m`, `hdg_deg`, `spd_mps`, `waypoints[]` |
| `AdapterScenario` | `name`, `ref_lat_deg`, `ref_lon_deg`, `ref_alt_m`(ENU 기준점), `aircraft[]` |

모두 frozen dataclass. 경계에서 fail-fast 검증(위경도 범위·유한값·음수 속도·`acid` 중복·공백 식별자).

## 4. BlueSky `.scn` 매핑

```
# SDACS-SCENARIO <name>
# SDACS-REF <ref_lat> <ref_lon> <ref_alt_m>
00:00:00.00>CRE <acid>,<actype>,<lat>,<lon>,<hdg>,<alt_ft>,<spd_kt>
00:00:00.00>ADDWPT <acid>,<lat>,<lon>,<alt_ft>[,<spd_kt>]
```

- 모든 명령 앞에 시각 접두 `00:00:00.00>` (t=0 일괄 스폰).
- 고도 ft(`1 ft = 0.3048 m`)·속도 kt(`1 kt = 0.514444 m/s`) 변환. SDACS 정규형은 SI 유지.
- SDACS 기준점·시나리오명은 `#` 메타 주석으로 보존 → BlueSky 는 `#` 줄 무시, 왕복 보존.
- 가져오기는 `CRE`/`ADDWPT` 만 의미로 해석하고 `DEST` 등 기타 명령은 무시한다.
- 인자 구분자는 쉼표/공백 혼용 허용(BlueSky 관용).

## 5. U-TRAFMAN-호환 JSON 매핑

```json
{
  "format": "utrafman-compat",
  "format_version": "1.0",
  "scenario": "<name>",
  "reference": {"lat": ..., "lon": ..., "alt_m": ...},
  "operations": [
    {
      "uav_id": "<acid>", "uav_type": "<actype>",
      "heading_deg": ..., "cruise_spd_mps": ...,
      "flight_plan": [
        {"lat": ..., "lon": ..., "alt_m": ..., "spd_mps": ...},
        ...
      ]
    }
  ]
}
```

- SI 단위 유지 → 왕복 무손실(부동소수 항등).
- `flight_plan[0]` = 스폰 상태, 이후 원소 = 경로점. 출력은 키 정렬·결정적.

## 6. ENU 브리지

SDACS 내부는 로컬 ENU 미터를 쓴다. WGS84 ECEF 경유 변환 제공:

- `geodetic_to_enu(lat, lon, alt, ref_lat, ref_lon, ref_alt) → (east, north, up)`
- `enu_to_geodetic(east, north, up, ref_lat, ref_lon, ref_alt) → (lat, lon, alt)` (Bowring 역해)
- `scenario_to_enu(scenario) → [{acid, east_m, north_m, up_m, hdg_deg, spd_mps}, ...]`

왕복 항등: `geodetic→enu→geodetic` 위경도 오차 ≤ 1e-9°, 고도 오차 ≤ 0.1 mm.

## 7. CLI

```bash
python simulation/external_sim_adapter.py --demo                      # 양 포맷 출력
python simulation/external_sim_adapter.py --demo --format bluesky     # .scn 만
python simulation/external_sim_adapter.py --demo --format utrafman    # JSON 만
python simulation/external_sim_adapter.py --self-test                 # 왕복 항등 점검
```

## 8. 불변식 (테스트로 강제)

1. **BlueSky 왕복** — 위경도 1e-7°·고도 1 cm·속도 0.01 m/s 이내 보존(ft/kt 양자화 한계).
2. **U-TRAFMAN 왕복** — SI 유지로 부동소수 항등(1e-12).
3. **ENU 왕복** — 측지↔ENU 1e-9°.
4. **결정성** — 동일 입력 → 바이트 동일 출력(키 정렬·고정소수 포맷).
5. **검증** — 범위 초과·비유한·음수 속도·`acid` 중복·고아 `ADDWPT`·`flight_plan` 공백 거부.
6. **교차 일관성** — 동일 시나리오의 BlueSky 경유·U-TRAFMAN 경유 기하 일치.

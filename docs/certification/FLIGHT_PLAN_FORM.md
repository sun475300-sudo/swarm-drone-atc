# 🏭 비행승인 신청서 자동 생성 (GENESIS Phase 303)

*Created: 2026-06-13 · 근거: 항공안전법 §127·§129, 동법 시행규칙 §306, 별지 제122호서식(무인비행장치 비행승인신청서), 국토교통부 Drone One-Stop(드론 원스톱 민원서비스)*
*면책: 본 도구는 시뮬레이션 시나리오로부터 신청서 **초안**을 생성하는 개발자 보조 자산이다. 인적사항·신고번호·자격번호·보험은 운영자가 직접 기입해야 하며, 실제 제출은 국토교통부 Drone One-Stop 포털을 통해 이루어진다.*

---

## 1. 목적

시뮬레이션 시나리오/기본 설정(`config/*.yaml`)에 이미 정의된 비행 파라미터(대수·고도·구역·시간)를
**별지 제122호서식**의 기계 작성 가능 필드로 결정적으로 변환한다. 운영자는 PII 필드만 채워 제출할 수 있다.

## 2. 산출물

| 산출물 | 경로 |
|---|---|
| 생성 스크립트 | `scripts/generate_flight_plan.py` |
| 회귀 테스트 | `tests/test_flight_plan_form.py` (14건) |
| 출력(런타임) | `reports/flight_plan_<name>.md` / `.json` |

## 3. 실행

```bash
# 기본 설정으로 생성
python scripts/generate_flight_plan.py

# 특정 시나리오로 생성 (config/scenario_params/<name>.yaml)
python scripts/generate_flight_plan.py --scenario high_density

# JSON만
python scripts/generate_flight_plan.py --config config/default_simulation.yaml --format json
```

## 4. 필드 매핑 (서식 ↔ 설정 ↔ 도출)

| 별지 제122호서식 항목 | 출처 | 도출 규칙 |
|---|---|---|
| 비행장치 대수 | `drone_count` / `drones.default_count` | 시나리오 우선, 없으면 기본 설정 |
| 비행 예정 시간 | `simulation_duration_min` / `_s` / `simulation.duration_minutes` | 초 단위는 분으로 환산 |
| 최대 고도(AGL) | `drones.max_altitude_m` / `airspace.bounds_km.z[1]×1000` | 명시값 우선 |
| 비행구역 좌표 | `airspace.home` + `bounds_km.x/y` | WGS84 평면근사(1°≈111.32 km) |
| 용도 | `description` | 시나리오 설명 그대로 |
| BVLOS 여부 | `bvlos` 또는 군집 추론 | 군집(대수>1)이면 기본 BVLOS(특별승인 필요) |
| 야간 비행 | `night` | 기본 아니오 |
| 안전대책 | 시스템 고정 | 5계층 안전망·분리간격·Remote ID·자동 RTB |
| 신청인·조종자·신고번호·보험 | — | `(운영자 기입)` placeholder |

## 5. 설계 원칙

- **결정성**: 동일 입력 → 동일 출력 (RNG 미사용). 회귀 테스트로 보장.
- **PII 분리**: 인적사항은 생성하지 않고 placeholder로 남겨 개인정보 처리 최소화.
- **법령 추적성**: 모든 출력에 근거 조항(시행규칙 §306)을 명시.

## 6. 한계 (Gap)

| 항목 | 현 상태 | 격상 계획 |
|---|---|---|
| 포털 직접 제출(API) | 미지원 — 수기 업로드 | Drone One-Stop 공개 API 부재 시 유지 |
| 관제권/비행제한구역 자동 판정 | 좌표만 산출 | `airspace_reservation.py` 연동(차기) |
| 좌표 정밀도 | 평면근사 | 실 측지 변환은 GENESIS 341(목포 실 좌표) 연계 |

## 🔗 관련

- [`AIR_SAFETY_ACT_MATRIX.md`](AIR_SAFETY_ACT_MATRIX.md) — 시행규칙 §306 매핑 (Phase 301)
- [`../SIMULATOR_GENESIS_PLAN.md`](../SIMULATOR_GENESIS_PLAN.md) — Track 🏭 인증 Phase 301-320
- [`RTM_5LAYER_COVERAGE.md`](RTM_5LAYER_COVERAGE.md) — 5계층 안전망 추적성 (Phase 306)

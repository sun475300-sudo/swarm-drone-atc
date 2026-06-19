# ISO/TC 20/SC 16 (UAS) 표준 동향 추적 매트릭스

**ODYSSEY Phase 462** · 모듈: [`simulation/iso_tc20_sc16_tracker.py`](../../simulation/iso_tc20_sc16_tracker.py) · 테스트: `tests/test_iso_tc20_sc16_tracker.py` (39건 PASS)

ISO 기술위원회 **TC 20**(Aircraft and space vehicles) 산하 소위원회 **SC 16
(Unmanned aircraft systems)** 의 국제 표준을 SDACS 기능에 결정적으로 대응시켜
정렬·갭을 추적하는 동향 매트릭스입니다.

## 위치

| 정렬 축 | Phase | 다루는 체계 |
|---|---|---|
| EASA U-space | 401 | EU 운영/서비스 |
| FAA UTM ConOps v2.0 | 402 | 미국 USS 역할 |
| ICAO UTM Framework Ed.4 | 407 | 글로벌 조화 원칙 |
| **ISO/TC 20/SC 16** | **462** | **국제 표준화(ISO)** |

Phase 401·402·407 이 *운영/규제* 체계 정렬을 다룬다면, 본 Phase 는 *국제
표준화(ISO)* 축을 별도로 추적합니다 — 같은 SDACS 자산을 ISO 표준의 렌즈로
재평가하는 자매편입니다.

## 추적 현황 (as of 2026-06)

| 지표 | 값 |
|---|:-:|
| 추적 표준 | 8건 |
| 발행 완료 | 6건 |
| 개발 중 | 2건 |
| SDACS 정렬 | 4/8 (50%) |
| 갭 | 4건 |

## 표준 카탈로그 ↔ SDACS 정렬

| 표준 | 표제 | 범주 | 상태 | SDACS 정렬 |
|---|---|---|:-:|---|
| ISO 21384-1 | General specification | General & Vocabulary | 개발중 | — (갭) |
| ISO 21384-2 | UAS components | UAS Components | 개발중 | — (갭) |
| ISO 21384-3 | Operational procedures | Operational Procedures | 발행 | `compliance_checker.py` |
| ISO 21384-4 | Vocabulary | General & Vocabulary | 발행 | — (갭) |
| ISO 21895 | Categorization & classification | Categorization & Safety | 발행 | `sora_category.py` |
| ISO 23665 | Training for personnel | Training & Personnel | 발행 | — (갭) |
| ISO 23629-5 | UTM functional structure | UTM / Traffic Management | 발행 | `federation_discovery.py` |
| ISO 23629-7 | UTM data model (spatial) | UTM / Traffic Management | 발행 | `operational_intent.py` |

## 정직한 갭 (4건)

- **ISO 21384-1 / -2** — 시스템·구성품 *하드웨어* 사양. 본 시뮬레이터는 물리
  구성품을 모델링하지 않으므로 범위 밖.
- **ISO 21384-4 (Vocabulary)** — 전용 표준 용어집 모듈 부재.
- **ISO 23665 (Training)** — 운영 인력 훈련/자격 관리 모듈 부재.

본 매트릭스의 가치는 정렬 주장보다 *미정렬 항목의 가시화* 에 있습니다.

## 정직 공시

- `status` 와 표준 발행/개발 단계는 **프로젝트가 추적하는 스냅샷**(`AS_OF = 2026-06`)
  이며 공식 권위는 ISO 카탈로그([iso.org](https://www.iso.org/committee/5336224.html))
  입니다. 정확한 판(edition)·발행 연도는 ISO 카탈로그로 확인해야 합니다. 본
  매트릭스는 표준 *번호와 표제* 의 안정성에 의존할 뿐, 시기 주장에 의존하지 않습니다.
- `sdacs_module` 은 해당 표준의 범위를 *실제로* 다루는 리포 내 모듈을 가리키며,
  테스트 `test_cited_modules_exist_on_disk` 가 인용 경로의 디스크 실재를 강제합니다.
- 매핑은 기능적 대응이며 ISO 적합성 *인증* 이 아닙니다.

## CLI

```bash
python simulation/iso_tc20_sc16_tracker.py --report      # 추적 요약
python simulation/iso_tc20_sc16_tracker.py --matrix      # 전체 매트릭스
python simulation/iso_tc20_sc16_tracker.py --category "UTM / Traffic Management"
python simulation/iso_tc20_sc16_tracker.py --gaps        # 미정렬(갭)
python simulation/iso_tc20_sc16_tracker.py --published   # 발행 완료 표준
```

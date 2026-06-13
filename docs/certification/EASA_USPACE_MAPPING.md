# 🇪🇺 EASA U-space U1–U4 서비스 ↔ SDACS 기능 매핑 (ODYSSEY Phase 401)

*Created: 2026-06-13 · 근거: EU Reg (EU) 2021/664 (U-space 규제 프레임워크) · SESAR CORUS ConOps v3 (U1–U4 단계)*

> SDACS는 K-UTM(국토부)·LAANC(FAA) 정렬을 이미 보유한다. 본 문서는 이를 **EASA U-space**
> 4단계(U1 Foundation → U4 Full)에 매핑해, 유럽 운용 시 USSP(U-space Service Provider) 역할
> 요건과의 정합·격차를 식별한다. ODYSSEY Phase 402(FAA UTM)·407(ICAO Ed.4)과 함께 3대 체계
> 동시 호환의 EU 축을 담당한다.

---

## 1. U-space 규제·아키텍처 배경

- **법적 근거**: (EU) 2021/664 — U-space 공역 내 운용은 인증된 **USSP**를 통해야 한다.
- **필수 서비스 4종** (2021/664 §-Annex): ① Network Identification ② Geo-awareness
  ③ UAS Flight Authorisation ④ Traffic Information.
- **단계 모델** (SESAR CORUS): U1 Foundation → U2 Initial → U3 Advanced → U4 Full.
  단계가 올라갈수록 자동화 수준(LoA)·교통 밀도·DAA 의존도가 높아진다.

## 2. U1 Foundation 서비스 매핑

| U-space 서비스 | SDACS 기능 | 모듈 | 성숙도 |
|---|---|---|:-:|
| e-Registration | 드론 프로파일·식별자(`D-NNN`) 등록 | `simulation/drone_agent.py` | production |
| e-Identification (Network RID) | ASTM F3411 v2.0 Remote ID 방송 | `src/utm/remote_id.py` | beta |
| Geo-awareness (정적 지오펜스) | NFZ 지오펜스 + 고도 레이어 제약 | `_sdacs.addNFZ()` / `ALTITUDE_LAYERS` | production |

## 3. U2 Initial 서비스 매핑

| U-space 서비스 | SDACS 기능 | 모듈 | 성숙도 |
|---|---|---|:-:|
| UAS Flight Authorisation | 비행계획 제출·승인 상태기계 | `simulation/kutm_protocol.py` (`PlanStatus`) | production |
| Strategic Deconfliction | CBS 사전 경로 충돌 해소 | `simulation/cbs_planner/` | production |
| Tracking | 2Hz 텔레메트리 스냅샷(표준 스키마) | `ws_bridge.py` + `docs/schemas/telemetry.schema.json` (Phase 466) | production |
| Dynamic Geofencing | 동적 NFZ + NOTAM 주입 | `src/utm/notam_manager.py` | beta |
| Conformance Monitoring | 경로 이탈·고도 위반 감지 | `_sdacs` 적대/INJ 계층 | beta |
| Weather Information | 풍속장 모델 (강풍 모드 APF 전환) | `simulation/` WindModel + `APF_PARAMS_WINDY` | beta |
| Emergency Management | RTB·HOLD·강하 ATC 명령 | `_sdacs.atcCommand()` | production |
| Procedural ATC Interface | ATC 명령 9종 + 감사 로그 | `_sdacs.atcCommand()` / CSV 감사 | production |

## 4. U3 Advanced 서비스 매핑

| U-space 서비스 | SDACS 기능 | 모듈 | 성숙도 |
|---|---|---|:-:|
| Tactical Deconfliction / DAA | CPA 90초 예측 + APF 회피 (5계층 안전망) | 5계층 안전망 | production |
| Automated Conflict Resolution | APF + CBS 재계획 협조 | avoidance + CBS | production |
| Dynamic Capacity Management | 고밀도 시나리오 처리량 한계 측정 | `config/scenario_params/high_density.yaml` | beta |
| Collaborative Interface (다중 USSP) | 연합 인스턴스 디스커버리·핸드오버 | ODYSSEY 421-430 (계획) | speculative |

## 5. U4 Full 서비스 매핑

| U-space 서비스 | SDACS 기능 | 모듈 | 성숙도 |
|---|---|---|:-:|
| Full ATM/U-space Integration | 유인-무인 통합 공역 모델 | ODYSSEY 408 공역 클래스 매핑 | beta |
| High Level of Automation (LoA) | 자율 등급(ALFUS) 자가 평가 | GENESIS 376-380 (계획) | speculative |
| Full Free Routing | 사전계획 없는 자율 군집 | `config/scenario_params/swarm_autonomous_no_preplan.yaml` | beta |

## 6. USSP 역할 요건 갭 분석

| (EU) 2021/664 요건 | SDACS 현황 | 격차 | 격상 경로 |
|---|---|---|---|
| 4종 필수 서비스 제공 | 4종 모두 기능 보유(RID·NOTAM은 beta) | RID 송출 실 HW·실 USSP 인증 부재 | Track A 실기 + 인증 절차 |
| 단일 CIS(Common Information Service) 연동 | 단일 인스턴스 내 정보 공유만 | 인스턴스 간 CIS 미구현 | ODYSSEY 421-431 연합 |
| 좌표계·시간대 일관성 | UTM 존 자동 판정 (Phase 406) | — | ✅ `simulation/geo_zones.py` |
| EASA SORA 카테고리 판정 | iGRC/ARC→SAIL (GENESIS 302) | Open/Specific/Certified 분기 부분 | ODYSSEY 403 확장 |
| 분리 최소치(separation minima) 공시 | CPA 90초·APF 이격 내부값 | EU 표준 수치 공개 미정렬 | ODYSSEY 446 검정력 분석 연계 |

## 7. 차기 격상 제안

1. **Phase 403** — `_sdacs.soraAssess()`에 EASA Open/Specific/Certified 카테고리 판정 분기 추가.
2. **Phase 421–431** — 연합 인스턴스 디스커버리로 다중 USSP·CIS 상호운용 모델 확보.
3. RID 송출(`remote_id.py`)을 beta → production 격상: 실 HW 방송 검증(Track A).

## 🔗 관련
- [`AIRSPACE_CLASS_MAPPING.md`](AIRSPACE_CLASS_MAPPING.md) — ICAO Class A-G (Phase 408)
- [`../SIMULATOR_ODYSSEY_PLAN.md`](../SIMULATOR_ODYSSEY_PLAN.md) — Track 🌏 Global Expansion Phase 401-420
- `simulation/geo_zones.py` — 다국 좌표계·시간대 (Phase 406)
- 외부: [EU Reg 2021/664](https://eur-lex.europa.eu/eli/reg_impl/2021/664/oj) · [SESAR CORUS ConOps](https://www.sesarju.eu/node/3411)

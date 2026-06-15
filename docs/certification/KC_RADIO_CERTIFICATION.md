# 📡 KC 전파인증 체크리스트 (GENESIS Phase 304)

*Created: 2026-06-12 · Updated: 2026-06-14 (실행 모듈 추가) · 근거: 전파법 §58의2, 방송통신기자재등의 적합성평가에 관한 고시(과기정통부)*
*면책: 본 문서는 SDACS가 사용·언급하는 통신 모듈별 인증 요건 매핑이며, 실 운영자는 최신 고시·NRRA 공지를 확인해야 한다.*

> **실행 모듈**: 본 체크리스트의 분류 규칙은 [`simulation/kc_certification.py`](../../simulation/kc_certification.py)에
> 결정적으로 구현되어 있다(테스트 [`tests/test_kc_certification.py`](../../tests/test_kc_certification.py) — **23건 PASS**).
> 모듈은 주파수·송신여부·공중선전력·종류로부터 적합인증/적합등록을 분류하고 유형별 제출서류를 생성한다.
> §1 표는 SDACS가 다루는 모듈의 큐레이션 목록이며, 실행 모듈은 대역·전력 기반으로 일반화한다.

---

## 1. SDACS가 다루는 통신 모듈 분류

| ID | 모듈 / 표준 | 사용처 | 인증 카테고리 |
|---|---|---|:-:|
| M1 | Wi-Fi (2.4/5 GHz) | 시뮬레이터 LAN·ws_bridge | 적합등록 |
| M2 | Bluetooth Low Energy (2.4 GHz) | Drone↔Operator 보조 | 적합등록 |
| M3 | LTE / 5G NR (LPWA) | 광역 텔레메트리 (Phase 35 MEC) | 사업자 단말 식별 |
| M4 | 920 MHz ISM (LoRa) | 백업 텔레메트리 | 적합등록¹ |
| M5 | GPS (1.575 GHz, 수신만) | 위치 측정 | 적합등록 |
| M6 | RTK GPS 송신 (Base station, 920 MHz) | 정밀 위치 (Phase 22) | 적합등록¹ |
| M7 | Remote ID 송출 (Wi-Fi/BT) | ASTM F3411 v2.0 (P693) | M1·M2와 동일 |

> ¹ 917–923.5 MHz는 한국 비면허 특정소출력(RFID/USN) 대역이므로 공중선전력 한도 이내면
> **적합등록** 대상이다(한도 초과·면허대역 변형은 적합인증으로 격상 — 실행 모듈이 자동 판정).

## 2. 인증 흐름 (drone 1대 양산 기준)

1. **사전 분류** — 사용 모듈 ID 목록 → 카테고리 매핑
2. **공인 시험기관 위탁** — RRA 지정 시험소(예: KOLAS 인정)에 모듈별 EMC + 전파특성 시험 의뢰
3. **신청서 제출** — 한국방송통신전파진흥원(KCA) 전자민원 (방송통신기자재등의적합성평가신청서)
4. **인증서 발급** — 통상 30~60일
5. **KC 마크 부착** — 본체·포장에 KC + 식별부호 표기 (필수)
6. **사후관리** — 시중 유통품 무작위 시험 가능 (변경 시 재신청)

## 3. 필수 첨부 자료 체크리스트

- [ ] 신청서 (KCA 양식 1호) + 제조자/수입자 정보
- [ ] 시험성적서 (공인 시험기관 발행, 영문 가능)
- [ ] 사용설명서 + 회로도 + PCB 레이아웃 (방사 평가)
- [ ] 안테나 사양서 (송신 시) — 이득·VSWR
- [ ] 전원 사양 (DC 입력 / 배터리 셀 구성)
- [ ] FCC ID / CE 인증서 (해외 호환 부품일 경우 — 동등성 평가 자료)
- [ ] 모듈 일련번호 부착 방법 및 견본 사진

## 4. SDACS 모듈별 인증 단계 매핑

| 모듈 | SDACS 컴포넌트 | 격상 단계 (인증 관점) |
|---|---|---|
| M1 Wi-Fi | `ws_bridge.py` (운영자 LAN) | 표준 Wi-Fi 칩셋 사용 가정 → 적합등록 충족 |
| M2 BLE | (현재 미사용) | Remote ID BT 송출 시 M1·M2 둘 다 필요 |
| M3 LTE | Phase 35 MEC mock | 격상 시 SKT/KT/LGU+ 단말 식별(IMEI) 등록 |
| M4 LoRa | (현재 미사용, 향후 LPWA 옵션) | 917–923.5 MHz 비면허 대역 — 적합등록 (한도 초과 시 적합인증) |
| M5 GPS Rx | Phase 22 HITL 시뮬 | 수신만 → 적합등록 |
| M6 RTK Tx | RTK base station (사용자 HW, P694) | 사용자 환경 — 본 문서 범위 밖 |
| M7 Remote ID | `src/utm/remote_id.py` (P693) | M1·M2와 동일 (송출 방식 선택) |

## 5. 출하 전 자가 점검 (개발자용)

```
[ ] KC 마크가 본체에 부착되어 있는가?
[ ] 식별부호(인증번호)가 라벨에 명확히 표시되어 있는가?
[ ] 안테나가 인증 시점 사양과 동일한가? (이득 변경 시 재인증)
[ ] FW OTA 업데이트 시 전파 특성에 영향이 없는가? (영향 시 재인증)
[ ] 사용설명서에 KC 적합성 평가 문구가 포함되어 있는가?
```

## 6. 갭 분석 (SDACS 현 상태)

| 영역 | 현재 | 격차 | 격상 |
|---|---|---|---|
| Wi-Fi/BLE 인증 | 사용자 HW 의존 | 본 프로젝트는 SW만 — 인증 대상 외 | (해당 없음) |
| 920 MHz LoRa | 사용 안 함 | — | 필요 시 추가 인증 절차 추가 |
| LTE/5G | mock | 실 모듈 격상 시 사업자 단말 식별 별도 | TRANSCENDENCE 263·GENESIS 365 |
| Remote ID 송출 | `remote_id.py` 시뮬만 | 실 HW 송출 시 M1/M2 인증 부속 | Track A 실기 검증 시 |

## 🔗 관련
- [`AIR_SAFETY_ACT_MATRIX.md`](AIR_SAFETY_ACT_MATRIX.md) — 항공안전법 매트릭스 (Phase 301)
- [`RTM_5LAYER_COVERAGE.md`](RTM_5LAYER_COVERAGE.md) — 5계층 안전망 추적 (Phase 306)
- [`../hardware/remote_id_broadcast.md`](../hardware/remote_id_broadcast.md) — Remote ID 가이드 (P693)
- 외부: [방송통신기자재 적합성평가 (KCA)](https://emc.kca.kr/)

# 🎖 조종자 자격증명 ↔ SDACS 교육 모드 매핑 (GENESIS Phase 309)

*Created: 2026-06-12 · 근거: 항공안전법 §125·§131, 시행규칙 §306·§307, 무인비행장치 조종자 증명 운영세칙*

> 본 문서는 한국 무인비행장치 조종자 자격 1~4종 요건을 SDACS의 교육·시뮬레이터 기능에
> 매핑한다. 자격 취득은 외부 절차이며, 본 매핑은 **사전 학습·시뮬 실습 모듈** 가이드다.

---

## 1. 자격 등급 요약 (2026 현행 기준)

| 등급 | 대상 기체 | 최대이륙중량 | BVLOS | 야간 | 비고 |
|---|---|:-:|:-:|:-:|---|
| **1종** | 자체중량 25kg 초과 ~ 사업용 | 150kg | △ (특별승인) | △ (특별승인) | 실기 의무 |
| **2종** | 자체중량 7kg 초과 25kg 이하 | 25kg | × | × | 실기 의무 |
| **3종** | 자체중량 2kg 초과 7kg 이하 | 7kg | × | × | 온라인 + 비행경력 |
| **4종** | 자체중량 250g 초과 2kg 이하 | 2kg | × | × | 온라인 수강만 |

## 2. 과목별 SDACS 매핑

### 공통 학과 (1·2·3종)

| 과목 | 핵심 주제 | SDACS 매핑 | 시뮬 실습 |
|---|---|---|---|
| 항공법규 | 항공안전법·드론활용촉진법 | [`AIR_SAFETY_ACT_MATRIX.md`](AIR_SAFETY_ACT_MATRIX.md) (12조항) | `_sdacs.soraAssess()` 실행으로 SAIL 산정 체험 |
| 항공기상 | METAR/TAF·풍속·시정 | Phase 23 풍속장·`src/utm/metar_parser.py` | `_sdacs.enableWindField(true)` |
| 비행이론 | 양력·항력·추력 + 멀티콥터 동역학 | `simulation/drone_agent.py` 비행 모델 | KPI 패널 — 배터리·고도 관계 관찰 |
| 비행운용이론 | 비행계획·인적요인·CRM | `_sdacs.missionTemplate('recon_orbit')` | 5종 미션 템플릿 실행 |

### 실기 (1·2종)

| 항목 | 평가 포인트 | SDACS 매핑 |
|---|---|---|
| 비행 전 점검 | 기체·조종기·배터리 | `kpiList()` "평균 배터리" / Phase 25 노화 모델 |
| 이착륙 | 안정성·방향 정확도 | 시뮬에서는 자동 — 교육 모드 단계 1 |
| 정지비행 | 위치 유지 | Phase 1 ATC HOLD 명령 시연 |
| 직진·곡선·8자 | 경로 추종 | 미션 템플릿 `recon_orbit` |
| 비상절차 | GPS 손실·모터 페일·통신 두절 | `_sdacs.injectFault(...)` / `injectScenario('EMP')` |

### 자격별 추가 (1종)

| 영역 | SDACS 매핑 |
|---|---|
| 항공 통신 | Phase 36 통신 모듈 + Phase 31 PQC |
| 항공 안전관리 | FMEA `docs/hardware/fmea_report.md` (12 failure modes) + `_sdacs.maturityReport()` |
| 항공 우주 | TRANSCENDENCE 트랙 🚁 HITL 로드맵 |

## 3. 교육 모드 5단계 ↔ 자격 시험 항목

`_sdacs.tutorialStart()` (GENESIS Phase 381 완료) 5단계는 자격 시험의 핵심 개념을 결정적으로 시연한다:

| 튜토리얼 단계 | 자격 시험 매핑 | 학습 효과 |
|:-:|---|---|
| 1 ATC HOLD | 정지비행 + 관제 통신 | 즉시 정지 + 명령 절차 |
| 2 CPA 예측 | 비상절차 (충돌 회피) | 90초 사전 경보 개념 |
| 3 동적 NFZ | 항공법규 (비행제한구역) | 지오펜스 자동 회피 |
| 4 APF 회피 (EMP) | 비상절차 (GPS 손실) | 결손 상황 자동 복구 |
| 5 Maturity 공시 | 항공 안전관리 (시스템 한계 인지) | 인공지능 한계 정직 |

## 4. 비행경력 인정 (참고)

자격 취득 시 요구되는 비행경력은 **실 비행**으로만 인정된다. SDACS 시뮬레이터는 **사전 학습 보조**로만 활용해야 한다.

| 등급 | 비행경력 | 시뮬 대체 가능? |
|:-:|:-:|:-:|
| 1종 | 20시간 (실기) | ❌ |
| 2종 | 10시간 | ❌ |
| 3종 | 6시간 | ❌ |
| 4종 | — (수강) | (해당 없음) |

> **권고**: 자격 취득 전, SDACS 교육 모드로 **5계층 안전망 개념을 학습**한 뒤 실기 훈련을 받으면 학습 곡선 단축 효과를 기대할 수 있다.

## 5. 사후 교육 (자격 취득자용)

자격을 취득한 운영자가 SDACS를 도입할 때 권장 학습 경로:

1. [`presentation/DEFENSE_KIT.md`](../presentation/DEFENSE_KIT.md) §3 알고리즘 Q&A (15분)
2. [`certification/RTM_5LAYER_COVERAGE.md`](RTM_5LAYER_COVERAGE.md) — 21건 추적 매트릭스
3. `_sdacs.tutorialStart()` → 5단계 완주
4. 운영하려는 시나리오에 `_sdacs.soraAssess({populationDensity: <상황>, bvlos: <상황>})` 적용
5. SAIL 등급 ≤ 본인 자격 보유 권한 — 부합 시 운영 / 미부합 시 특별승인 절차

## 🔗 관련
- [`AIR_SAFETY_ACT_MATRIX.md`](AIR_SAFETY_ACT_MATRIX.md) — 법령 12조항 매핑
- [`KC_RADIO_CERTIFICATION.md`](KC_RADIO_CERTIFICATION.md) — 전파인증 가이드
- [`../SIMULATOR_GENESIS_PLAN.md`](../SIMULATOR_GENESIS_PLAN.md) — Track 🎓 교육 Phase 381-400
- 외부: [한국교통안전공단 드론자격증명시스템](https://drone.ts2020.kr/)

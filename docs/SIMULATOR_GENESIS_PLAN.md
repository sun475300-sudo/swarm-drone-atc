# 🌱 SDACS GENESIS Plan — Phase 301-400 초대규모 신규 계획

*Created: 2026-06-12 — TRANSCENDENCE Phase 201-207 (Maturity Honesty) 완료 직후*

> **철학 전환 2단계**: Phase 1-200은 *능력의 차원*을 정의했고(매트릭스), Phase 201-300 TRANSCENDENCE는
> *검증 가능성*으로 무게중심을 옮겼다. Phase 301-400 GENESIS는 **시뮬레이터 바깥의 세계**로 나간다 —
> 인증받고, 생태계를 만들고, 실 지역에 배치되고, 다음 세대에게 물려줄 수 있는 시스템.
>
> TRANSCENDENCE가 "이것은 진짜인가"에 답한다면, GENESIS는 **"이것은 세상에 남는가"** 에 답한다.

---

## 📊 시작점 (2026-06-12 실측 기준선)

| 지표 | 값 | 출처 |
|---|:-:|---|
| `_sdacs` API | 404 (분류 404 = 93/98/110/103 + 헬퍼 3) | `scripts/extract_sdacs_api.py` 라이브 실측 |
| 종합 자동 검증 | 4,443 pass / 9 skip / 0 fail | 회귀 4,180 + E2E 263 |
| 데스크탑 | v1.5.0 (Win/Mac/Linux) | GitHub Releases |
| 선행 계획 | TRANSCENDENCE 201-300 (7% — 201-207 완료) | [`SIMULATOR_TRANSCENDENCE_PLAN.md`](SIMULATOR_TRANSCENDENCE_PLAN.md) |
| 실행 일정 | 2026 H2 마스터플랜 4 트랙 | [`MASTER_PLAN_2026H2.md`](MASTER_PLAN_2026H2.md) |

**전제**: GENESIS는 TRANSCENDENCE Phase 220 (Maturity 격상 1차) 도달 후 본격 착수.
단, 🏭 Track 인증 조사·🎓 Track 교육 자산화는 문서 작업이라 **즉시 병행 가능**.

---

## 🎯 5대 GENESIS 트랙 (각 20 Phase)

### Track 🏭 — Certification & Compliance (Phase 301-320) · 인증·규제 적합

*시뮬레이터/관제 스택을 한국 항공 규제 체계에 정렬. 기존 자산: `src/utm/`(K-UTM·LAANC·ICAO Doc 10019), `docs/track_f/p749_security_audit.md`(KISA CSAP)*

- **Phase 301** 항공안전법·드론활용촉진법 적합성 매트릭스 — 조항 ↔ SDACS 기능 매핑 문서
- **Phase 302** ✅ SORA 자동 계산기 — `_sdacs.soraAssess()` (JARUS 2.0 iGRC/완화/ARC→SAIL 결정적 구현, production 등급, E2E 6건) (2026-06-12)
- **Phase 303** 비행계획 신고 양식 자동 생성 — Drone One-Stop 신청서 export
- **Phase 304** KC 전파인증 요건 체크리스트 (통신 모듈별)
- **Phase 305** DO-178C/ED-12C 소프트웨어 수명주기 갭 분석 — DAL-D 기준 추적성
- **Phase 306** 요구사항 추적 매트릭스(RTM) 자동 생성 격상 — `scripts/generate_rtm.py` → 5계층 안전망 커버리지
- **Phase 307** ✅ 사고 보고 양식 (항철위 표준) 자동 작성 — `simulation/incident_report.py` (분석 이벤트 → 항공기사고/준사고/항공안전장애 분류) + `scripts/generate_incident_report.py` CLI, 단위 테스트 13건 (2026-06-13)
- **Phase 308** 보험 요율 산정 인터페이스 (Phase 67 mock 격상 — 실 보험사 API 스펙)
- **Phase 309** 조종자 자격(1~4종) 요건 ↔ 시뮬 교육 모드 매핑
- **Phase 310** 야간·비가시 특별비행승인 요건 시뮬 검증 시나리오
- **Phase 311-315** KISA CSAP 96항목 자가진단 자동화 (`security_audit.sh` 확장)
- **Phase 316-320** UAM 운용기준(K-UAM 로드맵 2.0) 정렬 + 감항 인증 준비 문서

**산출물**: `docs/certification/` 디렉터리 + `_sdacs.soraAssess()` production API

### Track 🌍 — Ecosystem & Open Source (Phase 321-340) · 생태계·오픈소스

*1인 캡스톤 → 커뮤니티 자산. 기존 자산: MIT 라이선스, `docs/track_f/p753_licensing.md`, CONTRIBUTING*

- **Phase 321** 플러그인 SDK v1 — `_sdacs.registerPlugin()` (시나리오·센서·UI 패널 주입 인터페이스)
- **Phase 322** 시나리오 마켓플레이스 포맷 — `.sdacs-scenario` 스키마 + 검증기
- **Phase 323** 외부 시뮬레이터 어댑터 스펙 공개 — BlueSky·U-TRAFMAN 호환 import/export
- **Phase 324** npm 패키지 `@sdacs/core` 분리 — 충돌 감지(CPA·APF) 순수 JS 모듈 추출
- **Phase 325** PyPI 패키지 `sdacs-sim` — SwarmSimulator 코어 배포
- **Phase 326** GitHub Discussions 운영 체계 + 이슈 템플릿 정비
- **Phase 327** Good First Issue 큐레이션 20건 + 멘토링 라벨
- **Phase 328** 다국어 문서 확장 — README EN 완역 (기존 25언어 i18n 위)
- **Phase 329** 데모 갤러리 사이트 — Pages에 시나리오별 영상·스크린샷 자동 게시
- **Phase 330** 학술 인용 추적 — CITATION.cff + Zenodo DOI 연동 (TRANSCENDENCE 283 연계)
- **Phase 331-335** 플러그인 레퍼런스 구현 3종 (기상 데이터 소스·커스텀 드론 모델·KPI 위젯)
- **Phase 336-340** v2.0 API 안정화 선언 — SemVer 보장 + deprecation 1년 정책

**산출물**: 플러그인 SDK + 2개 패키지 레지스트리 배포 + 커뮤니티 인프라

### Track 🏙 — Real Deployment (Phase 341-360) · 실 지역 실증 서비스

*목포·전남 실증. 기존 자산: `docs/track_f/p747_marine.md`(해수부)·`p748_forest.md`(산림청), `src/applications/`(농업 방제·의료 배송), helm 차트*

- **Phase 341** 목포 해역 실 좌표계 임포트 — 해도 기반 NFZ·회랑 실측 배치
- **Phase 342** 전남 도서지역(신안·완도) 의료 배송 경로 DB — `medical_delivery.py` 실 거점 적용
- **Phase 343** 실 기상 연동 운영 모드 — KMA API 실시간 풍속장 (TRANSCENDENCE 227 연계)
- **Phase 344** 지자체 관제 대시보드 화이트라벨 — 로고·권한·지역 설정 패키지
- **Phase 345** 24시간 무인 운영 모드 — 자동 복구·알림(Grafana 알람 → 문자)
- **Phase 346** 운영자 교대 인수인계 로그 — 시프트 리포트 자동 생성
- **Phase 347** 실증 데이터 수집 동의·개인정보 처리 방침 (영상 촬영 고지)
- **Phase 348** 항만 선박 감지 실증 — 해양 시뮬레이터 ↔ 실 AIS 피드 연결
- **Phase 349** 산불 감시 시나리오 실증 — IR 카메라 스펙 정합 (p748 연계)
- **Phase 350** 농업 방제 실증 — `agri_spray.py` 실 필지 폴리곤 적용
- **Phase 351-355** 파일럿 운영 90일 — SLA 99% 측정·NPS 수집·운영 비용 산정
- **Phase 356-360** 실증 백서 발간 — 지자체·기관 제출용 성과 보고서

**산출물**: 실 좌표 기반 운영 모드 + 90일 파일럿 백서

### Track 🤖 — Next-Gen Autonomy (Phase 361-380) · 차세대 자율

*온보드 지능·차세대 통신. 기존 자산: `src/rl/ppo_collision.py`, `src/llm/voice_atc.py`, Jetson 가이드, PQC*

- **Phase 361** 온보드 RL 추론 — PPO 정책 ONNX export → Jetson 실 추론 벤치
- **Phase 362** 충돌 회피 하이브리드 모드 — APF(규칙) + RL(학습) 가중 블렌딩, 규칙 우선 안전 보장
- **Phase 363** LLM 관제 보조 production 격상 — `voice_atc.py` 스트리밍 + 명령 확인 2단계
- **Phase 364** V2X 메시지 스펙 — 드론↔드론 직접 교신 (BSM 유사 포맷)
- **Phase 365** 5G NTN(비지상 네트워크) 링크 모델 — 지연·핸드오버 시뮬
- **Phase 366** GPS 거부 환경 항법 — VIO/UWB 폴백 모델 (Phase 22 RTK 보완)
- **Phase 367** 스웜 자가 치유 — 결손 드론 임무 자동 재분배 (CBS 재계획 연계)
- **Phase 368** 에너지 인식 임무 계획 — 풍속장 기반 소모 예측 경로 (energy_optimizer 연계)
- **Phase 369** 적대 환경 강건성 — GPS 스푸핑·재밍 탐지 시나리오 (C-UAS 방어 측)
- **Phase 370** 군집 이상 탐지 온라인화 — Isolation Forest 실시간 스트림 적용
- **Phase 371-375** 디지털 트윈 양방향 — 실 드론 상태 → 시뮬 반영 → 예측 → 권고 루프
- **Phase 376-380** 자율 등급(ALFUS) 자가 평가 — 임무별 자율 수준 리포트

**산출물**: 온보드 추론 벤치 + 하이브리드 회피 + 양방향 트윈

### Track 🎓 — Education & Legacy (Phase 381-400) · 교육·레거시

*졸업 후에도 살아있는 시스템. 기존 자산: `docs/track_f/p754_mentoring.md`, 캡스톤 보고서 v200, v6/v7 보고서*

- **Phase 381** 교육 모드 — 시뮬레이터 내 단계별 튜토리얼 (관제 개념 → 5계층 안전망)
- **Phase 382** 실습 과제 10종 — 학부 수업용 (시나리오 + 채점 기준 + `_sdacs` 검증 스크립트)
- **Phase 383** 강의 슬라이드 패키지 — 15주 커리큘럼 (드론 관제 시스템 설계)
- **Phase 384** 조종자 자격 이론 연계 문제은행 — 시뮬 상황 ↔ 기출 유형 매핑
- **Phase 385** 후속 기수 온보딩 자동화 — 환경 구축 1-스크립트 + 아키텍처 투어 노트북
- **Phase 386** 코드 고고학 가이드 — 200 Phase 히스토리 내비게이션 (커밋 → Phase 매핑)
- **Phase 387** 졸업 심사 발표 키트 — 시연 시나리오 + 예상 질문 50 + 라이브 데모 체크리스트
- **Phase 388** ✅ 기술 부채 대장 — `docs/TECH_DEBT_LEDGER.md` 자동 생성 (`extract_sdacs_api.py --ledger`, mock 110 + speculative 103 그룹별 난이도) (2026-06-12)
- **Phase 389** 유지보수 최소 모드 정의 — 1인 유지 가능한 코어 서브셋 명세
- **Phase 390** 아카이브 전략 — Zenodo 스냅샷 + Software Heritage 등재
- **Phase 391-395** 고교·일반인 체험판 — 단순화 UI 모드 (v7 쉬운 설명 연계)
- **Phase 396-400** **Phase 400 = SDACS Legacy 선언** — 인수인계 완료·생태계 자생·교육 자산 공개

**산출물**: 15주 커리큘럼 + 온보딩 자동화 + Legacy 선언문

---

## 🎯 우선순위 매트릭스 (즉시 착수 가능 Top 10)

| Phase | 트랙 | 임팩트 | 난이도 | sandbox 가능 |
|---|---|:-:|:-:|:-:|
| 302 SORA 자동 계산기 | 🏭 인증 | 🔥🔥🔥🔥🔥 | ⭐⭐ | ✅ |
| 306 RTM 5계층 커버리지 | 🏭 인증 | 🔥🔥🔥🔥 | ⭐⭐ | ✅ |
| 321 플러그인 SDK v1 | 🌍 생태계 | 🔥🔥🔥🔥🔥 | ⭐⭐⭐ | ✅ |
| 324 `@sdacs/core` 분리 | 🌍 생태계 | 🔥🔥🔥🔥 | ⭐⭐⭐ | ✅ |
| 341 목포 해역 실 좌표 | 🏙 실증 | 🔥🔥🔥🔥🔥 | ⭐⭐ | ✅ |
| 362 하이브리드 회피 | 🤖 자율 | 🔥🔥🔥🔥 | ⭐⭐⭐ | ✅ |
| 367 스웜 자가 치유 | 🤖 자율 | 🔥🔥🔥🔥 | ⭐⭐⭐ | ✅ |
| 381 교육 모드 튜토리얼 | 🎓 교육 | 🔥🔥🔥🔥🔥 | ⭐⭐ | ✅ |
| 387 졸업 심사 발표 키트 | 🎓 교육 | 🔥🔥🔥🔥🔥 | ⭐ | ✅ |
| 388 기술 부채 대장 | 🎓 교육 | 🔥🔥🔥🔥 | ⭐ | ✅ |

**권장 즉시 착수**: Phase 387(발표 키트)·388(부채 대장)·302(SORA)·381(교육 모드) — 캡스톤 심사 직결 + 전부 sandbox 가능.

---

## 📈 누적 KPI 목표 (GENESIS)

| 지표 | Phase 300 (목표) | Phase 320 | Phase 360 | Phase 400 |
|---|:-:|:-:|:-:|:-:|
| Production API | 200 | 230 | 280 | 330 |
| 인증 적합 문서 | 0 | 20종 | 갱신 | 갱신 |
| 외부 기여자 | 0 | 2 | 10 | 30 |
| 패키지 다운로드 | — | — | 500/월 | 2,000/월 |
| 실증 운영 일수 | 0 | 0 | 90일 | 365일 |
| 교육 수료 인원 | 0 | — | 30 | 200 |

---

## 🔁 거버넌스 (GENESIS 추가 게이트)

MASTER_PLAN_2026H2 공통 게이트(회귀 보존·md5 동기화·E2E 동반·실측 수치·mock 격상 근거)에 추가:

1. **규제 정합**: 인증 트랙 산출물은 법령 조항 번호를 인용하고 개정일 추적
2. **하위 호환**: 플러그인 SDK·패키지 공개 후 breaking change는 deprecation 1년
3. **실증 안전**: 실 비행 연계 기능은 시뮬 검증 → HITL → 실증 3단계 강제
4. **교육 검증**: 교육 자산은 비전공 1인 이상 파일럿 테스트 후 공개

## 🗺 전체 Phase 지도 (1-400)

| 구간 | 계획 | 상태 |
|---|---|:-:|
| 1-10 MEGA | [`SIMULATOR_MEGA_PLAN.md`](SIMULATOR_MEGA_PLAN.md) | ✅ |
| 11-50 HYPER | [`SIMULATOR_HYPER_PLAN.md`](SIMULATOR_HYPER_PLAN.md) | ✅ |
| 51-100 STELLAR | [`SIMULATOR_STELLAR_PLAN.md`](SIMULATOR_STELLAR_PLAN.md) | ✅ (51 격상) |
| 101-150 ULTIMATE | [`SIMULATOR_ULTIMATE_PLAN.md`](SIMULATOR_ULTIMATE_PLAN.md) | ✅ |
| 151-200 POST-UNIVERSE | [`SIMULATOR_POST_UNIVERSE_PLAN.md`](SIMULATOR_POST_UNIVERSE_PLAN.md) | ✅ 𝟏 Unity |
| 201-300 TRANSCENDENCE | [`SIMULATOR_TRANSCENDENCE_PLAN.md`](SIMULATOR_TRANSCENDENCE_PLAN.md) | 🟡 7% (201-207) |
| **301-400 GENESIS** | **본 문서** | ⬜ 수립 완료 |
| 실행 일정 | [`MASTER_PLAN_2026H2.md`](MASTER_PLAN_2026H2.md) | 🟢 가동 |

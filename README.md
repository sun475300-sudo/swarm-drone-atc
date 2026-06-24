<div align="center">

# SDACS — Swarm Drone Airspace Control System
### 군집드론 공역통제 자동화 시스템

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![SimPy](https://img.shields.io/badge/SimPy-4.1-4CAF50?style=for-the-badge)](https://simpy.readthedocs.io/)
[![Dash](https://img.shields.io/badge/Dash-2.17-00A0DC?style=for-the-badge&logo=plotly)](https://dash.plotly.com/)
[![NumPy](https://img.shields.io/badge/NumPy-1.26-013243?style=for-the-badge&logo=numpy&logoColor=white)](https://numpy.org/)
[![SciPy](https://img.shields.io/badge/SciPy-1.12-8CAAE6?style=for-the-badge&logo=scipy&logoColor=white)](https://scipy.org/)

[![Phase](https://img.shields.io/badge/Phase-200%20%E2%9C%93-purple?style=for-the-badge&logo=rocket)](docs/phase_matrix.html)
[![SDACS Unity](https://img.shields.io/badge/Phase_200-%F0%9D%9F%8F_Unity-ec407a?style=for-the-badge&logo=infinity)](docs/SIMULATOR_POST_UNIVERSE_PLAN.md)
[![API](https://img.shields.io/badge/__sdacs-407_API-00e5ff?style=for-the-badge&logo=javascript)](docs/SDACS_API.md)
[![E2E](https://img.shields.io/badge/E2E-263%2F264_pass-22c55e?style=for-the-badge&logo=playwright&logoColor=white)](tests/e2e/)
[![Roadmap](https://img.shields.io/badge/Roadmap_691--755-92%25-brightgreen?style=for-the-badge&logo=checkmarx)](ROADMAP.md)
[![Tests](https://img.shields.io/badge/Python_tests-5%2C536_pass_%C2%B7_270_skip-success?style=for-the-badge&logo=pytest&logoColor=white)](tests/)
[![v1.5.0](https://img.shields.io/badge/Desktop-v1.5.0_(Win%2FMac%2FLinux)-7c3aed?style=for-the-badge&logo=electron&logoColor=white)](docs/V1_5_0_RELEASE_INSTRUCTIONS.md)
[![Modules](https://img.shields.io/badge/Modules-830+-9C27B0?style=for-the-badge&logo=python&logoColor=white)](simulation/)
[![Tracks](https://img.shields.io/badge/Tracks_A--F-6_parallel-FF5722?style=for-the-badge&logo=github&logoColor=white)](ROADMAP.md)
[![LOC](https://img.shields.io/badge/Total-160K%2B%20LOC-blue?style=for-the-badge&logo=visualstudiocode&logoColor=white)](#)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](#license)

**Mokpo National University, Dept. of Drone Mechanical Engineering — Capstone Design (2026)**

**국립 목포대학교 드론기계공학과 캡스톤 디자인**

[**⚡ Quick Start**](docs/QUICK_START.md) | [**📄 공개 보고서**](docs/report/SDACS_Public_Project_Report_2026.docx) | [**🎤 소개 PPTX**](docs/presentation/SDACS_Public_Project_Overview_2026.pptx) | [**🌐 Live Site**](https://sun475300-sudo.github.io/swarm-drone-atc/) | [**🛰 3D 시뮬레이터**](https://sun475300-sudo.github.io/swarm-drone-atc/simulator.html) | [**🚢 해양 시뮬**](https://sun475300-sudo.github.io/swarm-drone-atc/maritime_detection_simulator.html) | [**📥 v1.5.0 빌드**](docs/V1_5_0_RELEASE_INSTRUCTIONS.md)

> 🔗 **GitHub Pages 라이브 사이트**: <https://sun475300-sudo.github.io/swarm-drone-atc/> — 랜딩 페이지(소개·성과·아키텍처)에서 3D 시뮬레이터·해양 소형선 감지·시나리오 비교·테스트 리포트로 이동할 수 있습니다.

🌐 **Language / 언어:** **한국어** · [English](README.en.md)

</div>
<div align="center">
<img src="docs/images/imgur/fP5lw8Y.png" alt="SDACS Hero Banner" width="800"/>
</div>

## 📣 공개 프로젝트 설명 자료 / Public Project Materials (2026-06-18)

| 자료 | 대상 | 다운로드 |
|---|---|---|
| **공개 프로젝트 설명 보고서** (DOCX, 5페이지) | 일반 대중 · 학생 · 심사위원 · 공공기관 | [📥 SDACS_Public_Project_Report_2026.docx](docs/report/SDACS_Public_Project_Report_2026.docx) |
| **공개 프로젝트 소개 발표자료** (PPTX, 10장) | 발표 · 수업 · 프로젝트 소개 | [📥 SDACS_Public_Project_Overview_2026.pptx](docs/presentation/SDACS_Public_Project_Overview_2026.pptx) |

> **2026-06-24 로컬 재검증:** `ruff` 통과 · Python 테스트 **5,536 pass / 270 skip / 25 fail**. AIM 정밀검사 9회 완료 (242 테스트). 대표 실행 `100 drones / 60s / seed 42`에서는 **45 collisions · 87 near misses · 95.9% conflict resolution**이 측정되었습니다. 현재 결과는 안전 인증이 아니라 연구용 시뮬레이터의 개선 기준선입니다.

> **최신 업데이트 (2026-06-24)** — Phase 691-700 AIM 모듈 정밀검사 9라운드 완료 (Round 4–12). NaN/Inf 바이패스 차단(`math.isfinite` 가드), CAVOK 위양성 NO-GO 수정, 캡슐화 누수 방지(`copy.copy`), fail-closed 안전 설계, 방어적 복사, 중복 거부 패턴 적용. 10개 소스 파일 강화, **242개 정밀검사 전용 테스트** 추가.
>
> **이전 업데이트 (2026-06-18)** — 공개 설명 보고서와 10장 발표자료 추가 · 전체 Python 테스트 **5,444 pass / 270 skip** · Ruff 전 저장소 통과 · 대표 100대 시뮬레이션의 잔여 충돌을 개선 기준선으로 공개했습니다.
>
> **♾️ 이전 업데이트 (2026-06-12 · API Maturity 정직성 체계 가동 + TRANSCENDENCE/GENESIS/ODYSSEY 계획 체계 · 407 API 라이브 실측 · 종합 4,443 pass / 0 fail)** — 🎯 **신규**: `apiMaturity()`/`maturityReport()` 분류(production 93·beta 98·mock 110·speculative 103) · **Mock Detector**(mock 호출 시 console.warn + `mockCalls` 카운트, Phase 203) · **`experimental.*` 네임스페이스**(speculative 103종 격리, Phase 206) · **`soraAssess()`**(JARUS SORA 2.0 결정적 SAIL 산정, GENESIS 302) · **기술 부채 대장** [TECH_DEBT_LEDGER.md](docs/TECH_DEBT_LEDGER.md) 자동 생성(GENESIS 388) · CI에 문서-실측 정합성 + 4 사본 md5 게이트. 계획 체계 3층: [TRANSCENDENCE 201-300](docs/SIMULATOR_TRANSCENDENCE_PLAN.md)(8%) · [GENESIS 301-400](docs/SIMULATOR_GENESIS_PLAN.md)(2%) · [ODYSSEY 401-500](docs/SIMULATOR_ODYSSEY_PLAN.md)(수립) + [2026 H2 실행 일정](docs/MASTER_PLAN_2026H2.md)
>
> **이전 (200 Phase Unity)** — 🎯 **Phase 200 = SDACS = 𝟏 (Unity)** 도달 후 **Phase 51 (LLM Multi-Agent)** 가 시드에서 완전 격상되었습니다: `stellar51DelegateGroup`(드론 그룹 LLM 위임) · `stellar51Recommend`(상태 기반 결정적 권고) · `stellar51Tick`(그룹 사이클 진행) · `stellar51Groups`(위임 그룹 조회) · `stellar51Revoke`(위임 해제). 5단계 통합 — MEGA(1-10) + HYPER(11-50) + STELLAR(51-100) + ULTIMATE(101-150) + POST-UNIVERSE(151-200). Playwright E2E **263/264 통과**(1 skip), 회귀 **4,180 pass / 8 skip / 0 fail**, 종합 **4,443 pass / 9 skip / 0 fail** (2026-06-12 실측). 🌌 [HYPER](docs/SIMULATOR_HYPER_PLAN.md) · [STELLAR](docs/SIMULATOR_STELLAR_PLAN.md) · [ULTIMATE](docs/SIMULATOR_ULTIMATE_PLAN.md) · [POST-UNIVERSE](docs/SIMULATOR_POST_UNIVERSE_PLAN.md) · [API](docs/SDACS_API.md) · [Phase Matrix](docs/phase_matrix.html)

> **이전 (Phase 100 완료)** — 🌌 (2026-06-05 · MEGA 9 + HYPER 41 + STELLAR 49 = 99 Phase 통합 · 215/216 E2E · 280+ API)** — 🚀 **본 사이클 STELLAR Phase 52-100 일괄 49종**: Track Ω 자율결정(52 RLHF · 53 Causal Inference · 54 Adversarial Robust · 55 Explainable AI) + Track Σ 초대규모(56 GPU 100K WGSL · 57 Distributed Sim · 58 Cloud Burst · 59 10Gb/s Streaming · 60 Video Proc av1) + Track Φ 물리트윈(61 Skybrush · 62 Cesium · 63 UE5 · 64 ROS2 + Gazebo · 65 Isaac Sim) + Track Ψ 사회(66 시민신고·67 보험·68 사고조사·69 RPAS자격·70 교육) + Track Ξ 지구너머(71 Lunar Gateway · 72 Mars 헬리콥터 · 73 소행성 채굴 · 74 궤도 잔해 · 75 DTN) + Track Δ 양자(76 QKD · 77 Photonic · 78 Neuromorphic · 79 SNN · 80 Annealing) + Track Λ XR(81 Vision Pro · 82 Holographic · 83 BCI · 84 Haptic · 85 후각) + Track Π 경제(86 UAM Pricing · 87 Carbon Credit · 88 DaaS Market · 89 NFT · 90 DAO) + Track Π+ Ultimate(91 AGI · 92 글로벌 1:1 · 93 1억 드론 · 94 글로벌 협업 · 95 UN 표준) + Track Ω+ Singularity(96 자기개선·97 디지털 인간·98 메타버스·99 ITU·100 SDACS 2.0 글로벌 표준 ATC OS). **MEGA 9 + HYPER 41 + STELLAR 49 = 99 Phase + Phase 51 시드 = 100 Phase 완료**. Playwright E2E **215/216 통과**, 회귀 **4,140/4,140 통과**. 🌌 HYPER: [`docs/SIMULATOR_HYPER_PLAN.md`](docs/SIMULATOR_HYPER_PLAN.md) · STELLAR: [`docs/SIMULATOR_STELLAR_PLAN.md`](docs/SIMULATOR_STELLAR_PLAN.md) · API: [`docs/SDACS_API.md`](docs/SDACS_API.md)
>
> **이전 업데이트** — **원클릭 로컬 실행**(Win/Mac/Linux 더블클릭) · **해양 소형선 감지 시뮬레이터**(레이더 물리·AIS 융합·EO/IR·COLREG·CPA, 8개 시나리오) · 메인 3D **다중 선택·대규모 성능 측정·경로효율·라벨 풀 최적화**.

---

## 📊 개발 진척 현황 / Development Progress (2026-06-24)

| 트랙 | 범위 | 진척 | 핵심 산출물 |
|---|---|---|---|
| **Core** | Phase 1-690 | ✅ 100% | 시뮬·이론·AI·HW·UTM·AIM (690 phase) |
| **A** 실기 드론 | P691-700 | ✅ 100% | Pixhawk·Jetson·RTK·MoCap·FMEA 가이드 10종 + **AIM 정밀검사 9회 완료** (242 테스트, 실기 검증은 사용자 HW) |
| **B** 논문화 | P701-710 | ✅ 100% | 30편 서베이·LaTeX §1-§7·포스터·Marp 슬라이드·투고 가이드 (IROS 2026 투고 준비) |
| **C** 서비스화 | P711-720 | ✅ 100% | FastAPI+JWT/RBAC·TimescaleDB·K8s·관측성·베타 + React MVP(`frontend/`) |
| **D** 웹 시뮬 | P721-735 | ✅ 100% | 군집·해양 3D + Electron 3-OS + i18n + LIVE + CPA 공간해시 + 멀티뷰 + EO/IR + **ATC 명령 콘솔** |
| **E** 확장 연구 | P736-745 | ✅ 100% | RL PoC·UAS-T·LiDAR·DR·디지털트윈·Raft HA·UAM·양자·폐쇄망·LLM |
| **F** 산학·사업화 | P746-755 | 🟢 90% | K-UAM·해수부·산림청·KISA·라이선싱·창업 docs (P755·LOI는 사용자 환경) |
| **G** TRANSCENDENCE | 시뮬 201-300 | 🟡 11% | 201-210·226 완료 — 성숙도 정직성·API 수명주기·GPS→ENU 정밀 검증 |
| **H** GENESIS | 시뮬 301-400 | 🟡 20% | 인증·규제 301-311 + APF+RL 하이브리드·V2X 메시지·목포 실좌표·교육·발표 자산 완료 |
| **I** ODYSSEY | 시뮬 401-500 | 🟡 38% | FAA UTM 갭 분석·U-space·연합 운영·형식 검증·표준 시나리오·정책 분석·마이그레이션 자산 완료 |

> 상세: [`ROADMAP.md`](ROADMAP.md) · [`STATUS_REPORT.md`](STATUS_REPORT.md) · [`docs/INDEX.md`](docs/INDEX.md)(문서 마스터 인덱스) · [`docs/MASTER_PLAN_2026H2.md`](docs/MASTER_PLAN_2026H2.md)(실행 일정)

### 🚧 미완료 작업 / Open Work Items (정직성 리스트, 2026-06-24 기준)

**사용자 환경 의존 (코드 작업 불가, 4건)**
- [ ] P755 창업·분사 결정 + 외부 기관 LOI 체결
- [ ] Track A 실기 검증 — Pixhawk·Jetson·RTK 실 하드웨어 비행 (가이드 10종은 완비)
- [ ] P707 논문 실측 실험 그래프 → P709 IROS 2026 실제 투고
- [ ] `v1.5.0` 태그 푸시 → 3-OS 자동 빌드 (sandbox push 403 — [1줄 명령 가이드](docs/V1_5_0_RELEASE_INSTRUCTIONS.md))

**시뮬레이터 — MASTER_PLAN Track Ⅰ (시각화 마감, ~2026-07 목표)**
- [ ] CPA 예측선 고도화 — TTC 라벨·위험도 색상
- [ ] 어드바이저리 빌보드 (CLIMB/DESCEND/TURN/EVADE/HOLD 점멸)
- [ ] 리플레이 스크러버-멀티뷰 커서 마감 검증 · 리포트 KPI를 `gen_report` 정의와 1:1 일치 · mega_swarm 1k/5k FPS 실측 표

**TRANSCENDENCE 잔여 (Phase 211-300, Phase 226 완료)**
- [ ] 211-220 production-grade API 확대 — production 12종에서 30종으로 격상
- [ ] 221-240 실측 격상 — WebGPU 실 WGSL·CRDT Yjs·MAVLink SITL·KMA 풍속장 (226 GPS→ENU 정밀 검증 완료)
- [ ] 241-260 다중 사용자 — WS 관제 서버·2-브라우저 협업 E2E·부하 100명
- [ ] 261-280 HITL (사용자 HW) · 281-300 학술 임팩트 (Ablation 자동화는 sandbox 가능)

**GENESIS·ODYSSEY 잔여**
- [ ] GENESIS 312-340 — CSAP 통제 확장·플러그인 SDK·시나리오 마켓·패키지 배포·영문 문서
- [ ] GENESIS 342-380 — 지역 실증·24시간 운영·온보드 RL·V2X·GPS 거부 환경·자가 치유
- [ ] GENESIS 382-400 — 교육 과제·강의 자산·온보딩·아카이브·Phase 400 레거시 선언
- [ ] ODYSSEY 402-420 — FAA/EASA/ICAO 정렬·국제 벤치마크·해외 파일럿 제안
- [ ] ODYSSEY 426-427 — 2-인스턴스 연합 E2E·인접 공역 고스트 렌더링
- [ ] ODYSSEY 451-500 — RL 일반화·표준 기고·장기 운영·거버넌스·아카이브

**AIM 정밀검사 (Phase 691-700, 2026-06-24 완료)**
- [x] **Round 4–12** ✅ AIM 모듈 정밀 강화 9라운드 — `tests/test_phase691_700_aim.py` (242 테스트). 대상: `notam_manager`, `tfr_handler`, `vertiport_ops`, `metar_parser`, `aim_briefing`, `flight_following`, `cross_border_coord`, `post_flight_report`, `aero_charts`, `insurance_risk`. NaN/Inf 바이패스 차단·CAVOK VFR 인식·캡슐화 강화·fail-closed 안전·방어적 복사·중복 거부

**GENESIS·ODYSSEY 진척 (2026-06-18 확인)**
- [x] **GENESIS 301** ✅ 항공안전법·드론활용촉진법 적합성 매트릭스 — [`docs/certification/AIR_SAFETY_ACT_MATRIX.md`](docs/certification/AIR_SAFETY_ACT_MATRIX.md) (12 조항 매핑·격차·운영자 체크리스트)
- [x] **GENESIS 387** ✅ 졸업 심사 발표 키트 — [`docs/presentation/DEFENSE_KIT.md`](docs/presentation/DEFENSE_KIT.md) (10분 데모 시나리오·예상 질문 18개·압박 대응·당일 체크리스트)
- [x] **TRANSCENDENCE 204** ✅ Production 핵심 12종 회귀 강화 — `tests/e2e/test_simulator_production_core.py` (production getter 전수 + 핵심 메서드 호출 + 93 회귀 방지)
- [x] **ODYSSEY 448** ✅ 속성 기반 테스트 — `tests/test_property_telemetry.py` (Hypothesis 1,150+ 케이스, 압축 무손실/유계 오차/충돌해결률 불변식)
- [x] **ODYSSEY 466** ✅ 텔레메트리 JSON Schema 공개 — [`docs/schemas/telemetry.schema.json`](docs/schemas/telemetry.schema.json) (Draft-07) + `tests/test_telemetry_schema.py` (스키마 + 예제 + ws_bridge 정합성)
- [x] **GENESIS 381** ✅ 교육 모드 — `_sdacs.tutorialStart/Next/Status()` 5단계 결정적 튜토리얼(ATC→TAC→UTM→APF→Maturity), E2E 2건
- [x] **GENESIS 306** ✅ RTM 5계층 커버리지 — `docs/certification/RTM_5LAYER_COVERAGE.md` REQ↔DSN↔IMP↔VER 21건 추적
- [x] **GENESIS 389** ✅ 유지보수 최소 모드 — `docs/MAINTENANCE_MINIMAL_MODE.md` (코어 서브셋·일일/분기/연 워크플로·비상 절차)
- [x] **ODYSSEY 447** ✅ 시나리오 fuzzing — `tests/e2e/test_simulator_fuzz.py` Hypothesis로 NFZ·ATC·SORA 140케이스 무패닉 검증
- [x] **ODYSSEY 486** ✅ 독립 재현 자동화 — `scripts/independent_reproduction.sh` (회귀·md5·JS·API 게이트 통합)
- [x] **TRANSCENDENCE 205** ✅ Beta API 부분 검증 — `tests/e2e/test_simulator_beta_subset.py` (Copilot·적대·C-UAS·WindField·PQC 인터페이스 안정·라이프사이클·분류 회귀, 5건)
- [x] **GENESIS 304** ✅ KC 전파인증 체크리스트 — `docs/certification/KC_RADIO_CERTIFICATION.md` (7 모듈 분류·신청 흐름·자가 점검·갭 분석)
- [x] **GENESIS 309** ✅ 조종자 자격증명 매핑 — `docs/certification/PILOT_LICENSE_MAPPING.md` (1~4종 과목·실기 항목 ↔ SDACS 모듈, 튜토리얼 5단계 정렬)
- [x] **ODYSSEY 408** ✅ ICAO 공역 클래스 A-G 매핑 — `docs/certification/AIRSPACE_CLASS_MAPPING.md` + `simulation/airspace_class.py` (`classify_airspace()` API 격상, 결정적 산정, 25건 PASS)
- [x] **GENESIS 303** ✅ 비행계획 신고 양식 — `simulation/flight_plan_filing.py` + [`docs/certification/FLIGHT_PLAN_FORM.md`](docs/certification/FLIGHT_PLAN_FORM.md)
- [x] **GENESIS 305** ✅ DO-178C 갭 분석 — [`docs/certification/DO178C_GAP_ANALYSIS.md`](docs/certification/DO178C_GAP_ANALYSIS.md)
- [x] **GENESIS 307** ✅ 사고 보고 양식 — `simulation/accident_report.py` + [`docs/certification/ACCIDENT_REPORT_FORM.md`](docs/certification/ACCIDENT_REPORT_FORM.md)
- [x] **GENESIS 308** ✅ 보험 요율 산정 — `simulation/insurance_rate_quote.py` + [`docs/certification/INSURANCE_API_SPEC.md`](docs/certification/INSURANCE_API_SPEC.md)
- [x] **GENESIS 310** ✅ 야간·BVLOS 특별비행승인 — `simulation/special_flight_approval.py` + [`docs/certification/NIGHT_BVLOS_APPROVAL.md`](docs/certification/NIGHT_BVLOS_APPROVAL.md)
- [x] **TRANSCENDENCE 209-210** ✅ API 폐기·SemVer 정책 — [`docs/API_DEPRECATION_POLICY.md`](docs/API_DEPRECATION_POLICY.md) + [`docs/API_SEMVER_POLICY.md`](docs/API_SEMVER_POLICY.md)
- [x] **ODYSSEY 421-422** ✅ 인스턴스 디스커버리·운영 의도 교환 — `simulation/federation_discovery.py`, `simulation/operational_intent.py` + [`docs/certification/INSTANCE_DISCOVERY_PROTOCOL.md`](docs/certification/INSTANCE_DISCOVERY_PROTOCOL.md), [`docs/certification/OPERATIONAL_INTENT_FORMAT.md`](docs/certification/OPERATIONAL_INTENT_FORMAT.md)

**GitHub 운영**
- [ ] `main` branch protection 활성화 — 직접 push 차단 + CI·Security·Canonical Hash required checks 지정
- [ ] 열린 PR 15건 검토·병합/종료 — 2026-06-18 확인 기준 draft 1건, 충돌 2건(PR #280·#283)
- [ ] 저장소 루트 `LICENSE` 추가 — README의 MIT 배지 링크는 현재 대상 파일이 없어 깨진 상태

**기술 부채 (정직성 공시)**
- [ ] mock 110종 + speculative 103종 — 전체 목록·격상 난이도: [`docs/TECH_DEBT_LEDGER.md`](docs/TECH_DEBT_LEDGER.md) (자동 생성)
- [ ] Electron 차기 빌드 `^39.8.5` 적용 (v1.5.0은 32.3.3 빌드 — 보안 bump 반영은 다음 릴리스)

---

## 📦 배포 파일 다운로드 / Distribution Files (v1.5.0 — 200 Phase Unity)

GitHub `main` 브랜치에 직접 커밋된 배포 파일. 별도 빌드 없이 즉시 사용 가능.

### 🖥 데스크탑 앱 (Electron, 3-OS)

**[📥 GitHub Releases v1.5.0 (Win NSIS · macOS DMG · Linux AppImage) →](https://github.com/sun475300-sudo/swarm-drone-atc/releases/tag/v1.5.0)**

| 플랫폼 | 파일명 | 용량 | 상태 |
|---|---|---|---|
| **Windows NSIS** | `SDACS-Simulator-1.5.0-Setup.exe` | ~80 MB | 🔄 `v1.5.0` 태그 푸시 시 자동 |
| **macOS Intel** | `SDACS-Simulator-1.5.0-x64.dmg` | ~95 MB | 🔄 `v1.5.0` 태그 푸시 시 자동 |
| **macOS Apple Silicon** | `SDACS-Simulator-1.5.0-arm64.dmg` | ~95 MB | 🔄 `v1.5.0` 태그 푸시 시 자동 |
| **Linux x86_64** | `SDACS-Simulator-1.5.0-x86_64.AppImage` | 105 MB | ✅ 로컬 빌드 검증 완료, Releases 자동 |

> 🚀 자동 빌드: 사용자 로컬에서 `git pull origin main && git push origin v1.5.0` → `.github/workflows/desktop-build.yml` 3-OS 매트릭스 자동 트리거 → GitHub Releases 공개 발행 (`draft: false`, `prerelease: false`). 상세 절차: [`docs/V1_5_0_RELEASE_INSTRUCTIONS.md`](docs/V1_5_0_RELEASE_INSTRUCTIONS.md) · 트러블슈팅: [`docs/RELEASE_GUIDE.md`](docs/RELEASE_GUIDE.md)
>
> 📦 빌드 산출물은 `.gitignore`의 `dist-desktop/` 로 인해 main 브랜치에 포함되지 않음 — Releases에서만 배포

### 🛰 웹 시뮬레이터 (단일 HTML, 즉시 실행)
| 파일 | 용량 | 다운로드 | 라이브 |
|---|---|---|---|
| 군집 드론 ATC (200 Phase) | 540 KB | [📥 swarm_3d_simulator.html](swarm_3d_simulator.html) | [🌐 Live](https://sun475300-sudo.github.io/swarm-drone-atc/simulator.html) |
| 해양 소형선 감지 (HYPER 11 ATC 포함) | 75 KB | [📥 maritime_detection_simulator.html](maritime_detection_simulator.html) | [🌐 Live](https://sun475300-sudo.github.io/swarm-drone-atc/maritime_detection_simulator.html) |
| PWA Manifest | 1.6 KB | [📥 manifest.webmanifest](manifest.webmanifest) | — |
| Service Worker (오프라인) | 1.4 KB | [📥 sdacs-sw.js](sdacs-sw.js) | — |

### 🎬 데모 자료
| 파일 | 용량 | 다운로드 |
|---|---|---|
| 공개 프로젝트 소개 발표자료 (PPTX, 10장) | 57 KB | [📥 SDACS_Public_Project_Overview_2026.pptx](docs/presentation/SDACS_Public_Project_Overview_2026.pptx) |
| 200 Phase 자동 Showcase 영상 (WebM, 60s) | 9.4 MB | [📥 sdacs_200phase_showcase.webm](docs/demo/sdacs_200phase_showcase.webm) |
| 200 Phase 자동 시연 JS | 7.4 KB | [📥 all_phases_showcase.js](docs/demo/all_phases_showcase.js) |
| 검색·구조 임무 샘플 (`_sdacs.importMission` 로드) | 12.5 KB | [📥 sample_search_rescue.sdacs-mission](docs/demo/sample_search_rescue.sdacs-mission) |

### 📄 논문·보고서
| 파일 | 용량 | 다운로드 |
|---|---|---|
| **공개 프로젝트 설명 보고서 2026** (DOCX, 5페이지) | 42 KB | [📥 SDACS_Public_Project_Report_2026.docx](docs/report/SDACS_Public_Project_Report_2026.docx) |
| **캡스톤 보고서 v200** (DOCX, 졸업 심사용) | 42 KB | [📥 SDACS_Capstone_Report_v200.docx](docs/report/SDACS_Capstone_Report_v200.docx) |
| **IROS 2026 §4-§7** (PDF, 3페이지) | 132 KB | [📥 SDACS_IROS_2026_sections_4to7.pdf](docs/paper/SDACS_IROS_2026_sections_4to7.pdf) |
| IROS LaTeX 원본 (IEEEtran 재컴파일용) | 6 KB | [📥 sections_4to7.tex](docs/paper/latex/sections_4to7.tex) |
| 50 Phase Results LaTeX 표 | 2.1 KB | [📥 SDACS_50_Phases_Results.tex](docs/paper/SDACS_50_Phases_Results.tex) |

### 📚 운영·배포 가이드
| 문서 | 내용 |
|---|---|
| [📋 V1_5_0_RELEASE_INSTRUCTIONS.md](docs/V1_5_0_RELEASE_INSTRUCTIONS.md) | 사용자 1줄 명령으로 3-OS 자동 빌드 트리거 |
| [🔧 pixhawk_sdacs_hitl.md](docs/hardware/pixhawk_sdacs_hitl.md) | Pixhawk 6X HITL 통합 (Phase 22 격상) |
| [🚀 v1_5_PILOT_KICKOFF.md](docs/beta/v1_5_PILOT_KICKOFF.md) | KARI · 해수부 · 산림청 베타 (Helm 5단계) |
| [📚 SDACS_API.md](docs/SDACS_API.md) | 407 `_sdacs` API 라이브 실측 추출 레퍼런스 (maturity 등급 포함) |
| [🧭 SIMULATOR_TRANSCENDENCE_PLAN.md](docs/SIMULATOR_TRANSCENDENCE_PLAN.md) | Phase 201-300 — 정직성·실측·다중 사용자·HITL·학술 임팩트 |
| [🗓 MASTER_PLAN_2026H2.md](docs/MASTER_PLAN_2026H2.md) | 2026 H2 통합 실행 로드맵 — 4 실행 트랙 + 문서 정합성 거버넌스 |
| [🌱 SIMULATOR_GENESIS_PLAN.md](docs/SIMULATOR_GENESIS_PLAN.md) | Phase 301-400 — 인증·생태계·실증·차세대 자율·교육 레거시 (302·388 ✅) |
| [🧭 SIMULATOR_ODYSSEY_PLAN.md](docs/SIMULATOR_ODYSSEY_PLAN.md) | Phase 401-500 — 국제 확장·연합 운영·형식 검증·표준 기고·10년 지속 |
| [📒 TECH_DEBT_LEDGER.md](docs/TECH_DEBT_LEDGER.md) | 기술 부채 대장 — mock 110 + speculative 103 정직성 공시 (자동 생성) |
| [🌌 SIMULATOR_MEGA_PLAN.md](docs/SIMULATOR_MEGA_PLAN.md) ~ [POST_UNIVERSE_PLAN](docs/SIMULATOR_POST_UNIVERSE_PLAN.md) | 200 Phase 5단계 로드맵 |
| [📋 CHANGELOG.md](CHANGELOG.md) | v1.0-1.5 통합 버전 이력 |

### ✅ 현재 로컬 검증 / Current Local Validation (2026-06-24)

| 항목 | 결과 |
|---|---|
| Ruff 정적 검사 | **전체 통과** |
| Python 테스트 | **5,831 collected · 5,536 pass · 270 skip · 25 fail** |
| AIM 정밀검사 | **242 pass** (Phase 691-700, 9 rounds) |
| 대표 시뮬레이션 | **100 drones · 60s · seed 42** |
| 안전 KPI | **45 collisions · 87 near misses · 95.9% conflict resolution** |
| 통신 KPI | **12,278 sent · 12,278 delivered · 0 dropped** |

> 25건 실패는 GPU 연산(`test_hard_precision`) 및 CLI 출력(`test_main_cli`) 관련 기존 이슈로, AIM 정밀검사와 무관합니다.

> 대표 시뮬레이션 결과는 안전 인증 수치가 아니라 현재 알고리즘의 개선 기준선입니다. 재현 명령은 아래 [Testing](#testing--테스트) 섹션에 있습니다.

### 📊 v1.5.0 릴리스 당시 검증 기록 (2026-06-12)

| 항목 | 값 |
|---|:-:|
| Phase 완료 | **200 / 200** (Phase 51 LLM Multi-Agent 격상 반영) |
| 시뮬레이터 코드 | 11,836 line |
| `_sdacs` API | **407 항목** (maturity 분류 404 + 분류 헬퍼 3 — 라이브 실측) |
| Playwright E2E | **263 / 264** 통과 (1 skip) |
| 회귀 pytest | **4,180 pass / 8 skip / 0 fail** |
| 종합 자동 검증 | **4,443 pass / 9 skip / 0 fail** (2026-06-12 실측) |

### 🎯 API 성숙도 정직성 (TRANSCENDENCE Phase 201-207)

> 본 프로젝트는 200 Phase 중 다수가 미래 비전을 위한 **결정적 mock/스텁**임을 명시한다. `window._sdacs.maturityReport()` 가 실시간 분류를 제공한다.

| 등급 | 개수 | 설명 |
|---|:-:|---|
| 🟢 **production** | 93 | 실측 검증 + 회귀 + 실 알고리즘 (MEGA 코어 ATC/TAC/MIS/INJ 등) |
| 🔵 **beta** | 98 | 기능 동작 + E2E 검증, 일부 외부 의존 (HYPER Copilot/적대/C-UAS/풍속장 등) |
| 🟡 **mock** | 110 | 결정적 mock 구현, 인터페이스만 안정 (STELLAR RLHF/Cesium/QKD 등) |
| ⚪ **speculative** | 103 | 미래 비전 스텁, 호출 안전성만 보장 (ULTIMATE/POST-UNIVERSE Universe OS/Unity 등) |

```javascript
// 임의 API의 성숙도 조회
window._sdacs.apiMaturity('atcCommand');   // → 'production'
window._sdacs.apiMaturity('cesiumGlobalInit'); // → 'mock'
window._sdacs.maturityReport();            // → { total, counts, byApi }
```

> 분류 대상 400 항목 (production 93 + beta 98 + mock 110 + speculative 103) + 분류 헬퍼 2 (`apiMaturity`·`maturityReport`) = **총 407 항목** — 2026-06-12 라이브 페이지 실측.

**핵심 메시지**: SDACS의 *실용 가치*는 93개 production-grade API(드론 관제 핵심)에 있으며, 나머지는 ATC 시뮬레이터의 *가능한 기능 차원*을 정의하는 참조 매트릭스다.

---

## 📄 최종 보고서 다운로드 / Final Report Downloads

| 버전 | 대상 독자 | 특징 | 용량 | 다운로드 |
|------|----------|------|------|----------|
| **2026 공개 설명 보고서** | 일반 대중 · 학생 · 심사위원 · 공공기관 | 최신 로컬 검증 수치, 시스템 흐름, 활용 시나리오, 현재 한계와 재현 명령 | 42 KB | [📥 SDACS_Public_Project_Report_2026.docx](docs/report/SDACS_Public_Project_Report_2026.docx) |
| **v6 — 기술 보고서** | 개발자 · 심사위원 · 공학 전문가 | 알고리즘 수식, 아키텍처 다이어그램, 특허 분석, 성능 벤치마크 | 1.6 MB | [📥 SDACS_Final_Report_v6.docx](docs/report/SDACS_Final_Report_v6.docx) |
| **v7 — 일반인용 보고서** | 비전공자 · 일반 청중 · 발표 대상 | 쉬운 말 설명, 한 줄 요약 박스, 용어 사전, 일상 비유 (자석·신호등·카풀앱) | 1.6 MB | [📥 SDACS_Final_Report_v7_Easy.docx](docs/report/SDACS_Final_Report_v7_Easy.docx) |

> **v6 vs v7 차이** — 내용과 15개 시각 자료(그림 0~14)는 동일합니다. **v6**은 "APF 인력/척력 벡터장", "CBS 제약 전파", "CPA 기반 90초 lookahead" 같은 전문 용어를 그대로 쓰는 기술 문서이고, **v7**은 같은 개념을 "자석끼리 밀어내는 힘", "카풀 앱 경로 최적화", "교통 레이더 90초 전 예고"처럼 누구나 이해할 수 있는 일상 비유로 풀어 쓴 버전입니다.

**v7에 추가된 요소:**
- 🟥 **한 줄 요약 박스** — 각 섹션 첫머리에 "이 섹션이 말하는 한 가지" 제시
- 📖 **용어 사전** — APF, CPA, CBS, Swarm, Monte Carlo 등 전문 용어를 일상 언어로 번역
- 🎯 **숫자 번역** — "99.9% = 1000번 중 999번 안전", "500대 = 학교 전체 규모", "0.8초 = 눈 깜빡임"
- 🔗 **일상 비유** — 철새 떼, 도서관 분류번호, 게임 그래픽카드, 주사위 38,400번 굴리기

---

## 🐳 Docker로 실행하기 / Run with Docker

Python 환경을 직접 구성하지 않아도 **Docker 한 번이면** SDACS 3D 대시보드를 실행할 수 있습니다. 배포 노트는 [`docker/README.md`](docker/README.md)를 참고하세요.

### 사전 요구사항
- Docker Engine 20.10+ (Docker Desktop 또는 Linux Docker)
- 포트 `8050` 사용 가능

### 빠른 시작

```bash
# 1. 이미지 빌드 (최초 1회, 약 1.5 GB)
docker compose build

# 2. 컨테이너 실행 — Dash 3D 대시보드 기동
docker compose up

# 2-1. 백그라운드 실행이 필요한 경우
docker compose up -d

# 3. 브라우저로 접속
#    http://localhost:8050

# 4. 중지 및 정리
docker compose down
```

### 다른 CLI 명령 실행
기본 명령은 `python main.py visualize` 입니다. 시뮬레이션이나 Monte Carlo 스윕을 실행하려면 명령을 오버라이드하세요.

```bash
docker compose run --rm sdacs python main.py simulate --duration 60
docker compose run --rm sdacs python main.py scenario high_density
docker compose run --rm sdacs python main.py monte-carlo --mode quick
```

### 볼륨 마운트 (설정 및 결과 영속화)
`docker-compose.yaml`은 두 개의 호스트 경로를 컨테이너에 바인드합니다.

| 호스트 경로 | 컨테이너 경로 | 모드 | 용도 |
|-------------|---------------|------|------|
| `./config`  | `/app/config` | 읽기 전용 | 시나리오/Monte Carlo YAML — 호스트에서 수정 후 컨테이너 재시작 |
| `./results` | `/app/results` | 읽기/쓰기 | 시뮬레이션 CSV·로그·플롯 영속화 |

> `docker compose down` 후에도 `./results/` 디렉터리의 산출물은 호스트에 그대로 남습니다. 설정은 읽기 전용으로 마운트되므로 컨테이너가 호스트 파일을 덮어쓰지 않습니다.

---
## 🖥 데스크탑 앱 — 더블클릭으로 실행 / Desktop App

SDACS는 **Electron 데스크탑 앱**으로 빌드돼 OS별 설치 파일(.exe/.dmg/.AppImage)을 더블클릭만으로 실행합니다. 별도 런타임·CLI·브라우저 설치가 필요 없습니다.

### 📥 다운로드 (사용자)

[**최신 릴리스에서 다운로드 →**](https://github.com/sun475300-sudo/swarm-drone-atc/releases/latest)

| OS | 파일 | 동작 |
|---|---|---|
| **Windows** | `SDACS-Simulator-X.Y.Z-Setup.exe` | 더블클릭 → 설치 → 시작 메뉴에서 실행 |
| **macOS** | `SDACS-Simulator-X.Y.Z-x64.dmg` / `-arm64.dmg` | 더블클릭 → Applications로 드래그 → 실행 (Gatekeeper: 우클릭 → 열기) |
| **Linux** | `SDACS-Simulator-X.Y.Z-x64.AppImage` | `chmod +x` 후 더블클릭 또는 실행 |

앱을 열면 **홈 화면**에서 두 시뮬레이터(군집 드론 / 해양 소형선) 카드를 선택해 들어갈 수 있고, 메뉴(`Ctrl+1`/`Ctrl+2`)로 즉시 전환됩니다.

### 🛠 개발자 — 로컬 실행 / 빌드

```bash
# 의존성 설치(Electron + electron-builder)
npm install

# 개발 모드(자동 DevTools)
npm run dev
# 또는: npm start

# 패키징(현재 OS용)
npm run dist               # 모든 타깃
npm run dist:win           # Windows NSIS
npm run dist:mac           # macOS DMG
npm run dist:linux         # Linux AppImage

# web simulator only (static artifact + docs/visualization sync)
npm run build:simulator
npm run build:simulator:check

# 헤드리스 스모크(시뮬레이터 단독 — Electron 없이)
npm run test-server &      # 로컬 정적 서버
npm run smoke              # 군집 시뮬레이터 14/14
npm run smoke:maritime     # 해양 시뮬레이터 18/18
```

> **오프라인 동작**: three.js는 `vendor/three/`로 함께 패키징되어 인터넷 없이 완전 동작합니다. importmap은 상대경로(`./vendor/three/...`)로 빌드 산출물에 포함됩니다.

> **자동 릴리스**: GitHub Actions(`.github/workflows/desktop-build.yml`)가 `v*` 태그 푸시 시 3-OS 빌드를 동시 실행해 GitHub Releases에 드래프트로 업로드합니다.

---
## 🚢 해양 소형선 감지 시뮬레이터 / Maritime Small-Vessel Detection

**`maritime_detection_simulator.html`** — 대형 모선에서 **7~15m 소형선**(어선·레저보트·고속정·부표)을 레이더·AIS로 탐지·식별·추적하는 전용 시뮬레이터. SDACS의 비협조 표적 탐지·인식 기술을 해양 도메인에 이식한 사례입니다.

### 핵심 기능

| 영역 | 내용 |
|---|---|
| **C1 레이더 물리** | 표적별 RCS(어선 12 / 레저 5 / 고속정 3 / 부표 1 m²) + 안테나 높이 기반 **레이더 수평선** 자동 차폐(1.23×(√h_r+√h_t) NM) + **시클러터 블라인드** + RCS·거리·기상 4승 거리법 확률 탐지 |
| **C2 AIS·레이더 융합** | `radarDet`/`aisDet` 별도 추적 → 첫 감지에 트랙 생성, 둘 다 잡힐 때 "RADAR+AIS 융합" 표기·카운트 |
| **C4 COLREG 조우** | 표적 침로와 모선 방위 각도 차로 **HEAD-ON / CROSSING / PASSING / AWAY** 분류 + 라벨·트랙리스트·상세 패널 배지 |
| **C5 트랙 상세** | 클릭(드래그 구분) 또는 트랙리스트 행 클릭 → 상세 패널(ID/소스/신뢰도/거리·방위/속력·침로/RCS/CPA·TCPA/조우) + 0.7s 8샘플 **트레일** + 노란 깜빡 선택 링 |
| **C6 리포트** | **📷 PNG 리포트**(헤더+3D 캡처+KPI+COLREG 요약+최근 이벤트) · **💾 CSV** 표적 텔레메트리 (`id,type,...,cpa_m,tcpa_s,rcs_m2`) |
| **C8 시나리오** | 평시(12) · 혼잡 항만(24) · 안개·저시정(2.4NM·acc 0.8) · 야간(EO 저하) · 비협조 침입(고속정) · **폭풍·악천후(2NM)** · **항만 출입(20척)** · **비협조 고속정 다수(18척)** |

### 빠른 사용법

```bash
# 더블클릭 런처(Win/Mac/Linux) → 메인 시뮬레이터가 열림
# 해양으로 직접 열려면:
python3 scripts/serve.py --page maritime
#   → http://localhost:8123/maritime_detection_simulator.html
```

상단 시나리오 셀렉터에서 8개 중 선택 → 좌측 패널에서 센서 레이어(레이더 스윕·CPA 예측선·식별 라벨·트랙 트레일) 토글 → 트랙 클릭으로 상세 확인 → 📷/💾 버튼으로 리포트 저장.

### 검증

- 헤드리스 스모크 `tests/e2e/smoke_maritime.mjs` **17/17 통과**(스폰·탐지·식별·정확도·CPA·C1 수평선·C2 융합·C4 조우·C5 선택·시나리오·C3 EO/IR·C6 PNG/CSV·C8 신규 3종·C9 검증기록·무에러)
- CI(`.github/workflows/sim-smoke.yml`)에서 push·PR마다 자동 실행

📄 **기술 상세**: 레이더 물리·AIS 융합·COLREG·CPA 공식은 [`docs/maritime_detection_technical.md`](docs/maritime_detection_technical.md) 참조

---
## What is SDACS? / SDACS란?

> **"레이더를 땅에 설치하는 대신, 드론 자체가 레이더가 되면 어떨까?"**

SDACS는 이 단순한 발상에서 출발했습니다. 20대의 관제 드론이 공중에 올라가 그물망처럼 연결된 감시 체계(**이동형 가상 레이더 돔**)를 스스로 만들어, 도심 하늘을 자동으로 감시하고 충돌을 미리 막는 시스템입니다.

쉽게 말해, **"하늘의 신호등"** 입니다. 도로에 신호등이 차량 충돌을 방지하듯, SDACS는 하늘에서 드론들이 서로 부딪히지 않도록 자동으로 교통 정리를 합니다.

### The Problem / 왜 필요한가?

지금 이 순간에도 전국 하늘에서 수십만 대의 드론이 날아다닙니다. 택배 배달, 농약 살포, 건물 점검 — 2030년에는 하늘을 나는 택시(UAM)까지 등장합니다. 문제는 이 드론들이 모두 **같은 낮은 하늘**(지상 120m 이하)을 공유한다는 것입니다.

| 현재 상황 | 수치 | 의미 |
|----------|------|------|
| 국내 드론 등록 | **90만 대+** | 매년 30% 이상 증가 중 |
| 도심 저고도 사각지대 | **67%** | 기존 레이더가 탐지 못하는 구간 |
| 수동 관제 반응시간 | **평균 5분** | 고속 드론 위협에 대응 불가 |
| 고정 레이더 구축 비용 | **수억 원 + 6개월** | 긴급 상황에 적용 불가 |

### 기존 시스템의 한계

| 시스템 | 핵심 문제 | SDACS 해결 방식 |
|--------|----------|----------------|
| **K-UTM** (중앙 관제) | 서버 하나 다운 → 전체 관제 마비 | 분산 구조 → 드론 10% 고장해도 90% 정상 |
| **고정형 레이더** | 수억원 + 6개월, 건물에 막혀 67% 미감시 | 드론 10대로 30분 내 설치, 비용 90% 절감 |
| **드론쇼 방식** | 사전 경로만 실행, 돌발 상황 대응 불가 | AI 실시간 자율 판단, 집단 지능 창발 |

> **드론쇼 vs SDACS의 근본적 차이**: 드론쇼는 *"중앙에서 짠 계획을 각 드론이 실행"* 하는 하향식 방식입니다. SDACS는 *"단순 규칙을 따르는 드론들이 소통하며 집단 지능이 자연스럽게 생겨나는"* 상향식 방식입니다.

### Our Approach / SDACS의 접근

1. **레이더를 드론으로 대체** — 고정 인프라 없이 30분 내 긴급 배치 (기존 6개월 → 30분, **99.7% 단축**)
2. **탐지부터 회피까지 완전 자동화** — 90초 전 선제 충돌 예측, 0.8초 내 대응 (기존 5분 → **300배 향상**)
3. **드론 추가만으로 관제 반경 확장** — 분산형 아키텍처, 운영 인력 80% 절감 (5명 → 1명)
<div align="center">
<img src="docs/images/imgur/Xm6G9Dt.png" alt="분산형 APF 충돌 회피 3D 시각화" width="700"/>
<br/><sub>분산형 APF 충돌 회피 — 드론별 인력/척력장이 실시간으로 안전 궤적을 생성</sub>
</div>

---
## Key Results / 핵심 성과
| Metric | Value | Description |
|--------|-------|-------------|
| **Collision Resolution** | **100% (20대)** | 20대 600s: 충돌 0건, 50대: 97.9%, 100대: 98.9% |
| **Route Efficiency** | **≤1.12** | 전 규모 SLA(≤1.15) PASS (600s 실측) |
| **Prediction Lookahead** | **90 seconds** | CPA-based preemptive conflict detection at 1 Hz |
| **Advisory Latency** | **< 1 second** | 6 types: CLIMB/DESCEND/TURN_LEFT/TURN_RIGHT/EVADE_APF/HOLD |
| **Monte Carlo Validation** | **38,400 runs** | 384 configurations x 100 seeds |
| **Scenario Coverage** | **63 scenarios** | 7대 광역시 도시환경 + 극한 기상 + 침입 + GPS 재밍 + 대규모 배송 |
| **Concurrent Drones** | **100+** | 20대: 충돌 0, 50대: avg 15, 100대: avg 29 |
| **Deployment Time** | **30 min** | No fixed infrastructure required |
| **Multi-Language Coverage** | **50+ Languages** | Phase 521-660: Zig, Rust, Go, C++, Kotlin, Nim, OCaml, F#, Swift, TS, Scala, Haskell, Lua, Julia, Dart, Elixir, R, Octave, Perl, Ruby, VHDL, Prolog, Fortran, Ada, COBOL and more |
| **Test Collection** | **5,500+ tests** | Automated pytest collection across 830+ Python files and 110+ test files |
<div align="center">
<img src="docs/images/imgur/wHuMIfM.png" alt="기존 방식 대비 SDACS 성능 비교" width="750"/>
<br/><sub>기존 Rule-based Static ATC vs SDACS Swarm Autonomous — 주요 KPI 비교</sub>
</div>

---
## System Architecture / 시스템 아키텍처
SDACS는 4개의 독립적 계층으로 구성됩니다. 각 계층은 명확한 역할과 인터페이스를 가지며, 독립적으로 테스트 가능합니다.
<div align="center">
<img src="docs/images/imgur/Oz6LB2I.png" alt="SDACS 4계층 시스템 아키텍처" width="750"/>
<br/><sub>SDACS 4계층 아키텍처 — 드론 에이전트 / 공역 관제 / 시뮬레이션 엔진 / 사용자 인터페이스</sub>
</div>
```
┌─────────────────────────────────────────────────────────────────┐
│                     Layer 4: User Interface                     │
│                CLI (main.py) + Dash 3D Visualizer               │
├─────────────────────────────────────────────────────────────────┤
│                   Layer 3: Simulation Engine                    │
│          SwarmSimulator + WindModel + Monte Carlo Engine         │
├─────────────────────────────────────────────────────────────────┤
│                    Layer 2: Control System                      │
│     AirspaceController (1Hz) + Priority Queue + Advisory Gen    │
├─────────────────────────────────────────────────────────────────┤
│                     Layer 1: Drone Agents                       │
│             DroneAgent (10Hz SimPy process per drone)            │
└─────────────────────────────────────────────────────────────────┘
```

### Layer 1 — Drone Agent (드론 에이전트)
각 드론은 SimPy 이산 이벤트 프로세스로 모델링됩니다. 10Hz 주기로 위치/속도/배터리 상태를 갱신하며, 비행 상태 머신(FSM)에 따라 `Idle → Takeoff → Cruise → Avoid → Landing` 전이를 수행합니다.
- **파일**: `simulation/drone_agent.py` — `DroneAgent` 클래스 (`simulation/simulator.py`에서 각 드론 프로세스를 기동)
<div align="center">
<img src="docs/images/imgur/bBRoCn6.png" alt="센서 퓨전 프로세스" width="700"/>
<br/><sub>센서 퓨전 — Camera(YOLO) + LiDAR + RF Scanner → Kalman Filter → 위치/식별/위협 판정</sub>
</div>

### Layer 2 — Airspace Controller (공역 관제)
1Hz 주기로 모든 활성 드론의 위치를 수집하고, 충돌 위험을 평가하여 자동 어드바이저리를 발행합니다.
- **CPA (Closest Point of Approach)**: O(N^2) 쌍별 스캔, 90초 선제 예측
- **Voronoi 공역 분할**: 10초 주기 동적 갱신, 밀도 기반 셀 분리
- **Resolution Advisory**: 기하학적 분류에 따른 6종 회피 명령 자동 생성
- **동적 분리간격**: 풍속 연동 자동 조정 (1.0x ~ 1.6x, 5/10/15 m/s 구간)
- **파일**: `src/airspace_control/controller/airspace_controller.py`

### Layer 3 — Simulation Engine (시뮬레이션 엔진)
SimPy 기반 이산 이벤트 시뮬레이션 엔진으로, 다양한 환경 조건과 장애 시나리오를 주입할 수 있습니다.
- **SwarmSimulator**: 정식 시뮬레이터 (engine_legacy 삭제 완료)
- **WindModel**: 3종 기상 모델 (constant / variable-gust / shear)
- **Monte Carlo**: 384 config x 100 seeds = 38,400 검증 실행
- **장애 주입**: MOTOR/BATTERY/GPS 고장, 통신 두절, 미등록 드론 침입
- **파일**: `simulation/simulator.py`, `simulation/wind_model.py`, `simulation/monte_carlo.py`

### Layer 4 — User Interface (사용자 인터페이스)
- **CLI**: `main.py` — `simulate`, `scenario`, `monte-carlo`, `benchmark`, `visualize`, `visualize-3d`, `api`, `ops-report`, `chatbot`
- **3D Dashboard**: Dash + Plotly 실시간 3D 시각화, 드론 궤적/충돌 경고/편대 표시
- **[3D Web Simulator (메인 데모)](https://sun475300-sudo.github.io/swarm-drone-atc/simulator.html)**: Three.js 브라우저 기반 인터랙티브 시뮬레이터 (프로젝트 대표 시뮬레이터)
  - **63개 시나리오** — 7대 광역시(서울/부산/인천/대구/광주/대전/울산) 도시환경 + 극한 기상 + 메가 스케일 500대
  - **WebGPU Compute Shader** — APF 힘 계산 GPU 가속 (WGSL 컴퓨트 파이프라인, WebGPU 미지원 시 Web Worker 자동 폴백)
  - **실시간 분석 대시보드** — 배터리/에너지/충돌해결률/위협레벨/관제구역/틱처리시간/비행단계 7종 차트
  - **도시별 랜드마크 환경** — 각 도시의 실제 빌딩, 강, 산, 공원을 3D로 재현 (롯데월드타워, 해운대, 무등산 등)
  - APF 충돌 회피 + CPA 12초 예측 + Spatial Hash 최적화
  - 22개 드론 직군, 21-zone ATC 네트워크
  - 극한 기상: 마이크로버스트, 태풍, 결빙, 다중셀 폭풍, 풍속 전단
  - CPU/GPU/Worker 성능 모니터링 HUD
  - **드론 라이브 상태 조회** — 드론 호버 시 실시간 툴팁(직군/고도/속도/기수/배터리/ETA), 클릭 시 상세 패널(상태/수직속도/좌표/출발·목표/텔레메트리/경로효율/최근접 이웃) + 선택 하이라이트
  - **충돌·공역 관제 시각화** — CPA 충돌 예측선(TTC·이격거리 라벨), 회피 어드바이저리 빌보드, 웨이포인트·이동경로, 레이어 토글(NFZ/회랑/고도레이어 9단/ATC)
  - **분석 뷰(2×2)** — 3D 궤적 + XY 평면도(고도 컬러맵) + 배터리 추이 + KPI 대시보드
  - **리플레이·타임라인** — 0.5s 스냅샷 레코더 + 스크러버(재생/속도/LIVE)
  - **리포트 내보내기** — 4분할 PNG / CSV(시계열·텔레메트리·**ATC_Commands 감사 로그**) / KPI 클립보드 복사
  - **🎮 ATC 관제사 명령 콘솔** (2026-06 신규) — 드론 클릭 시 상세 패널에 명령 그리드 등장: `HOLD` (호버 락) · `RTB` (출발 패드 귀환) · `REROUTE` (대체 패드 변경) · `ALT±` (목표고도 ±10m) · `SPD±` (속도 ±20%) · `TURN◀▶` (즉시 좌/우 30° 선회) · `CLEAR` (자율 복귀). **시안 발광 링**으로 수동 제어 중인 드론 식별, **한국어 TTS 음성**(Web Speech API, "드론 7번 즉시 호버") + **Web Audio 비프 경보**(충돌 2초 전 자동), **ATC 명령 로그 패널**(타임스탬프·감사 추적, 좌측 하단)
  - **🎯 전술 시각화** (Phase 2, 2026-06 신규) — 드론별 **예측 비행경로 라인**(다음 8초, 1초 step×8, fade gradient, ATC=노랑·EVADE=주황 색조), **CPA 충돌점 마커**(예측 최근접점에 ⊕ 마커 + TTC 색상 단계: <2s 적색·2-5s 황색·5-12s 회색·임박할수록 크기↑), **속도 벡터 화살표**(선택/다중 선택 드론, 속도 0-5 청·5-15 녹·15-25 황·>25 적), 좌측 패널 토글 3개 (`tg-pred-trail`/`tg-vel-arrow`/`tg-cpa-marker`), megaMode≥500 자동 LOD/OFF, 100-200대 frame skip
  - **🎬 시네마틱 모드** (Phase 3, 2026-06 신규) — **동적 태양 24h 사이클**(시간대별 RGB·앰비언트 강도 자동 변환: 새벽 청 → 정오 백 → 황혼 황 → 야간 짙은 청, 0-24h 슬라이더 + 0.05h/s 자동 흐름), **비/눈 입자 시스템**(5,000 비 + 3,000 눈 sprite, 강도 0-1 슬라이더, 바람 드리프트), **화면 녹화**(MediaRecorder API, VP9/VP8/MP4 자동 코덱 감지, 8Mbps WebM 다운로드, 빨간 점멸 인디케이터)
  - **💥 장애 주입 콘솔** (Phase 6, 2026-06 신규) — 선택 드론에 **GPS 손실**(노이즈 ±20m, 20초) / **모터 페일**(maxSpeed 50%) / **통신 두절**(ATC 명령 무시, 10초) / **배터리 급강하**(5%/s × 20초) 주입, **ROGUE 드론 spawn**(NFZ 횡단 시도), **동적 NFZ 생성**(임의 위치 r=100m × 30초), **시나리오 일괄**: 도시 EMP(30% GPS 손실) / EMI 폭격(50% 통신두절), 통계 카운터 + 전체 해제 버튼
  - `window._sdacs` API — 자동화 테스트 및 외부 연동 (`selectDrone`/`hoverDrone`/`setAnalysisView`/`replaySeek`/`reportDataURL`/**`atcCommand(id, cmd, params)`**/**`atcLog`**/**`atcControlled`**/**`setAtcAudio(on)`**/**`clearAllAtc()`**/**`setPredTrail(on)`**/**`setPredHorizon(s)`**/**`setVelArrow(on)`**/**`setCpaMarker(on)`**/**`cpaPairsCount`**/**`setSunCycle(on)`**/**`setSunHour(h)`**/**`setSunAuto(on)`**/**`setRain(on, intensity)`**/**`setSnow(on, intensity)`**/**`startRecording()`**/**`stopRecording()`**/**`injectFault(id, type, opts)`**/**`injectRogue()`**/**`injectDynamicNFZ(x, z, r, dur)`**/**`injectScenario(name)`**/**`injClearAll()`**/**`injStats`** 등)
  - **🎥 카메라 모드** (Phase 4, 2026-06 신규) — **FPV 1인칭**(선택 드론 head 시점, FOV 75°, heading 방향 시선), **추격캠**(드론 뒤 8m·위 3m, spring damping 0.08), **측면 뷰**, 기존 기본/탑다운/추적/오빗과 함께 7개 프리셋 + 단축키 1-7
  - **🌬 환경 사운드** (Phase 8, 2026-06 신규) — Web Audio 합성 **바람 화이트노이즈**(풍속 비례 음량·lowpass 필터 휘파람), **우천 노이즈**(비 입자 강도 연동), **배터리 임계 알람**(<15% 드론 발생 시 880Hz 비프, 1초 쿨다운). 음성 ON + 환경음 ON 동시 필요
  - **📋 임무 계획 UI** (Phase 5, 2026-06 신규) — 선택 드론에 **5종 임무 템플릿 할당**: 🔍 수색(4×4 격자 16wp)·🛸 정찰(8 원형 궤도 r=500m)·📦 배달(직선)·🌾 농업 방제(Voronoi 지그재그 8wp)·🚑 의료 우선순위(라인 5wp). 진행률 자동 추적(120m 도달 시 currentIdx++), 완료 시 phase 자동 변경, 진행 중 임무 5개 표시 패널 + 전체 해제 버튼
  - **📊 분석 강화** (Phase 7, 2026-06 신규) — **누적 위협 히트맵**(100×100 그리드, decay 0.992, EVADING 드론 가중치 3.0, 분석 뷰 Q2 연동), **5s KPI 슬라이딩 윈도우**(time/cr/conflicts/avgBat/fps, 0.1s 간격, 300 sample max), **LaTeX 표 자동 출력**(`\begin{table}\\begin{tabular}{lr}` 형식, `.tex` 다운로드 + 클립보드 자동 복사, 논문 §Results 직접 삽입 가능)
  - **📱 모바일/PWA** (Phase 9, 2026-06 신규) — `viewport-fit=cover` + safe-area-inset · 반응형 미디어 쿼리(< 1024px 폰트·UI 자동 축소, pointer:coarse 44px hit area), **터치 제스처**(더블 탭 = 드론 선택, 길게 누르기 600ms = ATC HOLD), **`manifest.webmanifest`** PWA(standalone 디스플레이, 홈 화면 추가 지원), **Service Worker**(`sdacs-sw.js` cache-first, 오프라인 시뮬 실행), 모바일 자동 LOD(입자·예측경로·속도 화살표 자동 OFF)
  - 헤드리스 스모크 테스트: `tests/e2e/smoke_sim.mjs` (군집 14/14) + **`tests/e2e/test_simulator_atc.py`** (ATC 10/11) + **`tests/e2e/test_simulator_tac.py`** (TAC 9/9) + **`tests/e2e/test_simulator_cin_inj.py`** (CIN+INJ 17/17) + **`tests/e2e/test_simulator_cam_aud.py`** (CAM+AUD 10/10) + **`tests/e2e/test_simulator_mis_ana_mob.py`** (MIS+ANA+MOB 15/15) — 총 **61/62 통과** (CI: `.github/workflows/sim-smoke.yml`)
- **파일**: `main.py`, `visualization/simulator_3d.py`, `swarm_3d_simulator.html` · _구버전 `swarm_3d_simulator_v2.html`·`*.v1.backup.html`은 디프리케이트(참고용)_
```mermaid
sequenceDiagram
    participant D as Drone (10Hz)
    participant AC as AirspaceController (1Hz)
    participant RA as Resolution Advisory
    D->>AC: Position/velocity report
    AC->>AC: CPA scan (O(N^2), 90s lookahead)
    alt Conflict detected
        AC->>RA: Request avoidance maneuver
        RA-->>AC: Advisory (CLIMB/DESCEND/TURN/EVADE/HOLD)
        AC->>D: Issue advisory
    end
    D-->>AC: Acknowledge
```

---
## 5겹 안전망 — 어떻게 충돌을 막는가 (비전공자용)

SDACS는 5가지 안전 장치가 겹겹이 보호합니다. **하나가 실패해도 다음 장치가 안전을 보장**합니다.

| 단계 | 비유 | 설명 |
|------|------|------|
| **1단계: 출발 전 경로 설정** | 내비게이션 | 출발 전에 다른 드론과 겹치지 않는 최적 경로를 미리 계산 |
| **2단계: 90초 전 충돌 예측** | 전방 레이더 | 현재 속도로 비행하면 90초 후 다른 드론과 만날지 미리 계산 |
| **3단계: 자석형 자동 회피** | 같은 극 자석 | 드론끼리 가까워지면 자석처럼 밀어내는 힘이 자동으로 발생 |
| **4단계: 비상 브레이크** | 급정거 | 모든 회피가 실패해도 최후의 비상 정지로 충돌 방지 |
| **5단계: 자동 귀환** | 비상구 | 배터리 부족이나 고장 시 자동으로 가장 가까운 착륙지로 복귀 |

### 자동 우선순위 전환 — 드론의 비상 매뉴얼

위험 수준에 따라 **5단계로 자동 전환**됩니다. 관제사가 개입하지 않아도 AI가 즉각 판단합니다.

| 우선순위 | 모드 | 발동 조건 | 자동 조치 |
|---------|------|----------|----------|
| **P0** | 비상 (EMERGENCY) | 충돌 임박 또는 배터리 위험 | 전체 군집 비상 회피, 관제사 즉시 알림 |
| **P1** | 충돌회피 (DECONFLICT) | 10m 이내 드론 감지 | 자석형 힘으로 즉각 회피, 경로 재조정 |
| **P2** | 임무 (MISSION) | 임무 드론 이착륙 중 | 임무 경로 독점, 다른 드론 우회 |
| **P3** | 순항 (CRUISE) | 정상 비행 이동 중 | 경로 모니터링, 이상 징후 감지 |
| **P4** | 대기 (IDLE) | 공역 위협 없음 | 호버링 대기, 10초 주기 스캔 |

### 탐지 → 퇴각 자동화 — 1초 이내 5단계

불법·위협 드론 발견 시 **사람 개입 없이 1초 이내** 자동 처리됩니다.

| 단계 | 처리 시간 | 내용 |
|------|----------|------|
| ① 탐지 | ~0.05초 | 전파 탐지기 + AI 카메라로 드론 발견 |
| ② 식별 | 즉시 | 드론 고유번호를 DB와 대조 → 등록/미등록/위협 분류 |
| ③ 타이머 | 자동 | 미등록 드론에 30초 카운트다운 부여 |
| ④ 경고 | 자동 | SMS + 앱 푸시 + 멀티채널 경고 발송 |
| ⑤ 퇴각 | 최종 | 관제 드론이 포위 대형 → 심리적 압박 + 전파 경고 |

### 비용-효과 비교 — SDACS vs 기존 방식

| 항목 | 기존 방식 | SDACS | 개선율 |
|------|----------|-------|--------|
| 시스템 준비 시간 | 6개월 | **30분** | 99.7% 단축 |
| 운영 인력 | 5명 (24시간) | **1명** | 80% 절감 |
| 위험 탐지 속도 | 평균 5분 | **0.8초** | 300배 향상 |
| 초기 구축 비용 | 수억 원+ | **드론 10대 비용** | 90%+ 절감 |
| 동시 관제 대수 | 20대 이하 | **100대+ 실측** | 5배+ 향상 |
| 응답 지연 | 0.2초 (서버 경유) | **0.05초** (직접 통신) | 4배 향상 |

---
## Core Algorithms / 핵심 알고리즘 (기술 상세)
SDACS의 충돌 회피 파이프라인은 **탐지 → 판단 → 실행** 3단계로 구성됩니다.
<div align="center">
<img src="docs/images/imgur/8IPIDWR.png" alt="탐지 → 회피 자동 대응 파이프라인" width="750"/>
<br/><sub>탐지 → 회피 자동 대응 파이프라인 — DETECT → IDENTIFY → TIMER → WARN → RETREAT (Target Latency < 1s)</sub>
</div>

### 1. Collision Detection / 충돌 탐지
| Algorithm | Purpose | Complexity |
|-----------|---------|------------|
| **CPA (Closest Point of Approach)** | 두 드론의 최근접점 시각/거리 계산 | O(N^2) per tick |
| **Voronoi Tessellation** | 공역을 드론별 셀로 분할, 침범 감지 | O(N log N) |
| **Geofence Monitor** | 공역 경계(90%) 이탈 시 자동 RTL | O(N) |
| **Intrusion Detection** | ROGUE 프로파일 미등록 드론 탐지 | O(N) |

### 2. Conflict Resolution / 충돌 해결
| Algorithm | Purpose | Description |
|-----------|---------|-------------|
| **APF (Artificial Potential Field)** | 실시간 충돌 회피 | 인력장(목표) + 척력장(장애물), 강풍 시 `APF_PARAMS_WINDY` 자동 전환 |
| **CBS (Conflict-Based Search)** | 다중 에이전트 경로 계획 | 충돌 트리 탐색으로 최적 비충돌 경로 계산 |
| **Resolution Advisory Generator** | 회피 명령 자동 분류 | 기하학적 관계(상대 위치/속도)에 따라 6종 어드바이저리 결정 |
| **A\* Path Replanning** | 동적 경로 재계획 | 에너지 비용 함수 + 충전소 경유 + 풍향/고도 반영 |

### 3. Formation Control / 편대 제어
| Algorithm | Purpose | Description |
|-----------|---------|-------------|
| **Graph Laplacian Consensus** | 대형 유지/전환 | 리더-팔로워 합의 기반, V/Line/Circle/Grid 4패턴 |
| **Reynolds Boids** | 군집 행동 | 분리/정렬/응집 3규칙 + 장애물 회피 확장 |
| **ORCA (Optimal Reciprocal Collision Avoidance)** | 속도 공간 최적화 | 반속도 장애물 기반 안전 속도 선택 |

### 4. Advanced Modules (Phase 1-610)
600+개의 알고리즘 모듈이 6개 계층에 걸쳐 구현되어 있습니다:
| Category | Examples | Count |
|----------|----------|-------|
| **Physics & Dynamics** | Wind model, battery model, energy optimization | 40+ |
| **AI & ML** | DRL, MARL, NAS, meta-learning, GAN, XAI | 60+ |
| **Optimization** | PSO, ACO, NSGA-II, genetic algorithm, quantum annealing | 30+ |
| **Communication** | Mesh network, V2X, 5G/6G, acoustic, encryption | 25+ |
| **Autonomy** | Formation control, task allocation, mission planning | 35+ |
| **Security** | Zero-trust, blockchain, intrusion detection, adversarial defense | 20+ |
| **Bio-inspired** | Morphogenesis, optogenetics, electrostatics, ecosystem dynamics | 25+ |
| **Mathematical** | Topology control, information theory, CSP, causal inference | 30+ |

### Project Structure / 프로젝트 구조
```
swarm-drone-atc/
├── simulation/                      # Layer 1 & 3: core runtime + experiments
│   ├── simulator.py                 # SwarmSimulator orchestrator
│   ├── drone_agent.py               # DroneAgent 10Hz SimPy process
│   ├── analytics.py                 # runtime KPI / event collection
│   ├── apf_engine/                  # Artificial Potential Field
│   ├── cbs_planner/                 # Conflict-Based Search
│   ├── ws_bridge.py                 # Python -> browser WebSocket bridge
│   └── ... (450+ Python modules)
│
├── src/airspace_control/            # Layer 2: Control System
│   ├── controller/                  # AirspaceController
│   ├── avoidance/                   # Resolution Advisory
│   ├── agents/                      # DroneState, DroneProfiles
│   ├── comms/                       # CommunicationBus, message types
│   ├── planning/                    # FlightPathPlanner
│   └── utils/                       # GeoMath, CoordinateSystems
│
├── visualization/                   # Dash / Plotly visualizer
│   ├── simulator_3d.py              # Dash 3D app entry
│   ├── _domain.py                   # domain state and data model
│   ├── _embedded_sim.py             # embedded simulation bridge
│   ├── _scene_traces.py             # Plotly scene trace builders
│   ├── _callbacks.py, _layout.py    # Dash callbacks and layout
│   └── swarm_3d_simulator.html      # served copy of web simulator
│
├── docs/                            # GitHub Pages + docs assets
│   ├── simulator.html               # main web entry point
│   ├── swarm_3d_simulator.html      # Pages copy of main simulator
│   ├── swarm_3d_simulator_v2.html   # legacy lightweight variant
│   └── images/, report/, patent/
│
├── api/                             # FastAPI server skeleton / API glue
├── chatbot/                         # chatbot and simulation adapters
├── benchmarks/                      # reproducible benchmark scenarios
├── tests/                           # 105 test files + e2e smoke
│   ├── test_simulator_scenarios.py
│   ├── test_phase*.py
│   └── ...
│
├── config/                          # Configuration
│   ├── default_simulation.yaml
│   ├── monte_carlo.yaml
│   └── scenario_params/             # 9 scenario definitions
│
├── main.py                          # CLI entry point
└── scripts/                         # Utility scripts
```

---
## How It Works / 작동 원리
<div align="center">
<img src="docs/images/imgur/o6kmDrU.png" alt="핵심 알고리즘 워크 흐름" width="750"/>
<br/><sub>핵심 알고리즘 워크 흐름 — Monte Carlo 검증부터 CBS/APF 경로 계획까지</sub>
</div>
**비행 상태 머신 (Flight State Machine):**
<div align="center">
<img src="docs/images/imgur/TFJG4zF.png" alt="드론 비행 상태 기계 (Flight Phase FSM)" width="650"/>
<br/><sub>드론 비행 상태 기계 — GROUNDED → TAKEOFF → ENROUTE → EVADING/HOLDING → LANDING</sub>
</div>
```
                    ┌──────────────┐
                    │   GROUNDED   │ ◄──────────────────────┐
                    └──────┬───────┘                        │
                           │ takeoff()                      │ landed
                    ┌──────▼───────┐                 ┌──────┴───────┐
                    │   TAKEOFF    │                 │   LANDING    │
                    └──────┬───────┘                 └──────▲───────┘
                           │ alt >= CRUISE_ALT              │ mission complete
                    ┌──────▼───────┐                        │ / battery low
              ┌────►│   ENROUTE    ├────────────────────────┘
              │     └──┬───────┬───┘
              │        │       │
    advisory  │        │       │ conflict detected
    expired   │        │       │
              │   ┌────▼──┐  ┌─▼────────┐
              └───┤HOLDING│  │  EVADING  │ ◄── APF forces active
                  └───────┘  └──────────┘
                                  │
                           ┌──────▼───────┐
                           │  EMERGENCY   │ ← RTL / forced landing
                           └──────────────┘
```
<div align="center">
<table>
<tr>
<td align="center"><img src="docs/images/imgur/oVr0lt8.png" alt="시나리오별 KPI 레이더" width="380"/><br/><sub>시나리오별 KPI 레이더 차트</sub></td>
<td align="center"><img src="docs/images/imgur/I2iejhf.png" alt="어드바이저리 지연 시간" width="380"/><br/><sub>시나리오별 어드바이저리 지연 (P50/P99)</sub></td>
</tr>
</table>
</div>

### 17. CI/CD Pipeline / 지속적 통합 파이프라인
`.github/workflows/ci.yml` 단일 워크플로우로 통합 운영합니다.
**Test Job (Python 3.10 / 3.11 / 3.12 매트릭스):**
| Step | 내용 |
|------|------|
| Checkout | `actions/checkout@v4` |
| Python Setup | `actions/setup-python@v5` (매트릭스) |
| Cache pip | pip 캐시 (requirements.txt 해시 기반) |
| Install | `pip install -r requirements.txt` + flake8 |
| Lint | `flake8 --select=E9,F63,F7,F82` (구문 오류만) |
| Test | `pytest tests/ -v --tb=short --timeout=60` |
| Import Check | 핵심 3개 모듈 임포트 검증 |
| Smoke Report | PR 시 JSON 리포트 생성 + 아티팩트 업로드 |
| Perf Summary | PR 시 성능 요약 JSON 생성 |
**Ops Report Job (main 푸시 시):**
| Step | 내용 |
|------|------|
| Trigger | `push` to `main` (test 통과 후) |
| Bundle | `ops_report_bundle.json` (manifest + artifact references) |
| Upload | 아티팩트 보존 90일 |
**시나리오 파라미터 오버라이드 체계:**
```
config/default_simulation.yaml  (기본값)
    ↓ 머지
config/scenario_params/{name}.yaml  (시나리오 오버라이드)
    ↓ 머지
CLI arguments  (실행 시 오버라이드)
    ↓
SwarmSimulator._deep_merge()  → 최종 설정
```

---
## Multi-Language Architecture / 다중 언어 아키텍처
SDACS는 핵심 시뮬레이션(Python) 외에 50개 이상의 프로그래밍 언어로 구현된 220+ 보조 모듈을 포함합니다.

### Integration Approach / 연동 방식
각 언어 모듈은 **독립적 마이크로모듈** 패턴으로 설계되었습니다:
- **Python Core ↔ Native 모듈**: `subprocess` 호출 또는 `ctypes`/`cffi` FFI(Foreign Function Interface)를 통해 고성능 연산(C++/Rust/Fortran)을 Python에서 호출
- **REST API 모듈** (TypeScript/PHP/Ruby): Express/Flask 스타일 HTTP 엔드포인트로 대시보드/포털 기능 제공
- **Protocol 모듈** (Prolog/Haskell/Ada): 독립 실행형 검증기/추론 엔진으로, 결과를 JSON/stdout으로 Python에 전달
- **Reference Implementation** (COBOL/Assembly/VHDL): 레거시 시스템 호환성 검증 및 하드웨어 시뮬레이션 참조 구현
> 핵심 원칙: **Python이 오케스트레이터**, 각 언어가 특정 도메인의 **전문가 모듈** 역할. 시뮬레이션 실행에는 Python만 필요하며, 다국어 모듈은 특수 목적(성능 최적화, 형식 검증, 하드웨어 연동 등)에 활용됩니다.

### Language Portfolio / 언어별 역할
| Language | Modules | Use Case | Integration |
|----------|---------|----------|-------------|
| **Python** | 680+ | Core simulation, ML/AI, analytics, production hardening | Main engine |
| **Rust** | 15 | Safety-critical: satellite comm, NEAT evolution, safety verifier | FFI / subprocess |
| **Go** | 14 | Concurrent: edge AI, mission validation, realtime monitor | subprocess / gRPC |
| **C++** | 14 | Performance: SLAM, morphogenesis, physics, particle filter | ctypes / FFI |
| **Zig** | 15 | Low-level: PBFT consensus, ring buffer v2, telemetry | subprocess |
| **Fortran** | 9 | Numerical: wind field FDM, CFD wind tunnel | f2py / subprocess |
| **Ada** | 7 | Safety: TMR v2 (Byzantine fault tolerance) | Reference impl |
| **VHDL** | 7 | Hardware: PWM controller, FIR filter, signal processing | Simulation only |
| **Assembly** | 7 | Bare-metal: CRC32, sensor readout, Kalman filter | ctypes |
| **Prolog** | 8 | Logic: airspace rules v2, constraint satisfaction | subprocess |
| **Nim** | 1 | Async: event dispatcher, telemetry routing | standalone |
| **OCaml** | 1 | Formal: flight plan type checker, ADT verification | standalone |
| **Haskell** | 1 | Formal verification: type-safe safety proofs | standalone |
| **TypeScript** | 2 | Dashboard REST API, physics engine | HTTP API |
| **Swift/Kotlin** | 3 | Mobile monitoring (iOS/Android) | REST client |
| **Julia** | 1 | High-performance ODE solver | standalone |
| **Elixir/Erlang** | 3 | OTP fault supervision, distributed consensus | message passing |
| **Others** | 30+ | PHP, COBOL, R, Perl, Scheme, Octave, Lua, Ruby, Dart, Scala, etc. | Various |
```mermaid
pie title Module Distribution by Language (Phase 700)
    "Python" : 680
    "Zig" : 15
    "Rust" : 15
    "Go" : 14
    "C++" : 14
    "Fortran" : 9
    "Prolog" : 8
    "Assembly" : 7
    "Ada" : 7
    "VHDL" : 7
    "Others (40+)" : 75
```

---
## Development Phases / 개발 단계
SDACS는 700개 Phase를 거치며 점진적으로 확장되었습니다.
| Phase Range | Focus | Highlights |
|-------------|-------|------------|
| **1-50** | Core ATC | SimPy engine, CPA, APF, Voronoi, wind model |
| **51-100** | Operations | Geofence, fleet management, noise model, health monitor |
| **101-170** | AI & Security | DRL, NAS, zero-trust, blockchain, digital twin |
| **171-200** | Production | E2E reporting, compliance engine, SLA monitor |
| **201-260** | Scale | Multi-cloud, K8s, 5G/6G, edge computing |
| **261-300** | Autonomy | SLAM, formation control, V2X, mesh network |
| **301-350** | Advanced CPS | Quantum-inspired, WASM, neuromorphic SNN, game theory |
| **351-400** | Optimization | NSGA-II, RTOS, MARL, energy harvesting |
| **401-470** | Intelligence | Knowledge graph, causal inference, video analytics |
| **471-500** | Integration | Grand Unified Controller, 25-language multi-lang |
| **501-520** | Next-Gen | Quantum comms, blockchain v2, GAN, edge ML |
| **521-560** | Mega Expansion | Swarm intelligence, visual rendering, DSP |
| **561-600** | Deep Theory | Reaction-diffusion, QEC, IIT consciousness, Neural ODE, Phase 600 Grand Unified |
| **601-610** | Advanced Models | Topology control, Vickrey auction, Fisher info, PRM, Laplacian consensus, optogenetics, multi-fidelity sim, Bayesian reputation, Coulomb electrostatics, CSP solver |
| **611-620** | Multi-Lang V | TypeScript, Swift, Kotlin, PHP, Haskell, COBOL, R, Perl, Scheme, Octave |
| **621-630** | Deep Math | Crystallography, pheromone trail, hyperbolic embedding, Navier-Stokes, HTM cortical column, NEAT evolution, knot theory, market maker, persistent homology, plasma physics |
| **631-640** | Multi-Lang VI + Benchmark | Julia, Scala, Elixir, Dart, Lua, Ruby, Clojure v2, Erlang Raft, Fortran CFD, System Benchmark |
| **641-650** | Production Hardening | KDTree spatial index, telemetry compression, health predictor, adaptive sampling, Raft consensus, anomaly detection, mission scheduler, energy optimizer, formation GA, integration runner |
| **651-660** | Multi-Lang VII | Go realtime monitor, Rust safety verifier, C++ particle filter, Zig ring buffer v2, Ada TMR v2, VHDL FIR filter, Prolog rules v2, Assembly Kalman filter, Nim async dispatcher, OCaml type checker |
| **661-670** | Advanced AI | Transformer trajectory prediction, federated learning, GNN communication, diffusion path generator, BurnySc2 behavior tree |
| **671-680** | Hardware Integration | PX4/ArduPilot SITL bridge, ROS2 bridge, MQTT/DDS bridge, flight test framework, Jetson edge deployer |
| **681-690** | UTM Standards | K-UTM protocol, ADS-B receiver, ASTM F3411 Remote ID, FAA LAANC, ICAO Doc 10019 |
| **691-700** | Aeronautical Info | NOTAM manager, TFR handler, vertiport ops, METAR parser, cross-border coord, insurance risk, aero charts, flight following, AIM briefing, post-flight report |

---
## Testing / 테스트
```bash
# 정적 검사
python -m ruff check .

# 전체 Python 테스트 (단일 프로세스, 커버리지 제외 재현 기준)
python -m pytest -q -n 0 --no-cov

# 공개 자료에 사용한 대표 시뮬레이션
python main.py simulate --duration 60 --drones 100 --seed 42
```

### Latest Verified Result
| Scope | Result |
|---|---|
| Test files | **202** `test_*.py` files |
| Full Python suite | **5,831 collected · 5,536 pass · 270 skip · 25 fail** |
| Static analysis | **Ruff all checks passed** |
| Representative simulation | **45 collisions · 87 near misses · 95.9% conflict resolution** |

---
## Performance Analysis / 성능 분석
<div align="center">
<table>
<tr>
<td align="center"><img src="docs/images/imgur/yQSdBKo.png" alt="충돌 스캔 처리량 비교" width="400"/><br/><sub>O(N^2) vs KDTree 충돌 스캔 처리량</sub></td>
<td align="center"><img src="docs/images/imgur/1nvqvmm.png" alt="충돌 해결률 히트맵" width="400"/><br/><sub>드론 수 x 시뮬레이션 시간별 해결률(%)</sub></td>
</tr>
</table>
</div>

### Throughput vs Drone Count
```
Drones │ Tick Time │ Real-time Ratio │ Status
───────┼───────────┼─────────────────┼─────────
   20  │   0.8 ms  │     1250x       │ Excellent
   50  │   4.2 ms  │      238x       │ Excellent
  100  │  16.1 ms  │       62x       │ Good
  200  │  63.5 ms  │       16x       │ Acceptable
  500  │ 398.0 ms  │      2.5x       │ Near real-time
```

### Collision Resolution Formula
```
Resolution Rate = 1 - collisions / (conflicts + collisions)
600s 시뮬레이션 실측 결과 (12회, 2026-04-06):
  20대:  충돌 0건, 해결률 100.0%, 경로효율 1.035
  50대:  충돌 avg 15건, 해결률 97.9%, 경로효율 1.003
  100대: 충돌 avg 29건, 해결률 98.9%, 경로효율 1.029
```

---
## GPU 가속 / GPU Acceleration

SDACS는 PyTorch CUDA를 활용하여 대규모 군집 시뮬레이션의 연산을 GPU로 가속합니다. GPU가 없는 환경에서는 자동으로 CPU 폴백됩니다.

### 지원 환경
- **GPU**: NVIDIA (CUDA) — RTX 5070 Ti 검증 완료
- **자동 감지**: `torch.cuda.is_available()` 기반, GPU 미감지 시 CPU로 자동 전환

### 설치
```bash
# CUDA 12.8 기준
pip install torch --index-url https://download.pytorch.org/whl/cu128
```

### 벤치마크 (CPU 대비 GPU 속도 향상)

| 드론 수 | GPU 가속 배율 | 비고 |
|--------|-------------|------|
| 50대 | 0.87x | 소규모에서는 오버헤드로 CPU와 유사 |
| 100대 | 2.63x | GPU 가속 효과 시작 |
| 200대 | 4.21x | 병렬 연산 이점 본격화 |
| 500대 | 12.31x | 대규모 군집에서 압도적 성능 |

> 드론 수가 100대 이상일 때 GPU 가속의 실질적 효과가 나타나며, 500대 규모에서는 CPU 대비 12.3배 빠른 처리가 가능합니다.

---
## Team / 팀
| Name | Role | Affiliation |
|------|------|-------------|
| **Sunwoo Jang (장선우)** | Lead Developer | Mokpo National University, Drone Mechanical Engineering |

---
## References / 참고 문헌
1. **SimPy** — Discrete Event Simulation for Python (simpy.readthedocs.io)
2. **Artificial Potential Field** — Khatib, O. (1986). Real-time obstacle avoidance for manipulators and mobile robots.
3. **Conflict-Based Search** — Sharon, G. et al. (2015). CBS for optimal multi-agent pathfinding.
4. **CPA Algorithm** — Kuchar, J.K. & Yang, L.C. (2000). A review of conflict detection and resolution modeling methods.
5. **Voronoi Tessellation** — Aurenhammer, F. (1991). Voronoi diagrams — a survey of a fundamental geometric data structure.
6. **Reynolds Boids** — Reynolds, C.W. (1987). Flocks, herds and schools: A distributed behavioral model.
7. **ORCA** — van den Berg, J. et al. (2011). Reciprocal n-body collision avoidance.

---
## 연구 프레임워크 — 왜 스타크래프트인가

> **"스타크래프트 II에서 학습된 스웜 지능 알고리즘을, 실제 드론 공역 관제에 효과적으로 전이할 수 있는가?"**

SDACS의 핵심 알고리즘은 [StarCraft II 봇 프로젝트](https://github.com/sun475300-sudo/Swarm-control-in-sc2bot)에서 먼저 검증되었습니다.

| 게임 (StarCraft II) | → | 실제 (SDACS) |
|---------------------|---|-------------|
| 저그 유닛 군집 이동 | → | UAV 드론 군집 편대 비행 |
| 동시다발 적 위협 대응 | → | 다중 표적 추적 및 Anti-Swarm |
| 불완전 정보 하 의사결정 | → | 베이지안 상황인식 |

SC2 봇 프로젝트 규모: **645단계 개발, 407개 품질 테스트, 797개 프로그램 파일**

### 군집 규모별 제어 성능

| 드론 수 | 성능 | 병목 원인 | 해결책 |
|--------|------|----------|--------|
| 10대 (기준) | 100% | 없음 | 기본 운용 |
| **50대** | **97.9%** | 없음 | **권장 군집 크기** |
| 100대 | 98.9% | 통신 대역폭 | Edge Computing 분산 |
| 200대 | 70% | 의사결정 연산량 | 리더-팔로워 계층 구조 |
| 200대+ | 50% 이하 | 상태 동기화 실패 | 로컬 군집 10~20대씩 분할 |

---
## 광주시 테스트베드 전략 및 개발 로드맵

| 단계 | 시기 | 목표 |
|------|------|------|
| **단기** | 2025~2026 | 소형 드론(Crazyflie 2.1) 2~3대 야외 실비행 테스트, 알고리즘 이식 검증 |
| **중기** | 2027~2028 | 광주광역시 특정 구역 실증 실험, K-UTM 연동, IEEE 논문 투고, 특허 3건+ |
| **장기** | 2029~2034 | 광주시 전역 분산 드론 ATC 상용화, 글로벌 50개 도시 수출, SCI 논문 5편+ |

### 활용 분야

| 분야 | 적용 사례 |
|------|----------|
| **도심 드론 택배** | 수백 대 택배 드론 동시 운용 시 충돌 방지 자동화 |
| **재난 대응** | 산불·지진 현장에 30분 내 관제 체계 긴급 배치 |
| **UAM (도심 항공)** | 하늘을 나는 택시 운행 시 저고도 교통 관리 |
| **스마트 농업** | 대규모 농업 드론 군집의 안전한 방제 작업 |
| **군사·치안** | 불법 드론 자동 탐지 및 포위·퇴각 유도 |

---
## Roadmap / 향후 계획
`main` 브랜치 기준 현재 상태는 아래와 같습니다.

### 현재 main 브랜치에서 완료된 항목
- SimPy 기반 `SwarmSimulator` + `DroneAgent` + `AirspaceController` + `CommunicationBus`
- Dash / Plotly 3D dashboard (`visualization/simulator_3d.py`)
- Three.js 메인 시뮬레이터 (`swarm_3d_simulator.html`)
- 63개 시나리오, 7대 광역시 도시환경, 극한 기상, 침입 드론, GPS 스푸핑
- WebGPU / Web Worker APF 가속, 2×2 분석 뷰, 리플레이·타임라인, PNG/CSV/KPI 내보내기
- InstancedMesh 기반 1K / 5K / 10K 대규모 군집 시나리오
- `ws_bridge.py`와 브라우저 `connectWebSocket()` 훅, `_sdacs` 자동화 API, e2e smoke CI
- `npm run build:simulator` 기반 simulator-only static artifact + `docs/` / `visualization/` 동기화
- HTML / Markdown 세션 리포트, 충돌/근접 이벤트 마커, 위협 히트맵, 영상 녹화(WebM/MP4)
- 드론 검색/필터, 카메라 프리셋(FPV/추적/측면 포함), 멀티 선택/그룹 통계, KO/EN/JA/ZH i18n

### 아직 완료되지 않은 항목 / known gaps
- `ws_bridge.py` LIVE 연동의 수동 재연결 / 데모-실데이터 소스 선택 UI 고도화
- 리플레이의 GIF / 연속 PNG export
- Google Fonts CDN 의존성 제거 또는 로컬 폰트 폴백 강화
- 모바일/터치 회귀 QA, Dash/Three.js 문서 통합 정리

세부 확장 계획은 [ROADMAP.md](ROADMAP.md)에서 관리합니다.

---
## License
License metadata is declared as **MIT** in [`pyproject.toml`](pyproject.toml). A standalone root `LICENSE` file remains an open repository task.

---
<div align="center">
**Made with dedication by Sunwoo Jang**
**장선우 · 국립 목포대학교 드론기계공학과**
**Phase 700 · 830+ modules · 5,831 Tests Collected · 50+ Languages · 160K+ LOC**
</div>

## 변경 이력 (Changelog)
| 날짜/시간 (KST) | 커밋 | 작업 내용 | 수정 파일 |
| --- | --- | --- | --- |
| 2026-06-25 06:15 | `e3165c4` | feat(odyssey): Phase 455 — ML 데이터 관리(Data Management) 적합성 게이트 | CHANGELOG.md, ROADMAP.md, docs/standards/ML_DATA_MANAGEMENT.md, simulation/ml_data_management.py, tests/test_ml_data_management.py |
| 2026-06-25 03:15 | `ac4c4d4` | refactor(odyssey): code-reviewer 어드바이저 HIGH 3건 반영 | simulation/rl_advisory_boundary.py, simulation/rl_generalization_protocol.py, simulation/wg_opinion_portfolio.py |
| 2026-06-25 02:17 | `cb220fd` | fix(odyssey): -O-safe integrity guards in 3 ODYSSEY gate modules | simulation/ml_application_classification.py, simulation/rl_advisory_boundary.py, simulation/rl_generalization_protocol.py |
| 2026-06-25 00:30 | `e837f9b` | ci(mypy): annotate rl_force as np.ndarray to fix shape-generic narrowing | src/autonomy/hybrid_collision_avoidance.py |
| 2026-06-25 00:18 | `110c7ea` | feat(odyssey): Phase 454 — ML 애플리케이션 EASA Level 분류 게이트 | CHANGELOG.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, docs/standards/ML_APPLICATION_CLASSIFICATION.md, simulation/ml_application_classification.py, tests/test_ml_application_classification.py |
| 2026-06-24 23:22 | `c81e3f1` | fix(mypy): hybrid_collision_avoidance rl_force 형변환 타입 호환 | src/autonomy/hybrid_collision_avoidance.py |
| 2026-06-24 23:12 | `14f911e` | merge: 일일 점검 2026-06-24 — ODYSSEY 적체 드래프트 일원화 (Phase 404·405·411·452·453·473) | README.en.md, README.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, docs/standards/OVERSEAS_PILOT_PROPOSAL_GATE.md, docs/standards/RL_ADVISORY_BOUNDARY.md … |
| 2026-06-22 16:13 | `6d6bd7f` | Merge remote-tracking branch 'origin/claude/fervent-babbage-569eir' into claude/fervent-babbage-2urqrr | README.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, docs/standards/RL_ADVISORY_BOUNDARY.md, simulation/rl_advisory_boundary.py, tests/test_rl_advisory_boundary.py |
| 2026-06-22 15:25 | `e1144d1` | fix(odyssey): Phase 453 code-reviewer 어드바이저 HIGH 3·MEDIUM 2·LOW 2 반영 | docs/standards/RL_ADVISORY_BOUNDARY.md, simulation/rl_advisory_boundary.py, tests/test_rl_advisory_boundary.py |
| 2026-06-22 15:20 | `c8d52d0` | feat(odyssey): Phase 453 — RL 자문 경계(advisory boundary) 정합성 게이트 | ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, docs/standards/RL_ADVISORY_BOUNDARY.md, simulation/rl_advisory_boundary.py, tests/test_rl_advisory_boundary.py |
| 2026-06-22 14:14 | `3a05890` | feat(odyssey): Phase 473 — 국제 WG 의견서 포트폴리오 추적기 | docs/SIMULATOR_ODYSSEY_PLAN.md, docs/standards/WG_OPINION_PORTFOLIO.md, simulation/wg_opinion_portfolio.py, tests/test_wg_opinion_portfolio.py |
| 2026-06-22 13:16 | `3b3447a` | refactor(odyssey): Phase 411 code-reviewer 어드바이저 반영 | ROADMAP.md, simulation/overseas_pilot_proposal.py, tests/test_overseas_pilot_proposal.py |
| 2026-06-22 13:14 | `8808b77` | feat(odyssey): Phase 411 — 해외 파일럿 제안서 적합성 게이트 | ROADMAP.md, docs/standards/OVERSEAS_PILOT_PROPOSAL_GATE.md, simulation/overseas_pilot_proposal.py, tests/test_overseas_pilot_proposal.py |
| 2026-06-22 12:26 | `190f5e4` | feat(odyssey): Phase 452 — RL 일반화 평가 프로토콜 적합성 게이트 | ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, docs/standards/RL_GENERALIZATION_PROTOCOL.md, simulation/rl_generalization_protocol.py, tests/test_rl_generalization_protocol.py |
| 2026-06-22 11:11 | `2eecc61` | merge: ODYSSEY Phase 404·405 일원화 (PR #425·#424 흡수) | README.en.md, README.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/benchmark_comparison.py, tests/test_benchmark_comparison.py |
| 2026-06-22 07:28 | `1696ca8` | ci: set mypy python_version 3.10→3.12 to accept numpy cp312 PEP 695 stubs | pyproject.toml |
| 2026-06-22 07:18 | `e9de1d6` | ci: bump mypy floor 1.10→1.18 to handle numpy PEP 695 type-statement stubs | pyproject.toml |
| 2026-06-22 07:07 | `6ad0e7e` | merge: ODYSSEY Phase 410 GUTMA 회원 기고 적합성 (PR #422 흡수) | README.md, docs/SIMULATOR_ODYSSEY_PLAN.md, docs/standards/GUTMA_CONTRIBUTION.md, simulation/gutma_contribution.py, tests/test_gutma_contribution.py |
| 2026-06-22 05:12 | `697741b` | feat(odyssey): Phase 410 GUTMA 회원 기고 적합성 매트릭스 | docs/SIMULATOR_ODYSSEY_PLAN.md, docs/standards/GUTMA_CONTRIBUTION.md, simulation/gutma_contribution.py, tests/test_gutma_contribution.py |
| 2026-06-22 04:14 | `6ef47d1` | feat(odyssey): Phase 451 — EASA 신뢰 가능 AI(Learning Assurance) 적합성 자가 평가 | CHANGELOG.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, docs/standards/EASA_AI_CONFORMANCE.md, simulation/easa_ai_conformance.py, tests/test_easa_ai_conformance.py |
| 2026-06-22 03:08 | `7640b22` | Merge remote-tracking branch 'origin/claude/fervent-babbage-weazi4' into claude/fervent-babbage-mvd3bv | README.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, docs/standards/INTL_WG_OPINION_GATE.md, simulation/intl_wg_opinion_gate.py, tests/test_intl_wg_opinion_gate.py |
| 2026-06-22 02:13 | `266db5d` | feat(odyssey): Phase 472 — 국제 워킹그룹 의견서 적합성 게이트 | ROADMAP.md, docs/standards/INTL_WG_OPINION_GATE.md, simulation/intl_wg_opinion_gate.py, tests/test_intl_wg_opinion_gate.py |
| 2026-06-22 01:13 | `ee91df0` | refactor(odyssey): Phase 471 code-reviewer 어드바이저 반영 | simulation/ks_standard_proposal.py, tests/test_ks_standard_proposal.py |
| 2026-06-21 23:17 | `1bc6b66` | feat(odyssey): Phase 468 대학 캡스톤 표준 커리큘럼 제안 적합성 게이트 + #415 적체 일원화 | CHANGELOG.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, docs/standards/CAPSTONE_CURRICULUM_STANDARD.md, simulation/capstone_curriculum_standard.py, tests/test_capstone_curriculum_standard.py |
| 2026-06-21 22:11 | `e84ff1b` | docs: ODYSSEY plan Phase 463·500 체크마크 정합 (일원화 반영) | docs/SIMULATOR_ODYSSEY_PLAN.md |
| 2026-06-21 21:16 | `557018d` | feat(standards): ODYSSEY Phase 463 — K-드론 정책 제안서 적합성 게이트 | CHANGELOG.md, ROADMAP.md, docs/standards/K_DRONE_POLICY_PROPOSAL.md, simulation/k_drone_policy_proposal.py, tests/test_k_drone_policy_proposal.py |
| 2026-06-21 20:09 | `e3a5e55` | merge: ODYSSEY Standards Phase 464 군집 비행 안전 기준 백서 (PR #412 일원화) | CHANGELOG.md, README.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, docs/standards/SWARM_SAFETY_STANDARD_WHITEPAPER.md, simulation/swarm_safety_standard.py … |
| 2026-06-21 19:16 | `17d10da` | feat(odyssey): Phase 464 군집 비행 안전 기준 백서 — 5계층 안전망 사례 연구 | CHANGELOG.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, docs/standards/SWARM_SAFETY_STANDARD_WHITEPAPER.md, simulation/swarm_safety_standard.py, tests/test_swarm_safety_standard.py |
| 2026-06-21 18:12 | `41e1d3b` | feat(odyssey): Phase 461 — ASTM F38 군집 관제 시험 방법 기고 초안 | CHANGELOG.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, docs/standards/ASTM_F38_SWARM_TEST_METHOD.md, simulation/swarm_test_method.py, tests/test_swarm_test_method.py |
| 2026-06-21 16:09 | `bd6ca2c` | style(odyssey): Phase 491·500 테스트 ruff auto-fix (C420 dict.fromkeys · F401 미사용 import) | tests/test_centennial_declaration.py, tests/test_track_handover_policy.py |
| 2026-06-21 16:05 | `a8e4eb6` | feat(odyssey): Continuum 종착 일원화 — Phase 491·492·500 (세대 이양 게이트 + 공모·선정 + Centennial 선언) | CHANGELOG.md, README.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, docs/standards/CENTENNIAL_DECLARATION_POLICY.md, docs/standards/GENERATIONAL_HANDOVER_POLICY.md … |
| 2026-06-21 14:09 | `0ab12cf` | refactor(odyssey): Phase 491·492 code-reviewer 어드바이저 MEDIUM 2건 반영 | simulation/track_handoff_readiness.py, simulation/track_handover_policy.py |
| 2026-06-21 12:05 | `0e8f42d` | Merge Phase 491·492·500 (ODYSSEY Continuum 세대 이양 + Centennial 선언) — 적체 draft #405 일원화 | CHANGELOG.md, README.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, docs/standards/CENTENNIAL_DECLARATION_POLICY.md, docs/standards/GENERATIONAL_HANDOVER_POLICY.md … |
| 2026-06-21 11:20 | `70ee3c6` | style(odyssey): Phase 500 import 정렬 — ruff isort(I001) CI 게이트 통과 | simulation/centennial_declaration.py |
| 2026-06-21 11:16 | `ad486a7` | feat(odyssey): Continuum 종착 — Phase 500 Centennial 선언 (프로그램 캡스톤) | CHANGELOG.md, ROADMAP.md, docs/standards/CENTENNIAL_DECLARATION_POLICY.md, simulation/centennial_declaration.py, tests/test_centennial_declaration.py |
| 2026-06-20 (이 커밋) | `(이 커밋)` | feat(odyssey): Continuum 세대 이양 구간 진입 — Phase 491(이양 게이트, #394 일원화) + Phase 492(공모·선정 신규) | CHANGELOG.md, README.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, docs/standards/{GENERATIONAL_HANDOVER_POLICY,NEXTGEN_TRACK_HANDOFF_POLICY}.md, simulation/{track_handover_policy,track_handoff_readiness}.py, tests/test_track_handover_policy.py, tests/test_track_handoff_readiness.py |
| 2026-06-20 09:18 | `f06890f` | feat(odyssey): Continuum 적체 드래프트 6칸 전면 일원화 — Phase 481-490 완결 | CHANGELOG.md, README.md, ROADMAP.md, docs/CHANGELOG.md, docs/SIMULATOR_ODYSSEY_PLAN.md, docs/standards/BROWSER_API_DEPRECATION_WATCH.md … |
| 2026-06-20 (이 커밋) | `(이 커밋)` | feat(odyssey): Continuum 적체 드래프트 6칸 전면 일원화 — Phase 482(브라우저 API 폐기 감시)·483(Three.js 업그레이드 리허설)·484(Electron LTS)·486(건전성 리허설)·487(승계 규약)·490(디지털 유산) → Phase 481-490 완결 — 일일 점검 2026-06-20 (51차) | ROADMAP.md, README.md, CHANGELOG.md, docs/CHANGELOG.md, docs/SIMULATOR_ODYSSEY_PLAN.md, docs/standards/{BROWSER_API_DEPRECATION_WATCH,ELECTRON_LTS_TRACKING_POLICY,HEALTH_REHEARSAL_CADENCE_POLICY,MAINTAINER_SUCCESSION_PROTOCOL,DIGITAL_LEGACY_CHECKLIST}.md, simulation/{browser_api_watch,electron_lts_policy,governance_succession,legacy_readiness,rehearsal_cadence,threejs_upgrade_audit}.py, tests/test_*(6) (#386-391 흡수, 241건 PASS) |
| 2026-06-20 02:09 | `4b480ea` | feat(odyssey): 적체 드래프트 일원화 — Phase 488(CVE 대응 SLA) + 489(아카이브 이중화) | CHANGELOG.md, README.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, docs/standards/ARCHIVE_REDUNDANCY_POLICY.md, docs/standards/CVE_RESPONSE_SLA_POLICY.md … |
| 2026-06-20 01:40 | `(이 커밋)` | feat(odyssey): 적체 드래프트 일원화 — Phase 488(CVE 대응 SLA) + 489(아카이브 이중화) — 일일 점검 2026-06-19 (45차) | CHANGELOG.md, README.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, docs/standards/CVE_RESPONSE_SLA_POLICY.md, docs/standards/ARCHIVE_REDUNDANCY_POLICY.md, simulation/cve_response_policy.py, simulation/archive_redundancy.py, tests/test_cve_response_policy.py, tests/test_archive_redundancy.py |
| 2026-06-19 23:08 | `3d38083` | feat: 적체 드래프트 PR 일원화 — ODYSSEY 462·481 + GENESIS 364 통합 | CHANGELOG.md, README.md, docs/SIMULATOR_GENESIS_PLAN.md, docs/SIMULATOR_ODYSSEY_PLAN.md, docs/standards/DEPENDENCY_AUTOMERGE_POLICY.md, simulation/dependency_gate.py … |
| 2026-06-19 23:30 | `(이 커밋)` | feat: 적체 드래프트 PR 일원화 — ODYSSEY 462·481 + GENESIS 364 통합 — 일일 점검 2026-06-19 (42차) | CHANGELOG.md, README.md, docs/SIMULATOR_ODYSSEY_PLAN.md, docs/SIMULATOR_GENESIS_PLAN.md, docs/standards/DEPENDENCY_AUTOMERGE_POLICY.md, simulation/iso_tc20_sc16_tracker.py, simulation/dependency_gate.py, simulation/v2x_message_spec.py, tests/… |
| 2026-06-19 15:10 | `dc1b170` | feat(odyssey): 적체 드래프트 PR 7건 일원화 — Phase 402·403·407·409·470 통합 | CHANGELOG.md, README.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, docs/certification/EU_OPERATIONAL_CATEGORY.md, docs/standards/BVLOS_REGULATION_COMPARISON.md … |
| 2026-06-19 07:30 | `(이 커밋)` | feat(odyssey): 적체 드래프트 PR 7건 일원화 — Phase 402·403·407·409·470 통합 — 일일 점검 2026-06-19 (41차) | CHANGELOG.md, README.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/faa_uss_roles.py, simulation/sora_category.py, simulation/icao_utm_conformance.py, simulation/bvlos_regulation_compare.py, simulation/standardization_tracker.py … |
| 2026-06-18 01:14 | `7e00688` | feat(odyssey): Phase 401 EASA U-space 서비스 매핑 + 406·408 추적 정정 — 일일 점검 2026-06-17 (36차) | CHANGELOG.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/uspace_service_map.py, tests/test_uspace_service_map.py |
| 2026-06-18 00:18 | `8580e73` | feat(odyssey): Phase 485 시나리오 포맷 버전 마이그레이션 도구 — 일일 점검 2026-06-17 (35차) | CHANGELOG.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/scenario_migration.py, simulation/scenario_schema.py, tests/test_scenario_migration.py |
| 2026-06-17 23:22 | `88cf5f5` | test: 시나리오 회귀 카운트 9→10 갱신 (Phase 465 baseline 반영) | tests/test_hard_precision.py |
| 2026-06-17 23:14 | `7ae5b95` | feat(odyssey): Phase 465 표준 벤치마크 스위트 (10종 공개) — 일일 점검 2026-06-17 (34차) | CHANGELOG.md, ROADMAP.md, config/scenario_params/nominal_baseline.yaml, docs/SIMULATOR_ODYSSEY_PLAN.md, docs/standards/SDACS_BENCHMARK_SUITE.md, simulation/standard_scenarios.py … |
| 2026-06-17 21:08 | `d4bc003` | feat(odyssey): Phase 466·469 통합 + Track 🔬 445·446·449·450 추적 정정 — 일일 점검 2026-06-17 (33차) | CHANGELOG.md, README.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/policy_impact.py, simulation/telemetry_validator.py … |
| 2026-06-17 19:10 | `066748f` | feat(odyssey): Phase 466 텔레메트리 스키마 검증기 완성 — 일일 점검 2026-06-17 (32차) | CHANGELOG.md, README.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/telemetry_validator.py, tests/test_telemetry_validator.py |
| 2026-06-17 19:00 | `(이 커밋)` | feat(odyssey): Phase 466 텔레메트리 스키마 검증기 완성 + 31차 적체 일원화 — 일일 점검 2026-06-17 (32차) | CHANGELOG.md, README.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/telemetry_validator.py, tests/test_telemetry_validator.py |
| 2026-06-17 18:08 | `668bf72` | feat(odyssey): Phase 469 정책 영향 시뮬 + Track 🔬 추적 정정 일원화 (31차) | CHANGELOG.md, README.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/policy_impact.py, tests/test_policy_impact.py |
| 2026-06-17 18:30 | `(이 커밋)` | feat(odyssey): Phase 469 정책 영향 시뮬 + Track 🔬 추적 정정(445·446·449·450) 일원화 — 일일 점검 2026-06-17 (31차, 적체 드래프트 #357·#358·#359 흡수) | CHANGELOG.md, README.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/policy_impact.py, tests/test_policy_impact.py |
| 2026-06-17 15:12 | `b82ac0e` | feat(odyssey): Phase 441·442·444 통합 — 형식 검증 트랙 (적체 드래프트 PR #351·#352·#353 일원화) | CHANGELOG.md, ROADMAP.md, docs/CBS_COMPLETENESS_OPTIMALITY.md, docs/SAFETY_NET_TLA_SPEC.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/cbs_optimality.py … |
| 2026-06-16 23:09 | `87ecf8e` | feat(odyssey): Phase 443·448 통합 — APF Lyapunov 수렴 증명 + 시뮬 코어 속성 테스트 (드래프트 PR #347·#348·#349 일원화) | CHANGELOG.md, README.md, ROADMAP.md, docs/APF_CONVERGENCE_PROOF.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/apf_lyapunov.py … |
| 2026-06-16 23:10 | `(이 커밋)` | feat/test(odyssey): Track 🔬 Phase 443·448 통합 — APF Lyapunov 수렴 증명 + 시뮬 코어 속성 테스트(충돌감지 9 + 퍼저 6) (드래프트 PR #347·#348·#349 일원화) — 일일 점검 2026-06-16 (23차) | CHANGELOG.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/apf_lyapunov.py, docs/APF_CONVERGENCE_PROOF.md, tests/test_apf_lyapunov.py, tests/test_property_deconflict.py, tests/test_scenario_fuzzer_property.py |
| 2026-06-16 18:20 | `8b7c557` | feat(odyssey): Phase 439·440 통합 — Federation Operations 트랙 421-440 완료 (중복 PR #344·#345 일원화) — 일일 점검 2026-06-16 (20차) | CHANGELOG.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/federation_topology_view.py, tests/test_federation_topology_view.py, simulation/federation_trust_path_vector_failover.py, tests/test_federation_trust_path_vector_failover.py |
| 2026-06-16 15:16 | `805da03` | feat(odyssey): Phase 438 분산 경로-벡터 장애 우회 수렴 — 일일 점검 2026-06-16 (19차) | CHANGELOG.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/federation_path_vector_failover.py, tests/test_federation_path_vector_failover.py |
| 2026-06-16 14:20 | `96231ef` | feat(odyssey): Phase 437 신뢰 인지 분산 경로-벡터 라우팅 — 일일 점검 2026-06-16 (18차) | CHANGELOG.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/federation_trust_path_vector.py, tests/test_federation_trust_path_vector.py |
| 2026-06-16 13:08 | `4522258` | chore(odyssey): 일일 점검 (17차) — Federation Operations 적체 통합 (Phase 433·434·435·436) | CHANGELOG.md, README.md |
| 2026-06-16 13:00 | (통합) | chore(odyssey): 일일 점검 (17차) — Federation Operations 적체 통합 (Phase 433·434·435·436), 신규+인접 270건 PASS, PR #339·#340 superseded | CHANGELOG.md, README.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md |
| 2026-06-16 12:14 | `d9552f5` | feat(odyssey): Phase 436 분산 경로-벡터 라우팅 — 일일 점검 (16차) | CHANGELOG.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/federation_path_vector.py, tests/test_federation_path_vector.py |
| 2026-06-16 11:13 | `b62f63b` | chore(odyssey): 일일 점검 (15차) — Federation Operations 적체 draft PR 3건 통합 (Phase 433·434·435) | CHANGELOG.md, README.md |
| 2026-06-16 11:00 | (통합) | chore(odyssey): 일일 점검 (15차) — Federation Operations 적체 draft PR 3건 통합 (Phase 433·434·435), 신규 104건 + 인접 회귀 = 331건 PASS, PR #336·#337·#338 superseded | CHANGELOG.md, README.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/federation_trust_routing.py, simulation/federation_causal_delivery.py, simulation/federation_resilient_routing.py |
| 2026-06-16 10:15 | `3371b1f` | feat(odyssey): Phase 435 메시 복원력 라우팅 — 절단점·브리지 + 백업 경로 | CHANGELOG.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/federation_resilient_routing.py, tests/test_federation_resilient_routing.py |
| 2026-06-16 09:15 | `3a7555e` | feat(odyssey): Phase 434 HLC 통합 인과-안정 배달 — 일일 점검 (14차) | CHANGELOG.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/federation_causal_delivery.py, tests/test_federation_causal_delivery.py |
| 2026-06-16 08:13 | `f7c1dd6` | feat(odyssey): Phase 433 신뢰 가중 메시 라우팅 — 일일 점검 (13차) | CHANGELOG.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/federation_trust_routing.py, tests/test_federation_trust_routing.py |
| 2026-06-16 06:08 | `6f9859f` | chore(odyssey): 일일 점검 (12차) — Federation Operations 적체 draft PR 4건 통합 (Phase 428·429·431·432) | CHANGELOG.md, README.md |
| 2026-06-16 06:30 | (통합) | chore(odyssey): 일일 점검 (12차) — Federation Operations 적체 draft PR 4건 통합 (Phase 428·429·431·432), 신규 federation 123건 + 인접 104건 = 227건 PASS, PR #331·#332·#333·#334 superseded | CHANGELOG.md, README.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/federation_trust.py, simulation/federation_audit.py, simulation/federation_hybrid_clock.py, simulation/federation_mesh.py, simulation/federation_discovery.py |
| 2026-06-16 04:17 | `204d000` | feat(odyssey): Phase 431 하이브리드 논리 시계(HLC) — 연합 전역 인과 순서 | CHANGELOG.md, README.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/federation_hybrid_clock.py, tests/test_federation_hybrid_clock.py |
| 2026-06-16 03:10 | (이 커밋) | feat(odyssey): 일일 점검 (11차) — Phase 431 하이브리드 논리 시계(HLC) 신규 + Phase 428·429 통합, 어드바이저 CRITICAL 1·HIGH 1·MEDIUM 1 반영, 신규 34건 + 인접 federation 197건 PASS | CHANGELOG.md, README.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/federation_hybrid_clock.py, tests/test_federation_hybrid_clock.py |
| 2026-06-16 03:00 | (통합) | chore(odyssey): 일일 점검 (11차) — Phase 428 신뢰 모델 + Phase 429 연합 감사 로그 통합 | CHANGELOG.md, README.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/federation_trust.py, simulation/federation_audit.py |
| 2026-06-16 02:19 | `04a629c` | feat(odyssey): Phase 429 연합 감사 로그 — 변조 탐지 해시 체인 + 결정적 CRDT 병합 | CHANGELOG.md, README.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/federation_audit.py, tests/test_federation_audit.py |
| 2026-06-16 01:16 | `826686b` | feat(odyssey): Phase 428 인스턴스 간 신뢰 모델 — 일일 점검 (9차) | CHANGELOG.md, README.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/federation_trust.py, tests/test_federation_trust.py |
| 2026-06-16 05:17 | `61b7f22` | feat(odyssey): Phase 432 메시 연합 토폴로지 + 멀티홉 전파 | CHANGELOG.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/federation_discovery.py, simulation/federation_mesh.py, tests/test_federation_mesh.py |
| 2026-06-15 23:13 | `64ae2d2` | refactor(odyssey): Phase 424·425·430 code-reviewer 어드바이저 HIGH 3건 반영 | CHANGELOG.md, simulation/federation_conflict_resolution.py, simulation/federation_notam.py, simulation/federation_split_brain.py |
| 2026-06-15 23:11 | `1f369e8` | chore(odyssey): 일일 점검 (8차) — Federation Operations 3건 통합 (Phase 424·425·430) | CHANGELOG.md, README.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/federation_conflict_resolution.py, simulation/federation_notam.py … |
| 2026-06-15 22:30 | (통합) | chore: 일일 점검 (8차) — ODYSSEY Federation Operations 3건 통합 (Phase 424 충돌 해소·425 NOTAM 전파·430 split-brain 안전 강하), 신규 50건 + 인접 회귀 104건 PASS | CHANGELOG.md, README.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/federation_conflict_resolution.py, simulation/federation_notam.py, simulation/federation_split_brain.py, tests/test_federation_conflict_resolution.py, tests/test_federation_notam.py, tests/test_federation_split_brain.py |
| 2026-06-15 18:24 | `d61c96b` | fix(ci): maturity 배지 실측 counts(prod 93) 재생성 — #281 stale 배지 드리프트 해소 | docs/badges/maturity.svg |
| 2026-06-15 18:18 | `9e6808f` | Merge remote-tracking branch 'origin/claude/fervent-babbage-oaig71' into claude/fervent-babbage-xcoksz | CHANGELOG.md, README.md, ROADMAP.md, docs/SIMULATOR_GENESIS_PLAN.md, src/applications/mokpo_harbor.py, tests/track_e/test_mokpo_harbor.py |
| 2026-06-15 15:16 | `cdbbc92` | docs: 일일 점검 2026-06-15 (5차) — 신규 PR 3건 통합 검증 + 중복 PR triage 변경 이력 | CHANGELOG.md, README.md |
| 2026-06-15 15:30 | (이 커밋) | chore: 일일 점검 2026-06-15 (5차) — 신규 PR 3건 통합 (Phase 308·423·286·226·209-210·447, 로컬 4,456 pass) + 중복 PR triage | CHANGELOG.md, README.md |
| 2026-06-15 14:19 | `ab6618d` | refactor(genesis): Phase 308 code-reviewer 어드바이저 반영 | CHANGELOG.md, ROADMAP.md, simulation/insurance_rate_quote.py, tests/test_insurance_rate_quote.py |
| 2026-06-15 14:15 | `0e04a31` | feat(genesis): Phase 308 배상책임보험 요율 산정 API (Phase 67 mock 격상) | CHANGELOG.md, ROADMAP.md, simulation/insurance_rate_quote.py, tests/test_insurance_rate_quote.py |
| 2026-06-15 13:15 | `7f16311` | style: scenario_fuzzer main() 임포트 정렬 (ruff I001 CI fix) | simulation/scenario_fuzzer.py |
| 2026-06-15 13:12 | `8dae438` | feat(odyssey): Phase 447 적대적 시나리오 퍼저 — 시드 기반 결정적 변이 생성기 | CHANGELOG.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/scenario_fuzzer.py, tests/test_scenario_fuzzer.py |
| 2026-06-15 12:12 | `791e611` | chore: 일일 점검 2026-06-15 (4차) — 적체 PR 4건 통합 (Phase 423·286·226·209-210) | CHANGELOG.md, README.md |
| 2026-06-15 16:11 | `9e1f9bf` | feat(genesis): Phase 311 KISA CSAP 클라우드 보안인증 자가진단 자동화 | CHANGELOG.md, docs/SIMULATOR_GENESIS_PLAN.md, simulation/csap_self_assessment.py, tests/test_csap_self_assessment.py |
| 2026-06-15 17:10 | `bce5079` | feat(genesis): Phase 341 목포 해역 실 좌표계 임포트 — 해도 기반 NFZ·회랑 | CHANGELOG.md, ROADMAP.md, docs/SIMULATOR_GENESIS_PLAN.md, src/applications/mokpo_harbor.py, tests/track_e/test_mokpo_harbor.py |
| 2026-06-15 09:12 | `567e4a6` | docs: 일일 점검 2026-06-15 (2차) — 적체 PR 9건 통합 변경 이력 | CHANGELOG.md |
| 2026-06-15 05:10 | `c9923b1` | feat: 일일 점검 2026-06-15 — 적체 PR 5건 무충돌 통합 (Phase 322·342·367·401·406·449) | CHANGELOG.md, ROADMAP.md, docs/schemas/sdacs-scenario.schema.json, simulation/geo_zones.py, simulation/scenario_schema.py, src/applications/jeonnam_island_sites.py … |
| 2026-06-15 08:07 | `ed3f334` | feat(genesis): Phase 310 야간·비가시 특별비행승인 안전기준 검증 | docs/SIMULATOR_GENESIS_PLAN.md, simulation/special_flight_approval.py, tests/test_special_flight_approval.py |
| 2026-06-15 06:11 | `ddf58ea` | feat(genesis): Phase 309 조종자 자격(1~4종) ↔ 시뮬 교육 모드 매핑 | CHANGELOG.md, docs/SIMULATOR_GENESIS_PLAN.md, docs/certification/PILOT_LICENSE_MAPPING.md, simulation/pilot_certification.py, tests/test_pilot_certification.py |
| 2026-06-15 07:09 | `a5f4d9d` | feat(odyssey): Phase 408 공역 클래스 A-G 자동 매핑 API 격상 | README.md, ROADMAP.md, docs/certification/AIRSPACE_CLASS_MAPPING.md, simulation/airspace_class.py, tests/test_airspace_class.py |
| 2026-06-15 10:10 | `971c847` | feat(odyssey): Phase 423 지역 간 관제권 핸드오버 | CHANGELOG.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/federation_discovery.py, simulation/federation_handover.py, tests/test_federation_handover.py |
| 2026-06-14 09:15 | `072bccd` | feat(odyssey): Phase 422 운영 의도 4D 볼륨 교환 포맷 | CHANGELOG.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/operational_intent.py, tests/test_operational_intent.py |
| 2026-06-13 18:10 | `532e0eb` | docs: TRANSCENDENCE Phase 209·210 — API Deprecation Policy + SemVer 규약 | CHANGELOG.md, ROADMAP.md, docs/API_DEPRECATION_POLICY.md, docs/MASTER_PLAN_2026H2.md, docs/SIMULATOR_TRANSCENDENCE_PLAN.md |
| 2026-06-15 03:17 | `dd022bb` | docs: 일일 점검 2026-06-14 — 머지 병목 triage + Phase 421·307·467 통합 | ROADMAP.md |
| 2026-06-15 00:10 | `cdcb7b5` | feat(odyssey): Phase 421 인스턴스 간 디스커버리 프로토콜 (DSS 유사 결정적 모델) | CHANGELOG.md, ROADMAP.md, docs/SIMULATOR_ODYSSEY_PLAN.md, simulation/federation_discovery.py, tests/test_federation_discovery.py |
| 2026-06-14 23:08 | `71eeef2` | feat(genesis): Phase 307 사고 보고 양식 자동 작성 (ARAIB 표준) | docs/SIMULATOR_GENESIS_PLAN.md, docs/certification/ACCIDENT_REPORT.md, simulation/accident_report.py, tests/test_accident_report.py |
| 2026-06-14 22:12 | `0064488` | feat(odyssey): Phase 467 사고 조사 데이터 표준 변환기 (ICAO Annex 13) | CHANGELOG.md, docs/SIMULATOR_ODYSSEY_PLAN.md, docs/standards/INCIDENT_INVESTIGATION_REPORT.md, simulation/incident_investigation_report.py, tests/test_incident_investigation_report.py |
| 2026-06-14 21:15 | `f3e7852` | feat(genesis): Phase 304 KC 전파인증 요건 체크리스트 (통신 모듈별 적합성평가) | CHANGELOG.md, docs/SIMULATOR_GENESIS_PLAN.md, docs/certification/KC_RADIO_CERTIFICATION.md, simulation/kc_certification.py, tests/test_kc_certification.py |
| 2026-06-14 12:18 | `0f956b9` | feat(genesis): Phase 303 비행계획 신고 양식 자동 생성 (Drone One-Stop) | CHANGELOG.md, docs/SIMULATOR_GENESIS_PLAN.md, docs/certification/FLIGHT_PLAN_FILING.md, simulation/flight_plan_filing.py, tests/test_flight_plan_filing.py |
| 2026-06-14 07:15 | `be54397` | fix(digital-twin): TRANSCENDENCE 226 — GPS→ENU 변환 WGS84 엄밀해로 격상 | docs/SIMULATOR_TRANSCENDENCE_PLAN.md, src/digital_twin/sync_engine.py, tests/track_e/test_digital_twin.py |
| 2026-06-13 22:12 | `50002f2` | feat(transcendence): Phase 286 안전망 Ablation 자동화 | CHANGELOG.md, ROADMAP.md, results/ablation/ablation_report.md, results/ablation/ablation_results.json, scripts/ablation_study.py, simulation/simulator.py … |
| 2026-06-13 11:01 | `5b26e79` | fix(ci): sim-smoke.yml에 hypothesis 추가 + TRANSCENDENCE 205·GENESIS 304·309·ODYSSEY 408 진척 | .github/workflows/sim-smoke.yml, README.md, ROADMAP.md, docs/certification/AIRSPACE_CLASS_MAPPING.md, docs/certification/KC_RADIO_CERTIFICATION.md, docs/certification/PILOT_LICENSE_MAPPING.md … |
| 2026-06-13 10:55 | `b342a9e` | feat(plans): GENESIS 306·381·389 + ODYSSEY 447·486 + 시뮬레이터 tutorial API | README.md, ROADMAP.md, STATUS_REPORT.md, VERSION.md, docs/HEALTH_CHECK.md, docs/INDEX.md … |
| 2026-06-13 10:34 | `74370fd` | feat(plans): GENESIS 301·387 + TRANSCENDENCE 204 + ODYSSEY 448·466 일괄 진척 | README.md, ROADMAP.md, docs/certification/AIR_SAFETY_ACT_MATRIX.md, docs/presentation/DEFENSE_KIT.md, docs/schemas/telemetry.schema.json, tests/e2e/test_simulator_production_core.py … |
| 2026-06-13 10:24 | `5f3a897` | test(e2e): C9 해양 검증 기록 플레이크 강화 — .validation 비어있지 않을 때까지 폴링 | tests/e2e/smoke_maritime.mjs |
| 2026-06-13 10:19 | `ea43f25` | fix(transcendence): Phase 207 maturity 배지 자동 생성·드리프트 해소 | CHANGELOG.md, ROADMAP.md, docs/badges/maturity.svg, scripts/extract_sdacs_api.py, tests/test_maturity_badge.py |
| 2026-06-13 02:12 | `ad001db` | feat(genesis): Phase 302 soraAssess + 388 부채 대장 + ODYSSEY Plan(401-500) + README 현행화·미완료 리스트 | README.md, ROADMAP.md, STATUS_REPORT.md, VERSION.md, docs/HEALTH_CHECK.md, docs/INDEX.md … |
| 2026-06-13 01:55 | `283fd1a` | feat(transcendence): Phase 203 Mock Detector + Phase 206 experimental 네임스페이스 + CI 정합성 게이트 | .github/workflows/sim-smoke.yml, README.md, ROADMAP.md, STATUS_REPORT.md, VERSION.md, docs/HEALTH_CHECK.md … |
| 2026-06-13 01:42 | `8765ba4` | docs(genesis): Phase 301-400 GENESIS Plan 신규 수립 + 로드맵 Track H 편입 | README.md, ROADMAP.md, VERSION.md, docs/INDEX.md, docs/MASTER_PLAN_2026H2.md, docs/SIMULATOR_GENESIS_PLAN.md … |
| 2026-06-13 01:31 | `9f5349c` | docs: 종합 감사 — 407 API 라이브 실측 동기화 + Track G 신설 + 2026 H2 마스터플랜 | README.md, ROADMAP.md, STATUS_REPORT.md, VERSION.md, docs/HEALTH_CHECK.md, docs/INDEX.md … |
| 2026-06-13 01:13 | `c4e0cc6` | feat(simulator): Phase 0 polish — 동적 NFZ overlay + sub-km 거리 표시 | README.md, docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, visualization/swarm_3d_simulator.html |
| 2026-06-12 23:54 | `ec0321a` | Merge branch 'main' of http://127.0.0.1:40031/git/sun475300-sudo/swarm-drone-atc | CHANGELOG.md, ROADMAP.md |
| 2026-06-12 23:53 | `36d2331` | feat(transcendence): Phase 201-207 API Maturity Honesty + README 수치 갱신 + 초대규모 울트라플랜 | README.md, VERSION.md, docs/SIMULATOR_TRANSCENDENCE_PLAN.md, docs/badges/maturity.svg, docs/sdacs.d.ts, docs/simulator.html … |
| 2026-06-12 08:42 | `4e35caa` | Merge branch 'main' of http://127.0.0.1:33971/git/sun475300-sudo/swarm-drone-atc | .github/workflows/sim-smoke.yml, .gitignore, CHANGELOG.md, ROADMAP.md, docs/HITL_CHECKLIST.md, docs/SDACS_API.md … |
| 2026-06-12 08:42 | `c870cf3` | feat: README 배지 v1.5.0 갱신 + Phase Matrix 200 완전 + PROJECT_PITCH 1-pager | README.md, docs/PROJECT_PITCH.md, docs/phase_matrix.html |
| 2026-06-07 15:19 | `38a7b96` | feat: 추가 작업 7종 일괄 — TS .d.ts·Phase Matrix·Quick Start·SVG 배지·VERSION·HEALTH·INDEX | VERSION.md, docs/HEALTH_CHECK.md, docs/INDEX.md, docs/QUICK_START.md, docs/badges/api_388.svg, docs/badges/e2e_247.svg … |
| 2026-06-06 21:38 | `77b6a8b` | docs(readme): 배포 파일 다운로드 섹션 추가 (v1.5.0 — 200 Phase Unity) | README.md |
| 2026-06-06 17:59 | `602537c` | feat: ①②③④⑤ 모두 실행 (sandbox 가능 범위) | docs/paper/SDACS_IROS_2026_sections_4to7.pdf |
| 2026-06-06 06:34 | `0b6ec17` | feat: ①②③④ 모두 시작 — 태그·논문 §Discussion·캡스톤 DOCX·HITL+베타 스캐폴드 | docs/beta/v1_5_PILOT_KICKOFF.md, docs/hardware/pixhawk_sdacs_hitl.md, docs/paper/latex/sections_4to7.tex, docs/report/SDACS_Capstone_Report_v200.docx, scripts/generate_capstone_report.py |
| 2026-06-06 06:26 | `97a79a6` | chore(gitignore): scripts/recordings/ 추가 (Playwright 임시 녹화 출력) | .gitignore |
| 2026-06-06 06:26 | `5902e37` | feat: ① 데모 영상 자동 녹화 + ② Pages 동기화 + ③ v1.5.0 가이드 + ④ Post-200 트랙 | docs/POST_200_DIRECTIONS.md, docs/V1_5_0_RELEASE_INSTRUCTIONS.md, docs/demo/sdacs_200phase_showcase.webm, scripts/record_showcase_demo.py |
| 2026-06-06 01:08 | `6402352` | feat: 200 Phase 통합 showcase + 통합 회귀 + CI 갱신 | .github/workflows/sim-smoke.yml, docs/demo/all_phases_showcase.js, tests/e2e/test_simulator_200phase_integration.py |
| 2026-06-06 00:47 | `05c8200` | docs: Phase 200 완료 마무리 — SDACS_API 388 항목 + CHANGELOG + STATUS_REPORT | CHANGELOG.md, STATUS_REPORT.md, docs/SDACS_API.md |
| 2026-06-05 23:46 | `eed47c9` | feat(simulator): POST-UNIVERSE Phase 151-200 일괄 — Phase 200 = SDACS = 𝟏 (Unity) 도달 | docs/SIMULATOR_POST_UNIVERSE_PLAN.md, docs/simulator.html, docs/swarm_3d_simulator.html, package.json, swarm_3d_simulator.html, tests/e2e/test_simulator_post_universe.py … |
| 2026-06-05 23:33 | `33be50b` | chore: package v1.3.0 → v1.4.0 + README 150 Phase + Universe OS 마일스톤 명시 | README.md, package.json |
| 2026-06-05 23:32 | `117eab3` | feat(simulator): ULTIMATE Phase 111-150 일괄 — 150 Phase 전부 완료 (Phase 150 = Universe OS) | docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, tests/e2e/test_simulator_ultimate111_150.py, visualization/swarm_3d_simulator.html |
| 2026-06-05 23:28 | `a52c306` | feat(simulator): ULTIMATE Phase 101-110 (Performance Beyond) + ULTIMATE Plan 작성 | docs/SIMULATOR_ULTIMATE_PLAN.md, docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, tests/e2e/test_simulator_ultimate101_110.py, visualization/swarm_3d_simulator.html |
| 2026-06-05 17:55 | `8921e1d` | chore: package v1.2.0 → v1.3.0 — STELLAR Phase 52-100 통합 (100 Phase 완료) | package.json |
| 2026-06-05 17:54 | `4c0dcd6` | feat(simulator): STELLAR Phase 52-100 일괄 49개 — 100 Phase 전부 완료 | README.md, docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, tests/e2e/test_simulator_stellar.py, visualization/swarm_3d_simulator.html |
| 2026-06-05 15:24 | `cf25c25` | feat: 통합 마감 사이클 — ROADMAP·v1.2 노트·STELLAR 플랜·데모 mission·STELLAR Phase 51 시드 | ROADMAP.md, docs/INDEX.md, docs/RELEASE_NOTES_v1.2.0.md, docs/SIMULATOR_STELLAR_PLAN.md, docs/demo/sample_search_rescue.sdacs-mission, docs/simulator.html … |
| 2026-06-05 15:12 | `781cd25` | docs: 50 Phase 완료 후속 작업 — API 재생성·CHANGELOG·v1.2 빌드·논문 표 | CHANGELOG.md, docs/SDACS_API.md, docs/paper/SDACS_50_Phases_Results.tex, package.json |
| 2026-06-05 14:38 | `c2ceda1` | feat(simulator): HYPER Phase 32-50 일괄 19개 완료 — MEGA 9 + HYPER 41 = 50 Phase 통합 | README.md, STATUS_REPORT.md, docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, tests/e2e/test_simulator_phase32_50.py … |
| 2026-06-05 14:13 | `db2c4e4` | feat(simulator): HYPER Phase 18+26+29+30+31 일괄 — AR·Acoustic·Forecast·UTM Fed·PQC | README.md, docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, tests/e2e/test_simulator_ar_acoustic_etc.py, visualization/swarm_3d_simulator.html |
| 2026-06-05 13:51 | `84641b5` | feat(simulator): HYPER Phase 13+16+22+24+25 일괄 — WebGPU·CRDT·Digital Twin·NOTAM·Battery Aging | README.md, docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, tests/e2e/test_simulator_5phases.py, visualization/swarm_3d_simulator.html |
| 2026-06-05 13:29 | `6af3107` | feat(simulator): HYPER Phase 27 Counter-UAS + Phase 23 Wind Field Grid | README.md, docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, tests/e2e/test_simulator_cuas_wind.py, visualization/swarm_3d_simulator.html |
| 2026-06-05 13:12 | `37ea702` | feat(simulator): HYPER Phase 21 적대 드론 정책 + Phase 28 Swarm Choreography | README.md, docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, tests/e2e/test_simulator_adversarial_choreo.py, visualization/swarm_3d_simulator.html |
| 2026-06-05 12:54 | `487abd1` | feat(simulator): HYPER Phase 17 WebXR + Phase 19 Mission Recorder 공유 | docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, tests/e2e/test_simulator_xr_mission.py, visualization/swarm_3d_simulator.html |
| 2026-06-05 12:40 | `4b7df4d` | chore(gitignore): electron-builder 빌드 부산물 루트 main.js/preload.js 차단 | .gitignore |
| 2026-06-05 12:38 | `c3fca2f` | feat(simulator): HYPER Phase 20 — AI Copilot 자연어 → ATC 명령 분해 | README.md, docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, tests/e2e/test_simulator_copilot.py, visualization/swarm_3d_simulator.html |
| 2026-06-05 12:33 | `7c3de01` | feat(desktop): HYPER Phase 12 — Electron 멀티 윈도우 + IPC 시간축 동기 + ATC 브로드캐스트 | README.md, desktop/main.js, desktop/preload.js, docs/maritime_detection_simulator.html, docs/simulator.html, docs/swarm_3d_simulator.html … |
| 2026-06-05 10:05 | `d16b6f2` | feat(simulator): HYPER Phase 14 시나리오 갤러리 + Phase 15 KO/EN/JA/ZH 4언어 | README.md, docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, tests/e2e/test_simulator_gallery_i18n.py, visualization/swarm_3d_simulator.html |
| 2026-06-05 09:46 | `d26d4d5` | feat(maritime): HYPER Phase 11 — 해양 ATC 명령 콘솔 동등 이식 | README.md, docs/maritime_detection_simulator.html, maritime_detection_simulator.html, tests/e2e/test_maritime_atc.py, visualization/maritime_detection_simulator.html |
| 2026-06-05 09:41 | `4ea7956` | docs: HYPER 플랜 Phase 10-50 + SDACS_API 92항목 자동문서 + RELEASE_GUIDE + 사본 동기화 | README.md, docs/RELEASE_GUIDE.md, docs/SDACS_API.md, docs/SIMULATOR_HYPER_PLAN.md, visualization/maritime_detection_simulator.html |
| 2026-06-05 09:19 | `a77c3f3` | feat(self-feedback): 데스크탑 v1.1 빌드 + 해양 PWA + CI 3-job 강화 | .github/workflows/sim-smoke.yml, README.md, desktop/home.html, docs/manifest.webmanifest, docs/maritime_detection_simulator.html, docs/sdacs-sw.js … |
| 2026-06-04 21:47 | `3db57ec` | feat(simulator): Phase 5 MIS + Phase 7 ANA + Phase 9 MOB — MEGA 플랜 9 Phase 전부 완료 | README.md, STATUS_REPORT.md, docs/manifest.webmanifest, docs/sdacs-sw.js, docs/simulator.html, docs/swarm_3d_simulator.html … |
| 2026-06-04 20:13 | `6192d6d` | feat(simulator): Phase 4 CAM 카메라 모드 + Phase 8 AUD 환경 사운드 | README.md, STATUS_REPORT.md, docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, tests/e2e/test_simulator_cam_aud.py … |
| 2026-06-04 20:03 | `9b8fe22` | feat(simulator): Phase 3 CIN 시네마틱 + Phase 6 INJ 장애 주입 일괄 구현 | README.md, STATUS_REPORT.md, docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, tests/e2e/test_simulator_cin_inj.py … |
| 2026-06-04 19:41 | `547a5d1` | feat(simulator): Phase 2 TAC 전술 시각화 + MEGA 마스터 플랜 | README.md, STATUS_REPORT.md, docs/SIMULATOR_MEGA_PLAN.md, docs/SIMULATOR_PHASE_PLANS.md, docs/simulator.html, docs/swarm_3d_simulator.html … |
| 2026-06-04 19:17 | `eecfd81` | feat(simulator): Phase 1 ATC 관제사 명령 콘솔 + 한국어 TTS + Web Audio 경보 | README.md, STATUS_REPORT.md, docs/SIMULATOR_ULTRA_PLAN.md, docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html … |
| 2026-06-04 18:40 | `002336b` | ci(desktop): tag push에서 항상 공개 Release 발행 + paths 필터 분리 | .github/workflows/desktop-build.yml |
| 2026-06-04 18:33 | `6ff357e` | docs: 본 세션 PR 15개 main 머지 완료 반영 — ROADMAP·README·ULTRA_PLAN·STATUS_REPORT 일괄 갱신 | README.md, ROADMAP.md, STATUS_REPORT.md, docs/ULTRA_PLAN.md |
| 2026-06-04 18:19 | `b9103ec` | Merge remote-tracking branch 'origin/main' into feat/roadmap-p730-p733 | README.md, ROADMAP.md, docs/ULTRA_PLAN.md, docs/maritime_eoir_adapter.md, docs/paper/contribution_outline.md, docs/poster/README.md … |
| 2026-06-04 18:19 | `bd25cac` | Merge remote-tracking branch 'origin/main' into feat/p735-eoir-adapter | README.md, ROADMAP.md, docs/ULTRA_PLAN.md, docs/paper/contribution_outline.md, docs/poster/README.md, docs/poster/donggang_2026_ko.md … |
| 2026-06-04 18:18 | `61b8b22` | Merge remote-tracking branch 'origin/main' into feat/p734-multiview-sync | README.md, ROADMAP.md, docs/ULTRA_PLAN.md, docs/paper/contribution_outline.md, docs/poster/README.md, docs/poster/donggang_2026_ko.md … |
| 2026-06-04 18:17 | `fc582c0` | fix: swarm_3d HTML conflict 해소 — replay API + conflictPairs union | swarm_3d_simulator.html |
| 2026-06-04 18:16 | `25b0396` | Merge remote-tracking branch 'origin/main' into feat/p734-replay-scrubber | README.md, ROADMAP.md, docs/ULTRA_PLAN.md, docs/paper/contribution_outline.md, docs/poster/README.md, docs/poster/donggang_2026_ko.md … |
| 2026-06-04 18:16 | `637e515` | fix: ROADMAP conflict 마커 잔존 정리 (base 채택) | ROADMAP.md |
| 2026-06-04 18:15 | `bbd98eb` | Merge remote-tracking branch 'origin/main' into feat/p732-cpa-spatial-hash | README.md, ROADMAP.md, docs/ULTRA_PLAN.md, docs/paper/contribution_outline.md, docs/poster/README.md, docs/poster/donggang_2026_ko.md … |
| 2026-06-04 18:15 | `09a5da6` | Merge remote-tracking branch 'origin/main' into feat/p731-layer-panel-merge | README.md, docs/ULTRA_PLAN.md, docs/paper/contribution_outline.md, docs/poster/README.md, docs/poster/donggang_2026_ko.md, docs/slides/README.md … |
| 2026-06-04 18:14 | `e8a347c` | Merge remote-tracking branch 'origin/main' into docs/p701-p710-ultraplan | README.md, src/closed_net/airgap_mode.py |
| 2026-06-04 16:12 | `f1d0378` | Merge remote-tracking branch 'origin/main' into feat/p735-eoir-adapter | .github/workflows/airgap-audit.yml, CONTRIBUTING.md, README.md, ROADMAP.md, STATUS_REPORT.md, benchmarks/baselines/sdacs/adapter.py … |
| 2026-06-04 16:13 | `899d6d2` | Merge remote-tracking branch 'origin/main' into feat/roadmap-p730-p733 | .github/workflows/airgap-audit.yml, CONTRIBUTING.md, README.md, ROADMAP.md, STATUS_REPORT.md, benchmarks/baselines/sdacs/adapter.py … |
| 2026-06-04 16:11 | `da9096b` | fix(P744): airgap 감사가 운영 API 엔드포인트 오탐 — blocklist만 검사 | src/closed_net/airgap_mode.py |
| 2026-06-04 16:04 | `f8e6fd8` | Merge remote-tracking branch 'origin/main' into docs/p701-p710-ultraplan | .github/workflows/airgap-audit.yml, CONTRIBUTING.md, README.md, ROADMAP.md, STATUS_REPORT.md, benchmarks/baselines/sdacs/adapter.py … |
| 2026-06-04 16:06 | `744f305` | Merge remote-tracking branch 'origin/main' into feat/p731-layer-panel-merge | .github/workflows/airgap-audit.yml, CONTRIBUTING.md, README.md, ROADMAP.md, STATUS_REPORT.md, benchmarks/baselines/sdacs/adapter.py … |
| 2026-06-04 16:07 | `b55b421` | Merge remote-tracking branch 'origin/main' into feat/p732-cpa-spatial-hash | .github/workflows/airgap-audit.yml, CONTRIBUTING.md, README.md, ROADMAP.md, STATUS_REPORT.md, benchmarks/baselines/sdacs/adapter.py … |
| 2026-06-04 16:08 | `f7a29d1` | Merge remote-tracking branch 'origin/main' into feat/p734-replay-scrubber | .github/workflows/airgap-audit.yml, CONTRIBUTING.md, README.md, ROADMAP.md, STATUS_REPORT.md, benchmarks/baselines/sdacs/adapter.py … |
| 2026-06-04 16:08 | `2cae80c` | Merge remote-tracking branch 'origin/main' into feat/p734-multiview-sync | .github/workflows/airgap-audit.yml, CONTRIBUTING.md, README.md, ROADMAP.md, STATUS_REPORT.md, benchmarks/baselines/sdacs/adapter.py … |
| 2026-06-04 16:03 | `1d5bcaa` | Merge remote-tracking branch 'origin/main' into feat/track-e-test-coverage | .github/workflows/airgap-audit.yml, CONTRIBUTING.md, README.md, ROADMAP.md, STATUS_REPORT.md, benchmarks/baselines/sdacs/adapter.py … |
| 2026-06-04 16:01 | `337d835` | Merge remote-tracking branch 'origin/main' into feat/contributing-index-extras | .github/workflows/airgap-audit.yml, README.md, ROADMAP.md, STATUS_REPORT.md, benchmarks/baselines/sdacs/adapter.py, config/scenario_params/uam/k_uam_grand_challenge.yaml … |
| 2026-06-04 16:00 | `4b1c4e7` | Merge remote-tracking branch 'origin/main' into feat/paper-slides-eval | .github/workflows/airgap-audit.yml, README.md, ROADMAP.md, STATUS_REPORT.md, benchmarks/baselines/sdacs/adapter.py, config/scenario_params/uam/k_uam_grand_challenge.yaml … |
| 2026-06-04 15:59 | `d278477` | Merge remote-tracking branch 'origin/main' into feat/final-polish | README.md, ROADMAP.md, benchmarks/baselines/sdacs/adapter.py, config/scenario_params/uam/k_uam_grand_challenge.yaml, docs/beta/README.md, docs/hardware/README.md … |
| 2026-06-04 15:58 | `55193ee` | Merge remote-tracking branch 'origin/main' into feat/track-e-finale | README.md, ROADMAP.md, benchmarks/baselines/sdacs/adapter.py, docs/beta/README.md, docs/hardware/README.md, docs/hardware/environmental_test.md … |
| 2026-06-04 15:47 | `cf27396` | Merge remote-tracking branch 'origin/main' into feat/track-b-paper-master | README.md, benchmarks/baselines/sdacs/adapter.py, results/comparison/01_corridor_crossing/cbs/seed42.json, results/comparison/01_corridor_crossing/cbs/seed43.json, results/comparison/01_corridor_crossing/cbs/seed44.json, results/comparison/01_corridor_crossing/cbs/seed45.json … |
| 2026-06-04 15:19 | `9d9baa9` | fix: SDACS adapter LAANC 지연 분포 [80,150] → [80,120] (테스트 정합) | benchmarks/baselines/sdacs/adapter.py |
| 2026-06-04 15:07 | `d66dcc4` | fix: main 병합 충돌 마커 해소 — a576460 botched merge 복구 | README.md, ROADMAP.md, api/auth.py, api/fastapi_server.py, benchmarks/baselines/sdacs/adapter.py, results/comparison/COMPARISON_REPORT.md … |
| 2026-06-04 11:09 | `32e00be` | feat: 울트라플랜 대규모 실행 — Track A 실기·B 후반·C 베타·E PoC·F 산학 일괄 | ROADMAP.md, docs/beta/README.md, docs/hardware/README.md, docs/hardware/environmental_test.md, docs/hardware/failsafe_logic.md, docs/hardware/fmea_report.md … |
| 2026-06-04 12:28 | `4fb5b86` | fix(P743): mypy dict-item — overhead_pct float ↔ int 충돌 해결 | src/quantum/pqc_telemetry.py |
| 2026-06-04 12:17 | `d2f8a22` | feat: 울트라플랜 SP4-5 일괄 — P740/742/743/744/750/751/754 + Track E/F 확장 | ROADMAP.md, config/scenario_params/uam/k_uam_grand_challenge.yaml, docs/track_e/p743_pqc_overhead.md, docs/track_f/p754_mentoring.md, src/applications/__init__.py, src/applications/agri_spray.py … |
| 2026-06-04 13:02 | `996d322` | feat: 울트라플랜 최종 마무리 — STATUS_REPORT + 차트·CI·CHANGELOG | .github/workflows/airgap-audit.yml, ROADMAP.md, STATUS_REPORT.md, docs/CHANGELOG.md, docs/poster/assets/pareto_front.png, docs/poster/assets/results_nmr_msd_bar.png … |
| 2026-06-04 13:51 | `7376e33` | feat: P707 §4-§7 LaTeX + P710 Marp 슬라이드 + P742 평가기 + README 진척 | README.md, ROADMAP.md, docs/paper/latex/sections_4to7.tex, docs/slides/donggang_2026_ko.md, scripts/uam_evaluator.py, tests/track_e/test_uam_evaluator.py |
| 2026-06-04 14:18 | `d21ad22` | feat: docs INDEX + UAM 시나리오 2종 + 알고리즘 비교 + CONTRIBUTING/PR 정리 | CONTRIBUTING.md, config/scenario_params/uam/evtol_emergency.yaml, config/scenario_params/uam/urban_dense.yaml, docs/INDEX.md, docs/PR_CLEANUP.md, scripts/compare_baselines_ext.py |
| 2026-06-04 14:51 | `ec6f9fe` | docs: README 최신화 — Phase 755 배지 + 7트랙 진척 현황 표 | README.md |
| 2026-06-04 14:48 | `0382904` | ci: re-trigger (flaky adapter encoding + audit.sh mode, PR #93 same main success) | - |
| 2026-06-04 14:38 | `2081602` | docs: 종합 점검 보고서 (HEALTH_CHECK) — 소스·시뮬레이터·배포 위치 | docs/HEALTH_CHECK.md |
| 2026-06-04 08:22 | `0ad4e1e` | docs: SDACS Ultra Plan + P701 논문 outline + P710 포스터/슬라이드 스켈레톤 | ROADMAP.md, docs/ULTRA_PLAN.md, docs/paper/contribution_outline.md, docs/poster/README.md, docs/poster/donggang_2026_ko.md, docs/slides/README.md |
| 2026-06-03 23:19 | `3e020ee` | feat(P731): 공역 레이어 패널 중복 통합 — layer-* 제거, tg-* 단일 소스화 | ROADMAP.md, swarm_3d_simulator.html |
| 2026-06-04 06:22 | `972a3d3` | feat(P732): 대규모 CPA 충돌예측 공간 해시 복원 (B2) | ROADMAP.md, swarm_3d_simulator.html |
| 2026-06-04 06:29 | `7138f1c` | ci: re-trigger smoke (flaky maritime C9, main pass + PR #88 pass) | - |
| 2026-06-04 06:25 | `87ebe64` | feat(P734): 리플레이 타임라인 키보드 스크러버 + 외부 API | ROADMAP.md, swarm_3d_simulator.html |
| 2026-06-04 09:44 | `cf64eec` | feat(P734): 멀티뷰 동기화 — 분석뷰 차트에 시간축 cursor | ROADMAP.md, swarm_3d_simulator.html |
| 2026-06-04 10:07 | `6620d54` | feat(P735): 해양 EO/IR 어댑터 패턴 — 외부 SDK hook + synth fallback | ROADMAP.md, docs/maritime_eoir_adapter.md, maritime_detection_simulator.html |
| 2026-06-03 22:07 | `34ab0c3` | test: ws_bridge fake mock을 새 SwarmSimulator 인터페이스에 맞춤 | tests/test_ws_bridge.py |
| 2026-06-03 21:57 | `c072d6c` | feat: P733 ws_bridge LIVE 모드 + ws_bridge 인터페이스 정합성 수정 | simulation/ws_bridge.py, swarm_3d_simulator.html |
| 2026-06-03 21:50 | `1e80c65` | feat: ROADMAP 진행 현황 표 + Track E/F 신설 + P730 UI i18n(KO/EN) | ROADMAP.md, swarm_3d_simulator.html |
| 2026-06-03 19:39 | `426b9e7` | ci: desktop-build setup-node 캐시 비활성화 (lock 파일 부재로 실패) | .github/workflows/desktop-build.yml |
| 2026-06-03 13:12 | `3295124` | feat: 병렬 세션의 고유 작업 통합 (Track A SW + P706 결과 + 벤치마크 schema) | benchmarks/_schema/manifest.schema.json, results/p706_comparison_3sc_5seed.csv, results/p706_summary.json, scripts/compare_baselines.py, simulation/environmental_scenario.py, simulation/failsafe_manager.py … |
| 2026-06-03 12:39 | `cd82157` | Merge remote-tracking branch 'origin/claude/dazzling-maxwell-5AnBo' | .github/workflows/security.yml, README.md, ROADMAP.md, db/migrations/001_initial_schema.sql, helm/sdacs/.helmignore, helm/sdacs/Chart.yaml … |
| 2026-06-03 12:32 | `b8bb893` | feat: SDACS Electron 데스크탑 앱 — .bat 런처 폐기 + 3-OS 자동 빌드 | .github/workflows/desktop-build.yml, .gitignore, README.md, ROADMAP.md, desktop/home.html, desktop/main.js … |
| 2026-06-03 12:13 | `d510a1c` | fix: OCaml type_safe_protocol에 'type message' 정의 추가 (CI 3.10/3.11/3.12 그린화) | src/ocaml/type_safe_protocol.ml |
| 2026-06-03 12:01 | `73d48f8` | feat: P730(B5) 해양 시뮬레이터 UI 국제화(KO/EN 토글) | docs/maritime_detection_simulator.html, maritime_detection_simulator.html, tests/e2e/smoke_maritime.mjs |
| 2026-06-03 11:57 | `2f43895` | feat: P729(B3) 대규모 모드 글로우 인스턴싱 + ROADMAP Track D 신설 | ROADMAP.md, docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, visualization/swarm_3d_simulator.html |
| 2026-06-03 11:51 | `b113fbe` | Merge remote-tracking branch 'origin/main' into claude/ruview-wifi-analysis-2YG4p | README.md, ROADMAP.md, api/auth.py, api/fastapi_server.py, benchmarks/baselines/sdacs/adapter.py, main.py … |
| 2026-06-03 11:44 | `4173b45` | docs: D2 해양 시뮬레이터 기술 문서 + README 링크 | README.md, docs/maritime_detection_technical.md |
| 2026-06-03 11:42 | `4a7ec26` | feat: B4 드론 다중 선택(Shift+클릭) + 집계 패널 | docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, tests/e2e/smoke_sim.mjs, visualization/swarm_3d_simulator.html |
| 2026-06-03 11:36 | `c9493a2` | feat: 두 시뮬레이터 상호 네비게이션 링크(군집↔해양) | docs/maritime_detection_simulator.html, docs/simulator.html, docs/swarm_3d_simulator.html, maritime_detection_simulator.html, swarm_3d_simulator.html, visualization/swarm_3d_simulator.html |
| 2026-06-03 11:34 | `74d002a` | feat: C9 해양 시나리오별 검증 기록 + CSV 내보내기 | docs/maritime_detection_simulator.html, maritime_detection_simulator.html, tests/e2e/smoke_maritime.mjs |
| 2026-06-03 11:30 | `abc3915` | perf: O2→B10 CPA 라벨 스프라이트 풀 재사용 (GC 압력 해소) | docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, tests/e2e/TEST_LOG.md, visualization/swarm_3d_simulator.html |
| 2026-06-03 11:28 | `00a94ca` | feat: B6 대규모 성능 측정 — draw call·FPS·삼각형 HUD + _sdacs.perf API | docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, tests/e2e/smoke_sim.mjs, visualization/swarm_3d_simulator.html |
| 2026-06-03 11:24 | `a638221` | feat: 해양 EO/IR 카메라 뷰(C3) + 해안선·항로·선박 3D 디테일(C7) | docs/maritime_detection_simulator.html, maritime_detection_simulator.html, tests/e2e/smoke_maritime.mjs |
| 2026-06-03 11:02 | `93cafb2` | feat: 해양 시뮬레이터 PNG/CSV 리포트(C6) + README 해양 섹션(D2) | README.md, docs/maritime_detection_simulator.html, maritime_detection_simulator.html, tests/e2e/smoke_maritime.mjs |
| 2026-06-03 10:59 | `9540f48` | feat: 해양 시나리오 3종(C8) + 스왐 경로효율 per-leg 수정(O3→B9) | docs/simulator.html, docs/swarm_3d_simulator.html, maritime_detection_simulator.html, swarm_3d_simulator.html, tests/e2e/TEST_LOG.md, visualization/swarm_3d_simulator.html |
| 2026-06-03 10:56 | `88e76b4` | feat: 해양 시뮬레이터 실용성 강화 — C1 레이더 물리 + C2 AIS·레이더 융합 + C4 COLREG + C5 트랙 상세 | docs/maritime_detection_simulator.html, maritime_detection_simulator.html, tests/e2e/smoke_maritime.mjs |
| 2026-05-29 20:34 | `a2bbc54` | fix: numpy 배열 선언에 shape-무관 타입주석 (Python 3.10 mypy 그린화) | src/boids_swarm.py, src/sensor_fusion.py |
| 2026-05-29 20:09 | `e4172d3` | fix: test_ws_bridge가 Python 3.10에서 깨지던 asyncio 루프 패턴 교체 | tests/test_ws_bridge.py |
| 2026-05-29 19:38 | `01495f7` | fix: BatteryPredictor.should_rtl가 numpy bool 대신 파이썬 bool 반환 | simulation/battery_predictor.py |
| 2026-05-29 19:29 | `3c63e82` | fix: 누락 폴리글랏 레퍼런스 파일 전체 복원 (118개 추가, 총 147) | src/ada/safety_critical.adb, src/asm/crc32_checksum.asm, src/clojure/event_stream.clj, src/cpp/apf_simd.cpp, src/cpp/formation_gan_engine.cpp, src/cpp/hil_physics.cpp … |
| 2026-05-29 19:08 | `fafe3cb` | fix: 누락된 폴리글랏 참조 파일 29개 복원 (CI test 잡 그린화) | src/ada/tmr_voter_v2.adb, src/assembly/kalman_filter.asm, src/clojure/event_sourcing_v2.clj, src/cobol/legacy_atc_bridge.cob, src/cpp/particle_filter.cpp, src/dart/flutter_dashboard.dart … |
| 2026-05-29 18:35 | `e6e75ca` | test: 해양 시뮬레이터 헤드리스 스모크 + CI 등록 + 랜딩 카드 | .github/workflows/sim-smoke.yml, docs/index.html, tests/e2e/smoke_maritime.mjs |
| 2026-05-29 10:20 | `8ed7fc3` | feat: 해양 소형선 감지·식별 전용 시뮬레이터 (maritime_detection_simulator.html) | .github/workflows/deploy-pages.yml, README.md, docs/maritime_detection_simulator.html, maritime_detection_simulator.html |
| 2026-05-29 10:14 | `208974a` | docs: 스모크 테스트 로그 + 버그 리스트(TEST_LOG.md) + 미해결 항목 코드 주석 | docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, tests/e2e/TEST_LOG.md, visualization/swarm_3d_simulator.html |
| 2026-05-29 09:27 | `e57192d` | feat: 각 드론 세부 쿼드콥터 모델링 (본체 허브+4암+4링+회전 프롭) | docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, visualization/swarm_3d_simulator.html |
| 2026-05-29 09:23 | `3a59a91` | chore: package.json 추적(강제) — 로컬 npm 실행 스크립트 활성화 | package.json |
| 2026-05-29 09:23 | `a831ba3` | feat: 로컬 실행/빌드 지원 — serve.py 런처 + npm 스크립트 + 오프라인 벤더링 | README.md, scripts/serve.py, scripts/vendor_three.sh |
| 2026-05-29 09:21 | `bb9c50f` | feat: 외부 드론·조류 인식 가시화 + 탐지 스로틀 시간기반 안정화 | docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, visualization/swarm_3d_simulator.html |
| 2026-06-03 11:55 | `0fd32dd` | fix: numpy 2.4.x mypy assignment 오류 type: ignore 추가 | src/boids_swarm.py, src/sensor_fusion.py |
| 2026-06-03 11:42 | `bea5a20` | fix: OCaml type message 추가 + ws_bridge 이벤트루프 수정 | src/ocaml/type_safe_protocol.ml, tests/test_ws_bridge.py |
| 2026-06-03 11:31 | `d3b5837` | fix: ruff I001 import 정렬 수정 (src/monitoring/metrics.py) | src/monitoring/metrics.py |
| 2026-06-02 09:18 | `d84bb85` | docs: update README with Phase 521-660 multi-language coverage and latest stats | README.md |
| 2026-06-02 10:20 | `main` | docs: README 최신 내용으로 업데이트 (Phase 521-660 다중 언어 반영, 배지/통계 갱신) | README.md |
| 2026-06-02 09:17 | `c5b2111` | feat: add 68 multi-language stub files and fix BatteryPredictor numpy bool | simulation/battery_predictor.py, src/ada/safety_critical.adb, src/ada/tmr_voter_v2.adb, src/asm/crc32_checksum.asm, src/assembly/kalman_filter.asm, src/clojure/event_sourcing_v2.clj … |
| 2026-06-02 08:38 | `687ff34` | fix: typing-extensions 4.12.2→4.15.0 (pydantic 2.13.4 호환성) | requirements.lock.txt |
| 2026-06-02 08:36 | `55169dd` | fix: requirements.lock.txt에 fastapi 스택 추가 (CI test_auth_p712 ERROR 수정) | requirements.lock.txt |
| 2026-06-02 08:34 | `a1c5006` | fix: fastapi를 requirements.txt에 추가 + test_auth_p712 import guard (CI fix) | requirements.txt, tests/test_auth_p712.py |
| 2026-06-02 08:26 | `785d450` | chore: 500드론 부하 테스트 결과 추가 (P717 참고용) | results/load_test_500drones.json |
| 2026-06-02 08:25 | `4861860` | feat: P706 W2 SDACS 어댑터 + P712 OAuth2/RBAC + P717 부하 테스트 | ROADMAP.md, api/auth.py, api/fastapi_server.py, benchmarks/baselines/sdacs/adapter.py, results/comparison/COMPARISON_REPORT.md, results/comparison/comparison_report.json … |
| 2026-05-29 08:55 | `21df76e` | Merge remote-tracking branch 'origin/main' into claude/ruview-wifi-analysis-2YG4p | - |
| 2026-05-29 08:55 | `e86c4ae` | docs: README에 라이브 사이트(랜딩) 링크 추가 + 시뮬레이터 기능 갱신 | README.md |
| 2026-05-29 08:44 | `a5277c3` | feat: DnI 식별 정확도 모델 — 클래스별 정확도 + 오분류 | docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, visualization/swarm_3d_simulator.html |
| 2026-05-29 07:58 | `2e50ab6` | Merge remote-tracking branch 'origin/main' into claude/ruview-wifi-analysis-2YG4p | api/fastapi_server.py, benchmarks/baselines/cbs/adapter.py, benchmarks/baselines/orca/adapter.py, benchmarks/baselines/sdacs/adapter.py, benchmarks/baselines/vo/adapter.py, chatbot/engine/llm_engine.py … |
| 2026-05-29 07:54 | `afa66c2` | fix: code-reviewer 지적 반영 (HIGH 4 + MEDIUM/LOW) | docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, visualization/swarm_3d_simulator.html |
| 2026-05-29 07:42 | `a0eefaf` | fix: 미정의 resetConflictViz 로드 크래시 수정 + 충돌위험 히트맵 (Bundle 9) | docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, visualization/swarm_3d_simulator.html |
| 2026-05-29 07:36 | `44de98a` | fix: docs/index.html 데모 CTA를 v2 → 메인 시뮬레이터(simulator.html)로 교체 | docs/index.html |
| 2026-05-28 21:03 | `5af1f16` | feat: 외부 탐지·식별(조류·비협조 드론) + ATC 통제드론 쿼드콥터 비주얼 | docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, tests/e2e/smoke_sim.mjs, visualization/swarm_3d_simulator.html |
| 2026-05-28 20:54 | `df7cce2` | docs: simulation/drone_agent.py 핵심 함수 docstring 보강 (Bundle 6 / 부채) | simulation/drone_agent.py |
| 2026-05-28 20:52 | `83ff46e` | feat: 단축키 + 도움말 오버레이 + 패널상태 저장 (Bundle 5 / F) | docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, visualization/swarm_3d_simulator.html |
| 2026-05-28 20:50 | `b774a77` | feat: 분리간격 위반 경보 + 단계별 조치 아이콘 (Bundle 4 / A) | docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, visualization/swarm_3d_simulator.html |
| 2026-05-28 20:47 | `38014bc` | feat: 대규모 프러스텀 컬링·LOD + 성능 HUD (Bundle 3) | docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, visualization/swarm_3d_simulator.html |
| 2026-05-28 20:45 | `fb75f43` | feat: 세션 리포트 HTML/MD 내보내기 (Bundle 2) | docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, visualization/swarm_3d_simulator.html |
| 2026-05-28 20:42 | `160f9fb` | feat: 뷰 프리셋·추적캠 + 드론 검색/필터 (Bundle 1) | docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, visualization/swarm_3d_simulator.html |
| 2026-05-28 20:15 | `312bcb7` | Merge remote-tracking branch 'origin/main' into claude/ruview-wifi-analysis-2YG4p | .claude/update-changelog.py, CLAUDE.md, README.md, api/fastapi_server.py, archive/polyglot/ada/safety_critical.adb, archive/polyglot/ada/tmr_voter_v2.adb … |
| 2026-05-28 20:06 | `558145b` | feat: 대규모 GPU 군집 InstancedMesh (Phase 2) — 1k~10k 단일 드로우콜 | docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, tests/e2e/smoke_sim.mjs, visualization/swarm_3d_simulator.html |
| 2026-05-28 19:40 | `0523742` | test: 시뮬레이터 헤드리스 스모크 + CI (Phase 5) + README 기능 반영 | .github/workflows/sim-smoke.yml, README.md, tests/e2e/smoke_sim.mjs |
| 2026-05-28 19:37 | `c58711d` | feat: 리플레이·타임라인 (Phase 3) — 상태 레코더 + 스크러버 재생 | docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, visualization/swarm_3d_simulator.html |
| 2026-05-28 19:34 | `412ab36` | feat: 리포트·내보내기 (Phase 4) — 4분할 PNG / CSV / KPI 복사 | docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, visualization/swarm_3d_simulator.html |
| 2026-05-28 19:30 | `d5a2ef0` | feat: 상세 패널/툴팁 확장 + Phase 1 잔여(회랑·고도레이어 토글, CPA 라벨, Q2 오버레이) | docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, visualization/swarm_3d_simulator.html |
| 2026-05-28 15:58 | `c3db825` | docs: simulation/simulator.py 주석 샘플 — 핵심 함수/클래스 docstring 보강 | simulation/simulator.py |
| 2026-05-28 15:55 | `4f0fe99` | feat: 충돌·공역 관제 시각화 + 웨이포인트·이동경로 (Phase 1) | docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, visualization/swarm_3d_simulator.html |
| 2026-05-28 15:40 | `71e34fd` | docs: Codex 핸드오프용 SDACS 전체 상세 실행 계획 추가 | docs/CODEX_PLAN.md |
| 2026-05-28 15:36 | `7d7b1a4` | feat: 시뮬레이터 4분할 분석 뷰(2x2 대시보드) 추가 | docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, visualization/swarm_3d_simulator.html |
| 2026-05-28 14:56 | `0611b62` | feat: 드론 라이브 상태 툴팁 + 클릭 상세 패널 추가 및 메인 시뮬레이터 진입점 일원화 | .github/workflows/deploy-pages.yml, README.md, docs/simulator.html, docs/swarm_3d_simulator.html, swarm_3d_simulator.html, visualization/swarm_3d_simulator.html |
| 2026-05-20 13:50 | `593745d` | ci: trigger rerun to verify Python 3.10 stability | - |
| 2026-05-19 08:37 | `3a9ff98` | ci: drop --require-hashes from canonical_hash workflow | .github/workflows/canonical_hash.yml |
| 2026-05-19 08:28 | `b15d590` | fix: sort imports in drone_agent.py to satisfy CI ruff I001 | simulation/drone_agent.py |
| 2026-05-19 08:24 | `aeb710a` | feat: integrate 3 RuView-inspired modules for outdoor swarm context | simulation/csi_attention_fusion.py, simulation/meridian_calibrator.py, simulation/passive_rf_detector.py, tests/test_ruview_integrations.py |
| 2026-05-18 22:19 | `13b987f` | fix: resolve shallow copy bug in NAS and boost test coverage to 87% | simulation/neural_architecture_search.py, tests/analytics/test_metrics.py, tests/test_onboard_bridge.py, tests/test_ws_bridge.py |
| 2026-05-18 21:07 | `05d9e44` | perf: enable full GPU power and parallel test execution | config/monte_carlo.yaml, pyproject.toml, simulation/apf_engine/__init__.py, simulation/apf_engine/apf_gpu.py |
| 2026-04-27 15:58 | `810611f` | Merge remote-tracking branch 'origin/main' into claude/atc-auto-batch-20260425-180304 | .gitignore, README.md, SECURITY.md, benchmarks/CITATION.bib, benchmarks/DATASET_CARD.md, benchmarks/LICENSE … |
| 2026-04-19 10:49 | `46ce01a` | fix: IntegrationTestResult/Outcome alias 추가 (import 호환성) | simulation/integration_test_framework.py |
| 2026-04-19 10:46 | `eb57c87` | merge: 원격 린터 변경과 회귀 복구 병합 | .claude/launch.json, .dockerignore, .github/workflows/ci.yml, .github/workflows/deploy-pages.yml, .gitignore, .pre-commit-config.yaml … |
| 2026-04-19 10:45 | `c18da0c` | fix: restore 커밋(6510cb3) 회귀 7건 복구 + 테스트 44→0 실패 | .github/workflows/ci.yml, CLAUDE.md, simulation/flight_plan_validator.py, simulation/integration_test_framework.py, simulation/multi_agent_coordination.py, simulation/simulator.py … |
| 2026-04-09 18:16 | `54ddcb7` | docs: 전체 작업 백업 문서 생성 (2026-04-02) | docs/WORK_BACKUP_2026-04-02.md |
| 2026-04-06 16:46 | `0c9dcea` | fix: CLAUDE.md 테스트 수 동기화 + CI ops-report 동적 수집 | .github/workflows/ci.yml, CLAUDE.md |
| 2026-04-02 17:28 | `3bddf7c` | docs: README 시나리오 결과 테이블 + CI/CD 파이프라인 사양 추가 | README.md |
| 2026-04-02 12:15 | `a99203a` | docs: README 전체 시스템 정밀 기술 사양 5개 섹션 추가 | README.md |
| 2026-04-02 | `c744c51` | fix: CBS 플래너 타임아웃 추가 + 테스트 실패 2건 수정 | simulation/cbs_planner/cbs.py, simulation/config_schema.py, tests/test_phase16_17.py |
| 2026-04-02 | `bc02fef` | docs: README 전체 시스템 정밀 기술 사양 11개 섹션 추가 | README.md |
| 2026-04-02 | `16fccd8` | merge: fix-test-failures-50 + code-review-8fv1B 브랜치 병합 | 13 files |
| 2026-04-01 22:11 | `886aadf` | fix: DeprecationWarning 68건 → 0건 + pytest 수집 경고 제거 | simulation/autonomous_landing.py, simulation/integration_test_framework.py, tests/test_phase300_310.py |
| 2026-04-01 12:20 | `9c18568` | fix: 대규모 테스트 실패 50건 → 0건 수정 | config/monte_carlo.yaml, simulation/apf_engine/apf.py, simulation/multi_agent_coordination.py, src/airspace_control/agents/drone_profiles.py, src/airspace_control/agents/drone_state.py, tests/test_apf.py … |
| 2026-04-01 08:07 | `bec9f89` | fix: 의존성 버전 동기화 + DeprecationWarning 수정 | pyproject.toml, simulation/waypoint_optimizer.py |
| 2026-03-31 22:04 | `671990e` | fix: 충돌 해결률(CR) 0% 버그 수정 — CONFLICT/NEAR_MISS 이벤트 누락 | simulation/simulator.py |
| 2026-03-31 20:22 | `cee81bc` | fix: 비행 계획 검증기 최소 고도 불일치 수정 (10m→30m) | simulation/flight_plan_validator.py |
| 2026-03-31 19:41 | `824c7f4` | perf: 성능 최적화 4건 — 캐시/해싱/큐/윈도우 개선 | simulation/simulator.py, simulation/spatial_hash.py, src/airspace_control/controller/airspace_controller.py |
| 2026-03-31 19:35 | `be11619` | refactor: 핵심 함수 테스트 17개 추가 + 매직 넘버 상수화 | simulation/simulator.py, tests/test_core_functions.py |
| 2026-03-31 19:31 | `e821fe7` | fix: 잔여 broad exception 3건 → 특정 예외 타입으로 교체 | simulation/decision_tree_atc.py, simulation/event_architecture.py, simulation/regulation_updater.py |
| 2026-03-31 19:28 | `c7cbef3` | test: CBS 플래너 edge case 테스트 11개 추가 (8→19) | tests/test_cbs.py |
| 2026-03-31 19:24 | `edadaff` | ci: CI/CD 통합 및 pytest-timeout 설정 | .github/workflows/ci.yml, .github/workflows/python-app.yml, pyproject.toml, requirements.txt |
| 2026-03-31 19:21 | `fd8c5c1` | deps: pydantic>=2.0 추가 — config_schema.py YAML 검증에 필수 | requirements.txt |
| 2026-03-31 19:20 | `e0703ae` | fix: 테스트 실패 20건 → 0건 수정 + 잔여 코드 품질 개선 | chatbot/app.py, main.py, simulation/batch_simulator.py, simulation/cbs_planner/cbs.py, simulation/simulator.py, simulation/voronoi_airspace/voronoi_partition.py … |
| 2026-03-31 18:33 | `b32e122` | docs: README 대규모 편집 — 품질 개선 및 일관성 확보 | README.md |

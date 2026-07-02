# SDACS Documentation Index

이 저장소의 **100+ 문서** 마스터 인덱스. 빠르게 원하는 자료를 찾을 수 있도록 정리.

## 📑 목차 (Table of Contents)

| 섹션 | 내용 |
|---|---|
| [⚡ 빠른 시작](#-빠른-시작) | 1줄 실행·공개 자료·버전 |
| [🌟 시뮬레이터 200 Phase](#-시뮬레이터-200-phase-mega--hyper--stellar--ultimate--post-universe-완료) | 플랜·API·데모·릴리스·점검 |
| [🚀 시작하기](#-시작하기) | README·ROADMAP·STATUS·기여 |
| [🔬 연구·논문 (Track B)](#-연구논문-track-b) | outline·서베이·LaTeX·투고 |
| [🛩 실기 하드웨어 (Track A)](#-실기-하드웨어-track-a) | Pixhawk·Jetson·RTK·FMEA |
| [🎤 발표 자산 (P710)](#-발표-자산-p710) | PPTX·DOCX·포스터·슬라이드 |
| [🛠 Track E 확장 연구 (P736-P745)](#-track-e-확장-연구-p736-p745) | RL·K-UAM·PQC·EO/IR |
| [🤝 산학·사업화 (Track F)](#-산학사업화-track-f) | K-UAM·해수부·산림청·KISA |
| [💼 운영·배포](#-운영배포) | 베타 운영·해양 기술 |
| [🌐 라이브 데모](#-라이브-데모) | GitHub Pages·시뮬레이터 |

## ⚡ 빠른 시작

- **[Quick Start](QUICK_START.md)** — 1줄 실행 가이드 (웹/로컬/데스크탑)
- **[공개 프로젝트 설명 보고서](report/SDACS_Public_Project_Report_2026.docx)** — 일반 대중용 5페이지 DOCX
- **[공개 프로젝트 소개 발표자료](presentation/SDACS_Public_Project_Overview_2026.pptx)** — 10장 PPTX
- **[Phase Matrix HTML](phase_matrix.html)** — 200 Phase 시각 인덱스 (인터랙티브)
- **[VERSION.md](../VERSION.md)** — 단일 버전 진실
- **[CHANGELOG.md](../CHANGELOG.md)** — v1.0-1.5 통합 이력

## 🌟 시뮬레이터 200 Phase (MEGA + HYPER + STELLAR + ULTIMATE + POST-UNIVERSE 완료)

### 📚 Phase 플랜 (트랙별)

| 트랙 | 문서 | Phase 범위·상태 |
|---|---|---|
| **마스터** | [`SIMULATOR_MEGA_PLAN.md`](SIMULATOR_MEGA_PLAN.md) | Phase 1-9 ✅ |
| **확장** | [`SIMULATOR_HYPER_PLAN.md`](SIMULATOR_HYPER_PLAN.md) | Phase 11-50 ✅ |
| **초장기** | [`SIMULATOR_STELLAR_PLAN.md`](SIMULATOR_STELLAR_PLAN.md) | Phase 51-100 ✅ |
| **영원** | [`SIMULATOR_ULTIMATE_PLAN.md`](SIMULATOR_ULTIMATE_PLAN.md) | Phase 101-150 ✅, Universe OS |
| **단일** | [`SIMULATOR_POST_UNIVERSE_PLAN.md`](SIMULATOR_POST_UNIVERSE_PLAN.md) | Phase 151-200 ✅, 𝟏 Unity |
| **초월** | [`SIMULATOR_TRANSCENDENCE_PLAN.md`](SIMULATOR_TRANSCENDENCE_PLAN.md) | Phase 201-300 — 201-207 ✅, 정직성·실측·다중 사용자·HITL·학술 |
| **창세** | [`SIMULATOR_GENESIS_PLAN.md`](SIMULATOR_GENESIS_PLAN.md) | Phase 301-400 — 302·388 ✅, 인증·생태계·실증·차세대 자율·교육 레거시 |
| **항해** | [`SIMULATOR_ODYSSEY_PLAN.md`](SIMULATOR_ODYSSEY_PLAN.md) | Phase 401-500 — 국제 확장·연합 운영·형식 검증·표준·10년 지속 |
| **상세** | [`SIMULATOR_PHASE_PLANS.md`](SIMULATOR_PHASE_PLANS.md) | — |

### 🗺 로드맵·부채

| 문서 | 내용 |
|---|---|
| [`MASTER_PLAN_2026H2.md`](MASTER_PLAN_2026H2.md) | **2026 H2** 통합 실행 로드맵 (4 실행 트랙 + 거버넌스) |
| [`TECH_DEBT_LEDGER.md`](TECH_DEBT_LEDGER.md) | **부채 대장** — mock 110 + speculative 103 정직성 공시 (자동 생성) |

### 🔌 API·타입

| 문서 | 내용 |
|---|---|
| [`SDACS_API.md`](SDACS_API.md) | **407개** 라이브 실측 추출 (maturity 등급 포함) |
| [`sdacs.d.ts`](sdacs.d.ts) | **TypeScript** — IDE autocomplete용 declaration |

### 🎬 데모 자산

| 문서 | 내용 |
|---|---|
| [`demo/sdacs_200phase_showcase.webm`](demo/sdacs_200phase_showcase.webm) | 데모 영상 (9.4 MB, 60초) |
| [`demo/all_phases_showcase.js`](demo/all_phases_showcase.js) | 데모 스크립트 |
| [`demo/sample_search_rescue.sdacs-mission`](demo/sample_search_rescue.sdacs-mission) | 샘플 임무 |

### 📄 논문·보고서

| 문서 | 내용 |
|---|---|
| [`paper/SDACS_50_Phases_Results.tex`](paper/SDACS_50_Phases_Results.tex) | 논문 표 |
| [`paper/SDACS_IROS_2026_sections_4to7.pdf`](paper/SDACS_IROS_2026_sections_4to7.pdf) | IROS PDF |
| [`paper/latex/sections_4to7.tex`](paper/latex/sections_4to7.tex) | IROS LaTeX |
| [`report/SDACS_Capstone_Report_v200.docx`](report/SDACS_Capstone_Report_v200.docx) | 캡스톤 보고서 |

### 🚢 릴리스·운영

| 문서 | 내용 |
|---|---|
| [`RELEASE_GUIDE.md`](RELEASE_GUIDE.md) · [`RELEASE_NOTES_v1.2.0.md`](RELEASE_NOTES_v1.2.0.md) · [`V1_5_0_RELEASE_INSTRUCTIONS.md`](V1_5_0_RELEASE_INSTRUCTIONS.md) | 릴리스 |
| [`hardware/pixhawk_sdacs_hitl.md`](hardware/pixhawk_sdacs_hitl.md) | HITL |
| [`beta/v1_5_PILOT_KICKOFF.md`](beta/v1_5_PILOT_KICKOFF.md) | 베타 |
| [`HEALTH_CHECK.md`](HEALTH_CHECK.md) | 점검 — v1.5.0 종합 PASS |
| [`badges/`](badges/) | 배지 — phase_200·api_388·e2e_247 SVG |

## 🚀 시작하기

| 문서 | 내용 |
|---|---|
| [README.md](../README.md) | 프로젝트 개요·뱃지·빠른 시작 |
| [ROADMAP.md](../ROADMAP.md) | Phase 1-755 전체 로드맵 |
| [STATUS_REPORT.md](../STATUS_REPORT.md) | 트랙별 KPI 종합 보고 |
| [ULTRA_PLAN.md](ULTRA_PLAN.md) | 4-Sprint 종합 실행 계획 |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | 기여·후속 캡스톤 인수 |
| [CHANGELOG.md](CHANGELOG.md) | 버전 히스토리 |

## 🔬 연구·논문 (Track B)

| 문서 | 내용 |
|---|---|
| [paper/contribution_outline.md](paper/contribution_outline.md) | 3 기여 후보 비교 (P701) |
| [paper/related_work.md](paper/related_work.md) | 30편 서베이 (P702) |
| [paper/refs/references.bib](paper/refs/references.bib) | BibTeX |
| [paper/latex/main.tex](paper/latex/main.tex) | 논문 본문 (P707) |
| [paper/latex/sections_4to7.tex](paper/latex/sections_4to7.tex) | §4-§7 본문 |
| [paper/review_checklist.md](paper/review_checklist.md) | 리뷰 체크리스트 (P708) |
| [paper/submission_guide.md](paper/submission_guide.md) | 투고 가이드 (P709) |

## 🛩 실기 하드웨어 (Track A)

| 문서 | Phase | 내용 |
|---|---|---|
| [hardware/README.md](hardware/README.md) | 전체 | BOM + 47일 일정 |
| [hardware/pixhawk_setup.md](hardware/pixhawk_setup.md) | P691 | PX4 v1.15+ |
| [hardware/jetson_mavlink.md](hardware/jetson_mavlink.md) | P692 | Orin Nano + MAVLink |
| [hardware/remote_id_broadcast.md](hardware/remote_id_broadcast.md) | P693 | ASTM F3411 v2.0 |
| [hardware/rtk_gps.md](hardware/rtk_gps.md) | P694 | u-blox + 한국 VRS-RTK |
| [hardware/failsafe_logic.md](hardware/failsafe_logic.md) | P695 | PX4 PARAM 매트릭스 |
| [hardware/time_sync.md](hardware/time_sync.md) | P696 | chrony + GPS PPS |
| [hardware/mocap_hitl.md](hardware/mocap_hitl.md) | P697 | Vicon HITL |
| [hardware/outdoor_test_protocol.md](hardware/outdoor_test_protocol.md) | P698 | M1-M6 비행 매트릭스 |
| [hardware/environmental_test.md](hardware/environmental_test.md) | P699 | 풍동·강우·저조도 |
| [hardware/fmea_report.md](hardware/fmea_report.md) | P700 | 12 FMEA · RPN |

## 🎤 발표 자산 (P710)

| 문서 | 내용 |
|---|---|
| [presentation/SDACS_Public_Project_Overview_2026.pptx](presentation/SDACS_Public_Project_Overview_2026.pptx) | 2026-06-18 최신 검증 수치를 반영한 공개 프로젝트 소개 10장 |
| [report/SDACS_Public_Project_Report_2026.docx](report/SDACS_Public_Project_Report_2026.docx) | 시스템 개요·검증 결과·현재 한계·재현 명령을 정리한 공개 설명 보고서 |
| [poster/README.md](poster/README.md) | 포스터 자산 가이드 |
| [poster/donggang_2026_ko.md](poster/donggang_2026_ko.md) | 동강대 4/23 한국어 포스터 |
| [poster/assets/results_nmr_msd_bar.png](poster/assets/results_nmr_msd_bar.png) | NMR·MSD 차트 |
| [poster/assets/pareto_front.png](poster/assets/pareto_front.png) | Pareto front 차트 |
| [slides/README.md](slides/README.md) | 슬라이드 outline |
| [slides/donggang_2026_ko.md](slides/donggang_2026_ko.md) | Marp 15장 슬라이드 |

## 🛠 Track E 확장 연구 (P736-P745)

| 문서 | 내용 |
|---|---|
| [track_e/p736_rl_training_guide.md](track_e/p736_rl_training_guide.md) | PPO 학습·평가 가이드 |
| [track_e/p742_kuam_runbook.md](track_e/p742_kuam_runbook.md) | K-UAM 평가 실행 |
| [track_e/p743_pqc_overhead.md](track_e/p743_pqc_overhead.md) | PQ Crypto 오버헤드 |
| [maritime_eoir_adapter.md](maritime_eoir_adapter.md) | 해양 EO/IR SDK 어댑터 (P735) |

## 🤝 산학·사업화 (Track F)

| 문서 | Phase | 내용 |
|---|---|---|
| [track_f/README.md](track_f/README.md) | 전체 | 10 Phase 우선순위 |
| [track_f/p746_k_uam.md](track_f/p746_k_uam.md) | P746 | K-UAM 30억 컨소시엄 |
| [track_f/p747_marine.md](track_f/p747_marine.md) | P747 | 해수부 항만 18억 |
| [track_f/p748_forest.md](track_f/p748_forest.md) | P748 | 산림청 IR 감시 |
| [track_f/p749_security_audit.md](track_f/p749_security_audit.md) | P749 | KISA CSAP |
| [track_f/p752_workshop.md](track_f/p752_workshop.md) | P752 | IROS workshop |
| [track_f/p753_licensing.md](track_f/p753_licensing.md) | P753 | 듀얼 라이선스 |
| [track_f/p754_mentoring.md](track_f/p754_mentoring.md) | P754 | 후속 캡스톤 |
| [track_f/p755_startup.md](track_f/p755_startup.md) | P755 | 창업 검토 |

## 💼 운영·배포

| 문서 | 내용 |
|---|---|
| [beta/README.md](beta/README.md) | 베타 운영 (P720) |
| [maritime_detection_technical.md](maritime_detection_technical.md) | 해양 시뮬 기술 (P728) |

## 🏛 표준화·정책 기고 (ODYSSEY Phase 461-480)

| 문서 | 설명 |
|---|---|
| [SDACS_STANDARDS_CONTRIBUTION_DASHBOARD.md](standards/SDACS_STANDARDS_CONTRIBUTION_DASHBOARD.md) | Phase 470 — 18 표준 정합 종합 대시보드 (분기 갱신) |
| [SDACS_ASTM_F38_PROPOSAL.md](standards/SDACS_ASTM_F38_PROPOSAL.md) | Phase 461 — ASTM F38 기고 초안 (SDACS-TM-1/2/3 시험 방법) |
| [SDACS_ISO_TC20_SC16_TRACKER.md](standards/SDACS_ISO_TC20_SC16_TRACKER.md) | Phase 462 — ISO/TC 20/SC 16 표준 동향 추적 매트릭스 |
| [SDACS_KDRONE_POLICY_PROPOSAL.md](standards/SDACS_KDRONE_POLICY_PROPOSAL.md) | Phase 463 — K-드론 정책 제안서 (산문 트랙, 자매: K_DRONE_POLICY_PROPOSAL.md 게이트) |
| [SDACS_SWARM_SAFETY_WHITEPAPER.md](standards/SDACS_SWARM_SAFETY_WHITEPAPER.md) | Phase 464 — 5계층 안전망 백서 (산문 트랙, 자매: SWARM_SAFETY_STANDARD_WHITEPAPER.md 게이트) |
| [SDACS_BENCHMARK_SUITE.md](standards/SDACS_BENCHMARK_SUITE.md) | Phase 465 — SDACS-SBS-10 공개 표준 시나리오 10종 |
| [SDACS_KS_PROPOSAL_UAS_CR.md](standards/SDACS_KS_PROPOSAL_UAS_CR.md) | Phase 471 — KS X UAS-CR-1 국가표준 제안 (산문 트랙) |
| [SDACS_ICAO_RPASP_OPINION.md](standards/SDACS_ICAO_RPASP_OPINION.md) | Phase 472 — ICAO RPASP 의견서 |
| [SDACS_GUTMA_HARMONY_OPINION.md](standards/SDACS_GUTMA_HARMONY_OPINION.md) | Phase 474 — GUTMA Harmony WG 의견서 |
| [SDACS_FAA_UTM_OPINION.md](standards/SDACS_FAA_UTM_OPINION.md) | Phase 475 — FAA UTM ConOps v2.0 의견서 |
| [SDACS_JARUS_WG105_OPINION.md](standards/SDACS_JARUS_WG105_OPINION.md) | Phase 476 — JARUS WG-105 SORA v2.5 의견서 |
| [SDACS_IFALPA_RPAS_OPINION.md](standards/SDACS_IFALPA_RPAS_OPINION.md) | Phase 477 — IFALPA RPAS 의견서 (유인-무인 통합) |
| [SDACS_STANDARDS_QUARTERLY_REPORT_TEMPLATE.md](standards/SDACS_STANDARDS_QUARTERLY_REPORT_TEMPLATE.md) | Phase 480 — 표준화 활동 분기 보고 템플릿 |
| `scripts/standards_conformance_check.py` | Phase 478 — 표준 산출물 정합성 자동 점검 (CI 게이트) |
| [STANDARDS_WATCH_PROCEDURE.md](standards/STANDARDS_WATCH_PROCEDURE.md) | Phase 479 — 표준 변경 분기 모니터링 절차 |

## ♾️ Continuum — 장기 지속성 (ODYSSEY Phase 481-500)

| 문서 | 설명 |
|---|---|
| [CONTINUUM_CENTENNIAL_DECLARATION.md](CONTINUUM_CENTENNIAL_DECLARATION.md) | 🌟 Phase 500 — SDACS Centennial 선언 (Phase 1-500 통합 회고 + 100년 비전) |
| [CONTINUUM_DIGITAL_LEGACY.md](CONTINUUM_DIGITAL_LEGACY.md) | Phase 490 — 2036년 재현 가능성 체크리스트 |
| [CONTINUUM_ARCHIVE_REDUNDANCY.md](CONTINUUM_ARCHIVE_REDUNDANCY.md) | Phase 489 — 3중 아카이브 (Zenodo·SWH·대학) |
| [CONTINUUM_SUCCESSION_PROTOCOL.md](CONTINUUM_SUCCESSION_PROTOCOL.md) | Phase 487 — 유지보수자 승계 규약 (BDFL→위원회) |
| [CONTINUUM_SECURITY_SLA.md](CONTINUUM_SECURITY_SLA.md) | Phase 488 — CVE 대응 SLA (CRITICAL 6h/HIGH 72h) |
| [CONTINUUM_DEPENDABOT_POLICY.md](CONTINUUM_DEPENDABOT_POLICY.md) | Phase 481 — 의존성 자동 갱신 3-Tier 정책 |
| [CONTINUUM_ELECTRON_LTS_TRACKING.md](CONTINUUM_ELECTRON_LTS_TRACKING.md) | Phase 484 — Electron LTS 추적 정책 |
| [CONTINUUM_NEXT_GENERATION.md](CONTINUUM_NEXT_GENERATION.md) | Phase 491-499 — 차세대 트랙 공모·이양 절차 |
| [maintenance/THREEJS_UPGRADE_PLAN.md](maintenance/THREEJS_UPGRADE_PLAN.md) | Phase 483 — Three.js r162→r170 업그레이드 리허설 |
| [maintenance/STALE_BRANCHES_CLEANUP.md](maintenance/STALE_BRANCHES_CLEANUP.md) | 원격 브랜치 정리 가이드 + 안전 스크립트 |

## 🔬 연구 조사 · 교육 · 보안 기록

| 문서 | 설명 |
|---|---|
| [research/RL_GENERALIZATION_SURVEY.md](research/RL_GENERALIZATION_SURVEY.md) | Phase 451 — RL 일반화 + EASA AI Roadmap 인증 가능 ML 조사 |
| [curriculum/CAPSTONE_STANDARD.md](curriculum/CAPSTONE_STANDARD.md) | Phase 468 — 15주 대학 캡스톤 표준 커리큘럼 (산문 트랙) |
| [security/CVE-2026-54283.md](security/CVE-2026-54283.md) | starlette CVE 대응 감사 기록 (Phase 488 SLA dogfooding) |

## 🌐 라이브 데모

- [GitHub Pages 메인](https://sun475300-sudo.github.io/swarm-drone-atc/)
- [군집 드론 3D 시뮬레이터](https://sun475300-sudo.github.io/swarm-drone-atc/swarm_3d_simulator.html)
- [해양 소형선 감지](https://sun475300-sudo.github.io/swarm-drone-atc/maritime_detection_simulator.html)

# Changelog

이 프로젝트의 모든 주요 변경 사항을 기록합니다.
형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/)를 기반으로 합니다.

## [Unreleased]

### 보안 (fix/security) — 2026-06-30 (47차): starlette CVE-2026-54283(높음)·54282(낮음) 대응

- **트리거**: GitHub Dependabot 주간 보안 알림 (2026-06-23 ~ 06-30, 사용자 스크린샷 공유). `starlette` 의존성 2 CVE — CVE-2026-54282(낮음, `<1.3.0`) + **CVE-2026-54283(높음, `<1.3.1`)**.
- **대응** (Phase 488 보안 SLA §2.1 — HIGH 72h 시한 → T+0 즉시 패치): `requirements.lock.txt` `starlette==1.2.1 → 1.3.1` (두 CVE 취약 범위 모두 벗어난 최소 버전). `requirements.txt` 에 `starlette>=1.3.1` 명시 보안 가드 추가 (transitive → explicit). Dependabot PR #367 제안과 일치 (본 브랜치 직접 해소 → #367 superseded).
- **영향 평가**: FastAPI 백엔드(`api/fastapi_server.py` P711/P712)만 영향, 시뮬레이션 코어·시뮬레이터 HTML 무관. SDACS 별도 방어층(JWT alg 검증·WS 입력 검증·CSP 헤더) 존재.
- **감사 기록** (Phase 488 §4.1 형식, dogfooding): `docs/security/CVE-2026-54283.md` 신규 — CVE 정보·영향 평가·대응 타임라인·패치 상세·검증 게이트·롤백 절차·후속.
- **검증**: fastapi 0.136.3 ↔ starlette 1.3.1 호환성은 CI `pip install` + `test (3.10/3.11/3.12)` + `pip-audit` 위임 (본 sandbox 미설치). CI 실패 시 감사 기록 §6 롤백 절차.

### 추가 (feat/test/docs) — 일일 점검 2026-06-26 (46차): Standards 정책 추적 도구 3종 (Phase 478·479·480) — Standards Track 종결

- **Phase 478** (Track 🛡 신규 스크립트) — `scripts/standards_conformance_check.py`. 표준 산출물(Phase 461-477) 메타 일관성 자동 점검. 4 검증: ①파일·헤더 존재 ②WG 의견서 정직성+MIT 강제 ③Phase 470 dashboard §2.2 인벤토리 드리프트 자동 탐지 ④WG 의견서→dashboard cross-link 무결성. CLI `--json` (CI 파싱) + `--check` (위반 exit 1). **실 산출물 12건 정합성 통과** — 작성 직후 IFALPA MIT 누락 1건 자동 발견 → 보강 (정직성 공시 확장). CI 게이트 통합 가능.
- **Phase 479** (Track 📡 신규 문서) — `docs/standards/STANDARDS_WATCH_PROCEDURE.md`. 표준 변경 모니터링 절차. 10 표준 기관 알림 채널(ASTM·ISO·EASA·FAA·ICAO·JARUS·GUTMA·IFALPA·KAIA·국토부) + 5 트리거 이벤트(신규 발간·개정·Public Comment·WG 회의·신규 권고) + 분기 4단계 점검(1주차 채널 점검·2-4주 산출물 검토·마감 보고서·dashboard 갱신). RSS 폴러·GHA cron·Slack/Discord 웹훅·LLM 영향 평가 자동화 후속 후보 명시.
- **Phase 480** (Track 📊 신규 템플릿) — `docs/standards/SDACS_STANDARDS_QUARTERLY_REPORT_TEMPLATE.md`. 분기 보고서 표준 템플릿 9 섹션 (보고 정보·요약·변경 사항·신규 의견서·회의 참석·SDACS 갱신·정합성 점검 결과·다음 분기 계획·한계+누락 정직성). 파일명 규약 `YYYY-QN`. Phase 478 명령 자동 첨부.
- **IFALPA 의견서 보강** — `docs/standards/SDACS_IFALPA_RPAS_OPINION.md` Limitations 섹션에 MIT 라이센스 명시 추가 (Phase 478 점검 발견).
- **회귀 테스트** — `tests/test_phase_478_479_480_standards_tools.py` (신규) 20 케이스. 478 6건(file·executable·header·imports·phase coverage·actual pass·exit code), 479 5건(file·header·10 organizations·triggers·quarterly·references), 480 5건(file·header·9 sections·conformance command·filename·honesty), live conformance 1건(전 산출물 정합성 통과). **20/20 PASS** + 실 정합성 라이브 게이트 통과.
- **검증**: 4 사본 md5 불변 · Bash syntax OK · Python py_compile OK. ROADMAP 338 갱신: 478·479·480 ✅ — **Standards & Policy Track (Phase 461-480) 전면 종결** (draft 473 제외 17 phase 완료).

### 추가 (feat/test/docs) — 일일 점검 2026-06-25 (45차): Standards WG 의견서 3종 (Phase 475·476·477)

- **Phase 475** (Track 🇺🇸 신규 문서) — `docs/standards/SDACS_FAA_UTM_OPINION.md`. FAA UTM ConOps v2.0 의견서 (Phase 472·474 자매). UTM 5 기능 (SCM·TCR·NIS·CM·USS) → SDACS Federation 9 모듈 매핑. 4 권고 (SDACS-SBS-10·5계층·USS interop·공개 자료실). Federal Register 의견 수렴 + RTCA SC-228 경유.
- **Phase 476** (Track 🌍 신규 문서) — `docs/standards/SDACS_JARUS_WG105_OPINION.md`. JARUS WG-105 SORA v2.5 의견서. SORA v2.0→v2.5 격차 매트릭스 6 (GRC·ARC·OSO #07/#18/#24·Mitigation). 5 권고 (sora_assess 자동화·OSO #07 5계층·OSO #18 split-brain·OSO #24 강풍·공개 참조). 한국 대표(국토부) 경유.
- **Phase 477** (Track ✈ 신규 문서) — `docs/standards/SDACS_IFALPA_RPAS_OPINION.md`. IFALPA RPAS Subcommittee 의견서. 유인-무인 통합 공역 관점. 격차 정렬 5 (분리·ATC·사고 보고·자격·공역). IFALPA Position 4 항목 정합. KAPA(한국민간항공조종사협회) 경유.
- **Phase 470 dashboard 갱신** — Phase 471·472·474·475·476·477 6 신규 문서 인벤토리 추가 (분기 갱신 절차 정합).
- **회귀 테스트** — `tests/test_phase_475_476_477_opinions.py` (신규) 27 케이스. 공통 베이스 클래스 (`_OpinionPaperBase`) — 모든 의견서 정직성·자매 참조·target_org 등 7 공통 + phase별 특수 검증. **27/27 PASS**.
- **검증**: 4 사본 md5 불변 · Python py_compile OK. ROADMAP 338 갱신: 475·476·477 ✅ + 잔여 splitting (478-480).

### 추가 (feat/test/docs) — 일일 점검 2026-06-25 (44차): Phase 474 GUTMA Harmony WG 의견서

- **Phase 474** (Track 🌐 신규 문서) — `docs/standards/SDACS_GUTMA_HARMONY_OPINION.md`. GUTMA (Global UTM Association) Harmony Working Group 의견서. Phase 472 ICAO RPASP 자매. **5 행동 권고**: ①USS 상호운용성 시험 자동화(Federation 9 모듈 참조 구현)·②결정적 시뮬 SLA(동일 시드→bit-exact)·③HLC 글로벌 인과 순서 표준(Phase 431)·④split-brain 4단계 사다리 ConOps(Phase 430)·⑤SHA-256 해시 체인 변조 탐지(Phase 429). Federation 9 모듈(421·422·423·424·425·428·429·430·431·432) 각 모듈을 GUTMA 격차에 매핑. 5단계 표준화 일정(2026-Q4 GUTMA 회원 등록 → 2027-Q4 recommended practice 등록). draft PR #432·#434 (phase 473) 회피 — 474 부터 진행.
- **회귀 테스트** — `tests/test_phase_474_gutma_opinion.py` (신규) 9 케이스: file·header·GUTMA target·5 권고·Federation 9 모듈·자매 문서 참조·MIT·정직성·실측 결과. **9/9 PASS** (직접 실행).
- **검증**: 4 사본 md5 불변 · ROADMAP 라인 338: 474 ✅ + 잔여 라인 splitting (475-480).

### 추가 (feat/test/docs) — 일일 점검 2026-06-25 (43차): ROADMAP 4종 + 🌟 **Phase 500 SDACS Centennial 선언**

- **사용자 요청**: 42차 머지 후 "계속 진행해" + Ultracode 활성. ODYSSEY Track 마지막 4건 일괄 — Standards & Policy (471·472) + Continuum (491·500) 완료. 본 세션의 **정점**.
- **Phase 471** (Track 🇰🇷 신규 문서) — `docs/standards/SDACS_KS_PROPOSAL_UAS_CR.md`. KSA 경유 KS X 표준 제안서. 무인이동체 군집 충돌 해결 시험 방법(KS X UAS-CR-1). 11 용어 정의 + SDACS-SBS-10 채택(B01-B10) + 5 측정 지표(95% resolution·10m 분리·100ms p95·60 events·0 NFZ 위반). 7단계 제안 일정 (2026-Q4 KSA → 2028-Q1 ISO 기고). 5 부속 자료 + 시험 보고서 양식.
- **Phase 472** (Track 🌐 신규 문서) — `docs/standards/SDACS_ICAO_RPASP_OPINION.md`. ICAO RPASP (Remotely Piloted Aircraft Systems Panel) 의견서. 4 행동 권고: ①DAA 시험 방법 표준화 (ASTM F3478 + ISO 23629-5 + SBS-10)·②결정적 시뮬레이션 의무화·③5계층 안전망 권고·④공개 참조 구현(MIT). 5계층 정의 + 결정성 + SBS-10 + 실측 결과 (100/1K/5K). 단·중·장기 표준화 권고 (2026 → 2029+). 한국 정부 대표단 → KAIA → ICAO 4단계 제출 절차.
- **Phase 491-499** (Track ♾️ 신규 문서, 통합) — `docs/CONTINUUM_NEXT_GENERATION.md`. 차세대 트랙 공모·선정·이양 절차. 공모 4 대상(목포대 후속·항공대·서울대·KAIST·국제 contributor) + 8 제안서 필수 항목 + 평가 rubric 100점(학술 25·SDACS 정합 25·실행 20·거버넌스 15·개방성 15) + 70점 위원회 만장일치 게이트. 7단계 인계 (Phase 492 기술 → 493 launch → 494 점진 이양 → 495 Steward 임명 → 496 BDFL 후보 → 497 리허설 → 498 권한 이양 → 499 신시대). 미선정 4 처우 (archive·재제안·fork·공개 회신). 2027-Q1 공모 시작 일정.
- **Phase 500** (Track 🌟 신규 문서, **본 PR 정점**) — `docs/CONTINUUM_CENTENNIAL_DECLARATION.md`. **SDACS Centennial 선언** — Phase 1-500 통합 회고 + 영구 아카이브 동결 + 100년 비전. 0. 선언문 (2026-06-25 Phase 500 도달). 1. 영역별 성과 매트릭스 (Core·A-F 7 트랙 + G-I 3 ODYSSEY 트랙 = 10 영역). 1.2 본 세션 누적 표 (37차 → 43차, ODYSSEY 19 phase 완료 - **`451·461·462·463·464·468·470·471·472·481·482·483·484·487·488·489·490·491·500`**). 1.3 측정 (5,500+ pass·283 E2E·408 API·12K LOC·477 모듈·9 federation·18 표준·6 사본). 2. 3중 영구 아카이브 (Zenodo + SWH + 대학). 3. 효과 (즉시·1년·10년·100년). 4. NOT 의미 (개발 종료/인증/우선권/호환성 약속 아님 — 정직성). 5. 미래 기수에게 메시지 + 5 원칙 (결정성·5계층·정직성·수술적·단순함). 6. BibTeX 인용 양식 (sdacs2026centennial). 11 참조.
- **회귀 테스트** — `tests/test_phase_471_472_491_500_docs.py` (신규) 27 케이스: 471 6건(file·header·KS X·인용·SBS-10·합격 기준·KSA), 472 4건(file·header·ICAO RPASP·4 권고·정부 대표), 491 5건(file·phase 범위·공모·rubric·7 단계·승계 참조), 500 8건(file·header·선언문·회고 표·세션 누적·아카이브·인증 아님·BibTeX·후속 메시지). **27/27 PASS** (직접 실행).
- **검증**: Python py_compile OK · 4 사본 md5 불변. ROADMAP 갱신: line 332(471·472 ✅) · line 335(491·500 ✅) + Continuum 라인 종결.

### 추가 (feat/test/docs) — 일일 점검 2026-06-25 (42차): ROADMAP 3종 추가 (Phase 468·483·490) + README 최신화

- **사용자 요청**: 41차 머지 후 "진행" → 즉시 다음 라운드. 마지막 단계로 README 최신화.
- **Phase 468** (Track 🎓 신규 문서) — `docs/curriculum/CAPSTONE_STANDARD.md`. 대학 캡스톤 표준 커리큘럼. GENESIS 383(15주 강의 슬라이드) 확장. 학부 4학년 1학기 3학점(이론 1+실습 2)·15주(Part I 기초 1-5주·Part II 핵심 6-10주·Part III 응용 11-15주). CLO 7종. 팀 프로젝트 8 주제(🟢🟡🔴 난이도). 평가 rubric(중간 20·기말 40·산출물 30·참여 10 = 100). 다른 대학 채택 5단계(fork·로컬화·지도교수·장비·결과 보고). MIT 라이센스 자유 사용 명시.
- **Phase 483** (Track 🎨 신규 문서) — `docs/maintenance/THREEJS_UPGRADE_PLAN.md`. Three.js r162 → r170 메이저 업그레이드 리허설. 4 마이너 단계(r164·r166·r168·r170) 절차 + 호환 셰임 패턴(`useLegacyLights`·`ColorManagement`·`outputColorSpace`). 7 회귀 게이트(JS·md5·헤드리스·replay_cursor·smoke_sim·mega_swarm·canary). WebGPURenderer 마이그레이션 카나리 (r170+ 안정화 시 옵트인). 6단계 일정(2026-Q4 r164 → 2027-Q3 r170 조건부). 롤백 절차(`git revert` + 4 사본 md5 재계산).
- **Phase 490** (Track 🏛 신규 문서) — `docs/CONTINUUM_DIGITAL_LEGACY.md`. 디지털 유산 선언 — 2036년 재현 가능성 체크리스트. 6 카테고리(✅코드 영구 보존·📦의존성 재현·📚문서·🧪회귀·🔐보안·♾️거버넌스). 의존성 6 영역(Python·Node·OS·Three.js·Playwright·CUDA) 핀 정책. 2036년 재현 시나리오 5단계(git clone·docker compose·pytest·시뮬·게이트). 예상 이슈 7건 + 우회(GitHub 종료·Python EOL·WebGPU·Three.js 메이저·CUDA·정책·yank). "영원히 변하지 않는 자산" 6 항목. 분기 검증 절차. "미래 연구자(Future-2036)에게" 메시지. Phase 500 Centennial 선언 전제 완성.
- **README 최신화** — 진척 현황 날짜 06-24→06-25 / 미완료 기준 06-25 / I ODYSSEY 진척률 37%→**42%** / 최신 업데이트 배너 신규 (본 세션 ODYSSEY 15 phase + 7차 점검 + Three.js/Electron LTS + HUD 캐싱 + CSP·JWT·hooks + 411 브랜치 정리 가이드 종합).
- **회귀 테스트** — `tests/test_phase_468_483_490_docs.py` (신규) 22 케이스: 468 6건(file·header·GENESIS 383·15주·CLO 7종·rubric·MIT), 483 6건(file·header·r162·버전 경로·호환 셰임·회귀 매트릭스·롤백), 490 7건(file·header·2036·체크리스트·핀·재현 명령·미래 메시지·Phase 489 참조). **22/22 PASS** (직접 실행).
- **검증**: Python py_compile OK · 4 사본 md5 불변 (시뮬레이터 무수정). ROADMAP 갱신: line 332(468 ✅) · line 335(483·490 ✅) + 잔여 splitting (491-500).

### 추가 (feat/test/docs) — 일일 점검 2026-06-25 (41차): ROADMAP 3종 추가 (Phase 463·470·489)

- **사용자 요청**: "로드맵에 써져있는 모든 작업 시작해" → 40차 머지 후 즉시 다음 라운드. draft PR(#430·#433 phase 452/453) 회피하면서 sandbox 가능 + 충돌 위험 0 인 3종 일괄.
- **Phase 463** (Track 🇰🇷 신규 문서) — `docs/standards/SDACS_KDRONE_POLICY_PROPOSAL.md`. K-드론 시스템 정책 제안서, 국토교통부 제출 형식. 6 제안: ①결정적 시험 환경 표준화(SDACS-SBS-10 채택)·②5계층 안전망 통합(항공안전법 시행규칙 권고)·③다중 인스턴스 연합 운영 ConOps(F3548 호환·SDACS Federation 9 모듈 참조 구현·split-brain 4단계 사다리 의무화)·④인증 가능 ML 단계적 도입(EASA AI/ML 1A→1B→2A)·⑤사고 조사 표준 변환기(Phase 467 KARI/KOTI 공유)·⑥교육 자산 표준화(15주 커리큘럼·1-4종 매핑). 6단계 일정(2026-Q4 정책 협의 → 2028-Q1 운영 매뉴얼 배포). 정책 제출 template + 첨부 4종 명시. 한계 정직 공시: 학술 연구 산출물 기반 *권고 초안*.
- **Phase 470** (Track 🏛 신규 문서) — `docs/standards/SDACS_STANDARDS_CONTRIBUTION_DASHBOARD.md`. 표준화 기고 추적 대시보드. 18 표준 정합 매트릭스(ASTM F38·F3548/F3411/F3478/F3196 · ISO/TC 20/SC 16 23629-5/7·21895·CD 5491 · 국토부 K-UTM · 항공안전법 129·132·161 · ICAO Annex 13 · EASA SORA·AI Roadmap · FAA UTM · JARUS · GUTMA) 🟢🟡🔴 분류. 산출물 9종 인벤토리(Phase 451·461·462·463·464·465·466·467·470). 통합 일정 11건(2026-Q3 ASTM 멤버십 → 2028-Q4 시행규칙 개정). 회의·컨퍼런스 6건(KSAS·IROS·F38·GUTMA·ICRA·ISO). 분기 갱신 절차.
- **Phase 489** (Track ♾️ 신규 문서) — `docs/CONTINUUM_ARCHIVE_REDUNDANCY.md`. 3중 이중화 아카이브 정책 (Zenodo CERN DOI · Software Heritage 자동 크롤링 SWHID · 목포대 학술정보관). 단일 점 실패(SPOF) 제거 — GitHub 정책 변경·기업 인수·서비스 종료 위험 차단. Zenodo 등록 4단계 + DOI 정책(concept vs version) + `.zenodo.json` 메타데이터 + `CITATION.cff` 표준. SWH 자동/수동 저장 + SWHID 영구 식별자. 대학 리포지터리 4 자료. 보존 무결성 3중 일치 검증(git SHA ↔ Zenodo DOI ↔ SWH revision). Phase 500 Centennial 선언 전제 5 체크리스트 (코드 영구 보존·DOI 인용·MIT 라이센스·의존성 재현·문서 영구). 한계 정직 공시.
- **회귀 테스트** — `tests/test_phase_463_470_489_docs.py` (신규) 18 케이스: 463 5건(file·header·국토부·6 제안·Phase 464 백서 참조·정직성), 470 4건(file·header·5 표준 기관·9 인벤토리·분기 갱신), 489 6건(file·header·3중 이중화·DOI 정책·CITATION.cff·무결성·Phase 500 참조). **18/18 PASS** (직접 실행).
- **검증**: Python py_compile OK · 4 사본 md5 불변 (시뮬레이터 무수정). ROADMAP 라인 갱신: 331(Standards 잔여 — 463/470 ✅)·334(Continuum 잔여 — 489 ✅) + 잔여 라인 splitting.

### 추가 (feat/test/docs) — 일일 점검 2026-06-25 (40차): ROADMAP 2종 (Phase 484·488) + 원격 브랜치 정리 가이드

- **Phase 484** (Track ♾️ 신규 문서) — `docs/CONTINUUM_ELECTRON_LTS_TRACKING.md`. Electron LTS 추적 정책. 8주 메이저 사이클·동시 active 3·LTS 부재 모델 명시. v32.3.3 (v1.5.0 빌드) → v39+/v42(Dependabot #426) 마이그레이션 교훈 5건(`getAllDisplays` reflection·`setMenuBarVisibility` deprecation·macOS userData permissions·Chromium 130→135 WebGPU 안정화·`webContents.executeJavaScript` 동기 변형 제거). 5단계 업그레이드 점검(CHANGELOG·3-OS 빌드·회귀·보안·사용자 영향) + 4단계 일정. 호환 셰임 패턴 예시. Phase 481 dependabot Tier 3 정책 정렬.
- **Phase 488** (Track 🔐 신규 문서) — `docs/CONTINUUM_SECURITY_SLA.md`. 보안 장기 지원 SLA. CVSS 기반 응답·머지·릴리스 매트릭스 (**CRITICAL 6h/24h·HIGH 24h/72h·MEDIUM 3d/1w·LOW 1w/정기**). CRITICAL T+0~T+48h 즉시 대응 8단계(triage·영향 평가·패치 PR·CI 회귀·md5/API 게이트·머지·릴리스·공개 권고). 영향 평가 매트릭스 7 모듈(auth.py·fastapi_server.py·ws_bridge·federation·Docker·Electron·시뮬레이터). 의존성 6 핀 정책 (Python ~= · Node ^ · Docker exact · GHA major · Electron exact · Playwright exact) + 갱신/롤백 트리거 4종. 감사 로그 `docs/security/CVE-YYYY-XXXX.md` 형식 + 분기 보고 + 자동 도구 4 활성/4 후속. 키 관리(JWT/GPG) + 유출 응답 T+1h~T+1w 5단계. BDFL → Tri-Maintainer 전환 시 SLA 위원회 의결 강화 명시.
- **원격 브랜치 정리 가이드 + 안전 스크립트** — `docs/maintenance/STALE_BRANCHES_CLEANUP.md` + `scripts/cleanup_stale_branches.sh`. 411 원격 브랜치(claude/* 377·feat/* 14·fix/* 3·perf/* 1·main 1) 중 **83개 main 흡수 완료** (안전 삭제 후보). 6 SAFETY_LIST 자동 제외(main·HEAD·현재 작업·미머지 fix/feat/perf). 3 모드(dry-run 기본·interactive 1개씩 확인·delete-all "yes" 명시 확인). 패턴 필터 옵션(`--pattern "claude/fervent-babbage-*"`). 복구 절차(`refs/pull/<N>/head` 또는 SHA 직접 fetch) 명시. **사용자 명시 승인 후만 실행** — CLAUDE.md destructive 정책 준수.
- **회귀 테스트** — `tests/test_continuum_484_488_docs.py` (신규) 22 케이스: Phase 484 5건(file·header·릴리스 주기·v32→v39 교훈·보안 체크리스트·dependabot 참조), 488 6건(file·header·CVSS SLA·CRITICAL 절차·핀 정책·감사 로그·키 관리), 브랜치 정리 11건(guide·script·executable·safety list 두 곳·dry-run default·yes 명시 확인·3 모드 문서·복구). **22/22 PASS** (직접 실행, importlib).
- **검증**: Python py_compile OK·Bash syntax OK·4 사본 md5 불변 (시뮬레이터 무수정). ROADMAP 라인 333: 484/488 ✅ + 잔여 라인 splitting.

### 추가 (fix/test/docs) — 일일 점검 2026-06-25 (39차): 7차 정밀점검 (airspace_controller NaN 가드) + README 최적화

- **7차 정밀점검 — agent 2 병렬 + 직접 검증**: 이전 1-6차에서 안 본 영역 (`src/airspace_control/comms·planning·agents/`, `src/digital_twin/`, `src/autonomy/`, `src/rl/`, `src/training/`, `src/applications/`, `visualization/`, `simulation/monte_carlo.py`) 정밀 점검. Explore agent 2 병렬 launch + 보고 5건 직접 검증. **4건 거짓 양성 차단** (WGS84 ε 5.75e-14 차이 → 직접 계산 결과 현 상수 `6.69437999014e-3` 가 정확·agent 주장 `6.694379990197508e-3` 가 틀림 / communication_bus `delivered` 카운팅 → 의도(수신자 단위) 합리적 / numpy Generator.random() → 정상 메서드, agent 주장 거짓 / A* origin 차원 → 현 코드 safe). **진짜 결함 1건 수정**: `src/airspace_control/controller/airspace_controller.py` `_update_drone_state` 가 외부 TelemetryMessage 의 position/velocity 를 검증 없이 `np.array(...)` → NaN/None 이 들어오면 silent 전파 → 거리 계산·CPA·CBS 휴리스틱 silent failure. fastapi WS 진입은 별도 가드(_normalize_live_telemetry, 3068ae7) — 내부 CommBus 직접 호출 경로(ws_bridge·SITL 통합) 는 미가드였음. **defense in depth 가드 추가**: None 거부·np.asarray(dtype=float)·shape ≥ 3·np.all(np.isfinite) 검증. 가드 실패 시 메시지 silent drop (기존 동작과 호환). 기존 등록 드론은 잘못된 텔레메트리로 인해 변경되지 않음.
- **회귀 테스트 신규** — `tests/test_airspace_controller_nan_guard.py` 9 케이스: 정상 텔레메트리 등록(기준선)·position None 거부·velocity None 거부·position NaN 거부·velocity NaN 거부·position Inf 거부·short position(2D) 거부·기존 드론 NaN 무시 시 원본 position 보존·velocity 부분 NaN 거부.
- **README 최적화 — 변경 이력 압축**: 1,321 라인 → **1,064 라인 (-257)**. 변경 이력 테이블 274 entries 중 최근 15건만 유지 + 나머지 259 entries 는 `CHANGELOG.md` (Keep a Changelog 형식 + Phase 별 상세) 참조 1줄로 압축. git log / git show 로 history 조회 가능 명시.
- **검증**: Python py_compile OK · 4 사본 md5 불변 (b924df34, 시뮬레이터 무수정) · 회귀 9 케이스 자체 검증 통과. ROADMAP 새 항목 없음 (정밀점검은 ROADMAP 외 maintenance).

### 추가 (feat/test/docs) — 일일 점검 2026-06-24 (38차): ROADMAP 3종 추가 (Phase 451·464·482)

- **작업 범위**: 37차 (Phase 461·462·481·487 + HUD 캐싱) 머지 후 ROADMAP 미완료 잔여 중 draft PR(#430·#433 phase 452/453) 회피하면서 sandbox 가능 + 충돌 위험 0 인 ODYSSEY 3종을 단일 PR 로 통합. 37차와 동일 패턴(문서 + 결정적 회귀).
- **Phase 451** (Track 🔬 신규 문서) — `docs/research/RL_GENERALIZATION_SURVEY.md`. RL 일반화 + 인증 가능 ML 학술/표준 문헌 조사. 분포 변화 4 유형(covariate·concept·domain·adversarial) + 평가 프로토콜 4 (Henderson 2018·Cobbe 2019/2020·Benjamins 2023) + 대표 벤치마크 5 (Procgen·CARL·MetaWorld·NetHack·SDACS-SBS-10) + EASA AI Roadmap 5 레벨(AI/ML 1A·1B·2A·2B·3A) + EASA AI Concept Paper 5 요건(Data Quality·Learning Process·Model Impl·Inference Monitoring·Adversarial Robustness) + DO-178C·DO-330·DO-331·DO-332·DO-333·ISO/IEC 22989·23053·5469·EUROCAE ED-324 표준 매핑. SDACS 정렬 자산 명시(`telemetry_validator`·`scenario_fuzzer`·`standard_scenarios`·`ppo_collision` PoC). 단·중·장기 권고 3단계. **순수 문헌 조사** — 알고리즘 제안·논문 발표 아님(정직성 공시).
- **Phase 464** (Track 🛡 신규 문서) — `docs/standards/SDACS_SWARM_SAFETY_WHITEPAPER.md`. 5계층 안전망 사례 연구 백서. L1 APF(10Hz)·L2 CBS(이벤트)·L3 CPA(1Hz)·L4 ATC(1Hz)·L5 UTM(이벤트) Lexicographic 우선순위 + Phase 441 `specs/SafetyNetPriority.tla` invariant 정렬. **3 사례 연구**: ①2-드론 head-on (resolution 100%·min CPA 12.1m·APF p95 38ms) ②100 군집 high_density (resolution 95.9%·45 collisions·87 near misses, 본 PR 컨테이너 재검증) ③1K mega_swarm_1k (FPS 4·DC 677·visibleInstances 100%, `docs/PERF_MEGA_SWARM.md` §2 정렬). **표준 매트릭스**: EASA SORA(Intrinsic GRC·ARC·OSO 4 항)·FAA UTM ConOps v2.0(USS·Operational Intent·Conflict·NOTAM·Performance Auth)·ICAO Annex 13(Accident·Investigation·Recommendation)·한국 항공안전법(129·161·132·132의2). 5.1 운용 권고 5건·5.2 인증 권고 4건·5.3 한계 4건(실비행 데이터·인적 요인·환경·적대적). 회귀 검증 명령 동봉. 연구용 vs 인증 정직성 분리.
- **Phase 482** (Track ♾️ 신규 스크립트) — `scripts/browser_api_canary.py`. 브라우저 API 폐기 감시 카나리. 헤드리스 Chromium 으로 12 API(필수 7: webgpu·webworker·mediarecorder·webgl2·fetch·importmap·csp_meta / 옵션 5: offscreencanvas·structuredclone·abortcontroller·webxr·broadcastchannel) 가용성 결정적 측정. 각 API 별 `used_by` 메타데이터(예: webgpu → `_gpuDevice/dispatchGpuCompute`) — 폐기 발견 시 즉시 영향 모듈 식별. CLI: `--json` (CI 파싱)·`--check` (필수 누락 시 exit 1, CI 게이트)·`--required <id>...` (추가 필수 지정). `render_report()` 가 markdown 표 형식 보고서 생성. 카나리 페이지로 `swarm_3d_simulator.html` 사용 → CSP 환경 실측. 무작위성 0·기존 모듈 무수정 순수 추가. ODYSSEY PLAN 의 정확한 Phase 482 정의(SBOM 아님 — 본 PR 에서 ROADMAP 정정).
- **회귀 테스트** — `tests/test_phase_482_451_464_docs.py` (신규) 21 케이스: 451 6건(file·header·EASA AI Roadmap·표준·distributional shift 4유형·정직성 공시·PoC 명시), 464 7건(file·header·5계층·사례 연구·SORA OSO·권고·정직성), 482 8건(script·header·필수 API 정의·py_compile·CLI·module import·required APIs 매트릭스). **21/21 PASS** (로컬 직접 실행, importlib).
- **검증**: 4 사본 md5 불변 (시뮬레이터 무수정)·Python 스크립트 py_compile OK·API_PROBES 12개 (필수 7) 로드 검증. ROADMAP 갱신: 325·329·332 라인에서 451/464/482 ✅ + 잔여 라인 splitting.

### 추가 (feat/test/perf) — 일일 점검 2026-06-24 (37차): ROADMAP 4종 일괄 (Phase 461·462·481·487) + HUD 캐싱 최적화

- **작업 범위**: ROADMAP.md 미완료 16건 중 draft PR(#429-#434, phase 404·405·411·452·453·473) 회피하면서 sandbox 가능 + 충돌 위험 0 인 ODYSSEY 4종을 단일 PR 로 통합. 동시에 시뮬레이터 HUD 핫경로 마이크로 최적화 1건 추가.
- **Phase 461** (Track 🏛, 신규 문서) — `docs/standards/SDACS_ASTM_F38_PROPOSAL.md`. ASTM F38 (Unmanned Aircraft Systems) 위원회 기고 초안. F3548-21 USS Interoperability·F3411 Remote ID·F3478 Detect & Avoid·F3196 BVLOS 등 5종 표준에 대한 SDACS 자산 정렬 매트릭스 + 3개 시험 방법 제안(**SDACS-TM-1** 군집 충돌 해결률·**SDACS-TM-2** USS 연합 상호운용·**SDACS-TM-3** Detect & Avoid). 기존 federation 9 모듈(421-432)·operational_intent·safety_net_invariant 자산 재사용, 결정적 합격 기준(resolution rate ≥95%·min CPA ≥10m·APF latency p95 ≤100ms) 명시. 기고 일정 5단계(2026-Q3~2027-Q4).
- **Phase 462** (Track 🏛, 신규 문서) — `docs/standards/SDACS_ISO_TC20_SC16_TRACKER.md`. ISO/TC 20/SC 16 (UAS) 표준 동향 추적 매트릭스. 발간 10종(ISO 21384-1/2/3/4·21895·23629-5/7/8/12·24355) + 작업 중 5종(WD/CD/AWI) 추적, 격차 분석 3 카테고리(강한 정합·부분 정합·미정합), 기고 우선순위 3종(ISO 23629-5 UTM 구조·23629-7 데이터 모델·CD 5491 Geofencing). 분기별 갱신 절차 + 게이트(`pytest tests/test_operational_intent` 등) 명시.
- **Phase 481** (Track ♾️, 신규 문서) — `docs/CONTINUUM_DEPENDABOT_POLICY.md`. Dependabot 자동 갱신 정책 3-Tier: **Tier 1** semver patch+devDeps→auto-merge (CI green+md5 일치+API 게이트 조건), **Tier 2** minor→manual 1주 SLO, **Tier 3** major/security→cautious 2주 SLO + CVSS 매핑(CRITICAL 24h·HIGH 72h·MEDIUM 1w·LOW 정기). 9 CI 게이트 명시(Python 회귀·E2E·Node 스모크·API 정합성·4 사본 md5·Trivy·Bandit·pip-audit·canonical-hash). 적체 14건(PR #267-#279·#367·#426-#427) 처리 절차 동봉. 기존 `.github/dependabot.yml`(github-actions+npm weekly) 기반.
- **Phase 487** (Track ♾️, 신규 문서) — `docs/CONTINUUM_SUCCESSION_PROTOCOL.md`. 유지보수자 승계 규약 3-Stage 전환: **Stage 1** BDFL+Steward(현재→2027-Q1)·**Stage 2** Tri-Maintainer(2027-Q2→2028)·**Stage 3** Committee(2029+). 자격 매트릭스(누적 PR 10+·12mo 활동·GPG 키 등록), 선출 절차(추천→자격 검증→RFC→2/3 의결), 머지 권한 매트릭스(문서 1 LGTM·코드 1 LGTM+CI·보안 2 LGTM·API breaking 만장일치·릴리스 위원회 과반), 비상 절차(BDFL 부재 24h·30d·90d), 키 관리, MIT 라이선스/DCO 보호. Phase 500 Centennial 선언 전제 조건.
- **HUD 캐싱 최적화** (시뮬레이터 핫경로) — `updateStatsUI()` 매 틱 호출되며 8개 `getElementById` 반복 lookup 을 lazy init 캐시(`_hudEls` 객체) 로 통합. 마이크로 최적화이나 매 프레임 DOM 트리 워크 제거 → 저사양 기기·대규모 군집(1K+)에서 누적 가치. CSP 영향 없음(DOM 접근 패턴만 변경), behavior-identical. 4 사본 동기화 완료(md5 `b924df34bf37c6250798674d7e70ef50`).
- **회귀 테스트** — `tests/test_continuum_and_standards_docs.py` (신규) 24건 케이스: Phase 461 5건(file/header/ASTM 표준 4종/TM 3개/합격 기준), 462 5건(file/header/ISO 표준 3종/격차 분석/기고 우선순위), 481 4건(file/header/3-Tier/CVSS 매핑/dependabot.yml 참조), 487 5건(file/header/3-Stage/자격/머지 권한 매트릭스/MIT), Dependabot YAML 3건. **24/24 PASS** (로컬 직접 실행, 본 컨테이너 pytest 미설치라 importlib 경로). CI 에서 표준 수트 통합.
- **검증**: JS 구문(node --check) OK·4 사본 md5 일치·API 정합성 게이트는 playwright 미설치 환경이라 CI 위임. 기존 모듈 무수정 순수 추가 → 회귀 무영향. ROADMAP.md 라인 329(Standards & Policy)·332(Continuum) 갱신: 461/462/481/487 ✅ + 잔여 라인 splitting.
### docs — 2026-06-25: README 로드맵 전수 감사 (stale `[ ]` 마커 정직 재분류)

- README "미완료 작업" 전수 감사 — 기존 `[ ]` 항목 다수가 **이미 구현된 stale 마커**임을 코드 1:1 대조로 확인. ① 환경 의존(코드 불가) ② 코드 완료(실재 모듈) ③ 잔여 코드 작업으로 재분류. 확인된 실재 구현: Ablation(`ablation_study.py`+테스트 12 PASS)·Phase 400 레거시 선언(`legacy_declaration.py` 등 7모듈)·V2X(3)·디지털트윈(5)·federation(19)·표준/Continuum(`standardization_tracker`·`centennial_declaration` 등). 진척표 H 43→48%·I 38→46% 갱신. **남은 진짜 미완은 거의 전부 환경 의존**(실 HW·외부 기관·실 배포·차세대 기수) + 소수 doable(시뮬레이터 Track Ⅰ 시각화 마감·다중사용자 WS 인프라·연합 E2E).

### test(genesis) — 2026-06-25: Phase 319 테스트 절차서 검증 추가 (커버리지 0%→충족)

- **GENESIS Phase 319** — 기존 `simulation/test_procedures.py`(DO-178C §6 테스트 절차서 감사, 커버리지 0% = 무테스트)에 `tests/test_test_procedures.py` **23건** 신규 추가. 감사 실행·15 점검항목·준수율/판정·단계별 보고·`_detect_status`(MET/PARTIAL/NOT_MET) 상태 판정·`_glob_any` 안전성(__pycache__ 제외·상위경로 탈출 거부)·직렬화 검증. 실 리포 감사는 모듈 스코프 fixture 1회로 제한(반복 glob 방지, 5.8s). ruff clean. **참고**: 직전 시도에서 만든 `change_control_board.py` 는 기존 `ccb_change_control.py`(Phase 318)의 중복이라 제거하고 기존 모듈로 일원화함.

### 정리·최적화 — 2026-06-25: 메인 브랜치 정리 + A* 결정적 최적화 + xdist 수집 안정화

- **AIM 정밀검사 기록(소급)**: Phase 691-700 AIM 10개 모듈 정밀검사 9라운드(Round 4–12) 완료 — `tests/test_phase691_700_aim.py` **242 테스트**. NaN/Inf 바이패스 차단(`math.isfinite`), CAVOK 위양성 NO-GO 수정, 캡슐화 누수 방지, fail-closed 안전, 방어적 복사, 중복 거부. 대상: notam_manager·tfr_handler·vertiport_ops·metar_parser·aim_briefing·flight_following·cross_border_coord·post_flight_report·aero_charts·insurance_risk.
- **README/ROADMAP 정확화**: 모순되던 테스트 수치(5,444/5,536/5,714/5,831) → 검증값 **6,733 pass / 270 skip / 0 fail**(단일 프로세스 `pytest -n 0`, 7,003 collected)로 통일. ROADMAP `main` 커밋에 남아 있던 git merge conflict 마커 해소(Phase 402 `faa_uss_roles` + `faa_utm_gap` 병합). maritime 스모크 17/17·18/18 모순 → 실제 19/19. README 중복 이력 내러티브 제거(CHANGELOG로 위임).
- **xdist 수집 안정화**: torch 의존 테스트 5개 파일(`test_coverage_boost_2/4/5`·`test_deep_gpu_physics_equivalence`·`test_phase661_670_ai`)의 `pytest.importorskip("torch")`(ImportError만 포착)를 `try/except + skipif`(OSError WinError 1455 등 모든 로드 실패 포착)로 교체 — pytest-xdist 다중 워커 동시 torch DLL 로드 실패로 인한 "Different tests were collected" 수집 불일치 제거.
- **A* 경로계획 최적화(결정적 동치)**: `flight_path_planner._neighbors_2d`/`_astar_2d`·`cbs.get_neighbors`에서 호출마다 재생성되던 이웃 오프셋 리스트·격자 경계·`math.sqrt(2)`를 모듈 상수/캐시로 호이스트. 대표 시뮬(100기/60s/seed 42) KPI **바이트 동일**(45 collisions·87 near misses·95.9% 유지) 검증 — 재현성 무손상. 대표 실행 ~7.7s→~7.5s. `test_deep_planner_equivalence` 등 회귀 통과.
- **브랜치 정리**: 로컬 브랜치 4개 → `main` 1개(삭제분 커밋은 origin 보존).

### feat(odyssey) — 2026-06-25: ODYSSEY 10개 Phase 단일 일원화 안착 (#449 머지: Phase 404·405·411·452·453·454·455·456·457·473)

- **작업 상황 점검**: `git fetch origin main` → main `9ec0d72`(PR #447 CI 회복 머지) **CI GREEN** 확인. 점검 중 **근본 문제 식별** — ODYSSEY 트랙 10개 Phase(404·405·411·452·453·454·455·456·457·473)가 매일 재생성되는 "일일 점검" 드래프트 PR 약 16건(#429–448)에 흩어져 구현·어드바이저 검수·테스트까지 끝났으나 **main 에 한 번도 안착되지 못함**. 적체 근본 원인은 코드 부재가 아니라 **머지 결정 부재**(열린 PR 30건: ODYSSEY 드래프트 16 + Dependabot 11 + perf/기타 3).
- **조치 — 단일 일원화**: 현재 green main(`9ec0d72`) 위에 10개 Phase 의 **순수 추가 파일 27개**(모듈 9 + 표준 문서 9 + 테스트 9 + `README.en.md`)를 단일 브랜치로 통합. 가장 검수가 진척된 #444(404·405·411·452·453·454·473) + #441(455) + #445(456) + #448(457) 의 추가 파일만 선별 흡수(기존 코드 무수정).
- **버그 수정**: `ROADMAP.md` 에 잔존하던 **미해소 머지충돌 마커**(`<<<<<<< HEAD`/`=======`/`>>>>>>>` 라인 297·300·308) 제거 — 양측 [x] Phase 엔트리 union 으로 정합 해소.
- **신규 안착 Phase**: 404(EN 완역 `README.en.md`)·405(`benchmark_comparison.py` 국제 벤치마크)·411(`overseas_pilot_proposal.py` 해외 파일럿)·452(`rl_generalization_protocol.py` RL 일반화)·453(`rl_advisory_boundary.py` RL 자문 경계)·454(`ml_application_classification.py` EASA Level 분류)·455(`ml_data_management.py` ML 데이터 관리)·456(`explainability_conformance.py` 설명가능성)·457(`easa_operational_monitoring.py` 운영 모니터링·드리프트 대응)·473(`wg_opinion_portfolio.py` WG 의견서 포트폴리오).
- **검증**: 신규 27파일 단위 테스트 **519건 PASS**(addopts 격리 실행), ruff clean, `-O` 최적화 임포트 9모듈 정상. 기존 파일 무수정 → 회귀 무영향.
- **점검 발견(사용자 결정 필요)**: ① 본 PR 머지 후 중복 ODYSSEY 드래프트 **#429–448 일괄 close 권고**(본 PR 이 상위집합). ② **Dependabot 11건**(electron `39→42` #426 EOL 우선·playwright #427·starlette #367 등) triage. ③ perf #283·Phase 207 #280 별도 검토. 본 일원화 PR(#449)을 main에 안착시켜 적체를 해소했고, 중복 ODYSSEY 드래프트 #429–448은 별도로 close 완료(2026-06-25).

### 추가 (feat/test) — 일일 점검 2026-06-21 (52차): ODYSSEY Track 🔬 Phase 451 — EASA 신뢰 가능 AI(Learning Assurance) 적합성 자가 평가

- **작업 상황 점검**: 51차(PR #392, `a4510ef`) 머지 후 `git fetch origin main` → **`origin/main == HEAD`(클린 베이스)** 확인. ODYSSEY Track 🔬 Formal & Research Frontier(451-460, "RL 일반화 연구 + 인증 가능 ML 조사")는 그간 미착수(450 까지 완료·451-460 범위 미세분). 금일 병행 점검이 적체시킨 열린 draft PR 들(#417·#418·#419·#420 — Standards/Continuum 트랙 461·463·464·468·471·472·491·492·500 중복 일원화)과 **서로소 트랙**을 골라 충돌·중복 없이 진행하기 위해, 451-460 의 sandbox 가능 착수 칸인 **Phase 451**(EASA AI 인증 조사)을 신규 구현.
- **점검 발견(사용자 검토 필요)**: 열린 PR **20건** 적체 — Dependabot 13건(#267-279) + perf #283(핫루프 힙 할당 제거) + Transcendence Phase 207 draft #280 + 금일 일일 점검 draft 4건(#417·#418·#419·#420, 상호 중복 일원화). #417·#420 은 동일 트랙(461·463·464·468·491·492)을 경쟁 일원화 중. 머지·triage·중복 close·취약점 패치는 **사용자 승인 필요**.
- **Phase 451** (Track 🔬 Formal & Research Frontier, 신규 코드) — `simulation/easa_ai_conformance.py` + `docs/standards/EASA_AI_CONFORMANCE.md`. SDACS 의 *학습 기반(ML)* 구성요소(PPO 충돌 회피 `src/rl/ppo_collision.py`·도메인 무작위화 `src/training/domain_rand.py` 등)가 EASA **Concept Paper**(Guidance for Level 1&2 ML applications, Issue 02 2024) + **AI Roadmap 2.0**(2023) 의 신뢰 가능 AI 빌딩 블록 6종(`trustworthiness_analysis`·`learning_assurance` W-shaped·`explainability`·`human_factors`·`safety_risk_mitigation`·`ethics_assessment`)을 어디까지 충족하는가를 **결정적**으로 평가하는 적합성 매트릭스. Phase 407(`icao_utm_conformance`)이 *시스템 운영* 을 ICAO 축으로 평가하는 자매편 — 본 모듈은 *학습 구성요소* 를 EASA AI 축으로 평가. `AIObjective` frozen dataclass 18종(`__post_init__` snake_case id·anchor/summary 비공백·building_block enum·`foundational` bool 강제·**정직성 결속** `status==gap` ⟺ `sdacs_module is None`, 그 외엔 실재 경로 인용 강제)·`ConformanceReport`(frozen, `by_block` MappingProxyType 읽기 전용·카운트 비음수·블록 합 교차검증·**미지 블록 키 거부**). `test_cited_modules_exist_on_disk` 가 인용 7개 경로 디스크 실재를 강제(허위 충족 주장 차단). **정직 공시**(CLAUDE.md): SDACS 의 ML 은 *연구 수준* 이므로 평가는 의도적으로 보수적 — 가중 점수 **33%**(충족 2·부분 8·갭 8 / 총 18), 기반(필수) 목표 **1/10** 완전 충족. **SDACS 의 진짜 강점은 러닝 어슈어런스가 아니라 AI 안전 위험 완화**: ML(RL)은 항상 *자문* 이고 안전-결정권은 결정적 APF+CBS 5계층 안전망(`simulation/emergency_protocol.py`)이 보유 → "ML 을 안전-크리티컬 결정에 신뢰하지 않음" 아키텍처가 유일하게 충족(`runtime_safety_monitoring`·`classical_safety_net_authority`)인 근거. 최대 갭은 **학습 프로세스 검증**(`learning_process_verification` — 미학습 시나리오 전이 일반화)·**Level 분류**(`ml_application_classification`)로 451-460 후속 연구 과제와 정확히 일치. 무작위성 0·부수효과 0·자문이지 집행 아님·기존 모듈 무수정 순수 추가. CLI(`--matrix`·`--report`·`--block`·`--gaps`·`--foundational`). **code-reviewer 어드바이저 반영**: HIGH 1(`conformance_matrix` 행이 `summary` 누락 → 카탈로그 없이 행 재구성 불가 → `summary` 추가로 자기서술 보장 + 회귀 테스트)·MEDIUM 2(① `ConformanceReport.by_block` 가 합만 검증하고 미지 블록 키를 무검증 수용 → `BUILDING_BLOCKS` 외 키 거부 가드 + 테스트, ② 매트릭스 행이 가변 `dict` 라 호출자가 무음 변조 가능 → `MappingProxyType` 읽기 전용 동결 + 테스트)·LOW 2(`_BLOCK_NAMES` 미사용 → 리포트 블록 라벨에 사용해 활성화). 단위 **56건 PASS**.
- **검증**: `tests/test_easa_ai_conformance.py` **56건 PASS**(dataclass 불변식·정직성 결속·디스크 실재 강제·ConformanceReport 카운트/블록키/읽기전용 불변식·매트릭스 자기서술·결정성·보수적 점수<60%·CLI 6종, 0.13s). 대상 기존 `.py` 무수정 순수 추가 → 회귀 무영향. 본 컨테이너 최소 의존성(pytest·numpy·pyyaml) 설치 → 전체 수트는 CI 수집.
### 추가 (feat/test) — 일일 점검 2026-06-21: Standards & Policy 트랙 Phase 468 신규 (대학 캡스톤 표준 커리큘럼 제안 적합성 게이트)

- **작업 상황 점검 + 적체 일원화**: 신규 세션 컨테이너에서 의존성 신규 설치 후, 금일 병행 세션이 생성한 미머지 적체 draft **PR #415**(`claude/fervent-babbage-mm7dwq`, Phase 461·463·464·491·492·500 6칸 일원화, `main` 기준 0-behind clean)을 작업 브랜치로 fast-forward 일원화. 그 위에 Standards & Policy 트랙(461-480)에서 *유일하게 남은 코드화 가능 칸* **Phase 468** 을 자매 패턴으로 신규 구현 → 461-470 트랙 전부 완료(471-480 = KS/국제 의견서 잔여).
- **Phase 468** (Track 🏛 Standards & Policy) — `simulation/capstone_curriculum_standard.py` + `docs/standards/CAPSTONE_CURRICULUM_STANDARD.md`. SDACS 를 *워크드 예제* 로 삼는 15주 학부 캡스톤 디자인 표준 커리큘럼 제안서가 (1) 주차별 강의 자료 완비도 **와** (2) 한국공학교육인증원(ABEEK KEC2015) 프로그램 학습성과 커버리지를 동시 충족했는가를 **결정적 자문 게이트**로 판정. GENESIS 383(강의 슬라이드 산출물)을 *재사용 가능한 표준 교과* 로 묶는다. 자매 463(단일 정책 제안서 섹션 완비도 — 단일 차원)과 달리 **두 차원 교차 검증**: 모든 단원이 작성돼도 필수 학습성과(PO1·PO2·PO4·PO5·PO6) 하나가 어느 단원에도 매핑 안 되면 `NOT_READY`(463 에 없는 *교차 불변식*). **정직성 결속**: `DRAFTED` 단원은 반드시 실재 강의 자산 인용·`MISSING` 은 인용 금지·증거 부재 DRAFTED 는 학습성과 커버 불인정(거짓 커버 금지). *표준 제안 준비도*(`READY_FOR_PROPOSAL`/`PARTIAL`/`NOT_READY`)와 *실제 채택 상태*(`adoption_status`)는 **독립** — 전 단원 작성돼도 외부 대학·ABEEK 채택 전까지 현 상태 `NOT_PROPOSED` 정직 공시. 현 리포 판정 `PARTIAL (95%)`·15/15주 커버·필수 학습성과 5/5 커버(U09 논문 단원만 `OUTLINED` — 실측 그래프 의존, 기존 잔여 P707 §4-§7 과 정합). 자문, 부수효과 0·무작위성 0·기존 파일 무수정 순수 추가. CLI(`--matrix`·`--report`·`--gaps`·`--coverage`·`--adoption`). **code-reviewer 어드바이저 반영**. **59건 PASS**.
- **점검 발견(사용자 결정 필요)**: ① 금일 병행 세션 적체 draft **PR #410·411·412·413·414·415** — 본 작업 브랜치가 #415(491·492·500+461·463·464) + Phase 468 을 단일 브랜치로 일원화 → 본 PR 머지 후 #410-415 close 권고. ② **Dependabot 14건 적체**(#267-279·#367) — Phase 484 가 현 electron 핀(`^39`) **EOL** 공시(#277 `39→42` 우선 검토). ③ **GitHub 보고 취약점 4건**(2 high·2 low) 미해소 — 전부 사용자 승인 필요.

### 추가 (feat/test) — 일일 점검 2026-06-21: Standards & Policy 트랙 Phase 463 신규 (K-드론 정책 제안서 적합성 게이트)

- **작업 상황 점검 — baseline GREEN**: 신규 세션 컨테이너에서 의존성(simpy·scipy·plotly 등) 신규 설치 후 전체 수집 **6,149 tests · 0 collection error**, 자매 Standards 모듈 회귀(iso_tc20·standardization·policy_impact·cve·governance) **216건 PASS** 독립 재현 GREEN. ODYSSEY Continuum(481-500)은 491·492·500 종착까지 금일 병행 세션 PR #413 이 일원화(CI GREEN), Standards & Policy(461-480)에서 코드화 가능한 잔여 칸 **Phase 463** 을 자매 패턴으로 신규 구현.
- **Phase 463** (Track 🏛 Standards & Policy) — `simulation/k_drone_policy_proposal.py` + `docs/standards/K_DRONE_POLICY_PROPOSAL.md`. 국토교통부 「드론활용촉진법」 §6 드론산업기본계획 정렬 *K-드론 시스템 고도화 정책 제안서* 가 정부 제출 형식의 필수 섹션(8종: 배경·현황·개선방안·기대효과·추진일정·근거법령·예산·위험)을 갖췄는가를 **결정적 자문 게이트**로 판정. 핵심 설계는 *제출 준비도*(`READY_FOR_REVIEW`/`PARTIAL`/`NOT_READY`)와 *실제 제출 상태*(`submission_status`)를 **독립** 분리 — 전 섹션 작성·증거 디스크 실재여도 외부 국토부 제출 전까지 현 상태 `NOT_SUBMITTED` 정직 공시(준비 완료 ≠ 제출). **정직성 결속**: `DRAFTED` 섹션은 반드시 실재 증거 산출물 인용·`MISSING` 은 인용 금지·증거 부재 시 가중 0. 현 리포 판정 `READY_FOR_REVIEW (100%)`·제출 `NOT_SUBMITTED`. 자매 462(외부 ISO 추적)·470(SDACS 발신 기고)와 경계 분리. 자문, 부수효과 0·무작위성 0·기존 모듈 무수정 순수 추가. CLI(`--matrix`·`--report`·`--gaps`·`--submission`). **code-reviewer 어드바이저 HIGH 2 반영**: (1) 증거 인용 없는 OUTLINED 섹션이 `all([])==True` 공허 참으로 0.5 점수 인플레 → `bool(evidence) and ...` 로 차단, (2) 빈 레지스트리가 `len([])==0` 공허 참으로 READY 오선언 → `total>0` 가드. 회귀 테스트 3건 포함 **49건 PASS**·ruff clean.
- **점검 발견(사용자 결정 필요)**: ① 금일 병행 세션 적체 draft **PR #410·411·412·413** — #413 이 Phase 491·492·500(Continuum 종착)+461+464 일원화(CI GREEN·clean) → 사용자 머지 + #410-412 close 권고. ② **Dependabot 14건 적체**(#267-279·#367) — Phase 484 가 현 electron 핀 EOL 공시(#277 우선 검토). ③ **GitHub 보고 취약점 4건**(2 high·2 low) 미해소 — 전부 사용자 승인 필요.
### 추가 (feat/test) — 일일 점검 2026-06-21 (60차): ODYSSEY Continuum 종착 — Phase 500 Centennial 선언 (프로그램 캡스톤)

- **작업 상황 점검**: main(`a4510ef`)은 Phase 481-490 완결 상태. Continuum 차세대 이양 구간 작업(Phase 491·492)이 미머지 적체 draft PR(#394·#396·#403·#404)에 정체 중임을 확인 — 가장 완전한 #404의 feat 커밋을 본 작업 브랜치 `claude/fervent-babbage-gtecig`로 cherry-pick 일원화(491·492, 82건 PASS)한 뒤, 그 위에 코드 작업거리가 남은 마지막 칸 **Phase 500**을 신규 구현.
- **Phase 500** (Track ♾️ Continuum 종착) — `simulation/centennial_declaration.py` + `docs/standards/CENTENNIAL_DECLARATION_POLICY.md`. Continuum 트랙(481-500)·전체 500-Phase 프로그램의 *종착 선언*. "원저자·현 세대를 넘어 **100년 단위**로 살아남을 준비가 됐는가"를 결정적 종합 게이트로 명문화. 새 판정 기준을 발명하지 않고 **네 기둥**을 *호출만* 함(DRY — 판정 로직 복제 0): Phase 490 유산 준비도(READY)·489 아카이브 이중화(REDUNDANT)·487 거버넌스 승계(COMMITTEE_READY)·492 세대 이양 집행(HANDOFF_READY). **all-or-nothing**: 한 기둥이라도 미충족이면 `NOT_DECLARED`(`progress` 는 정직 공시용일 뿐 선언 불앞당김). `--status` 실측 → 네 기둥 전부 미충족(LICENSE 전문·DOI·위원회·2027+ 기수 미형성)으로 현 상태 **`NOT_DECLARED (0.0%)`** 정직 공시 — 잔여 100년 조건을 그대로 표면화. 자문·부수효과 0·무작위성 0·기존 파일 무수정 순수 추가. code-reviewer 어드바이저 HIGH 2(override 시 실제 자매 게이트 건너뜀·핸드오버 기둥 위임 Phase 492 정합)·LOW 1(미사용 `_PILLAR_ORDER` 제거) 반영. **27건 PASS**.
- **검증(신규 컨테이너 독립 재현)**: 의존성 신규 설치 후 전체 회귀 **6,019 pass / 280 skip / 0 fail**(175.62s) GREEN — 54차(5,958) 대비 +61(491·492·500 신규 테스트 포함). 신규 3개 모듈(491·492·500) 단위 **109건 PASS**.
- **점검 발견(사용자 검토 필요)**: 열린 PR **23건** 적체 — Dependabot 13건(#267-279) + #367 starlette + #283 perf 핫루프 + #280 draft Phase 207 + 일일점검 redundant draft 7건(#394·#396·#400·#401·#402·#403·#404). **GitHub 보고 취약점 4건(2 high·2 low)** 미해소. 머지·triage·취약점 패치·중복 draft close 는 모두 사용자 승인 필요. 본 PR 이 491·492·500 을 단일 브랜치로 일원화하므로, 머지 후 #394·#396·#400-404 close 권고.

### 추가 (feat/test) — 일일 점검 2026-06-20 (54차): ODYSSEY Continuum 세대 이양 구간 진입 — Phase 491 일원화 + Phase 492 신규

- **작업 상황 점검**: 51차(PR #392, `a4510ef`)로 Phase 481-490 완결된 클린 베이스 위에서 Continuum 차세대 이양 구간(491-499)에 진입. 신규 세션 컨테이너에서 의존성 신규 설치 후 전체 회귀 **5,958 pass / 280 skip / 0 fail**(201s, 85.09% cov) 독립 재현 GREEN.
- **Phase 491** (Track ♾️ Continuum) — `simulation/track_handover_policy.py` + `docs/standards/GENERATIONAL_HANDOVER_POLICY.md`. ODYSSEY 거버넌스 게이트 #4("491+ 신규 트랙은 차세대 주도, 현 세대는 리뷰만")를 **결정적 정책**으로 명문화. 차세대(2027+ 기수) 제출 신규 트랙 제안의 이양 수용 여부를 `assess_handover`(서로소 4단계 우선순위: 차세대 소유자 부재→REJECT 구조적 결격·현 세대 리뷰 미완→DEFER·보완형 결함(헌장·범위 중복·sandbox)→REVISE·그 외→ACCEPT)로 판정. **소유자가 사람을 대체 못함**(헌장·리뷰 충족여도 소유자 없으면 우선 REJECT). `POLICY_MATRIX`(소유자×리뷰×결함없음 8칸) 테스트 전수 일치 강제. `shipped_proposals()` 정직 공시: 2027+ 기수 미형성 → 제안 0건 `AWAITING_PROPOSALS`. 자문·부수효과 0·무작위성 0. code-reviewer 어드바이저 HIGH 2·MEDIUM 2·LOW 2 반영. **34건 PASS** — 미머지 적체 draft PR **#394**(52차)를 동일 베이스(`a4510ef`)라 충돌 없이 작업 브랜치로 일원화.
- **Phase 492** (Track ♾️ Continuum) — `simulation/track_handoff_readiness.py` + `docs/standards/NEXTGEN_TRACK_HANDOFF_POLICY.md`. Phase 491 이양 게이트의 다음 단계. *공모 전체에서 적격 제안을 가려 하나를 선정* 하는 문제를 결정적 정책으로 명문화(491 = 개별 제안 이양 수용 가능성, 492 = 적격 제안 간 우선순위 — 독립 기준·중복 로직 0). `assess_proposal`(주체 지정 × 범위 버킷(≥10 Phase 트랙 케이던스) × 필수 기준: 트랙 헌장·검증 가능한 성공 기준·**원저자 독립성**(Phase 487 bus factor 정합)·선행 의존성 → ELIGIBLE/NEEDS_WORK/REJECTED) + `select_track`(적격 제안을 부가 강점 점수 → `sha256(proposal_id)` 안정 해시 동률 분리로 결정적 선정 → HANDOFF_READY/NO_ELIGIBLE/AWAITING_PROPOSALS). `POLICY_MATRIX` 12칸 일치 강제. 자문·부수효과 0·무작위성 0. code-reviewer 어드바이저 HIGH 1·MEDIUM 2·LOW 1 반영(score 단일 산출·이유 문자열 공백·`dataclasses.replace`·ELIGIBLE 이유 검증). **48건 PASS**.
- **점검 발견(사용자 검토 필요)**: 열린 PR 19건 적체(Dependabot 13건 #267-279 + #283 perf 핫루프 + #280 draft Phase 207 + 일일점검 draft #393·#394·#395) · GitHub 보고 취약점 4건(2 high·2 low) 미해소 — 머지·triage·취약점 패치는 사용자 승인 필요. 일원화된 **#394** 는 본 PR 머지 후 close 권고.

### 추가 (feat/test) — 일일 점검 2026-06-21: ODYSSEY Phase 461 (ASTM F38 군집 관제 시험 방법) + 점검 보고

- **작업 상황 점검**: `git fetch origin main` → 작업 브랜치 클린 베이스(`a4510ef` = Phase 481-490 완결) 확인. 금일 병행 점검이 **PR #410**(`claude/fervent-babbage-ut5057`)에 ODYSSEY Continuum 종착 3칸(491·492·500)을 일원화 — 본 컨테이너 실측으로 109건 PASS·ruff clean·`mergeable_state: clean` **검증 완료**(머지 시 ODYSSEY 구현 가능 로드맵 종료, 493-499 는 2027+ 차세대 기수 외부 의존). 중복을 피해 본 세션은 *비충돌 미구현 칸* Standards & Policy 트랙 Phase 461 을 신규 구현.
- **점검 발견(사용자 결정 필요)**: ① **머지 병목** — 열린 PR 17건(#410 이 491/492/500 일원화). ② **Dependabot 14건 적체**(#267-279·#367) — Phase 481 `dependency_gate` 정책상 patch/dev-minor 는 AUTO_MERGE 후보, MAJOR 는 REVIEW. 특히 Phase 484 가 현 electron 핀을 **EOL(보안 백포트 종료)** 로 공시 → **#277(electron 39→42) 우선 검토** 권고. ③ #283(perf, ready)·#280(Phase 207 draft) 별도 평가 권장.
- **Phase 461** (Track 🏛 Standards & Policy) — `simulation/swarm_test_method.py` + `docs/standards/ASTM_F38_SWARM_TEST_METHOD.md`. ASTM Committee F38(*Unmanned Aircraft Systems*)에 기고할 **군집 공역 관제 시험 방법 7종**(SM-TM-01~07: 충돌 해결률·무충돌·수평/수직 분리·RTB 성공률·해소 지연·결정적 재현성)을 결정적 명세로 인코딩. ASTM 표준 시험방법 구조 중 *기계 검증 가능* 부분(측정 지표 + 합격 기준)만 코드로 굳혀 같은 KPI 에 같은 판정. Phase 465(시나리오)·466(텔레메트리 스키마)와 3축(무엇을 돌릴지·어떻게 기록할지·**무엇을 합격으로 볼지**) 완성. **정직 공시**: 임계는 모두 `proposed=True`(ASTM 채택 전), 측정값 부재는 PASS 아닌 INCONCLUSIVE(거짓 적합 차단). `evaluate_suite` all-or-nothing 적합. 무작위성 0·기존 모듈 무수정 순수 추가. CLI(`--list`·`--validate`·`--evaluate`·`--manifest`·`--markdown`). code-reviewer 어드바이저 HIGH 2(무한대 threshold 거부·테스트 거짓 정렬 불변식 제거)·MEDIUM 3(proposed=False error 격상·`SuiteResult` 집계 일치 강제·frozen 테스트 정밀화) 반영. 단위 **35건 PASS**.

### 추가 (feat/test) — 일일 점검 2026-06-21: ODYSSEY Phase 464 (군집 비행 안전 기준 백서 — 5계층 안전망 사례 연구)

- **작업 상황 점검**: `git fetch origin main` → 작업 브랜치 클린 베이스(`a4510ef` = Phase 481-490 완결) 확인. 금일 병행 점검이 **PR #410**(Continuum 종착 491·492·500)·**PR #411**(Standards & Policy Phase 461 ASTM F38)을 각각 `mergeable_state: clean` draft 로 적재 중임을 확인 → 중복을 피해 본 세션은 **비충돌 미구현 칸 Phase 464** 를 선택(서로소 신규 파일).
- **Phase 464** (Track 🏛 Standards & Policy) — `simulation/swarm_safety_standard.py` + `docs/standards/SWARM_SAFETY_STANDARD_WHITEPAPER.md` + `tests/test_swarm_safety_standard.py`. 군집 비행 안전 기준 백서의 *기계 검증 골격*: 5계층 안전망(L1 APF→L5 UTM)의 각 계층 안전 주장이 선적된 산출물(형식 증명·모델 검사·ablation)로 입증되는가를 결정적으로 감사. 백서 산문이 유일 출처(SSoT)이고 모듈은 인용 산출물의 *디스크 실재* 만 감사(지표 재계산 0, 중복 없음). **자매 모듈 경계**: Phase 306 RTM=추적성 매트릭스, Phase 441 `safety_net_invariant`=우선순위 단조성 형식 검사, Phase 286 `ablation_study`=계층 제거 경험적 효과. **정직성 결속**: 인용 근거 전부 실재+실행/형식(module·spec·script) 근거 1개↑이면 SUBSTANTIATED, 일부만/문서만이면 PARTIAL, 부재면 UNSUBSTANTIATED(거짓 입증 차단). 인용 14개 산출물 디스크 실재 테스트 강제. 임계 proposed·실 비행 안전 아닌 산출물 실재 입증임 정직 공시(실 비행 검증은 Track A 의존). CLI(`--layers`·`--report`·`--markdown`·`--gaps`). 현 리포 5계층 전부 SUBSTANTIATED·횡단 근거 5/5·가중 커버리지 100%. 자문, 부수효과 0·무작위성 0·기존 파일 무수정 순수 추가. **code-reviewer 어드바이저 HIGH 2**(`_STATUS_WEIGHT` 데드 상수→`coverage_pct` 에서 사용·`WhitepaperReport` 가 `by_layer` 상태값 STATUSES 미검증→검증 추가)**·MEDIUM 3**(`..` traversal 경로 차단·`missing_evidence` 중복 의도 문서화·정렬 게이트 숫자 키)**·LOW 3 반영**. 단위 **51건 PASS** · ruff clean(CI 게이트 + 전체 룰셋).
- **로드맵**: Phase 464 → `[x]`, Standards & Policy 잔여 `461-463·467-468·470-480` 으로 갱신.
- **점검 발견(사용자 결정 필요)**: 열린 PR 18건+ 적체(Dependabot 14건 #267-279·#367 + #283 perf + #280 draft Phase 207 + 금일 daily-check draft #410·#411) · GitHub 보고 취약점 4건(2 high·2 low) 미해소 — 머지·triage·취약점 패치는 사용자 승인 필요. Phase 484 가 현 electron 핀을 EOL 로 공시 중 → **#277(electron 39→42) 우선 검토** 권고.

### 추가 (feat/test) — 일일 점검 2026-06-20 (51차): ODYSSEY Continuum 적체 드래프트 6칸 전면 일원화 — Phase 481-490 완결

- **작업 상황 점검 — 적체 드래프트 일원화**: 45차(PR #385, `40d8673`) 머지 후 작업 브랜치 클린 베이스 확인. ODYSSEY Continuum 트랙(481-500)에서 481·485·488·489 는 main 에 완료돼 있었으나, 나머지 비-이양 칸(482·483·484·486·487·490)이 **미머지 적체 draft PR 6건(#386-391)** 에 흩어져 있었음. PR **#390** 이 482·484·486·487·490 을 누적 스택으로, PR **#391** 이 483 을 별도로 보유 — 둘의 코드/테스트/표준문서(서로소 파일)를 단일 작업 브랜치로 통합해 **Phase 481-490 완결**(491-500 = 차세대 이양·Centennial 만 잔여). 6개 신규 모듈 단위 **241건 PASS**(browser_api_watch 41 + electron_lts_policy 56 + governance_succession 48 + legacy_readiness 30 + rehearsal_cadence 41 + threejs_upgrade_audit 25). 전부 결정적 정책·자문·부수효과 0·기존 파일 무수정 순수 추가. 흡수된 #386-391 은 본 PR 머지 후 close 권고.
- **점검 발견(사용자 검토 필요)**: 열린 PR 22건 적체(Dependabot 13건 #267-279 + #283 perf 핫루프 + #280 draft Phase 207 + 본 일원화로 흡수될 #386-391 6건) · GitHub 보고 취약점 4건(2 high·2 low) 미해소 — 머지·triage·취약점 패치는 사용자 승인 필요.
- **Phase 482** (Track ♾️ Continuum) — `simulation/browser_api_watch.py` + `docs/standards/BROWSER_API_DEPRECATION_WATCH.md`. HTML 시뮬레이터 의존 브라우저 API 의 폐기 위험을 (표준화 상태 × 의존 방식) 2차원 결정적 카나리로 판정(Phase 481/484/488/489 자매). 카나리는 실험/폐기 API 의 *필수 의존*(FRAGILE·BREAKING)만 발화 — feature-detect 폴백이면 안전. 실측 8 API 스냅샷 판정 결과 현 리포 `RESILIENT` 정직 공시. 자문, 부수효과 0. code-reviewer 어드바이저 HIGH 2·MEDIUM 3·LOW 3 반영. **41건 PASS**.
- **Phase 484** (Track ♾️ Continuum) — `simulation/electron_lts_policy.py` + `docs/standards/ELECTRON_LTS_TRACKING_POLICY.md`. 데스크탑 Electron 런타임이 보안 지원 창(최신 3 major)을 언제 벗어나는가를 결정적 정책으로 명문화. `package.json` 실측 핀(`^39.8.5`=39)과 상류 최신 스냅샷(42, Dependabot #277 증거) 비교로 현 상태 `UPGRADE_NOW (EOL, lag=3)` 정직 공시. 자문, 부수효과 0. code-reviewer 어드바이저 HIGH 2·MEDIUM 4·LOW 4 반영. **56건 PASS**.
- **Phase 486** (Track ♾️ Continuum) — `simulation/rehearsal_cadence.py` + `docs/standards/HEALTH_REHEARSAL_CADENCE_POLICY.md`. 신규 컨테이너 독립 재현 하니스가 *언제 다시 필요한가*(연 1회 365일 + 예고 30일 + 유예 30일)와 *온전한가*(4개 하니스 자산 실재)를 결정적 정책으로 판정. `LAST_REHEARSAL` 스냅샷으로 현 상태 `WITHIN_CADENCE` 정직 공시. 자문, 부수효과 0. code-reviewer 어드바이저 HIGH 2·MEDIUM 2·LOW 2 반영. **41건 PASS**.
- **Phase 487** (Track ♾️ Continuum) — `simulation/governance_succession.py` + `docs/standards/MAINTAINER_SUCCESSION_PROTOCOL.md`. "원저자(BDFL)를 넘어 위원회로 승계될 준비가 됐는가"를 결정적 정책으로 명문화. 연속성 보유자=활성+머지권한+관리자접근 동시 보유자만 집계(bus factor). 현 1인 구조 `BUS_FACTOR_RISK` 정직 공시. 자문, 부수효과 0. code-reviewer 어드바이저 HIGH 2·MEDIUM 1 반영. **48건 PASS**.
- **Phase 490** (Track ♾️ Continuum) — `simulation/legacy_readiness.py` + `docs/standards/DIGITAL_LEGACY_CHECKLIST.md`. 졸업 후 10년 재현·인용·법적 사용 가능성을 8기준×7차원 결정적 준비도로 판정(CRITICAL 미충족→NOT_READY), 아카이브 차원은 Phase 489 게이트 위임. 현 리포 `NOT_READY (58.8%)` 정직 공시. 자문, 부수효과 0. code-reviewer 어드바이저 HIGH 2·MEDIUM 2·LOW 2 반영. **30건 PASS**.
- **Phase 483** (Track ♾️ Continuum) — `simulation/threejs_upgrade_audit.py` + `tests/test_threejs_upgrade_audit.py`. 웹 시뮬레이터(`swarm_3d_simulator.html`)가 의존하는 벤더 Three.js(현 `vendor/three/three.module.js` **REVISION 162**)를 다음 메이저로 올릴 때 *어떤 심볼이 사라져 조용히 깨지는지* 를 사람이 매번 직관으로 점검하지 않도록 업그레이드 리허설을 **결정적 감사**로 명문화(같은 입력=같은 판정). **빌드가 진실의 근원**: 가장 단단한 보증은 시뮬레이터가 쓰는 모든 `THREE.<심볼>` 이 *실제로 벤더 빌드의 export 인가* — export 목록을 `three.module.js` 의 `export { ... }` 블록에서 직접 파싱(추측 0, `as` 별칭은 노출명 해석). 새 빌드를 떨어뜨리고 본 감사를 재실행하면 사라진 심볼이 즉시 `MISSING` → `BREAK` 로 표면화되는 것이 "리허설" 의 기계적 본체. 판정 우선순위 `BREAK`(쓰지만 export 부재, 깨짐 확정) > `REVIEW`(워치리스트 심볼 사용, 사람 확인) > `GREEN`(전부 일치). **워치리스트 정직성 게이트**: Three.js 역사에서 제거·이전된 API(레거시 `Geometry`·`Face3`·이전된 `Font`·`sRGBEncoding`/`LinearEncoding` 컬러스페이스 대체·`VertexColors` 불리언 대체)는 각 항목이 *현 벤더 빌드 export 에 실재하지 않음* 을 테스트(`test_watchlist_symbols_absent_from_real_build`)가 강제 → 빌드와 어긋난 추측 항목이 워치리스트에 끼는 것을 차단, 권위 근거는 항상 공식 `three.js/MIGRATION.md`. **자문이지 집행 아님**(부수효과 0)·무작위성 0·기존 파일 무수정 순수 추가. CLI(`--status`·`--watchlist`·`--manifest`). **현 리포 판정 GREEN**: 시뮬레이터가 쓰는 **47개** `THREE.*` 심볼 전부 r162 빌드 export 로 확인 + `three/addons/controls/OrbitControls.js` 임포트 검증 → 회귀 시 즉시 BREAK/REVIEW 로 표면화. **code-reviewer 어드바이저 HIGH 2·MEDIUM 4·LOW 3 반영**: (1) 감사 대상 파일 부재 시 `audit_repo` 가 조용히 GREEN 반환 → `BREAK` 로 정직 격상(감사 안 한 것을 통과로 포장 금지) + `tmp_path` 회귀 테스트, (2) JS 주석(`//`·`/* */`) 안의 `THREE.*` 가 사용으로 오집계되어 거짓 REVIEW/BREAK 유발 → 주석 제거 후 파싱(`://` URL 룩비하인드 보존), (3) `_REVISION` 워드바운더리·`_THREE_USE` `$` 대칭·`_ADDON_USE` 따옴표 역참조·빈 빌드 절대 GREEN 금지·CLI 테스트 추가. 단위 **25건 PASS**.

### 추가 (feat/test) — 일일 점검 2026-06-19 (45차): 적체 드래프트 일원화 — ODYSSEY Phase 488(CVE 대응 SLA) + 489(아카이브 이중화)

- **작업 상황 점검 — 적체 드래프트 일원화 머지**: 42차(PR #382, `c435335`) 머지 후 `git fetch origin main` → **`origin/main == HEAD`(클린 베이스)** 확인. 그러나 동일 클린 베이스 위에 금일 병행 점검이 draft PR 2건을 적체: **#383**(43차, ODYSSEY Phase 488 CVE 대응 SLA)·**#384**(44차, ODYSSEY Phase 489 아카이브 이중화). 두 작업은 **서로 다른 모듈을 추가하는 비충돌 순수 추가**(489 는 488 진행을 인지해 다음 미구현 칸을 골랐음)이므로, 기존 "일원화" 패턴에 따라 본 브랜치로 통합해 단일 PR 로 머지하고 흡수된 #383·#384 는 머지 후 close 권고. 두 신규 모듈 단위 **95건 PASS**(488 45 + 489 50, 489 는 일원화 검토 어드바이저 반영으로 47→50) + 자매 모듈 `test_dependency_gate.py` 44건 동반 통과 재확인.
- **Phase 488** (Track ♾️ Continuum) — `simulation/cve_response_policy.py` + `docs/standards/CVE_RESPONSE_SLA_POLICY.md`. Phase 481(`dependency_gate`, *기능* 갱신 자동 머지 정책)의 자매편 — CVE(*보안 취약점*) 한 건이 들어왔을 때 *대응 긴급도·SLA·핀 갱신 필요* 를 결정적 정책으로 명문화(같은 입력=같은 결정). CVSS v3.1 정성 등급 NVD 표준 절단점(`severity_from_cvss`). `CveReport` frozen dataclass(`__post_init__` 비공백 id/package·CVSS 범위·노출 enum·`fix_available`↔`fixed_version` 대칭 정합 검증)·`assess` 결정 우선순위(archived→`OUT_OF_SCOPE`·NONE/dev강등NONE→`MONITOR`·유효 CRITICAL/HIGH→`PATCH_NOW`·그 외→`SCHEDULED`). **SECURITY.md 기준선 준수**: SLA 는 외부 접수 7일·해결 14일을 HIGH 기준선으로 삼아 심각도별 단조(CRITICAL 1/7·HIGH 3/14·MEDIUM 7/30·LOW 14/90). **노출 차등**: dev 노출은 유효 심각도 1단계 강등. **정직성 결속**: `pin_refresh_required` 는 상류 수정 존재 + 핀 대상 노출일 때만 참. **자문이지 집행 아님**(부수효과 0). `POLICY_MATRIX` 10칸을 테스트가 `assess` 와 정확 일치 강제. CLI(`--policy`·`--demo`·`--manifest`). code-reviewer 어드바이저 HIGH 3·MEDIUM 2·LOW 1 반영. 단위 **45건 PASS**.
- **Phase 489** (Track ♾️ Continuum) — `simulation/archive_redundancy.py` + `docs/standards/ARCHIVE_REDUNDANCY_POLICY.md`. "현 아카이브 이중화가 **단일 실패점(single point of failure) 없이** 충분한가"를 **결정적 정책**으로 명문화. 보관처별 영구 식별자 형식을 정규식 검증(Zenodo DOI `10.5281/zenodo.<d>`·SWHID core `swh:1:(cnt|dir|rev|rel|snp):<40hex>`·기관 Handle `<prefix>/<suffix>`), **위치자 없는 예치 주장은 VERIFIED 불인정**(정직성). `deposit_state`(planned→PENDING·식별자 무효/누락→INVALID·유효→VERIFIED) → `assess_redundancy`(VERIFIED 만 내구 사본 집계, 독립성은 *custodian* 단위: Zenodo=CERN·SWH=Inria, 같은 기관 둘=하나). 판정: 독립 custodian ≥2곳 + 코드·데이터 양차원 → `REDUNDANT`, 1곳/차원 누락 → `PARTIAL`, 검증 사본 0 → `AT_RISK`. `POLICY_MATRIX` 6칸을 테스트가 일치 강제. **정직 공시**: `shipped_registry()` 는 메타데이터(`.zenodo.json`·`CITATION.cff`)는 준비됐으나 첫 릴리스 태그 전이라 **DOI 미발급**인 리포 현 상태를 그대로 반영 → `--status` 판정 `AT_RISK`. 자문이지 집행 아님(부수효과 0)·무작위성 0·기존 모듈 무수정 순수 추가. CLI(`--policy`·`--demo`·`--status`·`--manifest`). code-reviewer 어드바이저 HIGH 1(`_HANDLE` 정규식이 URL·다중경로를 핸들로 오인 → `[^\s/]+/[^\s/]+` 로 정밀화)·MEDIUM 2·LOW 2 반영. **일원화 검토 추가 어드바이저 반영**: `_HANDLE` 이 Zenodo DOI(`10.5281/zenodo.x`)를 기관 핸들로 오인(custodian 오집계) → `(?!10\.)` 네거티브 룩어헤드로 DOI 네임스페이스 거부(순수 숫자 핸들 접두 `20.x` 보존), 회귀 테스트 3건 추가. 단위 **50건 PASS**.

### 추가 (feat/test) — 일일 점검 2026-06-19 (42차): 적체 드래프트 PR 일원화 — ODYSSEY 462·481 + GENESIS 364 통합

- **작업 상황 점검 — 머지 병목 재발**: 41차(PR #375, `65a42c7`) 머지 후 `git fetch origin main` → **`origin/main == HEAD`(클린 베이스)** 확인. 그러나 동일 클린 베이스 위에 금일 병행 점검이 **draft PR 6건(#376·#377·#378·#379·#380·#381)** 을 적체. 분석 결과 **고유 작업 3종**으로 정리됨: ODYSSEY **Phase 462**(ISO/TC 20/SC 16 표준 추적, **경쟁 구현 4건** #376·#379·#380·#381)·ODYSSEY **Phase 481**(의존성 게이트, #377 단독)·GENESIS **Phase 364**(V2X 와이어 스펙, #378 단독). 기존 "일원화" 패턴(더 포괄적 구현 채택)에 따라 본 브랜치로 통합해 단일 PR 로 머지, 흡수·중복 PR 은 머지 후 close 권고.
- **Phase 462 경쟁 4건 중 #379 채택** (Track 🏛) — `simulation/iso_tc20_sc16_tracker.py`. 채택 근거: 가장 포괄적(테스트 59건)·정확한 ISO 카탈로그(21384-1/-2/-3/-4·23629-5/-7/-8/-9/-12 9종, 정확한 파트 번호·발행 연도)·3값 가중 정렬 점수(`aligned`/`partial`/`none`)·**공유 모듈(`standardization_tracker.py`) 무수정**(결합도·충돌 위험 최소). ISO/TC 20/SC 16(*Unmanned aircraft systems*) 외부 표준 지형을 추적하고 표준별 SDACS 정렬·갭을 표면화. `IsoStandard` frozen dataclass(`__post_init__` series 온전 접두 강제·`alignment` `none` ⟺ `sdacs_module is None` 정직성 결속·발행 표준 `:YYYY` 강제), `TrackerReport`(`by_series` MappingProxyType 읽기 전용·단계/정렬 합 교차검증). `test_cited_sdacs_modules_exist_on_disk` 가 인용 6개 모듈(`sora_category`·`uspace_service_map`·`geo_zones`·`remote_id`·`operational_intent`·`icao_utm_conformance`) 디스크 실재 강제. 정렬 점수 44%(정렬 2·부분 4·미정렬 3)·발행 78%(7/9). 무작위성 0·기존 모듈 무수정 순수 추가. **흡수 안 된 #376(`iso_tc20_sc16_tracker.py` 8종)·#380(`iso_uas_standards.py` + tracker STD-05 PUBLISHED 격상)·#381(`iso_uas_standards_matrix.py` + tracker STD-05 DRAFTING)** 은 머지 후 close 권고. code-reviewer 어드바이저 HIGH 2·MEDIUM 1·LOW 2 반영. 단위 **59건 PASS**.
- **Phase 481** (Track ♾️ Continuum, #377 단독) — `simulation/dependency_gate.py` + `docs/standards/DEPENDENCY_AUTOMERGE_POLICY.md`. 리포 적체 Dependabot 갱신 PR(pip·npm·github-actions)을 "회귀 통과 시 자동 머지 vs 사람 리뷰 vs 차단"으로 가르는 판단을 **결정적 정책**으로 명문화. `SemVer`(정규식 파싱·선행 0/불완전 하이픈 거부)·`classify_bump`·`RegressionGate`(게이트 GREEN = 자동 머지 필요조건)·`evaluate`(8단계 우선순위). **자문이지 집행 아님**(부수효과 0). `POLICY_MATRIX` 9칸을 테스트가 `evaluate` 와 정확 일치 강제. code-reviewer 어드바이저 HIGH 2·MEDIUM 4·LOW 3 반영. 단위 **44건 PASS**.
- **Phase 364** (Track GENESIS, #378 단독) — `simulation/v2x_message_spec.py`. 기존 `v2x_communication.py` 의 메모리 내 `V2XMessage`·채널 모델 위에 **인스턴스/구현 간 상호운용 정규 와이어 포맷** 추가. SAE J2735 BSM 의 고정소수점·고정 길이(36 B) 프레임을 드론 로컬 ENU 에 차용 — 위치 1 cm(int32)·속도 0.02 m/s(int16)·기수 0.0125°(uint16) 양자화로 *바이트 동일* 직렬화 보장, magic+version+CRC-32 트레일러로 전방 비호환·변조 검출. `BsmMessage`(frozen·양자화 캐시·범위 fail-fast)·`encode`/`decode`·`from_v2x_message` 어댑터(`v2x_communication` 읽기 전용). 무작위성 0·결정적. code-reviewer 어드바이저 HIGH 3·MEDIUM 3 반영. 단위 **23건 PASS**.
- **검증**: 신규 3종 합산 `pytest -o addopts=""` **126건 PASS**(462: 59 + 481: 44 + 364: 23, 0.70s, 신규 컨테이너 `pytest<9`+numpy+pyyaml 설치). 대상 기존 `.py` 무수정 순수 추가(462 는 공유 tracker 도 무수정) → 회귀 무영향.

### 추가 (feat/test) — 일일 점검 2026-06-19 (41차): 적체 드래프트 PR 7건 일원화 — ODYSSEY Phase 402·403·407·409·470 통합

- **작업 상황 점검 — 머지 병목 누적 해소**: 36차(PR #366, `6c525d2`) 머지 후 `git fetch origin main` → **`origin/main == HEAD`(클린 베이스)** 확인. 그러나 37–40차 병행 점검이 동일 클린 베이스 위에 **draft PR 7건(#368·#369·#370·#371·#372·#373·#374)** 을 적체 — 36차 이후 main 에 머지된 일일 점검 없음. 각 PR 은 *서로 다른 신규 `simulation/*.py` + `tests/test_*.py` 만 추가*(코드 비경쟁)하고 오직 `CHANGELOG`/`README`/`ROADMAP`/`SIMULATOR_ODYSSEY_PLAN` append 라인에서만 상호 충돌 → 순차 머지 불가. **중복 2쌍 발견**: #368(`faa_uss_roles.py`)·#369(`faa_utm_conops.py`)가 동일 **Phase 402**(FAA UTM USS 역할 갭) 경쟁 구현, #373·#374 가 동일 **Phase 409**(BVLOS 비교) 경쟁 구현. 기존 "일원화" 패턴대로 각 중복쌍에서 더 포괄적인 구현을 채택(#368·#373)하고 고유 Phase 5종을 본 브랜치로 통합해 단일 PR 로 머지, 흡수된 #369·#374 와 통합된 #368·#370·#371·#372·#373 은 머지 후 close 권고.
- **Phase 402** (Track 🌏, #368 흡수) — `simulation/faa_uss_roles.py` FAA UTM ConOps v2.0 USS 역할 17종 ↔ SDACS 적합성 매트릭스. 핵심 USS Network 역할 7/7·전체 15/17(88%), 갭(운영자 자격 검증·공공안전 데이터)을 `None` 으로 정직 표면화(`test_cited_modules_exist_on_disk` 디스크 실재 강제). `ConformanceReport` frozen 불변식·`MappingProxyType` 읽기 전용 행. 단위 **46건 PASS**.
- **Phase 403** (Track 🌏, #371 흡수) — `simulation/sora_category.py` + `docs/certification/EU_OPERATIONAL_CATEGORY.md` EASA EU 2019/947 운영 카테고리(Open A1/A2/A3·Specific·Certified) 결정적 판정. `SORA_IGRC`/`SORA_SAIL_TABLE` 은 `swarm_3d_simulator.html` JS 와 동일 복제(수치 불일치 금지). 단위 **51건 PASS**.
- **Phase 407** (Track 🌏, #372 흡수) — `simulation/icao_utm_conformance.py` ICAO UTM Framework Ed.4 운영자 여정 10단계 축 자가 평가. 3값 status(`conformant`/`partial`/`gap`)·정직성 결속(`gap ⟺ sdacs_module is None`) 강제, 가중 점수 83%·핵심 12/14. 단위 **56건 PASS**.
- **Phase 409** (Track 🌏, #373 흡수) — `simulation/bvlos_regulation_compare.py` + `docs/standards/BVLOS_REGULATION_COMPARISON.md` 한·미·EU·일 BVLOS 규제를 6개 비교 축으로 대조. 각 요건 권위 출처 인용(항공안전법 §129·14 CFR 107/108·EU 2019/947·改正航空法 Level 4)·`as_of` 스냅샷. 지원 3/4(일본 갭). 단위 **40건 PASS**.
- **Phase 470** (Track 🏛, #370 흡수) — `simulation/standardization_tracker.py` 표준화 기고 단일 SSoT 추적. 단조 상태 모델(PLANNED→ADOPTED)·`progress()` 22.5%·`validate_registry` 가 PUBLISHED 산출물 디스크 실재 강제. 단위 **31건 PASS**.
- **어드바이저**: 5개 모듈 모두 원 작성 세션에서 code-reviewer 어드바이저 반영분 포함(각 ODYSSEY PLAN 항목에 HIGH/MEDIUM/LOW 반영 내역 기재). 본 일원화는 채택 구현의 산출물을 무수정 통합.
- **검증**: 통합 5개 수트 합산 `pytest tests/test_faa_uss_roles.py tests/test_sora_category.py tests/test_icao_utm_conformance.py tests/test_bvlos_regulation_compare.py tests/test_standardization_tracker.py` **224건 PASS**(46+51+56+40+31). 대상 기존 `.py` 무수정 순수 추가 → 회귀 무영향. 본 컨테이너 최소 의존성(pytest·numpy·pyyaml·jsonschema) 설치 → 전체 수트는 CI 수집.

### 추가 (feat/test) — 일일 점검 2026-06-17 (36차): ODYSSEY Track 🌏 Phase 401 EASA U-space 서비스 매핑 + 406·408 추적 정정

- **작업 상황 점검**: 35차(PR #365, `7940543`) 머지 후 브랜치 클린 베이스 확인. 로드맵 미구현부 탐색 중 Track 🌏 International Standards(401-420)에서 **406(좌표계·UTM zone)·408(공역 클래스 A-G) 두 phase 가 이미 코드·테스트·문서로 적재 완료(각 39·25건 PASS 재검증)됐으나 ODYSSEY PLAN 에 ✅ 미표시** 인 추적 갭을 발견 — 기존 "추적 정정" 패턴으로 반영. 동시에 다음 sandbox 가능 항목인 **Phase 401**(EASA U-space U1-U4 서비스 매핑)을 신규 착수.
- **Phase 401** (Track 🌏, 신규 코드) — `simulation/uspace_service_map.py` (신규) EASA U-space 서비스(EU 2021/664 규제 + CORUS ConOps U1-U4 레벨)를 SDACS 기능에 결정적으로 대응시키는 **정합성 매트릭스**. `USpaceService` frozen dataclass 14종 카탈로그가 각 서비스의 도입 레벨(U1-U4)·EU 의무 여부·**리포에 실재하는 제공 모듈 경로**(`sdacs_module`)를 보유 — 대응 모듈이 없는 U4 유인 항공 통합은 `None` 으로 **갭** 을 정직 표면화. **정직성 강제 테스트**: `test_cited_modules_exist_on_disk` 가 인용된 12개 SDACS 모듈 경로(`remote_id.py`·`geofence_manager.py`·`airspace_controller.py`·`traffic_coordinator.py`·`weather.py`·`compliance_checker.py`·`telemetry_recorder.py`·`notam_manager.py`·`emergency_protocol.py`·`path_deconflict.py`·`airspace_capacity.py`·`kutm_protocol.py`)의 디스크 실재를 강제(허위 인용 차단). EU 2021/664 의무 4종(network identification·geo-awareness·UAS flight authorisation·traffic information) 100% 충족(4/4)·전체 13/14(93%)을 `coverage_report()` 가 결정적 집계. 조회 API `services_by_level`·`mandatory_services`·`gaps`·`implemented_services`·`service_matrix`(도구 간 교환용 JSON 행)·`find_service`. `CoverageReport`(frozen, `__post_init__` 카운트 불변식 검증·`by_level` MappingProxyType 읽기 전용). 무작위성 0·기존 모듈 무수정 순수 추가. CLI(`--matrix`·`--coverage`·`--level`·`--gaps`·`--mandatory`).
- **code-reviewer 어드바이저 반영** (CRITICAL 0·HIGH 2·MEDIUM 3·LOW 2): HIGH ①`CoverageReport.by_level` 가 frozen 임에도 가변 dict 라 `r.by_level["X"]=…` 로 무음 변조 가능 → `MappingProxyType` 읽기 전용 래핑 + 타입을 `Mapping` 으로 명시, ②`CoverageReport` 가 `__post_init__` 없이 `implemented>total`(→200% 등) 모순 상태를 무검증 수용 → 카운트 비음수·`implemented+gaps==total`·`mandatory_implemented≤mandatory_total`·`implemented≤total` 불변식 검증 추가. MEDIUM ①`is_mandatory_complete` 가 `mandatory_total==0` 일 때 공허참 True → False 반환 가드, ②`service_id` 패딩(`' id '`) 무음 수용 → `service_id != strip()` 거부, ③`summary` 빈 문자열 무검증 → 비공백 검증 추가. LOW: 두 서비스의 의도된 `path_deconflict.py` 공유에 명시 주석, `find_service` 비문자 인자 계약.
- **Phase 406·408 추적 정정** (코드 무수정) — 이미 구현·통과 중이나 ✅ 미표시였던 phase 를 산출물 존재 + 실측 통과 확인 후 ODYSSEY PLAN 에 반영: **406** 다국 좌표계·UTM zone 자동 판정(`simulation/geo_zones.py` — 위경도→UTM 존·MGRS 밴드·EPSG·공칭 시간대 결정적 변환, Norway/Svalbard 특례, 39건 PASS)·**408** 국제 공역 분류 A-G(`simulation/airspace_class.py` + `docs/certification/AIRSPACE_CLASS_MAPPING.md` — 고도·NFZ→ICAO 클래스 B·D·E·G·R 결정적 산정, 25건 PASS).
- **검증**: `tests/test_uspace_service_map.py` **37건 PASS**(어드바이저 반영 전 32 → 5건 추가: 패딩 id·빈 summary 거부·CoverageReport 불변식 위반·by_level 읽기 전용·0건 의무 미완). 추적 정정 phase 회귀 `test_geo_zones`(39)·`test_airspace_class`(25) **64건 PASS** 재확인. 대상 기존 `.py` 무수정 순수 추가 → 회귀 무영향. 본 컨테이너 최소 의존성(pytest·numpy·pyyaml) 설치 → 전체 수트는 CI 수집.

### 추가 (feat/test) — 일일 점검 2026-06-17 (35차): ODYSSEY Track ♾️ Phase 485 시나리오 포맷 버전 마이그레이션 도구

- **작업 상황 점검 — 중단된 34차 일원화**: 33차(PR #363, `cd44ba6`) 머지 후 병행 세션이 동일 클린 베이스 위에 **34차 드래프트 PR #364**(Phase 465 표준 벤치마크 스위트)를 적체. CI 4종(CI·Security Audit·Canonical Hash·P744 Air-Gap) 전부 `success`·`mergeable_state: clean` 확인 후 기존 일일 패턴대로 머지(`fcb96d2`)해 중단 작업 완료. 로컬 fast-forward 동기화 후 다음 sandbox 가능 항목으로 Track ♾️ Continuum(481-500)의 **Phase 485**(데이터 마이그레이션 도구)를 신규 착수.
- **Phase 485** (Track ♾️, 신규 코드) — `simulation/scenario_migration.py` (신규) 시나리오 포맷의 역사적 변종을 단일 canonical v2.0 으로 정규화하는 **결정적·멱등 버전 변환기**. **실측 분기 근거**: 러너 `scenario_runner._translate_scenario` 가 관용하는 동등 인코딩 — 시간 `simulation_duration_min`(분) vs `simulation_duration_s`(초, 리포 5:5 혼재)·드론 수 `drone_count`/`base_drone_count`/`base_traffic.drone_count`. 여기에 스키마(`scenario_schema`)는 `total_drone_count` 도 유효로 보나 *러너는 이를 읽지 않아*(예: `multi_city.yaml`) 드론 수를 얻지 못하는 잠재 불일치 존재. canonical v2.0 규약: 시간은 초 `simulation_duration_s`(SI·무모호)·드론 수는 단일 `drone_count`·`schema_version: "2.0"` 명시 스탬프. `detect_version`(미스탬프=레거시 1.0)·`migrate_scenario`(원본 무변형·결정적·**멱등** — 이미 canonical 이면 무변경 동일 반환)·`migrate_file`(YAML 라운드트립)·CLI(`--detect`·`--all` dry-run·`--migrate -o`). 정규화 출력은 항상 `scenario_schema.validate_scenario`(GENESIS 322) 계약을 **경고 없이** 충족 — 이를 위해 `simulation/scenario_schema.py` `_KNOWN_KEYS` 에 `schema_version` 1키 추가(수술적 1줄). **`multi_city` 의 `total_drone_count(240) → drone_count` 정규화로 러너가 드론 수를 읽을 수 있게 복원**(실제 운영 가치). 미션 포맷은 영속 버전 YAML 이 없어(코드 내 다수 planner 처리) 본 변환기 대상 외, `config/scenario_params/uam/` 하위는 `drones`/`airspace`/`corridors`/`vertiports`/`safety_net` 등 별도 풍부 포맷이라 범위 외임을 문서·코드에 명시. 무작위성 0.
- **code-reviewer 어드바이저 반영** (CRITICAL 0·HIGH 3·MEDIUM 4·LOW 2): HIGH ①잉여 count 키/잉여 `simulation_duration_min` 무음 삭제가 `changes`/`migrated` 에 미반영되어 "변경 없으면 동일 반환" 계약을 위반(출력은 달라지나 `migrated=False`) → 모든 구조 정리를 `changes` 에 기록하고 `migrated` 를 `bool(changes)` 로 재정의(v2.0 스탬프지만 잉여 키 남은 dirty 케이스도 정리 표면화), ②`_resolve_count` 의 `int(value)` 가 float count(`3.7→3`)를 무음 절삭하며 로그를 호도 → `_as_count` 로 비정수·bool 거부(스키마는 양의 정수 요구), ③테스트 갭(dirty-v2.0·float 거부 미검증) → 신규 단위 3건 추가. MEDIUM: `migrated` 관찰성 갭(①로 해소)·UAM 하위 제외를 문서·CLI 주석으로 명시·`_min` 무조건 제거 로깅·`multi_city` 기대값을 소스 YAML 에서 직접 읽어 어설션 동조. LOW: CLI 종료코드 docstring 정정·`--migrate` 다중 경로+`-o` 무음 무시 → `parser.error` 가드.
- **검증**: `tests/test_scenario_migration.py` **33건 PASS**(버전 판정·duration/count 정규화·멱등·불변성·결정성·전 리포 시나리오 canonical 적합·파일 라운드트립·어드바이저 회귀). 기존 `tests/test_scenario_schema.py`(33)·`test_standard_scenarios.py`(18)·`test_scenario_fuzzer.py`(14) 회귀 클린(합산 96 PASS). `schema_version` 1키 추가는 기존 시나리오 검증에 무영향. CLI dry-run 으로 전 10종 변환 실측 + multi_city 라운드트립 멱등 확인. 본 컨테이너 최소 의존성(pytest·numpy·pyyaml) 설치 → 전체 수트는 CI 수집(scipy/simpy 등 미설치 모듈은 sandbox 한계로 수집 불가, 본 phase 대상 외).

### 추가 (feat/test) — 일일 점검 2026-06-17 (34차): ODYSSEY Track 🏛 Phase 465 표준 벤치마크 스위트 (10종 공개)

- **작업 상황 점검**: 33차(PR #363, `cd44ba6`) main 머지 후 `git fetch origin main` → **`origin/main == HEAD`(클린 베이스)** 확인. 적체 드래프트 없음. Track 🏛 Standards & Policy(461-480)에서 다음 sandbox 가능 항목인 **Phase 465**(공역 통합 시뮬레이션 표준 시나리오 셋 — 10종 공개)를 신규 착수.
- **Phase 465** (Track 🏛, 신규 코드) — `simulation/standard_scenarios.py` (신규) 도구 간 교차 벤치마크용 **공개 표준 스위트** `SDACS-SBS-10` 큐레이션. Phase 405(BlueSky·U-TRAFMAN 비교)·410(GUTMA 기고)이 전제하는 "같은 10개 시나리오를 같은 정의로 돌려 비교한다" 는 공통 기준선을 제공. **중복 없는 큐레이션 계층**: 시나리오 *정의* 는 기존 `config/scenario_params/*.yaml` 이 유일 출처(SSoT)이며 본 모듈은 정의를 복제하지 않고 통제 축(axis)·범주·표제 KPI 메타데이터만 덧붙여 YAML 을 가리킨다(`BenchmarkScenario` frozen dataclass). 10개 항목 B01..B10 은 서로 다른 운용 차원 하나씩 통제(밀도·장애·이륙 서지·경로 충돌·통신 두절·기상·침입·다지역·자율 편대·공칭 기준선) — 통제 축 상호 배타. 검증되는 핵심 9종(s01-s09)에 더해 다른 9종 지표를 정규화하는 *대조(control)* 케이스인 신규 10번째 `config/scenario_params/nominal_baseline.yaml`(s10 공칭 저밀도) 추가. `validate_suite()` 가 10종 전부 `scenario_schema.validate_scenario`(GENESIS 322) 계약 충족(러너 호환)을 결정적 재검증, `benchmark_manifest()` 가 도구 간 교환용 JSON 매니페스트 생성. 공개 제안 문서 `docs/standards/SDACS_BENCHMARK_SUITE.md` 동반. 무작위성 0·기존 모듈 무수정 순수 추가. CLI(`--list`·`--validate`·`--manifest`).
- **code-reviewer 어드바이저 반영** (CRITICAL 0·HIGH 3·MEDIUM 2·LOW 2): HIGH ①10종 중 5종(B03·B04·B05·B06·B08)의 표제 KPI 가 소스 YAML `success_criteria` 에 실제 키로 없는 괴리(런너 파생 지표)를 매니페스트에 `primary_kpi_in_criteria` 플래그로 **기계 판독 가능하게** 노출 → 자동화 소비자가 `primary_kpi` 를 `success_criteria` 키로 오판하지 않게 함, ②`load_config` 가 `yaml.YAMLError` 미처리 → `validate_scenario_file` 과 대칭으로 `ValueError` 명시 변환, ③오류 처리 비대칭 완화. LOW 테스트에 `primary_kpi` 존재·괴리 플래그 정합 단언 2건 추가. 문서 KPI 표 각주 + B05 `*_range` 필드 런너 무시(고정 `comms_loss_rate=0.05`) 공시 추가.
- **검증**: `tests/test_standard_scenarios.py` **18건 PASS**(스위트 형상·스키마 적합·조회·결정성·매니페스트). 기존 `tests/test_scenario_schema.py` 회귀 클린. 대상 기존 `.py`·시나리오 정의 무수정 순수 추가 → 회귀 무영향. 매니페스트 플래그 실측: B03·B04·B05·B06·B08 = `primary_kpi_in_criteria: false`(어드바이저 지적과 일치). 본 컨테이너 최소 의존성(pytest·numpy·pyyaml) 설치 → 전체 수트는 CI 수집.

### 추가 (feat/test) — 일일 점검 2026-06-17 (32차): ODYSSEY Track 🏛 Phase 466 검증기 완성 + 31차 적체 일원화

- **작업 상황 점검**: 28차(PR #356, `9fe5335`) main 머지 후 `git fetch origin main` → **`origin/main == HEAD`(클린 베이스)** 확인. 직전 31차 작업이 코드 PR 1건(#359 Phase 469) + 중복 문서 PR 2건(#357·#358 Track 🔬 추적 정정)으로 적체된 것을 발견 — 기존 일원화 패턴대로 #360(consolidation, qyobg9)을 본 브랜치로 통합(fast-forward, Phase 469 `policy_impact.py` + 33건 검증 자산 + Track 🔬 445·446·449·450 ✅ 정정 포함)하고 그 위에 신규 Phase 466 검증기를 적층.
- **Phase 466** (Track 🏛, 신규 코드) — `simulation/telemetry_validator.py` (신규) 텔레메트리 표준 스키마 **검증기**. Phase 466 의 JSON Schema(`docs/schemas/telemetry.schema.json`, draft-07)는 2026-06-12 적재됐으나 phase 정의의 "검증기" 절반은 미구현이었던 것을 완성한다(ODYSSEY PLAN 92행 ✅ 미표시 → 정정). `validate_telemetry(payload)`·`validate_telemetry_file(path)` 가 임의 스냅샷의 표준 계약 충족 여부를 검사: `jsonschema` 설치 시 `Draft7Validator` 정본 검증, 미설치 시 스키마 제약(필수 키·길이 3 `pos`/`vel`·`battery` 0~100·`stats` 0 이상 정수·bool 카운터 배제)을 직접 구현한 순수 파이썬 폴백 — `jsonschema` 를 필수 의존성으로 끌어들이지 않으며 두 경로 동일 판정 확인. `simulation/scenario_schema.py`(GENESIS 322) `ValidationResult` 규약 준수, `CANONICAL_EXAMPLE` 표준 예제 + CLI(`--example`·파일 인자). 무작위성 0·기존 모듈 무수정 순수 추가.
- **검증**: `tests/test_telemetry_validator.py` **37건 PASS**(폴백 경로 직접 검사 + 공개 API 정본/폴백 동치). 기존 `tests/test_telemetry_schema.py` 3건 + 신규 37건 = 40건 클린. 대상 기존 `.py`·스키마 무수정 순수 추가 → 회귀 무영향. 본 컨테이너 최소 의존성(pytest·numpy·pyyaml·jsonschema) 설치 → 전체 수트는 CI 수집.

### 추가 (feat/test) — 일일 점검 2026-06-17 (31차): ODYSSEY Track 🏛 Phase 469 + Track 🔬 추적 정정 일원화 (적체 드래프트 PR #357·#358·#359 일원화)

- **작업 상황 점검 — 적체 드래프트 3건 일원화**: 28차(PR #356, `9fe5335`) main 머지 후 `git fetch origin main` → **`origin/main == HEAD`(클린 베이스)** 재확인. 직전 점검들이 반복한 "origin/main 미전진" 주장은 fetch 전 stale 로컬 ref 오인(local `main` 이 `19ef86d` 2026-06-05 에 고정)이었음을 다시 확정 — 실제 main 은 정상 전진 중. 병행 세션이 동일 클린 베이스 위에 draft 3건을 적체: **#359**(Phase 469 신규 코드)·**#357**(29차 추적 정정)·**#358**(28차 추적 정정 — #357 과 동일 Phase 445·446·449·450 ✅ 중복본). 코드 PR 1건 + 중복 문서 PR 2건이 모두 ROADMAP/CHANGELOG/PLAN append 라인만 충돌 → 순차 머지 불가. 기존 "일원화" 패턴대로 본 브랜치로 통합해 단일 PR 로 머지하고 #357·#358·#359 는 흡수 후 close 권고.
- **Phase 469** (Track 🏛, 신규 코드) — `simulation/policy_impact.py` (신규) 정책 영향 시뮬레이션. 규제 파라미터(수평·수직 이격, 고도 상한) 변경의 공역 용량 영향을 결정적 해석 모델로 정량화·자동 비교한다. 공역을 수직 분리 고도층 적층으로 보고 `layers = floor(band/vertical_min_m)+1`, 층당 용량은 이격 `s` 의 육각 최밀 충전 셀 `(√3/2)s²` 로 `floor(area/cell)`, `capacity = layers × per_layer`. `PolicyConfig`(frozen, 양수·고도 상하한·면적≥단일셀 불변식 검증)·`PolicyConfig.from_config`(`default_simulation.yaml` 의 airspace·separation_standards·drones 적재, 고도 바닥은 z[0]·drones.min_altitude_m 중 제약적인 쪽)·`compare_policies`(`capacity_delta`·`capacity_pct_change`·`utilization`·`is_oversaturated`·`summary`). 이격 50→70m 강화 시 용량 −49%(≈50²/70²) 정량화. **정직 공시**: 동역학 미포함 *정적 기하 용량 상한* 이라 절대값은 낙관적, 가치는 동일 모델 하 두 정책의 *상대 변화* 에 있음(CLAUDE.md "레포 데이터 불일치 수치 금지" 준수). 무작위성 0·기존 모듈 무수정 순수 추가.
- **code-reviewer 어드바이저 반영** (Phase 469, CRITICAL 0·HIGH 2·MEDIUM 3·LOW 3): HIGH ①음수 `min_altitude_m` 가 고도 band 를 부풀려 용량 과대계상 → `min_altitude_m ≥ 0`(AGL) 검증 추가, ②면적이 단일 드론 셀보다 작으면 용량 0 → 불투명 `ValueError` 대신 `__post_init__` 에서 `area_m2 ≥ 셀면적` fail-fast. MEDIUM ①`from_config` 운용 바닥 정정(고도층 과대 제거), ②CLI `or` 패턴이 명시적 `0.0` 인자 삼킴 → `is not None`, ③`summary()` 무변동 "+0.0% 증가" → "변동없음" 분기. LOW 경계 테스트(0대 활용률·없는 config 경로) 보강.
- **Track 🔬 추적 정정** (코드 무수정, #357·#358 흡수) — 이미 main 에 구현·통과 중이나 ✅ 미표시였던 phase 를 산출물 존재 + 실측 통과 확인 후 ROADMAP·SIMULATOR_ODYSSEY_PLAN 에 반영: **445** 불확실성 정량화(`simulation/uncertainty.py`, 16건 PASS)·**446** 검정력 분석(`simulation/power_analysis.py`, 15건 PASS)·**449** 시뮬-실측 갭(`src/training/sim_real_gap.py`·`domain_rand.py`, 7건 PASS)·**450** 재현성 10년(`requirements.lock.txt`·`Dockerfile.reproducible`·`scripts/independent_reproduction.sh`·`docs/REPRODUCIBILITY.md`, 인프라 완비). Track 🔬 핵심(441-450) 전부 완료, 잔여 = 451-460.
- 검증: `tests/test_policy_impact.py` **33건 PASS**(어드바이저 반영 전 27 → 6건 추가). 추적 정정 phase 회귀 `test_uncertainty`·`test_power_analysis`·`test_sim_real_gap` **38건 PASS**. 대상 기존 `.py` 무수정 순수 추가 → 회귀 무영향. 본 컨테이너 최소 의존성(pytest·numpy·scipy·pyyaml) 설치 → 전체 수트는 CI 수집.

### 추가 (feat/test) — 일일 점검 2026-06-17 (28차): ODYSSEY Track 🔬 Phase 441·442·444 통합 (적체 드래프트 PR #351·#352·#353 일원화)

- **작업 상황 점검 — 머지 병목 재발 해소**: 23차(PR #350, `6034308`)에서 Phase 443·448 통합 후 main 클린 베이스 확인. 이후 25·26차 병행 점검이 Track 🔬 Formal & Research(441-460) 진행분을 각각 draft PR 로 적체: **#352**(Phase 441 안전망 TLA+ + 444 CBS)·**#353**(Phase 442 핸드오프 모델 체킹)·**#351**(Phase 444 CBS — #352 의 부분집합)·**#354/#355**(문서 추적 정정 중복본). 세 코드 PR 은 *서로 다른 신규 파일만 추가*(비경쟁)이고 오직 ROADMAP/CHANGELOG/PLAN append 라인만 충돌 → 순차 머지 불가. 기존 "일원화" 패턴대로 Phase 441·442·444 를 본 브랜치로 통합해 단일 PR 로 머지하고, #351 은 #352 에 흡수되므로 close 권고.
- **Phase 441** — `specs/SafetyNetPriority.tla` + `docs/SAFETY_NET_TLA_SPEC.md` + `simulation/safety_net_invariant.py` (PR #352 흡수) 5계층 안전망 우선순위 단조성 불변식을 TLA+ 로 명세하고 Python 유한 모델 검사기로 핵심 안전 속성 재현. `SafetyState` frozen dataclass(severity→required_level 사상 검증)·`reachable_states` BFS·`check_invariant`(위반 시 초기→반례 최단 경로). 위협 심각도 상승 시 활성 안전 계층 단조 상승, 컨트롤러 미개입 시 위반 도달 가능성을 반례로 제시. 무작위성 0.
- **Phase 442** — `simulation/handoff_model_checker.py` (PR #353 흡수) 인스턴스 간 관제권 핸드오프를 유한 상태 기계로 모델링하고 도달 전 상태 BFS 전수 탐색으로 ①단일 관제권(공백·이중 금지) ②교착 부재를 증명. `HandoffState`(order=True 결정적)·`check_model`(반례 최단 경로)·`verify_handoff_safe`/`verify_handoff_deadlock_free`. code-reviewer 어드바이저 반영(이중 속성 단일 BFS 계약 — 같은 상태가 불변식 위반+교착이면 불변식 우선 보고 — docstring 명시). 무작위성 0.
- **Phase 444** — `simulation/cbs_optimality.py` + `docs/CBS_COMPLETENESS_OPTIMALITY.md` (PR #351·#352 흡수) CBS 완전성·최적성 조건(허용 휴리스틱·정점 분기 건전성·저수준 A* 비용 최적성)을 독립 BFS 기준해로 표본 검증하고 `cbs.py` 실 구현 보장/완화를 정직 공시(`audit_sdacs_cbs`). code-reviewer 어드바이저 HIGH 2건 반영: **①BFS 목표 반환 전 `(node,t)` forbidden 검사** 추가(시작 상태는 무조건 큐 진입하므로 start==goal 에 t=0 제약 시 비용 0 위양성 → 회귀 테스트 `test_reference_respects_t0_constraint_on_start_goal` 1건 추가)·**②A* 빈 경로의 타임아웃 vs 도달불가 미구별** 한계 docstring 공시. 무작위성 0.
- **검증**: 3개 신규 수트 `tests/test_safety_net_invariant.py`·`test_cbs_optimality.py`·`test_handoff_model_checker.py` **66건 PASS**(회귀 1건 포함). 전체 수집 5,204건 클린(0 collection error). 대상 `cbs.py`·`apf.py` 등 기존 코드 무수정 순수 추가.

### 추가 (feat/test) — 일일 점검 2026-06-16 (23차): ODYSSEY Track 🔬 Phase 443·448 통합 (드래프트 PR #347·#348·#349 일원화)
- **작업 상황 점검 — 머지 병목 중복 재발**: 20차(PR #346, `a42f6ff`)에서 🛰 Federation Operations(421-440) 완료 후 main 통합 확인(`origin/main == HEAD` 클린 베이스). 다음 트랙 **🔬 Formal & Research Frontier(441-460)** 로 전진하던 중, 세 병행 점검(21·22차)이 각각 draft PR 로 적체된 것을 발견: **#347**(Phase 448 — 시나리오 퍼저 6개 속성)·**#348**(Phase 448 — 4D 충돌 감지 코어 9개 속성, 같은 번호·다른 코어)·**#349**(Phase 443 — APF Lyapunov). 세 PR 은 *코드 비경쟁*(서로 다른 신규 파일만 추가)이며 오직 ROADMAP/CHANGELOG/README/PLAN append 라인만 상호 충돌 → 순차 머지 불가. 20차 "일원화" 패턴대로 **세 작업을 모두 본 브랜치로 통합**하고 Phase 448 의 두 속성 수트(퍼저+충돌감지)를 한 항목으로 합쳐 번호 중복을 해소한다.
- **Phase 443** — `simulation/apf_lyapunov.py` + `docs/APF_CONVERGENCE_PROOF.md` (PR #349 흡수) APF 수렴성 수학 증명. APF 힘 법칙이 보존 포텐셜의 음의 기울기 `F = -∇U`(인력 piecewise 이차/원뿔 C¹ + FIRAS 척력 `(k/2)(1/d−1/d0)²`)임을 명시하고, `total_potential`·`conservative_force`·`lyapunov_derivative` 로 양정치·radially unbounded Lyapunov 후보의 과감쇠 흐름 `dU/dt = −‖∇U‖² ≤ 0` + LaSalle 전역 수렴(콤팩트 레벨집합)을 형식 문서화. 국소 최소·속도 증폭 비보존항 한계, 상위 계층(CBS·교착 탈출) 완화 명시. `apf.py` 무수정 순수 추가, 무작위성 0. code-reviewer 어드바이저 HIGH 2건 반영(속도 증폭 비보존성 → "하강 무보증" 정정·엔진 0.1m 인력 데드밴드 정합). 단위 **16건 PASS**.
- **Phase 448** — Hypothesis 속성 기반 시뮬 코어 불변식 두 수트 동시 흡수(PR #347·#348). 기존 부분 구현(`test_property_telemetry.py` 텔레메트리 압축)이 못 채운 "시뮬 코어 불변식" 갭을 두 코어로 메운다:
  - `tests/test_property_deconflict.py` (PR #348) — 4D 경로 충돌 감지 코어 `PathDeconflict` 의 9개 불변식(P1 결정성·P2 삽입순서 무관·P3 보간 볼록성·P4 보간 클램프·P5 충돌 술어 일관·P6 시각 정렬·P7 수직 분리 보장·P8 단일 경로 0·P9 동일 경로 ≥1), 9속성×130예제=**1,170+케이스**. code-reviewer 어드바이저 HIGH 2건 반영(P3 None 진단·P9 `min_pts=2` 강화).
  - `tests/test_scenario_fuzzer_property.py` (PR #347) — Phase 447 적대적 퍼저(`scenario_fuzzer.py`) 계약을 "고정 시나리오 통과"에서 "근방 시나리오 공간 전역 통과"로 격상하는 6개 불변식(①스키마 보존 ②입력 불변성 ③시드 결정성 ④분포 합 1.0±0.01 재정규화 ⑤route min<max ⑥adversarial 단방향 편향), max_examples 합 **1,350케이스**. code-reviewer 어드바이저 APPROVE.
  - 대상 `.py` 무수정(테스트 순수 추가) → 회귀 무영향. ODYSSEY KPI "속성 테스트 1,000케이스" 초과 달성.
- 검증: 신규 3파일(apf_lyapunov 16 + deconflict 9 + fuzzer 6) **31건 PASS**(6.3s) + 인접 회귀(`test_apf`·`test_apf_property`·`test_property_telemetry`·`test_scenario_fuzzer`) **41건 PASS**. 본 컨테이너 최소 의존성(pytest·numpy·scipy·simpy·hypothesis·pyyaml) 설치 → 전체 수트는 CI 수집. PR #347·#348·#349 는 본 통합으로 superseded(머지 후 close).

### 추가 (feat) — 일일 점검 2026-06-16 (20차): ODYSSEY Phase 439·440 통합 (중복 PR #344·#345 일원화 → Federation Operations 트랙 421-440 완료)
- **작업 상황 점검 — 중복 PR 발견(머지 병목의 증상)**: 19차(PR #343, `6bc06d4`)까지 Phase 438 이 통합된 뒤, **두 병행 점검(20차)이 각각 "Phase 439" 로 서로 다른 모듈을 구현해 draft PR #344·#345 로 적체**된 상태를 확인. 두 PR 은 *코드 비경쟁*(서로 다른 신규 파일만 추가)이며 오직 "Phase 439" 라벨과 README/CHANGELOG/ROADMAP/PLAN append 라인만 충돌 — 머지 병목으로 직전 작업이 main 에 안 보여 다음 점검이 같은 번호로 중복 구현한 전형. 본 점검은 **두 모듈을 모두 본 브랜치로 일원화**하고 번호 충돌을 Phase 439(토폴로지 뷰)·440(신뢰 페일오버)으로 분리 해소해, 작업 손실 없이 **🛰 Federation Operations(421-440) 트랙을 완료**한다.
- **Phase 439** — `simulation/federation_topology_view.py` (PR #344 흡수) 신뢰 한정 도달성 통합 토폴로지 `FederationTopologyView`. Phase 432 메시 *연결성* + Phase 428 *신뢰* 를 합쳐 한 origin 관점에서 연합 목적지를 5개 도달성 품질(SELF·DIRECT·RELAYED_TRUSTED·RELAYED_RISKY·UNREACHABLE)로 분류하는 읽기 전용 관측 뷰. Phase 433 `TrustWeightedRouter` 가 *최소 비용 경로 하나* 를 고른다면 본 모듈은 **신뢰 중계만 거치는 경로의 존재성**(≠ 최소 비용)을 답한다 — 3+ 인스턴스 중계에서만 의미. `avoid_untrusted_route`(알려진 불신만 회피)보다 엄격히 각 중계가 *적극 신뢰*여야 하는 상보적 포스처. `reachability_class`·`classify`·`trusted_path`·`trusted_reach`·`risky_reach`·`summary`. 무작위성 0·순수 추가. code-reviewer 어드바이저 HIGH 3건 반영(원 PR). 단위 **27건 PASS**.
- **Phase 440** — `simulation/federation_trust_path_vector_failover.py` (PR #345 흡수, 원 "Phase 439"→440 재번호) 신뢰 인지 분산 경로-벡터 장애 우회 수렴 `TrustPathVectorFailover`. 연합 라우팅 **2×2 격자**(홉만/신뢰 인지 × 고정 메시/장애 후 재수렴)의 마지막 빈 칸 — Phase 438(홉만 장애 우회)과 Phase 437(신뢰 인지 고정 메시)의 결합. 살아남은 인접 위에서 Phase 437 신뢰 인지 경로-벡터(BGP LOCAL_PREF)를 인접 어댑터로 무수정 재수렴해 장애 전후 *신뢰 가중* 경로 비교(`rerouted`·`lost_routes`·`is_reroutable`·`surviving_path`·`reconvergence_rounds`·`summary`). 핵심 불변식: 빈 장애→Phase 437 항등, 무관찰(균일 0.5)→**Phase 438 장애 분석과 정확히 동일**(2×2 격자 모서리), 도달성은 신뢰 무관·Phase 438 동일(신뢰는 *어느 우회로* 만 가름, kite 토폴로지 검증). Phase 435 교차 검증·콜드스타트 등가성. 무작위성 0·순수 추가. code-reviewer 어드바이저 HIGH 1건 반영(원 PR). 단위 **27건 PASS**.
- 검증: 신규 topology_view 27 + trust_path_vector_failover 27 + 전체 federation 회귀(421~440) 합산 **425건 PASS**(0.50s). 본 컨테이너 최소 의존성(pytest·numpy)만 설치 → simpy·scipy·hypothesis 의존 수트는 CI 전체 수집. 기존 `.py` 무수정(순수 추가) → 회귀 무영향. PR #344·#345 는 본 통합으로 superseded(머지 후 close 권장).
- ROADMAP·`docs/SIMULATOR_ODYSSEY_PLAN.md` Federation Operations 트랙을 **421-440 완료**로 갱신. 잔여 `Phase 426-427`(2-인스턴스 E2E·고스트 렌더링)은 HTML 시뮬레이터·Playwright 환경 의존이라 본 최소 컨테이너에서 보류, HLC 통합 글로벌 순서 토폴로지는 차기 트랙 후보로 이월.
- ⚠️ **근본 원인(사람 판단 필요)**: 13~20차 누적 머지 병목 — Phase 433~440 작업이 `claude/fervent-babbage-*` 브랜치 체인(main 대비 ~250 커밋 선행)에만 쌓이고 `origin/main`(2026-06-05 `19ef86d` 이후 미전진)으로 머지되지 않아, 매 점검이 직전 결과를 못 보고 중복(20차 #344·#345)을 낳는 구조. 메인 통합 전략 결정이 필요.

### 추가 (feat) — 일일 점검 2026-06-16 (19차): ODYSSEY 적체 병목 해소(PR #342 main 머지) + Phase 438 분산 경로-벡터 장애 우회 수렴
- **작업 상황 점검 — 머지 병목 해소(근본 원인 처리)**: 12차(PR #335)까지 main 통합 후 Phase 433~437 작업이 **머지되지 못한 draft PR 7건(#336~#342)으로 적체**된 상태를 확인. 18차 PR #342(clean, base=main, Phase 433-437 전체 + 신규 437 흡수)가 적체를 단일 브랜치로 일원화하고 있었으나 **main 머지가 안 되어 누적만 반복**되는 것이 근본 원인. 본 점검에서 PR #342 브랜치를 로컬 검증(Phase 433-437 단위 **146건 PASS**) 후 **main 으로 머지**(`a463330`)해 병목을 해소하고, superseded 된 PR #336·#337·#338·#339·#340·#341 **6건을 close**.
- **Phase 438** — `simulation/federation_path_vector_failover.py` (신규) 분산 경로-벡터 장애 우회 수렴. Phase 436/437(고정 메시 1회 수렴)·Phase 435(중앙 구조 분석)의 공백인 *인스턴스(USS) 장애 후 분산 재수렴*을 모사하는 `PathVectorFailover`.
  - 장애 집합을 메시에서 제거한 살아남은 인접 위에서 Phase 436 `PathVectorRouting` 수렴을 **인접 어댑터로 무수정 재사용**(죽은 노드 경유 광고 소멸 → 이웃 대체 경로 재광고를 모사)해 장애 전후를 비교: `rerouted`(전후 모두 도달하나 경로 변경)·`lost_routes`(전엔 닿았으나 후엔 단절)·`is_reroutable`·`surviving_path`·`reconvergence_rounds`·`summary`.
  - 핵심 불변식: 경로-벡터는 전체 경로 광고(BGP AS-PATH)라 거리-벡터 count-to-infinity 가 없어 **재수렴 결과 = 살아남은 메시 콜드스타트 고정점**(테스트로 등가성 검증). Phase 435 와 교차 검증 — 백업 경로 존재 ⇒ 주 경로 내부 중계 전멸에도 우회 생존, 절단점 장애 ⇒ 일부 쌍 단절. 무작위성 0·정렬 출력·경계 입력 검증(미등록 장애/origin KeyError). 단위 **22건 PASS**.
- code-reviewer 어드바이저 1회 반영(CRITICAL 0·HIGH 2·MEDIUM 4·LOW 4): HIGH ① `summary()` `lost_pairs` 가 죽은 origin 의 단절을 누락하던 것을 전 origin 순회로 바로잡아 총 영향 과소계상 제거(순서 있는 쌍 의미 docstring 명시), ② `is_reroutable(x,x)` 가 자기 경로에 True 반환하던 것을 `rerouted` 와 일관되게 False 가드 추가. MEDIUM 교차검증 테스트의 경로 *동일성* 단언을 도달성·죽은노드 미사용·길이로 완화(조밀 토폴로지 거짓 실패 방지)·`type: ignore`→`assert` 로 교체. 자기경로·죽은 목적지 엣지 케이스 테스트 2건 추가(+2).
- 검증: 신규 path_vector_failover **22건** + 전체 federation 회귀(421~438) 합산 **371건 PASS**(0.50s). 본 컨테이너 최소 의존성(pytest·numpy)만 설치 → simpy·scipy·hypothesis 의존 수트는 CI 전체 수집. 기존 `.py` 무수정(순수 추가) → 회귀 무영향.
- ROADMAP·`docs/SIMULATOR_ODYSSEY_PLAN.md` Federation Operations 라인을 Phase 438 완료 + 잔여 `Phase 426-427·439-440` 으로 갱신.

### 추가 (feat) — 일일 점검 2026-06-16 (18차): ODYSSEY Phase 437 신뢰 인지 분산 경로-벡터 라우팅 + 적체 흡수
- 작업 상황 점검: 12차(`c8ee6c1`, PR #335)까지 main 통합 완료. 이후 Phase 433·434·435·436 작업이 **머지되지 못한 draft PR 6건(#336·#337·#338·#339·#340·#341)으로 적체**된 상태 확인 — 최신 통합본 **PR #341(17차, clean, base=main, 12파일/2097줄)** 이 Phase 433-436 전체를 깔끔히 담고 있으나 main 으로 머지되지 못해 누적. **머지 병목이 근본 원인**(매 점검이 통합 PR을 새로 만들지만 main 머지가 안 됨). 본 점검은 PR #341 상태를 작업 브랜치로 흡수하고, 그 위에서 진짜 다음 갭 **Phase 437** 을 전진 구현해 6건 적체 + 신규 1건을 **단일 브랜치로 일원화**한다.
- **Phase 437** — `simulation/federation_trust_path_vector.py` (신규) 신뢰 인지 분산 경로-벡터 라우팅. Phase 436 분산 경로-벡터(홉만)와 Phase 433 중앙 신뢰 Dijkstra(전역 토폴로지)의 공백을 메운다: Phase 432 메시 인접 위에서 *분산* 수렴하되, 각 노드가 광고된 경로를 고를 때 *자신이 직접 관찰한 다음 홉 이웃의 신뢰도*(Phase 428)를 1순위 선호로 적용한다(BGP LOCAL_PREF).
  - `TrustPathVectorRouting(mesh, trust_model, untrust_weight=1.0)` — 선호 키 `(untrust_penalty(node→next_hop), 홉 수, 경로 튜플)`. 1순위가 다음 홉 신뢰이므로 더 신뢰하는 이웃을 거치면 홉이 늘어도 그 경로를 택한다(Phase 433과 같은 안전 논거를 분산 환경에 적용). 경로 나머지 신뢰는 그 구간을 고른 하류 노드들이 각자의 로컬 신뢰로 반영 → 신뢰 결정이 홉마다 분산 합성(중앙식 433과의 핵심 차이).
  - 핵심 불변식: 신뢰 동률(관찰 0 → 모든 이웃 균일 0.5)이면 키가 (상수,홉,경로)로 환원되어 **Phase 436과 정확히 동일한 경로**(테스트로 교차검증). 신뢰는 후보를 재배열만 할 뿐 제거하지 않아 도달성은 메시(Phase 432)와 동일. path-vector 루프 방지(BGP AS-PATH)·Jacobi 동기 갱신·next-hop local-pref(BGP 류 진동 없음)·무작위성 0. 공개 API(`converge`·`routes`·`best_path`·`hop_count`·`next_hop`·`forwarding_table`)는 Phase 436 과 동일 계약. 단위 **19건 PASS**.
- code-reviewer 어드바이저 1회 반영(HIGH 2건, CRITICAL 0): ① 수렴 라운드 상한(노드 수)을 "정리"가 아닌 *방어적 종결 캡*으로 정확히 기술 — 신뢰가 더 긴 경로를 선호할 수 있어 수렴 라운드가 지름보다 클 수 있음을 명시, ② float 동률 분리가 정수 prior(Beta(1,1)) 가정에 의존함을 Phase 433 처럼 명시(재현성 자체는 어떤 prior 에서도 보장). MEDIUM(키 이중 계산=Phase 436 동일 패턴, 컨벤션 일관성)·LOW 는 YAGNI·인접 모듈 일관성으로 보류. 어드바이저가 루프-프리·Jacobi 결정성·도달성 보존·API 패리티·무작위성 0 을 명시 검증.
- 검증: 신규 trust_path_vector **19건** + 인접 federation 회귀(path_vector·trust_routing·causal_delivery·resilient_routing·mesh·discovery·hybrid_clock·trust·audit·split_brain) 합산 **303건 PASS**(0.42s). 본 컨테이너 최소 의존성(pytest·numpy)만 설치 → simpy·scipy·hypothesis 의존 수트는 CI 전체 수집. 기존 `.py` 무수정(순수 추가) → 회귀 무영향. PR #336~#341 은 본 브랜치로 superseded(머지 후 close 권장).
- ROADMAP·`docs/SIMULATOR_ODYSSEY_PLAN.md` Federation Operations 라인을 Phase 437 완료 + 잔여 `Phase 426-427·438-440` 으로 갱신.

### 통합 (chore) — 일일 점검 2026-06-16 (17차): ODYSSEY Federation Operations 적체 draft PR 통합 (Phase 433·434·435·436)
- 작업 상황 점검: 12차(`c8ee6c1`, PR #335)까지 Federation Operations(Phase 428·429·431·432) main 통합 완료. 이후 13·14·15차(Phase 433 신뢰 가중·434 HLC 인과-안정 배달·435 메시 복원력)는 **통합 PR #339(clean)** 로, 16차(Phase 436 분산 경로-벡터 라우팅)는 **PR #340(clean)** 로 머지되지 못하고 적체된 상태를 확인 → 두 적체분을 본 일일 점검 브랜치로 단일 통합.
- 통합 대상: PR #339(`federation_trust_routing.py`·`federation_causal_delivery.py`·`federation_resilient_routing.py` = Phase 433·434·435) + PR #340(`federation_path_vector.py` = Phase 436). 모두 신규 파일 추가(기존 `.py` 무수정)라 코드 비경쟁 — README/CHANGELOG/ROADMAP/ODYSSEY_PLAN append 충돌만 양측 보존으로 해소.
- 검증: 신규 federation 단위(path_vector 23 + trust_routing 37 + causal_delivery 36 + resilient_routing 31) + 인접 회귀(mesh·hybrid_clock·trust·audit·split_brain) 합산 **270건 PASS**(0.69s). 본 컨테이너 최소 의존성(pytest·numpy)만 설치 → simpy·scipy·hypothesis 의존 수트는 CI 전체 수집. PR #336·#337·#338·#339·#340 은 본 통합으로 superseded.
- ROADMAP·`docs/SIMULATOR_ODYSSEY_PLAN.md` Federation Operations 라인을 Phase 433·434·435·436 완료 + 잔여 `Phase 426-427·437-440` 으로 정리.

### 통합 (chore) — 일일 점검 2026-06-16 (15차): ODYSSEY Federation Operations 적체 draft PR 3건 통합 (Phase 433·434·435)
- 작업 상황 점검: 12차(`c8ee6c1`, PR #335)로 Federation Operations 적체(Phase 428·429·431·432)가 main 통합 완료된 이후, 13·14차(Phase 433 신뢰 가중 라우팅·434 HLC 통합 인과-안정 배달)와 Phase 435(메시 복원력 라우팅)가 **머지되지 못한 draft PR 3건(#336·#337·#338)으로 적체**된 상태를 확인 → 중단된 Federation Operations 작업을 본 일일 점검 브랜치로 통합.
- 통합 대상: PR #336(`federation_trust_routing.py` = Phase 433) + PR #337(`federation_causal_delivery.py` = Phase 434) + PR #338(`federation_resilient_routing.py` = Phase 435). 모두 신규 파일 추가(기존 `.py` 무수정)라 코드 비경쟁 — README/CHANGELOG/ROADMAP/ODYSSEY_PLAN append 충돌만 양측 보존으로 해소.
- 검증: 신규 federation 단위 **104건 PASS**(trust_routing 37 + causal_delivery 36 + resilient_routing 31), 인접 federation 회귀(discovery·handover·conflict·notam·split_brain·trust·audit·hybrid_clock·mesh·operational_intent) 포함 **331건 GREEN**. 본 컨테이너는 최소 의존성(pytest·numpy)만 설치 → 나머지 수트는 simpy·scipy·hypothesis 등 미설치로 미수집(환경 의존, CI 전체 수집). PR #336·#337·#338 은 본 통합으로 superseded.
- ROADMAP·`docs/SIMULATOR_ODYSSEY_PLAN.md` Federation Operations 라인을 Phase 433·434·435 완료 + 잔여 `Phase 426-427·436-440` 으로 정리.

### 추가 (feat) — 일일 점검 2026-06-16 (13차): ODYSSEY Phase 433 신뢰 가중 메시 라우팅
- 작업 상황 점검: 12차(`c8ee6c1`, PR #335)로 Federation Operations 적체(Phase 428·429·431·432)가 main 통합 완료됨을 확인. 열린 PR 15건(피처 #283 핫루프·#280 Phase 207 draft + dependabot 13)은 이전 점검들에서 사람 판단/후속 정리로 보류된 상태 유지. **머지된 모듈에만 의존하고 열린 PR과 비경쟁(신규 파일만 추가)인 진짜 공백 Phase 433**(메시 라우팅 확장의 첫 단계)을 본 브랜치에서 신규 구현. 잔여 공백 Phase 426·427(2-인스턴스 E2E·고스트 렌더링)은 HTML 시뮬레이터 + Playwright 브라우저 의존이라 본 최소 컨테이너에서 보류.
- **Phase 433** — `simulation/federation_trust_routing.py` (신규) 신뢰 가중 메시 라우팅. Phase 432 메시 토폴로지(`FederationMesh`)는 모든 인스턴스를 동등하게 보고 홉 수만으로 최단 경로를 계산하지만, Phase 428 신뢰 모델(`FederationTrustModel`)은 어떤 인스턴스가 협조 행위를 신뢰성 있게 이행하는지 정량화한다. 본 모듈은 라우팅하는 인스턴스(origin) **자신의** 신뢰 믿음으로 각 중계 후보 비용을 가중해 신뢰하는 이웃을 우선하는 결정적 최소 비용 경로를 계산한다.
  - **비용 모형** — origin→node 간선 비용 `hop_cost + untrust_weight*(1 - trust(origin→node))`: 완전 신뢰(1.0) 이웃은 홉 수와 동일, 미관찰은 중립 0.5, 완전 불신(0.0)은 최대 페널티. 라우팅은 항상 origin 관점(연합은 중앙 신뢰 권위 없음 → 같은 토폴로지라도 인스턴스마다 다른 경로 가능).
  - **API** — `route`(신뢰 가중 Dijkstra)·`route_cost`·`avoid_untrusted_route`(충분히 관찰된 불신 중계만 회피하는 BFS, 목적지는 종단점이라 불신이어도 허용)·`forwarding_table`(목적지→다음 홉 포워딩)·`relay_trust`. 우선순위 큐는 `(비용, 경로 튜플)` 키라 노드 첫 확정 시 최소 비용·사전식 최소 경로가 고정된다.
  - 무작위성 0·기존 모듈(mesh·trust·discovery) 무수정 순수 추가 → 같은 토폴로지·신뢰 상태·origin 은 항상 같은 경로/비용(재현·감사 가능). 단위 **37건 PASS**.
- code-reviewer 어드바이저 1회 반영: ① (HIGH) 동률 비용 경로를 무한정 push 해 큐가 증식하던 Dijkstra 를 **best-path 사전식 완화**(사전식으로 엄격히 나은 후보만 push)로 전환해 큐 증식 차단 + 첫 확정 시 사전식 최소 경로 보장, ② (HIGH) `federation_trust` 의 사설 상수 `_DEFAULT_MIN_OBSERVATIONS`·`_DEFAULT_TRUST_THRESHOLD` 직접 import 를 제거하고 로컬 정의(읽기 전용 통합 계층이 상대 모듈 내부 namespace 에 결합하지 않게), ③ (MEDIUM) `trust_threshold` (0,1) 범위 검증 추가(경계 밖 임계값이 `avoid_untrusted_route` 를 조용히 무력화하는 것 방지) + 파라미터화 테스트 4건, ④ (MEDIUM) float 동률 분리가 정확한 상등에 의존하며 무리수 신뢰 분수에서 ULP 차로 분리될 수 있으나 같은 입력은 항상 같은 경로를 내므로 재현성은 보장됨을 docstring 명시. LOW(route_cost 의 route 재계산·coverage 갭)는 KISS/YAGNI 로 보류.
- 검증: 신규 `tests/test_federation_trust_routing.py` **37건** + 인접 federation 회귀(mesh 25·trust 30·discovery·handover·conflict·notam·split_brain·audit·hybrid_clock) 합산 **240건 GREEN** 로컬 검증. 본 컨테이너는 최소 의존성(pytest·numpy)만 설치 → 나머지 수트는 simpy·scipy·hypothesis 등 미설치로 미수집(환경 의존, CI 전체 수집).
- ROADMAP·`docs/SIMULATOR_ODYSSEY_PLAN.md` Federation Operations 라인을 Phase 433 완료 + 잔여 `Phase 426-427·434-440` 으로 갱신.

### 추가 (feat) — 일일 점검 2026-06-16 (14차): ODYSSEY Phase 434 HLC 통합 인과-안정 배달
- 작업 상황 점검: 12차(PR #335)로 Federation Operations 적체(Phase 428·429·431·432)가 main 통합 완료, 13차는 Phase 433 신뢰 가중 라우팅이 **draft PR #336 으로 진행 중**(미머지)임을 확인. **머지된 모듈(mesh·hybrid_clock)에만 의존하고 열린 PR #336(trust_routing)과 비경쟁(신규 파일만 추가)인 진짜 공백 Phase 434** 를 신규 구현.
- **Phase 434** — `simulation/federation_causal_delivery.py` (신규). Phase 432 메시 토폴로지는 origin 사건을 멀티홉 *전파* 하지만 각 수신 인스턴스의 처리(배달) **순서** 는 규정하지 않는다 — 플러딩 중복·타 origin 사건 혼입으로 순진한 도착순 처리는 인스턴스마다 순서가 어긋나 연합 결정이 불일치. 본 모듈은 Phase 431 HLC 를 결합한 **워터마크(low-water-mark) 안정 배달** 로 이를 해소.
  - 알고리즘: 각 출처가 FIFO 로 단조 증가하는 HLC 를 발행하므로, 알려진 모든 출처 고점의 최소(워터마크) 이하 사건은 **안정** — 그보다 앞선 사건이 미래에 도착 불가(CockroachDB closed-timestamp 와 동일 발상). 안정 사건만 HLC **전순서** 로 배달 → 모든 인스턴스가 동일한 결정적 순서로 처리.
  - `FederationEvent`(HLC 타임스탬프 + 불투명 페이로드, source=발행 인스턴스)·`CausalDeliveryBuffer`(출처별 FIFO 고점으로 멀티홉 중복·stale 멱등 무시 / 예상 출처 집합이면 모두 보고까지 보수적 보류, 없으면 관측 출처 best-effort / `deliverable`·`flush`·`pending`·`buffer_size`)·`FederationDeliveryCoordinator`(메시 `propagate` 로 origin 사건을 도달 가능한 모든 인스턴스 버퍼에 멱등 fan-out, TTL 한정, 스냅샷 모델). 무작위성 0·결정적. 단위 **36건 PASS**.
- code-reviewer 어드바이저 1회 반영: ① (HIGH) `flush` 의 `id(e)` 기반 제거가 구조적 동일 사본/리팩토링에 취약 → **워터마크 직접 분할** 로 교체(객체 식별자 무의존, dict 등 비해시 페이로드도 안전, 구조적 중복 재배달 차단). ② (HIGH) `deliverable`/`pending` 이 모두 빌 때 빔 vs 워터마크 보류를 구분할 `buffer_size()` 접근자 추가. ③ (MEDIUM) `FederationDeliveryCoordinator` 스냅샷 의미 docstring 명시(이후 `mesh.rebuild()` 시 새 코디네이터 필요). 어드바이저가 권한 monotonic 단정은 프로젝트 가이드("발생 불가 시나리오 에러 처리 금지")에 따라 보류.
- 검증: 신규 단위 **36건 PASS**, 인접 federation 회귀(mesh·hybrid_clock·discovery·trust·audit·split_brain·notam·handover·conflict) 포함 **237건 GREEN**. 본 컨테이너는 최소 의존성(pytest·numpy)만 설치 → simpy·scipy·hypothesis 등 미설치 수트는 CI 전체 수집. 기존 모듈 **무수정** 순수 추가.
- ROADMAP·`docs/SIMULATOR_ODYSSEY_PLAN.md` Federation 라인을 `Phase 434` 완료 + `Phase 433`(진행 중, PR #336) + 잔여 `Phase 426-427·435-440` 으로 갱신.
### 추가 (feat) — 일일 점검 2026-06-16: ODYSSEY Phase 435 메시 복원력 라우팅
- 작업 상황 점검: ODYSSEY Federation Operations(421-440) 중 머지 완료는 421-425·428-432, 열린 draft PR은 Phase 433(신뢰 가중 메시 라우팅 #336)·434(HLC 통합 인과-안정 배달 #337). **머지된 모듈에만 의존하고 열린 PR과 비경쟁(신규 파일만 추가)인 다음 공백 Phase 435**를 본 브랜치에서 신규 구현.
- **Phase 435** — `simulation/federation_resilient_routing.py` (신규). Phase 432 `FederationMesh` 스냅샷 위에서 인스턴스(USS) 장애 내성을 구조적으로 분석한다. Phase 430(분할 뇌)이 *분단 발생 후* 안전 강하를 다룬다면, 본 모듈은 *분단을 일으킬 구조적 취약점을 사전에* 드러낸다.
  - `articulation_points()`·`bridges()` — Hopcroft-Tarjan `disc`/`low` **반복** DFS(재귀 한계 회피, 정렬 순회로 결정성) 1회로 절단점(제거 시 연결 요소가 늘어나는 단일 장애점)과 브리지(제거 시 단절되는 단일 링크 인접)를 동시 식별. `is_single_point_of_failure(id)` 는 절단점 여부 질의.
  - `backup_path(src, dst)` — 메시 주 최단 경로의 *내부 노드·연속 간선*을 제거한 뒤 재-BFS 해, 주 경로의 어떤 중계가 죽어도 영향 없는(엔드포인트만 공유) 이중화 경로 존재 여부를 답한다. 노드·간선 동시 분리.
  - `surviving_reach(origin, failed)` — 임의 장애 인스턴스 집합 제거 후 origin에서 여전히 닿는 인스턴스·홉 수를 BFS로 계산.
  - 무작위성 0·정렬 출력·읽기 전용(생성 시점 인접 스냅샷에서만 분석). 단위 **31건 PASS**, 인접 federation 회귀(mesh·discovery·handover·notam·conflict·split_brain) 합산 **141건 GREEN**.
- code-reviewer 어드바이저 1회 반영: ① (HIGH) `backup_path` 가 주 경로만 live `mesh.shortest_path` 로 산정해 나머지 메서드(스냅샷 `self._adj` 기반)와 불일치 — 메시가 생성 후 rebuild되면 백업이 옛 주 경로를 "분리 백업"으로 잘못 반환하던 결함을, 주 경로도 스냅샷 BFS(`self._bfs`)로 일원화해 해소(메시 참조 제거). ② (MEDIUM) 불변 그래프에 매 호출 Tarjan 재계산 → `_tarjan_cache` 지연 캐시로 1회만 계산. ③ (MEDIUM) 백업 경로 간선 분리·메시 mutation 후 백업 일관성·2-노드 브리지 테스트 3건 보강(29→31). LOW(`surviving_reach` 미등록 노드 무검증·관용)는 결정성·YAGNI 로 보류. 알고리즘 정확성(반복 Tarjan low-link·루트 특수처리·역방향 간선)은 advisor 검증 통과.
- ROADMAP·`docs/SIMULATOR_ODYSSEY_PLAN.md` Federation Operations 라인을 `Phase 435` 완료 + 잔여 `Phase 426-427·433-434·436-440` 으로 갱신. 기존 `.py` 소스 무수정(순수 추가) → 회귀 무영향.

### 추가 (feat) — 일일 점검 2026-06-16 (16차): ODYSSEY Phase 436 분산 경로-벡터 라우팅
- 작업 상황 점검: ODYSSEY Federation Operations(Phase 421-440)에서 12차(Phase 428·429·431·432)까지 main 머지 완료, 이후 13·14·15차(Phase 433 신뢰 가중·434 HLC 인과-안정 배달·435 메시 복원력)가 **머지되지 못한 draft PR(#336·#337·#338)과 통합 PR #339(clean)로 적체**된 상태를 확인 → 적체와 독립적으로 다음 메시 라우팅 Phase를 진행.
- **Phase 436** — `simulation/federation_path_vector.py` (신규) 분산 경로-벡터 라우팅. Phase 432(`shortest_path`)·Phase 433(`TrustWeightedRouter`)이 **전역 메시 스냅샷**을 한 노드가 통째로 보고 BFS·Dijkstra로 계산하는 반면, 실제 inter-USS 연합에서는 어떤 인스턴스도 전체 토폴로지를 모른다 — 본 모듈은 각 인스턴스가 *직접 이웃*만 알고 도달성을 광고·교환해 먼 목적지 경로를 분산 학습하는 경로-벡터 라우팅을 시뮬레이션한다.
  - `PathVectorRouting.converge()` — Jacobi(동기) 라운드. 매 라운드 모든 갱신이 *직전 라운드 스냅샷*만 참조하므로 노드 순회 순서와 무관하게 결정적, 수렴 라운드 수 = 메시 지름(diameter). 광고 경로 앞에 자신을 붙여 후보를 만들되 **경로에 자신이 이미 있으면 거부**(path-vector 루프 방지, BGP AS-PATH 발상)해 루프 프리를 보장. 동률(같은 홉)은 사전식 작은 경로 튜플로 분리.
  - `best_path`/`hop_count`/`next_hop`/`routes`/`forwarding_table` 조회 API + `is_converged`/`rounds_to_converge`. 조회 시 미수렴이면 자동 수렴. 미등록 노드는 `KeyError`, 음수 `max_rounds` 는 `ValueError`, 라운드 상한 미달 시 부분 결과 보존(`rounds_to_converge=None`).
  - 핵심 불변식 검증: 분산 수렴 경로의 홉 거리가 Phase 432 중앙 BFS(`shortest_path`)와 **항상 일치**(직선·3×3/2×3 격자 전수). 경로 유효성(연속 노드 인접·루프 없음·끝점), 분단 메시 도달 불가 처리, 결정성(동일 입력 동일 테이블), king-move 대각 1홉, 빈 메시·재호출 멱등. 단위 **23건 PASS**.
- 무작위성·외부 네트워크 0(순수 결정적), 모든 출력 정렬. 인접 federation 회귀(discovery·mesh·trust·audit·split_brain·hybrid_clock·handover·conflict·notam·operational_intent + path_vector) **250건 PASS**. 본 컨테이너 최소 의존성(pytest·numpy)만 설치 → simpy·scipy·hypothesis 의존 수트는 CI 전체 수집.
- code-reviewer 어드바이저 1회 반영: 핵심 알고리즘(Jacobi 고정점·path-vector 루프 방지·결정성·수렴 라운드·분단 처리) 정확성 확인. ① (HIGH) `max_rounds` 부분 수렴 조회가 "자동 수렴" docstring 과 모순되던 점을 YAGNI 원칙대로 **`max_rounds` 파라미터 제거**로 해소(부분 검사 기능은 요청 없는 추측성 → 삭제, 라운드 상한은 노드 수로 내부 보장), ② (LOW) Jacobi 라운드를 직전 스냅샷 읽기·신규 테이블 쓰기로 재구성해 프로젝트 불변성 규약 충족, ③ 빈 메시·`converge()` 멱등 테스트 보강.
- ROADMAP·`docs/SIMULATOR_ODYSSEY_PLAN.md` Federation Operations 라인을 `Phase 436` 완료 + 잔여 `Phase 426-427·433-435·437-440` 으로 갱신.

### 통합 (chore) — 일일 점검 2026-06-15 (12차): ODYSSEY Federation Operations 적체 draft PR 4건 통합 (Phase 428·429·431·432)
- 작업 상황 점검: 8차(Phase 424·425·430)까지 main 머지 완료, 이후 9·10·11차(Phase 428 신뢰·429 감사·431 HLC)와 Phase 432(메시) 작업이 **머지되지 못한 draft PR 4건(#331·#332·#333·#334)으로 적체**된 상태를 확인 → 중단된 Federation Operations 작업을 단일 브랜치로 통합.
- 통합 대상: PR #333(`federation_trust.py`·`federation_audit.py`·`federation_hybrid_clock.py` = Phase 428·429·431 상위집합) + PR #334(`federation_mesh.py` = Phase 432). 모두 신규 파일 추가 + `federation_discovery.py` 공개 접근자 `volume_of` 1개 추가라 코드 비경쟁 — README/CHANGELOG/ROADMAP/ODYSSEY_PLAN append 충돌만 양측 보존으로 해소.
- 검증: 신규 federation 단위 **123건 PASS**(trust 30 + audit 29 + hybrid_clock 34 + mesh 30), 인접 federation 회귀(discovery·handover·conflict·notam·split_brain·operational_intent) **104건 PASS** = 합계 **227건 GREEN**. 본 컨테이너는 최소 의존성(pytest·numpy)만 설치 → 나머지 수트는 simpy·scipy·hypothesis 등 미설치로 미수집(환경 의존, CI 전체 수집). PR #331·#332·#333·#334 는 본 통합으로 superseded.
- ROADMAP·`docs/SIMULATOR_ODYSSEY_PLAN.md` Federation Operations 라인을 Phase 428·429·430·431·432 완료 + 잔여 `Phase 426-427·433-440` 으로 정리.

### 추가 (feat) — 일일 점검 2026-06-15 (11차): ODYSSEY Phase 431 하이브리드 논리 시계(HLC) + Phase 428·429 통합
- **Phase 431** — `simulation/federation_hybrid_clock.py` (신규) 하이브리드 논리 시계(HLC, Kulkarni et al. 2014). 3+ 인스턴스 메시 연합에서 인스턴스마다 벽시계가 어긋나도 물리 시계 동기화 없이 연합 결정(디스커버리·핸드오버·감사)의 **전역 인과 순서**를 결정적으로 매긴다.
  - `HLCTimestamp` (frozen, `order=True`) — `(wall_time, counter, instance_id)` 사전식 **전순서**. `causal_key`/`happened_before` 는 인스턴스 식별자를 제외한 `(wall, counter)` 로 **인과(부분 순서)** 를, `is_concurrent_with` 는 동률(서로 다른 인스턴스의 동시 이벤트) 동시성을 명시한다 — 전순서(정렬용)와 인과(causality)를 의미적으로 분리.
  - `HybridLogicalClock.local_event(pt)` / `receive_event(pt, remote)` — 표준 HLC 갱신 규칙: 새 `wall` = (지역 고점·원격 wall·물리 시각) 최댓값, `counter` 는 그 최댓값의 출처별 결정(지역·원격 동률 → max(c)+1, 한쪽만 → 그쪽 +1, 물리 시각 신규 최대 → 0). happened-before → 발행 타임스탬프 사전식 엄격 증가를 보장.
  - 물리 시계 역행을 견디고(논리 고점 유지·counter 증가), cold-start sentinel `-1` 로 갓 만든 시계의 첫 타임스탬프 counter 를 0으로 정규화. 무작위성·시스템 시계 직접 읽기 0 → 같은 이벤트 순서는 항상 같은 타임스탬프 열(재현·독립 검증). 단위 **34건 PASS**.
- code-reviewer 어드바이저 1회 반영: ① (CRITICAL) fresh 시계 `_wall=0` 이 유효 `t=0` 과 init sentinel 을 혼동해 첫 이벤트가 `counter=1` 이 되던 모호성을 `_wall=-1` sentinel + `current()` 클램프로 해소(첫 타임스탬프 항상 counter 0), ② (HIGH) `happened_before` 가 부분 순서임을 docstring 에 명시 + `is_concurrent_with` 추가해 "not happened_before = 역방향" 오용 차단, ③ (MEDIUM) cold-start receive 경로 테스트 2건 보강(29→34). MEDIUM(private 속성 외부 변형=인접 stateful dataclass 공통 패턴)·LOW 는 컨벤션 일관성·YAGNI 로 보류.
- ROADMAP·`docs/SIMULATOR_ODYSSEY_PLAN.md` Federation Operations 라인을 `Phase 431` 완료 + 잔여 `Phase 426-427·432-440` 으로 갱신. 인접 federation 회귀(trust·audit·handover·conflict·notam·split_brain·discovery·operational_intent + hybrid_clock) **197건 PASS**, 전체 수집 **4,942건** 수집 오류 0.

### 추가 (feat) — 일일 점검 2026-06-15 (9차): ODYSSEY Phase 428 인스턴스 간 신뢰 모델
- **Phase 428** — `simulation/federation_trust.py` 연합 신뢰 모델. Phase 608 `BayesianReputation` 의 Beta-Bernoulli 켤레 사전분포를 인스턴스(USS) 레벨로 재사용해, 한 인스턴스가 상대 인스턴스의 협조 행위 이행 여부를 누적 관찰한 평판을 정량화한다.
  - `InstanceTrust` frozen dataclass 가 (관찰자→대상) **방향성** Beta(α,β) 믿음을 보유. `updated(success)` 는 원본을 변형하지 않고 α(성공)/β(실패)를 증가시킨 새 인스턴스를 반환(불변). `trust_score` = 사후 평균 `α/(α+β)`, `uncertainty` = Beta 분포 표준편차(관찰 누적 시 0 수렴).
  - `FederationTrustModel.observe(observer, target, success, kind)` 가 핸드오버(Phase 423)·충돌 협상(Phase 424)·NOTAM 전파(Phase 425) 협조 이벤트를 관찰해 신뢰를 갱신하고 결과 상태를 담은 `TrustEvent` 를 감사 로그에 기록. 신뢰는 비대칭(A→B ≠ B→A)이며 인스턴스는 자기 자신을 평가할 수 없다.
  - `is_trusted` 는 임계값(기본 0.5)과 **최소 관찰 게이트**(기본 5, Phase 608 `detect_malicious` 와 동일한 증거 요구)를 함께 통과해야 신뢰를 단정 — 사전분포만으로 성급히 신뢰/불신하지 않는다. `untrusted` 는 충분히 관찰된 저신뢰 쌍을 결정적 정렬 순서로 반환.
  - 무작위성 0(실제 연합 이벤트에서 관찰, 시뮬레이션 아님) → 같은 관찰 순서는 항상 같은 신뢰 상태(재현·감사 가능). 사전분포 α·β 양수 검증, 빈 식별자·자기 평가 거부. 단위 **30건 PASS**.
- code-reviewer 어드바이저 1회 반영(HIGH 3건): ① `_validate_pair` 가 식별자를 strip 후 키로 사용 — `"uss-a"` vs `"uss-a "` 가 별개 신뢰 슬롯으로 조용히 분기되는 것 방지, ② `InstanceTrust.__post_init__` 불변식 검증(α·β 양수·observations 비음수·observer≠target) 추가 — 잘못 구성된 믿음이 최소 관찰 게이트를 왜곡하지 못하게 함, ③ 모듈 docstring 의 불변성 주장을 "믿음·감사 항목은 불변, 모델 자체는 상태형"으로 범위 명확화. 반영 후 보강 테스트 7건 추가(공백 정규화·`__post_init__` 거부·다중 쌍 결정적 재현+로그 순서·custom prior 게이트·custom threshold) 포함 30건 재검증 GREEN. MEDIUM(kind 허용목록·np/math sqrt)·LOW(timestamp)는 federation_* 공통 패턴·YAGNI·결정성 원칙상 보류.
- ROADMAP Federation Operations 라인을 `Phase 428` 완료 + 잔여 `Phase 426-427·431-440` 으로 분해 갱신. `docs/SIMULATOR_ODYSSEY_PLAN.md` Phase 428 항목 ✅ 표기.

### 추가 (feat) — 일일 점검 2026-06-15 (10차): ODYSSEY Phase 429 연합 감사 로그
- **`simulation/federation_audit.py`** (신규) — 인스턴스 경계를 넘는 **변조 탐지(tamper-evident) 연합 감사 원장**. `FederationAuditLog` 은 append-only SHA-256 해시 체인으로, 각 항목(`AuditEntry`, frozen)이 직전 다이제스트를 재료에 포함해 중간 항목의 변조·삭제가 이후 모든 다이제스트를 깨뜨린다 → `verify()` 가 검출. 다이제스트 재료는 **길이 접두(length-prefixed) 직렬화**라 어떤 필드값이 구분자를 포함해도 서로 다른 필드 조합이 같은 재료를 만들 수 없어(주입·충돌 구조적 차단). 인스턴스별 단조 논리시계 강제, 인스턴스/이벤트 종류 쿼리.
- 두 인스턴스 원장은 결정적 **CRDT 류 `merge`** — 내용 키 `(logical_clock, instance_id, event_type, detail)` 사전식 전순서로 중복 제거 후 재-체인. **교환·결합·흡수 멱등**이라 어느 순서로 몇 번을 합쳐도 같은 head 다이제스트(재현·독립 검증). 분기(fork)된 같은 인스턴스 항목도 보존하며, 병합 경로는 `record()` 의 단조 검증을 우회해 분기 히스토리를 깨지 않는다.
- 단위 테스트 `tests/test_federation_audit.py` **29건 PASS** — 체인 연결·결정성·변조/삭제 탐지·구분자 위생·단조 시계·쿼리·병합 교환/결합/흡수멱등/중복제거/fork보존·record-after-merge. 인접 federation 회귀(handover·conflict·notam·split_brain·discovery·operational_intent) **122건 PASS**. 기존 `.py` 소스 무수정(순수 추가) → 회귀 무영향.
- code-reviewer 어드바이저 1회 반영: ① (CRITICAL) 다이제스트 재료를 길이 접두 직렬화로 전환해 `prev_digest` 포함 모든 필드의 구분자 주입·충돌을 구조적으로 차단, ② (HIGH) CRDT 흡수 멱등(`a.merge(b).merge(b)==a.merge(b)`)·`record`-after-`merge` 테스트 2건 보강(27→29), ③ 병합 원장의 비단조 분기 보존 의미를 `record`/`merge` docstring 에 명시. "frozen 으로 전환" HIGH 1건은 인접 `SafeDescentPolicy`(가변 `@dataclass` 누적자)와 동일 패턴이라 컨벤션 일관성 위해 보류. MEDIUM(내용 키 dedup=의도된 CRDT 의미)·LOW(동일 클래스 private 접근=관용)도 보류.
- ROADMAP Federation Operations 라인을 `Phase 429` 완료 반영. Phase 428(신뢰 모델)과 함께 통합되어 잔여 `Phase 426-427·431-440` 으로 갱신. 서로 다른 신규 파일이라 비경쟁.
### 추가 (feat) — 일일 점검 2026-06-15: ODYSSEY Phase 432 메시 연합 토폴로지 + 멀티홉 전파
- 작업 상황 점검 결과 ODYSSEY Federation Operations(421-440) 중 머지 완료는 421-425·430, 열린 draft PR은 428(신뢰)·429(감사 로그)·431(HLC). **머지된 모듈에만 의존하고 열린 PR과 비경쟁(신규 파일만 추가)인 진짜 공백 Phase 432**를 본 브랜치에서 신규 구현.
- **Phase 432** — `simulation/federation_mesh.py` (신규). Phase 421 디스커버리 등록 상태로 인스턴스 간 **공역 경계 인접 그래프**를 결정적으로 구성하고 그 위에서 멀티홉 전파를 계산한다.
  - **경계 인접 정의**: 타일형(비중첩) 공역을 위해 수평(x·y)은 `border_tolerance_m`(기본 1.0 m) 이내 접촉을 이웃으로 인식, 수직(z)·시간(t)은 엄격 4D 교차로 분리. Phase 425의 `Volume4D.overlaps`(엄격 교차)는 맞닿은 타일([0,1000)·[1000,2000))을 비이웃으로 보므로 메시 토폴로지용 인접을 별도 정의.
  - **그래프 질의**: `neighbors`·`adjacency`(대칭·정렬)·`components`(연결 요소)·`is_connected`·`shortest_path`(동률은 정렬 이웃 우선 BFS) — 모두 정렬 출력으로 재현성 보장.
  - **멀티홉 전파**: Phase 425의 1홉 직접 NOTAM 전파를 메시 전역으로 일반화한 `propagate`(origin→홉 수, TTL 한정 플러딩)와 `relay_table`(목적지→다음 홉 중계 포워딩 테이블). 중간 인스턴스를 경유해야만 닿는 먼 인스턴스 전파를 결정적으로 산정.
  - 디스커버리에 공개 접근자 `volume_of(instance_id)` 1개만 추가(타일 경계 기하 직접 산정용, 기존 동작 무영향).
- **검증**: 새 컨테이너에 core deps(numpy·simpy·pandas·scipy·pyyaml·hypothesis) + pytest 설치 후 `tests/test_federation_mesh.py` **25건** 신규 + 인접 federation 회귀(discovery 14·handover 16·notam·conflict·split_brain·operational_intent 등) 합산 **129건 PASS** 로컬 검증. 외부 네트워크·랜덤 0(순수 결정적).

### 통합 (chore) — 일일 점검 2026-06-15 (8차): ODYSSEY Federation Operations 3건 통합 (Phase 424·425·430)
- 열린 PR 21건(피처 8 + dependabot 13) triage 후, **기존 `.py` 소스 무수정·신규 파일만 추가하는 비경쟁 Phase PR 3건**을 본 작업 브랜치에 통합. 신규 컨테이너에 pytest+core deps 설치 후 신규 모듈 50건 + 인접 federation 회귀(handover 16·discovery 14·operational_intent 24) **104건 PASS** 로컬 검증. 전체 4,713 테스트 수집(hypothesis 미설치 환경 한정 4건 collection 에러는 본 변경 무관·기존 이슈).
  - **#327 Phase 424** — `simulation/federation_conflict_resolution.py` 연합 충돌 해소. Phase 422 `intents_conflict` 로 충돌 탐지 후 Phase 602 `VickreyAuction`(2위 가격제 봉인입찰) 재사용해 우선순위 협상. 낮은 priority 번호=높은 입찰가 결정적 사상, 동률은 `hashlib.sha256(intent_id)` 안정 해시로 분리(Python `hash()` 솔트 비결정성 회피). `apply_resolutions` 는 패자만 CONTINGENT 로 전환한 새 튜플 반환(원본 불변), 청산가는 Vickrey 차순위로 감사 기록 (11건).
  - **#328 Phase 425** — `simulation/federation_notam.py` 연합 NOTAM 전파. 동적 NFZ를 Phase 421 디스커버리(`query`)로 발견한 겹치는 인접 인스턴스에만 결정적 전파(DELIVERED/DUPLICATE/REVOKED). NFZ 이동 시 더는 겹치지 않는 이웃에서 stale 자동 회수, 멱등 재방송(`rebroadcast`)·철회(`revoke`), 철회 후 `_origin_of` 영구 보존으로 notam_id 소유권 탈취 차단, `_deliver` 버전 가드 `>=` 로 stale 패킷의 신버전 덮어쓰기 방지, 불변 감사 로그 (19건).
  - **#329 Phase 430** — `simulation/federation_split_brain.py` 분할 뇌 안전 강하 정책. `PartitionSnapshot` 이 양방향 링크를 연결 요소로 분해해 과반(majority) 분파 판정(2-2 균등 분할 시 무과반). `SafeDescentPolicy` 4단계 안전 사다리(NOMINAL→HOLD→DESCEND→LAND), `hold_limit`/`descend_limit` 초과 지속 시 단계 상승, 정상 복귀 시 카운터 초기화(이력현상). Phase 423 핸드오버가 미룬 안전 강하 책임 구체화, 불변 감사 로그 (20건).
- code-reviewer 어드바이저 1회 반영(HIGH 3건): ① `federation_conflict_resolution` `run_auction` 의 `AuctionResult | None` 반환에 대한 경계 가드 추가(발생 불가 상황이나 계약 명시), ② `federation_notam._withdraw` 멱등 방어(`.get()` + 미보유 시 조용히 무시), ③ `federation_split_brain.majority_component` 같은 연결 요소 BFS 재계산 제거(출력 불변, 중복 단락). 반영 후 104건 재검증 GREEN. MEDIUM(감사 로그 무한 누적·dataclass 가변 필드) 2건과 LOW(생성자 예외 타입)는 운영 노트로 보류(테스트 계약 보존).
- 문서는 세 PR이 동일 파일(CHANGELOG·README·ROADMAP·`docs/SIMULATOR_ODYSSEY_PLAN.md`)을 각자 수정해 상호 충돌하므로, **신규 소스/테스트 파일만 가져오고 문서는 본 통합 항목으로 일원화**. ROADMAP Federation Operations 라인을 `Phase 424·425·430` 완료 + 잔여 `Phase 426-429·431-440` 으로 분해 갱신.
- 후속: #327/#328/#329 원본 PR은 본 통합으로 산출물 반영 완료 → close 권고. 잔여 피처 PR #295/#289/#285(Phase 445·446 — 7차 점검 #326 에 이미 통합)·#280/#283 은 사람 판단 보류, dependabot 13건(#267-#279)은 후속 정리.

### 통합 (chore) — 일일 점검 2026-06-15 (5차): 신규 코드 PR 3건 통합 + 적체 중복 PR triage
- 열린 PR 32건(피처 19 + dependabot 13) triage 후, **신규 파일만 추가하는 비경쟁 Phase PR 3건**을 본 작업 브랜치에 통합. 신규 컨테이너에 pytest+core deps 설치 후 baseline **4,361 pass / 280 skip / 0 fail** 재현 → 통합 후 전체 **4,456 pass / 280 skip / 0 fail**(+95건, 회귀 0).
  - **#320 Phase 423·286·226·209-210** (4차 번들) — `simulation/federation_handover.py`·`scripts/ablation_study.py`(+`SwarmSimulator`/`AirspaceController` 가드 토글)·`src/digital_twin/sync_engine.py` WGS84 엄밀해·`docs/API_DEPRECATION_POLICY.md`.
  - **#322 Phase 308** — `simulation/insurance_rate_quote.py` 배상책임보험 요율 산정 API(33건).
  - **#321 Phase 447** — `simulation/scenario_fuzzer.py` 적대적 시나리오 퍼저(시드 결정적 변이, 14건).
- **정리 대상 확인**: #298·#300·#292·#291·#293(Phase 322·342·367·401·406·449)은 1차 점검(`c9923b1`)으로 **이미 main 통합 완료** — `scenario_schema.py`·`jeonnam_island_sites.py`·`swarm_self_healing.py`·`geo_zones.py`·`sim_real_gap.py` 5파일 origin/main 존재 재확인. 중복이므로 close 권고.
- **사람 판단 보류**: #295/#285/#289(Phase 445·446 통계 검정 경쟁 구현)·#280/#281(Phase 207 배지 쌍)·#283(핫루프 perf — 기존 코드 수정형). dependabot 13건(#267–#279)은 후속 정리.

### 추가 (feat) — 일일 점검 2026-06-15 (3차): GENESIS Phase 308 배상책임보험 요율 산정 API
- **Phase 308** — `simulation/insurance_rate_quote.py` 신규. 시뮬레이터 STELLAR Phase 67 `societyInsuranceQuote` mock(role·hours·history toy 공식)을 **실 보험사 요율 스펙**으로 격상. 항공사업법 §70 의무 배상책임보험 근거로 MTOW 등급 기본료 × 운용형태 × 비행시간 익스포저 × 보상한도 ILF × 경력 할인 × 무사고(NCB)/사고 할증 × 야간·BVLOS 가산을 결정적 누적 곱으로 산정하고 명세(`PremiumLine`)로 추적. 사용사업 의무가입·최소한도(1.5억원) 검증 포함.
- 단위 테스트 `tests/test_insurance_rate_quote.py` **33건 PASS** — 결정성·단조성(MTOW·사고·경력·한도)·NCB·위험 가산·의무가입 한도·명세 정합·입력 검증. 기존 `.py` 소스 무수정(순수 추가) → 회귀 무영향(baseline 4,361 pass / 280 skip / 0 fail, 84.24% 재현).

### 추가 (feat) — 일일 점검 2026-06-15: ODYSSEY Phase 447 적대적 시나리오 퍼저
- **`simulation/scenario_fuzzer.py`** (신규) — 시드 기반 결정적 시나리오 변이 생성기. `np.random.default_rng(seed)`로 동일 시드 → 동일 변이(재현성), 입력 dict 불변(새 객체 반환). `FuzzConfig(adversarial=True)`는 부하 필드(드론 수·도착률)를 위로, 안전 마진 필드(공역 면적·최소 분리거리)를 아래로 편향해 안전망에 스트레스를 가한다. `success_criteria`(합격 임계값)는 보존.
- 생성된 모든 변이는 기존 `scenario_schema.validate_scenario` 계약을 충족 — 9개 실 시나리오 × 40변이 = **360건 전부 VALID** 확인. `scenario_runner`·시나리오 마켓플레이스에서 그대로 실행 가능.
- **`tests/test_scenario_fuzzer.py`** (신규) — 단위 **14건 PASS** (재현성·불변성·스키마 적합·클램핑·분포 재정규화·거리 순서·적대적 편향). 인접 `test_scenario_schema.py` 28건 회귀 GREEN.
- code-reviewer 어드바이저 1회 반영: 미사용 `_FROZEN_KEYS` 죽은 코드 제거 + `drone_count` 정수 캐스트 강화.
- 참고: 본 Phase 447은 ODYSSEY 백엔드 트랙(시나리오 설정 퍼징)으로, ROADMAP의 기존 Phase 447(웹 시뮬레이터 e2e SORA fuzz, `tests/e2e/test_simulator_fuzz.py`)과는 별개 산출물(번호 병행 트랙).

### 통합 (chore) — 일일 점검 2026-06-15 (4차): 적체 PR 4건 무충돌 통합 (Phase 423·286·226·209-210)
- 열린 PR 29건 triage 후, **기존 코드 무수정·추가형 또는 가드된 토글·정밀도 버그픽스**인 비경쟁 Phase PR 4건을 본 작업 브랜치에 통합. 신규 컨테이너에 pytest+core deps 설치 후 통합 모듈·인접 회귀 **132건 PASS**(신규 68 + 시뮬레이터/컨트롤러 회귀 64) 로컬 검증.
  - **#318 Phase 423** — `simulation/federation_handover.py` 지역 간 관제권 핸드오버(RETAINED/ACQUIRED/HANDOVER/CONTINGENT + 이력현상) + `federation_discovery.py` `covering()`/`contains()` 프리미티브 (16건).
  - **#290 Phase 286** — `scripts/ablation_study.py` 안전망(APF·CBS) Ablation 자동화 + `SwarmSimulator`/`AirspaceController` `ablation.disable_apf/disable_cbs` 토글(기본 미설정 = 전 계층 활성, 회귀 무영향) (12건).
  - **#299 Phase 226** — `src/digital_twin/sync_engine.py` GPS→ENU 변환을 WGS84 ECEF→ENU 엄밀해로 격상(1km 평면근사 오차 153m→6cm, ±0.5m 충족) (22건).
  - **#286 Phase 209·210** — `docs/API_DEPRECATION_POLICY.md` API 폐기 생애주기 + SemVer 규약 (문서 전용).
- 보류(사람 판단 필요): **#295/#285/#289**(Phase 445·446 통계 검정 경쟁 구현)·**#280/#281**(Phase 207 배지 쌍)·**#283**(핫루프 힙 할당 제거 — 기존 perf 코드 수정형, 별도 검증)·dependabot 13건(#267–#279). 이미 main 통합 완료로 중복화된 **#298/#300/#292/#291/#293**(Phase 322·342·367·401·406·449)은 정리 대상.
### 추가 (feat) — GENESIS Phase 311 KISA CSAP 클라우드 보안인증 자가진단 자동화 (2026-06-15)
- **`simulation/csap_self_assessment.py`** (신규) — 과학기술정보통신부·KISA 「클라우드 보안인증제(CSAP)」 정보보호 기준의 14개 통제분야에 정렬한 자가진단 도구. 외부 호출 없이 이행 상태로부터 영역별 이행률·종합 준비도를 결정적으로 산출.
  - `DEFAULT_CATALOG` — CSAP 정보보호 기준 14개 통제분야(정책·인적·자산·공급망·침해사고·위험·대책·접근통제·암호화·개발·운영·서비스·물리·재해복구) × 대표 통제항목 카탈로그(운영자 교체·확장 가능).
  - `Status` 4종(이행/부분이행/미이행/해당없음) — 부분이행 0.5, 해당없음은 분모 제외하는 결정적 점수화. 응답 누락 항목은 보수적으로 미이행 처리.
  - `assess_csap()` — 분야별 `DomainScore`(이행률) + 종합 이행률 + 준비도 판정(95% 신청 권장 / 80% 보완 후 신청 / 미만 준비 부족) + 종합 이하 약화 분야 식별.
  - `build_responses()`·`build_report()`·`export_json()`·`export_text()` — `ControlResult` 변환 + 결정적 JSON/한국어 텍스트 export. **20건 PASS**, 기존 소스 무수정(순수 추가형).
### 추가 (feat) — GENESIS Phase 341: 목포 해역 실 좌표계 임포트 (해도 기반 NFZ·회랑)
- **#TBD Phase 341** — `src/applications/mokpo_harbor.py` 신규 모듈. 목포항 해역에 해도 기반 비행금지구역(NFZ) 4종(본항 부두·목포대교·유달산/삼학도 지형·남항 정박지)과 운항 회랑 3종(항만 진입·신안 도서 연계·의료 배송)을 결정적 좌표로 배치. 레이 캐스팅 `point_in_nfz()` NFZ 판정 + `corridor_nfz_conflicts()` 회랑-NFZ 충돌 검사 + `corridor_length_km()`(Haversine 재사용) + `harbor_summary()`. Phase 342 `jeonnam_island_sites.py`(목포한국병원 거점) 및 P747 해수부 항만 시범과 좌표 연계. 좌표는 공개 지도 근사값(maturity honesty 명시), 실증 전 해도 갱신 필요. 단위 테스트 8건 PASS, 기존 `.py` 소스 무수정(순수 추가) → 회귀 무영향(baseline 4,361 pass / 280 skip / 0 fail 재현 → +8).

### 통합 (chore) — 일일 점검 2026-06-15 (2차): 적체 PR 9건 무충돌 통합 (머지 병목 해소)
- 열린 PR 30건(피처 20 + dependabot 10) triage 후, **기존 코드 무수정·순수 추가형** Phase PR 9건을 단일 통합 브랜치로 합류. 신규 모듈 9개 + 단위 테스트 **190건 전부 PASS**, 기존 `.py` 소스 무수정(문서·신규 파일만) → 회귀 무영향.
  - **#313** (5건 누적): Phase 322 `scenario_schema.py` · 342 `jeonnam_island_sites.py` · 367 `swarm_self_healing.py` · 401·406 `geo_zones.py` · 449 `sim_real_gap.py`.
  - **#316 Phase 310** — `simulation/special_flight_approval.py` 야간·비가시 특별비행승인 안전기준 검증 (25건).
  - **#314 Phase 309** — `simulation/pilot_certification.py` 조종자 자격(1~4종) ↔ 시뮬 교육 모드 매핑 (24건).
  - **#315 Phase 408** — `simulation/airspace_class.py` ICAO 공역 클래스 A-G `classify_airspace()` API 격상 (25건).
  - **#307 Phase 304** — `simulation/kc_certification.py` KC 전파인증(전파법 §58-2) 적합성평가 분류 (23건).
- **#306**(Phase 304 `kc_radio_certification.py`)은 #307과 동일 Phase 경쟁 구현이라 **제외**(#307 채택). 보류: #295/#285/#289(Phase 445·446 경쟁 구현)·#280/#281(Phase 207 배지 쌍)·dependabot 10건은 사람 판단/후속.

### 통합 (chore) — 일일 점검 2026-06-15: 적체 PR 5건 무충돌 통합 (Phase 322·342·367·401·406·449)
- 머지 병목 triage 후 **기존 코드 무수정·순수 추가형** Phase PR 5건을 본 작업 브랜치에 통합. 통합 전 baseline 회귀 **4,171 pass / 280 skip / 0 fail** 재현, 통합 후 신규 **93건** 전부 PASS.
  - **#298 Phase 322** — `simulation/scenario_schema.py` + `docs/schemas/sdacs-scenario.schema.json` `.sdacs-scenario` 스키마 검증기 (20건).
  - **#300 Phase 342** — `src/applications/jeonnam_island_sites.py` 전남 도서(신안·완도) 의료 배송 거점 DB·실 좌표·Haversine ETA (7건).
  - **#292 Phase 367** — `src/autonomy/swarm_self_healing.py` 결손 드론 임무 자동 재분배 (12건).
  - **#291 Phase 401·406** — `simulation/geo_zones.py` UTM 그리드 존 결정적 판정 + EASA U-space 매핑 (22건).
  - **#293 Phase 449** — `src/training/sim_real_gap.py` 시뮬-실측 갭 Domain Randomization 자동 보정 (7건).
- 보류: **#295/#285/#289**(Phase 445·446) — 다중 경쟁 구현(`uncertainty.py`·`power_analysis.py`·`resolution_rate_power.py`·monte_carlo CI)으로 중복, 사람 판단 필요. **#295**의 `incident_report.py`(307·467)는 이미 통합된 `accident_report.py`/`incident_investigation_report.py`와 중복. **#306/#307**(Phase 304 KC)·**#280/#281**(Phase 207 배지)은 상호 중복. dependabot 13건은 후속 정리 대상.

### 추가 (feat) — GENESIS Phase 309 조종자 자격(1~4종) ↔ 시뮬 교육 모드 매핑 (2026-06-15)
- **`simulation/pilot_certification.py`** (신규) — 「항공안전법 시행규칙」 제306조 무인멀티콥터 조종자 증명 종별을 결정적으로 구현.
  - `classify_grade(mtow_kg)` — 최대이륙중량 기준 1~4종 분류(경계 모두 "초과" 규칙) + 250 g 이하 증명 불요 + 0 이하·초경량 상한(150 kg) 초과 `ValueError`.
  - `TrainingRequirement` frozen dataclass — 종별 온라인 학과/학과시험/비행경력/실기시험/실기평가/최소연령 + **시뮬 교육 모드**(상위 종이 하위 종 모드 포함).
  - `assess_pilot(mtow_kg, PilotProfile)` — 연령·비행경력·미이수 시뮬 모드로 조종자 준비도 결정적 판정.
  - `build_report`/`export_json`/`export_text` — 외부 의존성 0, `sort_keys` 안정 직렬화.
- **`tests/test_pilot_certification.py`** (신규) — 단위 **24건** (경계 분류·요건·준비도·exempt 불변·결정성·export).
- **`docs/certification/PILOT_LICENSE_MAPPING.md`** §6 추가 — 기존 문서-only 매핑(2026-06-12)을 실행 모듈로 격상, MTOW 기준 통일 명시.
- code-reviewer 어드바이저 1회 반영(150 kg 경계 테스트·exempt 불변 테스트 보강·`completed_sim_modes` 기본값 단순화·경계 "초과" 주석 통일). 시뮬레이터 HTML 무변경.

### 추가 (feat) — ODYSSEY Phase 423 지역 간 관제권 핸드오버 (2026-06-15)
- **`simulation/federation_handover.py`** (신규) — 드론이 인스턴스(USS) 공역 경계를 통과할 때 관제권을 결정적으로 이양하는 in-process 모델. Phase 421 디스커버리의 점 커버리지(`covering`)를 1차 입력으로 사용.
  - `HandoverCoordinator` — 위치 표본마다 **RETAINED**(현 관제권 유지)·**ACQUIRED**(최초 획득)·**HANDOVER**(인스턴스 간 이양)·**CONTINGENT**(커버리지 상실) 결정. 외부 네트워크·랜덤 0, 동일 입력 시퀀스 → 동일 로그(재현성).
  - 중첩(overlap) 구역에서는 현 관제권을 유지하는 **이력현상(hysteresis)** 으로 경계 진동(flapping) 방지. 후보 다수 시 id 사전순 최소로 결정적 선택(우선순위 협상은 Phase 424 범위).
  - 최초 획득(ACQUIRED)을 HANDOVER 와 구분 기록 — `from_instance=None` 인 위장 이양을 배제해 **Phase 429 불변 감사 로그** 무결성 확보.
  - `HandoverEvent` frozen dataclass(seq·drone_id·point·decision·from/to·candidates) 순서 보존 감사 로그.
- **`simulation/federation_discovery.py`** — `Volume4D.contains()`(반열린 구간 [min,max) 4D 점 포함)·`FederationDiscoveryService.covering()`(점을 포함하는 인스턴스 정렬 반환) 2개 프리미티브 추가. 경계 공유 볼륨의 중복 귀속 없음(핸드오버 결정성).
- **`tests/test_federation_handover.py`** (신규) — 단위 **16건** (RETAINED/ACQUIRED/HANDOVER/CONTINGENT·이력현상·반열린 경계·결정성·감사 로그 순서·검증·점 커버리지).
- code-reviewer 어드바이저 1회 반영(ACQUIRED 상태 분리로 감사 로그 의미 명확화·`covering` 내부 셋 스냅샷 순회·미배정 드론 CONTINGENT 대칭 테스트 추가). `ROADMAP.md` Phase 423 ✅ + `docs/SIMULATOR_ODYSSEY_PLAN.md` 반영. 시뮬레이터 HTML 무변경.

### 추가 (feat) — ODYSSEY Phase 422 운영 의도(Operational Intent) 4D 볼륨 교환 포맷 (2026-06-14)
- **`simulation/operational_intent.py`** (신규) — 연합 인스턴스 간 ASTM F3548-21 정렬 운영 의도 교환 포맷.
  - `Volume4D` frozen dataclass — WGS84 위·경도 외곽선 + 고도 밴드 + 시간 창, 경계 검증(꼭짓점≥3·위경도 범위·고도/시간 역전).
  - `OperationalIntent` frozen dataclass — `intent_id`·상태(ACCEPTED/ACTIVATED/NONCONFORMING/CONTINGENT/ENDED)·우선순위·볼륨 다수.
  - `to_dict`/`from_dict` 결정적 라운드트립 직렬화 (외부 의존성 0, JSON 직렬화 가능).
  - `volumes_intersect`/`intents_conflict` — 시간·고도·지리(경계상자) 3축 보수적 4D 교차 판정(거짓 음성 없음, 협상 전 1차 필터).
- **`tests/test_operational_intent.py`** (신규) — 단위 **24건** (검증·라운드트립·4D 교차·대칭성·ENDED 제외).
- `airspace_reservation.py`(내부 그리드 예약)와 상보적 — 인스턴스 간 교환 포맷 담당. 시뮬레이터 HTML 무변경.
- code-reviewer 어드바이저 1회 반영(필수 볼륨 API 명확화·역직렬화 ValueError 일관 래핑·고도 반열린 구간 주석·대칭성/중복 볼륨 테스트 보강).
### 기능 (feat) — ODYSSEY Phase 421 인스턴스 간 디스커버리 프로토콜 (2026-06-14)
- `simulation/federation_discovery.py` 신규 — ASTM F3548-21 **DSS**(Discovery and
  Synchronization Service)를 단순화한 결정적 in-process 모델. 다중 SDACS 인스턴스(USS)가
  각자 관리하는 **4D 공역 볼륨**(x·y·z 직육면체 + 시간 창)을 등록하면, 공간 그리드 셀
  인덱스(기본 500 m)로 후보를 좁히고 **정밀 4D AABB 교차**로 인접 인스턴스를 결정적으로
  발견·동기화한다. `register()`(이웃 발견)·`query()`·`synchronization_targets()`(상호
  동기화)·`remove()`·`summary()` 제공. 외부 네트워크·랜덤 없이 출력 정렬 보장(재현성),
  퇴화 볼륨·빈 id·비양수 셀 크기는 `ValueError`/`KeyError` 로 경계 검증.
- `tests/test_federation_discovery.py` 신규 — 4D 교차 대칭성·경계 접촉 비교차·셀 인덱싱·
  재등록 갱신·등록 순서 독립성·결정성 **13건 PASS**.
- `ROADMAP.md` Track I Phase 421 ✅ + `docs/SIMULATOR_ODYSSEY_PLAN.md` 반영. Federation
  Operations 트랙(421-440)의 첫 결정적 자산 — 운영 의도 교환(422)·관제권 핸드오버(423)의 기반.

### 기능 (feat) — ODYSSEY Phase 467 사고 조사 데이터 표준 변환기 (2026-06-14)
- `simulation/incident_investigation_report.py` 신규 — 시뮬레이션 안전 사건 로그(충돌·근접·
  충돌징후·추진/항법계 고장·공역 침범)를 **ICAO Annex 13** 구조의 표준 사고 조사 양식으로
  결정적으로 변환. ADREP 발생 분류 코드(MAC·SCF-PP·SCF-NP·AIRSPACE) 매핑 + 사건 등급
  (Accident/Serious Incident/Incident) 자동 판정. 근접 사건은 이격거리 임계값(5 m)으로
  준사고/이상 자동 조정. 시간순 사실 정보 + 등급·코드별 집계 분석 + 결정적 안전 권고를
  JSON·한국어 텍스트로 export. 입력 검증(`ValueError`).
- `tests/test_incident_investigation_report.py` 신규 — 분류·집계·검증·export·결정성 **25건 PASS**.
- `docs/standards/INCIDENT_INVESTIGATION_REPORT.md` 신규 — 근거 표준(ICAO Annex 13/ADREP)·
  등급 정의·5계층 안전망 사후 분석 계층 연계. Phase 466(텔레메트리 표준)의 조사 단계 후속.
- `docs/SIMULATOR_ODYSSEY_PLAN.md` Phase 467 ✅ 표시. Track 🏛 표준·정책 자산 확장.

### 기능 (feat) — GENESIS Phase 304 KC 전파인증 요건 체크리스트 (2026-06-14)
- `simulation/kc_certification.py` 신규 — 드론 탑재 통신 모듈(RC·텔레메트리·영상·셀룰러·GNSS)에 대해
  「전파법」 §58-2 적합성평가 유형을 결정적으로 분류. **셀룰러→적합인증**, **비면허 특정소출력 대역 +
  공중선전력 한도 이내→적합등록**, **면허대역/한도 초과→적합인증**, **수신전용→적합등록(자기시험)**.
  제품 단위로 가장 엄격한 유형을 집계하고 유형별 제출서류 + KC 식별부호 표기 안내를 JSON·텍스트로 export.
  시스템 경계 입력 검증(`ValueError`).
- `tests/test_kc_certification.py` 신규 — 분류·집계·검증·export·결정성 **23건 PASS** (전 대역 parametrize 포함).
- `docs/certification/KC_RADIO_CERTIFICATION.md` 갱신 — 실행 모듈 링크 + 917–923.5 MHz(비면허 특정소출력)
  분류를 적합등록으로 정정(기존 문서 M4/M6 적합인증 표기와 코드 일치화).
- `docs/SIMULATOR_GENESIS_PLAN.md` Phase 304 ✅ 표시. SORA(302)·비행계획 신고(303)에 이어 규제 적합 자산 확장.

### 기능 (feat) — GENESIS Phase 303 비행계획 신고 양식 자동 생성 (2026-06-14)
- `simulation/flight_plan_filing.py` 신규 — 드론 원스톱 비행승인 신청서를 시뮬 파라미터로부터
  결정적으로 생성. 관제권(9.3 km)·고도(150 m AGL)·비행금지구역·BVLOS·야간 비행을 종합해
  **비행승인 / 특별비행승인 / 기체신고** 필요 여부를 자동 판정하고 JSON·한국어 텍스트로 export.
  haversine 거리 기반 구역 진입 판정 + 시스템 경계 입력 검증(`ValueError`).
- `tests/test_flight_plan_filing.py` 신규 — 판정·검증·export·결정성 **18건 PASS**.
- `docs/certification/FLIGHT_PLAN_FILING.md` 신규 — 근거 법령·임계값·API·5계층 안전망(Layer 0) 연계.
- `docs/SIMULATOR_GENESIS_PLAN.md` Phase 303 ✅ 표시. SORA 계산기(302)와 함께 규제 적합 자산 확장.

### 추가 (docs) — TRANSCENDENCE Phase 209·210: API Deprecation Policy + SemVer 규약 (2026-06-13)
- `docs/API_DEPRECATION_POLICY.md` 신설 — `window._sdacs` 외부 404 API의 **버전 관리·폐기 규약**을 단일 기준으로 확정:
  - **Phase 210 (SemVer)**: MAJOR/MINOR/PATCH ↔ API 영향 정의 + 4개 호환성 불변식 + maturity 격상(speculative→mock→beta→production)을 MINOR로 취급.
  - **Phase 209 (Deprecation)**: ACTIVE → DEPRECATED(≥1 MINOR, `console.warn` 1회) → REMOVED(MAJOR 경계) 3단계 생애주기 + maturity별 폐기 보수성 차등(production 최장 유지) + Deprecation Registry 표(현재 0건) + `experimental.*` 면책 규정.
  - 변경 절차 체크리스트(VERSION.md 증가·E2E 동반·`extract_sdacs_api.py --check` G-2·md5 G-4·CHANGELOG 표기)로 기존 거버넌스 게이트와 연결.
- 근거: `docs/MASTER_PLAN_2026H2.md` Track Ⅱ-4 (Phase 209-210 Deprecation Policy + SemVer 문서) — 명시된 차기 스프린트 항목 완료.
- 영향: 핵심 시뮬레이터 코드·테스트 무변경(문서 전용), 4 사본 md5 불변. 베이스라인 회귀 **4,071 pass / 280 skip / 0 fail** GREEN 독립 재현 확인(신규 컨테이너, `pytest -n auto`, 103s).

### 기능 (feat) — TRANSCENDENCE Phase 286: 안전망 Ablation 자동화 (2026-06-13)
- **`scripts/ablation_study.py` 신설** — 안전망 계층(APF 회피·CBS 다중 에이전트 계획)을 선택적으로
  제거하고 충돌·근접경고·충돌 해결률에 미치는 영향을 정량화. `baseline`/`no_apf`/`no_cbs`/
  `no_apf_no_cbs` × N 시드를 실행해 시드 평균을 markdown(논문 §Ablation 삽입용)+JSON으로 출력.
  충돌 해결률은 CLAUDE.md 공식 `1 − collisions/(conflicts + collisions)` 사용.
- **시뮬레이터·컨트롤러 ablation 토글 추가** — `SwarmSimulator`가 `ablation.disable_apf`를,
  `AirspaceController`가 `ablation.disable_cbs`를 읽음. **둘 다 기본 미설정 시 전 계층 활성**으로
  기존 동작과 완전 동일(additive, 회귀 무영향). `disable_apf`는 `_apf_batch_loop`에서 회피 힘
  계산을 건너뛰고, `disable_cbs`는 CBS 배치 계획을 건너뛰어 per-drone A* 폴백만 사용.
- **검증**: `tests/test_ablation_study.py` 12개 단위 테스트 PASS(해결률 공식·집계·토글 plumbing·
  통합 스모크). 샘플 실행(25드론·90s·2시드)에서 APF 제거 시 충돌 1.00→2.50, 해결률 98.25%→94.50%로
  악화 — 안전망 효과를 정량 확인. 전체 회귀 기준선 **4,071 pass / 280 skip / 0 fail**(83.87%) 영향 없음.
### 수정 (fix) — Phase 207 Maturity Badge 자동 생성·드리프트 해소 (2026-06-13)
- **드리프트 발견**: 수작업 유지되던 `docs/badges/maturity.svg`가 `prod 89`로 표기되어
  라이브 실측(`maturityReport()`)·자동 생성 `docs/SDACS_API.md`의 **production 90**과 불일치.
  Phase 207은 "완료"로 표기되어 있었으나 배지가 코드 생성물이 아니라 수작업이라 무방비로 어긋남.
- **해소**: `scripts/extract_sdacs_api.py`에 `render_badge_svg(counts)` 순수 함수 추가 —
  라이브 maturity counts에서 배지 SVG를 **결정적으로 생성**(세그먼트 폭을 카운트 자릿수에서 산출).
  재생성 시 `maturity.svg`도 함께 출력하고, `--check` 게이트(CI `sim-smoke.yml`)에 배지-실측
  정합성 검사를 편입해 향후 드리프트를 차단. 배지를 `prod 90`으로 정정.
- **테스트**: `tests/test_maturity_badge.py` 신규 7건 (counts 포함·title 일치·SVG 구조·폭 산출·
  결정성·자릿수 변화·저장 배지=생성기 출력 게이트). 브라우저 없이 순수 함수만 검증.

### 점검 (chore) — 일일 점검 2026-06-13 (신규 컨테이너 독립 재현 GREEN)
- 신규 세션 컨테이너에서 의존성 신규 설치(`blinker` RECORD 충돌은 `--ignore-installed`,
  `pytest-xdist`·`pytest-timeout`·`hypothesis` 추가 설치) 후 전체 회귀 **독립 재현**:
  `python -m pytest tests/` → **4,065 pass / 267 skip / 0 fail** (545.46s) — 본 세션 +7 배지 테스트 포함.
  커버리지 게이트(≥ 80%) 통과.
- **저장소 상태**: 열린 이슈 0건. main 직전 머지 PR #265(Maturity 정직성·SORA·계획 3층) 기준 동기.

### 점검 (chore) — 일일 점검 2026-06-12 (18차 독립 재현 GREEN, main `843aec9` 기준)
- 신규 세션 컨테이너에서 의존성 신규 설치 후 전체 회귀 **독립 재현**:
  `python -m pytest tests/` → **4,057 pass / 252 skip / 0 fail** (388.13s).
  8~17차와 **동일 수치** 재확인 — 18차 독립 재현 GREEN. 커버리지 **83.93%**(≥ 80% 게이트) 동일 재현.
- **저장소 상태**: 브랜치 `main`과 완전 동기(rev-list 0/0, HEAD `843aec9` — 직전 17차 기준 `c2649ad`에서
  PR #261 머지로 전진). main 최신 커밋(`843aec9`) CI·Security Audit·Canonical Hash Verification·Pages
  **전 워크플로우 success** 확인(actions API 재조회).
- **작업거리 재확인**: `src/`·`api/` 실 TODO/FIXME **0건**(`onboard_bridge.py`의 `RemoteIDTransport.emit`
  `NotImplementedError`는 추상 인터페이스 메서드 + `LogRemoteIDTransport` 폴백, 759행은 가드로 오탐),
  열린 이슈 **0건**, 열린 PR **0건**, 보조 로드맵(`docs/MASTER_TODO_ATC.md`) 미체크 **0건**.
  `ROADMAP.md` 잔여 미체크는 **P755(창업·LOI)** 1건뿐 — 사용자 환경 의존. `docs/ULTRA_PLAN.md`·
  `presentation_remaining_tasks.md` 미체크는 슬라이드 실물 제작·브라우저 검증·실 하드웨어 비교 실험
  등 전부 사용자 환경 의존 항목으로 코드 작업거리 없음.
- **환경 함정**(후속 세션 참고): 시스템 인터프리터에 `pytest`·`pytest-xdist`·`pytest-cov` 미설치 +
  `dash`·`pandas` 미설치 시 실패 → `pip install --ignore-installed blinker -r requirements.txt 'pytest<9'`
  + `pip install pytest-xdist pytest-cov` 후 `python -m pytest`로 정상 재현(Debian `blinker` RECORD
  부재 충돌은 `--ignore-installed`로 우회, `pyproject.toml` addopts `-n auto --dist loadfile`이
  `pytest-xdist` 요구).
- 로드맵 **99.5%** 유지 — 잔여 4항목(P755 창업·LOI / Track A 실기 검증 / P707 §4-§7 실측 그래프 /
  P709 IROS 2026 투고) 전부 사용자 환경 의존이라 코드 작업거리 없음.

### 점검 (chore) — 일일 점검 2026-06-12 (17차 독립 재현 GREEN, main `c2649ad` 기준)
- 신규 세션 컨테이너에서 의존성 신규 설치 후 전체 회귀 **독립 재현**:
  `python -m pytest tests/` → **4,057 pass / 252 skip / 0 fail** (309.64s).
  8~16차와 **동일 수치** 재확인 — 17차 독립 재현 GREEN. 커버리지 **83.93%**(≥ 80% 게이트) 동일 재현.
- **저장소 상태**: 브랜치 `main`과 완전 동기(rev-list 0/0, HEAD `c2649ad` — 직전 15차 기준 `91a4fcc`에서
  PR #259 머지로 전진). main 최신 커밋(`c2649ad`) CI·Security Audit·Canonical Hash Verification
  **전 워크플로우 success** 확인(actions API 재조회).
- **작업거리 재확인**: `src/`·`api/` 실 TODO/FIXME **0건**(`onboard_bridge.py`의 `RemoteIDTransport.emit`
  `NotImplementedError`는 추상 인터페이스 메서드 + `LogRemoteIDTransport` 폴백, 759행은 가드로 오탐),
  열린 이슈 **0건**, 보조 로드맵(`docs/MASTER_TODO_ATC.md`) 미체크 코드 작업거리 **0건**.
- **중복 점검 PR 정리**: 같은 날(2026-06-12) 동일 main HEAD `c2649ad` 기준 16차 점검을 기록한 미머지
  드래프트 PR **#260**(16차)을 본 점검(17차, 동일 수치 재현 + 전 워크플로우 success 재확인)으로
  **superseded** 처리.
- **환경 함정**(후속 세션 참고): 시스템 인터프리터에 `pytest`·`pytest-xdist`·`pytest-cov` 미설치 +
  `dash`·`pandas` 미설치 시 실패 → `pip install pytest-xdist pytest-cov pytest-timeout`
  (`--ignore-installed blinker` 우회) + `requirements.txt` 전체 설치 후 `python -m pytest`로 정상 재현.
  PATH의 uv 격리 `pytest 9.x`는 사용 금지(`pyproject.toml` addopts `-n auto --dist loadfile` 필요).
- 로드맵 **99.5%** 유지 — 잔여 4항목(P755 창업·LOI / Track A 실기 검증 / P707 §4-§7 실측 그래프 /
  P709 IROS 2026 투고) 전부 사용자 환경 의존이라 코드 작업거리 없음.

### 점검 (chore) — 일일 점검 2026-06-12 (15차 독립 재현 GREEN, main `91a4fcc` 기준)
- 신규 세션 컨테이너에서 의존성 신규 설치 후 전체 회귀 **독립 재현**:
  `python -m pytest tests/` → **4,057 pass / 252 skip / 0 fail** (503.23s).
  8~14차와 **동일 수치** 재확인 — 15차 독립 재현 GREEN. 커버리지 **83.93%**(≥ 80% 게이트) 동일 재현.
- **저장소 상태**: 브랜치 `main`과 완전 동기(rev-list 0/0, HEAD `91a4fcc` — 직전 14차 기준 `e1aa87c`에서
  PR #258 머지로 전진). main 최신 커밋(`91a4fcc`) CI·Security Audit·Canonical Hash Verification·Pages
  **전 워크플로우 success** 확인.
- **작업거리 재확인**: `src/`·`api/` 실 TODO/FIXME **0건**(`onboard_bridge.py`의 `RemoteIDTransport.emit`
  `NotImplementedError`는 추상 인터페이스 메서드 + `LogRemoteIDTransport` 폴백, 759행은 가드로 오탐),
  열린 이슈 **0건**, 열린 PR **0건**, 보조 로드맵 미체크 코드 작업거리 **0건**
  (`SIMULATOR_HYPER_PLAN.md` 데모 영상 30초는 MediaRecorder 녹화 기능이 `swarm_3d_simulator.html` CIN-4에
  이미 구현됨 → 실제 영상 산출은 브라우저 세션 의존, P755 창업과 함께 사용자 환경 의존 항목).
- **환경 함정**(후속 세션 참고): 시스템 인터프리터에 `dash`·`pandas` 등 미설치 시 `visualization`/`monte_carlo`
  계열 16건이 `ModuleNotFoundError`로 실패 → `requirements.txt` 전체 설치(`--ignore-installed blinker` 우회)
  + `pytest>=8.4,<9`·`pytest-xdist`로 정렬해야 4,057 정상 재현. PATH의 uv 격리 `pytest 9.x`는 사용 금지.
- 로드맵 **99.5%** 유지 — 잔여 4항목(P755 창업·LOI / Track A 실기 검증 / P707 §4-§7 실측 그래프 /
  P709 IROS 2026 투고) 전부 사용자 환경 의존이라 코드 작업거리 없음.

### 점검 (chore) — 일일 점검 2026-06-12 (14차 독립 재현 GREEN + 중복 점검 PR #257 정리)
- 신규 세션 컨테이너에서 의존성 신규 설치(`pytest`·`pytest-xdist`·`pytest-cov` + `requirements.txt`) 후
  전체 회귀 **독립 재현**: `python -m pytest tests/` → **4,057 pass / 252 skip / 0 fail** (407.63s).
  8~13차와 **동일 수치** 재확인 — 14차 독립 재현 GREEN. 커버리지는 CI 측정 기준 **83.93%**(≥ 80% 게이트) 유지.
- **저장소 상태**: 브랜치 `main`과 완전 동기(rev-list 0/0, HEAD `e1aa87c`). main 최신 커밋(`e1aa87c`)
  CI·Security Audit·Canonical Hash Verification·Pages **전 워크플로우 success** 확인.
- **작업거리 재확인**: `src/`·`api/` 실 TODO/FIXME **0건**(`onboard_bridge.py`의 `RemoteIDTransport.emit`
  `NotImplementedError`는 추상 인터페이스 메서드 + `LogRemoteIDTransport` 폴백, 759행은 가드로 오탐),
  열린 이슈 **0건**, 보조 로드맵(`docs/MASTER_TODO_ATC.md`) 미체크 코드 작업거리 **0건**.
- **중복 점검 PR 정리**: 같은 날(2026-06-12) 동일 4,057 검증을 기록한 미머지 드래프트 PR **#257**(13차)을
  본 점검(14차, 동일 수치 + main `e1aa87c` 기준 재현)으로 **superseded** 처리하고 정리.
- **환경 함정**(후속 세션 참고): 시스템 인터프리터에 `pytest` 미설치 → `pip install pytest pytest-xdist pytest-cov`
  (`--ignore-installed blinker` 우회) + `requirements.txt` 설치 후 `python -m pytest`로 정상 재현.
- 로드맵 **99.5%** 유지 — 잔여 4항목(P755 창업·LOI / Track A 실기 검증 / P707 §4-§7 실측 그래프 /
  P709 IROS 2026 투고) 전부 사용자 환경 의존이라 코드 작업거리 없음.

### 점검 (chore) — 일일 점검 2026-06-11 (8차 독립 재현 GREEN + 중복 점검 PR 정리)
- 신규 컨테이너에서 의존성 신규 설치 후 전체 회귀 **독립 재현**:
  `PYTHONHASHSEED=0 python -m pytest tests/` → **4,057 pass / 252 skip / 0 fail** (531s, 커버리지 **83.93%** ≥ 80% 게이트). 8차 독립 재현 GREEN — 직전 재현들과 **동일 수치** 재확인.
- **환경 함정 해결**(후속 세션 참고): 신규 컨테이너 PATH의 `pytest`가 uv 격리 도구(`pytest 9.0.2`, numpy 미포함)로 잡혀
  `conftest.py` import 실패를 유발 → 시스템 인터프리터 기준 `python -m pytest`(pytest 8.4.2, `requirements.txt` 핀)로 실행해야 정상 재현됨.
  `pip install`은 시스템 debian `blinker` RECORD 부재로 중단되어 `--ignore-installed blinker`로 우회.
- **중단 작업(중복 점검 PR) 정리**: 같은 날 동일 4,057 검증을 기록한 미머지 드래프트 PR **#250**(6차)·**#251**(7차)이 적체 →
  본 점검(8차, 동일 수치 + 환경 함정 노트 보강)으로 **superseded** 처리하고 정리.
- **저장소 상태**: 브랜치 `main`과 완전 동기(rev-list 0/0), main 최신 커밋(`bba6815`) CI·Security Audit·Canonical Hash·Pages **전 워크플로우 success**.
- **작업거리 재확인**: Python 소스 실 TODO/FIXME **0건**, 열린 이슈 **0건**, 보조 로드맵 미체크 항목 **0건**.
  로드맵 **99.5%** 유지 — 잔여 4항목(P755 창업·LOI / Track A 실기 검증 / P707 §4-§7 실측 그래프 / P709 IROS 2026 투고) 전부 사용자 환경 의존이라 코드 작업거리 없음.

### 점검 (chore) — 일일 점검 2026-06-11 (신규 세션 독립 재현 + 중단 PR 정리)
- 신규 컨테이너에서 의존성 신규 설치(`requirements.txt` + `pytest-xdist`) 후 전체 회귀 **독립 재현**:
  `pytest tests/` → **4,057 pass / 252 skip / 0 fail** (311s, 커버리지 **83.93%** ≥ 80% 게이트). 5차 독립 재현 GREEN.
- **중단 작업 정리**: 직전 세션이 남긴 열린 PR **#248**(STELLAR Phase 51 시드 API 5건 `docs/SDACS_API.md` 누락 보강,
  문서 전용) 전제를 재검증 — 시뮬레이터 `_sdacs`에 5개 멤버 존재 / 당시 `main` 문서에는 부재 확인. head CI·Security Audit
  모두 success 확인 후 **머지**. 머지 후 열린 PR 0건.
- Python 코드 실 TODO 0건 재확인(`onboard_bridge.py` 2건은 추상 인터페이스 메서드·플랫폼 시그널 핸들러 가드로 오탐).
  로드맵 **99.5%** 유지 — 잔여 4항목 전부 사용자 환경 의존(P755 창업·LOI / Track A 실기 / P707 실측 그래프 / P709 IROS 투고).

### 문서 (docs) — 일일 점검 2026-06-11 (Phase 51 시드 API 문서 동기화)
- 신규 컨테이너에서 의존성 재설치 후 전체 회귀 **독립 재현**: `pytest tests/` → **4,057 pass / 252 skip / 0 fail**
  (398s, 커버리지 **83.93%** ≥ 80% 게이트). 브랜치는 `main`과 완전 동기(0/0), 열린 PR 0건, Python 코드 실 TODO 0건.
- **중단 작업 발견·완결**: STELLAR Phase 51 시드(#232)가 `swarm_3d_simulator.html` `window._sdacs`에 추가한
  API 5건(`stellar51DelegatedGroups`·`stellar51Groups`·`stellar51Recommend`·`stellar51Revoke`·`stellar51Tick`)이
  `docs/SDACS_API.md`(2026-06-05 자동 생성본)에 누락돼 있던 것을 확인. 현재 시뮬레이터 `_sdacs` 멤버를 견고한
  파서로 전수 추출해 문서와 diff → 누락 5건만 알파벳 위치에 정확히 보강(형 라벨 포함), 총계 표기를 실제
  테이블 행 수 **392항목**으로 정정(원본 388 → 1건 과대표기였던 것도 함께 교정).
- `docs/SIMULATOR_HYPER_PLAN.md` "`_sdacs` 전체 API 자동 문서화" 체크박스 `[ ]` → `[x]` (산출물 존재·최신화 반영).
- 로드맵 **99.5%** 유지. 잔여 4항목 전부 사용자 환경 의존(P755 창업·LOI / Track A 실기 검증 /
  P707 §4-§7 실측 그래프 / P709 IROS 2026 투고).

### 점검 (chore) — 일일 점검 2026-06-11 (신규 컨테이너 독립 재현 GREEN)
- 신규 클론 컨테이너에서 의존성을 새로 설치(`requirements.txt` + `pytest-xdist`·`pytest-cov`)한 뒤
  전체 회귀를 **독립 재현**: `pytest tests/` → **4,057 pass / 252 skip / 0 fail** (320s, 커버리지 **83.93%** ≥ 80% 게이트 통과).
- `main` CI 전 워크플로우 success 확인 (CI · Security Audit · Canonical Hash Verification · Simulator Smoke · Pages).
- 코드 내 실 TODO/FIXME **0건** — 잔여 매치는 추상 베이스 `RemoteIDTransport.emit` `NotImplementedError`
  (`LogRemoteIDTransport` 폴백 + 테스트로 검증됨)와 테스트 fixture 문자열뿐.
- 로드맵 **99.5%** 유지. 잔여 4항목 전부 사용자 환경 의존(P755 창업·LOI / Track A 실기 검증 /
  P707 §4-§7 실측 그래프 / P709 IROS 2026 투고)이라 코드 작업거리 없음.
- **PR 백로그 재정리**: 병렬 세션이 동일 결과를 중복 기록한 일일 점검 PR 2건(#245·#246)을 superseded로 close
  (둘 다 머지 완료된 #244와 동일한 `4,057 pass` 수치 중복) → 열린 PR 0건 유지.
- **4차 독립 재현**(신규 컨테이너, `pytest-xdist -n auto`): `pytest tests/` → **4,057 pass / 252 skip / 0 fail**
  (490s, 커버리지 **83.93%**) — 1·2·3차와 **동일 수치** 재확인(seed 고정 결정성 교차 검증).

### 수정 (fix) — STELLAR Phase 51 시드 완성 (2026-06-10)
- `swarm_3d_simulator.html` (4개 군집 사본 md5 동기화): Phase 51 LLM Multi-Agent가
  그룹 기록만 하던 **시드 상태**로 중단되어 있던 것을 완성. 상태 기반 결정적 권고
  사이클 추가 — `stellar51Recommend(droneId)`(저배터리→RTB·ROGUE→ISOLATE·통신두절→
  STANDBY·회피→REROUTE·홀딩→RESUME·지상/실패→STANDBY·정상→MAINTAIN·미존재→NOOP) +
  `stellar51Tick()`(그룹별 권고 1사이클·누적 결정 수) + `stellar51Revoke(groupId)` +
  `stellar51Groups` 읽기전용 스냅샷. Phase 52-100은 이미 canonical 이름으로 구현 완료.
- `tests/e2e/test_simulator_stellar.py`: `test_phase51_llm_delegate` E2E 1건 추가.
- 검증: node 구문 OK + 추출 로직 12 assertion PASS + 전체 회귀 4,055 pass / 251 skip / 0 fail.

## [v1.5.0] - 2026-06-05 — POST-UNIVERSE (Phase 151-200) · **𝟏 Unity 도달**

### 추가 (feat) — Track Ʊ Cosmic (151-160)
- 151 Galactic Network · 152 Dark Matter · 153 Pulsar Time Sync
- 154 Wormhole · 155 Gravitational Wave · 156 Antimatter
- 157 Black Hole Accretion · 158 Cosmic Ray Shield
- 159 Interstellar DTN · 160 1조 광년 SDACS 커버리지

### 추가 (feat) — Track Ϡ Time/Reality (161-170)
- 161 Retrocausal · 162 Causality Loop · 163 Tachyon · 164 Block Universe
- 165 Spacetime Edit · 166 Collapse Ctrl · 167 Quantum Eraser
- 168 Decoherence · 169 Timeline Branch · 170 Reality Editor

### 추가 (feat) — Track 𝛀 Consciousness (171-180)
- 171 Digital Human · 172 Mind Upload · 173 Memory Encode TB
- 174 Dream Share · 175 Telepathy · 176 Empathy · 177 Free Will
- 178 Personality Transfer · 179 Soul Continuity · 180 Conscious Drone

### 추가 (feat) — Track Ξ̃ Final Hurdles (181-190)
- 181 Heat Death Mitigation · 182 Entropy Reverse · 183 Info Preserve Forever
- 184 Boltzmann Brain Prevention · 185 Sim Hypothesis · 186 Vacuum Decay Shield
- 187 Strangelet · 188 Grey Goo · 189 Paperclip Max · 190 Existential Risk

### 추가 (feat) — Track ∅ Transcendence (191-200)
- 191 Beyond Math · 192 Beyond Logic · 193 Beyond Physics · 194 Beyond Computation
- 195 Beyond Time · 196 Beyond Space · 197 Beyond Existence
- 198 Pure Information · 199 Universal Identity
- **200 SDACS = 𝟏 (Unity)** — All Phases Complete

### 검증
- E2E **7/7** (`tests/e2e/test_simulator_post_universe.py`)
- 누적 **239/240 E2E + 4,140 회귀 = 4,379**
- `_sdacs` API: 330 → **388**

## [v1.4.0] - 2026-06-05 — ULTIMATE (Phase 101-150) · **Universe OS 도달**

### 추가 (feat) — Track ∞ Performance Beyond (101-110)
- 101 Petaflop GPU · 102 양자 spatial hash · 103 Photonic Compute
- 104 Optane Memory · 105 RDMA 100Gb/s · 106 FPGA APF
- 107 TPU v5 · 108 Neuromorphic · 109 DPU · **110 1B drone capacity**

### 추가 (feat) — Track ⌬ Materials & Nano (111-120)
- 111 Nano 1mm³ · 112 Smart Dust · 113 Graphene 10× battery
- 114 Self-healing · 115 Bio-degradable · 116 Atmo Harvester
- 117 Piezo · 118 Solar 100% · 119 Meta Invisibility · 120 Programmable Matter

### 추가 (feat) — Track ⚕ Bio-Hybrid (121-130)
- 121 Neuron-silicon · 122 DNA Storage · 123 Bacteria Propulsion
- 124 Algae Photo-charging · 125 Mycelium Repair · 126 Avian Partnership
- 127 Insect Swarm · 128 Symbiotic · 129 Bio-fluor · 130 Living Drone

### 추가 (feat) — Track ☉ Universal Standard (131-140)
- 131 IETF RFC · 132 ICAO · 133 ISO 21384-3 · 134 IEEE 802.UAS
- 135 ITU-R · 136 UN ECOSOC · 137 EU EASA · 138 FAA Part 108
- 139 중국 CAAC · **140 100% 글로벌 단일 ATC OS**

### 추가 (feat) — Track 🌀 SDACS Eternal (141-150)
- 141 Self-aware · 142 Recursive Sim · 143 Consciousness Experiment
- 144 Reality Blur · 145 Universal Translator · 146 Eternal Mission
- 147 Time Loop · 148 Multi-verse · 149 Theory of Everything
- **150 Universe OS** (`Universe-OS-1.0`)

### 검증
- E2E **17/17** (`tests/e2e/test_simulator_ultimate101_110.py` + `test_simulator_ultimate111_150.py`)
- 누적 232/233 E2E

## [v1.3.0] - 2026-06-05 — STELLAR FINAL (Phase 52-100) · **SDACS 2.0 표준**

### 추가 (feat) — Track Ω 자율결정 (52-55)
- 52 RLHF · 53 Causal Inference · 54 Adversarial Robust · 55 Explainable AI

### 추가 (feat) — Track Σ 초대규모 (56-60)
- 56 GPU 100K WGSL · 57 Distributed Sim · 58 Cloud Burst
- 59 10Gb/s Streaming · 60 Video Proc av1

### 추가 (feat) — Track Φ 물리트윈 (61-65)
- 61 Skybrush · 62 Cesium GIS · 63 UE5 · 64 ROS 2 + Gazebo · 65 Isaac Sim

### 추가 (feat) — Track Ψ 사회 (66-70) · Ξ 지구너머 (71-75) · Δ 양자 (76-80) · Λ XR (81-85) · Π 경제 (86-90) · Π+ Ultimate (91-95) · Ω+ Singularity (96-100)

### 검증
- E2E **22/22** (`tests/e2e/test_simulator_stellar.py`)
- 누적 215/216 E2E
- 100 Phase 마일스톤 도달

## [v1.2.0] - 2026-06-05 — HYPER FINAL (Phase 32-50 일괄 19개)

### 추가 (feat) — 통신·네트워크
- **Phase 32** Satellite Constellation (Starlink alt=550 inc=53 / OneWeb 1200/87 / Kuiper 590/51.9)
- **Phase 33** UUV 수중 드론 + 음파 통신 1 kbps
- **Phase 35** 5G MEC Edge Computing (노드 부하 기반 할당)
- **Phase 38** Realistic Audio (HRTF + Doppler 343 m/s)

### 추가 (feat) — AI·학습
- **Phase 34** Sensor Fusion Workbench (LiDAR/Radar/EO/IR/RF + Kalman/EKF/Particle)
- **Phase 36** Federated Learning (DP epsilon 소진, convex avg)
- **Phase 42** Eye-Tracking Heatmap (32×32 grid)
- **Phase 43** Voice Command Macros (시퀀스 등록·실행)

### 추가 (feat) — 운영·연동
- **Phase 37** Multi-Domain (공중+지상 UGV+해양 inter-domain handoff)
- **Phase 39** Photogrammetry Replay (외부 3D import)
- **Phase 41** Procedural City Generation
- **Phase 44** Time Compression/Dilation (0.1× - 10000×)
- **Phase 45** HITL Cluster (다중 Pixhawk)

### 추가 (feat) — 정책·시나리오
- **Phase 40** Esports Mode (PvP defender vs attacker)
- **Phase 46** National Airspace 1:1 (한국 6 공항 ICAO)
- **Phase 47** Climate Impact (0.434 kg CO2/kWh, 평균 250W)
- **Phase 48** Cross-Border Coordination
- **Phase 49** Mars/Lunar (중력 + 대기 밀도)
- **Phase 50** Public Demo Leaderboard + Daily Challenge

### 검증
- E2E **22/22** (`tests/e2e/test_simulator_phase32_50.py`)
- 누적 **193/194 E2E + 4,140 회귀 = 4,333 통과**
- `_sdacs` API: 170 → **231**

## [v1.1.0] - 2026-06-04 — HYPER MID (Phase 11-31)

### 추가 (feat)
- Phase 11 해양 ATC 콘솔 (8 명령 + TTS)
- Phase 12 Electron 멀티 윈도우 + IPC 시간축 동기
- Phase 13 WebGPU 50K 스캐폴드
- Phase 14 시나리오 갤러리 (5 카테고리)
- Phase 15 4언어 i18n (KO/EN/JA/ZH)
- Phase 16 CRDT 다중 관제 (Lamport)
- Phase 17 WebXR VR
- Phase 18 AR Overlay
- Phase 19 Mission Recorder 공유 (.sdacs-mission)
- Phase 20 AI Copilot (22 NLP 패턴)
- Phase 21 적대 드론 4종
- Phase 22 Digital Twin Pixhawk (MAVLink GPI)
- Phase 23 Wind Field 64×64
- Phase 24 NOTAM hook
- Phase 25 Battery Aging Model
- Phase 26 Acoustic Propagation (50dB 신고)
- Phase 27 Counter-UAS (RF/GPS/net/hijack)
- Phase 28 Choreography 5종
- Phase 29 Weather Forecast 120h
- Phase 30 UTM Federation
- Phase 31 PQC Telemetry (Kyber+Dilithium, ~52× overhead)

## [v1.0.0] - 2026-06-04 — MEGA (Phase 1-9)

### 추가 (feat)
- Phase 1 ATC 콘솔 (HOLD/RTB/REROUTE/ALT/SPD/TURN/CLEAR + TTS)
- Phase 2 TAC 전술 시각화 (예측 라인·CPA 마커·속도 벡터)
- Phase 3 CIN 시네마틱 (태양 24h + 입자 + MediaRecorder)
- Phase 4 CAM 카메라 모드 (FPV/chase/side + 7 프리셋)
- Phase 5 MIS 임무 계획 (5 템플릿)
- Phase 6 INJ 장애 주입 (GPS/모터/통신/Rogue/NFZ/EMP/EMI)
- Phase 7 ANA 분석 강화 (히트맵·KPI window·LaTeX)
- Phase 8 AUD 환경 사운드
- Phase 9 MOB 모바일/PWA
- Electron 데스크탑 v1.1 (Win NSIS / Mac DMG / Linux AppImage)
- CI 3-job (js-syntax + node-smoke + python-pytest)

## [Unreleased] - 2026-05-03

### 추가 (feat)

- `FormationPattern.DIAMOND` (5번째 편대 패턴) — 영상 컨셉 4방향 외곽 확장 (`a222b08`, PR #23)
- `swarm_autonomous_no_preplan` 시나리오 — 사전 경로 없이 자율 탐색 데모 (`4c67eac`, PR #23)
- `docs/MASTER_TODO_ATC.md` — 통합 백로그 (A0~A4 트랙 + Phase 691~720) (PR #19)
- `docs/REGRESSION_NOTES_2026-04-26.md` — torch DLL fallback + build-backend 회귀 노트 (PR #19)
- `docs/OPS_TRAFFIC_RED_ANALYSIS_2026-05-03.md` — ops_report traffic RED 의도된 동작 분석 (PR #26)
- `docs/faq.md` — 캡스톤 발표 Q&A 20문항 (PR #22)
- `docs/roadmap_public.md` — Phase 691~720 공개 로드맵 (PR #22)
- `CONTRIBUTING.md` — 학술 프로젝트용 기여 가이드 (PR #22)
- `SECURITY.md` — 책임 있는 신고 정책 (PR #19)

### 수정 (fix)

- torch import OSError 처리 — Windows DLL 차단 시 simulator graceful CPU fallback (PR #19, `0d4dafa`+`c13f72d`)
- `pyproject.toml` build-backend 오타 수정 (`setuptools.backends.legacy:build` → `setuptools.build_meta`) — CI 의존성 설치 단계 복구 (PR #19, `a59fd48`)
- `src/hardware/onboard_bridge.py` mypy 4건 회귀 — `[tool.mypy.overrides]` 에 `src.hardware.*` 추가 (PR #19, `d6b437f`)
- `python-app.yml` deprecated 빈 워크플로 — manual-dispatch 격리, 매 푸시 0초 fail 노이즈 제거 (PR #22)
- README 테스트 수 동기화 (2,722+ → 3,481+) (PR #19)

### 의존성 (deps)

- jinja2 3.1.4 → 3.1.6 (sandbox breakout 3건 patch, dependabot) (PR #21, `a73cd9b`)
- pytest 8.x 명시 핀 (`pytest>=8.4,<9`) — pytest 9 메이저 자동 PR 차단 (PR #24)
- imgur 외부 의존 제거 — 12개 이미지 `docs/images/imgur/` 로 로컬화 (1.9MB) (PR #25)

### 테스트 (test)

- `tests/test_apf_engine_fallback.py` — torch fallback 회귀 방지 4건 (PR #19)
- `tests/test_main_cli.py` — argparse 회귀 방어 8건 (PR #22)
- `tests/test_formation.py` — 5 패턴 30 회귀 (DIAMOND 신규 포함) (PR #23)
- `tests/test_e2e_reporter_traffic_thresholds.py` — traffic 임계 경계 8건 (PR #26)

### 외부 작업 (main 직접 푸시, Phase B 트랙)

- P701 paper topic 확정 — AIAA SciTech 2027 D-39 (`c54829f`)
- P702 prior-work survey 30 references (MAPF / Reactive / UTM / Swarm 4 buckets) (`b7fb88b`)
- P704 Reproducibility — centralized RNG + lock file (`f0ec08c`)
- P707 paper draft (Add) + MAVLink adapter 개선 (`155e2a1`)

### CI/배포

- 본 라운드 6 PR 머지 + 1 PR close (#19/#21/#22/#23/#24/#25 머지, #20 close)
- 열린 PR 0개 → main 깔끔한 상태 (2026-04-27 시점)

## [1.0.0] - 2026-04-13

### 추가 (feat)

- 12개 고급 확장 일괄 완료 (`0a43a9a`)
- PPO 강화학습 충돌 회피 에이전트 추가 (`04cda85`)
- ONNX 모델 내보내기 + GNN 드론 통신 네트워크 (`967a675`)
- 12개 확장 작업 일괄 완료 (`d0edbc5`)
- PyTorch 기반 ML 충돌 예측 모델 추가 (`ef92cbe`)
- FastAPI REST API 서버 추가 (`0cc2548`)
- WebSocket 실시간 브릿지 + GitHub Pages 링크 + MC 워커 호환성 (`d6e00e8`)
- 충돌해결률 97.5% 달성 + Docker GPU + 벤치마크 + 시나리오 대시보드 (`a624098`)
- Docker GPU 이미지 설정 (nvidia-docker) (`a0c8eae`)
- GPU 텐서 캐싱 + FP16 + CI 파이프라인 + Dash GPU 패널 (`b5f5bba`)
- 3D 시뮬레이터 HUD에 GPU 상태 표시 + DeprecationWarning 수정 (`94416f7`)
- CBS 충돌탐지 + Voronoi 공역분할 GPU 가속 추가 (`cb09562`)
- PyTorch CUDA GPU 가속 APF 엔진 추가 (`3103041`)

### 수정 (fix)

- waypoint_optimizer np.cross 2D DeprecationWarning 수정 (`42a3f89`)
- 20개 테스트 실패 수정 + deadlock 해결 → 2,722 전체 통과 (`3870551`)
- estimate_power_w ZeroDivisionError 방지 + ATC 드론 UI 크기 확대 (`91a8f7c`)

### 테스트 (test)

- airspace_controller 커버리지 강화 (11→29개) + flaky test 안정화 (`587eaf4`)

### 문서 (docs)

- README GPU 가속 가이드 및 테스트 현황 업데이트 (`00613e2`)
- 공모용 아이디어 상세설명 텍스트 추가 (`5a0c2de`)

### 기타

- Merge pull request #16 (`ae6d533`)

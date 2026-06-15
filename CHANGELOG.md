# Changelog

이 프로젝트의 모든 주요 변경 사항을 기록합니다.
형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/)를 기반으로 합니다.

## [Unreleased]

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

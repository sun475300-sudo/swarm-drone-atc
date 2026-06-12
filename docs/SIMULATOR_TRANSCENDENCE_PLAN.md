# ✴️ SDACS TRANSCENDENCE Plan — Phase 201-300 초대규모 울트라플랜

*Created: 2026-06-12 — Phase 200 (𝟏 Unity) 도달 + Phase 51 LLM Multi-Agent 격상 직후*

> **철학 전환**: Phase 1-200은 *"무엇을 할 수 있는가"* 의 한계를 정의했다(능력 매트릭스).
> Phase 201-300 TRANSCENDENCE 단계는 *"무엇을 실제로 검증·실증·확산할 수 있는가"* 로 무게중심을 옮긴다.
> 즉, 추상적 스텁(stub)을 **실측 가능한 구현**으로 격상하고, 단일 인스턴스 검증을 **다중 사용자·다중 기관·실 하드웨어** 검증으로 확장한다.

---

## 📊 시작점 (Phase 200 + Phase 51 격상 시점)

| 지표 | 값 |
|---|:-:|
| 시뮬레이터 코드 (군집) | 11,723 line |
| `_sdacs` API | 404 항목 (분류 401 + 헬퍼 3) |
| Playwright E2E | 263 / 264 통과 (1 skip) |
| 회귀 pytest | 4,180 pass / 8 skip / 0 fail |
| 데스크탑 빌드 | v1.5.0 (Win/Mac/Linux) |
| Phase 완료 | 200 / 200 (단, 51-200 다수는 mock/stub) |

**핵심 인식**: Phase 51-200 중 상당수(특히 71-200)는 인터페이스 호환을 위한 **결정적 mock**이다.
TRANSCENDENCE는 이 중 **실측 가치가 있는 30~40개를 선별 격상**하고, 나머지는 명시적으로 "speculative stub"로 라벨링하여 **구현 성숙도(maturity)를 정직하게 표시**한다.

---

## 🎯 5대 TRANSCENDENCE 트랙

### Track ✅ — Maturity Honesty (Phase 201-220) · 성숙도 정직성
*가장 높은 실용 가치. 각 Phase에 maturity 등급을 부여.*

- **Phase 201** API Maturity Registry — 각 `_sdacs` API에 `maturity: 'production'|'beta'|'mock'|'speculative'` 메타데이터 부착
- **Phase 202** `_sdacs.maturityReport()` — 404 API의 성숙도 분포 자동 집계 (분류 401)
- **Phase 203** ✅ Mock Detector — mock/speculative API 호출 시 console.warn 1회 + `maturityReport().mockCalls` 카운트 (2026-06-12)
- **Phase 204** Production API 핵심 12종 회귀 강화 (ATC/TAC/MIS/INJ)
- **Phase 205** Beta API 부분 검증 (Copilot/적대/C-UAS)
- **Phase 206** ✅ Speculative API 격리 — `window._sdacs.experimental.*` 네임스페이스 (직접 호출 호환 유지, speculative 103종 전수 노출) (2026-06-12)
- **Phase 207** ✅ Maturity Badge SVG 자동 생성 — `extract_sdacs_api.py --badge` 가 실측 counts 로 `docs/badges/maturity.svg` 재생성 + `--check` 정합성 게이트에 배지 검증 추가 (prod 89→90 드리프트 정정) (2026-06-12)
- **Phase 208** README Maturity 섹션 자동 갱신
- **Phase 209** API Deprecation Policy 문서
- **Phase 210** Semantic Versioning 적용 (API breaking change 추적)
- **Phase 211-220** 각 트랙별 production-grade 격상 (12 API → 30 API)

### Track 🔬 — Real Validation (Phase 221-240) · 실측 검증
*mock을 실 데이터/실 알고리즘으로 교체.*

- **Phase 221** WebGPU Compute Shader 실 구현 (Phase 13/56 mock → WGSL 실제 컴파일)
- **Phase 222** Spatial Hash GPU 벤치마크 (1K/10K/50K 실측 ms)
- **Phase 223** CRDT 실 Yjs 통합 (Phase 16 mock → Yjs WebRTC P2P)
- **Phase 224** 2-브라우저 협업 E2E (Playwright 다중 컨텍스트)
- **Phase 225** MAVLink 실 파서 검증 (Phase 22 — PX4 SITL 연동 E2E)
- **Phase 226** GPS→ENU 변환 정밀도 검증 (±0.5m 기준)
- **Phase 227** 풍속장 실 KMA 데이터 import (Phase 23 — 1km grid)
- **Phase 228** 음향 전파 실측 보정 (Phase 26 — dB 측정 캘리브레이션)
- **Phase 229** PQC 실 라이브러리 (Phase 31 — Kyber-768 WASM)
- **Phase 230** Battery Aging 실 LiPo 곡선 (Phase 25 — 방전 데이터)
- **Phase 231-240** 나머지 실측 격상 + 비교 실험 자동화

### Track 🌐 — Multi-User Reality (Phase 241-260) · 다중 사용자
*단일 브라우저 → 실 다중 사용자/기관.*

- **Phase 241** WebSocket 관제 서버 (`api/fastapi_server.py` 통합)
- **Phase 242** JWT 다중 관제사 세션 (Phase 16 CRDT 위)
- **Phase 243** 실 동시 편집 충돌 해결 검증
- **Phase 244** TimescaleDB 텔레메트리 영속 (30일 보존)
- **Phase 245** Grafana 실 대시보드 연동
- **Phase 246** 부하 테스트 100 동시 사용자
- **Phase 247** Helm K8s 실 배포 검증 (kind 클러스터)
- **Phase 248** 베타 파일럿 NPS 자동 수집 파이프라인
- **Phase 249** A/B 시나리오 통계 자동 비교
- **Phase 250** 공개 데모 게스트 ATC 계정 (Phase 50 격상)
- **Phase 251-260** SaaS-grade 운영 안정화

### Track 🚁 — Hardware Loop (Phase 261-280) · 실 하드웨어
*시뮬-실드론 HITL 실증.*

- **Phase 261** Pixhawk 6X SITL → 시뮬 실시간 매핑 (Phase 22 실증)
- **Phase 262** 10Hz 텔레메트리 p99 < 100ms 검증
- **Phase 263** 5 드론 클러스터 동시 HITL (Phase 45 실증)
- **Phase 264** 역방향 명령 (시뮬 ATC → MAVLink COMMAND_LONG)
- **Phase 265** Jetson Orin 엣지 추론 (Phase 35 MEC 실증)
- **Phase 266** RTK-GPS ±2cm 정밀 (Phase 22 정밀화)
- **Phase 267** Failsafe 시나리오 12 failure mode 실증
- **Phase 268** 야외 비행 사전 검증 매트릭스
- **Phase 269** FMEA 실 데이터 갱신
- **Phase 270** Remote ID 방송 실증 (ASTM F3411)
- **Phase 271-280** 실 비행 데이터셋 수집·공개

### Track 🏆 — Academic Impact (Phase 281-300) · 학술 임팩트
*캡스톤 → 학술 기여 → 표준 제안.*

- **Phase 281** IROS 2026 투고 패키지 완성 (PaperCept)
- **Phase 282** arXiv 익명화 fork + 동시 업로드
- **Phase 283** 벤치마크 데이터셋 Zenodo DOI
- **Phase 284** Reproducibility 컨테이너 검증 (PYTHONHASHSEED=0)
- **Phase 285** 비교 실험 ORCA/VO/CBS 통계 유의성
- **Phase 286** Ablation study 자동화 (각 안전망 계층 제거 효과)
- **Phase 287** Sim-to-Real gap 정량화
- **Phase 288** 후속 캡스톤 멘토링 자산 패키지
- **Phase 289** 오픈소스 커뮤니티 CONTRIBUTING 강화
- **Phase 290** 국제 학회 발표 슬라이드 (ICRA/AIAA)
- **Phase 291-300** K-UTM 표준 제안 + 산학 LOI 체결

---

## 🎯 우선순위 매트릭스 (즉시 착수 Top 10)

| Phase | 영역 | 임팩트 | 난이도 | sandbox 가능 |
|---|---|:-:|:-:|:-:|
| 201 API Maturity Registry | 정직성 | 🔥🔥🔥🔥🔥 | ⭐ | ✅ |
| 202 maturityReport() | 정직성 | 🔥🔥🔥🔥 | ⭐ | ✅ |
| 206 experimental 네임스페이스 | 정직성 | 🔥🔥🔥🔥 | ⭐⭐ | ✅ |
| 207 Maturity Badge | 정직성 | 🔥🔥🔥 | ⭐ | ✅ |
| 221 WebGPU 실 구현 | 검증 | 🔥🔥🔥🔥 | ⭐⭐⭐⭐ | 🟡 |
| 223 CRDT Yjs 실 통합 | 다중 | 🔥🔥🔥🔥 | ⭐⭐⭐ | 🟡 |
| 224 2-브라우저 협업 E2E | 다중 | 🔥🔥🔥🔥 | ⭐⭐⭐ | ✅ |
| 225 MAVLink SITL E2E | 하드웨어 | 🔥🔥🔥🔥🔥 | ⭐⭐⭐⭐ | 🟡 |
| 281 IROS 투고 패키지 | 학술 | 🔥🔥🔥🔥🔥 | ⭐⭐⭐ | ✅ |
| 286 Ablation 자동화 | 학술 | 🔥🔥🔥🔥 | ⭐⭐⭐ | ✅ |

**권장 즉시 착수**: Phase 201·202·206·207 (Maturity Honesty) — 4개 모두 sandbox 가능, 프로젝트 신뢰성을 근본적으로 강화.

---

## 📈 누적 KPI 목표 (TRANSCENDENCE)

| 지표 | Phase 200 | Phase 220 | Phase 260 | Phase 300 |
|---|:-:|:-:|:-:|:-:|
| `_sdacs` API | 404 | 420 | 480 | 550 |
| Production-grade API | ~20 | 50 | 100 | 200 |
| E2E 케이스 | 248 | 320 | 450 | 600 |
| 실 사용자 검증 | β | 10 | 100 | 1,000 |
| 실 비행 데이터 | 0 | 0 | 5 드론 | 50 비행 |
| 학술 산출물 | scaffold | IROS 투고 | 게재 | 표준 제안 |

---

## 🔁 거버넌스 (TRANSCENDENCE)

- **정직성 우선**: 모든 신규/기존 API에 maturity 등급 필수
- mock 격상 시 **실측 E2E 1개 이상** 추가
- 회귀 4,140+ 통과 보존
- 사본 동기화 md5 일치
- README maturity 섹션 자동 갱신
- 분기마다 SDACS_API.md + maturityReport 재생성

## 📚 참고
- [`SIMULATOR_MEGA_PLAN.md`](SIMULATOR_MEGA_PLAN.md) — Phase 1-10 (✅)
- [`SIMULATOR_HYPER_PLAN.md`](SIMULATOR_HYPER_PLAN.md) — Phase 11-50 (✅)
- [`SIMULATOR_STELLAR_PLAN.md`](SIMULATOR_STELLAR_PLAN.md) — Phase 51-100 (✅, 51 격상)
- [`SIMULATOR_ULTIMATE_PLAN.md`](SIMULATOR_ULTIMATE_PLAN.md) — Phase 101-150 (✅)
- [`SIMULATOR_POST_UNIVERSE_PLAN.md`](SIMULATOR_POST_UNIVERSE_PLAN.md) — Phase 151-200 (✅)
- [`SIMULATOR_GENESIS_PLAN.md`](SIMULATOR_GENESIS_PLAN.md) — Phase 301-400 (다음 지평: 인증·생태계·실증·자율·레거시)
- [`MASTER_PLAN_2026H2.md`](MASTER_PLAN_2026H2.md) — 2026 H2 통합 실행 일정
- [`STATUS_REPORT.md`](../STATUS_REPORT.md) · [`CHANGELOG.md`](../CHANGELOG.md)

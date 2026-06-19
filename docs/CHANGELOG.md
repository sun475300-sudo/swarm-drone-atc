# SDACS Changelog

## 2026-06-19 — ODYSSEY Continuum Phase 486 신규 + 드래프트 #388 일원화 (일일 점검 49차)

신규 컨테이너에서 의존성 신규 설치 후 적체 드래프트 #388(Phase 484·487·490,
#386·#387 흡수)을 통합하고 전체 회귀 **5,840 pass / 280 skip / 0 fail**
(177.83s, 84.98% cov) 독립 재현 GREEN. 이어 Continuum 비브라우저 잔여 1칸 신규:

- **Phase 486** ✅ 연 1회 건전성 리허설 자동화 — `simulation/rehearsal_cadence.py` +
  `docs/standards/HEALTH_REHEARSAL_CADENCE_POLICY.md`. 신규 컨테이너 독립 재현
  하니스(`scripts/independent_reproduction.sh`)가 *언제 다시 필요한가*(연 1회
  365일 + 예고 30일 + 유예 30일)와 *온전한가*(4개 하니스 자산 실재)를 결정적
  정책으로 판정(Phase 481/484/488/489 자매편, 부수효과 0). `assess` 우선순위:
  하니스 손상→REVIEW·기록 없음→RUN_NOW·미래→REVIEW·비-PASS→RUN_NOW·그 외
  케이던스 등급. `LAST_REHEARSAL` 스냅샷(2026-06-19=PASS) → `WITHIN_CADENCE`
  정직 공시. code-reviewer HIGH 2·MEDIUM 2·LOW 2 반영. 41건 PASS.
- 통합 시 발견한 문서 불일치 정정 — ODYSSEY 플랜에서 모듈 실재에도 미표시였던
  Phase 487·490 을 ✅ 로 동기화.

점검 발견(사용자 검토): 열린 PR 18건 적체 지속(Dependabot 13 + #283 perf +
#280 draft Phase 207 + 일원화 대상 #386·#387·#388) · GitHub 보고 취약점 4건
(2 high·2 low) 미해소 — 머지·triage 는 사용자 승인 필요.

## 2026-06-19 — ODYSSEY Continuum 3칸 일원화 (일일 점검 48차)

신규 컨테이너 baseline 회귀 **5,747 pass / 280 skip / 0 fail**(84.92% cov) 독립
재현 GREEN 후, 적체 드래프트 일원화 + 신규 1칸:

- **Phase 484** ✅ Electron LTS 추적 정책 — `simulation/electron_lts_policy.py` +
  `docs/standards/ELECTRON_LTS_TRACKING_POLICY.md`. Electron 최신 3 major 지원 창
  기준 핀 수명을 결정적 판정(Phase 481 자매편). 현 핀 39 = 상류 42 대비
  `EOL (lag=3)` 정직 공시. code-reviewer HIGH 2·MEDIUM 4·LOW 4 반영. 56건 PASS.
- **Phase 487** ✅ 유지보수자 승계 규약(BDFL→위원회) — `simulation/governance_succession.py`
  (적체 드래프트 #387 일원화). 현 1인 구조 `BUS_FACTOR_RISK` 정직 공시. 48건 PASS.
- **Phase 490** ✅ 디지털 유산 10년 재현성 체크리스트 — `simulation/legacy_readiness.py`
  (적체 드래프트 #386 일원화). 현 리포 `NOT_READY (58.8%)` 정직 공시. 30건 PASS.

점검 발견(사용자 검토): 열린 PR 18건 적체 지속(Dependabot 13 + #283 perf +
#280 draft + 일원화 대상 #386·#387) · GitHub 보고 취약점 4건(2 high·2 low)
미해소 — 머지·triage 는 사용자 승인 필요.

## [v1.0-ultraplan] — 2026-06-04

### 🎉 울트라플랜 대규모 실행 — 17 PR 동시 진행

본 세션에서 Phase 691-755 전반의 미진행 작업을 일괄 처리.

#### Track A — 실기 드론 통합 (P691-P700)
- ✨ 실기 가이드 10종 (`docs/hardware/`) — Pixhawk + Jetson + RTK + Failsafe + MoCap + 실외 + 환경 시험 + FMEA
- ✨ M1-M6 비행 매트릭스 + 사전 체크리스트 + 한국 인프라(KGI VRS, NSDI) 명시

#### Track B — 연구·논문화 (P701-P710)
- ✨ P701 outline + 논문 제목 후보 3개 + IROS §-outline
- ✨ P702 30편 서베이 (5 카테고리 × 차별점 표)
- ✨ P707 LaTeX scaffold (Abstract + §1-§3 + algorithm)
- ✨ P708 review checklist (R1/R2/R3 + 잠재 reviewer 질문 사전 대비)
- ✨ P709 IROS PaperCept + arXiv 가이드
- ✨ P710 동강대 포스터 스켈레톤 + Marp 슬라이드 outline
- ✨ 차트 생성 스크립트 (`scripts/poster/generate_charts.py`) — NMR/MSD bar + Pareto front

#### Track C — 배포·서비스 (P720)
- ✨ P720 공개 베타 운영 가이드 — 3 파일럿 + SLA + NPS + 듀얼 라이선스

#### Track D — 웹 시뮬레이터 (P730-P735)
- ✨ P730 UI 국제화 (KO/EN 토글)
- ✨ P731 공역 레이어 패널 통합 (O1)
- ✨ P732 대규모 CPA 공간 해시 (B2)
- ✨ P733 ws_bridge LIVE 모드 + 인터페이스 정합성 수정
- ✨ P734 키보드 스크러버 (←/→/Home/End/L) + 멀티뷰 동기화
- ✨ P735 해양 EO/IR adapter 패턴 + Mock SDK 예시

#### Track E — 확장 연구 (P736-P745, 신설)
- ✨ P736 PPO scaffold (`src/rl/ppo_collision.py`) + 학습 가이드
- ✨ P737 비협조 침입자(UAS-T) 결정 트리 + 9 단위 테스트
- ✨ P738 NSDI 3D 건물 → NFZ 임포터
- ✨ P739 Domain Randomization + ADR 곡선
- ✨ P740 디지털 트윈 동기화 엔진 (MAVLink → SDACS)
- ✨ P741 Raft HA AirspaceController + 13 단위 테스트
- ✨ P742 K-UAM Grand Challenge 시나리오 YAML + Runbook
- ✨ P743 양자 안전 통신 (Kyber-768 + Dilithium-3 + AES-GCM)
- ✨ P744 폐쇄망(MIL/L4) 모드 + CI workflow (`airgap-audit.yml`)
- ✨ P745 LLM 관제 보조 (Whisper + Claude)

#### Track F — 산학 실증·사업화 (P746-P755, 신설)
- ✨ P746 K-UAM 컨소시엄 + 30억 3년 계획
- ✨ P747 해수부 항만 3거점 18억 가이드
- ✨ P748 산림청 야간 IR 23억
- ✨ P749 KISA CSAP 96항목 1.5억
- ✨ P750 농업 방제 드론 + Voronoi 분할 + 5 단위 테스트
- ✨ P751 의료 배송 + Urgency 4단계 + Haversine ETA + 6 단위 테스트
- ✨ P752 IROS/ICRA workshop proposal
- ✨ P753 듀얼 라이선스 + 5건 특허 + 5개 회사 타겟
- ✨ P754 후속 캡스톤 멘토링 가이드
- ✨ P755 창업 결정 매트릭스 + 5년 매출 계획

#### 인프라
- ✨ `docs/ULTRA_PLAN.md` — Phase 691-755 4-Sprint 종합 계획
- ✨ `STATUS_REPORT.md` — 트랙별 KPI 종합 보고서
- ✨ Air-Gap Policy CI 워크플로우 (`.github/workflows/airgap-audit.yml`)
- 🔧 PR #78: setup-node cache 옵션 제거 (lock 파일 부재)
- 🔧 PR #89: ws_bridge fake mock 인터페이스 갱신
- 🔧 PR #94: `dict[str, int | float]` 명시 (mypy dict-item)

### 📊 통계

- **신규 코드**: ~75 파일, +5,300 라인
- **신규 테스트**: 79 (Track E 54 + 추가)
- **신규 docs**: 35+ (Track A 10 + paper 5 + track_f 9 + track_e 5 + 기타)
- **PR 머지 대기**: 17개 (본 세션 9 + 다른 세션 8)

### 🎯 머지 후 진척률

- Phase 1-690: 100% ✅
- Phase 691-755: **89%** (58/65, partial 포함)
- 잔여: Track A 실기 검증, P707 §4-§7, IROS 투고, P746-P749 LOI

## [v0.9] — 2026-06-03

- PR #70: Electron 데스크탑 앱 (.bat 폐기, 3-OS 자동 빌드)
- PR #69: P714 TimescaleDB + P715 Helm + P718 관측성 + P719 보안 감사
- Track A SW 컴포넌트 11개 통합 (`3295124`)
- P706 비교 실험 결과 + 벤치마크 schema

## [v0.8] — 2026-06-01

- P712 JWT/RBAC + 29 테스트
- P717 부하 테스트 (100기 60s PASS)
- P706 APF+CBS 하이브리드 vs ORCA/VO/CBS

## [v0.7] — 2026-05-29

- P703 벤치마크 데이터셋 + P704 Docker 재현성 + P705 메트릭 정형화
- P713 WebSocket 채널 + P716 CI 6 워크플로우

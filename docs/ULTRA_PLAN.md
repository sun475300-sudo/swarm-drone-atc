# 🚀 SDACS Ultra Plan (Phase 691-755)

목포대 캡스톤 → 학술 기여 → 산업 자산화 → 사업화까지 65 Phase 종합 실행 계획.

*작성: 2026-06-03. 매 Sprint 종료 시 갱신.*

---

## 📊 현재 상태 (2026-06-03 기준)

- **완료**: Phase 1-690 (100%) + 691-735 일부 → **22/65 = 34%**
- **머지 대기**: PR #81 (P730/P733/Track E·F), #84 (P731), #88 (P732), #89 (P734)
- **머지 후 예상**: 27/65 = 42%

---

## 🎯 우선순위 매트릭스

| 작업 유형 | 가치 | 노력 | 의존성 | 적정 시점 |
|---|---|---|---|---|
| **SW 단독 진행 가능** | ★★★ | ☆☆ | 없음 | 즉시 |
| **문서 작성** | ★★ | ☆ | 없음 | 즉시 |
| **연구·실험 (PyTorch)** | ★★★ | ★★ | 환경 | 단기 |
| **실기 통합** | ★★★ | ★★★ | 하드웨어 | 사용자 PC |
| **산학·논문** | ★★★ | ★★ | 외부 | 중기 |
| **창업·기술이전** | ★★ | ★★★ | 사업화 | 장기 |

---

## 🗓️ 4-Sprint 로드맵

### Sprint 1 — 이번 세션 + 1주 (Phase A 마무리)

| 작업 | 산출물 | 환경 |
|---|---|---|
| 머지 대기 4 PR (#81/#84/#88/#89) | Track D 87% | 사용자 승인 |
| **P734 멀티뷰 동기화** | 분석뷰 ↔ 메인뷰 시간축 공유 | SW |
| **P735 해양 EO/IR adapter** | 실 카메라 SDK 연동 hook (Mock + 어댑터) | SW |
| **P701 논문 주제 outline** | `docs/paper/contribution_outline.md` | 문서 |
| **P710 학회 포스터 스켈레톤** | `docs/poster/`, `docs/slides/` | 문서 |

**SP1 목표**: Track D 15/15 = 100%, Track B 5/10 = 50%

---

### Sprint 2 — 2-3주 (논문 + Track E 시동)

| 작업 | 산출물 | 환경 |
|---|---|---|
| **P702 선행 연구 서베이** | 30편 IROS/ICRA/AIAA + Zotero export | 문서 |
| **P707 논문 초안 §1-§3** | Abstract/Intro/Method (LaTeX) | 문서 |
| **P736 RL 충돌회피 PoC** | `src/rl/ppo_collision.py` — SB3 PPO + SwarmSimulator wrapper | PyTorch |
| **P737 비협조 침입자 회피** | `src/uast/intruder_response.py` — DnI + 결정 트리 | SW |

**SP2 목표**: Track B 8/10 = 80%, Track E 2/10 = 20%

---

### Sprint 3 — 1개월 (논문 투고 + 실기 준비)

| 작업 | 산출물 | 환경 |
|---|---|---|
| **P707 §4-§6 완성** | Experiments/Discussion/Conclusion | 문서 |
| **P708 내부 리뷰** | 3회 리뷰 + 지도교수 피드백 | 문서 |
| **P709 arXiv + 투고** | IROS 2026 / AIAA SciTech 2027 | 문서 |
| **P738 도시 LiDAR 통합** | 국토부 NSDI 3D 건물 → NFZ 자동 생성 | SW |
| **P739 Sim-to-Real DR** | 풍속·센서 노이즈 분포 학습 wrapper | PyTorch |
| **P691-P692 실기 준비 docs** | Pixhawk/Jetson 체크리스트 | 문서 |

**SP3 목표**: Track B 10/10 (투고), Track E 4/10, Track A 소프트 시작

---

### Sprint 4 — 2-3개월 (실기 + 사업화 시동)

| 작업 | 산출물 | 환경 |
|---|---|---|
| **P691-P700 실기 통합** | Pixhawk + Jetson + RTK-GPS HITL, 3-5기 실외 비행 | 하드웨어 |
| **P700 HITL 보고서** | FMEA + 안전 분석 | 문서 |
| **P711 React 프론트엔드** | 별도 repo `swarm-dashboard-web` | 별도 |
| **P720 공개 베타** | 3개 파일럿 기관 모집 | 외부 |
| **P740 디지털 트윈** | MAVLink2 → SDACS <50ms | PyTorch+실기 |
| **P741 페일오버 클러스터** | Raft 합의 기반 HA | SW |
| **P710 학회 발표** | 동강대 4/23 + IROS workshop | 문서·외부 |

**SP4 목표**: Track A 80%, Track C 100%, Track E 70%, Track D 100%

---

### Sprint 5+ — 6개월+ (확장 + 사업화)

| 작업 | 산출물 |
|---|---|
| **P742 eVTOL/UAM** | K-UAM Grand Challenge 호환 |
| **P743 양자 안전 통신** | Kyber/Dilithium PoC |
| **P744 폐쇄망 모드** | 외부 의존 0, 군용 베이스라인 |
| **P745 LLM 관제 보조** | Whisper + Claude/GPT 음성·자연어 → ATC |
| **P746-755 Track F 산학** | K-UAM·해수부·산림청·KISA·창업 |

---

## 🎯 핵심 우선순위 — Now / Next / Later

### NOW (이 세션·다음 세션)
1. PR #81/#84/#88/#89 머지
2. P734 멀티뷰 동기화
3. P701 논문 주제 outline (이 문서와 함께 작성됨)

### NEXT (1-2주)
4. P702 서베이 30편 (Zotero)
5. P735 해양 EO/IR adapter
6. P710 포스터 완성 (동강대 4/23 데드라인)

### LATER (1개월+)
7. P707 논문 초안 LaTeX
8. P736 RL PoC (PyTorch + SB3)
9. P691-P700 실기 (하드웨어 도착 후)

---

## 🚨 리스크 및 대응

| 리스크 | 영향 | 대응 |
|---|---|---|
| 실기 하드웨어 부재 | Track A 정체 | SW 시뮬·SITL로 P700 FMEA 선행 |
| 논문 데드라인(IROS 1월) | P707-P709 압박 | SP2 LaTeX 시작, SP3 투고 |
| 동강대 4/23 | P710 압박 | SP1 스켈레톤 → SP2 완성 |
| RL 학습 시간 | P736 정체 | SP2 시작, GPU 클라우드 검토 |
| Track F 외부 거절 | P746-749 지연 | 복수 후보 동시 컨택 |

---

## 📈 KPI 추적

| 지표 | 현재 | SP1 목표 | SP2 | SP3 | SP4 |
|---|---|---|---|---|---|
| 전체 Phase 완료율 | 34% | 42% | 55% | 70% | 85% |
| Track A 실기 | 0% | 0% | 10% | 30% | 80% |
| Track B 논문 | 40% | 50% | 80% | 100% | 100% |
| Track C 서비스 | 80% | 80% | 80% | 90% | 100% |
| Track D 시뮬 | 60% | 100% | 100% | 100% | 100% |
| Track E 확장 | 0% | 0% | 20% | 40% | 70% |
| Track F 산학 | 0% | 0% | 0% | 10% | 30% |
| 테스트 수 | 3,830+ | 3,900+ | 4,100+ | 4,300+ | 4,500+ |
| 논문 투고 | 0 | 0 | 0 | 1 | 1 |

---

## 🔁 갱신 규칙

- 매 Sprint 종료 시 KPI 표 갱신
- 신규 PR 머지 시 ROADMAP.md ↔ 본 문서 양방향 동기화
- 우선순위 변경은 매트릭스 + Sprint 표 동시 수정

# 🎓 SDACS 졸업 심사 발표 키트 (GENESIS Phase 387)

*국립 목포대학교 드론기계공학과 캡스톤 디자인 2026 — 심사 대비 통합 자료*
*2026-06-12 기준 실측 수치 사용 (출처: `scripts/extract_sdacs_api.py` + pytest 실행 로그)*

---

## 1️⃣ 30초 엘리베이터 피치

> "SDACS는 군집드론 공역통제 자동화 시스템입니다. 드론 수십~수천 대가 같은 공역을 쓸 때
> 충돌을 막는 것이 핵심 문제인데, 저희는 **APF 회피 → CBS 경로계획 → CPA 90초 예측 →
> ATC 관제 → UTM 연동**의 5계층 안전망으로 해결했습니다. SimPy 이산 사건 시뮬레이션과
> 브라우저 단독 3D 시뮬레이터로 구현했고, **자동 테스트 4,443건 전부 통과**로 검증했습니다.
> 특히 407개 외부 API 전부에 구현 성숙도 등급을 공시하는 **정직성 체계**가 차별점입니다."

## 2️⃣ 라이브 데모 시나리오 (10분)

> 사전 조건: 크롬에서 `swarm_3d_simulator.html` 로컬 오픈 (오프라인 동작 — 인터넷 불필요)

| # | 시간 | 시연 | 명령/조작 | 보여줄 것 |
|---|:-:|---|---|---|
| 1 | 1분 | 기본 비행 | 페이지 로드 → 자동 시작 | 드론 이륙·순항·役割 색상, KPI 패널 |
| 2 | 1분 | 드론 상세 | 드론 클릭 | 배터리·고도·속도·비행거리 패널 |
| 3 | 2분 | **충돌 회피 (핵심)** | 시나리오 `high_density` 선택 | CPA 예측 마커, 충돌 해결률 ≈100% 유지 |
| 4 | 1분 | ATC 관제 | 드론 선택 → HOLD → RTB | 음성(TTS) + 발광 링 + 감사 로그 |
| 5 | 1분 | 장애 주입 | 콘솔 `_sdacs.injectScenario('EMP')` | GPS 손실 드론 회복 과정 |
| 6 | 1분 | 동적 NFZ | `_sdacs.injectDynamicNFZ(0,0,200,30)` | 분석 뷰 Q2 원형 NFZ + 잔여 시간 펄스 |
| 7 | 1분 | 분석 뷰 | `_sdacs.setAnalysisView(true)` | 2×2: 3D + 평면도 + 배터리 + KPI |
| 8 | 1분 | **정직성 (차별점)** | `_sdacs.maturityReport()` | production 93 / mock 110 공시 |
| 9 | 1분 | SORA 인증 산정 | `_sdacs.soraAssess({populationDensity:'populated'})` | JARUS 2.0 → SAIL II 도출 |

**백업 플랜** (데모 실패 대비):
- 1순위: `docs/demo/sdacs_200phase_showcase.webm` (60초 자동 시연 영상, 사전 다운로드)
- 2순위: 발표 슬라이드 내 스크린샷 (분석 뷰·CPA·ATC 각 1장)
- 노트북 사양 무관: 시뮬레이터는 단일 HTML, GPU 없어도 SwiftShader로 동작

## 3️⃣ 예상 질문 & 답변 포인트 (영역별)

### A. 알고리즘 (핵심 — 반드시 숙지)

1. **APF의 local minimum 문제는 어떻게 처리했나?**
   → 회랑(corridor) 유도 + 충돌 쿨다운(`_conflictCooldown`) + 상위 계층 CBS 재계획이 폴백. APF 단독이 아니라 5계층이라 단일 기법 한계가 시스템 실패로 이어지지 않음.
2. **CPA 90초 예측의 수학적 근거는?**
   → 등속 외삽 기반 최근접점(Closest Point of Approach) 해석해. 상대위치·상대속도 내적으로 t* = -(Δp·Δv)/|Δv|² 도출, 0≤t*≤90s 구간만 경보.
3. **CBS는 완전한가(complete)?**
   → 이산 그리드·유한 제약에서 완전·최적. 실시간성 위해 타임박스 두고 실패 시 APF가 안전 유지 (논문 §4 Ablation에 계층 제거 효과 수록).
4. **충돌 해결률 공식의 정의는?**
   → `1 - collisions/(conflicts + collisions)`. 감지된 위험 중 실제 충돌로 이어진 비율의 보수. 속성 기반 테스트로 [0,1] 불변식 검증.
5. **왜 RL이 아니라 규칙 기반인가?**
   → 안전 핵심 시스템의 검증 가능성. RL은 PoC(`src/rl/ppo_collision.py`)로 분리, GENESIS 362에서 "규칙 우선 안전 보장" 하이브리드로 계획.

### B. 검증·신뢰성

6. **테스트 4,443건은 무엇을 검증하나?**
   → 회귀 4,180(단위·통합) + Playwright E2E 263(브라우저 실 구동). 속성 기반(Hypothesis) 1,150케이스 포함. CI에서 Python 3.10/3.11/3.12 매트릭스.
7. **407개 API 중 실제 동작은 얼마나 되나? (정직성 질문)**
   → 정면 답변: production 93 + beta 98 = **188종이 실 동작**, mock 110·speculative 103은 인터페이스 안정성만 보장. `maturityReport()`로 실시간 공시하고 mock 호출 시 콘솔 경고. 이 정직성 체계 자체가 기여.
8. **시뮬레이션 결과를 실제 드론에 신뢰할 수 있나? (Sim-to-Real)**
   → 한계 인정: 현재 실 비행 데이터 0건. Domain Randomization(`src/training/domain_rand.py`)과 Pixhawk HITL 가이드(P691-700)로 격차 축소 경로 마련, TRANSCENDENCE 261-280이 실증 로드맵.
9. **재현성은?**
   → `np.random.default_rng(seed)` 고정, PYTHONHASHSEED=0 Docker 재현 패키지, 18차례 독립 컨테이너 재현 GREEN 기록 (ROADMAP 일일 점검).

### C. 시스템·구현

10. **왜 단일 HTML 파일인가?**
    → 배포 마찰 제로(이메일·USB 전달 가능), 오프라인 동작(PWA), 심사·교육 현장 즉시 실행. 코드 11,900줄 단일 파일의 유지보수 비용은 4사본 md5 CI 게이트와 자동 문서화로 상쇄.
11. **1,000대 이상에서 성능은?**
    → InstancedMesh 단일 드로우콜 + 공간 해시 CPA + Web Worker APF + WebGPU compute(베타). 성능 HUD로 draw call·FPS 실측 표시.
12. **Python 시뮬과 웹 시뮬의 관계는?**
    → Python(SimPy)이 정밀 검증·논문용, 웹이 시연·교육용. `ws_bridge.py`(2Hz WebSocket)로 라이브 연결 — 같은 데이터로 두 뷰.

### D. 기여·확장

13. **학술적 기여는 무엇인가?**
    → ① 5계층 안전망 아키텍처와 Ablation ② ORCA/VO/CBS 대비 비교 실험(NMR·MSD 개선) ③ 공개 벤치마크 10종 + 재현 패키지. IROS 2026 §1-§7 초안 완성.
14. **상용화 가능성은?**
    → K-UAM·해수부 항만·산림청 산불 감시 제안서(docs/track_f) + SORA 자동 산정으로 규제 적합 경로. 다만 실증(90일 파일럿)이 선행 조건임을 명시.
15. **이 프로젝트에서 본인이 가장 잘했다고 생각하는 결정은?**
    → (개인 답변 준비) 추천 포인트: mock을 production으로 위장하지 않고 maturity 공시 체계를 만든 것 — 공학적 정직성.

### E. 압박 질문 대비

16. **"Phase 200, Universe OS… 과장 아닌가?"**
    → 인정 + 반전: 명명은 비전 매트릭스이고, 그래서 maturity 분류(89→90 production)와 기술 부채 대장을 만들어 **과장과 실체를 코드로 구분**했다. `TECH_DEBT_LEDGER.md` 제시.
17. **"테스트 수가 많다고 품질이 좋은가?"**
    → 동의: 수가 아니라 속성. 그래서 속성 기반 테스트(불변식)·E2E(실 브라우저)·독립 컨테이너 재현의 3중 구조. 단순 카운트 부풀리기 방지를 위해 CI가 문서-실측 일치를 강제.
18. **"한 학기 분량인가?"**
    → 커밋 히스토리·CHANGELOG·PR 260+개가 개발 과정 전부를 공개 기록. 자동화 도구(Claude Code) 활용을 명시하되, 아키텍처 결정·검증 설계·실측 판단은 직접 수행.

## 4️⃣ 심사 당일 체크리스트

**전날**
- [ ] 노트북에 리포 클론 + `swarm_3d_simulator.html` 오프라인 열기 확인
- [ ] showcase.webm 로컬 다운로드 + 재생 확인
- [ ] `python main.py simulate --duration 60` 1회 실행 (Python 데모 백업)
- [ ] 슬라이드 PDF 내보내기 (PPT 호환 문제 대비)

**당일**
- [ ] HDMI/USB-C 어댑터 + 발표 파일 USB 사본
- [ ] 브라우저 시크릿 창 (확장 프로그램 간섭 차단)
- [ ] 콘솔 미리 열어두기 (F12 — 데모 명령 복사 준비)
- [ ] 데모 명령 치트시트 (본 문서 2️⃣ 표) 인쇄

**발표 구조 (15분 기준)**
- [ ] 문제 정의 2분 → 아키텍처 3분 → **라이브 데모 6분** → 검증·정직성 2분 → 한계·로드맵 2분

## 5️⃣ 핵심 수치 카드 (암기용)

| 항목 | 값 | 한 줄 설명 |
|---|:-:|---|
| 안전망 | 5계층 | APF·CBS·CPA·ATC·UTM |
| 자동 검증 | 4,443 pass / 0 fail | 회귀 4,180 + E2E 263 |
| API | 404 (production 93) | maturity 공시 |
| 충돌 해결률 | `1 - c/(c+f)` | high_density에서 ≈100% |
| CPA 예측 | 90초 lookahead | 등속 외삽 해석해 |
| 시뮬 코드 | 11,900줄 / 540KB | 단일 HTML 오프라인 |
| 부채 공시 | mock 110 + spec 103 | TECH_DEBT_LEDGER |

## 🔗 관련 자산
- 슬라이드: [`../slides/donggang_2026_ko.md`](../slides/donggang_2026_ko.md) (Marp 15장)
- 포스터: [`../poster/donggang_2026_ko.md`](../poster/donggang_2026_ko.md)
- 보고서: [`../report/SDACS_Capstone_Report_v200.docx`](../report/SDACS_Capstone_Report_v200.docx) · v6(기술)/v7(일반인)
- 데모 영상: [`../demo/sdacs_200phase_showcase.webm`](../demo/sdacs_200phase_showcase.webm)

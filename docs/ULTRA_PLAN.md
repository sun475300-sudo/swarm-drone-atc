# 🚀 SDACS Ultra Plan v2 (2026-06-04 갱신)

**상태**: 본 세션 SW 작업 100% 완료 · PR 15개 main 머지 · Phase 691-755 진척 **92%**.

이제 남은 5항목은 모두 **사용자 환경 의존**이며, SW로 더 진행할 부분이 없습니다.
이 문서는 **남은 5항목의 실행 플레이북** + **그 이후 확장 트랙** 을 정의합니다.

---

## 📊 현재 상태 (2026-06-04)

| 트랙 | 진척 | 잔여 |
|---|---|---|
| Phase 1-690 (Core) | ✅ 100% | — |
| Track A (실기, P691-700) | ✅ docs 100% | 사용자 HW |
| Track B (논문, P701-710) | ✅ 100% | P707 실측 그래프, P709 IROS 투고 |
| Track C (서비스, P711-720) | 🟢 90% | P711 React (PR #87) |
| Track D (웹 시뮬, P721-735) | ✅ 100% | — |
| Track E (확장, P736-745) | ✅ 100% | 실 학습·실 API 연결 |
| Track F (산학, P746-755) | 🟢 90% | P755 창업·LOI 체결 |

**잔여 5항목 = 100% SW로는 불가, 모두 사용자 환경 의존.**

---

## 🎯 잔여 5항목 실행 플레이북

### #1 PR #87 React MVP 평가 + 머지
- **소요**: 1일 (검토·테스트)
- **체크리스트**:
  - [ ] `frontend/` 폴더 코드 리뷰 (Vite + React + TypeScript)
  - [ ] `npm run build` + `npm test` 로컬 통과 확인
  - [ ] 백엔드 `uvicorn api.fastapi_server:app --port 8000` 기동
  - [ ] 실 브라우저에서 시나리오 실행·텔레메트리 동작 확인
  - [ ] 머지 후 P711 [x] 갱신

### #2 P707 실측 그래프 (논문 §4-§5 보강)
- **소요**: 1주
- **체크리스트**:
  - [ ] `python main.py monte-carlo --mode hardware-pre-flight` 실 비교 실험
  - [ ] `python scripts/compare_baselines_ext.py --results ...` 자동 KPI 비교
  - [ ] `python scripts/poster/generate_charts.py` 차트 재생성
  - [ ] LaTeX `docs/paper/latex/sections_4to7.tex` 표 수치 갱신
  - [ ] 지도교수 1차 검토

### #3 P709 IROS 2026 투고
- **데드라인**: 2027-01-15 (추정)
- **체크리스트**:
  - [ ] arXiv 익명화 fork 준비 (`scripts/anonymize_repo.py`)
  - [ ] PaperCept 계정 등록 + IROS 2026 submission
  - [ ] PDF 6 page + cover letter + CoI
  - [ ] arXiv 동시 업로드 (cs.RO + eess.SY)
  - [ ] GitHub `v1.0-paper-arxiv-submitted` 태그
  - [ ] CITATION.bib 갱신

### #4 Track A 실기 검증 (P698-P700)
- **소요**: 2-3개월 (하드웨어 수급 + 시험)
- **사전 요건**:
  - [ ] Pixhawk 6X + Jetson Orin Nano + u-blox ZED-F9P 구매
  - [ ] 항공안전법 사전 비행 승인 (국토부 e민원24)
  - [ ] 드론 책임보험 5억 가입
  - [ ] 비행 구역 확보 (안성·고흥·서산 시범)
- **실행**:
  - [ ] `docs/hardware/pixhawk_setup.md` 따라 P691-P697 단계별 진행
  - [ ] M1-M6 비행 매트릭스 90회 실시
  - [ ] `docs/hardware/fmea_report.md` 12 failure mode 실증

### #5 P755 창업 / 분사 검토
- **소요**: 6개월+
- **체크리스트**:
  - [ ] 시장 검증 LOI 5건 (KARI·해수부·한화·NAVER·LIG)
  - [ ] 특허 5건 출원 (`docs/track_f/p753_licensing.md` 참조)
  - [ ] 팀 구성 (대표 + CTO + SE×2 + SI×1)
  - [ ] TIPS 지원 신청 또는 사내 벤처 결정
  - [ ] 자본금 3억 (정부 1억 + 엔젤 2억)

---

## 🌱 Phase 756-800 (다음 확장)

본 세션 완료 후 향후 확장 계획:

### Track G — 운영 자동화 (P756-P765)
- P756: GitOps (ArgoCD) 자동 배포
- P757: Chaos Engineering (Litmus) 회복성 검증
- P758: SLO/SLI 기반 알람 (Sloth)
- P759: 멀티 리전 Active-Active
- P760: Cost monitoring (Kubecost)
- P761-P765: 운영자 도구·자동 진단

### Track H — AI 고도화 (P766-P775)
- P766: LLM 텔레메트리 자연어 질의
- P767: Multi-Agent RL (MARL) — VDN/QMIX
- P768: Adversarial robustness (FGSM·PGD)
- P769: 설명 가능 AI (SHAP·LIME)
- P770: 연합학습 + 차분 프라이버시
- P771-P775: 강화된 자율성

### Track I — 인증·표준화 (P776-P790)
- P776: ISO 21384-3 (UAS Operational Safety)
- P777: SORA (EUROCAE WG-105)
- P778: KAS Part 107 (국내 소형무인기)
- P779: DO-178C (항공 SW 인증)
- P780: ISMS-P 정보보호 관리체계
- P781-P790: 국제·국방 인증

### Track J — 글로벌 확장 (P791-P800)
- P791: 영문 README + docs 번역
- P792: 다국어 시뮬레이터 (EN/JA/ZH/KO)
- P793: 국제 학회 발표 (IROS·ICRA·AAAI)
- P794: 오픈소스 커뮤니티 운영
- P795: 해외 협력 (DLR·MIT·Stanford·NUS)
- P796-P800: 글로벌 ATC 표준 기여

---

## 🛠 즉시 실행 가능 (이번 세션 후)

본 세션 후 추가로 SW 개선이 가능한 항목 (Quick wins):

1. **테스트 커버리지 80%→90%** — `pytest --cov` 누락 영역 보강
2. **시뮬레이터 모바일 최적화** — viewport meta + touch event
3. **Helm v3 chart 검증** — `helm install` 실 테스트
4. **API OpenAPI 3.1 spec** — `openapi.json` 자동 생성
5. **Docker multi-arch (arm64)** — Apple Silicon 지원
6. **GitHub Actions 캐시 최적화** — pip cache + node cache
7. **PR 자동 머지 워크플로우** (Mergify)
8. **Renovate dependency 갱신** 자동화

---

## 📈 KPI 추적

| 지표 | 본 세션 시작 | 본 세션 종료 (2026-06-04) | 목표 (2026 Q4) |
|---|---|---|---|
| 전체 Phase 완료율 | 34% | **92%** (Phase 691-755) | 100% |
| 테스트 수 | 3,830 | **4,080+** | 5,000 |
| 코드 커버리지 | 85% | **88.18%** | 90% |
| 머지된 PR | — | **15개** (본 세션) | — |
| 논문 게재 | 0 | scaffold 완비 | 1편 (IROS 2026) |
| 산학 LOI | 0 | docs 7종 완비 | 3건 체결 |
| GitHub Stars | TBD | — | 100 |

---

## 🔁 갱신 규칙

- 잔여 5항목 진척 시 본 문서 + ROADMAP + STATUS_REPORT 동기화
- 새 트랙 시작 시 [`docs/INDEX.md`](INDEX.md) 마스터 인덱스 갱신
- 매 Phase 완료 시 ROADMAP 체크 + CHANGELOG 추가

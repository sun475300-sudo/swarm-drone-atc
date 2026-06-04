# P709 — 공식 투고 + arXiv 프리프린트 가이드

## 타겟 학회 (우선순위)

| 학회 | Deadline (예상) | 수락률 | 노트 |
|---|---|---|---|
| **IROS 2026** | 2026-01-15 (rolling) | ~45% | Primary — 공학·로보틱스 |
| **ICRA 2027** | 2026-09-15 | ~40% | Fallback |
| **AIAA SciTech 2027** | 2026-06-30 (early) | ~50% | 항공 · UAM 강함 |
| **RA-L (T-RO Letter)** | rolling | ~30% | Short paper (C3 분리 시) |

## IROS 2026 투고 절차

### 사전 등록
- PaperCept 계정: `irconnect.papercept.net/conferences/scripts/start.pl`
- IROS 2026 conference code 입력

### 양식
- 양식: IEEE conference (`ieeeconf.cls`)
- Page: 6 pages (+ references unlimited)
- Font: Times Roman 10pt
- Figures: PNG 300 DPI 또는 PDF vector

### 제출 항목
- [ ] PDF (≤6 MB)
- [ ] Cover letter (1 page)
- [ ] Conflict of Interest (CoI)
- [ ] Video supplement (선택, 3 min, MP4 H.264)
- [ ] Multi-Media supplement (선택)

### 인증
- IROS supplementary code repo: GitHub anonymized fork
  ```bash
  # 익명화 (저자 정보 제거)
  python scripts/anonymize_repo.py --output ../sdacs-anonymous/
  ```

## arXiv 동시 업로드

```bash
# 카테고리: cs.RO (Robotics)
# 보조: eess.SY (Systems and Control)
arxiv-submission --primary cs.RO --secondary eess.SY \
  --pdf docs/paper/latex/main.pdf \
  --source docs/paper/latex/main.tex \
  --license CC-BY-4.0
```

arXiv ID 받은 후:
- `CITATION.bib`에 추가
- README.md `## Citation` 섹션 갱신
- GitHub release tag `v1.0-paper-arxiv-submitted`

## 투고 후 대응

### Rebuttal (수락 시 가끔)
- 리뷰어 의견 1주일 내 답변
- 부정적 리뷰 1편 → 점잖게 반박
- 긍정적 리뷰 → 감사 + clarification

### Rejection 시 (40% 확률)
- 리뷰 분석 → 즉시 개선
- ICRA 2027 (9월)으로 재투고
- 동시 RA-L 가능

## Camera-ready (수락 시)

- PaperCept에서 양식 점검
- copyright form IEEE
- 발표용 슬라이드 작성 (P710 활용)

## 학회 참석 예산

| 항목 | 금액 (USD) |
|---|---|
| 등록비 (early) | 800 |
| 항공권 (왕복) | 1,500 |
| 숙박 5박 | 1,200 |
| 식대·교통 | 500 |
| **소계** | **4,000** |

지원 자금:
- BK21 사업단
- 캡스톤 디자인 예산
- 한국연구재단(NRF) 학회참가 신청

## 산출물

- [ ] arXiv 프리프린트 PDF + DOI
- [ ] IROS PaperCept 제출 확인 메일
- [ ] GitHub `v1.0-paper-arxiv-submitted` 태그
- [ ] README citation 갱신
- [ ] 대학·연구실 홈페이지 게시

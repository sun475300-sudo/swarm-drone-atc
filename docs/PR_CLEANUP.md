# PR 정리 권고 (2026-06-04)

총 18개 열린 PR을 카테고리별로 정리 권고. 본 세션 11개 + 다른 세션 7개.

## ✅ 머지 권고 (본 세션 11개)

CI 확인 후 차례로 머지.

| PR | 작업 | 충돌 위험 |
|---|---|---|
| #81 | P730 i18n + P733 LIVE + Track E/F 신설 | low (HTML + ROADMAP) |
| #84 | P731 layer panel merge | low (HTML 부분) |
| #88 | P732 CPA 공간 해시 | low (HTML 부분) |
| #89 | P734 키보드 스크러버 | low (HTML 부분) |
| #90 | Ultra Plan + P701 + P710 docs | none (신규 docs) |
| #91 | P734 멀티뷰 cursor | low (HTML 부분) |
| #92 | P735 EO/IR adapter | low (maritime HTML) |
| #93 | Track A 10 + B 후반 + C P720 + E PoC + F | none (신규 파일) |
| #94 | P740/742/743/744/750/751/754 | none (신규 파일) |
| #95 | STATUS_REPORT + 차트·CI·CHANGELOG | none (신규 파일) |
| #96 | P707 §4-§7 + P710 슬라이드 + P742 평가기 + README | none (신규 파일) |

**권고 머지 순서**: #93 → #94 → #95 → #96 (docs/코드 우선) → #90 → #84 → #88 → #89 → #91 → #92 → #81 (HTML 충돌 주의)

## ⚠️ 다른 세션 PR — 중복/스테일 판단

### 머지 권고 (1)
| PR | 이유 |
|---|---|
| **#87** | Track C P711 React 프론트엔드 MVP — **우리 PR 어디에도 없는 진짜 미구현** ✅ |

### 중복으로 close 권고 (7)
| PR | 사유 |
|---|---|
| #85 | P733 ws_bridge LIVE — 우리 PR #81의 P733과 중복 (대안 구현) |
| #86 | P734 멀티뷰 — 우리 PR #89·#91의 P734와 중복 |
| #77 | P732 (구버전 main `f1ac8ee` 기반, 스테일) |
| #79 | P732 (구버전 main 기반, 스테일) |
| #80 | P732 (구버전 main 기반, 스테일) |
| #82 | P732 (#88 후속 시도, 중복) |
| #83 | P732 (#88 후속 시도, 중복) |

본 세션 #88이 최신 main(`c712bbd`) 기반이고 가장 깔끔하므로 #82/#83 close.

## 📋 처리 순서 권고

### Step 1 (즉시)
1. `#93`(Track A+B+C+E+F docs 일괄) 머지 — 가장 큰 가치, 충돌 없음
2. `#94`(P740-P754) 머지 — mypy fix 적용됨
3. `#95`(STATUS_REPORT) 머지 — 메타문서

### Step 2 (CI 확인 후)
4. `#96`(P707/P710/P742) 머지
5. `#90`(Ultra Plan + P701) 머지
6. `#87`(P711 React) 평가 후 머지

### Step 3 (HTML 충돌 주의)
7. `#84`(P731) → `#88`(P732) → `#89`(P734) → `#91`(P734 멀티뷰) → `#92`(P735) 순차
8. `#81`(P730 i18n + P733 LIVE) 마지막 — Track E/F 섹션 추가가 다른 ROADMAP 변경과 충돌 가능

### Step 4 (스테일 정리)
9. `#77/#79/#80/#82/#83/#85/#86` close

## 🎯 머지 후 상태

- 모든 본 세션 PR 머지: Phase 691-755 진척 **89%** (58/65)
- 잔여 (사용자 환경): Track A 실기, P707 §4-§7 실험 결과 그래프, IROS 투고, Track F LOI

## 자동화 명령 (참고)

```bash
# 본 세션 PR 일괄 ready (draft → ready) — 사용자가 GitHub 웹에서
# Step 1
gh pr merge 93 --merge --auto
gh pr merge 94 --merge --auto
gh pr merge 95 --merge --auto

# Step 4 (정리)
for n in 77 79 80 82 83 85 86; do
  gh pr close $n --comment "중복/스테일 — PR #88(P732) 또는 본 세션 PR이 main 기반 최신."
done
```

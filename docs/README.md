# SDACS 공식 웹사이트

> Swarm Drone Airspace Control System — 공식 랜딩 사이트
> APF + WebGPU 기반 군집드론 공역통제 자동화 시스템

이 폴더는 **그대로 GitHub Pages에 배포할 수 있는 정적 웹사이트**입니다.
별도 빌드 단계가 필요 없습니다 — `index.html`만 서빙하면 됩니다.

## 미리보기 (로컬)

```bash
cd sdacs-official-site
python -m http.server 8000
# 브라우저에서 http://localhost:8000
```

## GitHub Pages 배포 (2가지 방법)

### ① GitHub Actions로 자동 배포 (권장)

1. 이 폴더 내용을 저장소의 `docs/` 디렉토리로 이동/복사합니다.
2. 루트에 `.github/workflows/deploy.yml`을 함께 커밋합니다 (이 폴더에 포함됨).
3. GitHub → **Settings** → **Pages** → **Source: GitHub Actions** 로 설정.
4. `main`에 푸시하거나 Actions 탭에서 수동 실행.
5. 약 1~2분 후 아래 URL로 접속 가능:

```
https://sun475300-sudo.github.io/swarm-drone-atc/
```

### ② 브랜치 기반 배포

- Settings → Pages → Source: `Deploy from a branch` → `main` / `/docs`
- `.nojekyll` 파일이 포함돼 있어 Jekyll 전처리가 비활성화됩니다.

## 파일 구성

```
sdacs-official-site/
├── index.html              # 메인 랜딩 (한/영 토글, 다크모드, 모바일 대응)
├── simulator.html          # Three.js WebGPU 3D 시뮬레이터
├── scenarios.html          # Chart.js 시나리오 비교 대시보드
├── test-report.html        # pytest 커버리지 리포트
├── 404.html                # 커스텀 404 페이지
├── favicon.svg             # SVG 파비콘 (SDACS 로고)
├── manifest.webmanifest    # PWA 매니페스트
├── robots.txt              # 검색 크롤러 설정
├── sitemap.xml             # 사이트맵
├── .nojekyll               # Jekyll 비활성화
├── CNAME                   # (선택) 커스텀 도메인
├── images/                 # 15개 figure (PNG+SVG)
├── report/                 # v6 · v7 · v3 docx
├── presentation/           # pptx
├── docs/                   # 아키텍처·매뉴얼·벤치마크·스크립트 md
└── .github/workflows/      # Pages 자동 배포
    └── deploy.yml
```

## 기능 체크리스트

- ✅ 모바일 퍼스트 반응형 (≥320px)
- ✅ 한국어/English 실시간 토글
- ✅ 라이트/다크 테마 자동 + 수동 토글
- ✅ Open Graph · Twitter Card · Schema.org JSON-LD
- ✅ 스크롤 fade-in 애니메이션 (prefers-reduced-motion 존중)
- ✅ 라이트박스 이미지 갤러리 (ESC/클릭 닫기)
- ✅ 스크롤 복귀 버튼, skip-to-content 링크
- ✅ WCAG 대비비·키보드 포커스 유지
- ✅ SEO 메타 + 사이트맵 + robots
- ✅ 외부 의존성 최소화 (구글 폰트만)

## 커스터마이징

- 색상 팔레트: `index.html` 상단 `:root` CSS 변수
- 소셜/링크: `<footer>`의 `a[href]`
- 히어로 문구: `.hero` 섹션 `<h1>` 및 `.subtitle`
- 통계 수치: `.hero-stats .hero-stat .n` · `.metric-value`

## 라이선스

MIT © 2026 Jang Sunwoo

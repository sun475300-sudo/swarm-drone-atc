# Permanent URL Setup Guide — SDACS

**목적:** SDACS 프로젝트를 영구적/안정적으로 외부에서 접근 가능한 형태로 만들기 위한 단계별 가이드. 무료 방법 중심, 발표(2026-04-23) 이전 필수 항목 표시.

---

## 1. 지금 즉시 사용 가능한 URL들 (✅ 이미 설정됨)

모든 링크는 발표에 그대로 사용 가능합니다.

| 용도 | URL | 비고 |
|---|---|---|
| **메인 허브** (단일 QR용) | <https://sun475300-sudo.github.io/swarm-drone-atc/go.html> | ⭐ 이거 하나만 QR로 만들면 됨 |
| 프로젝트 홈 | <https://sun475300-sudo.github.io/swarm-drone-atc/> | 랜딩 페이지 |
| 3D 시뮬레이터 v2 | <https://sun475300-sudo.github.io/swarm-drone-atc/swarm_3d_simulator_v2.html> | 신규 버전 |
| 3D 시뮬레이터 v1 | <https://sun475300-sudo.github.io/swarm-drone-atc/swarm_3d_simulator.html> | 원본 안정판 |
| GitHub 저장소 | <https://github.com/sun475300-sudo/swarm-drone-atc> | 소스 코드 |
| 최종 보고서 | <https://sun475300-sudo.github.io/swarm-drone-atc/report/SDACS_Final_Report_v6.docx> | 다운로드 |
| 감사 리포트 | <https://sun475300-sudo.github.io/swarm-drone-atc/AUDIT_2026-04-20.md> | 내부 개선 |

→ **QR 코드는** `docs/qr/` 폴더에 생성 완료. 인쇄용 PNG와 확대해도 깨지지 않는 SVG 두 가지로 있음.

---

## 2. Zenodo 영구 DOI (무료, 학술용)

**발표 전 필수: 20분 소요.** DOI는 한 번 발급되면 절대 변하지 않으므로 논문·이력서·레퍼런스에 인용 가능.

### 순서

1. **Zenodo 가입 및 GitHub 연동**
   - <https://zenodo.org/> 접속 → "Log in with GitHub"
   - GitHub OAuth 승인 후 `Account → GitHub` 메뉴로 이동
   - `sun475300-sudo/swarm-drone-atc` 저장소 **토글 ON**

2. **첫 릴리즈 태그 생성**
   ```
   git tag -a v1.0.0 -m "SDACS v1.0 — Capstone final release"
   git push origin v1.0.0
   ```

3. **GitHub에서 Release 작성**
   - <https://github.com/sun475300-sudo/swarm-drone-atc/releases/new>
   - Tag: `v1.0.0`
   - Title: `SDACS v1.0 — Capstone Design Final Release`
   - Description: 주요 기능 요약 (v2 시뮬레이터, 감사 리포트 등)
   - **Publish release** 클릭

4. **Zenodo가 자동으로 아카이빙**
   - 보통 1~5분 내 아카이브 완료
   - DOI 형태: `10.5281/zenodo.XXXXXXX`
   - 예: `https://doi.org/10.5281/zenodo.10234567`

5. **CITATION.cff 업데이트**
   - 루트의 `CITATION.cff` 파일 `doi:` 필드에 발급받은 DOI 추가
   - `docs/index.html` JSON-LD 구조화 데이터에도 `identifier` 필드로 추가

### 📁 관련 파일 (이미 준비됨)

- `.zenodo.json` — 메타데이터 정의 (릴리즈 시 Zenodo가 자동으로 읽음)
- `CITATION.cff` — Google Scholar 색인용

---

## 3. 무료 커스텀 서브도메인

구매 없이 예쁜 도메인 얻는 방법. **신청 후 승인까지 1~3일** 걸리므로 발표 전 통과 가능성은 반반.

### 3-A. `.js.org` (JavaScript 프로젝트 전용)

- 예시: `sdacs.js.org`
- 신청: <https://github.com/js-org/js.org> → `cnames_active.js` PR 제출
- 규칙: 활성 JavaScript 프로젝트여야 함 — 본 프로젝트의 3D 시뮬레이터는 JS 기반이므로 **자격 충족**.
- 소요: 보통 1~3일

### 3-B. `is-a.dev` (개발자 포트폴리오용)

- 예시: `sdacs.is-a.dev`
- 신청: <https://github.com/is-a-dev/register> → `domains/sdacs.json` PR
- 규칙: 한 개발자당 한 서브도메인
- 소요: 1~2일

### 3-C. `.eu.org` (학술/비영리용)

- 예시: `sdacs.eu.org`
- 신청: <https://nic.eu.org/>
- 소요: 2주+ (발표 전 못 받음)

### 적용 방법 (승인 후)

1. 저장소 루트(`docs/`가 아닌 저장소 루트)에 `docs/CNAME` 파일 생성 — 내용은 도메인 하나:
   ```
   sdacs.js.org
   ```
2. GitHub Pages 설정에서 커스텀 도메인 입력 → **Enforce HTTPS** 체크
3. 약 1시간 내 적용

**템플릿:** `docs/CNAME.example` 파일이 준비되어 있음. 적용 시 `CNAME`으로 이름 변경.

---

## 4. 짧은 URL & QR 코드 전략

### 4-A. 발표용 짧은 URL

**가장 짧으면서도 자체 호스팅:** `sun475300-sudo.github.io/swarm-drone-atc/go.html`

이 `go.html` 페이지가 허브 역할:
- 한 QR로 들어오면 시뮬레이터·보고서·GitHub 다 선택 가능
- 모바일 최적화
- 접근성 (스크린 리더, 키보드 내비)
- PPT에 한 줄로 적기 좋음

### 4-B. 더 짧게: bit.ly / tinyurl

- bit.ly: 회원가입 → 커스텀 alias로 `bit.ly/sdacs2026` 등
- tinyurl.com: 회원가입 없이 바로 가능
- is.gd: 영구 유효성 없음(권장 안 함)

**권장:** bit.ly 커스텀 alias로 `bit.ly/sdacs2026` 만들면 명함/슬라이드에 한 줄 들어감.

### 4-C. QR 코드 (이미 생성됨)

`docs/qr/` 폴더:

| 파일 | 용도 |
|---|---|
| `go.svg` / `go.png` | ⭐ **이거 써라** — 허브 페이지 |
| `landing.svg` / `.png` | 랜딩 직접 |
| `v2.svg` / `.png` | v2 시뮬레이터 직접 |
| `v1.svg` / `.png` | v1 시뮬레이터 직접 |
| `github.svg` / `.png` | GitHub 저장소 |
| `report.svg` / `.png` | 보고서 PDF 직접 |
| `audit.svg` / `.png` | 감사 리포트 |

**인쇄 용도:** `.svg` (무한 확대 가능) → 명함/포스터용
**슬라이드 용도:** `.png` (600×600, 컬러 #0055AA) → PPT 직접 삽입

---

## 5. 발표 전 체크리스트 (2026-04-23)

- [ ] **Zenodo 릴리즈 태그 발행** — DOI 확보 (20분)
- [ ] **GitHub Pages 배포 확인** — `https://sun475300-sudo.github.io/swarm-drone-atc/` 열어보기
- [ ] **go.html QR 코드 PPT 마지막 슬라이드에 삽입** — 300×300px 이상
- [ ] **bit.ly 커스텀 alias** 생성 (선택, 5분)
- [ ] **오프라인 폴백 준비** — v2 시뮬레이터를 로컬에서 실행 가능하도록 USB에 복사
- [ ] **발표 중 Wi-Fi 실패 대비** — 60초 MP4 녹화본 준비 (`docs/demo_fallback.mp4`)
- [ ] **handout.html을 A4로 인쇄** — `docs/handout.html` (아래 6절)
- [ ] **`.js.org` 서브도메인 신청** (선택, 발표 전 통과 가능성 ~50%)

---

## 6. 프린트용 핸드아웃

`docs/handout.html`이 A4 1장에 맞춰 디자인된 발표 부록이다.

- 헤더: SDACS 타이틀 + 저자
- 핵심 KPI 3~5개
- QR 3개 (시뮬레이터 / 보고서 / GitHub)
- 연락처

브라우저에서 열고 `Ctrl+P` → "배경 인쇄" 체크 → PDF 저장 또는 종이 인쇄.

---

## 7. 영속성(Permanence) 요약표

| 방법 | 영구성 | 무료 | 소요 | 발표 전 가능? |
|---|---|---|---|---|
| GitHub Pages URL | ★★★ (저장소 유지 중엔 영원) | ✅ | 즉시 | ✅ 이미 됨 |
| Zenodo DOI | ★★★★★ (영구 학술 표준) | ✅ | 20분 | ✅ |
| bit.ly 커스텀 | ★★ (계정 유지 시) | ✅ | 5분 | ✅ |
| `.js.org` 서브도메인 | ★★★ | ✅ | 1~3일 | 반반 |
| 구매 도메인 | ★★★★ (갱신 시) | ❌ | 30분 | — |
| Wayback Machine 스냅샷 | ★★★★ (영구 보존) | ✅ | 2분 | ✅ |

### Wayback Machine 아카이빙 (추가 보험)

<https://web.archive.org/save/https://sun475300-sudo.github.io/swarm-drone-atc/>

이 URL을 브라우저에서 한 번 열면 Internet Archive가 스냅샷을 영구 보존합니다. 저장소가 미래에 사라져도 접근 가능.

다음 URL들도 각각 한 번씩 열어두기를 권장:

- <https://web.archive.org/save/https://sun475300-sudo.github.io/swarm-drone-atc/swarm_3d_simulator_v2.html>
- <https://web.archive.org/save/https://sun475300-sudo.github.io/swarm-drone-atc/swarm_3d_simulator.html>
- <https://web.archive.org/save/https://sun475300-sudo.github.io/swarm-drone-atc/go.html>
- <https://web.archive.org/save/https://github.com/sun475300-sudo/swarm-drone-atc>

---

## 8. 부록 — `js.org` 신청 템플릿

이미 내용을 준비했으니 Fork 후 그대로 사용 가능.

**Fork 대상:** <https://github.com/js-org/js.org>

**편집할 파일:** `cnames_active.js`

**추가할 라인 (알파벳 순 정렬 위치에):**

```js
,"sdacs": "sun475300-sudo.github.io/swarm-drone-atc"
```

**PR 제목:**
```
add sdacs.js.org — Swarm Drone Airspace Control System
```

**PR 설명 템플릿:**
```markdown
## Project
SDACS — Swarm Drone Airspace Control System

## URL requested
sdacs.js.org → sun475300-sudo.github.io/swarm-drone-atc

## About
Swarm drone airspace control automation system built with Three.js r175,
SimPy, and APF (Artificial Potential Field) collision avoidance. Academic
capstone project at Mokpo National University. The live 3D simulator at
the above URL is fully JavaScript-based (WebGL2 / Three.js).

## JS content confirmation
- [x] Primary content is JavaScript (Three.js-based 3D simulator)
- [x] Not commercial
- [x] Live site currently deployed at GitHub Pages
- [x] Domain will redirect via GitHub Pages CNAME

## Author
Sunwoo Jang — @sun475300-sudo — Mokpo National University
```

---

문의/수정: `docs/AUDIT_2026-04-20.md` 의 A-섹션 참고.

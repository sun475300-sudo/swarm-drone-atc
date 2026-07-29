# SDACS 배포 가이드

마지막 정리: **2026-07-30**. 이 문서는 `main`의 현재 배포 경로만 설명합니다. 과거 릴리스 수치나 로컬 산출물 존재 여부는 배포 성공의 증거가 아닙니다.

## 1. GitHub Pages: 정적 웹 사이트와 시뮬레이터

공개 주소: <https://sun475300-sudo.github.io/swarm-drone-atc/>

Pages는 `main` 브랜치의 `docs/` 디렉터리를 배포합니다. `.github/workflows/deploy-pages.yml`은 메인 시뮬레이터 정본과 Three.js vendor 파일을 `docs/`로 동기화한 후 Pages artifact를 배포합니다.

### 배포 전 로컬 확인

```bash
python scripts/build_simulator.py
python scripts/build_simulator.py --check
```

`--check`이 성공하면 다음 사본과 정적 산출물이 정본과 일치합니다.

- `visualization/swarm_3d_simulator.html`
- `docs/swarm_3d_simulator.html`
- `docs/simulator.html`
- `build/simulator/`

### Pages 배포 절차

```bash
git status
git add <변경 파일>
git commit -m "docs: update deployment content"
git push origin main
```

푸시 뒤 Actions의 `Deploy SDACS to GitHub Pages` 완료를 확인합니다.

- 사이트: <https://sun475300-sudo.github.io/swarm-drone-atc/>
- 메인 시뮬레이터: <https://sun475300-sudo.github.io/swarm-drone-atc/simulator.html>
- 해양 시뮬레이터: <https://sun475300-sudo.github.io/swarm-drone-atc/maritime_detection_simulator.html>

GitHub Pages는 정적 호스팅입니다. FastAPI, WebSocket, 데이터베이스가 필요한 서비스는 별도 ASGI 호스팅 환경에 배포해야 합니다.

## 2. 정적 시뮬레이터만 배포하기

```bash
python scripts/build_simulator.py
python -m http.server 8123 --directory build/simulator
```

`build/simulator/` 전체를 정적 호스팅 서비스에 업로드합니다. `simulator.html`, `vendor/three/`, `manifest.webmanifest`, `sdacs-sw.js`를 함께 유지해야 합니다.

HTML 파일을 `file://`로 직접 열면 ES module/CORS 문제로 Three.js가 로드되지 않을 수 있습니다.

## 3. Electron 데스크톱 패키지

```bash
npm ci
npm run build:simulator
npm run pack
npm run dist:win
```

- Windows: `npm run dist:win`
- macOS: `npm run dist:mac` (macOS에서 실행)
- Linux: `npm run dist:linux` (Linux에서 실행)

산출물은 `dist-desktop/`에 생성되며 Git에서 제외됩니다. 현재 GitHub Releases에는 SDACS 앱 설치 파일이 공개되어 있지 않으므로, 배포하려면 새 버전 태그와 GitHub Actions 릴리스가 필요합니다.

## 4. GitHub Release 발행

`v*` 태그를 푸시하면 `.github/workflows/desktop-build.yml`이 Windows·macOS·Linux 빌드를 실행하고 성공한 산출물을 GitHub Release에 첨부하도록 구성돼 있습니다.

```bash
git tag -a vX.Y.Z -m "SDACS vX.Y.Z"
git push origin vX.Y.Z
```

태그 전에는 최소한 다음을 확인합니다.

```bash
python scripts/build_simulator.py --check
ruff check src/ simulation/
python -m pytest tests/ -q
```

릴리스 페이지에서 각 OS 산출물, 설치·실행 여부, 코드 서명 정책을 확인한 뒤 공개합니다.

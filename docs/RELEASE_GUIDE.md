# 🚀 SDACS Desktop Release Guide

*Last updated: 2026-06-04 — v1.1.0 (Phase 1-9 + 해양 PWA + 데스크탑 빌드 v1.1)*

본 가이드는 **3-OS 데스크탑 앱**(Win NSIS · macOS DMG · Linux AppImage)을 GitHub Releases에 자동 발행하는 절차입니다.

## 📋 사전 체크리스트

- [ ] `package.json` 의 `version` 이 새 릴리스 버전(예: `1.1.0`)으로 갱신
- [ ] `README.md` · `STATUS_REPORT.md` 의 "최신 업데이트" 섹션 갱신
- [ ] 회귀 테스트 통과: `pytest tests/ --no-cov` (4,140/4,140)
- [ ] E2E 테스트 통과: `pytest tests/e2e/ --no-cov` (67/68)
- [ ] 사본 동기화 (md5 일치): `swarm_3d_simulator.html` × `visualization/` × `docs/×2`
- [ ] 로컬 Linux 빌드 검증: `npm run dist:linux` → `dist-desktop/*.AppImage` 정상

## 🔁 릴리스 흐름 (사용자 수동)

### 1. 버전 태그 생성 + 푸시
```bash
git tag -a v1.1.0 -m "SDACS Desktop v1.1.0 — Phase 1-9 + 해양 PWA + 데스크탑 빌드"
git push origin v1.1.0
```

### 2. desktop-build.yml 워크플로우 자동 실행
- 트리거: `push` to `v*` 태그 (paths 필터 없음)
- 매트릭스: `ubuntu-latest`, `windows-latest`, `macos-latest`
- 각 OS에서:
  - `npm install` (electron 32.x + builder 25.x)
  - `npm run dist:linux` / `dist:win` / `dist:mac`
  - `dist-desktop/` artifact 업로드 (30일 보존)
- 모든 빌드 성공 시 `release` job 실행:
  - `softprops/action-gh-release@v2` 액션
  - **공개 Release 자동 발행** (`draft: false`, `prerelease: false`)
  - 파일: `*.exe` (Win NSIS) · `*.dmg` (Mac) · `*.AppImage` (Linux)
  - 자동 릴리스 노트 생성

### 3. 릴리스 확인
```bash
# GitHub CLI (선택)
gh release view v1.1.0 --repo sun475300-sudo/swarm-drone-atc

# 또는 웹
https://github.com/sun475300-sudo/swarm-drone-atc/releases/tag/v1.1.0
```

## 🛠 GitHub Desktop 사용자

CLI 가 어색하면 GitHub Desktop 으로도 가능:
1. `Branch` 메뉴 → `Create Tag…`
2. 태그 이름 `v1.1.0` 입력 → Description `Phase 1-9 + 해양 PWA 완성판`
3. `Repository` 메뉴 → `Push origin` (태그 포함)

## 📦 빌드 결과 검증 방법

### Linux AppImage
```bash
chmod +x SDACS-Simulator-1.1.0-x86_64.AppImage
./SDACS-Simulator-1.1.0-x86_64.AppImage
# 또는 ASAR 내부 검증:
./SDACS-Simulator-1.1.0-x86_64.AppImage --appimage-extract
npx asar list squashfs-root/resources/app.asar | head
```

### Windows NSIS
1. `SDACS-Simulator-1.1.0-Setup.exe` 다운로드
2. 더블 클릭 → 설치 마법사
3. 시작 메뉴 → "SDACS Simulator" 실행

### macOS DMG
1. `SDACS-Simulator-1.1.0-x64.dmg` (Intel) / `*-arm64.dmg` (Apple Silicon) 다운로드
2. DMG 마운트 → Applications 폴더로 드래그
3. **첫 실행**: Gatekeeper 차단 시 우클릭 → 열기

## 🔬 ASAR 검증 (전체 패키징 무결성)

본 세션 v1.1.0 AppImage 검증 결과 (2026-06-04, 로컬 Linux 빌드):

| 파일 | ASAR 내 위치 | 상태 |
|---|---|---|
| `swarm_3d_simulator.html` | `/swarm_3d_simulator.html` | ✅ |
| `maritime_detection_simulator.html` | `/maritime_detection_simulator.html` | ✅ |
| `manifest.webmanifest` | `/manifest.webmanifest` | ✅ |
| `sdacs-sw.js` | `/sdacs-sw.js` | ✅ |
| `desktop/main.js` | `/desktop/main.js` | ✅ |
| `desktop/home.html` | `/desktop/home.html` | ✅ |
| `desktop/preload.js` | `/desktop/preload.js` | ✅ |
| `vendor/three/three.module.js` | `/vendor/three/three.module.js` | ✅ |
| `vendor/three/addons/controls/OrbitControls.js` | `/vendor/three/addons/...` | ✅ |
| `package.json` | `/package.json` | ✅ |

총 545,978 bytes ASAR (UI는 ELF 105MB 안에 정상 패키징)

## 🚨 트러블슈팅

### "스마트 앱 컨트롤이 차단" (Windows 11)
- 우클릭 → 속성 → 하단 "차단 해제" 체크 → 확인
- 또는 PowerShell: `Unblock-File 'SDACS-Simulator-1.1.0-Setup.exe'`

### macOS "확인되지 않은 개발자" (Gatekeeper)
- 시스템 설정 → 보안 및 개인정보 보호 → "그래도 열기"
- 또는 터미널: `xattr -cr /Applications/SDACS\ Simulator.app`

### Linux AppImage "Permission denied"
```bash
chmod +x SDACS-Simulator-1.1.0-x86_64.AppImage
```

### AppImage "FUSE not available" (Ubuntu 22.04+)
```bash
sudo apt install libfuse2
# 또는 추출 실행:
./SDACS-Simulator-1.1.0-x86_64.AppImage --appimage-extract-and-run
```

## 🔢 버전 정책

- **Patch (`v1.1.1`)**: 버그 픽스, 단일 시뮬레이터 fix
- **Minor (`v1.2.0`)**: 신규 Phase 추가, 새 시나리오, 새 API
- **Major (`v2.0.0`)**: 아키텍처 변경, 호환성 깨짐

## 📜 릴리스 히스토리

| 버전 | 날짜 | 핵심 변경 |
|---|---|---|
| **v1.1.0** | 2026-06-04 | Phase 1-9 (ATC·TAC·CIN·CAM·MIS·INJ·ANA·AUD·MOB) + 해양 PWA + 데스크탑 빌드 |
| v1.0.0 | 2026-04-14 | 초기 데스크탑 빌드 (`workflow` 추가 전 push) — 빌드 미실행 |

## 🔗 참고

- 자동화 워크플로우: [`.github/workflows/desktop-build.yml`](../.github/workflows/desktop-build.yml)
- 마스터 플랜: [`docs/SIMULATOR_MEGA_PLAN.md`](SIMULATOR_MEGA_PLAN.md)
- 상세 명세: [`docs/SIMULATOR_PHASE_PLANS.md`](SIMULATOR_PHASE_PLANS.md)
- electron-builder docs: <https://www.electron.build/configuration/configuration>

# 🚀 SDACS v1.5.0 사용자 로컬 배포 가이드

*2026-06-05 — Phase 200 (Unity) 완료, 사용자 로컬 1단계 액션*

## 📦 사전 상태 (이미 완료된 항목)

- ✅ `package.json` v1.5.0
- ✅ `swarm_3d_simulator.html` 11,695 line + 388 API
- ✅ Linux AppImage 105MB 로컬 빌드 검증
- ✅ Playwright E2E 247/248 통과
- ✅ 회귀 4,140/4,140 통과
- ✅ `git tag v1.5.0` 로컬 생성 완료 (sandbox 푸시는 403)
- ✅ `docs/demo/sdacs_200phase_showcase.webm` 9.4MB 데모 영상

## 🎯 사용자 1줄 명령 (Win/Mac/Linux 자동 빌드 + Releases 발행)

```bash
git pull origin main
git push origin v1.5.0
```

이 두 줄로:
1. 본 세션 main 최신 동기화
2. `v1.5.0` 태그 origin으로 푸시
3. → `.github/workflows/desktop-build.yml` 자동 트리거
4. → ubuntu-latest + windows-latest + macos-latest 3-OS 매트릭스
5. → 빌드 완료 후 `softprops/action-gh-release@v2` 가 **공개 Release 자동 발행**
6. → 사용자가 https://github.com/sun475300-sudo/swarm-drone-atc/releases/tag/v1.5.0 에서 다운로드:
   - `SDACS-Simulator-1.5.0-Setup.exe` (Windows NSIS)
   - `SDACS-Simulator-1.5.0-x64.dmg` (macOS Intel)
   - `SDACS-Simulator-1.5.0-arm64.dmg` (macOS Apple Silicon)
   - `SDACS-Simulator-1.5.0-x86_64.AppImage` (Linux)

## 🧪 빌드 진행 확인

```bash
# GitHub CLI 사용 (gh)
gh run list --workflow=desktop-build.yml --limit 5
gh run watch
```

또는 웹: https://github.com/sun475300-sudo/swarm-drone-atc/actions

빌드 시간 ≈ 8-15분 (3-OS 병렬).

## 🚨 트러블슈팅

### 태그 푸시 시 인증 오류
GitHub Desktop 또는 PAT(Personal Access Token) 재인증 후 재시도

### 빌드 실패 시
- electron-builder 캐시 충돌 → Actions 에서 `Re-run all jobs`
- npm install 실패 → `package-lock.json` 갱신 후 새 태그 (v1.5.1)

### v1.5.0 태그가 이미 존재
```bash
git tag -d v1.5.0        # 로컬 삭제
git push --delete origin v1.5.0  # 원격 삭제
git tag -a v1.5.0 -m "v1.5.0 200 Phase Unity"
git push origin v1.5.0
```

## 🎬 데모 영상

본 세션 자동 녹화: `docs/demo/sdacs_200phase_showcase.webm` (9.4 MB, 60초)
- Playwright headed Chromium (swiftshader WebGL)
- showcase.js 200 Phase 자동 시연 캡처

## 📊 200 Phase 완료 요약

| 항목 | 값 |
|---|:-:|
| 시뮬레이터 코드 | 11,695 line |
| `_sdacs` API | 388 항목 |
| Playwright E2E | 247/248 통과 |
| 회귀 pytest | 4,140/4,140 |
| 종합 통과 | 4,387/4,389 |

## 🔗 관련 문서

- [RELEASE_GUIDE.md](RELEASE_GUIDE.md) — 일반 릴리스 절차
- [RELEASE_NOTES_v1.2.0.md](RELEASE_NOTES_v1.2.0.md) — 50 Phase 시점 노트
- [CHANGELOG.md](../CHANGELOG.md) — v1.0-1.5 통합 이력
- [SDACS_API.md](SDACS_API.md) — 388 API 레퍼런스

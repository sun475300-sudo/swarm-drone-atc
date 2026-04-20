# SDACS 사이트 영구 배포 가이드

**목표**: PC·터미널이 꺼져 있어도 언제든 접속 가능한 영구 URL 확보
**방식**: GitHub Pages (GitHub 서버에서 호스팅, 24/7 자동 운영)
**최종 URL**: https://sun475300-sudo.github.io/swarm-drone-atc/

---

## 현재 상태 (Claude가 준비 완료한 것)

1. `sdacs-official-site/` 의 새 파일(simulator.html, scenarios.html, test-report.html, CNAME 등)을 `docs/` 로 **병합 완료** (기존 파일은 보존, 신규 파일만 추가)
2. `.github/workflows/deploy-pages.yml` 워크플로가 이미 `docs/` 배포하도록 설정되어 있음
3. 배포 자동화 배치 파일 `DEPLOY_PAGES.bat` 작성 완료

---

## 사용자가 할 일 (1단계, 약 30초)

### 방법 1: 더블클릭 (권장)

1. 파일 탐색기에서 `E:\GitHub\swarm-drone-atc\DEPLOY_PAGES.bat` 더블클릭
2. 검은 창이 뜨면서 자동으로 실행:
   - index.lock 정리
   - `git add` → `git commit` → `git push origin main`
3. 마지막에 "Push complete!" 메시지가 나오면 완료

> `git push` 단계에서 GitHub 인증 창이 뜰 수 있습니다. 처음 한 번만 로그인하면 이후에는 저장됩니다. GitHub Desktop이 설치되어 있으면 자동으로 인증이 연결됩니다.

### 방법 2: GitHub Desktop GUI

1. GitHub Desktop 실행
2. 좌측에서 `swarm-drone-atc` 리포 선택
3. 하단에 변경된 파일 목록이 보이면 → "Commit to main" 클릭
4. 상단 `Push origin` 버튼 클릭

---

## 배포 확인 (약 2~3분 후)

1. **Actions 탭**: https://github.com/sun475300-sudo/swarm-drone-atc/actions
   - `Deploy SDACS to GitHub Pages` 워크플로가 초록색 ✓ 로 완료되면 성공
2. **영구 URL**: https://sun475300-sudo.github.io/swarm-drone-atc/
   - 이때부터 PC 꺼도, 터미널 닫아도, 인터넷만 되면 누구나 접속 가능

> **최초 1회**: Settings → Pages 메뉴에서 Source = "GitHub Actions" 로 설정되어 있는지 확인 필요.
> 이미 설정되어 있으면 그냥 넘어가세요. https://github.com/sun475300-sudo/swarm-drone-atc/settings/pages

---

## 임시 Cloudflare 터널 URL vs GitHub Pages

| 항목 | Cloudflare Quick Tunnel | GitHub Pages |
|---|---|---|
| PC 꺼짐 | ✗ 접속 불가 | ✓ 접속 가능 |
| 터미널 닫힘 | ✗ 접속 불가 | ✓ 접속 가능 |
| URL 고정 | ✗ 재시작 시 변경 | ✓ 영구 고정 |
| HTTPS | ✓ | ✓ |
| 비용 | 무료 | 무료 |
| 세션 한도 | 있음 | 없음 (100GB/월 트래픽) |

---

## 문제 해결

**Q. 배치파일에서 `git push` 실패**
- GitHub 계정 로그인이 필요합니다. GitHub Desktop을 한 번 실행해서 로그인하면 Git Credential Manager가 저장합니다.

**Q. "remote rejected" 또는 "non-fast-forward"**
- 원격 브랜치가 앞서 있는 상황입니다. `git pull --rebase origin main` 실행 후 DEPLOY_PAGES.bat 재실행.

**Q. Pages URL 접속 시 404**
- Actions 빌드가 아직 안 끝났거나, Settings → Pages → Source = "GitHub Actions" 가 아닌 상태입니다.

---

*작성: 2026-04-20, Claude*

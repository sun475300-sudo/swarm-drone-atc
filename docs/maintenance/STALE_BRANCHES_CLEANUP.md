# 🌿 SDACS 원격 브랜치 정리 가이드

*Created: 2026-06-25 · 원격 브랜치 누적(411개) 정리 절차 + 안전 스크립트*

## 1. 배경

`origin` 원격에 누적된 브랜치 **411개**:

| 패턴 | 개수 | 비고 |
|---|---:|---|
| `claude/*` | 377 | 이전 Claude Code 세션들 (대부분 stale) |
| `feat/*` | 14 | 일부 활성 |
| `fix/*` | 3 | 일부 활성 |
| `perf/*` | 1 | `perf/simulator-hotloop-allocations` |
| `main` | 1 | active |

이 중 **83개**가 `origin/main` 에 흡수 완료 (안전 삭제 후보).

---

## 2. 안전 삭제 절차

### 2.1 dry-run (사용자 검토)

```bash
# main 흡수 완료 브랜치 리스트만 출력
git branch -r --merged origin/main | grep -v "origin/HEAD\|origin/main"
```

또는 본 스크립트:

```bash
./scripts/cleanup_stale_branches.sh --dry-run
```

### 2.2 실제 삭제 (사용자 명시 승인 후)

```bash
# 옵션 A: 한 번에 모두 삭제 (위험)
./scripts/cleanup_stale_branches.sh --delete-all

# 옵션 B: 한 번에 하나씩 확인 후 삭제 (권장)
./scripts/cleanup_stale_branches.sh --interactive

# 옵션 C: 특정 패턴만 삭제
./scripts/cleanup_stale_branches.sh --pattern "claude/fervent-babbage-*"
```

---

## 3. 삭제 금지 (Safety List)

다음 브랜치는 **삭제 금지** — 작업 보존:

| 브랜치 | 사유 |
|---|---|
| `main` | active default branch |
| `claude/ruview-wifi-analysis-2YG4p` | 현재 작업 브랜치 (PR #283) |
| `fix/desktop-build-cache` | 미머지, 176 커밋 독립 |
| `fix/main-merge-conflicts` | 미머지, 185 커밋 독립 |
| `perf/simulator-hotloop-allocations` | 미머지, 2 커밋 독립 |

### 3.1 검증 절차

삭제 전 각 브랜치마다:
1. `git rev-list --count origin/main..<branch>` → 0 이면 흡수 완료 (안전)
2. 0 이 아니면 → 독립 작업 존재 (보존)
3. 작업 트리에 체크아웃된 브랜치 → 절대 삭제 X (`git switch main` 먼저)

---

## 4. 복구 가능성

GitHub 는 force-pushed 또는 삭제된 브랜치 ref 를 일정 기간 보존 (보통 30~90일). 실수 삭제 시:

```bash
# PR ref 로 복구 (PR이 있던 브랜치)
git fetch origin refs/pull/<NUMBER>/head:recovered-<NUMBER>

# 커밋 SHA 로 복구 (마지막 SHA 안다면)
git fetch origin <SHA>:recovered-<NUMBER>
```

본 PR 의 401e88a 복구 사례 참조 (`recovered-283` ref).

---

## 5. 자동 정리 (장기 후보, 미도입)

장기적으로 GitHub Actions 으로 자동 정리:

```yaml
# .github/workflows/cleanup-stale-branches.yml (계획)
on:
  schedule:
    - cron: '0 0 1 * *'  # 매월 1일
jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - name: List merged branches
        run: |
          git branch -r --merged origin/main \
            | grep -v "origin/HEAD\|origin/main\|origin/claude/ruview-wifi-analysis-2YG4p" \
            > /tmp/stale.txt
          cat /tmp/stale.txt
      # 자동 삭제는 추가 검토 후 활성화
```

**제약**: 자동 삭제는 매우 destructive — 분기별 사용자 검토 후 도입 결정.

---

## 6. 한계 (정직성 공시)

- 본 스크립트는 **로컬 검사** 만 수행 (GitHub API 미사용)
- PR 열린 브랜치 식별 미포함 (수동 확인 필요: `gh pr list --head <branch>`)
- 보호 브랜치 (branch protection) 자동 우회 안 됨

---

## 7. 참조

- `scripts/cleanup_stale_branches.sh` — 본 가이드의 안전 삭제 스크립트
- `docs/CONTINUUM_SUCCESSION_PROTOCOL.md` — Phase 487 거버넌스 (브랜치 권한)
- GitHub Branch Cleanup 권장: <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-branches> (외부)

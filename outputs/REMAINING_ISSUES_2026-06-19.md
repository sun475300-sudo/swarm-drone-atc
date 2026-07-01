# REMAINING ISSUES — 2026-06-19

> 2026-06-16 감사 잔여 + 본 세션 신규 발견. severity는 CI/배포 영향 기준.
> SSOT: `outputs/EXECUTION_LOG_2026-06-19.md`

---

## 우선순위 매트릭스

| ID | Severity | 영역 | 요약 | 차단 대상 |
|---|---|---|---|---|
| **P0-1** | CRITICAL | 미트래킹 코드 | 6개 드래프트 파일이 truncated body / null byte 포함 → `ruff check`·`pytest --collect` 실패 | 로컬 lint, 신규 PR collect |
| **P0-2** | CRITICAL | git 상태 | 작업 트리에 미트래킹 7쌍(src+test) — 의도 불명, 위험한 일괄 add 금지 | 청결한 main HEAD |
| **H-03** | HIGH | DOI | Zenodo DOI 발급 대기 — `v1.5.0` 태그 푸시 필요 | 학술 인용, 6개 placeholder 치환 |
| **H-04** | HIGH | CI 정책 | CI는 `ruff format` 강제 미적용 → 993파일 format diff 누적 가능 | 코드 일관성 |
| **M-01** | MEDIUM | CI 정책 | CI에 `-m "not slow"` 필터 부재 → fast lane PR에서 slow 테스트 그대로 실행 | CI 시간, PR latency |
| **M-02** | MEDIUM | 테스트 | 본 세션 8,271 tests 풀 실행 미수행 (시간 제약) | 회귀 확신도 |
| **M-03** | MEDIUM | git ops | sandbox에서 `.git/index.lock` 권한 락 → 자동 commit/branch 불가 | Cowork 워크플로우 |
| **L-01** | LOW | 데드코드 | 8개 worktree(`.claude/worktrees/agent-*`) 잔존 — 모두 동일 컨텐츠 거의 복제 | 디스크 |
| **L-02** | LOW | docs | AIAA SciTech 2027 D-day(2026-06-04) 결과 비결정 — 투고 여부 사용자 확인 필요 | 발표 일정 |

---

## P0-1 · 미트래킹 드래프트 6개 파일

```
simulation/citation_validator.py        + tests/test_citation_validator.py
simulation/gps_denied_nav.py            + tests/test_gps_denied_nav.py    ← truncated body (478:if __name__ no main())
simulation/llm_atc_production.py        + tests/test_llm_atc_production.py ← truncated body (495:if check.violations no body)
simulation/ntn_link_model.py            + tests/test_ntn_link_model.py    ← I001 import sort only
simulation/onboard_rl_bench.py          + tests/test_onboard_rl_bench.py
simulation/plugin_sdk.py                + tests/test_plugin_sdk.py        ← null byte 0x00 at EOF
simulation/rtm_generator.py             + tests/test_rtm_generator.py
```

**행동 선택지:**
- **A. 폐기**: `rm simulation/{citation_validator,gps_denied_nav,...}.py tests/test_{...}.py` — 의도 불명 + 결함 → 안전한 청소.
- **B. 완성 후 커밋**: 각 파일의 정확한 의도를 사용자와 확인 → body 보완 → 별도 feature 브랜치.
- **권장**: 폐기 후 필요 시 작성자가 깨끗한 브랜치에서 재작성.

---

## P0-2 · 미트래킹 7쌍 일괄 add 금지

```bash
# DO NOT do this:
git add -A   # ← 위 6개 결함 파일 함께 staged 됨
```

**권장:** 본 세션 수정한 트래킹 파일만 명시 add (`git add pyproject.toml CITATION.cff api/fastapi_server.py tests/test_*.py`).

---

## H-03 · Zenodo DOI placeholder

`simulation/archive_redundancy.py`:
- `shipped_registry()` → 현재 `AT_RISK` (DOI 미발급 정직 공시)
- 의존: 첫 `v1.5.0` GitHub Release 태그 푸시

**액션:**
1. `chore/version-sync-1.5.0` 머지
2. `git tag v1.5.0 && git push --tags`
3. GitHub Release 작성 (zenodo webhook 자동 트리거)
4. 발급된 DOI(예 `10.5281/zenodo.XXXXXXX`)로 다음 6곳 치환:
   - `CITATION.cff`
   - `docs/PERMALINK_GUIDE.md:51-52`
   - `docs/standards/ARCHIVE_REDUNDANCY_POLICY.md:33,90`
   - `.zenodo.json`
   - `README.md` (badges 영역, 있는 경우)
   - `CHANGELOG.md` v1.5.0 항목

---

## H-04 · CI `ruff format` 정책 결정 필요

| 옵션 | trade-off |
|---|---|
| ① CI에 `ruff format --check` 추가 | 일관성 ↑, 한 번의 993파일 사전 정리 필요 |
| ② 포맷터 미강제 유지 | drift 누적, 리뷰 노이즈 |
| ③ pre-commit hook만 추가 (CI 미강제) | 점진적 정리, 강제력 약함 |

→ 권장: ① — `pyproject.toml`에서 `ruff>=0.4` → `ruff~=0.7` 으로 핀 → 단일 PR로 일괄 format → CI 강제.

---

## M-01 · CI fast lane 슬로우 제외 도입

`.github/workflows/ci.yml`에 다음 추가 권장:

```yaml
- name: Test (fast lane)
  run: pytest -m "not slow and not e2e and not gpu" -n auto --maxfail=20

- name: Test (slow lane, nightly)
  if: github.event.schedule  # 또는 'workflow_dispatch'
  run: pytest -m "slow or e2e" -n 2 --timeout=300
```

---

## M-02 · 풀 회귀 실행 (8,271 tests)

본 세션 미수행. 권장 명령:

```bash
pytest -q -n auto --maxfail=999 \
  --ignore=tests/test_citation_validator.py \
  --ignore=tests/test_gps_denied_nav.py \
  --ignore=tests/test_llm_atc_production.py \
  --ignore=tests/test_onboard_rl_bench.py \
  --ignore=tests/test_plugin_sdk.py \
  --ignore=tests/test_rtm_generator.py \
  > outputs/full_run_$(date +%F).log 2>&1
```

기대 결과: 4,094 → 8,271 증가 분에서 대부분 PASS. 잠재 회귀: ODYSSEY Phase 488/489/490 신규 모듈.

---

## L-01 · `.claude/worktrees/agent-*` 8개 잔존

```bash
.claude/worktrees/agent-a192c7d2d4c90dc71/
.claude/worktrees/agent-a6693b9a1f2c82b6d/
.claude/worktrees/agent-a7a87e336c49bab9a/
.claude/worktrees/agent-a962fa3833592866d/
.claude/worktrees/agent-aa1b63afc16635de1/
.claude/worktrees/agent-ad0f775c89ee40b51/
.claude/worktrees/agent-aef7a36e8ec89e371/
.claude/worktrees/agent-afaba199e8b9bd190/
```

각 worktree에 fastapi_server.py·CHANGELOG.md·docs 전체 복제. 디스크 비용 큼 (× 8).
**권장:** `git worktree list` 확인 후 `git worktree remove` 일괄 정리.

---

## L-02 · AIAA SciTech 2027 추상 투고 결과 확인

- 2026-06-04 D-day 지남 (3주 전)
- P701 (commit `c54829f2`): "투고 전략 IROS 2026(1순위) / AIAA SciTech 2027(2순위)"
- **사용자 확인 필요:** SciTech 추상이 실제 투고됐는지 / IROS로 우선순위 변경 후 SciTech 보류 결정인지

---

## 다음 우선 작업 Top 3

1. **`chore/version-sync-1.5.0` PR 분리·머지** → `v1.5.0` 태그 푸시 → Zenodo DOI 자동 발급 → 6곳 placeholder 일괄 치환
2. **P0 정리**: 미트래킹 7쌍 폐기 or 완성 결정 → `git clean -fd` 또는 별도 feature 브랜치
3. **CI 정책 결정** (H-04 + M-01): ruff format 강제 도입 및 fast/slow lane 분리

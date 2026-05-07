# swarm-drone-atc branch merge plan (2026-05-03)

## main 기준 ahead/behind
- local main vs origin/main: 0/0 (sync 상태)
- 워킹 트리 깨끗 (수정 사항 없음)

## 분류

### 1) Merged into local main (정리 가능, 자동 삭제 후보)
- claude/atc-broad-except-20260502-150627
- claude/atc-formation-flight-20260427-024340
- claude/atc-hypothesis-tests-20260502-223805
- claude/atc-imgur-localize-20260427-081624
- claude/atc-p703-benchmarks-20260503-050107
- claude/atc-p705-metrics-20260502-150603
- claude/atc-test-count-20260503-041747
- claude/cool-mendeleev-90751f
- claude/jolly-hypatia-a8d2d7

### 2) NOT merged into local main (수동 처리)
- claude/atc-ruff-audit-20260503-050142
- claude/laughing-pasteur-d5f0fb

## 자동 머지 대상
없음 — merged 그룹은 이미 main 에 포함되어 있어 단순 삭제만 함.

## 정리 액션 (자동 .bat)
- merged 그룹 9개 로컬 브랜치 삭제 (`git branch -d <name>`)
- no-merged 그룹은 이름만 출력

swarm-drone-atc 레포 배치 파일 안내 (Cowork Claude 자동 생성, 2026-05-03)

[현재 상태]
- main 이 origin/main 과 sync 상태 (ahead/behind 0/0).
- 워킹 트리 클린.
- 발견 버그 없음 (가벼운 점검). 별도 코드 수정 없음.
- 스모크 테스트: tests/test_apf.py + test_drone_state.py + test_apf_property.py
  → 32 passed.

[배치 파일]
1. PUSH_FIX_TO_MAIN.bat
   - .git/index.lock 자동 제거
   - 스모크 pytest 통과 시에만 batch helper 파일들을 commit + push
   - 실패 시 중단

2. MERGE_ALL_BRANCHES_TO_MAIN.bat
   - origin fetch
   - 이미 main 에 merge 된 9개 로컬 브랜치 자동 삭제
   - merge 안 된 2개는 이름만 출력 (claude/atc-ruff-audit, claude/laughing-pasteur)

[전체 테스트 실행 (선택)]
torch 가 필요한 일부 테스트는 PUSH 스크립트에서 건너뜁니다.
전체 실행하려면:
  pytest tests/ --ignore=tests/test_phase661_670_ai.py --ignore=tests/test_coverage_boost_2.py --ignore=tests/test_coverage_boost_4.py --ignore=tests/test_coverage_boost_5.py --ignore=tests/test_new_modules.py

[실행 방법]
cmd 창에서:
  cd /d E:\GitHub\swarm-drone-atc
  PUSH_FIX_TO_MAIN.bat

또는 통합 실행:
  E:\PUSH_ALL_REPOS_TO_MAIN.bat

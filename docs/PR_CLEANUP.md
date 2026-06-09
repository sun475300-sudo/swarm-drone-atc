# PR 정리 권고 (2026-06-09 일일 점검)

> 이전 권고(2026-06-04, #77~#96 대상)는 모두 처리 완료되어 본 문서로 갱신함.

## 일일 점검 결과 요약

| 항목 | 상태 |
|---|---|
| 작업 브랜치 | `claude/fervent-babbage-dd443e` (main `e5c8ff6`와 동기) |
| 회귀 테스트 | **3,902 pass + 250 skip, 실패 0** (샌드박스 누락 의존성 `pandas`/`dash`/`plotly`/`hypothesis` 설치 후 16건 전부 통과 재확인) |
| ROADMAP 진척 | 코드 로드맵 99.5% 완료. 잔여는 사용자 환경(HW/GPU/API/외부기관) 의존 |
| 코드 내 실제 TODO | 4건 — 전부 아래 클린 드래프트 PR로 커버됨 |
| 열린 PR | **30개** (대부분 이미 main 반영된 obsolete 중복) |

main HEAD에서 확인:
- `main.py:487` `simulate --output` 옵션 존재 → "simulate --output JSON" CI 복구 PR 전부 obsolete
- `frontend/` 디렉터리 존재 (P711 React, 커밋 `ced8481`) → #138 obsolete

---

## ✅ 머지 권고 — 진짜 미완성 TODO를 해소한 클린 드래프트 (2026-06-09, 4건)

코드 내 마지막 4개 실 TODO를 각각 해소한 신규 작업. 충돌 위험 낮음(서로 다른 모듈).

| PR | 작업 | 해소한 TODO |
|---|---|---|
| #204 | onboard_bridge ATTITUDE yaw 헤딩 폴백 | `src/hardware/onboard_bridge.py` HITL yaw |
| #205 | P707 논문 `main.tex` §2-§7 통합 | 논문 초안 §4-§7 보강 |
| #206 | P736 `SDACSGymEnv` 실동작 구현 (+12 테스트) | `src/rl/ppo_collision.py` reset/step/obs/reward 스텁 |
| #207 | P741 Raft 로그 일관성 검사 §5.3 + 팔로워 catch-up | `src/raft/airspace_controller_ha.py` `on_append_entries` 로그 검사 |

→ #206은 `mergeable_state: clean` 확인. 권고 머지 순서: **#205 → #204 → #206 → #207** (docs·독립 모듈 우선).

## 🤖 Dependabot (2건) — 보안 패치, 검토 후 머지

| PR | 내용 |
|---|---|
| #202 | esbuild·vite·vitest bump (/frontend) |
| #203 | vite·@vitejs/plugin-react·vitest bump (/frontend) |

→ 동일 패키지군이므로 둘 중 최신(#203) 머지 후 #202 자동 close 가능. `frontend` vitest 5/5 통과 확인 후 진행.

## ❌ Close 권고 — 이미 main 반영된 obsolete (16건)

### CLI 벤치마크 복구 — `simulate --output`은 이미 main `da73009`에 머지됨 (15건)
`#120 #121 #125 #126 #130 #131 #132 #133 #134 #135 #136 #137 #139 #140 #141`

→ 모두 동일한 "나이틀리 벤치마크 CI RED 복구" 대안 구현. main에 이미 옵션 존재하므로 전부 중복.

### P711 React — 이미 main `ced8481`에 머지됨 (1건)
`#138`

## ⚠️ 검토 필요 — main 반영 여부 확인 후 판단 (5건)

`STATUS_REPORT.md`는 200 Phase(STELLAR 51-100·HYPER 전부) 완료를 명시. 아래 PR들은 해당 Phase를 *추가*한다고 주장 → 이미 main에 반영된 대안 구현일 가능성 높음. 머지 전 main과 diff 확인 권고.

| PR | 내용 | 비고 |
|---|---|---|
| #127 | STELLAR Phase 51 LLM Multi-Agent | #128에 포함 가능 |
| #128 | STELLAR Phase 51-55 자율 결정 5종 | STATUS상 완료 표기 |
| #124 | HYPER Phase 18 AR Overlay | STATUS상 완료 표기 |
| #123 | _sdacs API 자동 문서 생성기 | main 반영 여부 확인 |
| #122 | HYPER Phase 12 데스크탑 멀티 윈도우 | main 반영 여부 확인 |
| #165 | IROS 논문 §4-§7 | #205로 대체 가능성 |
| #158 | ROADMAP P755 완료 반영 | P755는 사용자 환경 의존 — 실제 완료 여부 확인 |
| #129 | 일일 점검 2026-06-05 | 스테일 docs |

## 📋 처리 순서 권고

1. **머지**: #205 → #204 → #206 → #207 (코드 마지막 TODO 해소)
2. **Dependabot**: #203 머지 (#202 자동 close)
3. **Close (obsolete)**: CLI 15건 + #138 = 16건 일괄 close
4. **검토 후 결정**: #122·#123·#124·#127·#128·#129·#158·#165 (main diff 확인)

머지+close 완료 시 열린 PR 30 → 8 이하로 정리, 코드 로드맵 TODO 0건 도달.

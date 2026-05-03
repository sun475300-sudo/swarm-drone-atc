# A2-09 Ruff Lint Audit — 2026-05-03

**Tool**: `ruff check . --select I,F,E --exit-zero --statistics`
**Scope**: 전체 저장소 (archive/ 포함)
**총 errors**: **1,860건** (1,380 auto-fixable, 480 수동)

본 문서는 코드 변경 없는 **분석 보고서**. 실제 fix 는 단계별 별 PR 사이클로 권장.

---

## 1. Rule 별 통계

| Rule | Count | Auto-fix | 분류 | 권장 단계 |
|------|-------|----------|------|----------|
| **F401** unused-import | 688 | ✅ | 안전 | **1단계** |
| **I001** unsorted-imports | 655 | ✅ | 안전 (isort) | **1단계** |
| **E402** module-import-not-at-top | 153 | ❌ | 의도 가능 (sys.path 조작) | 4단계 (수동 검토) |
| **E501** line-too-long | 112 | ❌ | 스타일 | 5단계 (선택) |
| **F841** unused-variable | 106 | ❌ | 수동 (간혹 의도적) | 3단계 |
| **E741** ambiguous-variable-name | 44 | ❌ | 수동 (`l`, `I`, `O`) | 5단계 (선택) |
| **F541** f-string-missing-placeholder | 32 | ✅ | 안전 | **1단계** |
| **E702** multiple-statements-semicolon | 31 | ❌ | 수동 | 4단계 |
| **E731** lambda-assignment | 18 | ❌ | 수동 | 5단계 (선택) |
| **F821** undefined-name | 9 | ❌ | **버그 가능성** | **2단계 (조사 필수)** |
| **E401** multiple-imports-on-one-line | 5 | ✅ | 안전 | **1단계** |
| **invalid-syntax** | 4 | ❌ | **심각 가능** | **2단계 (조사 필수)** |
| **E701** multiple-statements-colon | 1 | ❌ | 수동 | 4단계 |
| **F402** import-shadowed-by-loop-var | 1 | ❌ | 수동 | 3단계 |
| **F811** redefined-while-unused | 1 | ❌ | 수동 | 3단계 |

---

## 2. 활성 코드 vs Archive 분리 — **중요 발견**

`F821` (undefined-name) **9건 전부 `archive/simulation_unused/` 안**:
- `digital_twin_sync_v3.py` — TupleState 미정의
- `mission_auction_system.py` — bid 미정의
- `monte_carlo_runner.py` — pd (pandas) forward-ref 문제 (런타임 import)
- 외 archive 파일들

`invalid-syntax` 4건 중 **3건이 archive/**, 1건이 활성 코드 (`visualization/advanced_dashboard.py:21`).

→ **활성 코드는 F821/invalid-syntax 경고 거의 0**. 시뮬레이터 / 컨트롤러 / 분석 모듈 모두 안전.

---

## 3. 단계별 권장 PR 사이클

### 1단계 (auto-fix, 안전) — F401 + I001 + F541 + E401 = **약 1,380건**

```
ruff check . --select F401,I001,F541,E401 --fix
```

- 한 번에 적용해도 의미 변경 없음 (미사용 import 제거, import 정렬, 빈 f-string 일반 문자열로).
- 변경 범위: 광범위 (many files).
- **별 PR 권장 — 단일 commit, "ruff --fix safe rules"**.
- 회귀 위험: 매우 낮음 (CI 통과 시점이면 의미 동일).

### 2단계 (조사 필수) — F821 + invalid-syntax = 13건

- 9 건 F821 → archive/ 위주, 폐기로 결론 가능 (또는 archive 자체를 lint 제외)
- 4 건 invalid-syntax → 1 건 visualization/advanced_dashboard.py 활성, **즉시 조사**
- 권장: 활성 1건만 별 PR 로 fix, archive 는 ruff `[tool.ruff.lint.exclude]` 에 추가

### 3단계 (수동, 가벼움) — F841 + F811 + F402 = 108건

- F841 unused-var 는 의도적인 경우 (디버깅 / 향후 사용 예정) 도 있음
- 모듈 단위 분리 PR (예: simulation/ 따로, src/ 따로)

### 4단계 (수동, 스타일 위반) — E402 + E702 + E701 = 185건

- E402 153 건은 sys.path 조작 후 import 같은 의도적 패턴 다수
- 모듈별 검토 후 noqa 부여 또는 정상화

### 5단계 (선택, cosmetic) — E501 + E741 + E731 = 174건

- 라인 길이 / 변수명 / lambda — 가독성 개선이지만 우선순위 낮음

---

## 4. 즉시 적용 권장 ruff 설정 변경

`pyproject.toml [tool.ruff.lint]` 에 추가 권장:

```toml
[tool.ruff.lint.per-file-ignores]
"archive/**" = ["F401", "F811", "F841", "F821", "E402", "E701", "E702"]
"visualization/simulator_3d.py" = ["E402"]  # sys.path 조작 패턴
```

→ 분석 1,860 → 활성 코드 약 **400건 수준** 으로 즉시 감소.

---

## 5. 결론

- **활성 코드 품질은 양호** — F821/invalid-syntax 사실상 0건.
- 1,860 errors 중 1,380 (75%) 는 auto-fix 안전.
- 별 PR 5단계 사이클 으로 정리 권장. 각 단계 100~700건 변경 규모.
- 본 PR 은 **분석 + 권장만**. 실제 fix 는 사용자 검토 후 별 사이클.

## 6. 후속 자동 가능 작업 (사용자 승인 후)

- [ ] `pyproject.toml` archive/ ignore rule 추가 (5분, 즉시 1,400+ 알림 감소)
- [ ] 1단계 auto-fix `--select F401,I001,F541,E401 --fix` (별 PR, 회귀 위험 낮음)
- [ ] 2단계 F821 archive 제외 / advanced_dashboard.py:21 invalid-syntax 1건 fix
- [ ] visualization/advanced_dashboard.py:21 즉시 조사

---

*Last updated: 2026-05-03.* 본 분석으로 ruff 결과를 우선순위 + 위험 분류. fix 적용 보류, 별 사이클로.

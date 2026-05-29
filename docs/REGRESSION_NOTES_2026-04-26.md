# Regression Notes — 2026-04-26

## 배경

Phase 660 완료 직후 CI 실패 2건 발견. 두 건 모두 즉시 수정 완료.

---

## 회귀 1: torch import OSError — Windows DLL 차단

### 현상

`apf_engine.py` 가 `import torch` 시 `OSError: [WinError 126]` 발생.
Windows 보안 정책으로 DLL 로드 차단 환경(학교 전산실 등)에서 재현.

### 영향 범위

| 파일 | 변경 내용 |
|------|----------|
| `simulation/apf_engine.py` | `try/except OSError` fallback → CPU NumPy 경로 |
| `simulation/cbs_planner/*.py` | 동일 패턴 적용 |
| `simulation/voronoi_airspace/*.py` | 동일 패턴 적용 |
| `simulation/heatmap_generator.py` | 동일 패턴 적용 |

### 수정 커밋

`0d4dafa`, `c13f72d` (PR #19)

### 검증

```bash
# GPU 없는 환경에서 정상 실행 확인
python -c "from simulation.apf_engine import APFEngine; print('OK')"
```

---

## 회귀 2: pyproject.toml build-backend 오타

### 현상

CI 런 24931567631: `pip install -e .` 단계에서 `ModuleNotFoundError`.

### 원인

```toml
# BEFORE (잘못됨)
build-backend = "setuptools.backends.legacy:build"

# AFTER (수정됨)
build-backend = "setuptools.build_meta"
```

### 수정 커밋

`a59fd48` (PR #19)

---

## 회귀 3: src/hardware/onboard_bridge.py mypy 오류 4건

### 현상

`mypy` 타입 검사 단계에서 `onboard_bridge` 모듈 오류 4건.

### 수정

`pyproject.toml` `[tool.mypy.overrides]` 에 `src.hardware.*` 추가.

### 수정 커밋

`d6b437f` (PR #19)

---

## 후속 작업

- [x] A0-01: torch fallback 7파일 적용 완료
- [x] A0-02: build-backend 오타 수정 완료
- [x] A1-01: `tests/test_apf_engine_fallback.py` 회귀 방지 테스트 4건 추가
- [x] A0-03: CI 재실행 → 녹색 확인 완료 (PR #19 머지 후)

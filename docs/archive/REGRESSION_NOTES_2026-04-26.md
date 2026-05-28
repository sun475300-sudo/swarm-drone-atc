# 회귀 노트 — 2026-04-26

## 발견된 회귀 2건

### 1. torch import OSError 가 simulator 기동을 막음 (P0)

**증상**: Windows 환경에서 `python main.py simulate` 실행 시 다음과 같이 죽었음.

```
OSError: [WinError 4551] 애플리케이션 제어 정책에서 이 파일을 차단했습니다.
Error loading "...\torch\lib\c10_cuda.dll" or one of its dependencies.
```

스택 끝은 `simulation/apf_engine/__init__.py:17 → simulation/apf_engine/apf_gpu.py:19 (import torch)`.

**근본 원인**: 5개 GPU 가속 모듈의 torch import 가드가 **`ImportError`만** 잡고 있었음.

```python
# Before
try:
    import torch
    _TORCH_AVAILABLE = True
except ImportError:           # ← OSError 안 잡음
    _TORCH_AVAILABLE = False
```

Windows Application Control이 `c10_cuda.dll` 같은 의존 DLL을 차단하면 OSError(WinError 4551)가 발생하는데, 가드를 빠져나와 simulator 전체가 죽음. README의 *"GPU 미감지 시 CPU 자동 폴백"* 약속과 어긋남.

**수정**: `(ImportError, OSError)` 로 가드 확장.

| 파일 | 변경 |
|------|------|
| `simulation/apf_engine/apf_gpu.py:18-23` | `except (ImportError, OSError)` |
| `simulation/apf_engine/__init__.py:14-25` | `except (ImportError, OSError)` + `_USE_GPU` 플래그를 `_TORCH_AVAILABLE` 기반으로 재계산 |
| `simulation/apf_engine/multi_gpu.py:12-17` | 동일 |
| `simulation/cbs_planner/cbs_gpu.py:11-15` | 동일 |
| `simulation/voronoi_airspace/voronoi_gpu.py:11-15` | 동일 |
| `simulation/heatmap_generator.py:12-17` | 동일 |

**커밋**: `0d4dafa`, `c13f72d`.

**검증**:
- `python main.py simulate --duration 30 --seed 42 --drones 20` 정상 완료, GPU `NVIDIA GeForce RTX 5070 Ti` 인식, KPI 정상 (충돌 0, 해결률 100%).
- `pytest tests/test_apf.py` → 14 passed.
- 회귀 방지 테스트 추가: `tests/test_apf_engine_fallback.py` (4 tests, OSError 모의).

### 2. CI 의존성 설치 단계 실패 — `pip install ".[dev]"` (P0)

**증상**: 2026-04-25 이후 `main` 브랜치 푸시의 모든 CI run이 빨간불.

```
pip._vendor.pyproject_hooks._impl.BackendUnavailable:
  Cannot import 'setuptools.backends.legacy'
##[error]Process completed with exit code 2.
```

영향 받은 워크플로: `.github/workflows/ci.yml` (run id `24931567631` 등).

**근본 원인**: `pyproject.toml:3` 의 `build-backend` 가 잘못된 모듈 경로.

```toml
# Before
build-backend = "setuptools.backends.legacy:build"   # 존재하지 않는 모듈
```

setuptools 패키지에는 `setuptools.backends.legacy` 라는 모듈이 없음 — 정상 모듈은 `setuptools.build_meta` (또는 legacy mode가 필요할 때만 `setuptools.build_meta:__legacy__`).

**수정**:
```toml
# After
build-backend = "setuptools.build_meta"
```

**커밋**: `a59fd48`.

**검증**:
- `python -c "from setuptools import build_meta"` 정상.
- `python -m build --sdist --no-isolation` → `swarm_drone_atc-0.1.0.tar.gz` 생성 성공.
- 다음 CI run에서 의존성 설치 단계 통과 예상.

## 후속 작업

- [x] 회귀 방지 테스트 (`tests/test_apf_engine_fallback.py`)
- [ ] CI run 녹색 확인 (push 후 watch)
- [ ] `archive/` 내 동일 패턴(except ImportError) 점진 정리는 별도 PR

## 교훈

- **try/except ImportError 만으로는 native lib 로드 실패를 못 잡는다.** Windows DLL 차단·동적 라이브러리 누락·CUDA 초기화 실패 같은 OSError 계열까지 커버해야 README 약속을 지킬 수 있다.
- **build-backend 문자열은 setuptools 메이저 업데이트마다 검증.** `setuptools.backends.legacy:build` 는 한 번도 존재한 적이 없는 경로 — 처음부터 잘못 적혀있던 것을 setuptools 79 가 더 엄격하게 검증하면서 드러남.
- **회귀 추적**: AUDIT C-01 ("Run full test suite + coverage report") 와 함께, OSError 시나리오까지 포함한 import 가드 회귀 테스트는 모든 GPU 가속 모듈의 표준 가드가 되어야 한다.

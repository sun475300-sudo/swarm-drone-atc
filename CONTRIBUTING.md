# Contributing to SDACS / 기여 가이드

> Mokpo National University 캡스톤 디자인 프로젝트 — 외부 기여를 환영합니다.

## 시작하기

```bash
git clone https://github.com/sun475300-sudo/swarm-drone-atc.git
cd swarm-drone-atc

# 1. Python 3.10+ 필요
python -m pip install --upgrade pip
pip install ".[dev]"

# 2. (선택) GPU 가속
pip install torch --index-url https://download.pytorch.org/whl/cu128

# 3. 시뮬 한 번 돌려보기
python main.py simulate --duration 30 --seed 42 --drones 20
```

## 변경 작업 흐름

1. **Issue 먼저** — 큰 변경은 Issue 로 의도 공유 후 시작.
2. **브랜치 명명**
   - 기능: `feat/<주제>` (예: `feat/voronoi-edge-coloring`)
   - 버그: `fix/<주제>` (예: `fix/torch-dll-fallback`)
   - 문서: `docs/<주제>`
3. **테스트 우선** — 새 동작은 새 테스트로 락. `tests/test_*.py` pattern.
4. **로컬 검증**
   ```bash
   pytest tests/ -v --tb=short --cov=src --cov=simulation
   mypy src/
   ```
5. **PR**
   - Draft 로 시작, CI 통과 후 ready-for-review.
   - 본문에 무엇을/왜 + 검증 방법.
   - 한국어/영어 모두 OK.

## 커밋 메시지 규칙

```
<type>: <description>

<optional body>
```

**type**: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`

예시:
```
fix: torch import OSError 처리 — Windows DLL 차단 graceful fallback
docs: README 테스트 수 동기화 (2722→3330)
test: APF 경로 효율 회귀 케이스 추가 (#42)
```

## 스타일

- **Python**: PEP 8, 타입 힌트 권장, `ruff` + `mypy --ignore-missing-imports`
- **파일 크기**: 800줄 미만 권장 — 넘어가면 모듈 분해 검토
- **함수 길이**: 50줄 미만 — 넘으면 헬퍼 추출
- **immutability**: dataclass 는 `frozen=True` 또는 `NamedTuple` 우선
- **broad except 금지**: 명시적 예외 타입 사용

## 테스트 정책

- 최소 커버리지 75% (`pytest --cov`).
- 새 모듈은 단위 테스트 + 통합 테스트(가능 시).
- E2E 시나리오는 `tests/test_simulator_scenarios.py` 패턴 따라가기.
- `pytest.mark.slow` 로 느린 테스트(>10s) 표시.

## 시뮬레이션 모듈 추가 가이드

`simulation/` 에 새 알고리즘을 넣을 때:

1. 단일 책임 원칙 — 한 파일 = 한 알고리즘.
2. `simulation/__init__.py` 에서 export.
3. 회귀 테스트 (`tests/test_phase<N>.py`) 추가.
4. `README.md` "Core Algorithms" 표 갱신 (선택).

## GPU 가속 모듈

GPU 가속 코드 (`*_gpu.py`) 는 다음 가드 패턴을 반드시 따라야 합니다.

```python
try:
    import torch
    _TORCH_AVAILABLE = True
except (ImportError, OSError):
    # OSError covers Windows DLL load failures (WinError 4551 등)
    _TORCH_AVAILABLE = False
```

CPU NumPy 백엔드로 graceful fallback 가능해야 함. 이유: `docs/REGRESSION_NOTES_2026-04-26.md`.

## 보안 / 비공개 정보

- secrets / API key / .env 절대 커밋 금지.
- 문제 신고: `SECURITY.md` 참조 (sun475300@gmail.com).
- 알려진 한계 / 감사 결과: `docs/AUDIT_2026-04-20.md`.

## Phase 통합

이 저장소는 **Phase 1~660 + 661~690 완료** 상태이고, **Phase 691~720** 이 작업 중.
새 작업은 가능한 적절한 Phase 범위에 매핑하여 `tests/test_phase<N1>_<N2>.py` 에 회귀 테스트 추가.
대규모 변경은 `docs/MASTER_TODO_ATC.md` / `ROADMAP.md` 갱신.

## License

MIT. 기여 시 동일 라이선스에 동의한 것으로 간주합니다.

---

문의: [GitHub Issues](https://github.com/sun475300-sudo/swarm-drone-atc/issues) · 메일 sun475300@gmail.com

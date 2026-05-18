# 대형 파일 분해 설계서

**Phase:** P2-3/P2-4 (ADDITIONAL_WORK_PLAN_2026-05-15)
**Date:** 2026-05-18
**Scope:** `visualization/simulator_3d.py` (1,769 lines) · `simulation/simulator.py` (861 lines)
**Goal:** 각 파일의 분리 경계를 확정하여 이후 PR이 안전하게 진행될 수 있는 기준 문서를 만든다.

---

## 1. 원칙

- 파일당 200-400 라인 권장, 800 라인 상한 (coding-style.md).
- 기능 회귀 방지: 분리 전 테스트 통과 상태를 기준으로, 각 PR은 기존 테스트가 그대로 통과해야 한다.
- 한 PR에 하나의 모듈 분리만 포함. 동시에 두 파일을 리팩터하지 않는다.
- 분리 후 원래 `simulator_3d.py`와 `simulator.py`는 얇은 re-export shell로 남겨 하위 호환성을 유지하고, 한 사이클 뒤 제거한다.

---

## 2. `visualization/simulator_3d.py` (1,769 lines)

### 현재 구조

| 라인 범위 | 내용 | 관심사 |
| ---------- | ---- | ------ |
| 1–115 | import, 상수, `FlightPhase`, `DroneState`, `WindModel` | 도메인 값 객체 |
| 116–225 | `SimState` | 대시보드 내장 시뮬레이션 상태 |
| 227–553 | `_in_nfz`, `_assign_goal`, `_step`, `_update`, `_sim_loop` | 내장 물리 엔진 (Dash 전용 미니-sim) |
| 554–600 | `_btn`, `_legend_row`, `_stat` | Dash UI 헬퍼 컴포넌트 |
| 601–1068 | `_nfz_mesh`, `build_figure` 등 | 3D 씬 트레이스 빌더 (Plotly) |
| 1069–1396 | `build_layout()` (HTML 트리) | Dash 레이아웃 |
| 1397–1752 | `_ctrl`, `_refresh`, 콜백들 | Dash 콜백 |
| 1753–1769 | `if __name__ == "__main__"` | 진입점 |

### 문제

1. 내장 물리 엔진 (~327 lines)이 `simulation/simulator.py`의 `_DroneAgent` 로직과 독립적으로 존재 — 두 코드베이스가 동기화 없이 발산할 수 있다.
2. 3D 트레이스 빌더 (~467 lines)와 Dash 레이아웃/콜백 (~684 lines)이 같은 파일 안에 섞여 있어, UI 변경이 물리 로직에 영향을 줄 위험이 있다.

### 제안 분리 구조

```
visualization/
├── __init__.py
├── simulator_3d.py           # thin shell (import + run) — 하위 호환 유지, 1 cycle 후 제거
├── _domain.py                # FlightPhase, DroneState, WindModel, SimState (~150 lines)
├── _embedded_sim.py          # _in_nfz, _assign_goal, _step, _update, _sim_loop (~330 lines)
├── _scene_traces.py          # _nfz_mesh, _corridor_traces, build_figure 등 (~470 lines)
├── _layout.py                # build_layout() HTML 트리 (~330 lines)
└── _callbacks.py             # _ctrl, _wind, _apf_toggle, _refresh 등 (~360 lines)
```

### 분리 우선순위

| 순서 | 모듈 | 이유 |
| ---- | ---- | ---- |
| 1st | `_scene_traces.py` | 물리/UI와 의존이 가장 적음. 순수 함수. |
| 2nd | `_domain.py` + `_embedded_sim.py` | 값 객체와 물리 로직을 함께 꺼내면 `_scene_traces`가 즉시 import 가능. |
| 3rd | `_layout.py` + `_callbacks.py` | Dash app 객체에 의존하므로 마지막에 분리. |

### 장기 제거 대상

`_embedded_sim.py`의 내장 물리 엔진은 `simulation/simulator.py`의 `SwarmSimulator`로 교체하는 것이 이상적이다. 현재는 Dash 반응형 루프와 SimPy 이벤트 루프가 통합되지 않아 바로 교체하기 어렵고, 장기 목표로 별도 추적한다.

---

## 3. `simulation/simulator.py` (861 lines)

### 현재 구조

| 라인 범위 | 내용 | 관심사 |
| ---------- | ---- | ------ |
| 1–67 | import, `_load_yaml`, `_drone_to_apf`, `_estimate_power_w` | 공유 헬퍼 |
| 68–120 | `DroneState` dataclass, 연관 상수 | 도메인 값 객체 |
| 121–431 | `_DroneAgent` (SimPy 프로세스, ~310 lines) | 드론 개별 행동 |
| 432–461 | `_clamp_speed` | 속도 유틸리티 |
| 462–861 | `SwarmSimulator` (~399 lines) | 시뮬레이션 오케스트레이터 |

### 문제

`_DroneAgent` (~310 lines)와 `SwarmSimulator` (~399 lines)가 같은 파일에 있어 총 861 라인. 두 클래스의 역할이 명확히 다르다: `_DroneAgent`는 10 Hz 개별 에이전트 SimPy 프로세스이고, `SwarmSimulator`는 1 Hz 컨트롤러 조율자다 (CLAUDE.md Layer 1/Layer 3 경계).

### 제안 분리 구조

```
simulation/
├── simulator.py              # SwarmSimulator만 남음 (~430 lines after cleanup)
└── drone_agent.py            # _DroneAgent + 관련 헬퍼 + DroneState (~450 lines)
```

**분리 경계 판단 기준:**

- `drone_agent.py`에 들어갈 것: `_DroneAgent`, `_clamp_speed`, `DroneState`, `_drone_to_apf`, `_estimate_power_w`, 개별 드론이 소비하는 상수들
- `simulator.py`에 남을 것: `SwarmSimulator`, `_load_yaml`, `SimulationResult`, 전체 시뮬레이션 파라미터 상수

**순환 의존 주의:** `simulator.py`가 `drone_agent.py`를 import하는 단방향 구조. `drone_agent.py`는 `simulator.py`를 import하지 않는다.

### 분리 전 체크리스트

- [ ] `_DroneAgent`가 `SwarmSimulator`의 속성에 직접 접근하는 라인 목록 작성
  (현재 `sim.env`, `sim.rng`, `sim.apf`, `sim.controller` 등 접근 — 인터페이스 정의 필요)
- [ ] `DroneState`가 `visualization/simulator_3d.py`의 `DroneState`와 다른지 확인 (두 파일 모두 동명 클래스 보유)
- [ ] 분리 후 `pytest tests/ -v`가 2,823+ 모두 통과하는지 확인

---

## 4. 실행 순서 권장

```
PR #A  simulation/drone_agent.py 분리
       └─ simulator.py에서 DroneAgent 관련 코드 꺼냄
          └─ 기존 tests/ 전부 통과 확인

PR #B  visualization/_scene_traces.py 분리
       └─ build_figure 및 trace 함수들 꺼냄

PR #C  visualization/_domain.py + _embedded_sim.py 분리

PR #D  visualization/_layout.py + _callbacks.py 분리

PR #E  visualization/simulator_3d.py shell 정리 (re-export만 남김)
       └─ 한 sprint 뒤 완전 제거
```

---

## 5. 회귀 방지 전략

- 각 PR 전: `pytest tests/ -v --tb=short` 기준 실행 후 스냅샷 비교
- `visualization/simulator_3d.py`는 테스트가 적으므로, 분리 전 `tests/test_visualization.py`에 smoke test 1건 추가 권장 (Dash app 초기화가 예외 없이 완료되는지)
- `simulation/simulator.py` 분리 후 `tests/test_simulator_*.py` 전체 재실행

---

*이 문서는 실제 코드 변경 없이 분리 기준만 확정한다.
코드 변경은 각 PR에서 이 문서를 참조하여 진행한다.*

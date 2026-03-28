# SDACS Development Guide

## Project
군집드론 공역통제 자동화 시스템 (Swarm Drone Airspace Control System)
SimPy 기반 이산 이벤트 시뮬레이션 + Dash 3D 시각화

## Quick Commands
```bash
pytest tests/ -v                              # 전체 테스트 (835개)
python main.py simulate --duration 60         # 기본 시뮬레이션
python main.py scenario high_density          # 시나리오 실행
python main.py monte-carlo --mode quick       # Monte Carlo 스윕
python main.py visualize                      # 3D 대시보드 (localhost:8050)
```

## Architecture
- **Layer 1** (드론): `simulation/simulator.py` — `_DroneAgent` 10Hz SimPy 프로세스
- **Layer 2** (제어): `src/airspace_control/controller/` — `AirspaceController` 1Hz
- **Layer 3** (시뮬): `simulation/` — `SwarmSimulator`, `WindModel`, Monte Carlo
- **Layer 4** (UI): `main.py` CLI, `visualization/simulator_3d.py` Dash

## Key Conventions
- 시뮬레이터 엔진: `SwarmSimulator` (canonical), engine_legacy 삭제됨
- 테스트: `tests/test_*.py`, pytest, 모든 PR 전 835+ 통과 필수
- 드론 수 설정 키: `drones.default_count` (SwarmSimulator가 읽는 키)
- 충돌 해결률 공식: `1 - collisions/(conflicts + collisions)`
- APF 강풍 모드: 풍속 >10 m/s → `APF_PARAMS_WINDY` 자동 전환

## Config Files
- `config/default_simulation.yaml` — 기본 시뮬레이션 파라미터
- `config/monte_carlo.yaml` — MC 스윕 설정
- `config/scenario_params/*.yaml` — 7개 시나리오 정의

## Do NOT
- `engine_legacy.py` 다시 만들지 말 것 (SwarmSimulator로 일원화 완료)
- `random.random()` 대신 `np.random.default_rng(seed)` 사용 (재현성)
- 테스트에서 SimPy 프로세스 직접 호출 금지 — `env.run()` 사용

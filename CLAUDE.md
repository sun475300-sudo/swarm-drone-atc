# SDACS Development Guide

안드레 카파시(Andrej Karpathy) 원칙 기반 행동 가이드라인.
LLM 코딩 실수를 줄이기 위한 규칙 + 프로젝트별 컨텍스트.
**트레이드오프:** 이 가이드라인은 속도보다 신중함에 가중치를 둡니다. 단순 작업에는 판단에 따라 유연하게 적용하세요.

---

## 1. 코딩 전에 생각하기

**가정하지 마라. 혼란을 숨기지 마라. 트레이드오프를 표면화하라.**

구현 전에:
- 가정을 명시적으로 서술할 것. 불확실하면 질문할 것.
- 해석이 여러 가지면 모두 제시할 것 — 조용히 하나만 선택하지 마라.
- 더 단순한 접근법이 있으면 말할 것. 필요하면 반론을 제기할 것.
- 뭔가 불명확하면 멈추고, 뭐가 헷갈리는지 이름 붙이고, 질문할 것.

## 2. 단순함 우선

**문제를 해결하는 최소한의 코드. 추측성 기능 금지.**

- 요청받지 않은 기능 추가 금지.
- 한 번만 쓸 코드에 추상화 금지.
- 요청 없는 "유연성"이나 "설정 가능성" 금지.
- 발생 불가능한 시나리오에 대한 에러 처리 금지.
- 200줄로 썼는데 50줄이면 될 경우, 다시 쓸 것.

자문: "시니어 엔지니어가 이거 과하다고 하겠나?" 그렇다면 단순화.

## 3. 수술적 변경

**필요한 부분만 수정. 자기가 만든 쓰레기만 치울 것.**

기존 코드 수정 시:
- 인접 코드, 주석, 포맷팅을 "개선"하지 마라.
- 고장나지 않은 걸 리팩토링하지 마라.
- 기존 스타일에 맞출 것, 내 취향이 다르더라도.
- 관련 없는 죽은 코드 발견 시 언급만 하고 삭제하지 마라.

내 변경으로 인해 고아가 생겼을 때:
- 내 변경으로 미사용된 import/변수/함수는 제거할 것.
- 기존에 있던 죽은 코드는 요청 없이 삭제하지 마라.

테스트: 변경된 모든 라인은 사용자 요청에 직접 추적 가능해야 한다.

## 4. 목표 주도 실행

**성공 기준을 정의하라. 검증될 때까지 반복하라.**

작업을 검증 가능한 목표로 변환:
- "유효성 검사 추가" → "잘못된 입력에 대한 테스트를 작성하고, 통과시켜라"
- "버그 수정" → "재현 테스트를 작성하고, 통과시켜라"
- "X 리팩토링" → "리팩토링 전후로 테스트 통과를 확인하라"

다단계 작업 시 간단한 계획 서술:
```
1. [단계] → 검증: [확인 사항]
2. [단계] → 검증: [확인 사항]
3. [단계] → 검증: [확인 사항]
```

강한 성공 기준은 독립 반복을 가능하게 한다. 약한 기준("되게 해줘")은 끊임없는 확인이 필요하다.

---

## 5. Project

군집드론 공역통제 자동화 시스템 (Swarm Drone Airspace Control System)
SimPy 기반 이산 이벤트 시뮬레이션 + Dash 3D 시각화

## 6. Quick Commands
```bash
pytest tests/ -v                              # 전체 테스트 (9,156+ collected)
python main.py simulate --duration 60         # 기본 시뮬레이션
python main.py scenario high_density          # 시나리오 실행
python main.py monte-carlo --mode quick       # Monte Carlo 스윕
python main.py visualize                      # 3D 대시보드 (localhost:8050)
```

## 7. Architecture
- **Layer 1** (드론): `simulation/drone_agent.py` — `DroneAgent` 10Hz SimPy 프로세스 (simulator.py가 `_DroneAgent` 별칭으로 임포트)
- **Layer 2** (제어): `src/airspace_control/controller/` — `AirspaceController` 1Hz
- **Layer 3** (시뮬): `simulation/` — `SwarmSimulator`, `WindModel`, Monte Carlo
- **Layer 4** (UI): `main.py` CLI, `visualization/simulator_3d.py` Dash

## 8. Key Conventions
- 시뮬레이터 엔진: `SwarmSimulator` (canonical), engine_legacy 삭제됨
- 테스트: `tests/test_*.py`, pytest, 모든 PR 전 9,156+ 수집/검증 권장
- 드론 수 설정 키: `drones.default_count` (SwarmSimulator가 읽는 키)
- 충돌 해결률 공식: `1 - collisions/(conflicts + collisions)`
- APF 강풍 모드: 풍속 >10 m/s → `APF_PARAMS_WINDY` 자동 전환

## 9. Config Files
- `config/default_simulation.yaml` — 기본 시뮬레이션 파라미터
- `config/monte_carlo.yaml` — MC 스윕 설정
- `config/scenario_params/*.yaml` — 13개 시나리오 정의 (기본 10 + UAM 3)

## 10. 프로젝트 컨텍스트 (선우 전용)

### 주요 프로젝트

| 프로젝트 | 스택 | 핵심 규칙 |
|---------|------|----------|
| **SDACS 캡스톤** | Python, SC2 시뮬레이터, HTML/JS | 4계층 아키텍처·5계층 안전망 구조 유지. Sim-to-Real 파이프라인 용어 통일. |
| **SC2 Swarm Bot** | python-sc2 (burnysc2), PyTorch | ~95% 규칙 기반. RL 코드 추가 시 기존 FSM/규칙 로직 건드리지 말 것. |
| **JARVIS Discord Bot** | Node.js/Python, MCP, Haiku/Opus | MCP 타임아웃 핸들링 필수. 모델 라우팅 로직 변경 시 기존 폴백 체인 보존. |
| **FPV 드론 마운트** | OpenSCAD, TPU 95A | 파라메트릭 설계 유지. 치수 변경 시 연쇄 영향 체크. |

### 코딩 스타일 규칙
- **언어:** 한국어 주석 + 영어 변수명/함수명 혼용 허용.
- **문서:** 학교 제출용 → 공식 어투 (합니다체). 개인 프로젝트 → 자유.
- **Word/PPTX 생성 시:** OOXML 스키마 순서 준수 (cantSplit, keepNext 등 기존 이슈 반복 방지).
- **DXF 출력 시:** Continuous 라인타입으로 통일 (AutoCAD 호환성).

## 11. Do NOT
- `engine_legacy.py` 다시 만들지 말 것 (SwarmSimulator로 일원화 완료)
- `random.random()` 대신 `np.random.default_rng(seed)` 사용 (재현성)
- 테스트에서 SimPy 프로세스 직접 호출 금지 — `env.run()` 사용
- SC2 봇 코드에서 검증 안 된 RL 모듈을 규칙 기반 로직에 직접 연결 금지.
- JARVIS에서 MCP 서버 추가 시 기존 서버 설정 덮어쓰기 금지.
- 캡스톤 보고서에서 GitHub 레포 데이터와 불일치하는 수치 기재 금지.

---

**이 가이드라인이 작동하는 징후:** diff에 불필요한 변경이 줄어들고, 과도한 설계로 인한 재작성이 줄어들고, 구현 후가 아니라 구현 전에 명확화 질문이 나온다.

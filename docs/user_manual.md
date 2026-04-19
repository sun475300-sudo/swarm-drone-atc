# SDACS 사용자 매뉴얼

**군집드론 공역통제 자동화 시스템 (Swarm Drone Airspace Control System)**

SimPy 기반 이산 이벤트 시뮬레이션 + 3D 시각화 플랫폼

---

## 목차

1. [설치 가이드](#1-설치-가이드)
2. [빠른 시작](#2-빠른-시작)
3. [CLI 명령어 참조](#3-cli-명령어-참조)
4. [시나리오 설명](#4-시나리오-설명)
5. [GPU 설정](#5-gpu-설정)
6. [Docker 실행](#6-docker-실행)
7. [REST API](#7-rest-api)
8. [문제 해결 (FAQ)](#8-문제-해결-faq)

---

## 1. 설치 가이드

### 시스템 요구사항

| 항목 | 최소 | 권장 |
|------|------|------|
| Python | 3.10 | 3.11 |
| RAM | 8 GB | 16 GB |
| GPU | - | NVIDIA CUDA 12.x 지원 GPU |
| OS | Windows 10 / Ubuntu 20.04 | Windows 11 / Ubuntu 22.04 |

### Python 환경 설치

```bash
# 저장소 클론
git clone <repository-url> swarm-drone-atc
cd swarm-drone-atc

# 가상환경 생성 및 활성화
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### GPU 가속 (PyTorch CUDA) 설치

GPU 가속을 사용하려면 PyTorch CUDA 버전을 별도로 설치해야 합니다.

```bash
# CUDA 12.x 기준
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

설치 확인:

```bash
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
```

---

## 2. 빠른 시작

### 시뮬레이션 실행

```bash
# 기본 시뮬레이션 (100대 드론, 600초)
python main.py simulate

# 드론 50대, 120초
python main.py simulate --drones 50 --duration 120
```

### 3D 시각화 대시보드

```bash
# Dash/Plotly 기반 대시보드 (http://127.0.0.1:8050)
python main.py visualize

# Three.js 브라우저 시뮬레이터
python main.py visualize-3d
```

### REST API 서버

```bash
# FastAPI 서버 시작 (http://127.0.0.1:8000)
uvicorn api.server:app --host 0.0.0.0 --port 8000

# API 문서 확인
# http://127.0.0.1:8000/docs (Swagger UI)
```

---

## 3. CLI 명령어 참조

### `simulate` - 단일 시뮬레이션

```bash
python main.py simulate [옵션]
```

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--duration` | 600.0 | 시뮬레이션 시간 (초) |
| `--seed` | 42 | 랜덤 시드 (재현성 보장) |
| `--drones` | 100 | 드론 수 |
| `--log-level` | INFO | 로그 레벨 (DEBUG/INFO/WARNING) |

### `scenario` - 시나리오 실행

```bash
# 시나리오 목록 확인
python main.py scenario --list

# 특정 시나리오 실행
python main.py scenario high_density

# 반복 실행 (통계 집계)
python main.py scenario weather_disturbance --runs 5 --seed 42
```

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `name` | - | 시나리오 이름 |
| `--list`, `-l` | - | 시나리오 목록 표시 |
| `--runs`, `-n` | 1 | 반복 횟수 |
| `--seed` | 42 | 기본 시드 |

### `monte-carlo` - Monte Carlo 파라미터 스윕

```bash
# 빠른 스윕
python main.py monte-carlo --mode quick

# 전체 스윕
python main.py monte-carlo --mode full
```

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--mode` | quick | 스윕 모드 (`quick` / `full`) |

### `visualize` - 3D 대시보드

```bash
python main.py visualize [옵션]
```

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--port` | 8050 | 대시보드 포트 |
| `--drones` | 30 | 데모 드론 수 |

### `visualize-3d` - Three.js 시뮬레이터

```bash
python main.py visualize-3d
```

브라우저에서 Three.js 기반 3D 시뮬레이터를 자동으로 엽니다.

### `ops-report` - E2E 운영 리포트

```bash
python main.py ops-report --scenario ops_report --city Seoul --seed 42
```

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--scenario` | ops_report | 리포트 시나리오 이름 |
| `--seed` | 42 | 데이터 생성 시드 |
| `--city` | Seoul | 기상 샘플 도시 |
| `--hour` | 18 | 교통 샘플 시간 |
| `--out-dir` | data/e2e_reports | 리포트 저장 경로 |

---

## 4. 시나리오 설명

SDACS는 8개의 사전 정의된 시나리오를 제공합니다.

| 번호 | 시나리오 | 드론 수 | 설명 |
|------|---------|---------|------|
| S01 | `high_density` | 100 | 정상 고밀도 교통 -- 처리량 한계 및 기준선 충돌률 검증 |
| S02 | `emergency_failure` | 80 | 비행 중 드론 장애 -- 비상착륙 우선순위 및 장애 처리 검증 |
| S03 | `mass_takeoff` | 100 | 대규모 동시 이착륙 -- 출발/도착 시퀀싱 검증 |
| S04 | `route_conflict` | - | 경로 충돌 해소 -- TCAS-like 알고리즘 정확성 검증 |
| S05 | `comms_loss` | 50 | 통신 두절 -- Lost-link 프로토콜 검증 |
| S06 | `weather_disturbance` | 100 | 기상 교란 -- 바람 하 경로 추적 강건성 검증 |
| S07 | `adversarial_intrusion` | 50 | 적대적 드론 침입 -- 탐지 지연시간 및 오탐율 검증 |
| S08 | `multi_city` | 다중 | 다중 도시 동시 운영 -- 서울/부산/대구 3개 공역 병렬 시뮬레이션 |

### 시나리오 실행 예시

```bash
# 고밀도 시나리오 3회 반복
python main.py scenario high_density --runs 3

# 기상 교란 시나리오
python main.py scenario weather_disturbance

# 모든 시나리오 목록 확인
python main.py scenario --list
```

---

## 5. GPU 설정

### APF(Artificial Potential Field) GPU 가속

SDACS는 충돌 회피 연산(APF)에 PyTorch CUDA GPU 가속을 지원합니다.

- 풍속 >10 m/s 시 자동으로 `APF_PARAMS_WINDY` 파라미터로 전환
- GPU 사용 가능 시 자동 감지하여 GPU 백엔드 활성화

### GPU 상태 확인

```bash
# API로 확인
curl http://127.0.0.1:8000/health
# 응답에 GPU/backend 정보 포함

# Python으로 확인
python -c "from simulation.apf_engine import get_apf_backend_info; print(get_apf_backend_info())"
```

### NVIDIA 드라이버 요구사항

| CUDA 버전 | 최소 드라이버 |
|-----------|-------------|
| CUDA 12.1 | 530.30+ |
| CUDA 12.4 | 550.54+ |

---

## 6. Docker 실행

### CPU 모드

```bash
# 빌드
docker build -t sdacs .

# 시각화 대시보드 (포트 8050)
docker run -p 8050:8050 sdacs

# 시뮬레이션 실행
docker run sdacs python main.py simulate --duration 60
```

### GPU 모드

```bash
# GPU 이미지 빌드
docker build -f Dockerfile.gpu -t sdacs-gpu .

# GPU 컨테이너 실행
docker run --gpus all -p 8050:8050 sdacs-gpu

# docker-compose로 실행
docker compose -f docker-compose.gpu.yml up
```

### Docker Compose

```bash
# 기본 실행
docker compose up

# GPU 모드
docker compose -f docker-compose.gpu.yml up

# 백그라운드 실행
docker compose up -d
```

---

## 7. REST API

FastAPI 기반 REST API를 제공합니다.

### 서버 시작

```bash
uvicorn api.server:app --host 0.0.0.0 --port 8000
```

### 주요 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/health` | 서버 상태 및 GPU 정보 |
| POST | `/simulate` | 시뮬레이션 실행 |
| GET | `/scenarios` | 시나리오 목록 |
| POST | `/scenarios/{name}/run` | 시나리오 실행 |

### API 문서

서버 실행 후 브라우저에서 확인:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

---

## 8. 문제 해결 (FAQ)

### Q: `ModuleNotFoundError: No module named 'simpy'`

의존성이 설치되지 않았습니다.

```bash
pip install -r requirements.txt
```

### Q: CUDA가 감지되지 않습니다

1. NVIDIA 드라이버가 설치되어 있는지 확인: `nvidia-smi`
2. PyTorch CUDA 버전 설치 확인:
   ```bash
   python -c "import torch; print(torch.cuda.is_available())"
   ```
3. CPU 전용 PyTorch가 설치된 경우 재설치:
   ```bash
   pip uninstall torch
   pip install torch --index-url https://download.pytorch.org/whl/cu121
   ```

### Q: Windows에서 한글이 깨집니다

`main.py`가 자동으로 UTF-8 인코딩을 설정합니다. 그래도 문제가 있으면:

```bash
set PYTHONIOENCODING=utf-8
python main.py simulate
```

### Q: 시각화 대시보드에 접속이 안 됩니다

1. 포트 충돌 확인: `--port 8051` 등 다른 포트 지정
2. 방화벽 확인: 8050 포트 허용
3. `0.0.0.0`이 아닌 `127.0.0.1`로 접속

### Q: 시뮬레이션이 느립니다

1. GPU 가속 활성화 확인 (위 GPU 설정 참조)
2. 드론 수 줄이기: `--drones 50`
3. 시뮬레이션 시간 줄이기: `--duration 60`
4. Monte Carlo는 `--mode quick` 사용

### Q: Docker GPU 컨테이너가 실행되지 않습니다

1. NVIDIA Container Toolkit 설치 확인:
   ```bash
   # Ubuntu
   sudo apt install nvidia-container-toolkit
   sudo systemctl restart docker
   ```
2. `--gpus all` 플래그 확인
3. 호스트에서 `nvidia-smi` 작동 확인

### Q: 테스트 실행 방법

```bash
# 전체 테스트 (2,722개)
pytest tests/ -v

# 특정 모듈 테스트
pytest tests/test_simulator.py -v

# 커버리지 포함
pytest tests/ --cov=simulation --cov-report=term-missing
```

---

## 설정 파일

| 파일 | 용도 |
|------|------|
| `config/default_simulation.yaml` | 기본 시뮬레이션 파라미터 |
| `config/monte_carlo.yaml` | Monte Carlo 스윕 설정 |
| `config/scenario_params/*.yaml` | 시나리오별 파라미터 (8개) |

### 주요 설정 항목 (`default_simulation.yaml`)

```yaml
simulation:
  seed: 42
  duration_minutes: 10
  time_step_hz: 10        # 시뮬레이션 틱 (10Hz)
  control_hz: 1           # 공역 컨트롤러 틱 (1Hz)

drones:
  default_count: 100
  max_speed_ms: 15.0
  cruise_speed_ms: 8.0
  max_altitude_m: 120.0
  min_altitude_m: 30.0

separation_standards:
  lateral_min_m: 50.0
  vertical_min_m: 15.0
```

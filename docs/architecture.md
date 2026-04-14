# SDACS 아키텍처

## 4-Layer 아키텍처 개요

```mermaid
graph TB
    subgraph "Layer 4: UI / 인터페이스"
        CLI["CLI<br/>(main.py)"]
        DASH["Dash 3D 대시보드<br/>(simulator_3d.py)"]
        API["FastAPI REST API<br/>(api/)"]
        WS["WebSocket 브릿지"]
    end

    subgraph "Layer 3: 시뮬레이션 엔진"
        SIM["SwarmSimulator<br/>(SimPy 이산 이벤트)"]
        WIND["WindModel<br/>(바람 모델)"]
        MC["Monte Carlo<br/>(통계 스윕)"]
    end

    subgraph "Layer 2: 공역 제어"
        ATC["AirspaceController<br/>(1Hz 제어 루프)"]
        VOR["Voronoi 공역분할<br/>🔷 GPU 가속"]
        RA["ResolutionAdvisory<br/>(충돌 해결)"]
    end

    subgraph "Layer 1: 드론 에이전트"
        DRONE["_DroneAgent<br/>(10Hz SimPy 프로세스)"]
        APF["APF 경로 계획<br/>🔷 GPU 가속"]
        CBS["CBS 충돌탐지<br/>🔷 GPU 가속"]
        STATE["DroneState"]
    end

    subgraph "ML / AI 모듈"
        ML["ML 충돌 예측<br/>(PyTorch)"]
        PPO["PPO 강화학습<br/>에이전트"]
        GNN["GNN 통신<br/>네트워크"]
        ONNX["ONNX 내보내기"]
    end

    %% Layer 4 → Layer 3
    CLI -->|시뮬 실행| SIM
    DASH -->|실시간 상태| SIM
    API -->|REST 요청| SIM
    WS -->|실시간 스트림| SIM

    %% Layer 3 → Layer 2
    SIM -->|환경 상태| ATC
    WIND -->|풍속 데이터| ATC
    MC -->|파라미터 스윕| SIM

    %% Layer 2 → Layer 1
    ATC -->|제어 명령| DRONE
    VOR -->|공역 할당| ATC
    RA -->|회피 기동| DRONE

    %% Layer 1 내부
    DRONE --> APF
    DRONE --> CBS
    DRONE --> STATE

    %% ML 연동
    ML -->|예측 결과| ATC
    PPO -->|회피 정책| DRONE
    GNN -->|통신 그래프| DRONE
    PPO --> ONNX

    %% 스타일
    classDef gpu fill:#e1f5fe,stroke:#0288d1,stroke-width:2px
    class APF,CBS,VOR gpu
```

## 데이터 흐름

```mermaid
sequenceDiagram
    participant UI as Layer 4: UI
    participant SIM as Layer 3: SwarmSimulator
    participant ATC as Layer 2: AirspaceController
    participant DRONE as Layer 1: DroneAgent

    UI->>SIM: 시뮬레이션 시작 (duration, 드론 수)
    loop 매 시뮬레이션 스텝
        SIM->>ATC: 환경 상태 전달 (1Hz)
        ATC->>ATC: Voronoi 공역분할 (GPU)
        ATC->>DRONE: 제어 명령
        DRONE->>DRONE: APF 경로 계산 (10Hz, GPU)
        DRONE->>DRONE: CBS 충돌 탐지 (GPU)
        DRONE-->>ATC: 드론 상태 보고
        ATC-->>SIM: 충돌/해결 이벤트
        SIM-->>UI: 실시간 시각화 데이터
    end
```

## GPU 가속 모듈

| 모듈 | 설명 | 기술 |
|------|------|------|
| APF 엔진 | 인공 포텐셜 필드 경로 계획 | PyTorch CUDA |
| CBS 충돌탐지 | 다중 에이전트 충돌 감지 | PyTorch CUDA |
| Voronoi 공역분할 | 동적 공역 파티셔닝 | PyTorch CUDA |
| ML 충돌 예측 | 사전 충돌 위험 예측 | PyTorch + FP16 |
| PPO 에이전트 | 강화학습 회피 정책 | PyTorch + ONNX |

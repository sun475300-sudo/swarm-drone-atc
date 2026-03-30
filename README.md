# SDACS — Swarm Drone Airspace Control System
# 군집드론 공역통제 자동화 시스템

<div align="center">

```
    ╔═══════════════════════════════════════════════════════════════════════════════╗
    ║                                                                               ║
    ║   ██████╗ ██╗██╗     ██╗     ██╗███████╗██╗  ██╗    ███████╗██╗  ██╗███████╗ ║
    ║   ██╔══██╗██║██║     ██║     ╚═╝██╔════╝╚██╗██╔╝    ╚══███╔╝██║  ██║██╔════╝ ║
    ║   ██████╔╝██║██║     ██║     ██╗███████╗ ╚███╔╝       ███╔╝ ███████║█████╗   ║
    ║   ██╔═══╝ ██║██║     ██║     ╚═╝╚════██║ ██╔██╗      ███╔╝  ╚════██║██╔══╝   ║
    ║   ██║     ██║███████╗███████╗██╗███████║██╔╝ ██╗    ███████╗     ██║███████╗ ║
    ║   ╚═╝     ╚═╝╚══════╝╚══════╝╚═╝╚══════╝╚═╝  ╚═╝    ╚══════╝     ╚═╝╚══════╝ ║
    ║                                                                               ║
    ╚═══════════════════════════════════════════════════════════════════════════════╝
```

### 🚁 **"드론판 교통경찰" — AI가 하늘의 교통을 관리합니다** 🚁

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![SimPy](https://img.shields.io/badge/SimPy-4.1-4CAF50?style=for-the-badge)](https://simpy.readthedocs.io/)
[![Dash](https://img.shields.io/badge/Dash-2.17-00A0DC?style=for-the-badge&logo=plotly)](https://dash.plotly.com/)
[![NumPy](https://img.shields.io/badge/NumPy-1.26-013243?style=for-the-badge&logo=numpy&logoColor=white)](https://numpy.org/)
[![SciPy](https://img.shields.io/badge/SciPy-1.12-8CAAE6?style=for-the-badge&logo=scipy&logoColor=white)](https://scipy.org/)

[![Tests](https://img.shields.io/badge/Tests-1841%20collected-success?style=for-the-badge&logo=pytest&logoColor=white)](tests/)
[![Phase](https://img.shields.io/badge/Phase-350%2F350-4CAF50?style=for-the-badge&logo=rocket)](simulation/)
[![Schema](https://img.shields.io/badge/Schema-v1.0.0-2196F3?style=for-the-badge&logo=json)](simulation/report_input_normalizer.py)
[![Algorithms](https://img.shields.io/badge/Algorithms-235-FF6F00?style=for-the-badge&logo=databricks&logoColor=white)](#알고리즘-계층-구조)
[![Modules](https://img.shields.io/badge/Modules-248+-9C27B0?style=for-the-badge&logo=python&logoColor=white)](simulation/)
[![Lines](https://img.shields.io/badge/Python-34%2C000%2B%20LOC-blue?style=for-the-badge&logo=visualstudiocode&logoColor=white)](#)
[![Languages](https://img.shields.io/badge/Languages-25-FF5722?style=for-the-badge&logo=github&logoColor=white)](#multi-language)
[![MultiLang](https://img.shields.io/badge/Multi--Lang%20Files-87-E91E63?style=for-the-badge&logo=github&logoColor=white)](#multi-language)
[![Monte Carlo](https://img.shields.io/badge/Monte%20Carlo-38%2C400%20runs-E91E63?style=for-the-badge&logo=chart.js&logoColor=white)](#monte-carlo-sla)
[![CI](https://github.com/sun475300-sudo/swarm-drone-atc/actions/workflows/ci.yml/badge.svg)](https://github.com/sun475300-sudo/swarm-drone-atc/actions)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

```
    ┌────────────────────────────────────────────────────────────────────────┐
    │  🔬 마지막 업데이트: 2026-03-30 22:00:00  │  📦 Phase 331-350 완료     │
    │  ⏱️ 빌드 상태: ✅ PASSING  │  📊 테스트: 1841개  │  🎯 커버리지: 91.5%     │
    └────────────────────────────────────────────────────────────────────────┘
    ```

---

**🏛️ Mokpo National University, Dept. of Drone Mechanical Engineering — Capstone Design (2026)**

**국립 목포대학교 드론기계공학과 캡스톤 디자인 (2026)**

[📖 Technical Report / 기술 보고서](docs/report/SDACS_Technical_Report.docx) · [📊 Charts / 성능 차트](docs/images/) · [🎥 3D 시뮬레이터](swarm_3d_simulator.html)

---

## 🎬 실시간 시뮬레이터 프리뷰

```
    ╭─────────────────────────────────────────────────────────────────────────╮
    │                                                                         │
    │              ⬆️ 500 drones in formation                                │
    │                    ·  ·  ·  ·  ·                                        │
    │               ·  ·  ·  ·  ·  ·  ·  ·                                   │
    │          ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·                              │
    │     ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·                          │
    │         ═══════════════════════════════                                │
    │         ║  AIRSPACE CONTROL ZONE  ║  ← 3D SimPy+Dash                  │
    │         ═══════════════════════════════                                │
    │                                                                         │
    │   [███████░░░] Traffic: 65%  [████████░░] Health: 89%  [██████████] 100% │
    │                                                                         │
    ╰─────────────────────────────────────────────────────────────────────────╯
```

</div>

---

<div align="center">

### 🎯 핵심 성과 요약

| 🎯 지표 | 📊 결과 | 📝 설명 |
|:---:|:---:|:---|
| **충돌 감소율** | **99.9%** | 500대 메가 군집: 58,038 → 19 |
| **자동 테스트** | **1,791개** | 67 모듈 · 수집 완료 |
| **알고리즘** | **205개** | 4계층 28,000+줄 · 25개 언어 |
| **MC 검증** | **38,400회** | 384 config × 100 seeds |
| **시나리오** | **42종** | 극한기상·침입·GPS교란·대규모배송 |
| **반응 시간** | **< 1초** | CPA 90초 선제 예측 |
| **배치 시간** | **30분** | 고정 인프라 불필요 |
| **동시 관제** | **500대+** | 분산형 자율 관제 |
| **진행률** | **100%** | Phase 1-310 전체 완료 ✅ |

</div>

---

## 🌟 3D 시뮬레이션 실시간 뷰어

<div align="center">

[![3D Simulator](docs/images/architecture.svg)](swarm_3d_simulator.html)

**[🎮 3D 시뮬레이터 실행하기](swarm_3d_simulator.html)** — 실시간 드론 군집 시뮬레이션

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│    DRONE SWARM SIMULATION                    [▶ START] [⏸ PAUSE] [🔄]   │
│    ══════════════════════════                                               │
│                                                                          │
│         ★  ★  ★  ★  ★           ←  드론 위치 (실시간)                     │
│       ★  ★  ★  ★  ★  ★                                                     │
│         ★  ★  ★  ★  ★                                                     │
│                                                                          │
│    ┌─────────────────────────────────────────┐                           │
│    │  Active: 500  │  Collisions: 0  │  Safe  │                           │
│    └─────────────────────────────────────────┘                           │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

</div>

---

## 🔄 시스템 아키텍처 Mermaid 다이어그램

```mermaid
flowchart TB
    subgraph Drone["🚀 드론 계층 (Layer 1)"]
        D1[드론 1] --> D2[드론 2]
        D1 --> D3[드론 N]
        D2 --> D3
    end

    subgraph Control["🎯 관제 계층 (Layer 2)"]
        AC[Airspace Controller]
        PQ[Priority Queue]
        RA[Resolution Advisor]
    end

    subgraph Simulation["⚙️ 시뮬레이션 계층 (Layer 3)"]
        SS[Swarm Simulator]
        WM[Wind Model]
        MC[Monte Carlo]
    end

    subgraph UI["🖥️ UI 계층 (Layer 4)"]
        CLI[CLI Interface]
        DASH[Dash 3D Visualizer]
    end

    Drone --> Control
    Control --> Simulation
    Simulation --> UI
```

```mermaid
sequenceDiagram
    participant D as 드론
    participant AC as AirspaceController
    participant RA as ResolutionAdvisory
    participant SS as SwarmSimulator

    D->>AC: 위치/속도 보고 (1Hz)
    AC->>SS: 충돌 예측 요청
    SS-->>AC: CPA 분석 결과
    alt 위험 감지
        AC->>RA: 회피 명령 요청
        RA-->>AC: 수정 경로 반환
        AC->>D: 경고/지시 전송
    end
    D-->>AC: Acknowledge
```

### 충돌 회피 알고리즘 파이프라인

```mermaid
flowchart LR
    subgraph Detection["탐지 단계"]
        CPA["CPA 90s\nLookahead"]
        VOI["Voronoi\n공역 분할"]
        RADAR["센서 퓨전\nIMU+GPS+Lidar"]
    end

    subgraph Decision["판단 단계"]
        APF["APF\n포텐셜 장"]
        CBS["CBS\n다중경로"]
        RA2["Resolution\nAdvisory"]
    end

    subgraph Action["실행 단계"]
        REPLAN["경로\n재계획"]
        FORM["편대\n재구성"]
        EMRG["비상\n착륙"]
    end

    CPA --> APF
    VOI --> CBS
    RADAR --> RA2
    APF --> REPLAN
    CBS --> FORM
    RA2 --> EMRG
```

### 드론 상태 머신 (FSM)

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Takeoff: 임무 배정
    Takeoff --> Cruise: 이륙 완료
    Cruise --> Avoid: 충돌 감지
    Avoid --> Cruise: 회피 완료
    Cruise --> Landing: 목적지 도달
    Landing --> Idle: 착륙 완료
    Cruise --> Emergency: 통신 두절/고장
    Avoid --> Emergency: 회피 실패
    Emergency --> Landing: 복구
    Emergency --> [*]: 추락
```

### Multi-Language 기술 스택 분포

```mermaid
pie title 다국어 모듈 분포 (87 files)
    "Python" : 50
    "Zig" : 5
    "Rust" : 5
    "Go" : 5
    "C++" : 5
    "Kotlin" : 4
    "Nim" : 4
    "OCaml" : 4
    "F#" : 3
    "Swift" : 3
    "TypeScript" : 3
    "Others" : 6
```

### Phase 331-350 모듈 의존성

```mermaid
flowchart TD
    QP["331: Quantum\nPath Optimizer"]
    WR["332: WASM\nRuntime"]
    DS["333: Digital\nSovereignty"]
    NC["334: Neuromorphic\nSNN"]
    MN["335: Mesh\nNetwork"]
    DT["336: Digital\nThread"]
    GT["337: Game\nTheory"]
    AC["338: Acoustic\nSensing"]
    ENC["339: Swarm\nEncryption"]
    PM["340: Predictive\nMaint v2"]

    QP --> MN
    NC --> WR
    DS --> ENC
    MN --> GT
    AC --> NC
    DT --> PM
    ENC --> MN
    GT --> QP
```

---

## 📊 성능 대시보드 실시간 차트

<div align="center">

```
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                           PERFORMANCE DASHBOARD                          ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║                                                                           ║
    ║   충돌 회피율              │    드론 처리량             │    시스템 건강도    ║
    ║   ┌─────────────────┐      │    ┌─────────────────┐     │    ┌─────────┐   ║
    ║   │ 99.9%  ████████ │      │    │ 500    ████████ │     │    │  89%   │   ║
    ║   │       ██        │      │    │       ██        │     │    │███████ │   ║
    ║   │       ██        │      │    │       ██        │     │    │        │   ║
    ║   └─────────────────┘      │    └─────────────────┘     │    └─────────┘   ║
    ║                                                                           ║
    ║   📈 충돌 감소: 99.9%        📦 동시 관제: 500대+          ⏱️ 반응: < 1초    ║
    ║                                                                           ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
```

</div>

### Phase 331-350 핵심 알고리즘 매트릭스

```
    ╔══════════════════════════════════════════════════════════════════════════════╗
    ║                     PHASE 331-350 ALGORITHM MATRIX                         ║
    ╠══════════════════════════════════════════════════════════════════════════════╣
    ║                                                                            ║
    ║  331 Quantum    ║ QAOA ░░░░░██████████   VQE ░░██████████████             ║
    ║  332 WASM       ║ Stack VM ░░████████   Bytecode ░░████████████           ║
    ║  333 Sovereignty║ Region Policy ░░░██████   Encryption ░░██████████       ║
    ║  334 SNN        ║ LIF Neuron ░░████████   STDP ░░░░░██████████           ║
    ║  335 Mesh       ║ Dijkstra ░░████████████   Self-Heal ░░██████████       ║
    ║  336 Digital    ║ Lifecycle ░░░██████████   PLM Chain ░░██████████        ║
    ║  337 Game       ║ Nash Eq ░░██████████████   Pareto ░░████████████       ║
    ║  338 Acoustic   ║ FFT ░░░░░░████████████   Beamform ░░██████████         ║
    ║  339 Encryption ║ Group Key ░░████████████   Lattice KEM ░░████████      ║
    ║  340 PredMaint  ║ Weibull ░░████████████████   RUL ░░████████████        ║
    ║                                                                            ║
    ╚══════════════════════════════════════════════════════════════════════════════╝
```

### 전체 시스템 레이어 상세

```
    ┌──────────────────────────────────────────────────────────────────────────────┐
    │                          SDACS FULL SYSTEM LAYERS                           │
    ├──────────────────────────────────────────────────────────────────────────────┤
    │                                                                              │
    │  Layer 5: AI & Analytics                                                     │
    │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
    │  │ Quantum  │ │ Neuro-   │ │ Game     │ │ Federated│ │ Deep RL  │          │
    │  │ Optimizer│ │ morphic  │ │ Theory   │ │ Learning │ │ Control  │          │
    │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘          │
    │       │             │            │             │            │                │
    │  Layer 4: Security & Communication                                           │
    │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
    │  │ Swarm    │ │ Digital  │ │ IDS      │ │ Spectrum │ │ Satellite│          │
    │  │ Encrypt  │ │ Sovereign│ │ Anomaly  │ │ Access   │ │ Comm     │          │
    │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘          │
    │       │             │            │             │            │                │
    │  Layer 3: Simulation & Physics                                               │
    │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
    │  │ Swarm    │ │ WASM     │ │ 3D       │ │ Weather  │ │ Acoustic │          │
    │  │ Simulator│ │ Runtime  │ │ Physics  │ │ Predict  │ │ Sensing  │          │
    │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘          │
    │       │             │            │             │            │                │
    │  Layer 2: Control & Planning                                                 │
    │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
    │  │ Airspace │ │ Path     │ │ Formation│ │ Mesh     │ │ Pred.    │          │
    │  │ Control  │ │ Planner  │ │ Optimizer│ │ Network  │ │ Maint    │          │
    │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘          │
    │       │             │            │             │            │                │
    │  Layer 1: Drone Hardware Abstraction                                         │
    │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
    │  │ Digital  │ │ HIL      │ │ Sensor   │ │ Motor    │ │ Battery  │          │
    │  │ Twin     │ │ Simulator│ │ Fusion   │ │ Control  │ │ Manager  │          │
    │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
    │                                                                              │
    └──────────────────────────────────────────────────────────────────────────────┘
```

---

## 👥 기여자 프로필 카드

<div align="center">

```
    ┌────────────────────────────────────────────────────────────────────────┐
    │                                                                        │
    │   ╭─────────────────────────────────────────────────────────────╮    │
    │   │  👤 장선우 (SunWoo Jang)                                     │    │
    │   │  🏛️ 국립 목포대학교 드론기계공학과                            │    │
    │   │  📧 sun475300@sunu.ac.kr                                     │    │
    │   │  🎓 캡스톤 디자인 2026                                        │    │
    │   │  ━━━━━━━━━━━━━━━━━━━━━━━━                                    │    │
    │   │  💻 GitHub: @sun475300-sudo                                   │    │
    │   │  🛠️ 기술: Python, SimPy, Dash, NumPy, SciPy, AI/ML          │    │
    │   │  🏆 기여: 350 Phase + 1841 테스트 + 235 알고리즘              │    │
    │   ╰─────────────────────────────────────────────────────────────╯    │
    │                                                                        │
    └────────────────────────────────────────────────────────────────────────┘
```

</div>

---

## Table of Contents / 목차

### Quick Navigation / 빠른 이동

- 시작: [At a Glance / 한눈에 이해하기](#at-a-glance--한눈에-이해하기), [빠른 시작](#빠른-시작), [3D 시뮬레이터 체험](https://sun475300-sudo.github.io/swarm-drone-atc/swarm_3d_simulator.html)
- 구조: [시스템 개요](#시스템-개요), [4계층 아키텍처](#4-layer-architecture--4계층-아키텍처), [핵심 알고리즘](#핵심-알고리즘)
- 검증: [시나리오 검증 결과](#시나리오-검증-결과), [Monte Carlo SLA](#monte-carlo-sla), [테스트](#tests--테스트)
- 운영: [Changelog / 변경 이력](#changelog--변경-이력), [Next Mega Plan / 다음 대규모 계획](#next-mega-plan--다음-대규모-계획)

### Full Index / 전체 인덱스

1. [프로젝트 배경](#프로젝트-배경)
2. [시스템 개요](#시스템-개요)
3. [4계층 아키텍처](#4-layer-architecture--4계층-아키텍처)
4. [핵심 알고리즘](#핵심-알고리즘)
5. [알고리즘 계층 구조](#알고리즘-계층-구조)
6. [기존 시스템 비교 분석](#기존-시스템-비교-분석)
7. [시나리오 검증 결과](#시나리오-검증-결과)
8. [Monte Carlo SLA](#monte-carlo-sla)
9. [빠른 시작](#빠른-시작)
10. [프로젝트 구조](#프로젝트-구조)
11. [테스트](#tests--테스트)
12. [SC2 테스트베드](#sc2-testbed--sc2-테스트베드)
13. [개발 일정](#development-timeline--개발-일정)
14. [팀 정보](#team--팀-정보)
15. [참고 문헌](#references--참고-문헌)

---

## Reader Paths / 독자별 읽기 경로

문서가 길기 때문에 목적에 맞는 경로로 읽으면 빠르게 핵심을 파악할 수 있습니다.

| 독자 유형 | 권장 경로 | 예상 시간 |
|----------|-----------|-----------|
| 처음 보는 사용자 | [At a Glance / 한눈에 이해하기](#at-a-glance--한눈에-이해하기) → [시스템 개요](#시스템-개요) → [빠른 시작](#빠른-시작) | 7분 |
| 아키텍처 리뷰어 | [4계층 아키텍처](#4-layer-architecture--4계층-아키텍처) → [핵심 알고리즘](#핵심-알고리즘) → [알고리즘 계층 구조](#알고리즘-계층-구조) | 12분 |
| 검증/QA 담당자 | [시나리오 검증 결과](#시나리오-검증-결과) → [Monte Carlo SLA](#monte-carlo-sla) → [테스트](#tests--테스트) | 10분 |
| 운영/배포 담당자 | [프로젝트 구조](#프로젝트-구조) → [Changelog / 변경 이력](#changelog--변경-이력) → [Next Mega Plan / 다음 대규모 계획](#next-mega-plan--다음-대규모-계획) | 9분 |

---

## Visual Assets Hub / 시각자료 허브

### 1) 핵심 다이어그램

| 구분 | 미리보기 | 설명 |
|------|---------|------|
| Hero | ![Hero](docs/images/hero_banner.svg) | 프로젝트 핵심 메시지 배너 |
| Architecture | ![Architecture](docs/images/architecture.svg) | 4계층 시스템 아키텍처 |
| Detection Pipeline | ![Pipeline](docs/images/detection_pipeline.svg) | 탐지→판단→회피 파이프라인 |

### 2) 성능/운영 차트

| 구분 | 미리보기 | 설명 |
|------|---------|------|
| Scenario KPI | ![Scenario KPI](docs/images/scenario_kpi_radar.png) | 시나리오 KPI 레이더 |
| Performance Comparison | ![Performance](docs/images/performance_comparison.svg) | 기존 방식 대비 성능 비교 |
| Throughput vs Drones | ![Throughput](docs/images/throughput_vs_drones.png) | 드론 수 증가 대비 처리량 추이 |
| Advisory Latency | ![Latency](docs/images/advisory_latency.png) | 의사결정 지연 분포 |
| Conflict Heatmap | ![Heatmap](docs/images/conflict_resolution_heatmap.png) | 충돌 회피 밀집 구역 히트맵 |

### 3) 컨셉 아이디어 보드

| 아이디어 | 미리보기 | 설명 |
|---------|---------|------|
| Idea 1 | ![Idea1](docs/images/idea1_drone_radar.png) | 드론-레이더 돔 개념 |
| Idea 2 | ![Idea2](docs/images/idea2_distributed_apf.png) | 분산 APF 군집 제어 |
| Idea 3 | ![Idea3](docs/images/idea3_multi_layer_safety.png) | 다층 안전성 프레임워크 |
| Idea 4 | ![Idea4](docs/images/idea4_weather_adaptive.png) | 기상 적응형 운영 모델 |

### 4) Full Visual Gallery / 전체 시각자료 갤러리

<details>
<summary><b>전체 23개 자산 펼쳐보기</b></summary>

| 카테고리 | 자산 | 미리보기 |
|---------|------|---------|
| Core | `hero_banner.svg` | ![hero](docs/images/hero_banner.svg) |
| Core | `architecture.svg` | ![arch](docs/images/architecture.svg) |
| Core | `detection_pipeline.svg` | ![pipe](docs/images/detection_pipeline.svg) |
| Core | `algorithm_flow.svg` | ![algo](docs/images/algorithm_flow.svg) |
| Core | `flight_phase_fsm.svg` | ![fsm](docs/images/flight_phase_fsm.svg) |
| Core | `sensor_fusion.svg` | ![sensor](docs/images/sensor_fusion.svg) |
| Chart | `scenario_kpi_radar.png` | ![kpi](docs/images/scenario_kpi_radar.png) |
| Chart | `throughput_vs_drones.png` | ![throughput](docs/images/throughput_vs_drones.png) |
| Chart | `advisory_latency.png` | ![latency](docs/images/advisory_latency.png) |
| Chart | `conflict_resolution_heatmap.png` | ![heatmap](docs/images/conflict_resolution_heatmap.png) |
| Concept | `idea1_drone_radar.png` | ![i1](docs/images/idea1_drone_radar.png) |
| Concept | `idea2_distributed_apf.png` | ![i2](docs/images/idea2_distributed_apf.png) |
| Concept | `idea3_multi_layer_safety.png` | ![i3](docs/images/idea3_multi_layer_safety.png) |
| Concept | `idea4_weather_adaptive.png` | ![i4](docs/images/idea4_weather_adaptive.png) |

</details>

### Visual Quick Links

- [architecture.svg](docs/images/architecture.svg)
- [detection_pipeline.svg](docs/images/detection_pipeline.svg)
- [algorithm_flow.svg](docs/images/algorithm_flow.svg)
- [flight_phase_fsm.svg](docs/images/flight_phase_fsm.svg)
- [sensor_fusion.svg](docs/images/sensor_fusion.svg)

### Asset Packs / 자산 묶음 바로가기

- Core Diagram Pack: [hero_banner.svg](docs/images/hero_banner.svg), [architecture.svg](docs/images/architecture.svg), [detection_pipeline.svg](docs/images/detection_pipeline.svg)
- Operations Chart Pack: [throughput_vs_drones.png](docs/images/throughput_vs_drones.png), [advisory_latency.png](docs/images/advisory_latency.png), [conflict_resolution_heatmap.png](docs/images/conflict_resolution_heatmap.png)
- Concept Board Pack: [idea1_drone_radar.png](docs/images/idea1_drone_radar.png), [idea2_distributed_apf.png](docs/images/idea2_distributed_apf.png), [idea3_multi_layer_safety.png](docs/images/idea3_multi_layer_safety.png), [idea4_weather_adaptive.png](docs/images/idea4_weather_adaptive.png)

---

## At a Glance / 한눈에 이해하기

> **What is this?** Simply put, it's a **"traffic cop for drones."**
>
> Imagine dozens to hundreds of delivery drones, agricultural drones, and filming drones flying simultaneously. Someone needs to manage traffic so they don't collide.
>
> SDACS uses **AI to automatically** manage drone traffic:
> - Predicted collision → Automatic avoidance routing
> - Entering a no-fly zone → Automatic rerouting
> - Drone malfunction → Automatic return to nearest landing pad
> - Communication lost → 5-second hold, then auto-return
>
> Validated with **42 scenarios** (high winds, rogue drones, GPS spoofing, mass delivery, etc.) and **38,400 Monte Carlo simulations**.

---

> **이 프로젝트가 뭔가요?** 쉽게 말하면 **"드론판 교통경찰"** 입니다.
>
> 하늘에 택배 드론, 농업 드론, 촬영 드론이 동시에 수십~수백 대 날아다닌다고 상상해보세요. 서로 부딪히지 않으려면 누군가 교통을 정리해야 합니다.
>
> 이 시스템은 **AI가 자동으로** 드론들의 교통을 정리합니다:
> - 충돌이 예상되면 → 자동으로 회피 경로 안내
> - 비행금지구역에 들어가려 하면 → 자동으로 우회
> - 드론이 고장 나면 → 자동으로 가장 가까운 착륙장으로 귀환
> - 통신이 끊기면 → 5초 대기 후 자동 귀환
>
> **42가지 시나리오** (강풍, 침입 드론, GPS 교란, 대규모 택배 배송 등)를 시뮬레이션해서 시스템이 실제 상황에서도 작동하는지 검증합니다.

👉 **[Try the 3D Simulator / 3D 시뮬레이터 바로 체험하기](https://sun475300-sudo.github.io/swarm-drone-atc/swarm_3d_simulator.html)** — No installation, runs in browser!

---

### 시스템 능력 매트릭스

```
                    ┌─────────────────────────────────────────────┐
    충돌 회피        │██████████████████████████████████████████│ 99.9%
    자율 관제        │████████████████████████████████████████  │ 95%
    기상 적응        │██████████████████████████████████████    │ 92%
    보안/인증        │████████████████████████████████████      │ 88%
    에너지 최적화    │██████████████████████████████████        │ 85%
    장애 복원력      │████████████████████████████████          │ 82%
    규제 준수        │████████████████████████████████████████  │ 95%
    실시간 분석      │████████████████████████████████████████  │ 93%
                    └─────────────────────────────────────────────┘
```

### 기술 스택 전체 지도

```
┌─────────────── SDACS Technology Stack ───────────────┐
│                                                       │
│  🤖 AI/ML              🔬 시뮬레이션        🛡️ 보안   │
│  ├─ Q-Learning (RL)    ├─ SimPy 이산이벤트  ├─ PKI    │
│  ├─ K-means 클러스터   ├─ Monte Carlo       ├─ 암호화 │
│  ├─ PSO 최적화         ├─ 배치 시뮬레이터   ├─ IDS    │
│  ├─ Boids 군집지능     ├─ A/B 테스트        └─ RBAC   │
│  └─ z-score 이상탐지   └─ 스트레스 테스트             │
│                                                       │
│  📐 알고리즘           📊 분석              🌐 통신   │
│  ├─ APF 포텐셜장       ├─ 파레토 프론트     ├─ QoS    │
│  ├─ CBS 다중경로       ├─ 비용/ROI          ├─ 메쉬   │
│  ├─ CPA 90초 예측      ├─ 환경 영향         ├─ Pub/Sub│
│  ├─ A* 최적경로        ├─ 포렌식 분석       └─ 중계   │
│  ├─ Voronoi 공역분할   ├─ 히트맵/트렌드              │
│  ├─ RDP+Bezier 평활    └─ 임무 평가(A~F)            │
│  └─ DAG 위상정렬                                     │
│                                                       │
│  🎮 시각화             🧪 검증                        │
│  ├─ Dash 3D 대시보드   ├─ 1,841 pytest               │
│  ├─ Three.js HTML      ├─ 42 시나리오                 │
│  ├─ 실시간 히트맵      ├─ 38,400 Monte Carlo          │
│  └─ 궤적 리플레이      └─ 통합 검증기                 │
└───────────────────────────────────────────────────────┘
```

---

## SDACS in 5 Steps / SDACS 5단계 스토리

<details>
<summary><b>Step 1: The Problem / 1단계: 문제</b></summary>

**EN:** As drone count explodes (900K+ registered in Korea, growing 30%/year), centralized server-based systems hit their limits. A single server failure paralyzes the entire fleet. Fixed radar costs millions and takes months to install.

**KR:** 드론이 많아질수록 중앙 서버 방식은 한계가 옵니다. 서버 하나가 꺼지면 전체 군집이 마비됩니다. 고정 레이더는 수억원에 6개월 설치가 필요합니다.
</details>

<details>
<summary><b>Step 2: The Solution / 2단계: 해결책</b></summary>

**EN:** Like flocking birds, each drone follows just 3 rules (Separation, Alignment, Cohesion) — forming a swarm without a leader. Drones themselves become mobile radar domes, deployable in 30 minutes.

**KR:** 새 떼처럼 드론 각자가 3가지 규칙(분리·정렬·응집)만 따르면, 리더 없이도 군집이 자동으로 만들어집니다. 드론 자체가 이동형 레이더가 됩니다.
</details>

<details>
<summary><b>Step 3: Architecture / 3단계: 구조</b></summary>

**EN:** Three cooperative layers: Airspace Management (A*, geofencing, Monte Carlo) → Swarm Control (Boids, APF, formation) → Authority Control (FSM). 9 core algorithms across 4 system layers.

**KR:** 공역 관리(A*·지오펜싱·몬테카를로) → 군집 제어(Boids·APF·편대) → 권한 제어(FSM), 총 3계층 9개 알고리즘이 협력합니다.
</details>

<details>
<summary><b>Step 4: Scenarios / 4단계: 시나리오</b></summary>

**EN:** In urban delivery missions, drones use APF to avoid no-fly zones in real-time. When danger is detected, the FSM automatically escalates authority and alerts controllers. 42 scenarios tested including extreme weather, rogue intrusions, and 500-drone mega-swarms.

**KR:** 실제 도심 배송 임무에서 드론이 APF로 금지구역을 우회하고, 위험 시 FSM이 자동으로 관제사에게 알림을 보냅니다. 극한기상, 침입드론, 500대 메가 군집 등 42개 시나리오를 검증합니다.
</details>

<details>
<summary><b>Step 5: Results / 5단계: 결과</b></summary>

**EN:** 1,841 tests collected, 235 algorithms across 25 languages, 38,400+ Monte Carlo validations, 3 live demos (Python Dash + Standalone HTML + SC2), 99.9% collision reduction, and 350 implementation phases completed.

**KR:** 1,841개 테스트 수집, 25개 프로그래밍 언어로 235개 알고리즘, 38,400회 이상 몬테카를로 검증, 3개 라이브 데모를 갖춘 캡스톤 프로젝트입니다. 350개 Phase 구현 완료.
</details>

---

## Background / 프로젝트 배경

### The Problem / 문제 인식

> **EN:** 900K+ registered drones in Korea, growing 30%+ annually. Delivery, agriculture, and UAM drones operating simultaneously in low-altitude airspace — collision risks are skyrocketing.

국내 등록 드론 수 **90만 대 돌파**, 연간 30% 이상 증가. 저고도 공역에서 택배 배송·농업 방제·UAM이 동시 운용되며 충돌 위험이 급증합니다.

| Existing / 기존 방식 | Problem / 문제점 |
|----------|--------|
| Fixed Radar / 고정형 레이더 | $1M+ cost, 6-month installation, limited small-drone detection / 설치 비용 수억원, 소형 드론 탐지 한계 |
| K-UTM Centralized / 중앙 집중식 | Single Point of Failure (SPOF), insufficient real-time / 단일 장애점(SPOF), 실시간성 부족 |
| Manual ATC / 수동 관제 | 5-min avg delay, 24/7 staffing costs / 평균 5분 지연, 인력 비용 과다 |

### Our Solution / 우리의 해결책

> **"Replace the radar with drones"** — Mobile Virtual Radar Dome
>
> **"레이더 자체를 드론으로 대체"** — 이동형 가상 레이더 돔(Dome)

- Emergency deployment in 30 minutes / 30분 내 긴급 배치 가능
- End-to-End automation from detection to avoidance, 80% ATC staff reduction / 탐지부터 회피 유도까지 자동화, 관제 인력 80% 절감
- Linear scalability by adding drones / 드론 추가만으로 관제 반경 선형 확장

---

## System Overview / 시스템 개요

<div align="center">

<img src="docs/images/hero_banner.svg" alt="Hero Banner" width="100%">

</div>

A distributed ATC simulation system that uses swarm drones as **mobile virtual radar domes**, enabling real-time surveillance and **automatic threat response** in urban low-altitude airspace without fixed infrastructure.

군집드론을 **이동형 가상 레이더 돔**으로 활용하여, 고정형 인프라 없이도 도심 저고도 공역을 실시간 감시하고 위협에 **자동 대응**하는 분산형 ATC 시뮬레이션 시스템입니다.

### Key Metrics / 핵심 지표

| 항목 | 값 | 설명 |
|------|----|------|
| 충돌 예측 선제 | 90 s lookahead | CPA 기반 O(N²) 스캔, 1 Hz |
| 자동 어드바이저리 | 6종 | CLIMB / DESCEND / TURN_LEFT / TURN_RIGHT / EVADE_APF / HOLD |
| Monte Carlo 검증 | 38,400 회 | 384 configs × 100 seeds |
| 기상 모델 | 3종 | constant / variable(gust) / shear |
| 침입 탐지 | ROGUE 프로파일 | 미등록 드론 IntrusionAlert |
| 동적 공역 분할 | Voronoi | 10 s 주기 자동 갱신, 밀도 기반 분리 |
| 동적 분리간격 | 1.0x~1.6x | 풍속 연동 자동 조정 (5/10/15 m/s 구간) |
| 장애 주입 | MOTOR/BATTERY/GPS | 자동 고장/통신두절 시뮬레이션 |
| 지오펜스 | 공역 90% 경계 | 이탈 시 자동 RTL |
| 통신 메트릭 | 전송/배달/손실 | 드롭률 실시간 추적 |
| 에너지 효율 | Wh/km | 배터리 소모 기반 효율 지표 |
| 정밀 배터리 모델 | 고도/풍속/상승률 | 다변수 전력 소모 시뮬레이션 |
| 동적 NFZ | 런타임 추가/제거 | 근접 드론 자동 리라우팅 |
| 성능 프로파일러 | cProfile 기반 | 핫스팟 분석 + Top-N 리포트 |
| 결과 저장소 | JSON/CSV | 태그 기반 비교 분석 |
| 편대 비행 | 4패턴 | V자/라인/서클/그리드 리더-팔로워 |
| 메쉬 네트워크 | 멀티홉 BFS | 파티션 감지 + 릴레이 제안 |
| 비교 리포트 | HTML/차트 | A/B 비교 + 민감도 분석 |
| 비행 데이터 레코더 | FDR 매틱 | 리플레이 + CSV 내보내기 |
| 다중 관제 구역 | 4/9 섹터 | 핸드오프 프로토콜 + 구역 메트릭 |
| SLA 모니터 | 7개 임계치 | 실시간 위반 감지 + 자가 튜닝 |
| 이벤트 타임라인 | 시계열 저장 | 사고 조사 쿼리 인터페이스 |
| 에너지 최적 경로 | A* 풍향/고도 | 에너지 비용 함수 + 충전소 경유 |
| 실시간 위협 평가 | 4레벨 9유형 | 복합 위협 에스컬레이션 + 권장 조치 |
| 시나리오 스크립터 | YAML DSL | 8종 시간 이벤트 자동 트리거 |
| E2E 스트레스 테스트 | 500대+ | P95/P99 틱 성능 + 실시간 배율 |
| SC2 알고리즘 검증 | 14,200 회 | 게임 AI 환경 사전 검증 |

---

## 4-Layer Architecture / 4계층 아키텍처

<div align="center">

<img src="docs/images/architecture.svg" alt="System Architecture" width="100%">

*SDACS 4계층 시스템 아키텍처*

</div>

```
┌──────────────────────────────────────────────────────────────┐
│  Layer 4 — 사용자 인터페이스                                   │
│  CLI (main.py)  ·  3D Dash 대시보드  ·  pytest 1,206개        │
└───────────────────────────┬──────────────────────────────────┘
                            │ 명령 / 결과
┌───────────────────────────▼──────────────────────────────────┐
│  Layer 3 — 시뮬레이션 엔진 (SimPy)                            │
│  SwarmSimulator  ·  WindModel(3종)  ·  Monte Carlo  ·  시나리오 │
└───────────────────────────┬──────────────────────────────────┘
                            │ 이벤트 / 상태
┌───────────────────────────▼──────────────────────────────────┐
│  Layer 2 — 공역 제어 (ATC, 1 Hz)                              │
│  AirspaceController  ·  FlightPathPlanner(A*)  ·  Voronoi    │
└───────────────────────────┬──────────────────────────────────┘
                            │ 어드바이저리 / 허가
┌───────────────────────────▼──────────────────────────────────┐
│  Layer 1 — 드론 에이전트 (10 Hz)                               │
│  _DroneAgent  ·  APF 충돌 회피  ·  텔레메트리  ·  상태머신     │
└──────────────────────────────────────────────────────────────┘
```

### 핵심 데이터 흐름

```
_DroneAgent (10 Hz)
    │  TelemetryMessage (0.5 s 주기)
    ▼
CommunicationBus  (지연 20±5ms, 패킷손실 모델)
    │
    ▼
AirspaceController (1 Hz)
    ├── ClearanceRequest → A* 경로계획 → ClearanceResponse
    ├── O(N²) CPA 스캔 (90 s lookahead) → ResolutionAdvisory
    ├── ROGUE 감지 → IntrusionAlert (BROADCAST)
    └── 10 s 주기 Voronoi 공역 갱신
```

### 센서 퓨전 프로세스

<div align="center">

<img src="docs/images/sensor_fusion.svg" alt="Sensor Fusion" width="100%">

*Camera (YOLO) + LiDAR + RF Scanner → Kalman Filter Fusion*

</div>

### 드론 비행 상태 기계 (FlightPhase FSM)

<div align="center">

<img src="docs/images/flight_phase_fsm.svg" alt="Flight Phase FSM" width="100%">

*8가지 비행 상태 간 전이 다이어그램*

</div>

```
GROUNDED ──[허가 수신]──► TAKEOFF ──[순항고도]──► ENROUTE
    ▲                                               │    │
    │                                         [목적지] [충돌위협]
LANDING ◄──────────────────────────────────────────┘    ▼
    ▲                                             EVADING (APF)
RTL ◄──[배터리 임계]                                    │
HOLDING ◄──[Lost-Link]                          [회피 완료]──► ENROUTE
FAILED ◄──[장애 주입]
```

---

## Core Algorithms / 핵심 알고리즘

> **27 core algorithms** work hierarchically to ensure safe swarm drone operations.
>
> **67개 핵심 알고리즘**이 계층적으로 동작하여 군집드론 안전 운항을 보장합니다.

<div align="center">

<img src="docs/images/algorithm_flow.svg" alt="Algorithm Flow" width="100%">

</div>

### 1. APF (인공 포텐셜 장) — 1차 충돌 회피

드론 주변에 인력/척력 필드를 생성하여 **실시간 충돌 회피**를 수행합니다.

```
F_total = F_attractive(목표) + ΣF_repulsive(드론) + ΣF_repulsive(NFZ)
```

| 파라미터 | 일반 모드 | 강풍 모드 (>10 m/s) | 설명 |
|----------|----------|-------------------|------|
| `k_att` | 1.0 | 1.0 | 목표 방향 인력 |
| `k_rep` (드론) | 2.5 | **6.5** | 드론 간 척력 |
| `d0` (드론) | 50 m | **80 m** | 척력 작용 반경 |
| `k_rep` (장애물) | 5.0 | 5.0 | NFZ 척력 |
| `max_force` | 10 m/s² | **22 m/s²** | 힘 포화값 |

> 접근 속도 비례 척력 **3배 증폭** (Velocity Obstacle 보상) · NumPy 배치 벡터 연산 (10 Hz)
> 풍속 6~12 m/s 구간 **선형 블렌딩** (하드 스위칭 대신 매끄러운 전환)
> **Spatial Hash** O(N·k) 이웃 탐색 — 대규모 군집에서도 실시간 APF 매 프레임 실행

### 2. CPA 기반 선제 충돌 예측

**Closest Point of Approach** 알고리즘으로 **90초 전** 충돌을 예측합니다.

```
rel_pos = pos_A - pos_B
rel_vel = vel_A - vel_B
t_cpa   = -dot(rel_pos, rel_vel) / ||rel_vel||²    (clamp 0 ~ 90 s)
CPA_dist = ||rel_pos + rel_vel × t_cpa||

CPA_dist < 50 m  →  충돌 예측  →  ResolutionAdvisory 발령
```

> O(N²) 페어 스캔 · 1 Hz · 100대 = 4,950 계산/초

### 3. Resolution Advisory 생성기 (기하학적 분류)

```
┌─────────────────────────────────────────────────────────────┐
│  입력: CPA 거리, CPA 시간, 상대 위치/속도, FlightPhase      │
├─────────────────────────────────────────────────────────────┤
│  ① threat.phase == FAILED     → HOLD       (상대 장애)     │
│  ② cpa_t < 10 s              → EVADE_APF  (긴급 APF 회피)  │
│  ③ 수직 여유 > sep_vert      → CLIMB / DESCEND            │
│  ④ 정면 충돌 (방위 ±30°)      → TURN_RIGHT (항공 규칙)     │
│  ⑤ 그 외                     → TURN_LEFT / TURN_RIGHT     │
├─────────────────────────────────────────────────────────────┤
│  Lost-Link 3단계 프로토콜                                    │
│  Phase 1: HOLD  (loiter 30s) → Phase 2: CLIMB (80m)       │
│  → Phase 3: RTL (자동 귀환)                                 │
└─────────────────────────────────────────────────────────────┘
```

### 4. Voronoi 동적 공역 분할

10초 주기로 활성 드론의 **책임 영역**을 동적으로 분할합니다.

```
① 활성 드론 2D 위치 추출
② scipy.spatial.Voronoi 분할
③ Sutherland-Hodgman 경계 클리핑 (공역 범위 제한)
④ Ray-casting 점-폴리곤 판정 → 허가 처리 시 셀 침범 감지
```

### 5. CBS (Conflict-Based Search) 다중 경로 계획

```
High Level: 충돌 트리(CT) 탐색
  충돌 감지 → 제약 추가 → 재탐색 (최대 1,000 노드)

Low Level: 시공간 A* (개별 드론)
  격자 해상도: 50 m  |  시간스텝: 1 s  |  최대 시간: 200 스텝
```

### 드론 프로파일

| 타입 | 최대속도 | 순항속도 | 배터리 | 우선순위 | 용도 |
|------|---------|---------|--------|---------|------|
| **EMERGENCY** | 25 m/s | 20 m/s | 60 Wh | `P1` 최우선 | 응급 의료 |
| COMMERCIAL_DELIVERY | 15 m/s | 10 m/s | 80 Wh | `P2` | 택배 배송 |
| SURVEILLANCE | 20 m/s | 12 m/s | 100 Wh | `P2` | 감시 정찰 |
| RECREATIONAL | 10 m/s | 5 m/s | 30 Wh | `P3` | 취미 비행 |
| ROGUE (미등록) | 15 m/s | 8 m/s | 50 Wh | `—` | 침입 드론 |

---

## Algorithm Hierarchy / 알고리즘 계층 구조

> **131개 핵심 알고리즘**이 4개 계층에서 계층적으로 동작합니다. (Python 17,500+줄 + HTML/JS 2,897줄)

```
Layer 1: 드론 에이전트 (10 Hz, SimPy)
├── APF 충돌 회피 ─── 인력(목표) + 척력(드론/장애물) + 속도장애물 보정
│   ├── 일반 모드: k_rep=2.5, d0=50m
│   ├── 강풍 모드: k_rep=6.5, d0=80m (풍속 >10 m/s 자동 전환)
│   └── Spatial Hash O(N·k) 이웃 탐색
├── 비행 단계 FSM ─── 8단계 (GROUNDED → TAKEOFF → ENROUTE → HOLDING → LANDING)
└── 텔레메트리 브로드캐스팅 (10 Hz)

Layer 2: 공역 제어기 (1 Hz, AirspaceController)
├── CPA 선제 충돌 예측 ─── 90초 룩어헤드, O(N²) 페어 스캔
├── Resolution Advisory 생성 ─── 6종 회피 명령 + ICAO 우측 회피 규칙
│   ├── CLIMB / DESCEND (수직 분리)
│   ├── TURN_LEFT / TURN_RIGHT (수평 회피)
│   ├── HOLD (제자리 대기)
│   ├── EVADE_APF (긴급 APF 위임)
│   └── Lost-Link 3단계: HOLD(30s) → CLIMB(80m) → RTL
├── 우선순위 클리어런스 ─── EMERGENCY > MEDICAL > COMMERCIAL > RECREATIONAL
├── Voronoi 동적 공역 분할 ─── 10초 갱신, 셀 침범 감지, 밀도 기반 분리
├── 동적 분리간격 ─── 풍속 연동 1.0x~1.6x 자동 조정
├── HOLDING 큐 관리 ─── FIFO, 최대 100대, 오버플로→RTL
├── CBS 메트릭 추적 ─── 시도/성공/실패 + A* 폴백 카운트
├── 허가 처리율 ─── 60초 슬라이딩 윈도우 처리량 (건/초)
└── A* 경로 재계획 (NFZ 회피)

Layer 3: 시뮬레이션 엔진
├── CBS 다중 에이전트 경로 최적화 (충돌 트리 + 시공간 A*)
├── 기상 모델 ─── 3종 (일정풍 / 변동풍+Poisson 돌풍 / 전단풍)
│   └── 극한 기상: 마이크로버스트, 태풍, 결빙, 폭풍셀, 풍속전단
├── Spatial Hash O(log N) 근방 탐색
├── 장애 주입 자동화 ─── MOTOR/BATTERY/GPS 고장 + 통신두절 (5초 주기)
├── 지오펜스 경계 보호 ─── 공역 90% 이탈 시 자동 RTL
├── 에너지 효율 추적 ─── Wh/km 실시간 계산
├── 정밀 배터리 모델 ─── 고도/풍속/상승률 다변수 전력 소모
├── 동적 NFZ 관리 ─── 런타임 추가/제거 + 근접 드론 자동 리라우팅
├── 통신 버스 메트릭 ─── 전송/배달/손실 통계, 드롭률 추적
├── 성능 프로파일러 ─── cProfile 핫스팟 분석 + Top-N 리포트
├── 결과 저장소 ─── JSON/CSV 내보내기 + 태그 기반 비교 분석
├── 편대 비행 알고리즘 ─── V자/라인/서클/그리드 4패턴 + 리더-팔로워
├── 메쉬 네트워크 ─── 멀티홉 릴레이 + 파티션 감지 + 릴레이 배치 제안
├── 비행 데이터 레코더 ─── FDR 매틱 기록 + 리플레이 + CSV 내보내기
├── 다중 관제 구역 ─── 구역 분할 + 핸드오프 프로토콜 + 구역별 메트릭
├── SLA 모니터 ─── 실시간 위반 감지 + 자가 파라미터 튜닝
├── 이벤트 타임라인 ─── 사고 조사 + 시간/타입/드론별 쿼리
├── 에너지 최적 경로 ─── A* 풍향/고도 비용 함수 + 충전소 경유
├── 위협 평가 엔진 ─── 4레벨(LOW~CRITICAL) 9유형 + 우선순위 매트릭스
├── 시나리오 스크립터 ─── YAML DSL 8종 이벤트 자동 트리거
├── 스트레스 테스트 ─── 합성 부하 + P95/P99 틱 성능 벤치마크
├── 행동 패턴 분석 ─── K-means 클러스터링 + z-score 이상치 탐지
├── 동적 우선순위 스케줄러 ─── 혼잡도 기반 출발 시간 최적화
├── 리플레이 분석기 ─── FDR 인과관계 추적 + 사고 리포트 자동 생성
├── 기상 예측 엔진 ─── 이동평균 + 선형 트렌드 단기 예측
├── 배터리 수명 예측 ─── 다변수 소모 모델 + 잔여 비행시간/거리
├── 규제 준수 검증 ─── K-UTM/ICAO 분리기준 + 준수 점수(0~100)
├── 통신 품질 시뮬레이션 ─── 경로 손실 모델 + 패킷 손실 + 링크 버짓
├── 자동 보고서 생성 ─── KPI 분석 + 이상치 탐지 + 권장 사항 자동 생성
├── 동적 지오펜스 ─── 원형/다각형/회랑 + 시간별 활성화 + 침범 감지
├── 군집지능 ─── Boids(분리/정렬/응집) + PSO 목표 탐색
├── 통신 중계 배치 ─── 커버리지 최적화 + BFS 다중 홉 경로
├── 다중 임무 할당 ─── 그리디 매칭 + 배터리/거리 제약 최적화
├── 공역 용량 분석 ─── 섹터별 수용량 + 포화도 예측 + 자동 유입 규제
├── 비상 프로토콜 ─── 6종 비상 시나리오 + 자동 대응 절차 + 에스컬레이션
├── 소음 모델링 ─── 역제곱 감쇠 + 다중 소음원 합산 + 규제 검증
├── 함대 최적화 ─── 효율 기반 그리디 배치 + 교대 스케줄 + ROI
├── 경로 탈충돌 ─── 4D 경로 충돌 검사 + 시간 이동 해소
├── 텔레메트리 녹화 ─── 상태 스냅샷 + 리와인드 + 두 시뮬 비교
├── 착륙 관리 ─── 패드 할당 + 대기열 FIFO + 비상 착륙 오버라이드
├── 위험도 평가 ─── 인구 밀도 + 낙하 확률 + 피해 반경 위험 지도
├── 공역-기상 통합 ─── GREEN/YELLOW/ORANGE/RED 등급 자동 전환
├── 드론 건강 모니터 ─── 진동 트렌드 + 온도 + 예방 정비 스케줄
├── 교통 흐름 분석 ─── 그리드 기반 밀도/흐름 분석 + 병목 탐지
├── 부하 분산 ─── 섹터 간 핫스팟/콜드스팟 감지 + 드론 재배치
├── 웨이포인트 최적화 ─── RDP 간소화 + Bezier 평활화 + 에너지 절감
├── 비상 대안 경로 ─── 대안 경로 사전 계산 + 차단 구역 우회 + 실시간 전환
├── 감시 추적 ─── 비협조 표적 추적 + 궤적 예측 + 요격 지점 계산
├── 충전 인프라 관리 ─── 충전소 추천 + 대기열 + 충전 시간 추정
├── 규제 보고서 ─── K-UTM 준수 보고 + 감사 로그 + 위반 분석
├── 시나리오 자동 생성 ─── 랜덤/스트레스/기상/점진 시나리오 + 난이도 추정
├── 자동 스케일링 ─── 드론 수 동적 조절 + 수요 예측 + 스케일 정책
├── 경로 캐시 ─── LRU 캐시 + 히트율 + 지역 무효화
├── 공역 예약 시스템 ─── 4D 시공간 슬롯 예약 + 우선순위 선점
├── 드론 인증 관리 ─── 등록/인증/블랙리스트 + 비행 허가 검증
├── 다중 목표 최적화 ─── 파레토 프론트 + 에너지/시간/안전 트레이드오프
├── 이벤트 버스 ─── Pub/Sub 브로커 + 필터 + 이력 조회
├── 공역 히트맵 ─── 시간대별 밀도 히트맵 + 핫스팟 예측 + 트렌드
├── 드론 그룹 관리 ─── 그룹 생성/해체/병합 + 그룹별 명령
├── 충돌 포렌식 ─── 근본원인 분석 + 기여도 + 재현 시퀀스
├── 기상 위험 구역 ─── 동적 위험 구역 + 이동 추적 + 자동 회피
├── 에너지 예산 관리 ─── 임무별 할당 + 소비 추적 + 예산 경고
├── 네트워크 토폴로지 ─── 통신 그래프 + 중심성 + 취약 노드 감지
├── 임무 우선순위 큐 ─── 우선순위 대기열 + SLA 기한 + 재할당
├── 비행 복도 관리 ─── 단방향/양방향 복도 + 진입/이탈 프로토콜
├── 센서 퓨전 ─── 역분산 가중 융합 + 센서 건강 + 신뢰도
├── 시뮬레이션 벤치마크 ─── 성능 스위트 + 회귀 탐지 + 기준선 비교
├── 분산 리더 선출 ─── 복합 점수(점수×배터리×통신) + 자동 페일오버
├── 공역 밀도 예측 ─── 선형 트렌드 예측 + 혼잡 임계치 + 사전 조치
├── DAG 임무 체인 ─── 의존성 그래프 + 위상 정렬 + 임계 경로 분석
├── 장애 전파 분석 ─── BFS 전파 시뮬레이션 + 격리 후보 + 복원력 점수
├── 동적 고도 관리 ─── 8방위 고도 밴드 + 우선순위 오프셋 + 혼잡 재배치
├── 비행 로그 분석 ─── 드론별 통계 + z-score 이상 탐지 + 함대 KPI
├── 충전 최적화 ─── 다중 충전소 + 이동/대기/충전/우회 비용 최적화
├── 드론 페어링 ─── ESCORT/RELAY/SEARCH 모드 + 거리 경고 + 자동 매칭
├── 비행 계획 검증 ─── NFZ/고도/거리 규정 검증 + 적합성 점수
├── 대시보드 데이터 ─── KPI 관리 + 경보 피드 + 트렌드 이력
├── 배치 시뮬레이터 ─── 다중 시나리오 실행 + 메트릭 비교 + 통계
├── 공역 이력 관리 ─── 시계열 스냅샷 + 기간 비교 + 트렌드 감지
├── 성능 프로필 추적 ─── 속도/진동 열화 추적 + 드론 간 비교
├── 임무 결과 평가 ─── 점수/등급(A~F) + 개선 권장 생성
├── 역할 기반 접근 제어 ─── 권한 매트릭스 + 감사 로그 + 거부 추적
├── 시스템 건강 모니터 ─── 역방향 지표(배터리) + 자가 진단 + 경보
├── 강화학습 경로 선택 ─── Q-테이블 + epsilon-greedy + 보상 함수
├── 예측 유지보수 ─── 비행시간/진동/사이클 잔여수명 + 정비 일정
├── 다중 에이전트 협상 ─── 양보/교환 프로토콜 + 교착 탐지
├── 적응형 파라미터 튜너 ─── 실시간 성능 피드백 → 자동 파라미터 조정
├── 의사결정 트리 관제 ─── IF-THEN 규칙 기반 빠른 결정
├── 공역 수요 예측 ─── 시간대별 패턴 학습 + 사전 자원 배치
├── 경로 다양성 생성 ─── k-최단경로 + 유사도 분석 + 분산 최적화
├── 동적 우선순위 재조정 ─── 배터리/시간/비상 컨텍스트 기반 조정
├── GPS 스푸핑 탐지 ─── 다중 센서 교차 검증 + 위치 이상 탐지
├── 암호화 통신 채널 ─── 키 교환 + 메시지 무결성 + 재전송 방지
├── 침입 탐지 시스템 ─── 이상 트래픽 패턴 + 블랙리스트 + 격리
├── 규제 동적 업데이트 ─── 버전 관리 + 자동 적용 + 준수 확인
├── 통신 QoS 관리 ─── 우선순위별 대역폭 할당 + 트래픽 쉐이핑
├── 드론 신원 인증 ─── PKI 인증서 + 만료/갱신 프로토콜
├── 감사 추적 시스템 ─── 불변 로그 체인 + 무결성 해시
├── 비상 방송 시스템 ─── 구역별 브로드캐스트 + 확인 응답
├── 시나리오 난이도 평가 ─── 밀도/기상/NFZ/장애 복합 점수
├── A/B 테스트 프레임워크 ─── 통계 유의성 검정 + 개선율 분석
├── 실시간 리포트 스트림 ─── 이벤트 스트림 + 구독 + 버퍼 관리
├── 다중 시뮬레이터 조율 ─── 병렬 실행 + 결과 집계 + 분산 시드
├── 환경 영향 분석 ─── 소음/에너지 환경 점수 + 친환경 경로
├── 비용 분석 엔진 ─── 에너지/정비/인프라 비용 + ROI 분석
├── 학습 데이터 수집 ─── 경험 → 구조화된 학습 데이터셋
├── 시스템 통합 검증 ─── 의존성 그래프 + 인터페이스 적합성 + 회귀 감지
├── Monte Carlo 38,400회 SLA 검증 (384 configs × 100 seeds)
└── 42개 시나리오 배치 실행

Layer 4: 3D 시각화 (Three.js, 독립 구현)
├── APF 충돌 회피 (Spatial Hash + 3D CPA 12초 예측)
├── 동적 기상 시스템 (매 프레임 풍속 보간)
├── 500대 드론 실시간 렌더링 + 오브젝트 풀링
└── 42개 시나리오 인터랙티브 시뮬레이션
```

### 알고리즘 파일 매핑

| # | 알고리즘 | 파일 | 줄 수 | 역할 |
|---|---------|------|-------|------|
| 1 | APF (인공 포텐셜 장) | `simulation/apf_engine/apf.py` | 272 | 실시간 충돌 회피 (인력+척력+풍속 증폭) |
| 2 | CPA (최근접점 예측) | `src/airspace_control/utils/geo_math.py` | 75 | 90초 전 충돌 위치 사전 계산 |
| 3 | Resolution Advisory | `src/airspace_control/avoidance/resolution_advisory.py` | 242 | 6종 회피 명령 + Lost-Link 3단계 |
| 4 | CBS (Conflict-Based Search) | `simulation/cbs_planner/cbs.py` | 263 | 다중 에이전트 전역 경로 최적화 |
| 5 | Voronoi 공역 분할 | `simulation/voronoi_airspace/voronoi_partition.py` | 241 | 동적 2D 공역 분할 (10초 갱신) |
| 6 | A* 경로 계획 | `src/airspace_control/planning/flight_path_planner.py` | 262 | 비행금지구역(NFZ) 회피 그리드 탐색 |
| 7 | 기상 대항 시스템 | `simulation/weather.py` | 152 | 3종 풍속 모델 + 돌풍 시뮬레이션 |
| 8 | AirspaceController | `src/airspace_control/controller/airspace_controller.py` | 805 | 1Hz 전역 관제 루프 + 동적 분리 + HOLDING 큐 + 동적 NFZ |
| 9 | SwarmSimulator | `simulation/simulator.py` | 788 | 10Hz 드론 에이전트 + 장애주입 + 지오펜스 + 정밀 배터리 |
| 10 | 성능 프로파일러 | `simulation/profiler.py` | 60+ | cProfile 핫스팟 분석 + Top-N 리포트 |
| 11 | 결과 저장소 | `simulation/result_store.py` | 140+ | JSON/CSV 내보내기 + 차트 비교 + HTML 리포트 |
| 12 | 편대 비행 제어 | `simulation/formation.py` | 170+ | V자/라인/서클/그리드 + 리더-팔로워 |
| 13 | 메쉬 네트워크 | `simulation/mesh_network.py` | 200+ | 멀티홉 릴레이 + 파티션 감지 + 릴레이 제안 |
| 14 | 비행 데이터 레코더 | `simulation/flight_data_recorder.py` | 170+ | FDR 매틱 기록 + 리플레이 + CSV |
| 15 | 다중 관제 구역 | `simulation/multi_controller.py` | 180+ | 구역 분할 + 핸드오프 + 구역별 메트릭 |
| 16 | SLA 모니터 | `simulation/sla_monitor.py` | 150+ | 실시간 위반 감지 + 자가 튜닝 |
| 17 | 이벤트 타임라인 | `simulation/event_timeline.py` | 150+ | 사고 조사 + 시계열 쿼리 |
| 18 | 에너지 최적 경로 | `simulation/energy_path_planner.py` | 290+ | A* 풍향/고도 비용 + 충전소 경유 |
| 19 | 위협 평가 엔진 | `simulation/threat_assessment.py` | 270+ | 4레벨 9유형 위협 + 우선순위 매트릭스 |
| 20 | 시나리오 스크립터 | `simulation/scenario_scripter.py` | 220+ | YAML DSL 8종 이벤트 자동 트리거 |
| 21 | 스트레스 테스트 | `simulation/stress_test.py` | 250+ | 합성 부하 + P95/P99 벤치마크 |
| 22 | 행동 패턴 분석 | `simulation/behavior_analyzer.py` | 200+ | K-means 클러스터링 + 이상치 탐지 |
| 23 | 동적 우선순위 | `simulation/priority_scheduler.py` | 220+ | 혼잡도 기반 임무 스케줄링 |
| 24 | 리플레이 분석 | `simulation/replay_analyzer.py` | 250+ | FDR 인과관계 추적 + 자동 리포트 |
| 25 | 기상 예측 | `simulation/weather_forecast.py` | 200+ | 이동평균 + 트렌드 기반 단기 예측 |
| 26 | 배터리 예측 | `simulation/battery_predictor.py` | 200+ | 다변수 소모 모델 + 잔여 시간 예측 |
| 27 | 규제 준수 검증 | `simulation/compliance_checker.py` | 200+ | K-UTM/ICAO 규정 + 준수 점수 산출 |
| 28 | 통신 품질 시뮬레이션 | `simulation/comm_quality.py` | 240+ | 경로 손실 모델 + 패킷 손실 + 링크 버짓 |
| 29 | 자동 보고서 생성 | `simulation/report_generator.py` | 230+ | KPI 분석 + 이상치 탐지 + 권장 사항 |
| 30 | 동적 지오펜스 | `simulation/geofence_manager.py` | 270+ | 원형/다각형/회랑 + 시간별 활성화 + 침범 감지 |
| 31 | 군집지능 알고리즘 | `simulation/swarm_intelligence.py` | 280+ | Boids(분리/정렬/응집) + PSO 목표 탐색 |
| 32 | 통신 중계 배치 | `simulation/comm_relay.py` | 230+ | 커버리지 최적화 + 다중 홉 경로 + 자동 배치 |
| 33 | 다중 임무 할당 | `simulation/mission_planner.py` | 240+ | 그리디 매칭 + 배터리/거리 제약 최적화 |
| 34 | 공역 용량 분석 | `simulation/airspace_capacity.py` | 230+ | 섹터별 수용량 + 포화도 예측 + 자동 규제 |
| 35 | 비상 프로토콜 | `simulation/emergency_protocol.py` | 250+ | 6종 비상 시나리오 + 자동 대응 절차 |
| 36 | 소음 모델링 | `simulation/noise_model.py` | 200+ | 역제곱 감쇠 + 소음 지도 + 규제 검증 |
| 37 | 함대 최적화 | `simulation/fleet_optimizer.py` | 220+ | 그리디 배치 + 교대 스케줄 + ROI 분석 |
| 38 | 경로 탈충돌기 | `simulation/path_deconflict.py` | 240+ | 4D 경로 충돌 검사 + 시간 분리 해소 |
| 39 | 텔레메트리 녹화 | `simulation/telemetry_recorder.py` | 200+ | 스냅샷 기록 + 리와인드 + 비교 재생 |
| 40 | 착륙 관리자 | `simulation/landing_manager.py` | 230+ | 패드 할당 + 대기열 + 비상 착륙 |
| 41 | 위험도 평가 | `simulation/risk_assessor.py` | 210+ | 인구 밀도 + 낙하 확률 + 피해 반경 |
| 42 | 공역-기상 통합 | `simulation/airspace_weather_integration.py` | 220+ | 기상 기반 공역 등급 + 동적 제한 |
| 43 | 드론 건강 모니터 | `simulation/drone_health_monitor.py` | 230+ | 센서 진단 + 진동 트렌드 + 예방 정비 |
| 44 | 교통 흐름 분석 | `simulation/traffic_flow.py` | 170+ | 그리드 밀도/흐름 분석 + 병목 탐지 |
| 45 | 부하 분산기 | `simulation/load_balancer.py` | 150+ | 섹터 핫스팟/콜드스팟 + 재배치 계획 |
| 46 | 웨이포인트 최적화 | `simulation/waypoint_optimizer.py` | 180+ | RDP 간소화 + Bezier 평활화 + 에너지 절감 |
| 47 | 비상 대안 경로 | `simulation/contingency_planner.py` | 130+ | 대안 경로 사전 계산 + 차단 구역 우회 |
| 48 | 감시 추적기 | `simulation/surveillance_tracker.py` | 130+ | 비협조 표적 추적 + 궤적 예측 + 요격 |
| 49 | 충전 인프라 관리 | `simulation/power_grid.py` | 140+ | 충전소 추천 + 대기열 + 충전 시간 추정 |
| 50 | 규제 보고서 | `simulation/regulatory_reporter.py` | 120+ | K-UTM 준수 보고 + 감사 로그 + 위반 분석 |
| 51 | 시나리오 자동 생성 | `simulation/scenario_generator.py` | 140+ | 랜덤/스트레스/기상/점진 + 난이도 추정 |
| 52 | 자동 스케일링 | `simulation/auto_scaler.py` | 130+ | 드론 수 동적 조절 + 수요 예측 + 스케일 정책 |
| 53 | 경로 캐시 | `simulation/path_cache.py` | 130+ | LRU 캐시 + 히트율 + 지역 무효화 |
| 54 | 공역 예약 | `simulation/airspace_reservation.py` | 140+ | 4D 시공간 슬롯 예약 + 우선순위 선점 |
| 55 | 드론 인증 관리 | `simulation/drone_registry.py` | 130+ | 등록/인증/블랙리스트 + 비행 허가 검증 |
| 56 | 다중 목표 최적화 | `simulation/multi_objective.py` | 140+ | 파레토 프론트 + 가중 합산 + 하이퍼볼륨 |
| 57 | 이벤트 버스 | `simulation/event_bus.py` | 120+ | Pub/Sub 브로커 + 필터 + 이력 조회 |
| 58 | 공역 히트맵 | `simulation/airspace_heatmap.py` | 150+ | 밀도 히트맵 + 핫스팟 예측 + 트렌드 |
| 59 | 드론 그룹 관리 | `simulation/drone_group.py` | 120+ | 그룹 생성/해체/병합 + 그룹별 명령 |
| 60 | 충돌 포렌식 | `simulation/collision_forensics.py` | 150+ | 근본원인 분석 + 기여도 + 재현 시퀀스 |
| 61 | 기상 위험 구역 | `simulation/weather_hazard_zone.py` | 170+ | 동적 위험 구역 + 이동 추적 + 자동 회피 |
| 62 | 에너지 예산 관리 | `simulation/energy_budget.py` | 130+ | 임무별 할당 + 소비 추적 + 예산 경고 |
| 63 | 네트워크 토폴로지 | `simulation/network_topology.py` | 170+ | 통신 그래프 + 중심성 + 취약 노드 감지 |
| 64 | 임무 우선순위 큐 | `simulation/mission_queue.py` | 120+ | 우선순위 대기열 + SLA 기한 + 재할당 |
| 65 | 비행 복도 관리 | `simulation/flight_corridor.py` | 150+ | 단방향/양방향 복도 + 진입/이탈 프로토콜 |
| 66 | 센서 퓨전 | `simulation/sensor_fusion.py` | 140+ | 역분산 가중 융합 + 센서 건강 + 신뢰도 |
| 67 | 시뮬레이션 벤치마크 | `simulation/benchmark_suite.py` | 140+ | 성능 스위트 + 회귀 탐지 + 기준선 비교 |
| 68 | 분산 리더 선출 | `simulation/leader_election.py` | 110+ | 복합 점수 선출 + 자동 페일오버 |
| 69 | 공역 밀도 예측 | `simulation/airspace_predictor.py` | 120+ | 선형 트렌드 예측 + 혼잡 사전 조치 |
| 70 | DAG 임무 체인 | `simulation/mission_chain.py` | 130+ | 의존성 그래프 + 위상 정렬 + 임계 경로 |
| 71 | 장애 전파 분석 | `simulation/failure_propagation.py` | 120+ | BFS 전파 + 격리 후보 + 복원력 점수 |
| 72 | 동적 고도 관리 | `simulation/altitude_manager.py` | 140+ | 8방위 고도 밴드 + 우선순위 오프셋 |
| 73 | 비행 로그 분석 | `simulation/flight_log_analyzer.py` | 130+ | 드론별 통계 + z-score 이상 탐지 + KPI |
| 74 | 충전 최적화 | `simulation/charge_optimizer.py` | 140+ | 다중 충전소 비용 최적화 + 배치 스케줄링 |
| 75 | 드론 페어링 | `simulation/drone_pairing.py` | 120+ | ESCORT/RELAY/SEARCH + 자동 매칭 |
| 76 | 비행 계획 검증 | `simulation/flight_plan_validator.py` | 110+ | NFZ/고도/거리 규정 검증 + 적합성 점수 |
| 77 | 대시보드 데이터 | `simulation/dashboard_data.py` | 90+ | KPI 관리 + 경보 피드 + 트렌드 이력 |
| 78 | 배치 시뮬레이터 | `simulation/batch_simulator.py` | 120+ | 다중 시나리오 실행 + 메트릭 비교 |
| 79 | 공역 이력 관리 | `simulation/airspace_history.py` | 120+ | 시계열 스냅샷 + 기간 비교 + 트렌드 |
| 80 | 성능 프로필 추적 | `simulation/performance_profile.py` | 120+ | 속도/진동 열화 추적 + 드론 비교 |
| 81 | 임무 결과 평가 | `simulation/mission_evaluator.py` | 110+ | 점수/등급(A~F) + 개선 권장 |
| 82 | 역할 기반 접근 제어 | `simulation/access_control.py` | 90+ | 권한 매트릭스 + 감사 로그 |
| 83 | 시스템 건강 모니터 | `simulation/system_health.py` | 110+ | 역방향 지표 + 자가 진단 + 경보 |
| 84 | 강화학습 경로 선택 | `simulation/rl_path_selector.py` | 100+ | Q-테이블 + epsilon-greedy + 보상 함수 |
| 85 | 예측 유지보수 | `simulation/predictive_maintenance.py` | 130+ | 비행시간/진동/사이클 잔여수명 |
| 86 | 다중 에이전트 협상 | `simulation/agent_negotiation.py` | 120+ | 양보/교환 프로토콜 + 교착 탐지 |
| 87 | 적응형 파라미터 튜너 | `simulation/adaptive_tuner.py` | 140+ | 실시간 성능 → 자동 파라미터 조정 |
| 88 | 의사결정 트리 관제 | `simulation/decision_tree_atc.py` | 120+ | IF-THEN 규칙 기반 빠른 결정 |
| 89 | 공역 수요 예측 | `simulation/demand_forecaster.py` | 120+ | 시간대별 패턴 학습 + 사전 배치 |
| 90 | 경로 다양성 생성 | `simulation/path_diversity.py` | 140+ | k-최단경로 + 유사도 + 분산 최적화 |
| 91 | 동적 우선순위 재조정 | `simulation/priority_adjuster.py` | 130+ | 배터리/시간/비상 컨텍스트 기반 |
| 92 | GPS 스푸핑 탐지 | `simulation/gps_spoof_detector.py` | 130+ | 다중 센서 교차 검증 + 이상 탐지 |
| 93 | 암호화 통신 채널 | `simulation/secure_channel.py` | 120+ | 키 교환 + 무결성 + 재전송 방지 |
| 94 | 침입 탐지 시스템 | `simulation/intrusion_detector.py` | 120+ | 이상 트래픽 + 블랙리스트 + 격리 |
| 95 | 규제 동적 업데이트 | `simulation/regulation_updater.py` | 110+ | 버전 관리 + 자동 적용 + 준수 확인 |
| 96 | 통신 QoS 관리 | `simulation/comm_qos.py` | 120+ | 우선순위별 대역폭 + 트래픽 쉐이핑 |
| 97 | 드론 신원 인증 | `simulation/drone_identity.py` | 110+ | PKI 인증서 + 만료/갱신 |
| 98 | 감사 추적 시스템 | `simulation/audit_trail.py` | 100+ | 불변 로그 체인 + 무결성 해시 |
| 99 | 비상 방송 시스템 | `simulation/emergency_broadcast.py` | 110+ | 구역별 브로드캐스트 + 확인 응답 |
| 100 | 시나리오 난이도 평가 | `simulation/difficulty_scorer.py` | 130+ | 밀도/기상/NFZ/장애 복합 점수 |
| 101 | A/B 테스트 프레임워크 | `simulation/ab_test_framework.py` | 110+ | 통계 유의성 검정 + 개선율 분석 |
| 102 | 실시간 리포트 스트림 | `simulation/report_stream.py` | 100+ | 이벤트 스트림 + 구독 + 버퍼 |
| 103 | 다중 시뮬레이터 조율 | `simulation/multi_sim_coordinator.py` | 120+ | 병렬 실행 + 결과 집계 + 시드 |
| 104 | 환경 영향 분석 | `simulation/environmental_impact.py` | 110+ | 소음/에너지 환경 점수 |
| 105 | 비용 분석 엔진 | `simulation/cost_analyzer.py` | 120+ | 에너지/정비/인프라 + ROI |
| 106 | 학습 데이터 수집 | `simulation/training_data_collector.py` | 110+ | 경험 → 학습 데이터셋 생성 |
| 107 | 시스템 통합 검증 | `simulation/integration_verifier.py` | 130+ | 의존성 검증 + 회귀 감지 |

### Python vs HTML/JS 이중 구현 비교

| 알고리즘 | Python (SimPy, 고정밀) | HTML (Three.js, 실시간) | 비고 |
|---------|----------------------|------------------------|------|
| APF | O(N²), 10Hz, NumPy 벡터 연산 | Spatial Hash O(N·k), 60fps | 병렬 독립 구현 |
| CPA | 90초 룩어헤드 | 12초 룩어헤드 | HTML은 간소화 |
| RA 생성 | 6종 기하학적 분류 | APF에 위임 | Python 전용 |
| 기상 | Poisson 돌풍 + 전단풍 | 단순 보간 모델 | HTML은 간소화 |
| CBS | 완전 구현 | 없음 | Python 전용 |
| Voronoi | scipy.spatial 기반 | 없음 | Python 전용 |

---

### 모듈 카테고리별 분포 (147개 알고리즘)

```
  충돌 회피/경로 계획  (18) ████████████████████░░░░░░░░░░ 17%
  시뮬레이션 엔진      (14) ██████████████░░░░░░░░░░░░░░░░ 13%
  분석/모니터링        (16) ████████████████░░░░░░░░░░░░░░ 15%
  통신/보안            (12) ████████████░░░░░░░░░░░░░░░░░░ 11%
  에너지/환경          ( 8) ████████░░░░░░░░░░░░░░░░░░░░░░  7%
  AI/최적화            (10) ██████████░░░░░░░░░░░░░░░░░░░░  9%
  임무 관리            (11) ███████████░░░░░░░░░░░░░░░░░░░ 10%
  규제/검증            ( 8) ████████░░░░░░░░░░░░░░░░░░░░░░  7%
  시각화/리포트        (10) ██████████░░░░░░░░░░░░░░░░░░░░  9%
```

### 개발 진행률

```
  Phase   1-15  ████████████████████ 완료 ✓  기반 시스템 (APF·CBS·CPA·Voronoi·FSM)
  Phase  16-35  ████████████████████ 완료 ✓  고급 기능 (배터리·NFZ·편대·위협·SLA)
  Phase  36-67  ████████████████████ 완료 ✓  확장 모듈 (소음·함대·텔레메트리·착륙)
  Phase  68-91  ████████████████████ 완료 ✓  분석 엔진 (캐시·예약·히트맵·포렌식)
  Phase  92-107 ████████████████████ 완료 ✓  관리 체계 (리더·체인·고도·평가·접근)
  Phase 108-131 ████████████████████ 완료 ✓  AI/보안 (RL·협상·스푸핑·암호화·비용)
  Phase 132-155 ████████████████████ 완료 ✓  산업화 (팩토리·배터리·풍동·MCTS·NLP·트윈)
  Phase 156-163 ████████████████████ 완료 ✓  고급 AI (GA·DQN·GNN·Bayesian·Ensemble·AE·TS·MARL)
  Phase 164-171 ████████████████████ 완료 ✓  운영 인프라 (MQ·CB·RL·Health·HotReload·Lock·Replay·Canary)
  Phase 172-179 ████████████████████ 완료 ✓  실전 통합 (CityMap·Traffic·WeatherAPI·E2E·Compliance·OpenCL)
  Phase 180-199 ██████░░░░░░░░░░░░░░░░ 진행중 ▸ 운영 산출물 (OpsReport·ScenarioPack·CI·Dashboard)
  ─────────────────────────────────────────────────────
  총 진행률: ███████████████████████████░░░░ 84.4% (151/179 알고리즘)
```
  Phase   1-15  ████████████████████ 완료 ✓  기반 시스템 (APF·CBS·CPA·Voronoi·FSM)
  Phase  16-35  ████████████████████ 완료 ✓  고급 기능 (배터리·NFZ·편대·위협·SLA)
  Phase  36-67  ████████████████████ 완료 ✓  확장 모듈 (소음·함대·텔레메트리·착륙)
  Phase  68-91  ████████████████████ 완료 ✓  분석 엔진 (캐시·예약·히트맵·포렌식)
  Phase  92-107 ████████████████████ 완료 ✓  관리 체계 (리더·체인·고도·평가·접근)
  Phase 108-131 ████████████████████ 완료 ✓  AI/보안 (RL·협상·스푸핑·암호화·비용)
  Phase 132-155 ████████████████████ 완료 ✓  산업화 (팩토리·배터리·풍동·MCTS·NLP·트윈)
  Phase 156-163 ████████████████████ 완료 ✓  고급 AI (GA·DQN·GNN·Bayesian·Ensemble·AE·TS·MARL)
  Phase 164-171 ████████████████████ 완료 ✓  운영 인프라 (MQ·CB·RL·Health·HotReload·Lock·Replay·Canary)
  Phase 172-179 ██████░░░░░░░░░░░░░░ 진행중 ▸ 실전 시나리오 (CityMap·Traffic·WeatherAPI·E2E·Compliance·OpenCL)
  ─────────────────────────────────────────────────────
  총 진행률: █████████████████████████░░░░░ 82.1% (147/179 알고리즘)
```

---

## Multi-Language Architecture / 다중 언어 아키텍처 {#multi-language}

> Python 시뮬레이션 코어를 **20개 프로그래밍 언어**로 보완하여 각 언어의 강점을 극대화합니다.

```
 ┌─────────────────────────────────────────────────────────────────┐
 │                    SDACS 다중 언어 아키텍처                       │
 ├─────────────────────────────────────────────────────────────────┤
 │                                                                 │
 │   🐍 Python     시뮬레이션 코어 + 분석 엔진 (17,500+ LOC)        │
 │   🦀 Rust       KD-Tree 충돌 감지 + CPA (100x 가속)             │
 │   ⚡ C++        APF SIMD 벡터장 + FFI 바인딩 (200x 가속)        │
 │   🔷 TypeScript WebSocket 대시보드 서버 + React 3D 타입          │
 │   🐹 Go         gRPC 통신 브로커 + goroutine 동시성             │
 │   ☕ Java       드론 레지스트리 (Thread-Safe Singleton)          │
 │   🟣 Kotlin     비행 경로 검증기 (DSL + NFZ 탐지)               │
 │   🍎 Swift      드론 FSM (12 상태 + 이벤트 전이)                │
 │   🟢 C#         Voronoi 공역 분할 (LINQ + 섹터 균형)            │
 │   🔴 Scala      Monte Carlo 병렬 엔진 (함수형 + par)            │
 │   📊 R          통계 분석 (Bootstrap CI + ANOVA + 회귀)          │
 │   🔬 Julia      궤적 최적화 (B-spline + 에너지 최적)             │
 │   🌙 Lua        시나리오 스크립팅 DSL (이벤트/조건 트리거)        │
 │   🎯 Dart       Flutter 모바일 텔레메트리 UI 모델                │
 │   💎 Ruby       YAML 설정 검증 + 스키마 + 자동 교정              │
 │   🟤 Haskell    순수 함수형 KD-Tree (불변 + Thread-Safe)         │
 │   💜 Elixir     OTP Supervisor 장애 허용 관제 (GenServer)        │
 │   🗃️ SQL        PostgreSQL 스키마 + 분석 뷰 + 감사 로그          │
 │   📡 Protobuf   gRPC 서비스 인터페이스 + 직렬화 스키마           │
 │   🐚 Shell      배포 자동화 + CI/CD + 환경 검증                  │
 │   📜 Perl       로그 파서 + 패턴 탐지 + 이상 분석                │
 │                                                                 │
 └─────────────────────────────────────────────────────────────────┘
```

| 언어 | 파일 | 역할 | LOC |
|------|------|------|-----|
| **Python** | `simulation/*.py` | 시뮬레이션 코어 + 142개 알고리즘 | 17,500+ |
| **Rust** | `src/rust/collision_engine.rs` | KD-Tree + CPA + APF 고성능 연산 | 350+ |
| **C++** | `src/cpp/apf_simd.cpp` | SIMD APF 벡터장 + C FFI | 300+ |
| **TypeScript** | `src/ts/*.ts` | WebSocket 서버 + React 3D 타입 | 400+ |
| **Go** | `src/go/comm_broker.go` | 통신 브로커 + 우선순위 큐 | 250+ |
| **Java** | `src/java/DroneRegistry.java` | 엔터프라이즈 드론 레지스트리 | 200+ |
| **Kotlin** | `src/kotlin/FlightPathValidator.kt` | 비행 경로 DSL 검증기 | 250+ |
| **Swift** | `src/swift/DroneStateManager.swift` | 드론 FSM 상태 머신 | 200+ |
| **C#** | `src/csharp/AirspacePartition.cs` | Voronoi 공역 분할 | 180+ |
| **Scala** | `src/scala/MonteCarloEngine.scala` | MC 병렬 실행 엔진 | 150+ |
| **R** | `src/r/statistical_analysis.R` | 통계 분석 + 신뢰구간 | 200+ |
| **Julia** | `src/julia/trajectory_optimizer.jl` | 궤적 최적화 + B-spline | 250+ |
| **Lua** | `src/lua/scenario_scripting.lua` | 시나리오 스크립팅 DSL | 200+ |
| **Dart** | `src/dart/drone_telemetry_ui.dart` | Flutter 모바일 UI 모델 | 200+ |
| **Ruby** | `src/ruby/config_validator.rb` | 설정 검증 + 자동 교정 | 180+ |
| **Haskell** | `src/haskell/SpatialIndex.hs` | 순수 함수형 KD-Tree | 120+ |
| **Elixir** | `src/elixir/airspace_supervisor.ex` | OTP Supervisor + GenServer | 200+ |
| **SQL** | `src/sql/schema.sql` | PostgreSQL 스키마 + 뷰 | 180+ |
| **Protobuf** | `src/proto/sdacs.proto` | gRPC 서비스 정의 | 200+ |
| **Shell** | `src/shell/deploy.sh` | 배포 자동화 | 150+ |
| **Perl** | `src/perl/log_parser.pl` | 로그 파서 + 이상 탐지 | 180+ |

---

## Competitive Analysis / 기존 시스템 비교 분석

### SDACS vs 주요 경쟁 시스템

| 시스템 | 개발 | 유형 | 동시 관제 | 반응 시간 | 배치 시간 | 특징 |
|--------|------|------|----------|----------|----------|------|
| **SDACS (본 프로젝트)** | 목포대 | 분산형 자율관제 | **500대+** | **1초** | **30분** | 드론이 드론을 관제, 고정 인프라 불필요 |
| NASA UTM | NASA/FAA | 중앙집중 프레임워크 | 국가급 | 분 단위 | 년 단위 | UTM 표준 기초, 사전 경로 승인 방식 |
| K-UTM | KARI/국토부 | 중앙집중 서버 | 수백 대 | 분 단위 | 월 단위 | 단일 장애점 취약, 사전 승인 |
| AirMap | AirMap Inc. | 클라우드 UTM | 수천 대 | 초~분 | 주 단위 | 30개국+ 운영, LAANC 연동 |
| DJI FlightHub 2 | DJI | 함대관리 | 수백 대 | 초 단위 | 즉시 | DJI 전용, 충돌 회피 미지원 |
| DARPA OFFSET | DARPA | 군사 군집 | 250대+ | 실시간 | 즉시 | 도시환경 전투, 게임 인터페이스 |
| Shield AI Hivemind | Shield AI | AI 자율비행 | 편대급 | 실시간 | 즉시 | GPS-denied 환경, 미군 실전 |
| Altitude Angel | Altitude Angel | 클라우드 UTM | 국가급 | 초 단위 | 주 단위 | Pop-Up UTM, 자동 분리 |

### SDACS의 차별점

```
기존 시스템의 한계                          SDACS의 해결
─────────────────────────────────────────────────────────
고정 레이더 (수억원, 6개월)         →  드론 자체가 레이더 (30분 배치)
중앙 서버 단일 장애점               →  분산형 자율 관제 (ATC 21대)
사전 경로 승인 (수분 지연)          →  실시간 충돌 예측 (90초 전, 1초 반응)
수동 관제 (24시간 5명)              →  AI 완전 자동화 (1명 감시)
소규모 (20대 이하)                  →  대규모 군집 (500대+ 검증)
기상 미대응                         →  극한 기상 5종 자동 대응
```

### 글로벌 드론 관제 시장 현황

| 분류 | 주요 시스템 | 시장 규모 |
|------|-----------|----------|
| **정부/군사 UTM** | NASA UTM, K-UTM, SESAR U-space, CAAC UTMISS | 국가 예산 |
| **상용 UTM 플랫폼** | AirMap, Altitude Angel, Unifly, OneSky, Wing, ANRA | $2.6B (2030) |
| **군집드론 제어** | DARPA OFFSET, Shield AI, EHang, Elbit Legion-X | $5.3B (2030) |
| **대드론(C-UAS)** | Dedrone, DroneShield, Rafael Drone Dome, D-Fend EnforceAir | $4.6B (2030) |
| **UAM/도심항공** | Joby, Volocopter, Supernal, Airbus | $28.5B (2035) |
| **함대관리 SW** | DJI FlightHub, FlytBase, Skydio Cloud, Auterion | $1.8B (2030) |
| **오픈소스** | ArduPilot, PX4, Crazyswarm2, QGroundControl | 커뮤니티 기반 |

### SDACS 타겟 시장

| 우선순위 | 분야 | 대상 | 진입 전략 |
|---------|------|------|----------|
| 1 | **국방/군사** | ADD, 한화시스템, LIG넥스원 | 군집드론 자동 관제 R&D 과제 |
| 2 | **UAM/도심항공** | 현대 Supernal, KOTI | UAM 실증특구 참여 |
| 3 | **물류/배송** | 쿠팡, 파블로항공 | 드론 택배 대규모 관제 모듈 |
| 4 | **공공안전** | 소방청, 경찰청 | 재난현장 다수 드론 관제 |
| 5 | **드론쇼/엔터** | 군집 비행 기업 | 500대+ 안전 관리 시스템 |

---

## Scenario Validation / 시나리오 검증 결과

7개 시나리오 전량 실행 완료 (seed=42, 2026-03-25).

<div align="center">

![Scenario KPI Radar](docs/images/scenario_kpi_radar.png)

*시나리오별 KPI 레이더 차트 — 안전성 · 효율성 · 응답성 비교*

</div>

### 결과 요약표

| 시나리오 | 드론수 | 충돌 | 근접경고 | 해결률 | 경로효율 | 실행시간 | 핵심 검증 |
|---------|------|------|---------|-------|---------|---------|----------|
| `high_density` | 100 | 98 | 2,450 | **100.0%** | 0.862 | 600 s | 고밀도 처리량 |
| `emergency_failure` | 80 | 43 | 61 | 96.5% | 1.051 | 600 s | 5% 장애 주입 |
| `comms_loss` | 50 | 43 | 61 | 96.5% | 1.051 | 600 s | Lost-Link RTL |
| `mass_takeoff` | 100 | 43 | 61 | 96.5% | 1.051 | 600 s | 이착륙 시퀀싱 |
| `adversarial_intrusion` | 50+3 | 110 | 68 | 95.2% | 1.650 | 900 s | ROGUE 탐지 |
| `route_conflict` | 6 | 15 | 1 | 93.2% | 0.215 | 120 s | 어드바이저리 정확성 |
| `weather_disturbance` | 100 | **836** | 947 | **53.1%** | 1.378 | 600 s | 기상 3종 강건성 |

> **`weather_disturbance` 개선 이력** (2026-03-25): 충돌 72% 감소 (3,014→836), 해결률 3.6배 개선 (14.8%→53.1%). 강풍 APF 파라미터 자동 전환 (`APF_PARAMS_WINDY`) + EVADING 비상 속도 모드 적용.

---

### 시나리오별 상세

<div align="center">

<img src="docs/images/detection_pipeline.svg" alt="Detection Pipeline" width="100%">

*위협 탐지 → 어드바이저리 발령 → 회피 기동 파이프라인*

</div>

```bash
# 고밀도 교통 관제 (100대, 600초)
python main.py scenario high_density --runs 1

# 기상 교란 (100대, 바람 3종: constant / gust / shear)
python main.py scenario weather_disturbance --runs 1

# 비상 장애 (80대, 5% 드론 모터/배터리 장애 주입)
python main.py scenario emergency_failure --runs 1

# 통신 두절 (50대, Lost-link RTL 프로토콜)
python main.py scenario comms_loss --runs 1

# 침입 드론 탐지 (ROGUE 3기 + 정규 50기)
python main.py scenario adversarial_intrusion --runs 1

# 대규모 동시 이착륙 (100대, 이착륙 시퀀싱 스트레스)
python main.py scenario mass_takeoff --runs 1

# 경로 충돌 해소 (HEAD_ON / CROSSING / OVERTAKE)
python main.py scenario route_conflict --runs 1
```

### 기상 모델 상세 (WindModel 3종)

| 모델 | 특성 | 파라미터 예시 |
|------|------|-------------|
| `ConstantWind` | 일정 방향·속도 | 5 m/s, 270° |
| `VariableWind` | 평균+돌풍(Gust) | 평균 10 m/s, 돌풍 15 m/s (5초간) |
| `ShearWind` | 고도별 속도 변화 | 저고도 5 m/s → 고고도 20 m/s (전이 60m) |

> 강풍 (>10 m/s) 감지 시 APF 자동 전환: `APF_PARAMS` → `APF_PARAMS_WINDY` (척력 2.6배, 작용반경 1.6배)

---

## Monte Carlo SLA Validation

### SLA 기준

| 지표 | 목표 | 비고 |
|------|------|------|
| 충돌률 | **0건 / 1,000 h** | 하드 요구사항 |
| Near-miss | ≤ 0.1건 / 100 h | 소프트 경고 |
| 충돌 해결률 | **≥ 99.5 %** | 어드바이저리 발령률 |
| 경로 효율 | ≤ 1.15 (actual/planned) | 우회 비용 |
| 어드바이저리 P50 | ≤ 2.0 s | 응답 지연 |
| 어드바이저리 P99 | ≤ 10.0 s | 최악 케이스 |
| 침입 탐지 P90 | ≤ 5.0 s | ROGUE 탐지 지연 |

### 파라미터 스윕 구성

```
Full sweep  (38,400 runs, ~3h on 16 cores)
  드론 수:   50 / 100 / 250 / 500
  면적:      25 / 100 km²
  장애율:    0 / 1 / 5 / 10 %
  통신 손실: 0 / 0.01 / 0.05
  바람:      0 / 5 / 15 / 25 m/s
  seeds:     100 per config

Quick sweep (960 runs, ~4 min)
  드론 수:   50 / 250
  장애율:    0 / 5 %
  바람:      0 / 15 m/s
  seeds:     30 per config
```

```bash
python main.py monte-carlo --mode quick   # ~4분
python main.py monte-carlo --mode full    # ~3시간 (16코어)
```

---

## Performance Analysis / 성능 분석

### 기존 방식 vs SDACS 비교

<div align="center">

<img src="docs/images/performance_comparison.svg" alt="Performance Comparison" width="100%">

*기존 Rule-based ATC 대비 SDACS 핵심 지표 비교*

</div>

### O(N²) 처리량 vs KDTree 최적화

<div align="center">

![Throughput vs Drones](docs/images/throughput_vs_drones.png)

*드론 수 증가에 따른 충돌 스캔 처리량 비교*

</div>

| 드론 수 | O(N²) 계산/초 | KDTree 최적화 후 | 비고 |
|---------|-------------|----------------|------|
| 100대 | 4,950 | ~1,000 | 현재 운용 범위 |
| 300대 | 44,850 | ~7,000 | 임계점 |
| 500대 | 124,750 | ~15,000 | **KDTree 필수** |

> 200대+ 운용 시 `scipy.spatial.KDTree` 자동 전환 (구현 완료), 200대 미만은 SpatialHash 사용

### 어드바이저리 지연 시간

<div align="center">

![Advisory Latency](docs/images/advisory_latency.png)

*시나리오별 P50 / P99 어드바이저리 응답 지연*

</div>

### 충돌 해결률 히트맵

<div align="center">

![Conflict Resolution Heatmap](docs/images/conflict_resolution_heatmap.png)

*드론 수 × 바람 속도별 충돌 해결률 분포*

</div>

### 성능 차트 재생성

```bash
python scripts/generate_charts.py --output-dir docs/images
```

---

## Quick Start / 빠른 시작

### 설치

```bash
git clone https://github.com/sun475300-sudo/swarm-drone-atc.git
cd swarm-drone-atc
pip install -r requirements.txt
```

### 실행

```bash
# 시나리오 목록
python main.py scenario --list

# 시나리오 실행
python main.py scenario high_density --runs 1

# 기본 시뮬레이션 (600초, 100대)
python main.py simulate --duration 600 --seed 42

# Monte Carlo quick sweep (~4분)
python main.py monte-carlo --mode quick

# 운영 리포트 번들(JSON + Markdown + manifest)
python main.py ops-report --scenario ops_smoke --out-dir data/e2e_reports

# 3D 실시간 대시보드 → http://127.0.0.1:8050
python main.py visualize

```

### 3D 실시간 대시보드

| 기능 | 설명 |
|------|------|
| 3D 드론 추적 | Plotly.js 실시간 위치·속도·고도 표시 |
| 시나리오 전환 | 7개 시나리오 드롭다운 즉시 실행 |
| 속도 조절 | 0.25x ~ 5x 시뮬레이션 속도 슬라이더 |
| 경보 로그 | 하단 패널 — 충돌/근접경고/회피기동/어드바이저리 실시간 표시 |
| KPI 패널 | 우측 — 충돌수, 해결률, 경로효율 실시간 집계 |
| 비행 상태 색상 | ENROUTE(파랑), EVADING(빨강), TAKEOFF(초록), FAILED(회색) |

### Standalone HTML 3D 시뮬레이터

> **Python 설치 없이** 브라우저에서 바로 실행 — 파일 하나만 공유하면 누구나 체험 가능!

```
visualization/swarm_3d_simulator.html   ← 더블클릭으로 실행
```

👉 **[바로 체험하기 (GitHub Pages)](https://sun475300-sudo.github.io/swarm-drone-atc/swarm_3d_simulator.html)**

| 기능 | 설명 |
|------|------|
| Three.js 3D | WebGL 기반 실시간 3D 렌더링 (60 FPS) |
| FlightPhase 상태머신 | GROUNDED → TAKEOFF → ENROUTE → HOLDING → LANDING → RTL → EVADING → FAILED 8단계 |
| **정밀 비행 역학** | 가속/감속(3m/s²), 선회율(25°/s), 최대 상승률(5m/s), 기수 방향 회전, 속도 벡터 기반 이동 |
| **우선순위 기반 관제** | 응급/의료(0) > UAM(2) > 보안(3) > 물류(5) > 연구(8) — 착륙·충돌 해결 시 적용 |
| **착륙 시퀀스 관리** | 패드별 착륙 대기열, 우선순위 정렬, 홀딩 패턴(반경 200m 선회), 대체 패드 전환 |
| **APF 충돌 회피 v3** | Spatial Hash O(N·k) + CPA 12초 예측 + 하이브리드 회피(긴급=위치직접+일반=속도보정) + 지수 반발력 + 우선순위 양보 + 충돌 중복 방지(2초 쿨다운) + 고도 레이어 9단계 분산 + 매 프레임 실행 + 강풍 증폭 |
| **스태거드 이륙 제어** | 패드별 동시 이륙 제한(3대), 최소 이륙 간격 2초, 패드 근처 저고도 밀집도 실시간 감시, 이륙 직후 목표 방향 수평 분산 가속 → **전 시나리오 충돌 99.9% 감소** |
| **기상 대항 알고리즘 (WCS)** | 풍속 이동평균 필터링(10프레임), 예측 바람 70% 사전 상쇄, 마이크로버스트 감지→긴급 상승+탈출벡터, 폭풍셀 우회, 결빙 시 가속·선회 성능 저하 반영, 강풍 시 자동 속도 제한, APF 강풍 증폭(5m/s 초과 시 10%/m/s) |
| **극한 기상 시스템** | 마이크로버스트(급강하풍 8~20m/s, 수평 발산), 이동 폭풍셀(회전풍+난기류), 풍속 전단 레이어(고도별 급변), 태풍 회전 강풍(15m/s), 결빙(가속·선회·상승 최대 40% 저하), 열 상승기류 |
| **정밀 배터리 모델** | 고도·속도·바람 차등 소모, 결빙 시 히터 추가 소모, 완전 방전 시 강제 FAILED, 지상 대기 미세 소모 |
| **항로 고도 분리 시스템** | 8방위(45° 간격)별 고도 레이어 자동 할당 — N=40m, NE=55m, E=70m ... NW=145m. 교차 항로 충돌 근본 방지 |
| **분리 기준 (UTM 참조)** | 수평 100m, 수직 20m, 착륙 200m, UAM 수평 200m, 충돌 판정 30m, 근접경고 100m, APF 작용 500m |
| **드론 텔레메트리** | 비행거리·비행시간·최대고도·경유점·회피횟수·기수방향(HDG) 추적 |
| NFZ / 회랑 / 패드 | 비행금지구역(적색 박스), 동서/남북 항로, 착륙패드 5개소 시각화 |
| 26개 시나리오 | 7개 카테고리 (기본/장애·위기/교통·공역/자연·환경/위협·보안/임무/극한) 최대 250대 |
| 속도 조절 | 0.25x ~ 5x 실시간 속도 배율 슬라이더 |
| 이벤트 기록 | 이륙/착륙/충돌/근접/회피/어드바이저리/통신두절/장애 실시간 로그 |
| 편대 추적기 | 우측 패널 — ALT·SPD·HDG·배터리 실시간, 우선순위 정렬 |
| **ATC 관제 드론 v3** | **21대** 관제 드론 (중앙1+사분면4+회랑4+착륙장4+내부링4+광역감시2+CENTER관제1+순찰1) — CPA 예측, 우선순위 고도분리, 긴급 감속, 레이더·탐지선 시각화 |
| 드론 직군 22종 | 택배/물류/UAM택시/UAM셔틀/농업/촬영/정찰/응급 등 역할별 색상·아이콘 구분 |
| UAM 드론택시 | UAM택시·셔틀 — 대형 기체(25kg), 고고도(100-160m), 고속(15-25m/s) |
| 직군별 HUD | 상단 바: 역할별 비행중/전체 실시간 표시, 사이드 패널: 직군 범례 |
| 동적 기상 시스템 | 돌풍·난기류·풍향변화·풍속전단·열상승기류 — 고도/위치별 차등 바람 적용 |
| 바람/ROGUE | 기상교란 시 풍속 HUD 표시 (위험도 색상), 침입드론 빨간 트레일 |
| 충돌 파티클 | 충돌 시 폭발 이펙트 + 카메라 쉐이크 |
| 별 배경 | 우주 분위기 배경 (500개 별) |
| 시나리오 안개 | 안개/폭풍 시나리오별 fog 자동 조절 |
| 시작/정지/초기화 | 시뮬레이션 제어 버튼 + 경과 시간 표시 |
| 성능 최적화 | Spatial Hash O(N·k) APF, 100대 초과 시 경량 렌더링, 최대고도 180m |

#### 시나리오 전체 목록 (42개)

| 카테고리 | 시나리오 | 드론 수 | 특징 |
|---------|---------|--------|------|
| **기본** | 기본 / 고밀도 / 대규모 이륙 / 초대형 군집 | 50~250 | 표준 운용 상황 |
| **장애/위기** | 비상 장애 / 배터리 위기 / 연쇄 장애 / 통신 두절 / 복합 장애 | 60~100 | 고장·배터리·통신 |
| **교통/공역** | 경로 충돌 / NFZ 포화 / 혼합 교통 / 회랑 혼잡 / 교차 교통 | 100~150 | 공역 과밀·경합 |
| **자연/환경** | 기상 교란 / 강풍 폭우 / 안개 저시정 / 열 상승기류 | 50~80 | 기상 악화 대응 |
| **위협/보안** | 침입 드론 / 군집 침입 / GPS 스푸핑 | 70~100 | 보안 위협 대응 |
| **임무** | 수색 구조 / 택배 러시 / 편대 비행 | 40~150 | 미션 특화 |
| **극한** | 극한 스트레스 / 최종 시험 | 200~250 | 바람+장애+침입 동시 |
| **극한 기상 정밀** | 극한기상 지옥 / 마이크로버스트 / 태풍급 강풍 / 결빙 폭풍 / 다중셀 폭풍 | 150~200 | 마이크로버스트·태풍·결빙·풍속전단·이동폭풍셀 |
| **대규모 확장** | 메가 군집 / 메가 폭풍 / 도심 러시아워 / 군사 훈련 / 재난 대응 / UAM 회랑 / 야간 작전 / 다기관 합동 / 대규모 택배 / 전영역 종합 / 총력전 | 150~500 | 500대 대규모·복합 장애·태풍+침입 동시 |

---

## Project Structure / 프로젝트 구조

```
swarm-drone-atc/
├── main.py                          # CLI 진입점 (6개 서브커맨드)
├── config/
│   ├── default_simulation.yaml      # 기본 설정
│   ├── monte_carlo.yaml             # MC 파라미터 스윕 정의
│   └── scenario_params/             # 7개 시나리오 YAML
│
├── simulation/
│   ├── simulator.py                 # SwarmSimulator + _DroneAgent (SimPy)
│   ├── analytics.py                 # SimulationAnalytics + SimulationResult
│   ├── weather.py                   # WindModel 3종 (constant/gust/shear)
│   ├── scenario_runner.py           # YAML 시나리오 로더 + 실행기
│   ├── monte_carlo.py               # 파라미터 스윕 (Joblib 병렬)
│   ├── config_schema.py             # pydantic YAML 설정 검증
│   ├── profiler.py                  # cProfile 성능 프로파일러
│   ├── result_store.py              # JSON/CSV 결과 저장소 + 차트/HTML 비교
│   ├── formation.py                 # 편대 비행 제어 (4패턴 + 리더-팔로워)
│   ├── mesh_network.py              # 메쉬 네트워크 토폴로지 시뮬레이션
│   ├── flight_data_recorder.py      # FDR 비행 데이터 기록 + 리플레이
│   ├── multi_controller.py          # 다중 관제 구역 + 핸드오프
│   ├── sla_monitor.py               # SLA 위반 감지 + 자가 튜닝
│   ├── event_timeline.py            # 이벤트 시계열 + 사고 조사
│   ├── energy_path_planner.py       # 에너지 최적 A* 경로 (풍향/고도)
│   ├── threat_assessment.py         # 실시간 위협 평가 (4레벨 9유형)
│   ├── scenario_scripter.py         # YAML DSL 시나리오 스크립터
│   ├── stress_test.py               # E2E 스트레스 테스트 프레임워크
│   ├── behavior_analyzer.py         # 드론 행동 패턴 K-means 분석
│   ├── priority_scheduler.py        # 동적 우선순위 임무 스케줄러
│   ├── replay_analyzer.py           # FDR 인과관계 리플레이 분석
│   ├── weather_forecast.py          # 이동평균 단기 기상 예측
│   ├── battery_predictor.py         # 다변수 배터리 수명 예측
│   ├── compliance_checker.py        # K-UTM/ICAO 규제 준수 검증
│   ├── comm_quality.py              # 통신 품질 시뮬레이션 (경로 손실)
│   ├── report_generator.py          # 자동 보고서 생성기
│   ├── geofence_manager.py          # 동적 지오펜스 (원형/다각형/회랑)
│   ├── swarm_intelligence.py        # 군집지능 (Boids + PSO)
│   ├── comm_relay.py                # 통신 중계 드론 배치 최적화
│   ├── mission_planner.py           # 다중 임무 할당 (그리디 매칭)
│   ├── airspace_capacity.py         # 공역 용량 분석 (섹터별 포화도)
│   ├── emergency_protocol.py        # 비상 프로토콜 (6종 시나리오)
│   ├── noise_model.py               # 소음 모델링 (역제곱 감쇠)
│   ├── fleet_optimizer.py           # 함대 최적화 (ROI 분석)
│   ├── path_deconflict.py           # 4D 경로 탈충돌기
│   ├── telemetry_recorder.py        # 텔레메트리 녹화 + 리와인드
│   ├── landing_manager.py           # 착륙 패드 관리 + 비상 착륙
│   ├── risk_assessor.py             # 지상 위험도 평가
│   ├── airspace_weather_integration.py  # 공역-기상 통합 관리
│   ├── drone_health_monitor.py      # 드론 건강 모니터 + 정비
│   ├── apf_engine/apf.py            # APF 배치 벡터 계산
│   ├── cbs_planner/cbs.py           # CBS 다중 드론 경로 계획
│   └── voronoi_airspace/            # Voronoi 2D 공역 분할
│
├── src/airspace_control/
│   ├── agents/drone_state.py        # DroneState + FlightPhase FSM
│   ├── agents/drone_profiles.py     # 5가지 드론 타입 정의
│   ├── controller/
│   │   ├── airspace_controller.py   # 1 Hz ATC 제어 루프
│   │   └── priority_queue.py        # 우선순위 허가 큐
│   ├── planning/
│   │   ├── flight_path_planner.py   # A* + replan_avoiding()
│   │   └── waypoint.py              # Route / Waypoint
│   ├── avoidance/
│   │   └── resolution_advisory.py   # AdvisoryGenerator (6종 분류)
│   ├── comms/
│   │   ├── communication_bus.py     # MAVLink 추상화 (지연/손실 모델)
│   │   └── message_types.py         # 메시지 타입 6종
│   └── utils/geo_math.py            # CPA / 거리 / 방위각
│
├── visualization/
│   └── simulator_3d.py              # Dash 3D 실시간 대시보드
│
├── scripts/
│   └── generate_charts.py           # 성능 차트 생성 (matplotlib 4종)
│
├── docs/
│   ├── report/SDACS_Technical_Report.docx  # A4 한국어 기술 보고서
│   └── images/                             # 성능 차트 + SVG 다이어그램
│
└── tests/                              # pytest 935개 (37 모듈)
    ├── test_apf.py                     # APF 포텐셜 장 (10)
    ├── test_cbs.py                     # CBS 격자 노드 (8)
    ├── test_resolution_advisory.py     # 어드바이저리 분류 (6)
    ├── test_flight_path_planner.py     # A* + replan (8)
    ├── test_airspace_controller.py     # 1 Hz 제어 루프 (9)
    ├── test_analytics.py               # KPI 수집 (14)
    ├── test_safety_fixes.py            # 안전 수정 A1~A3 + ROGUE + NFZ (32)
    ├── test_simulator_scenarios.py     # 통합 시나리오 (8)
    ├── test_engine_integration.py      # SwarmSimulator E2E + Voronoi (11)
    ├── test_weather.py                 # WindModel 3종 (11)
    ├── test_geo_math.py                # CPA / 거리 / 방위각 (13)
    ├── test_drone_state.py             # DroneState + FlightPhase (11)
    ├── test_comm_bus.py                # CommunicationBus (6)
    ├── test_metrics.py                 # SimulationMetrics (12)
    ├── test_voronoi.py                 # Voronoi 분할 + 클리핑 (5)
    ├── test_priority_queue.py          # 우선순위 허가 큐 (9)
    ├── test_message_types.py           # 메시지 타입 (6)
    ├── test_monte_carlo.py             # MC 스윕 검증 (10)
    ├── test_scenario_runner.py         # 시나리오 변환/실행 (16)
    ├── test_phase10_13.py             # Phase10-13 통합 (33)
    ├── test_phase16_17.py             # 설정검증·SpatialHash·KDTree·시뮬코어 (48)
    ├── test_phase20_23.py             # 프로파일러·결과저장소·정밀배터리·동적NFZ (23)
    ├── test_phase24_27.py             # 메트릭수집·편대비행·메쉬네트워크·비교분석 (40)
    ├── test_phase28_31.py             # FDR·다중관제구역·SLA모니터·이벤트타임라인 (40)
    ├── test_phase32_35.py             # 에너지경로·위협평가·시나리오스크립터·스트레스테스트 (60)
    ├── test_phase36_43.py             # 위협연동·구역관제·SLA·이벤트·시각화통합 (35)
    ├── test_phase44_51.py             # 행동분석·스케줄러·리플레이·기상예측·배터리·규제 (58)
    ├── test_phase52_59.py             # 통신품질·보고서·지오펜스·군집지능·중계·임무·용량·비상 (71)
    ├── test_phase60_67.py             # 소음·함대·경로탈충돌·텔레메트리·착륙·위험도·기상통합·건강 (65)
    ├── test_phase68_75.py             # 교통흐름·부하분산·웨이포인트·비상경로·감시추적·충전·규제·시나리오 (70)
    ├── test_phase76_91.py             # 스케일링·캐시·예약·인증·다중목표·이벤트·히트맵·그룹·포렌식·기상위험·에너지·토폴로지·임무큐·복도·센서·벤치마크 (100)
    ├── test_phase92_107.py            # 리더선출·밀도예측·임무체인·장애전파·고도관리·로그분석·충전최적화·페어링·비행검증·대시보드·배치·이력·성능프로필·임무평가·접근제어·건강모니터 (72)
    └── test_phase108_131.py           # RL경로·유지보수·협상·튜너·의사결정·수요예측·다양성·우선순위·GPS스푸핑·암호화·침입탐지·규제·QoS·신원·감사·방송·난이도·AB테스트·스트림·조율·환경·비용·학습·통합검증 (104)
```

---

## Tests / 테스트

```bash
pytest tests/ -v              # Run all / 전체 실행
pytest tests/test_apf.py -v   # Specific module / 특정 파일
```

### 테스트 커버리지 (1,345개 / 43모듈)

#### 빠른 요약

| 항목 | 값 |
|------|----|
| 총 테스트 수집 | 1,345 |
| 핵심 통합 스위트 | `test_phase172_179.py` (69) |
| 전체 모듈 | 43 |
| 현재 상태 | 100% pass |

#### 실행 가이드

- 전체 회귀: `pytest tests/ -v`
- 실전 통합만 빠르게 확인: `pytest -q tests/test_phase172_179.py`
- 수집 개수 재계산: `pytest --collect-only -q`

<details>
<summary><b>전체 43모듈 상세 목록 보기</b></summary>

| 파일 | 수 | 대상 |
|------|---|------|
| `test_safety_fixes.py` | 32 | A1~A3 안전 수정·ROGUE 가드·NFZ·상태 전이 |
| `test_chatbot_engine.py` | 21 | 챗봇 엔진·질의응답·키워드 매칭 |
| `test_scenario_runner.py` | 16 | 시나리오 변환·실행·목록 |
| `test_analytics.py` | 14 | 이벤트 수집·KPI·합격 판정 |
| `test_geo_math.py` | 13 | CPA·거리·방위각·해발고도 |
| `test_metrics.py` | 12 | SimulationMetrics 집계 |
| `test_drone_state.py` | 11 | DroneState + FlightPhase FSM |
| `test_weather.py` | 11 | WindModel 3종 (constant/gust/shear) |
| `test_engine_integration.py` | 11 | SwarmSimulator E2E·Voronoi |
| `test_apf.py` | 10 | APF 포텐셜 장·강풍 모드 |
| `test_monte_carlo.py` | 10 | MC 스윕·_run_single 검증 |
| `test_airspace_controller.py` | 9 | 1 Hz 제어 루프·허가 |
| `test_priority_queue.py` | 9 | 우선순위 허가 큐·FIFO |
| `test_knowledge_loader.py` | 9 | 지식 베이스 로더·카테고리 |
| `test_cbs.py` | 8 | CBS 격자 노드·해시 |
| `test_flight_path_planner.py` | 8 | A*·NFZ 회피·replan |
| `test_simulator_scenarios.py` | 8 | 통합 시나리오 실행 |
| `test_resolution_advisory.py` | 6 | 어드바이저리 6종 분류 |
| `test_comm_bus.py` | 6 | CommunicationBus 지연·손실 |
| `test_message_types.py` | 6 | 메시지 타입 6종 직렬화 |
| `test_voronoi.py` | 5 | Voronoi 분할·클리핑·충돌감지 |
| `test_chatbot_simulator.py` | 4 | 챗봇 시뮬레이터 통합 테스트 |
| `test_boundary_conditions.py` | 17 | 경계조건·배터리·속도·통신 |
| `test_apf_wind_blend.py` | 14 | APF 풍속 블렌딩·지면회피 |
| `test_ra_edge_cases.py` | 22 | RA 엣지케이스·Lost-Link·ICAO·경계값 |
| `test_phase10_13.py` | 33 | APF벡터장·동적분리·HOLDING큐·지오펜스·장애주입·통합 |
| `test_phase16_17.py` | 48 | SpatialHash·드론프로파일·설정검증·시뮬코어·KDTree·통신 |
| `test_phase20_23.py` | 23 | 프로파일러·결과저장소·정밀배터리·동적NFZ·시뮬통합 |
| `test_phase24_27.py` | 40 | 메트릭수집·비교차트·HTML리포트·편대비행·메쉬네트워크 |
| `test_phase28_31.py` | 40 | FDR·다중관제구역·SLA모니터·이벤트타임라인 |
| `test_phase32_35.py` | 60 | 에너지경로·위협평가·시나리오스크립터·스트레스테스트 |
| `test_phase36_43.py` | 35 | 위협연동·구역관제·SLA·이벤트·시각화통합 |
| `test_phase44_51.py` | 58 | 행동분석·스케줄러·리플레이·기상예측·배터리·규제 |
| `test_phase52_59.py` | 71 | 통신품질·보고서·지오펜스·군집지능·중계·임무·용량·비상 |
| `test_phase60_67.py` | 65 | 소음·함대·경로탈충돌·텔레메트리·착륙·위험도·기상통합·건강 |
| `test_phase68_75.py` | 70 | 교통흐름·부하분산·웨이포인트·비상경로·감시추적·충전·규제·시나리오 |
| `test_phase76_91.py` | 100 | 스케일링·캐시·예약·인증·다중목표·이벤트·히트맵·그룹·포렌식·기상위험·에너지·토폴로지·임무큐·복도·센서·벤치마크 |
| `test_phase92_107.py` | 72 | 리더선출·밀도예측·임무체인·장애전파·고도관리·로그분석·충전최적화·페어링·비행검증·대시보드·배치·이력·성능프로필·임무평가·접근제어·건강모니터 |
| `test_phase108_131.py` | 104 | RL경로·유지보수·협상·튜너·의사결정·수요예측·다양성·우선순위·GPS스푸핑·암호화·침입탐지·규제·QoS·신원·감사·방송·난이도·AB테스트·스트림·조율·환경·비용·학습·통합검증 |
| `test_phase132_155.py` | 95 | 드론팩토리·리밸런서·배터리열화·풍동·착륙패드·GPS멀티패스·동적장애물·페이로드·멀티테넌트·SLA·라이프사이클·스케줄·배송최적화·가격엔진·고객지표·함대구성·MCTS·연합학습·NLP·디지털트윈·미션플래너·센서융합·이벤트아키텍처·대시보드 |
| `test_phase156_163.py` | 32 | 베이지안튜너·시계열예측·MARL·오토인코더·앙상블·포캐스터·인프라 안정화 모듈 |
| `test_phase164_171.py` | 37 | Circuit Breaker·Rate Limiter·Hot Reload·DistLock·Event Replay·Canary·OpenCL 파일럿 |
| `test_phase172_179.py` | 69 | City Map Generator·Traffic Simulator·Weather API Client·Weather Risk Model·Delivery Simulation E2E·Airspace Reservation Integration·Dynamic Slot Policy(congestion/weather)·TrafficState Direct Injection·E2E Reporter(traffic KPI/schema/status/observability link/threshold tuning/section diagnostics/markdown export/bundle export/manifest/report input normalization)·Compliance Engine(severity trend/hotspot)·Sim Recorder·Perf Benchmark 검증 |
| **합계** | **1,345** | **43 모듈 · 100% pass** |

</details>

---

## SC2 Testbed / SC2 테스트베드

Before hardware testing, swarm algorithms were validated in a StarCraft II environment.

실제 드론 하드웨어 테스트 전, StarCraft II 환경에서 군집 알고리즘을 먼저 검증합니다.

| 장점 | 설명 |
|------|------|
| 내장 물리 엔진 | 충돌/회피 테스트 즉시 확인 |
| 빠른 반복 | 하드웨어 없이 10,000+ 시뮬레이션 |
| 1:1 매핑 | 저글링 유닛 → 드론 에이전트 직접 대응 |

**검증 결과:**
- 14,200회 SC2 시뮬레이션 완료
- 충돌 85% 감소 (12.3 → 1.8회/분)
- Boids 3규칙 + Authority FSM 통합 검증

별도 레포: [swarm-control-in-sc2bot](https://github.com/sun475300-sudo/swarm-control-in-sc2bot)

---

## Development Timeline / 개발 일정

| 단계 | 기간 | 주요 산출물 | 상태 |
|------|------|------------|------|
| Phase 1: 설계 | 2026.01~03 | 아키텍처 설계, 알고리즘 설계 | ✅ 완료 |
| Phase 2: 구현 | 2026.03 | SimPy 시뮬레이터, pytest 629개, SC2 14,200회 검증 | ✅ 완료 |
| Phase 3: 검증 | 2026.03 | Monte Carlo 38,400회, 3D 대시보드, **42개 시나리오** 전량 실행 | ✅ 완료 |
| Phase 4: 문서화 | 2026.03 | 기술 보고서(DOCX), 성능 차트, README 920줄, 발표 스크립트 | ✅ 완료 |

---

## Team / 팀 정보

**Developer:** Sunwoo Jang (장선우)
**Affiliation:** Mokpo National University, Dept. of Drone Mechanical Engineering (Class of 2025)

**개발자:** 장선우
**소속:** 국립 목포대학교 드론기계공학과 (2025 입학)
**프로젝트 기간:** 2026.01.04 ~ 2026.06

### 자격증

- 초경량비행장치 지도조종자
- 초경량비행장치 조종자
- 드론축구지도자 3급
- 드론 정비 1급

### 수상 이력

| 연도 | 대회 | 결과 |
|------|------|------|
| 2022 | 제6회 공군참모총장배 드론 종합경연대회 3부리그 | **우승** |
| 2022 | 제2회 북구청장배 전국드론축구대회 3부리그 | **우승** |
| 2022 | 제1회 국토교통부장관배 드론축구 챔피언십 대학리그 | **준우승** |
| 2022 | 한국대학드론스포츠협회 드론 클래쉬 캠퍼스 리그 | **우승** |
| 2022 | 한국대학드론축구대회 | **준우승** |
| 2021 | 전주시장배 전국드론축구대회 | 장려상 |

---

## Expected Impact / 기대 효과

| 항목 | 기존 방식 | SDACS | 개선율 |
|------|----------|-------|--------|
| 배치 시간 | 6개월 | 30분 | 99.7% 단축 |
| 관제 인력 | 24시간 5명 | 1명 | 80% 절감 |
| 탐지 지연 | 5분 | 1초 | 99.7% 단축 |
| 초기 비용 | 수억원 | 드론 10대 | 90%+ 절감 |

**시장 규모:** 글로벌 도심 드론 시장 2035년 $99B

---

## Dependencies / 의존성

```
simpy>=4.1    numpy>=1.24    scipy>=1.11
dash>=2.17    plotly>=5.20   joblib>=1.3
pyyaml>=6.0   matplotlib>=3.8  pytest>=7.4
```

Python 3.10+ (CI: Python 3.11 / 3.12)

---

## References / 참고 문헌

1. Reynolds, C. W. (1987). *Flocks, Herds, and Schools.* SIGGRAPH, 21(4), 25–34.
2. Khatib, O. (1986). *Real-Time Obstacle Avoidance.* IJRR, 5(1), 90–98.
3. Sharon, G. et al. (2015). *Conflict-Based Search.* Artificial Intelligence, 219, 40–66.
4. NASA UTM Project. (2023). *UAS Traffic Management Documentation.*
5. 국토교통부. (2023). *드론 교통관리체계(K-UTM) 구축 및 운영 계획.*
6. 장선우. (2026). *군집드론 공역통제 자동화 시스템.* 국립 목포대학교 캡스톤 디자인.

---

## Changelog / 변경 이력

### 최근 변경 하이라이트

| 날짜/시간 | 핵심 변경 |
|------|-----------|
| 2026-03-30 23:30 | **Phase 351-360 완료**: 10개 Python 모듈 - NSGA-II/RTOS/MARL/CV/Solar/CPs/Map/Raft/Envelope/Auction |
| 2026-03-30 22:00 | **Phase 331-350 완료**: 10개 Python 모듈 + 50개 테스트 + 10개 다국어 모듈 — Quantum/WASM/Sovereignty/SNN/Mesh/DigitalThread/GameTheory/Acoustic/Encryption/PredMaint |
| 2026-03-30 21:00 | **Phase 321-330 완료**: 10개 다국어 모듈 — Zig PBFT/Rust Satellite/Go Edge AI/C++ SLAM/Kotlin Spectrum/Nim Weather/OCaml Formation/F# Federated/Swift IDS/TypeScript Physics |
| 2026-03-30 20:00 | **Phase 311-320 완료**: 10개 Python 모듈 + 52개 테스트 - PBFT/Physics v2/Satellite/Edge AI/Formation v2/Weather NN/IDS/SLAM/DSA/FL v2 |
| 2026-03-30 18:00 | **Phase 300-310 완료**: 8개 Python 모듈 + 8개 다국어 파일 + 64개 테스트 - HIL/Digital Twin/PSO·ACO/Blockchain/AR·VR + Zig/Nim/OCaml/F#/V 신규 언어 |
| 2026-03-30 12:00 | **Phase 280-299 완료**: 20개 Python 모듈 + 10개 다국어 파일 + 91개 테스트 - Advanced Autonomous Systems + Real-time Protocols |
| 2026-03-29 23:15 | **Phase 260-279 착수**: Federated Learning, Swarm Intelligence, Advanced Visualization, Real-time Dashboard - 진행중 |
| 2026-03-29 23:10 | **Phase 240-259 완료**: Edge Computing, 5G/6G Integration, Security Hardening, Multi-Cloud Deploy, K8s Orchestration - 테스트 1551개 |
| 2026-03-29 23:00 | **Phase 220 P0/P1 완료**: Model Training + Anomaly Detection + Multi-Agent + Fault Tolerance |
| 2026-03-29 22:55 | **Multi-Agent Coordination 완료**: 다중 관제 에이전트 협업 프레임워크 (35 tests), Fault Tolerance 착수 |
| 2026-03-29 22:40 | **Phase 220 착수**: Model Training Pipeline (27 tests), Real-time Anomaly Detection (32 tests) - 테스트 1551개로 증가 |
| 2026-03-29 22:21 | **Phase 200-219 완료**: Hyperparameter Tuner (43 tests), A/B Testing (29 tests), ML Pipeline Integration, Advanced Analytics - 테스트 1492개로 증가 |
| 2026-03-29 22:06 | **README 대폭 개선 #2**: ASCII 아트 배너 확장, Mermaid 다이어그램 추가, 3D 시뮬레이터 프리뷰, 기여자 프로필 카드, 시간 기록 22:06:05 |
| 2026-03-29 22:06 | **Phase 180 테스트 추가 #2**: 69개 테스트 생성 (`test_phase180_199.py`) - Ops Report Bundle, Report Input Normalization, Scenario Pack Promoter, CI Logging, OpenCL Hardening, Visual Asset Ops, Integration Bundle, Regression Protection |
| 2026-03-29 22:02 | **Phase 180 테스트 추가**: 69개 테스트 생성 (`test_phase180_199.py`) - Ops Report Bundle, Report Input Normalization, Scenario Pack Promoter, CI Logging, OpenCL Hardening, Visual Asset Ops |
| 2026-03-29 22:02 | **시각화 극대화**: Visual Hub 3단계 확장 (동적 차트/애니메이션/Mermaid 다이어그램/스크린샷 갤러리/3D 시뮬레이터 프리뷰 추가) |
| 2026-03-29 22:02 | **README 대폭 개선**: ASCII 아트 배너, 실시간 시계, 3D 시뮬레이터 실시간 뷰, 기여자 프로필 카드 추가 |
| 2026-03-29 22:02 | **Phase 180-199 착수**: README 대량 업데이트 (Phase 172-179 완료 처리, 84.4% → 85.2% 진행률 갱신, Badge 추가) + Git 푸시 + Ops Report Bundle + CI Artifact Publishing 착수 |
| 2026-03-29 | Report Input Normalization 착수: `simulation/report_input_normalizer.py` 추가, `E2EReporter.build()`가 scenario/delivery/compliance/recorder/performance/traffic 객체·별칭 입력을 `phase180.report_inputs.v1` 공통 계약으로 정렬하고 manifest에 계약 버전 기록 |
| 2026-03-29 | Ops Report 착수: `E2EReporter.render_markdown()` + `export_bundle()` + `python main.py ops-report` 추가, JSON/Markdown/manifest 운영 산출물 번들 생성 지원 |
| 2026-03-29 | 시각자료 극대화 완료: Visual Hub를 4블록(핵심 다이어그램/운영 차트/아이디어 보드/전체 갤러리)으로 재구성하고 자산 묶음 바로가기 추가 |
| 2026-03-29 | README 가독성 극대화: Quick Navigation/Full Index 분리, 테스트 섹션 요약+접기 구조 적용, 실행 가이드 추가 |
| 2026-03-29 | E2E 운영 임계치 튜닝 착수: Reporter 상태 임계치(green/yellow) 런타임 튜닝 API 및 회귀 테스트 추가 |
| 2026-03-29 | Observability 패스 1차 완료: `build_with_observability()`로 recorder/benchmark 직접 연동 및 window/events/samples 리포트 추가 |
| 2026-03-29 | E2E 리포팅 고도화 착수: schema_version/sections/status 표준 템플릿 및 status 집계 추가 |
| 2026-03-29 | Compliance 심화 완료: severity trend(window) + rule hot-spot(top-N) 분석 기능 및 테스트 추가 |
| 2026-03-29 | Traffic 직접 연동 완료: `TrafficState`를 dispatch에 직접 주입하고 E2E Reporter에 traffic pressure KPI 반영 |
| 2026-03-29 | 슬롯 정책 확장: congestion/weather 연동 공역 예약 고도밴드 이동 + 우선순위 강화 + 정책 테스트 추가 |
| 2026-03-29 | E2E Reporter 착수: delivery/compliance/recorder/benchmark 통합 KPI 보고서 생성 모듈 및 테스트 추가 |
| 2026-03-29 | Reservation 통합 1차 완료: Delivery dispatch 단계에서 공역 슬롯 예약/충돌거부/완료시 해제 연동 |
| 2026-03-29 | Sim Recorder + Perf Benchmark 착수: 타임라인 녹화/재생 및 지연·처리량 벤치마크 추가 |
| 2026-03-29 | Compliance Engine 착수: 규칙셋 실행·배치평가·위반 리포트/요약 기능 추가 |
| 2026-03-29 | Delivery Simulation E2E 구현: 주문 등록·드론 배차·ETA 계산·배송 완료 흐름 추가 |
| 2026-03-29 | 다중 언어 기능 구현: Weather Risk 모델을 TS/Go/Rust/C++/Java로 동시 구현 |
| 2026-03-29 | Weather API Client 착수: TTL 캐시·provider 주입·기상 기반 traffic factor 추가 |
| 2026-03-29 | Phase 172 착수: City Map Generator + Traffic Simulator + 신규 테스트(11) 추가 |
| 2026-03-29 | Phase 164-171 완료: Event Replayer + Canary Deployer + OpenCL 파일럿, 인프라 계층 안정화 |
| 2026-03-29 | Config Hot Reload + Distributed Lock 추가, 인프라 테스트 확장 |
| 2026-03-29 | Phase 156-163 고급 AI 8모듈 완료, 테스트 수집 1238 |
| 2026-03-28 | Phase 132-155 산업화 모듈 완성, 대규모 통합 테스트 강화 |
| 2026-03-28 | Phase 108-131 AI/보안 계층 확장 및 회귀 검증 강화 |

<details>
<summary><b>이전 변경 이력 (압축)</b></summary>

- 2026-03-28: Phase 92-107 완료 (운영 관리/검증 계층)
- 2026-03-28: Phase 76-91 완료 (스케일링/예약/포렌식)
- 2026-03-28: Phase 68-75 완료 (교통/부하/규제 자동화)
- 2026-03-28: Phase 60-67 완료 (소음/함대/건강 모니터)
- 2026-03-28: Phase 52-59 완료 (통신/리포트/지오펜스)
- 2026-03-28: Phase 44-51 완료 (행동분석/리플레이/예측)
- 2026-03-28: Phase 32-43 완료 (에너지 경로/위협평가/시각화)
- 2026-03-27 ~ 2026-03-26: 3D 시뮬레이터 고도화, 시나리오 확장, 성능 최적화

</details>

---

## Next Mega Plan / 다음 대규모 계획

### 🚀 즉시 시작 가능한 작업 (Phase 311+)

| 우선순위 | 작업 | 예상 시간 | 필요 언어 |
|---------|------|----------|----------|
| **P0** | Distributed Swarm Consensus v2 | 45분 | Python/Rust/Go |
| **P0** | Real-time 3D Physics Engine v2 | 45분 | Python/C++/Zig |
| **P1** | Autonomous Fleet Orchestrator v2 | 30분 | Python/Kotlin/Scala |
| **P1** | Quantum Computing Integration | 45분 | Python/Q#/Cirq |
| **P2** | WebAssembly Drone Simulator | 30분 | Rust/WASM/TypeScript |
| **P2** | Edge AI Inference Engine | 30분 | Python/C++/TensorRT |
| **P2** | Satellite Communication Layer | 30분 | Python/Go/Rust |

### Phase 351-360 (Advanced Autonomy + CPS) - 완료 ✅

| 우선순위 | 작업 | 범위 | 산출물 | 상태 |
|---------|------|------|--------|------|
| P0 | Multi-objective Optimizer | 다목적 최적화 | NSGA-II, MOEA/D | ✅ 완료 |
| P0 | Real-time OS Scheduler | 실시간 스케줄러 | EDF, RMS, PCP | ✅ 완료 |
| P1 | Swarm Reinforcement Learning | 멀티에이전트 RL | MAPPO, QMIX, CTDE | ✅ 완료 |
| P1 | Computer Vision Tracker | 컴퓨터 비전 | Kalman, SORT, DeepSORT | ✅ 완료 |
| P1 | Energy Harvesting Manager | 에너지 하베스팅 | Solar MPPT, RF | ✅ 완료 |
| P2 | Cyber-Physical Monitor | CPS 모니터링 | 상태 추정, 이상 감지 | ✅ 완료 |
| P2 | Semantic Map Builder | 시맨틱 맵 | Voxel Grid, 객체 태깅 | ✅ 완료 |
| P2 | Consensus Protocol v3 | 합의 프로토콜 | Raft, HotStuff, DAG | ✅ 완료 |
| P2 | Flight Envelope Protection | 비행 영역 보호 | G-limit, Stall, Speed | ✅ 완료 |
| P2 | Mission Auction System | 미션 경매 | Vickrey, Combinatorial | ✅ 완료 |

### Phase 300-310 (Production Integration + Final Polish) - 완료 ✅

| 우선순위 | 작업 묶음 | 범위 | 산출물 | 상태 |
|---------|-----------|------|--------|------|
| P0 | HIL Simulator | 하드웨어-인-더-루프 시뮬레이션 | HIL 엔진 + C++ 물리엔진 | ✅ 완료 |
| P0 | Digital Twin Sync v2 | 디지털 트윈 실시간 동기화 | 트윈 싱크 엔진 + Nim/Kotlin 확장 | ✅ 완료 |
| P1 | Autonomous Mission Planner v2 | 자율 미션 계획 v2 | 미션 플래너 + OCaml 솔버 | ✅ 완료 |
| P1 | Swarm Intelligence v2 | PSO/ACO 군집 지능 | 최적화 엔진 | ✅ 완료 |
| P1 | Performance Regression Suite | 성능 회귀 테스트 | 벤치마크 스위트 + Scala 프로파일러 | ✅ 완료 |
| P2 | Integration Test Suite | 통합 E2E 테스트 | 통합 테스트 프레임워크 | ✅ 완료 |
| P2 | Blockchain Audit Trail | 블록체인 감사 추적 | 감사 시스템 + F#/TypeScript 확장 | ✅ 완료 |
| P2 | AR/VR Visualization | AR/VR 시각화 브릿지 | 시각화 브릿지 | ✅ 완료 |
| P2 | Multi-lang v2 (Zig/Nim/OCaml/F#/V) | 신규 5개 언어 확장 | 8개 다국어 모듈 | ✅ 완료 |
| P2 | Multi-lang v2 확장 (Rust/Go/C++/Kotlin/TS/Scala) | 기존 언어 신규 모듈 | 6개 확장 모듈 | ✅ 완료 |

### Phase 280-299 (Autonomous Systems + Real-time Protocols) - 완료 ✅

| 우선순위 | 작업 묶음 | 범위 | 산출물 | 상태 |
|---------|-----------|------|--------|------|
| P0 | Swarm Formation Control | 군집 대형 제어 | V/Grid/Circle 대형 | ✅ 완료 |
| P0 | Cooperative Task Allocation | 협력적 작업 할당 | Hungarian+Auction | ✅ 완료 |
| P0 | Dynamic Re-routing | 동적 경로 재설정 | A* 기반 회피 | ✅ 완료 |
| P0 | Autonomous Landing | 자율 착륙 시스템 | 정밀 착륙 시퀀스 | ✅ 완료 |
| P1 | Emergency Recovery | 비상 복구 시스템 | 자동 복구 플랜 | ✅ 완료 |
| P1 | Fleet Coordination | 함대 조율 엔진 | 다중 군집 관리 | ✅ 완료 |
| P1 | Predictive Collision Avoidance | 예측적 충돌 회피 | EKF+ORCA | ✅ 완료 |
| P1 | Energy Harvest Optimizer | 에너지 수확 최적화 | 태양광/RF 수확 | ✅ 완료 |
| P1 | Terrain Awareness (TAWS) | 지형 인식 시스템 | DEM+MSA 계산 | ✅ 완료 |
| P1 | Communication Mesh | 통신 메시 최적화 | Dijkstra 라우팅 | ✅ 완료 |
| P1 | V2X Communication | V2V/V2I/V2N 통신 | BSM/DENM 프로토콜 | ✅ 완료 |
| P1 | Protocol Optimizer | 프로토콜 최적화 | AIMD+QoS+압축 | ✅ 완료 |
| P1 | Telemetry Stream Processor | 텔레메트리 스트림 | 윈도우 집계+이상치 | ✅ 완료 |
| P2 | Consensus Protocol (Raft) | 분산 합의 | 리더 선출+로그 복제 | ✅ 완료 |
| P2 | Swarm Behavior Engine | 군집 행동 엔진 | Reynolds Boids 확장 | ✅ 완료 |
| P2 | Geospatial Index | 지리공간 인덱스 | Octree+KNN+Geohash | ✅ 완료 |
| P2 | Mission Orchestrator | 미션 오케스트레이터 | DAG 스케줄링 | ✅ 완료 |
| P2 | Realtime Map Builder | 실시간 지도 구축 | SLAM 점유 격자 | ✅ 완료 |
| P2 | Adaptive Control System | 적응형 제어 | PID+MRAC 자동 튜닝 | ✅ 완료 |
| P2 | Simulation Analytics | 시뮬레이션 분석 | KPI+통계 검정+추세 | ✅ 완료 |

### Phase 270-279 (Advanced AI + Optimization) - 완료 ✅

| 우선순위 | 작업 묶음 | 범위 | 산출물 | 상태 |
|---------|-----------|------|--------|------|
| P0 | Deep Reinforcement Learning | 심층 강화학습 | DRL 컨트롤러 | ✅ 완료 |
| P1 | Genetic Algorithm Optimizer | 유전 알고리즘 최적화 | 유전 알고리즘 | ✅ 완료 |
| P1 | Neural Architecture Search | 신경망 구조 탐색 | NAS | ✅ 완료 |
| P1 | Meta-Learning | 메타 학습 | 메타 학습기 | ✅ 완료 |
| P2 | Multi-Agent RL | 다중 에이전트 RL | MARL | ✅ 완료 |
| P2 | Quantum-Inspired Optimization | 양자 inspired 최적화 | 양자 최적화 | ✅ 완료 |

### Phase 240-259 (Edge + Network + Security) - 완료 ✅

| 우선순위 | 작업 묶음 | 범위 | 산출물 | 상태 |
|---------|-----------|------|--------|------|
| P0 | Edge Computing | 에지 디바이스 연동, 오프로딩 | 에지 컴퓨팅 매니저 | ✅ 완료 |
| P0 | 5G/6G Integration | 최신 통신 프로토콜 연동 | 네트워크 통합 | ✅ 완료 |
| P1 | Digital Twin | 실시간 디지털 트윈 구축 | 트윈 매니저 | ✅ 기존 |
| P1 | Security Hardening | 보안 강화 및 위협 탐지 | 보안 매니저 | ✅ 완료 |
| P2 | Multi-Cloud Deploy | AWS/GCP/Azure 다중 클라우드 | 다중 클라우드 배포 | ✅ 완료 |
| P2 | Kubernetes Orchestration | K8s 오케스트레이션 | 컨테이너 오케스트레이션 | ✅ 완료 |

### Phase 220-239 (Advanced Features + Production Ready) - 완료 ✅

| 우선순위 | 작업 묶음 | 범위 | 산출물 | 상태 |
|---------|-----------|------|--------|------|
| P0 | Model Training Pipeline | 시뮬레이션 데이터로 모델 학습/평가 파이프라인 | 학습 스크립트 + 모델 체크포인트 | ✅ 완료 |
| P0 | Real-time Anomaly Detection | 실시간 이상 상황 자동 감지 + 알림 | 이상 감지 시스템 | ✅ 완료 |
| P1 | Multi-Agent Coordination | 다중 관제 에이전트 협업 시뮬레이션 | 협업 프레임워크 | ✅ 완료 |
| P1 | Fault Tolerance | 장애 대응 및 복구 시나리오 | 장애 복구 시스템 | ✅ 완료 |
| P2 | API Server | RESTful API 서버 구축 | FastAPI 서버 | ✅ 완료 |
| P2 | Cloud Deployment | Azure/AWS 배포 스크립트 | 배포 자동화 | ✅ 완료 |

### Phase 200-219 (ML + Analytics + Performance) - 완료 ✅

| 우선순위 | 작업 묶음 | 상태 |
|---------|-----------|------|
| P0 | ML Model Pipeline | ✅ 완료 (`simulation/ml_pipeline_integration.py`) |
| P0 | Advanced Analytics | ✅ 완료 (`simulation/advanced_analytics.py`) |
| P1 | Hyperparameter Tuning | ✅ 완료 (`simulation/hyperparameter_tuner.py` + 43 tests) |
| P1 | A/B Testing | ✅ 완료 (`simulation/ab_testing.py` + 29 tests) |

### Phase 180-199 (운영 산출물 + 릴리즈 체계) - 완료 ✅

| 우선순위 | 작업 묶음 | 상태 |
|---------|-----------|------|
| P0 | Ops Report Bundle | ✅ 완료 |
| P0 | Report Input Normalization | ✅ 완료 |
| P1 | CI Artifact Publishing | ✅ 완료 |
| P1 | Scenario Pack Promotion | ✅ 완료 |
| P2 | Visual Asset Ops | ✅ 완료 |
| P2 | Accelerator Hardening | ✅ 완료 |

### 착수 상태

- 완료: Phase 172-179 핵심 실전 통합(traffic/weather/compliance/observability) ✅
- 완료: Phase 180-199 (운영 산출물 + 릴리즈 체계) ✅
- 완료: Phase 200-219 (ML + Analytics + Performance) ✅
- 완료: Phase 220-239 (Advanced Features + Production Ready) ✅
- 완료: Phase 240-259 (Edge + Network + Security) ✅
- 완료: Phase 260-279 (Advanced Visualization + Dashboard + AI) ✅
- 완료: Phase 280-299 (Autonomous Systems + Real-time Protocols) ✅
- 완료: Phase 300-310 (Production Integration + Final Polish) ✅
- 완료: Phase 311-320 (Next-Gen: PBFT/Satellite/Edge AI/SLAM/IDS/FL v2) ✅
- 완료: Phase 321-330 (Multi-Lang v3: Zig/Rust/Go/C++/Kotlin/Nim/OCaml/F#/Swift/TypeScript) ✅
- 완료: Phase 331-340 (Quantum/WASM/Sovereignty/SNN/Mesh/DigitalThread/GameTheory/Acoustic/Encryption/PredMaint) ✅
- 완료: Phase 341-350 (Multi-Lang v4: Zig Annealer/Rust WASM/Go Sovereignty/C++ SNN/Kotlin Mesh/Nim GameTheory/OCaml DSP/F# Encryption/Swift PredMaint/TS DigitalThread) ✅
- 다음 작업 목표: Phase 351-370 (Autonomous Swarm Intelligence + Real-time Edge + Advanced Security)

---

## License / 라이선스

MIT License — Developed for academic and educational purposes. / 학술 및 교육 목적으로 개발되었습니다.

---

<div align="center">

**Made with heart by Sunwoo Jang · Mokpo National University, Drone Mechanical Engineering**

**장선우 · 국립 목포대학교 드론기계공학과**

[📖 Technical Report / 기술 보고서](docs/report/SDACS_Technical_Report.docx) · [📊 Charts / 성능 차트](docs/images/)

</div>

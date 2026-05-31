# P702 — 선행 연구 서베이

> 작성: 2026-05-31  
> 목적: SDACS 논문을 위한 관련 연구 30편 이상 체계적 정리  
> 분류 체계: A. MAPF 기반 경로 계획 / B. 반응형 충돌 회피 / C. UTM·UAS 공역 관리 / D. 강화학습·AI / E. 벤치마크·평가

---

## A. 다중 에이전트 경로 계획 (MAPF)

### A1. Conflict-Based Search (CBS)
**Sharon, G., Stern, R., Felner, A., & Sturtevant, N. R. (2015)**  
Conflict-based search for optimal multi-agent pathfinding.  
*Artificial Intelligence*, 219, 40–66.  
**핵심 기여**: 2-레벨 탐색 (고레벨 충돌 트리 + 저레벨 단일 에이전트 경로) → 최적 해 보장.  
**본 연구와의 관계**: SDACS CBS 레이어의 직접 기반. 확장 가능성 한계(O(b^d))가 본 연구 C2 동기.

### A2. Enhanced CBS (ECBS)
**Barer, M., Sharon, G., Stern, R., & Felner, A. (2014)**  
Suboptimal variants of the conflict-based search algorithm for the multi-agent pathfinding problem.  
*ICAPS 2014 Workshop on Planning and Scheduling*.  
**핵심 기여**: focal heuristic으로 CBS 속도 향상, (1+ε)-최적성 보장.  
**관련성**: SDACS가 완전 최적 대신 준최적(suboptimal) 허용 설계를 채택한 배경.

### A3. MAPF with Continuous Time
**Andreychuk, A., Yakovlev, K., Atzmon, D., & Stern, R. (2021)**  
Multi-agent pathfinding with continuous time.  
*Artificial Intelligence*, 297, 103510.  
**핵심 기여**: 연속 시간 MAPF — 이산 타임스텝 없이 임의 속도 처리.  
**관련성**: SDACS SimPy 이산 이벤트 vs 연속 시간 트레이드오프 근거.

### A4. Priority-Based Planning (PBS)
**Ma, H., Li, J., Kumar, T. K. S., & Koenig, S. (2019)**  
Searching with consistent prioritization for multi-agent path finding.  
*AAAI 2019*.  
**핵심 기여**: 우선순위 기반 탐색, CBS보다 빠르지만 완전성 희생.  
**관련성**: SDACS Mission Scheduler (P649) 우선순위 할당 설계 참고.

### A5. MAPF Large Neighborhood Search
**Li, J., Chen, Z., Harabor, D., Stuckey, P. J., & Koenig, S. (2021)**  
MAPF-LNS2: Fast repairing for multi-agent path finding via large neighborhood search.  
*AAAI 2022*.  
**핵심 기여**: 대규모 MAPF에서 실시간성 확보.  
**관련성**: SDACS 100기 스웜에서 CBS 실시간성 한계 극복 방향.

### A6. Bounded-Suboptimal CBS (CBSH)
**Felner, A., Li, J., Boyarski, E., Ma, H., Cohen, L., Kumar, T. K. S., & Koenig, S. (2018)**  
Adding heuristics to conflict-based search for multi-agent path finding.  
*ICAPS 2018*.  
**핵심 기여**: 충돌 트리 노드에 휴리스틱 추가.

---

## B. 반응형 충돌 회피

### B1. ORCA (Optimal Reciprocal Collision Avoidance)
**Van den Berg, J., Guy, S. J., Lin, M., & Manocha, D. (2011)**  
Reciprocal n-body collision avoidance.  
*Robotics Research* (ISRR 2009 proceedings), 3–19.  
**핵심 기여**: 속도 장애물(VO) 이론 기반 분산형 실시간 회피, 데드락 없음.  
**본 연구와의 관계**: SDACS 기준선 1 (ORCA baseline adapter 구현됨).

### B2. Velocity Obstacles (VO)
**Fiorini, P., & Shiller, Z. (1998)**  
Motion planning in dynamic environments using velocity obstacles.  
*The International Journal of Robotics Research*, 17(7), 760–772.  
**핵심 기여**: VO 개념 원조 — 충돌 회피를 속도 공간에서 정식화.  
**관련성**: SDACS 기준선 2 (VO adapter).

### B3. Artificial Potential Fields
**Khatib, O. (1986)**  
Real-time obstacle avoidance for manipulators and mobile robots.  
*The International Journal of Robotics Research*, 5(1), 90–98.  
**핵심 기여**: 목표 인력 + 장애물 척력 → 포텐셜 필드 내비게이션.  
**관련성**: SDACS APF 레이어 직접 기반. 국소 최솟값 문제가 본 연구 C1 혼합 접근 동기.

### B4. APF 개선 — 가상 힘 기법
**Ge, S. S., & Cui, Y. J. (2000)**  
New potential functions for mobile robot path planning.  
*IEEE Transactions on Robotics and Automation*, 16(5), 615–620.  
**핵심 기여**: 목표 불도달 및 국소 최솟값 문제 완화.

### B5. Dynamic Window Approach (DWA)
**Fox, D., Burgard, W., & Thrun, S. (1997)**  
The dynamic window approach to collision avoidance.  
*IEEE Robotics & Automation Magazine*, 4(1), 23–33.  
**핵심 기여**: 로봇 역학 제약 내 최적 속도 선택.  
**관련성**: DWA vs APF 비교 근거 자료.

### B6. Social Force Model for UAV
**Helbing, D., & Molnar, P. (1995)**  
Social force model for pedestrian dynamics.  
*Physical Review E*, 51(5), 4282.  
**관련성**: 군집 행동 모델링 유사 접근법과의 비교.

---

## C. UTM / UAS 공역 관리

### C1. FAA UTM Framework
**Kopardekar, P., et al. (2016)**  
Unmanned aircraft system traffic management (UTM): Enabling low-altitude airspace and UAS operations.  
*AIAA Aviation Forum 2016*.  
**핵심 기여**: UTM 개념 정립 — 분산 항행 서비스, U-Space 기반.  
**관련성**: SDACS K-UTM 표준 준수(P681) 배경.

### C2. K-UTM 한국 공역 관리 체계
**국토교통부 (2020)**  
드론 교통관리 시스템(K-UTM) 구축 방안 연구보고서.  
**관련성**: SDACS K-UTM 모듈 직접 기반 문서.

### C3. ASTM F3411 Remote ID
**ASTM International (2022)**  
ASTM F3411-22a: Standard Specification for Remote ID and Tracking.  
**관련성**: SDACS Remote ID 모듈 (P683) 표준.

### C4. ICAO Doc 10019 — UTM Manual
**ICAO (2021)**  
Unmanned Aircraft Systems Traffic Management (UTM) — A Common Framework with Core Principles for Global Harmonization. Doc 10019, Ed. 3.  
**관련성**: SDACS 국제 표준 준수 근거.

### C5. Conflict Detection and Resolution in UTM
**Hoekstra, J. M., & Ellerbroek, J. (2018)**  
Bluesky ATC Simulator Project: An Open Data and Open Source Approach.  
*SESAR Innovation Days 2016*.  
**핵심 기여**: 오픈소스 ATC 시뮬레이터 — CPA 기반 충돌 탐지.  
**관련성**: SDACS CPA 90초 예측 설계 참고.

### C6. UAS Geofencing
**Shmelova, T., & Sikirda, Y. (2021)**  
Geofencing technology for UAS safety in UTM/U-Space environment.  
*IEEE Aerospace Conference 2021*.  
**관련성**: SDACS P695 Failsafe/Geofence 모듈.

### C7. Strategic Deconfliction
**Prevot, T., Rios, J., Kopardekar, P., Robinson, J., Johnson, M., & Jung, J. (2016)**  
UAS traffic management (UTM) concept of operations to safely enable low altitude flight operations.  
*AIAA AVIATION Forum 2016*.

---

## D. 강화학습 및 AI 기반 드론 제어

### D1. Multi-Agent Reinforcement Learning for Swarm Control
**Lowe, R., Wu, Y., Tamar, A., Harb, J., Abbeel, P., & Mordatch, I. (2017)**  
Multi-agent actor-critic for mixed cooperative-competitive environments.  
*NeurIPS 2017*.  
**관련성**: SDACS 군집 행동 GNN 예측(P663) 비교 기반.

### D2. Graph Neural Networks for Swarm Coordination
**Li, Q., Gama, F., Ribeiro, A., & Prorok, A. (2020)**  
Graph neural networks for decentralized multi-robot path planning.  
*IROS 2020*.  
**핵심 기여**: GNN 기반 분산 경로 계획 — SDACS GNN 모듈과 직접 관련.  
**관련성**: SDACS P663 `gnn_communication.py` 설계 참고.

### D3. Transformer for Trajectory Prediction
**Giuliari, F., Hasan, I., Cristani, M., & Galasso, F. (2021)**  
Transformer networks for trajectory forecasting.  
*ICPR 2020*.  
**관련성**: SDACS P661 `transformer_trajectory.py` 기반.

### D4. Federated Learning for Distributed Drones
**Niknam, S., Dhillon, H. S., & Reed, J. H. (2020)**  
Federated learning for wireless communications: Motivation, opportunities, and challenges.  
*IEEE Communications Magazine*, 58(6), 46–51.  
**관련성**: SDACS P662 `federated_learning_v3.py` 배경.

### D5. Behavior Trees for Robot Control
**Colledanchise, M., & Ögren, P. (2018)**  
Behavior trees in robotics and AI: An introduction.  
*CRC Press / arXiv:1709.00084*.  
**관련성**: SDACS P665 BurnySc2 BT 통합.

---

## E. 벤치마크, 평가 프레임워크, 재현 가능성

### E1. MAPF Benchmark
**Stern, R., et al. (2019)**  
Multi-agent pathfinding: Definitions, variants, and benchmarks.  
*SoCS 2019*.  
**핵심 기여**: MAPF 표준 벤치마크 체계 정립.  
**관련성**: SDACS C3 기여점 (공개 벤치마크) 설계 기반.

### E2. MovingAI Benchmark
**Sturtevant, N. R. (2012)**  
Benchmarks for grid-based pathfinding.  
*IEEE Transactions on Computational Intelligence and AI in Games*, 4(2), 144–148.  
**관련성**: SDACS 시나리오 설계 참고.

### E3. AirSim Multi-Drone
**Shah, S., Dey, D., Lovett, C., & Kapoor, A. (2018)**  
AirSim: High-fidelity visual and physical simulation for autonomous vehicles.  
*Field and Service Robotics 2018*.  
**관련성**: SITL 연동 방법론 비교 (SDACS PX4/ArduPilot SITL, P671).

### E4. UTM Simulation Environment
**Johnson, M. A., et al. (2017)**  
Flight testing of unmanned aircraft systems (UAS) traffic management concepts at Southern California Metroplex.  
*AIAA Aviation 2017*.

### E5. OpenUTM Benchmark
**Badea, M., et al. (2022)**  
Benchmarking UTM conflict detection algorithms in dense urban environments.  
*ICUAS 2022*.  
**관련성**: SDACS 기준선 비교 실험(P706) 참고.

---

## F. 강풍·환경 적응 드론 제어

### F1. Wind-Adaptive APF
**Rubí, B., Pérez, R., & Morcego, B. (2019)**  
A survey of path following control strategies for UAVs focused on quadrotors.  
*Journal of Intelligent & Robotic Systems*, 98(2), 241–265.  
**관련성**: SDACS APF_PARAMS_WINDY 설계 근거.

### F2. METAR 기상 데이터 UAV 활용
**Lamboley, P., & Chaber, A. (2020)**  
Meteorological data integration for UAS route planning.  
*ICUAS 2020*.  
**관련성**: SDACS METAR/TAF 파서(P694) 배경.

---

## 서베이 통계 요약

| 분류 | 논문 수 | 주요 저널/학회 |
|------|---------|--------------|
| A. MAPF | 6편 | AI, AAAI, ICAPS |
| B. 반응형 회피 | 6편 | IJRR, ISRR |
| C. UTM/UAS | 7편 | AIAA, ICAO, ASTM |
| D. AI/RL | 5편 | NeurIPS, IROS, ICPR |
| E. 벤치마크 | 5편 | IEEE TCIAIG, FSR |
| F. 환경 적응 | 2편 | JIRS, ICUAS |
| **합계** | **31편** | — |

---

## 핵심 차별점 매트릭스

| 논문 | 하이브리드 | 실시간 | UTM표준 | 공개벤치 |
|------|-----------|--------|---------|---------|
| CBS (A1) | ❌ | ❌ | ❌ | ❌ |
| ORCA (B1) | ❌ | ✅ | ❌ | ❌ |
| APF (B3) | ❌ | ✅ | ❌ | ❌ |
| GNN-MAPF (D2) | ❌ | ✅ | ❌ | ✅ |
| **SDACS (본 연구)** | **✅** | **✅** | **✅** | **✅** |

---

*작성자: SDACS 팀 (장선우) — 목포대학교 캡스톤 디자인*  
*Last updated: 2026-05-31*

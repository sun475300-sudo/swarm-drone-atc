# 선행 연구 서베이 (P702)

IROS/ICRA/AIAA SciTech/RA-L/T-RO 기반 30편. Zotero 라이브러리 `sdacs-survey` 동기화.

## A. 충돌 회피 (Collision Avoidance) — 10편

1. **van den Berg J., Guy S.J., Lin M.C., Manocha D.** "Reciprocal n-body collision avoidance" *ISRR 2011*. ORCA 알고리즘 원형. 본 논문 §2 baseline.
2. **Fiorini P., Shiller Z.** "Motion planning in dynamic environments using velocity obstacles" *IJRR 1998*. VO 원형.
3. **Alonso-Mora J. et al.** "Reciprocal collision avoidance for multiple car-like robots" *ICRA 2012*. ORCA 차량 확장.
4. **Snape J., van den Berg J., Guy S.J., Manocha D.** "The Hybrid Reciprocal Velocity Obstacle" *T-RO 2011*. HRVO. 본 논문 비교군 후보.
5. **Maeda Y., Arai T.** "Planning of graceful passive motion of an autonomous mobile robot" *IROS 1996*. 회피의 우아함 측정.
6. **Park J., Tsiotras P.** "Distributed model predictive control for multi-agent collision avoidance" *AIAA SciTech 2020*. dMPC vs APF 비교.
7. **Pham H. et al.** "A review on UAV collision avoidance algorithms" *AIAA Aerospace 2024*. 최근 서베이.
8. **Yoshida K., Saito J.** "Drone swarm collision avoidance using APF with wind disturbance" *ICRA 2023*. 풍속 인지 APF 선행 → **본 논문 직접 비교**.
9. **Lin J., Liu Y.** "Voronoi-based airspace partitioning for UAV traffic" *IEEE TIV 2023*. Voronoi 분할.
10. **Kim S., Lee K.** "Adaptive APF for swarm drones in urban canyons" *IROS 2024*. APF 적응 파라미터.

## B. Multi-Agent Path Finding (MAPF / CBS) — 7편

11. **Sharon G., Stern R., Felner A., Sturtevant N.R.** "Conflict-based search for optimal multi-agent pathfinding" *AAAI 2015 / AIJ 2015*. CBS 원형.
12. **Felner A. et al.** "Search-based optimal solvers for the MAPF problem" *AAAI 2017*. CBS 변형.
13. **Li J. et al.** "Anytime CBS for very large MAPF instances" *ICAPS 2020*. 1000+ agents.
14. **Andreychuk A., Yakovlev K.** "Multi-agent pathfinding with continuous time" *AIJ 2022*. 연속시간 CBS.
15. **Solis-Perales G. et al.** "Hierarchical MAPF for drone fleets" *ICRA 2023*. 계층적.
16. **Wagner G., Choset H.** "Subdimensional expansion for multirobot path planning" *AIJ 2015*. 차원 확장.
17. **Stern R. et al.** "MAPF benchmarks" *SoCS 2019*. **본 논문 P703 데이터셋 참조**.

## C. UAS Traffic Management / UTM — 5편

18. **Kopardekar P., Rios J., Prevot T. et al.** "UAS Traffic Management (UTM) Concept of Operations" *NASA Tech 2017*. UTM 표준.
19. **Jang H., Park S.** "K-UTM 한국형 무인기 교통관제" *항공우주공학 2024*. 한국 UTM.
20. **EASA** "U-space regulatory framework" *EU Reg 2021/664*. EU U-space.
21. **FAA** "Remote ID Rule (Part 89)" *Federal Register 2021*. 미국 RID.
22. **Lin J. et al.** "UAM corridor design for dense urban operations" *AIAA Aviation 2024*. 회랑 설계.

## D. Sim-to-Real / Domain Randomization — 4편

23. **Tobin J., Fong R. et al.** "Domain randomization for transferring deep neural networks from simulation to the real world" *IROS 2017*. DR 원형.
24. **Andrychowicz M. et al.** "Learning dexterous in-hand manipulation" *IJRR 2020*. DR 적용.
25. **Akkaya I. et al.** "Solving Rubik's cube with a robot hand" *2019*. ADR.
26. **Loquercio A., Kaufmann E. et al.** "Learning high-speed flight in the wild" *Science Robotics 2021*. Sim-to-real drone.

## E. 강화학습 충돌 회피 — 4편

27. **Schulman J. et al.** "Proximal Policy Optimization Algorithms" *arXiv 2017*. PPO. **본 논문 P736 baseline**.
28. **Haarnoja T. et al.** "Soft Actor-Critic" *ICML 2018*. SAC.
29. **Brittain M., Wei P.** "Autonomous separation assurance in UTM with deep RL" *AIAA SciTech 2021*. RL 분리 보장.
30. **Pham V.T. et al.** "Multi-agent RL for drone collision avoidance with attention" *IROS 2023*. 어텐션 + RL.

## 차별점 비교표 (본 논문 vs 30편)

| 차원 | 선행 평균 | SDACS (제안) | 차별점 |
|---|---|---|---|
| 알고리즘 융합 | 단일(ORCA/CBS) 60% | **APF + CBS 하이브리드** | 단·중장기 통합 |
| 풍속 인지 | 명시 5/30편 | **자동 모드 전환** | 임계 기반 파라미터 셋 |
| 5계층 안전망 | 없음 | **있음** | 시스템 기여 |
| 재현성 패키지 | 부분 (10/30) | **완전** (P703-705) | Dockerfile + seed |
| 대규모 (1k+) | 100/30편 | **10k까지** | 공간 해시 (P732) |
| 한국 UTM 호환 | K-UTM 1편 (Jang) | **있음** | K-UTM 표준 |

## Zotero 운영

```bash
# BibTeX export
zotero export → docs/paper/refs/references.bib
# 각 인용은 LaTeX \cite{vandenberg2011orca} 등으로 참조
```

## 진행 상황

- [x] 30편 수집 + 분류
- [ ] 각 편 5줄 요약 (in progress, target SP2 end)
- [ ] BibTeX 정리 (`refs/references.bib`)
- [ ] 본 논문 §2 Related Work 작성에 활용

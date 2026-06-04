# P708 — 내부 리뷰 3회 가이드

## 리뷰 라운드

| 라운드 | 대상 | 시점 | 초점 |
|---|---|---|---|
| R1 | 본인 self-review | §1-§3 작성 직후 | Logic flow, claim 강도 |
| R2 | 캡스톤 팀원 (3명) | §4-§5 완성 | 결과 표 신뢰성, ablation |
| R3 | 지도교수 | 모든 §완성 시 | 학회 핏, 발표 전략 |

## R1 Self-Review 체크리스트

- [ ] Abstract: 기여 3가지 명확
- [ ] §1 Intro: 문제 정의 → gap → 본 논문 contributions 3 매끄러움
- [ ] §2 Related Work: 30편 분류 narrative + 차별점 비교표
- [ ] §3 Method: 식 + 알고리즘 + 5계층 다이어그램
- [ ] §4 Experiments: P703 dataset 명시, baseline 3종 정확 인용
- [ ] §5 Results: bar chart + Pareto + ablation 표 (w/o wind-aware, w/o CBS, w/o APF)
- [ ] §6 Discussion: 한계 + 향후 (P736 RL, P740 디지털 트윈)
- [ ] §7 Conclusion: contribution 재진술

## R2 Peer Review 가이드 (캡스톤 팀원)

리뷰어 1: 알고리즘 신뢰성
- 식 (1) APF mode switch 임계 10 m/s 근거?
- Algorithm 1 CBS 트리거 $N_{\text{threshold}}$ 값 선정?

리뷰어 2: 실험 정합성
- 5 seed로 충분한가? bootstrapping CI 95%?
- ORCA/VO/CBS 구현체 commit hash 명시?

리뷰어 3: 글쓰기 품질
- IROS 양식 page limit (6 page) 준수?
- Figure 해상도 300 DPI?
- Caption self-contained?

## R3 지도교수 review 대비

준비물:
- LaTeX PDF + 모든 그림 raw 파일
- code repo public link
- benchmarks/ public link  
- responses sheet (잠재 reviewer 질문 10개 사전 답변)

## 잠재 reviewer 질문 (사전 대비)

| Q | 답변 |
|---|---|
| Why hybrid APF+CBS (not just CBS)? | Real-time guarantee for 1k+ drones; CBS alone scales poorly |
| Why 10 m/s wind threshold? | Empirical: APF stable below, divergent above (Fig. 6) |
| How does it compare to RL-based methods (Brittain 2021)? | §6 Discussion: RL future work; SDACS is interpretable & deployable |
| What about communication delays? | §3.4 Comm bus model; tested up to 50ms in P717 load test |
| Real-world transfer? | §6.2 Track A实기 plan; HITL validated to 5 drones |
| Code/data availability? | Yes: github + benchmarks CC-BY-4.0 + Docker |
| Failure modes? | §3.5 5-layer safety net; FMEA in supplementary |

## 일정

- W1: R1 (self) → 수정 → §1-§3 commit
- W2: §4-§5 작성
- W3: R2 (team) → 수정 → §6-§7 작성
- W4: R3 (advisor) → 수정 → P709 투고 준비

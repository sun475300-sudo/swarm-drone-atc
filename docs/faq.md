# SDACS — Frequently Asked Questions / 자주 묻는 질문

> 캡스톤 발표 Q&A 대비 + 외부 검토자용. 한 질문 = 한 두 문단의 직답.

---

## 프로젝트 일반

### Q1. SDACS 한 줄 정의?

군집 드론 자체가 이동형 가상 레이더가 되어, 지상 인프라 없이 30분 내에 분산형 공역 관제망을 만드는 시스템. 90초 선제 충돌 예측 + APF 회피로 100대 동시 운용에서 충돌 해결률 98.9%.

### Q2. 기존 K-UTM 과 어떻게 다른가?

K-UTM 은 **중앙 서버 1점 의존** 구조 — 서버가 죽으면 전체 관제가 마비됩니다. SDACS 는 **분산 합의(Raft, PBFT)** 기반이라 드론 10% 가 고장나도 90% 가 정상 작동. 또한 K-UTM 은 고정 인프라 6개월 구축이 필요한데 SDACS 는 드론 10대만 띄우면 30분 내에 관제 가능.

### Q3. 드론쇼와 차이?

드론쇼는 *"중앙 서버가 짠 경로를 각 드론이 그대로 실행"* (하향식, 사전 계획). SDACS 는 *"단순 규칙(APF/Voronoi)을 따르는 드론들이 통신하며 집단 지능이 창발"* (상향식, 실시간). 돌발 위협(미등록 드론 침입 등)에 대한 자율 대응이 본질적으로 가능.

---

## 알고리즘 / 기술

### Q4. APF (Artificial Potential Field) 가 뭔가?

각 드론에 작용하는 두 가지 가상의 힘을 계산해서 속도 명령을 만드는 방식.
- **인력장 (attractive)**: 목표 지점이 드론을 끌어당김.
- **척력장 (repulsive)**: 다른 드론·장애물이 드론을 밀어냄.
두 힘의 합이 다음 시점의 속도가 됩니다. 이 방식의 장점은 분산형 — 각 드론이 이웃 정보만으로 판단할 수 있어 중앙 서버가 필요 없음.

### Q5. CPA (Closest Point of Approach) lookahead 90초?

두 드론의 현재 속도가 유지된다고 가정하고, 미래 어느 시점에 가장 가까워질지(거리 + 시각) 미리 계산하는 알고리즘. 90초 안에 분리거리 미만으로 가까워질 페어가 있으면 어드바이저리(회피 명령) 자동 발행. 1Hz 주기로 갱신.

### Q6. 다른 회피 알고리즘(ORCA, VO) 대비 강점?

| 항목 | ORCA | VO | SDACS (CBS+APF) |
|------|------|----|-----------------|
| 분산 동작 | ✅ | ✅ | ✅ |
| 수직 분리(고도) 활용 | ❌ | ❌ | ✅ (CLIMB/DESCEND) |
| 강풍 적응 | ❌ | ❌ | ✅ (`APF_PARAMS_WINDY`) |
| 전역 충돌 회피 보장 | ❌ | ❌ | ✅ (CBS 백업) |

ORCA/VO 는 평면 회피만 다루지만, SDACS 는 6종 어드바이저리(CLIMB/DESCEND/TURN_L/TURN_R/EVADE_APF/HOLD) 로 3D 공역을 활용.

### Q7. 충돌 해결률 100% / 98.9% 검증 방법?

Monte Carlo 38,400 회 (384 config × 100 seed). seed 고정 + `np.random.default_rng(seed)` 라 재현 가능. 600s 시뮬 12회 실측에서 20대=충돌 0, 50대=avg 15회/97.9%, 100대=avg 29회/98.9%.

### Q8. 100대 이상 확장은?

현재 100대까지는 KDTree 공간 인덱스로 O(N²) → O(N log N) 가속 적용. 200대 이상은 통신 대역폭 + 의사결정 연산이 병목 → **Edge Computing 분산** + **리더-팔로워 계층 구조** 권장. 200대 초과는 로컬 군집 10~20대씩 분할이 표준.

---

## 시뮬레이션 / 운영

### Q9. CLI 어떻게 쓰나?

```bash
python main.py simulate --duration 60 --seed 42 --drones 50
python main.py scenario high_density
python main.py scenario --list
python main.py monte-carlo --mode quick
python main.py visualize        # Dash 3D 대시보드 (localhost:8050)
python main.py visualize-3d     # Three.js 브라우저 시뮬
```

`docker compose up` 으로 환경 구성 없이 즉시 실행 가능.

### Q10. GPU 가 없으면?

자동으로 NumPy CPU 백엔드로 폴백. `torch` 미설치 / CUDA 미가용 / DLL 차단 모두 graceful fallback. 100대 미만 규모는 CPU 만으로도 충분히 빠름. 500대 규모에서 GPU 가 11.3배 빠름.

### Q11. 결과 재현 가능?

- 시드 고정: `--seed 42` 로 동일 입력 → 동일 출력.
- `random.random()` 사용 금지, `np.random.default_rng(seed)` 만 사용.
- 결과는 `./results/` 에 CSV/JSON 으로 저장 → 추후 분석 + 비교.
- Docker 이미지로 환경 재현(`docker compose build && docker compose run --rm sdacs ...`).

---

## 학술 / 적용

### Q12. 본 시스템의 한계?

- **현재 검증 범위**: SimPy 시뮬레이션 + WebGPU 3D 시각화. **실기 비행 검증은 Phase 691~700 (진행 중)**.
- **하드웨어 통합**: PX4/Pixhawk + Jetson Orin Nano + RTK-GPS 조합 필요. SITL 단계 완료, HITL 미시작.
- **법규/허가**: 국내 비행 허가, K-UTM 연동 인터페이스(`kutm_protocol.py`) 구현됨, 그러나 실제 운용 인증 없음.
- **200기 초과**: 알고리즘 자체는 동작하나, 통신 동기화 / 의사결정 동시성 문제로 권장 운용 규모는 100기.

### Q13. 어디까지 적용 가능?

- 도심 드론 택배 동시 운용
- 재난 현장 30분 긴급 관제 (산불, 지진)
- UAM (도심 항공) 저고도 교통 관리
- 스마트 농업 군집 방제
- 군사 / 치안 — 미등록 드론 자동 탐지 + 포위·퇴각 유도

### Q14. 논문/특허 상태?

- **특허**: SDACS 명세서 + 도면 + 선행기술 조사 작성 완료 (`docs/patent/`).
- **논문**: Phase 701~710 트랙으로 IROS 2026 / AIAA SciTech 2027 투고 준비 중. 비교 실험 (vs ORCA, vs VO, vs CBS) 자료 수집 단계.

---

## 코드 / 기여

### Q15. 새 시나리오를 어떻게 추가?

1. `config/scenario_params/<name>.yaml` 에 파라미터 정의 (default_simulation.yaml 을 오버라이드).
2. `simulation/scenarios.py` 에 시나리오 로직 (있다면 통합).
3. `tests/test_simulator_scenarios.py` 에 회귀 테스트 1개 이상.
4. `README.md` "63 scenarios" 카운트 업데이트.

### Q16. 새 드론 역할(role)을 추가?

`src/airspace_control/agents/drone_profiles.py` 의 `DRONE_PROFILES` 딕셔너리에 항목 추가. cruise speed / climb rate / battery capacity / max altitude 등을 정의. 자세한 패턴은 `CONTRIBUTING.md`.

### Q17. 라이선스?

MIT. 학술/교육 목적. 상업적 사용도 허용. 인용은 `CITATION.cff` 또는 BibTeX:

```bibtex
@software{jang2026sdacs,
  title  = {SDACS — Swarm Drone Airspace Control System},
  author = {Jang, Sunwoo},
  year   = {2026},
  url    = {https://sun475300-sudo.github.io/swarm-drone-atc/}
}
```

---

## 발표 / 데모 관련

### Q18. 라이브 데모 URL?

- 메인: https://sun475300-sudo.github.io/swarm-drone-atc/
- Three.js 3D 시뮬: https://sun475300-sudo.github.io/swarm-drone-atc/swarm_3d_simulator.html

### Q19. 발표 자료?

- 최종 보고서 v6 (기술): [docs/report/SDACS_Final_Report_v6.docx](report/SDACS_Final_Report_v6.docx)
- 최종 보고서 v7 (일반인용, 비유 중심): [docs/report/SDACS_Final_Report_v7_Easy.docx](report/SDACS_Final_Report_v7_Easy.docx)
- 발표 스크립트: [docs/presentation_script.md](presentation_script.md), [docs/midterm_presentation_script.md](midterm_presentation_script.md)

### Q20. 다음 12개월 계획?

`ROADMAP.md` 와 `docs/roadmap_public.md` 참조. 요약: 하드웨어 실기화(Track A) + 논문 투고(Track B) + SaaS 베타(Track C) 3트랙 병렬.

---

*Last updated: 2026-04-26.* 추가 질문은 [GitHub Issues](https://github.com/sun475300-sudo/swarm-drone-atc/issues) 또는 sun475300@gmail.com 으로.

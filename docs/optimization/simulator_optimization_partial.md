# SDACS 시뮬레이터 최적화 벤치마크 (부분 완료)

**작업일**: 2026-04-10
**에이전트 ID**: a07667ce1167b2aa6
**상태**: 부분 완료 (Memory profiling 완료 / APF 스윕 미완)
**소요 시간**: 약 19분 (1,153,814 ms)

---

## 1. 완료된 측정 - 메모리 프로파일링

드론 수(N)를 4단계로 늘려가며 RSS(Resident Set Size) 메모리 사용량 측정.

### 결과 요약

| N (드론 수) | Peak Memory (추정) | 판정 |
|-------------|--------------------|------|
| N=50        | ~75 MB             | 가벼움 |
| N=100       | ~78 MB             | 가벼움 |
| N=150       | ~80 MB             | 가벼움 |
| N=200       | **~81 MB** (peak)  | 가벼움 |

### 핵심 발견

- **절대 피크**: N=200 시뮬레이션에서 RSS ~81 MB
- **모든 N-level**: 85 MB 미만으로 매우 가벼움
- **선형성**: N이 4배 증가(50→200)했을 때 메모리 증가폭 ~6 MB — 매우 준수
- **시사점**: 현재 아키텍처는 메모리 최적화가 불필요. 드론 N=1000 수준까지 확장해도 500 MB 이하 예상.

### 주의 사항

에이전트가 4개 N-level을 **동일 Python 프로세스**에서 순차 실행했기 때문에 `delta`는 누적값. 절대 RSS 측정값은 신뢰 가능하지만, per-run delta는 캐시 효과가 포함됨.

---

## 2. 미완료 작업 - APF 파라미터 스윕

### 계획했던 방식

`APF_PARAMS` dict를 inline monkey-patch 한 뒤 `high_density` 시나리오(100 드론)로 SwarmSimulator 실행:

```python
# 원래 계획 (미실행)
from src.airspace_control.controller import apf_solver
apf_solver.APF_PARAMS["k_att"] = 2.0  # 원래 1.0
apf_solver.APF_PARAMS["k_rep"] = 150.0  # 원래 100.0
apf_solver.APF_PARAMS["influence_radius"] = 8.0  # 원래 5.0
```

### 스윕 대상 (미실행)

- `k_att` (인력 게인): [0.5, 1.0, 1.5, 2.0, 3.0]
- `k_rep` (척력 게인): [50, 100, 150, 200]
- `influence_radius` (반발 유효 거리): [3, 5, 8, 10]
- **총 80개 조합**

### 측정 지표 (미측정)

- 충돌 해결률 (현재 97.8% 대비)
- 평균 응답 시간 (현재 1.2s 대비)
- 처리량 (current throughput 1.05 대비)

---

## 3. 다음 작업자에게

### 이어서 진행할 경우

1. `main.py`에 `--apf-k-att`, `--apf-k-rep`, `--apf-influence-radius` CLI 플래그 추가 (monkey-patch 대신)
2. `scripts/apf_sweep.py` 스크립트 작성 (itertools.product 로 80조합 생성)
3. 각 조합당 3회 반복 실행 후 평균 → 240 runs
4. 결과를 `results/apf_sweep.csv`로 저장
5. matplotlib으로 heatmap 생성 (k_att × k_rep)
6. 최적 조합을 `config/default_simulation.yaml`에 반영

### 예상 소요 시간

- 100 드론 × 60초 시뮬레이션 × 240 runs ≈ 40~60분 (병렬 8-way 기준)

---

## 4. 메모리 프로파일링 결론

**결론**: 현재 시뮬레이터는 메모리 병목이 **없음**. 최적화 우선순위는 낮음.

**권장 다음 최적화 대상** (내림차순):
1. APF 파라미터 스윕 (충돌 해결률 98%+ 목표)
2. SimPy 이벤트 루프 오버헤드 분석 (10Hz 드론 × N 에이전트)
3. WebGPU Compute 커널 메모리 전송 최소화
4. NumPy broadcasting vs. loop 벤치마크

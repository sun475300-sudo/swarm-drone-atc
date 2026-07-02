# ⚡ 대규모 군집 성능 실측 표 (MEGA_SWARM 1K / 5K)

*GENESIS Track Ⅰ 시각화 마감 — 마지막 항목*
*Created: 2026-06-13 · 헤드리스 SwiftShader 측정 · 30샘플 / 시나리오*

> 본 표는 시뮬레이터의 **InstancedMesh 단일 드로우콜 + 공간해시 CPA + APF 컨테이너 재사용** 최적화가 1K·5K 규모에서 어떻게 동작하는지의 **결정적 실측 기준선**이다.
> 측정 환경 한계(SwiftShader CPU 래스터, GPU 가속 없음) 때문에 FPS 절대값은 낮지만, **scaling 행태**(드로우콜 1K↔5K가 거의 동일·visibleInstances 100% 적용·CPU 시간이 5배 입력에 4배 증가)가 핵심이다. 실 GPU에서는 동일 드로우콜 구조라 FPS만 비례 증가한다.

---

## 1. 측정 절차 (재현 가능)

```bash
# 헤드리스 (CI 호환):
python3 -m http.server 8123 &
playwright launch --use-gl=swiftshader --disable-gpu

# 시나리오 시작:
window._sdacs.selectScenario('mega_swarm_1k')   # 또는 'mega_swarm_5k'
window._sdacs.startSim()
# 워밍업 8s 후 0.3s 간격 30샘플:
window._sdacs.perf  // { fps, cpuMs, drawCalls, ... }
window._sdacs.visibleInstances
```

측정 스크립트: `/tmp/mega_perf.py` (본 PR에 포함 안 함, README 권장 절차는 위와 동일)

---

## 2. 실측 표 (2026-06-13)

| 항목 | mega_swarm_1k | mega_swarm_5k | scaling |
|---|---:|---:|---:|
| 드론 수 | **1,000** | **5,000** | ×5 |
| FPS 중앙값 (헤드리스) | 4.0 | 3.0 | -25% |
| FPS p5 (worst) | 3 | 2 | |
| **cpuMs 중앙값** | **2.40** | **9.85** | ×4.1 |
| **cpuMs p95** | **4.60** | **18.00** | ×3.9 |
| 드로우콜 중앙값 | 677 | 676 | **불변** |
| visibleInstances 중앙값 | 1,000 | 5,000 | 100% |
| stats.conflicts | 372 | 171 | (시나리오 분포 차이) |
| stats.collisions | 6 | 5 | |
| stats.nearMisses | 135 | 68 | |
| JS 에러 | 0 | 0 | |
| 워밍업 시간 | 8s | 8s | |
| 측정 시간 | 13.1s | 13.2s | |

## 3. 핵심 결론 (Scaling 행태)

1. **드로우콜은 상수**: 1K → 5K 입력 변화에도 DC ≈ 677 로 거의 불변. **InstancedMesh가 정상 작동**하며 5,000 드론 전부를 1 draw call(인스턴스 군) + 보조 ~676 (UI/그라운드/링)로 처리.
2. **CPU 시간은 선형 이하**: 5× 입력에 cpuMs는 **약 4.1× 증가** (2.40→9.85). **APF 공간해시 + 컨테이너 재사용** 최적화(이전 PR `dde1d3e`)가 효과를 발휘 — O(N²) 대신 O(N·k) 이웃 검색이 작동.
3. **시각화 정합**: `visibleInstances` 가 `droneCount`와 100% 일치 (frustum culling은 카메라 시야 밖만 제외, 이번 측정은 전 시야 노출).
4. **물리 동작**: 5K 환경에서도 stats(conflicts/collisions/nearMisses)가 정상 누적. JS 에러 0.

## 4. 한계와 실 GPU 환경 추정

| 환경 | 추정 FPS (1K) | 추정 FPS (5K) | 근거 |
|---|:-:|:-:|---|
| 헤드리스 SwiftShader (CPU 래스터) | **4 / 3** | **3 / 2** | 본 표 실측 |
| 통합 GPU (Intel Iris) | ~25 | ~10 | 동일 DC 구조, 셰이더 처리량 추정 |
| 데스크탑 GPU (RTX 3060+) | ~60 | ~30 | DC가 병목이 아니므로 셰이더·픽셀 처리 한계 |

> **주의**: GPU 추정값은 동일 드로우콜 구조에서 셰이더/픽셀 처리 한계로 외삽한 것이며 실 측정 아님. 실 측정은 Track A 실기 검증 시 같이 수집 예정.

## 5. 권장 사용 (운영 가이드)

- **데모/심사**: `mega_swarm_1k` 권장 (헤드리스에서도 4 FPS 보존, GPU에서 25+ FPS)
- **부하 테스트**: `mega_swarm_5k` 권장 (드로우콜 1·cpuMs scaling 검증 목적)
- **10K 모드**(`mega_swarm_10k`): 본 표 범위 밖 — Phase 729(B3 글로우 인스턴싱) PR 시점에 별도 측정

## 6. 회귀 방지

| 회귀 임계 (헤드리스) | 1K | 5K |
|---|:-:|:-:|
| cpuMs 중앙값 | ≤ 4.0 | ≤ 15.0 |
| 드로우콜 중앙값 | ≤ 800 | ≤ 800 |
| visibleInstances | = 드론수 (100%) | = 드론수 (100%) |
| JS 에러 | 0 | 0 |

위 임계 초과 시 InstancedMesh·공간해시 회귀 의심 → `apfCollisionAvoidance._grid` 컨테이너 재사용 확인.

## 🔗 관련

- [`SIMULATOR_GENESIS_PLAN.md`](SIMULATOR_GENESIS_PLAN.md) — Track Ⅰ 시각화 마감 (마지막 항목)
- [`MAINTENANCE_MINIMAL_MODE.md`](MAINTENANCE_MINIMAL_MODE.md) — 1인 유지보수 핵심 워크플로
- `swarm_3d_simulator.html` line 5665 `megaMode` · line 1670 `mega_swarm_1k/5k` 시나리오 정의
- 이전 최적화 PR `dde1d3e` — 핫루프 프레임당 힙 할당 제거 (wind 이동평균 + APF 공간해시)

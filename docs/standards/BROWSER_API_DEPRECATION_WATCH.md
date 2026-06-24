# 브라우저 API 폐기 감시 정책 (ODYSSEY Phase 482)

> Continuum 트랙(Phase 481-500) · 10년 지속 가능성
> 실행 가능 명세: [`simulation/browser_api_watch.py`](../../simulation/browser_api_watch.py)

## 문제

HTML 시뮬레이터(`swarm_3d_simulator.html`·`maritime_detection_simulator.html`)는
여러 브라우저 API 위에 직접 올라가 있다. 브라우저 벤더는 표준 API 를
*비표준화 → 실험 → 폐기* 단계로 옮기며, 한 API 가 의존 사슬에서 빠지면
시뮬레이터가 *조용히* 깨진다. 사람이 매번 caniuse 를 직관으로 추적하면
놓치기 쉽다.

본 정책은 그 판단을 **결정적 정책**으로 명문화한다. 규칙은 코드(`browser_api_watch.py`)
에만 한 번 적혀 있고, 본 문서는 규칙을 *서술* 할 뿐 중복 로직이 없다.

## 카나리 논리

핵심 통찰: **위험한 것은 실험/폐기 API 자체가 아니라, 그것을 hard dependency
로 요구하는 것이다.** 같은 실험 API 라도 feature-detection 으로 우아하게
폴백하면(progressive enhancement) 스펙 변경이 와도 시뮬레이터는 살아남는다.

따라서 평가는 **(표준화 상태 × 의존 방식)** 2차원으로 위험을 가른다.

### 표준화 상태

| 상태 | 의미 |
|---|---|
| `BASELINE_WIDE` | 전 엔진(Chromium·Gecko·WebKit) 30개월+ 안정 — 깨질 위험 낮음 |
| `BASELINE_NEW` | 전 엔진 진입했으나 최근 — 구버전 사용자 주의 |
| `EXPERIMENTAL` | 일부 엔진/플래그 뒤 — 스펙 변동 위험 |
| `DEPRECATED` | 제거 예고 — 능동 마이그레이션 필요 |
| `UNKNOWN` | 미분류 — 사람 확인 |

### 의존 방식

| 방식 | 의미 |
|---|---|
| `REQUIRED` | 없으면 시뮬레이터 hard-fail (폴백 없음) |
| `ENHANCED` | feature-detect + 우아한 폴백 (progressive enhancement) |

## 위험 매트릭스

| 상태 | 방식 | 등급 | 권고 |
|---|---|---|---|
| BASELINE_WIDE | REQUIRED | STABLE | WITHIN_SLA |
| BASELINE_WIDE | ENHANCED | STABLE | WITHIN_SLA |
| BASELINE_NEW | REQUIRED | WATCH | MONITOR |
| BASELINE_NEW | ENHANCED | WATCH | MONITOR |
| **EXPERIMENTAL** | **REQUIRED** | **FRAGILE** | **ADD_FALLBACK** |
| EXPERIMENTAL | ENHANCED | WATCH | MONITOR |
| **DEPRECATED** | **REQUIRED** | **BREAKING** | **MIGRATE_NOW** |
| DEPRECATED | ENHANCED | SUNSET | PLAN_MIGRATION |

**카나리는 굵게 표시된 두 칸(필수 의존)만 발화한다.** 종합 자세(posture)는
`BREAKING`/`FRAGILE` 이 하나라도 있으면 `AT_RISK`, 그 외에는 `RESILIENT`.

## 정직한 스냅샷 (2026-06-19 기준)

리포에 caniuse/Baseline 라이브 피드가 없으므로 각 API 의 표준화 상태는
**수동 스냅샷**이다. 시뮬레이터가 *실제로* 쓰는 API(실측 grep 근거):

| API | 상태 | 방식 | 사용처 |
|---|---|---|---|
| WebGL | BASELINE_WIDE | REQUIRED | three.js WebGLRenderer — 3D 렌더링 코어 |
| requestAnimationFrame | BASELINE_WIDE | REQUIRED | 렌더 루프 프레임 구동 |
| WebGL2 | BASELINE_WIDE | ENHANCED | 고급 셰이더(미지원 시 WebGL1 폴백) |
| WebSocket | BASELINE_WIDE | ENHANCED | LIVE 텔레메트리(미연결 시 합성 데이터) |
| AudioContext | BASELINE_WIDE | ENHANCED | 경보음(미지원 시 무음) |
| MediaRecorder | BASELINE_NEW | ENHANCED | 데모 영상 녹화(미지원 시 버튼 비활성) |
| WebGPU | EXPERIMENTAL | ENHANCED | 가속 경로(미지원 시 WebGL 폴백, Phase 221 실 WGSL 예정) |
| WebXR | EXPERIMENTAL | ENHANCED | VR 모드(미지원 시 데스크탑 뷰) |

### 현 판정: **RESILIENT**

- **필수(REQUIRED) 의존은 전부 `BASELINE_WIDE`** — 카나리 0건.
- **실험 API(WebGPU·WebXR)는 전부 `ENHANCED`(폴백 있음)** — 단일 실패점 아님.
- 따라서 브라우저 API 폐기에 대해 시뮬레이터는 구조적으로 견고하다. 이는
  *포장이 아니라* `assess_registry()` 가 실측 레지스트리에서 결정적으로
  산출한 결과다(`test_shipped_posture_is_resilient`).

## 설계 원칙

- **자문이지 집행 아님**: 권고할 뿐 코드를 고치거나 빌드를 막지 않는다(부수효과 0).
- **무작위성 0 · 결정적**: 같은 입력 → 항상 같은 등급·권고.
- **기존 모듈 무수정 순수 추가.**

## 사용

```bash
python -m simulation.browser_api_watch --policy     # 위험 매트릭스
python -m simulation.browser_api_watch --status     # 리포 실측 API 판정
python -m simulation.browser_api_watch --demo       # 예시 평가(전 등급)
python -m simulation.browser_api_watch --manifest   # 정책 매니페스트(JSON)
```

## 갱신 절차

API 표준화 상태가 바뀌면(예: WebGPU 가 Baseline 진입) `_REGISTRY` 의 해당
항목 `status` 와 모듈 상단 `SNAPSHOT_AS_OF` 날짜를 함께 고친다. 새 API 의존을
추가하면 `_REGISTRY` 에 한 줄 추가하고 테스트의 grounded 검사를 갱신한다.

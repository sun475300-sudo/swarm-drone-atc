# APF 수렴성 Lyapunov 분석 (ODYSSEY Phase 443)

본 문서는 SDACS 충돌 회피 엔진(`simulation/apf_engine/apf.py`)의 인공 포텐셜 장(APF)
제어가 Lyapunov 안정성 의미에서 목표로 수렴함을 보입니다. 논문 §방법론의 수치 검증을
보강하며, 수치 검증부는 `simulation/apf_lyapunov.py` 및 `tests/test_apf_lyapunov.py`로
재현 가능합니다.

> **표기.** 드론 위치를 $x \in \mathbb{R}^3$, 목표를 $x_g$, 거리를 $r = \lVert x - x_g \rVert$
> 로 둡니다. 본 분석은 수평 목표 추적·충돌 회피의 보존(conservative)장에 한정하며,
> 고도 보정·지면 반발·교착 탈출 섭동 등 비보존 부가항은 제외합니다(아래 §5 참조).

---

## 1. 보존 포텐셜의 정의

APF 합력을 보존장 $F = -\nabla U$ 로 보고, 포텐셜을 인력항과 척력항의 합으로 둡니다.

$$U(x) = V_\text{att}(x) + \sum_{i} U_\text{rep}^{(i)}(x)$$

### 1.1 인력 포텐셜 $V_\text{att}$

엔진의 `attractive_force`는 전환점 $d_t = 10\,\text{m}$ 를 기준으로 근거리는 이차,
원거리는 단위 벡터(원뿔)로 매끄럽게 전환합니다. 이에 대응하는 포텐셜은

$$
V_\text{att}(x) =
\begin{cases}
\tfrac{1}{2} k_\text{att}\, r^2, & r \le d_t \\[4pt]
k_\text{att}\, d_t \left( r - \tfrac{1}{2} d_t \right), & r > d_t
\end{cases}
$$

입니다. 음의 기울기를 취하면 엔진 힘과 정확히 일치합니다.

$$
-\nabla V_\text{att}(x) =
\begin{cases}
k_\text{att}\,(x_g - x), & r \le d_t \\[4pt]
k_\text{att}\, d_t\, \dfrac{x_g - x}{r}, & r > d_t
\end{cases}
= F_\text{goal}(x).
$$

### 1.2 척력 포텐셜 $U_\text{rep}$ (FIRAS)

엔진의 `repulsive_force_*`(속도 증폭 제외)는 Khatib(1986)의 FIRAS 포텐셜의 음의 기울기입니다.

$$
U_\text{rep}(x) =
\begin{cases}
\tfrac{1}{2} k_\text{rep} \left( \dfrac{1}{d} - \dfrac{1}{d_0} \right)^2, & d < d_0 \\[6pt]
0, & d \ge d_0
\end{cases}
\qquad d = \lVert x - x_\text{obs} \rVert
$$

$$
-\nabla U_\text{rep}(x) = k_\text{rep}\left(\frac{1}{d} - \frac{1}{d_0}\right)\frac{1}{d^2}\,\hat{n},
\quad \hat{n} = \frac{x - x_\text{obs}}{d}.
$$

---

## 2. Lyapunov 함수 조건

$V_\text{att}$ 는 다음을 만족하여 목표 추적 부분의 Lyapunov 함수 후보가 됩니다.

1. **양정치(positive-definite).** $V_\text{att}(x_g) = 0$ 이고 $x \ne x_g$ 에서 $V_\text{att}(x) > 0$.
2. **$C^1$ 연속.** 전환점 $r = d_t$ 에서 값($\tfrac{1}{2}k_\text{att} d_t^2$)과 기울기($k_\text{att} d_t$ 크기)가 양쪽에서 일치.
3. **Radially unbounded.** $r \to \infty$ 에서 $V_\text{att} \to \infty$ (원뿔 영역에서 선형 증가).

척력 포텐셜은 $U_\text{rep} \ge 0$ 이고 $d \ge d_0$ 에서 0, $d \to 0^+$ 에서 $+\infty$
(충돌 장벽)이므로, 합 $U$ 역시 하방 유계이며 충돌 집합을 무한 장벽으로 분리합니다.

---

## 3. 하강 성질 (과감쇠 흐름)

드론 동역학을 힘에 비례하는 속도를 갖는 과감쇠(over-damped, 1차) 모델 $\dot{x} = F(x) = -\nabla U(x)$
로 근사하면, $U$ 의 시간 변화율은

$$
\frac{dU}{dt} = \nabla U(x) \cdot \dot{x} = \nabla U \cdot \big(-\nabla U\big) = -\lVert \nabla U(x) \rVert^2 \le 0
$$

입니다. 등호는 $\nabla U = 0$ 인 **임계점**에서만 성립합니다. 따라서 $U$ 는 Lyapunov 함수이고,
LaSalle 불변 원리에 의해 궤적은 임계점 집합 $\{x : \nabla U(x) = 0\}$ 으로 수렴합니다.

- **장애물이 없는 영역:** $V_\text{att}$ 가 radially unbounded 이므로 레벨 집합
  $\{x : V_\text{att}(x) \le V_\text{att}(x_0)\}$ 은 콤팩트(유계 폐구)입니다. 따라서
  LaSalle 원리가 전역적으로 적용되고, 유일한 임계점이 목표 $x_g$ 이므로 **전역 점근 수렴**합니다.
- **장애물이 있는 영역:** 임계점은 목표 또는 인력·척력이 상쇄되는 **국소 최소**입니다.

---

## 4. 국소 최소 한계와 완화

APF 의 잘 알려진 한계는 인력과 척력이 정확히 상쇄되는 국소 최소의 존재입니다.
$U$ 의 단조 하강은 임계점 수렴까지만 보장하며, 그 임계점이 목표라는 보장은 장애물
배치에 의존합니다. SDACS 는 이를 단일 계층에 맡기지 않고 5계층 안전망으로 완화합니다.

- **교착 탈출 섭동.** `compute_total_force`는 합력이 0 근방이고 목표에서 멀면 목표 직교
  방향 횡섭동을 주입해 국소 최소를 탈출합니다(§5의 비보존항).
- **CBS 상위 계층.** 충돌 기반 탐색(Conflict-Based Search)이 APF 가 빠진 교착을 전역
  재계획으로 해소합니다.

따라서 본 분석의 결론은 *"APF 단독은 임계점으로 단조 수렴하며, 목표 수렴 실패(국소
최소)는 상위 계층이 보증한다"* 로 정리됩니다.

---

## 5. 분석 범위 (비보존항 제외)

다음 항은 보존장이 아니어서 본 Lyapunov 분석에서 제외했습니다.

| 항 | 성질 | 영향 |
|---|---|---|
| 척력 속도 증폭(접근 시 ×3–5) | 비보존(non-conservative) | **보존 분석 범위 밖 — 하강 무보증.** 인력·척력이 역방향인 배치에서 증폭 계수가 음의 교차항 $-(1{+}\alpha)(F_\text{att}\cdot F_\text{rep})$ 을 키워 $dU/dt>0$ 가능. 별도 분석 필요 |
| 고도 보정 $k_\text{alt}(z_\text{target} - z)$ | 수직축 별도 안정 | 수평 수렴과 분리 |
| 지면 반발($z < 5\,\text{m}$) | 경계 제약 | 안전 하한, 수렴과 무관 |
| 교착 탈출 횡섭동 | 비보존(국소 최소 탈출) | §4 의 완화 메커니즘 |

수직축 고도 보정은 $\dot{z} = k_\text{alt}(z_\text{target} - z)$ 형태의 선형 1차계로,
$V_z = \tfrac{1}{2}(z - z_\text{target})^2$ 가 $\dot{V}_z = -k_\text{alt}(z-z_\text{target})^2 \le 0$
을 주어 독립적으로 지수 안정합니다.

---

## 6. 재현

```bash
pytest tests/test_apf_lyapunov.py -v
```

- **G1** 포텐셜의 음의 기울기 = 실제 엔진 힘 (중심 차분 일치).
- **G2** 인력 포텐셜 양정치·$C^1$·radially unbounded.
- **G3** 척력 포텐셜 FIRAS 성질($\ge 0$, $d \ge d_0$ 에서 0, 근접 시 발산).
- **G4** 과감쇠 흐름 $dU/dt \le 0$, 장애물 없으면 목표로 단조 수렴.
- **G5** 장애물이 있어도 $U$ 단조 비증가(임계점 수렴).

## 참고문헌

- O. Khatib, "Real-Time Obstacle Avoidance for Manipulators and Mobile Robots," *IJRR*, 1986.
- J.-C. Latombe, *Robot Motion Planning*, Kluwer, 1991 (국소 최소·FIRAS).
- H. K. Khalil, *Nonlinear Systems*, 3rd ed., Prentice Hall, 2002 (Lyapunov·LaSalle).

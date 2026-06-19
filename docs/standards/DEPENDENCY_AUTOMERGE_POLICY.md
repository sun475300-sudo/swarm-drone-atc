# 의존성 자동 갱신 — 회귀 게이트 자동 머지 정책

> ODYSSEY Phase 481 (Continuum 트랙). 실행 가능 명세: [`simulation/dependency_gate.py`](../../simulation/dependency_gate.py)

## 목적

리포에는 Dependabot 이 생성하는 의존성 갱신 PR(pip·npm·github-actions)이
지속적으로 쌓인다. "어떤 갱신을 회귀 테스트만 통과하면 자동 머지해도 되고,
어떤 갱신은 사람 리뷰가 필요한가"를 매번 직관으로 판단하면 일관성이 없다.
본 정책은 그 판단을 **결정적 규칙**으로 명문화한다.

이 문서는 규칙을 *서술*할 뿐이며, **유일한 권위 있는 명세는
`simulation/dependency_gate.py` 의 `evaluate()`** 다. 본 문서와 코드가
어긋나면 코드가 옳고, 테스트(`tests/test_dependency_gate.py`)가 둘의 일치를
강제한다.

## 핵심 원칙

1. **자문이지 집행이 아님** — 본 모듈은 머지 *결정을 권고*할 뿐 실제로 PR 을
   머지하지 않는다(부수효과 0). 집행은 CI/사람이 한다.
2. **회귀 게이트 우선** — 머지 충돌·회귀 테스트 실패는 어떤 버전 점프든
   무조건 `BLOCK`. 자동 머지는 게이트 GREEN 이 *필요조건*.
3. **SemVer 보수성** — MAJOR 점프와 다운그레이드는 자동 머지 불가. 런타임
   의존성의 MINOR 도 사람 리뷰. 자동 머지는 *깨질 가능성이 낮은* 변경에만.

## 의존성 분류

| 분류 | 의미 | 예 |
|---|---|---|
| `runtime` | 런타임 동작에 직접 영향 | numpy·simpy·dash·matplotlib·pyyaml |
| `dev` | 개발/테스트 전용 | pytest·playwright·electron-builder·electron |
| `ci` | GitHub Actions 워크플로 액션 | actions/cache·setup-python·codeql-action |

## 결정 매트릭스 (게이트 GREEN 전제)

| 버전 점프 | runtime | dev | ci |
|---|:-:|:-:|:-:|
| **PATCH** (x.y.**Z**) | AUTO_MERGE | AUTO_MERGE | AUTO_MERGE |
| **MINOR** (x.**Y**.0) | REVIEW_REQUIRED | AUTO_MERGE | AUTO_MERGE |
| **MAJOR** (**X**.0.0) | REVIEW_REQUIRED | REVIEW_REQUIRED | REVIEW_REQUIRED |

게이트가 GREEN 이 아니거나 특수 케이스인 경우:

| 조건 | 결정 |
|---|---|
| 머지 충돌 존재 | **BLOCK** |
| 회귀 테스트 실패 | **BLOCK** |
| 버전 다운그레이드 | **BLOCK** |
| 알 수 없는 의존성 분류 | **BLOCK** |
| 버전 파싱 불가 (예: `latest`) | **REVIEW_REQUIRED** |
| 버전 변화 없음 (메타/해시만 변경) | **REVIEW_REQUIRED** |
| 커버리지 임계(80%) 미달 | **REVIEW_REQUIRED** (자동 머지 자격 박탈) |

## 결정 우선순위 (먼저 매칭되는 규칙이 결과)

1. 알 수 없는 의존성 분류 → `BLOCK`
2. 머지 충돌 → `BLOCK`
3. 회귀 테스트 실패 → `BLOCK`
4. 다운그레이드 → `BLOCK`
5. 버전 파싱 불가 → `REVIEW_REQUIRED`
6. 버전 변화 없음 → `REVIEW_REQUIRED`
7. 커버리지 미달 → `REVIEW_REQUIRED`
8. 자동 머지 후보 점프 → `AUTO_MERGE`, 아니면 `REVIEW_REQUIRED`

## 사용

```bash
python -m simulation.dependency_gate --policy     # 정책 매트릭스 출력
python -m simulation.dependency_gate --demo       # 적체 PR 형태 예시 평가
python -m simulation.dependency_gate --manifest   # 정책 매니페스트(JSON)
```

프로그래매틱 사용:

```python
from simulation.dependency_gate import DependencyUpdate, RegressionGate, evaluate

update = DependencyUpdate(
    name="pyyaml", ecosystem="pip",
    from_version="6.0.2", to_version="6.0.3",
    dep_class="runtime",
    gate=RegressionGate(tests_passed=True, coverage_ok=True),
)
print(evaluate(update).summary())
# AUTO_MERGE (PATCH): PATCH · runtime · 게이트 GREEN
```

## 범위 밖 (정직성 공시)

- 본 모듈은 **PR 을 실제로 머지하지 않는다.** GitHub Actions 워크플로로 본
  정책을 집행하려면 별도 자동화가 필요하며, 이는 본 Phase 범위 밖이다.
- 의존성 *분류*(`runtime`/`dev`/`ci`)는 호출자가 제공한다. 패키지명→분류
  자동 추론은 의도적으로 포함하지 않았다(오분류 위험 > 편익).
- 보안 권고(GHSA/CVE) 연동은 별도 Phase(488 CVE 대응 SLA) 후보.

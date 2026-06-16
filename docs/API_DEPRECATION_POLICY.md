# 📐 `window._sdacs` API Deprecation Policy & Semantic Versioning

*Created: 2026-06-13 · 근거: TRANSCENDENCE Phase 209-210 (Track Ⅱ-4) · `docs/MASTER_PLAN_2026H2.md`*
*용도: `_sdacs` 외부 API의 변경·폐기·버전 관리 규약 단일 기준*

> SDACS의 차별점은 **404개 외부 API 전부에 구현 성숙도(maturity)를 공시하는 정직성 체계**입니다.
> 본 문서는 그 정직성을 **시간축(버전 변경·폐기)** 으로 확장하여, API가 어떻게 도입·격상·폐기되는지를
> 규약화합니다. maturity가 "지금 이 API가 얼마나 믿을 만한가"라면, 본 정책은 "이 API가 다음 버전에서
> 어떻게 바뀌는가"를 규정합니다.

---

## 1. 적용 범위

| 대상 | 적용 |
|---|:-:|
| `window._sdacs.*` 외부 API (분류 404 + 헬퍼 3 = 407) | ✅ 본 정책 |
| `window._sdacs.experimental.*` (speculative 103종 격리) | ⚠️ 안정성 보장 제외 (아래 §6) |
| 시뮬레이터 내부 함수 (`_` prefix, 비노출) | ❌ 정책 외 (자유 변경) |
| Python `src/`·`simulation/`·`api/` 모듈 | ❌ 별도 (PEP·SemVer 패키지 단위) |

API 목록의 단일 출처는 [`SDACS_API.md`](SDACS_API.md)이며, `scripts/extract_sdacs_api.py`가 라이브
페이지에서 실측 추출합니다. 본 정책의 모든 "API"는 그 추출 결과에 존재하는 항목을 의미합니다.

---

## 2. Semantic Versioning 규약 (Phase 210)

시뮬레이터 버전은 [SemVer 2.0.0](https://semver.org/lang/ko/) `MAJOR.MINOR.PATCH`를 따릅니다.
현재 단일 출처는 [`VERSION.md`](VERSION.md)입니다 (예: `v1.5.0`).

| 변경 종류 | 증가 | API 영향 정의 |
|---|:-:|---|
| **MAJOR** (`X`.0.0) | 호환 불가 | 기존 API **시그니처 변경**·**제거**·**반환 의미 변경** |
| **MINOR** (1.`Y`.0) | 호환 가능 | 신규 API 추가·기존 API **maturity 격상**·**deprecated 표시** |
| **PATCH** (1.5.`Z`) | 버그 수정 | 동작 정정(반환 스키마·시그니처 불변) |

### 2.1 API 호환성 불변식

다음은 **MINOR/PATCH에서 보존**되어야 하는 계약입니다 (위반 시 MAJOR):

1. 기존 API 이름은 제거되지 않는다 (폐기 절차 §3을 거치기 전까지).
2. getter는 동일 키 집합 이상을 반환한다 (필드 제거 금지, 추가 허용).
3. method의 필수 인자 수는 늘어나지 않는다 (선택 인자 추가만 허용).
4. 반환 타입은 좁아지지 않는다 (`number → number|null` 같은 확대만 허용).

### 2.2 maturity 격상과 버전

maturity 등급 변경은 **MINOR**로 취급합니다 (호환성은 유지되나 신뢰 수준이 변하므로 기록 대상).

```
speculative ──▶ mock ──▶ beta ──▶ production
   ⚪            🟡         🔵          🟢
```

- 격상(좌→우)에는 **실측 근거**(회귀 테스트·E2E·외부 데이터 벤치)가 필수입니다 (거버넌스 게이트, `MASTER_PLAN_2026H2.md` §거버넌스 5).
- 강등(우→좌)은 결함 발견 시에만 허용하며, CHANGELOG에 사유를 명시합니다.

---

## 3. Deprecation 생애주기 (Phase 209)

API 폐기는 **3단계·최소 2 MINOR 버전**에 걸쳐 진행하며, 사용자에게 마이그레이션 시간을 보장합니다.

| 단계 | 상태 | 사용자 영향 | 최소 유지 기간 |
|---|---|---|---|
| **1. ACTIVE** | 정상 | 정상 동작 | — |
| **2. DEPRECATED** | 폐기 예고 | **동작 유지** + 호출 시 `console.warn` 1회 | ≥ 1 MINOR |
| **3. REMOVED** | 제거 | 호출 시 `undefined` (getter) / no-op (method) | MAJOR에서만 |

### 3.1 단계 전이 규칙

1. **ACTIVE → DEPRECATED**: MINOR 버전에서만 표시. 대체 API(`replacedBy`)와 제거 예정 버전(`removeIn`)을 §5 레지스트리에 등재.
2. **DEPRECATED → REMOVED**: 반드시 **MAJOR 버전 경계**에서만 수행. DEPRECATED를 최소 1개의 MINOR 사이클 이상 거친 뒤에만 제거.
3. 대체 API가 없는 폐기(순수 제거)는 MAJOR + 릴리스 노트 상단 **Breaking Changes** 명시를 동반.

### 3.2 폐기 경고 패턴 (권장 구현)

DEPRECATED API는 호출 시 1회 경고를 출력합니다 (Phase 203 Mock Detector와 동일 패턴 — 반복 스팸 금지):

```js
// 예시: 폐기된 getter
get oldMetric() {
  _sdacsDeprecate('oldMetric', { replacedBy: 'newMetric', removeIn: 'v2.0.0' });
  return this.newMetric;            // 동작은 그대로 유지
}
```

`_sdacsDeprecate(name, meta)`는 이름당 최초 1회만 `console.warn`을 발생시키고,
`maturityReport().deprecatedCalls`에 카운트를 누적하도록 설계합니다 (구현은 차기 시뮬레이터 PR — 본 문서는 정책 확정이 목적).

---

## 4. maturity ↔ deprecation 상호작용

| maturity | 폐기 정책 |
|---|---|
| 🟢 production | 가장 엄격 — DEPRECATED 최소 2 MINOR 유지 후 MAJOR 제거 |
| 🔵 beta | DEPRECATED 최소 1 MINOR 유지 후 MAJOR 제거 |
| 🟡 mock | 즉시 DEPRECATED 가능, 다음 MAJOR 제거 (인터페이스만 안정 보장이므로) |
| ⚪ speculative (`experimental.*`) | 정책 외 — **사전 경고 없이 변경/제거 가능** (§6) |

> 원칙: **신뢰를 더 약속한 API일수록 폐기를 더 천천히 한다.** production은 사용자가 의존하므로 가장 보수적으로, speculative는 비전 스텁이므로 자유롭게.

---

## 5. Deprecation Registry (현재)

> 폐기 예고된 API의 단일 추적 표. 신규 폐기 시 본 표에 행을 추가합니다.

| API | maturity | 상태 | 대체 (`replacedBy`) | 제거 예정 (`removeIn`) | 예고 버전 |
|---|---|---|---|---|---|
| _(없음)_ | — | — | — | — | — |

현재 폐기 예고된 외부 API는 **0건**입니다 (v1.5.0 기준). 404개 API 전부 ACTIVE.

---

## 6. `experimental.*` 네임스페이스 면책 (Phase 206 연계)

speculative 103종은 `window._sdacs.experimental.*`로 격리되어 있습니다 (Phase 206).
이 네임스페이스의 API는:

- **SemVer 호환성 보장 대상이 아닙니다** — MINOR/PATCH에서도 시그니처·동작이 바뀔 수 있습니다.
- 폐기 시 **DEPRECATED 단계를 건너뛰고** 즉시 변경/제거될 수 있습니다.
- 프로덕션 의존 금지. PoC·데모·미래 비전 탐색 용도로만 사용합니다.

직접 호출 호환성(`_sdacs.<name>`)은 Phase 206에서 유지되나, 이는 **편의이지 안정성 약속이 아닙니다.**

---

## 7. 변경 절차 체크리스트

API를 추가·격상·폐기하는 PR은 다음을 만족해야 합니다:

- [ ] `VERSION.md`의 버전을 SemVer 규칙(§2)대로 증가
- [ ] 신규/격상 API는 E2E 1건 이상 동반 (거버넌스 게이트)
- [ ] maturity 변경은 `apiMaturity()` 레지스트리 + `SDACS_API.md` 동시 갱신
- [ ] 폐기는 §5 레지스트리에 행 추가 + `removeIn`/`replacedBy` 명시
- [ ] `scripts/extract_sdacs_api.py --check` 통과 (문서-실측 일치, CI 게이트 G-2)
- [ ] 4 사본 md5 일치 보존 (CI 게이트 G-4)
- [ ] CHANGELOG.md에 변경 종류(MAJOR/MINOR/PATCH) 표기

---

## 8. 관련 문서

- [`SDACS_API.md`](SDACS_API.md) — 404 API maturity 레퍼런스 (단일 출처)
- [`VERSION.md`](VERSION.md) — 버전 단일 출처
- [`MASTER_PLAN_2026H2.md`](MASTER_PLAN_2026H2.md) — Track Ⅱ-4 (본 문서의 상위 계획)
- [`SIMULATOR_TRANSCENDENCE_PLAN.md`](SIMULATOR_TRANSCENDENCE_PLAN.md) — Phase 209·210 정의
- [`TECH_DEBT_LEDGER.md`](TECH_DEBT_LEDGER.md) — mock/speculative 부채 공시

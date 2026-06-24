# SDACS API Deprecation Policy / API 폐기 정책

**Phase 209 — TRANSCENDENCE**
**Version**: 1.0.0
**Date**: 2026-06-18
**Applies to**: All `window._sdacs.*` public APIs (407 endpoints as of Phase 200)

---

## 1. Purpose and Scope / 목적 및 적용 범위

### English

This document defines the lifecycle, deprecation process, and removal policy for all public APIs exposed under `window._sdacs`. It ensures consumers have predictable timelines and migration paths when APIs change.

**Scope**: Every property, method, and getter registered in `window._sdacs` — including those enumerated by `_sdacs.apiMaturity()` and `_sdacs.maturityReport()`. Internal helper APIs (`apiMaturity`, `maturityReport`, `maturityStats`) are exempt from deprecation timelines but follow the same communication standards.

### 한국어

본 문서는 `window._sdacs`에 등록된 모든 공개 API의 수명주기, 폐기 절차, 제거 정책을 정의합니다. API 변경 시 소비자에게 예측 가능한 일정과 마이그레이션 경로를 보장하는 것이 목적입니다.

**적용 범위**: `window._sdacs`에 등록된 모든 프로퍼티, 메서드, getter를 포함합니다. `_sdacs.apiMaturity()` 및 `_sdacs.maturityReport()`로 열거되는 모든 항목이 해당됩니다. 내부 헬퍼 API(`apiMaturity`, `maturityReport`, `maturityStats`)는 폐기 일정 적용 대상에서 제외되지만, 동일한 공지 기준을 따릅니다.

---

## 2. Maturity Lifecycle / 성숙도 수명주기

Each API progresses through the following stages. Transitions are unidirectional under normal circumstances.

각 API는 아래의 단계를 순차적으로 거칩니다. 일반적인 상황에서 단계 전환은 단방향입니다.

```
speculative → mock → beta → production → deprecated → removed
```

| Stage / 단계 | Symbol | Meaning / 의미 |
|---|---|---|
| **speculative** | ⚪ | Future-vision stub. Call-safety only — no behavioral guarantees. / 미래 비전 스텁. 호출 안전성만 보장합니다. |
| **mock** | 🟡 | Deterministic mock. Interface is stable; implementation returns synthetic data. / 결정적 mock. 인터페이스는 안정적이며 합성 데이터를 반환합니다. |
| **beta** | 🔵 | Functional with E2E verification. Some external dependencies may change. / E2E 검증 완료. 일부 외부 의존성이 변경될 수 있습니다. |
| **production** | 🟢 | Measured, regression-tested, real algorithm. Stability guaranteed. / 실측 검증 + 회귀 테스트 + 실제 알고리즘. 안정성을 보장합니다. |
| **deprecated** | 🔴 | Scheduled for removal. Still functional but emits warnings. / 제거 예정. 동작하지만 경고를 출력합니다. |
| **removed** | ❌ | No longer available. Calls throw or return undefined. / 더 이상 사용할 수 없습니다. 호출 시 예외 발생 또는 undefined 반환. |

### Runtime Query / 런타임 조회

```javascript
// Check individual API maturity
window._sdacs.apiMaturity('atcCommand');  // → "production"

// Full maturity report
window._sdacs.maturityReport();  // → { production: [...], beta: [...], mock: [...], speculative: [...], deprecated: [...] }
```

---

## 3. Deprecation Timeline Rules / 폐기 일정 규칙

Grace periods are measured from the date the API is officially marked `deprecated` in `DEPRECATION_LOG.md`.

유예 기간은 API가 `DEPRECATION_LOG.md`에 공식적으로 `deprecated` 표기된 날짜로부터 측정합니다.

| Current Maturity / 현재 성숙도 | Grace Period / 유예 기간 | Rationale / 근거 |
|---|---|---|
| 🟢 **production** | **12 months** | Consumers depend on stable behavior. Ample migration time required. / 소비자가 안정적 동작에 의존합니다. 충분한 마이그레이션 시간이 필요합니다. |
| 🔵 **beta** | **6 months** | Functional but explicitly labeled as evolving. / 동작하지만 변경 가능성이 명시되어 있습니다. |
| 🟡 **mock** | **1 month** | Interface-only contract. Can be replaced or removed with short notice. / 인터페이스 계약만 존재합니다. 짧은 공지로 대체 또는 제거 가능합니다. |
| ⚪ **speculative** | **None (즉시)** | Experimental stubs carry no stability promise. Can be removed without notice. / 실험적 스텁으로 안정성 보장이 없습니다. 사전 공지 없이 제거할 수 있습니다. |

**Key rule**: An API's grace period is locked at the time of deprecation. If a beta API is deprecated today, its 6-month clock starts today — even if it would have been promoted to production next week.

**핵심 규칙**: 유예 기간은 폐기 시점의 성숙도에 의해 결정됩니다. 오늘 beta API가 폐기되면 6개월 시계가 오늘부터 시작됩니다. 다음 주에 production 승격 예정이었더라도 변경되지 않습니다.

---

## 4. Deprecation Process / 폐기 절차

### Step 1: Code Annotation / 코드 주석 처리

Mark the API with `@deprecated` JSDoc and emit a console warning on the first invocation per session.

API에 `@deprecated` JSDoc을 추가하고, 세션당 첫 호출 시 콘솔 경고를 출력합니다.

```javascript
/**
 * @deprecated Since v1.5.0. Use `_sdacs.atcCommandV2()` instead.
 *             Removal scheduled: 2027-06-18 (production 12-month grace).
 */
get exampleApi() {
  if (!this._warned_exampleApi) {
    console.warn(
      '[SDACS Deprecation] exampleApi is deprecated and will be removed in v2.0.0. ' +
      'Use exampleApiV2() instead. See docs/DEPRECATION_LOG.md for details.'
    );
    this._warned_exampleApi = true;
  }
  return this._exampleApiImpl();
}
```

### Step 2: Log Entry / 로그 기록

Add an entry to `docs/DEPRECATION_LOG.md` with the following fields.

아래 필드를 포함하여 `docs/DEPRECATION_LOG.md`에 항목을 추가합니다.

| Field / 필드 | Description / 설명 |
|---|---|
| **API Name** | Full `_sdacs.*` identifier |
| **Deprecated Date** | ISO 8601 date (YYYY-MM-DD) |
| **Maturity at Deprecation** | production / beta / mock / speculative |
| **Removal Target Date** | Calculated from grace period |
| **Removal Target Version** | Next major version after grace period expires |
| **Reason** | Why the API is being deprecated |
| **Replacement** | New API name, or "None" if functionality is removed |
| **Migration Guide** | Link to migration section or inline instructions |

### Step 3: Update maturityReport() / maturityReport() 갱신

Update the maturity classification so `_sdacs.maturityReport()` lists the API under a `deprecated` category. The API must appear in the deprecated list, not its former maturity tier.

성숙도 분류를 갱신하여 `_sdacs.maturityReport()`에서 해당 API가 `deprecated` 범주에 나타나도록 합니다. 기존 성숙도 등급이 아닌 deprecated 목록에 표시되어야 합니다.

```javascript
window._sdacs.apiMaturity('exampleApi');  // → "deprecated"
```

### Step 4: Removal / 제거

Remove the API after **both** conditions are met:

다음 **두 조건이 모두** 충족된 후 API를 제거합니다:

1. The grace period has elapsed. / 유예 기간이 경과하였습니다.
2. A major version bump occurs (aligned with Phase 210 SemVer). / 메이저 버전 범프가 발생합니다 (Phase 210 SemVer와 연동).

Upon removal:
- The API entry is moved from `deprecated` to `removed` in `DEPRECATION_LOG.md`.
- The corresponding code is deleted from the codebase.
- `maturityReport()` no longer lists the API.

제거 시:
- `DEPRECATION_LOG.md`에서 해당 항목을 `deprecated`에서 `removed`로 이동합니다.
- 코드베이스에서 해당 코드를 삭제합니다.
- `maturityReport()`에서 해당 API가 더 이상 표시되지 않습니다.

---

## 5. Breaking vs. Non-Breaking Changes / 호환성 파괴 vs. 비파괴 변경

### Breaking Changes (호환성 파괴 변경)

The following changes are considered breaking and **require** the full deprecation process:

아래 변경 사항은 호환성 파괴 변경으로 간주하며, **반드시** 전체 폐기 절차를 따라야 합니다:

- Removing an API (method, property, or getter)
- Changing the return type of an existing API
- Changing required parameter count or types
- Renaming an API without preserving the old name as an alias
- Changing the semantic meaning of a return value (e.g., meters to feet)
- Changing error behavior (previously non-throwing API now throws)
- Removing a field from a returned object

### Non-Breaking Changes (비파괴 변경)

The following changes are non-breaking and do **not** require the deprecation process:

아래 변경 사항은 비파괴 변경으로 폐기 절차가 **불필요**합니다:

- Adding a new API
- Adding optional parameters with default values to existing APIs
- Adding new fields to returned objects
- Improving performance without changing behavior
- Fixing a bug to match documented behavior
- Promoting an API to a higher maturity tier (e.g., mock → beta)
- Adding `console.warn` for usage guidance (not deprecation)

---

## 6. Communication Channels / 공지 채널

Deprecation announcements are published through the following channels. All three must be updated for every deprecation.

폐기 공지는 아래 채널을 통해 게시합니다. 모든 폐기에 대해 세 채널 모두 갱신해야 합니다.

| Channel / 채널 | Content / 내용 | Timing / 시점 |
|---|---|---|
| **`docs/DEPRECATION_LOG.md`** | Canonical record with full details, migration guide | At deprecation and at removal / 폐기 시 및 제거 시 |
| **GitHub Releases Changelog** | Summary entry in release notes for the version that introduces the deprecation | At release / 릴리스 시 |
| **`README.md`** | "Deprecation Notices" section with active deprecations and their removal dates | At deprecation; remove entry after removal / 폐기 시 추가, 제거 후 삭제 |

### Console Runtime Notice / 콘솔 런타임 알림

In addition to written documentation, deprecated APIs emit a `console.warn` on first invocation per browser session (see Step 1). This ensures developers who test against the live simulator are notified directly.

문서 공지 외에, 폐기된 API는 브라우저 세션당 첫 호출 시 `console.warn`을 출력합니다 (Step 1 참조). 이를 통해 라이브 시뮬레이터를 대상으로 테스트하는 개발자에게 직접 알림이 전달됩니다.

---

## 7. Emergency Security Deprecation / 긴급 보안 폐기

When a security vulnerability is identified in an API, the standard grace periods may be bypassed.

API에서 보안 취약점이 식별된 경우, 표준 유예 기간을 우회할 수 있습니다.

### Criteria / 기준

Emergency deprecation applies when:
- The API exposes user data or session tokens
- The API enables cross-origin exploitation
- The API allows unauthorized control of simulator state
- A CVE or equivalent advisory is published

긴급 폐기는 다음의 경우에 적용됩니다:
- API가 사용자 데이터 또는 세션 토큰을 노출하는 경우
- API가 교차 출처(cross-origin) 악용을 허용하는 경우
- API가 시뮬레이터 상태의 무단 제어를 허용하는 경우
- CVE 또는 동등한 보안 권고가 발행된 경우

### Process / 절차

1. **Immediate disable**: API is disabled (returns error or no-op) within 24 hours. / **즉시 비활성화**: API를 24시간 이내에 비활성화합니다 (에러 반환 또는 no-op).
2. **Hotfix release**: A patch version is released with the API disabled and a security notice. / **긴급 패치 릴리스**: API를 비활성화하고 보안 공지를 포함한 패치 버전을 릴리스합니다.
3. **Post-incident log**: Entry added to `DEPRECATION_LOG.md` with reason `SECURITY` and reference to the advisory. / **사후 기록**: `DEPRECATION_LOG.md`에 `SECURITY` 사유와 권고 참조를 포함한 항목을 추가합니다.
4. **Migration support**: If a safe replacement exists, migration guide is published within 7 days. / **마이그레이션 지원**: 안전한 대체 API가 존재하는 경우, 7일 이내에 마이그레이션 가이드를 게시합니다.

Emergency deprecations are exempt from all grace periods regardless of the API's maturity at the time of the incident.

긴급 폐기는 사고 시점의 API 성숙도와 관계없이 모든 유예 기간에서 면제됩니다.

---

## 8. Migration Guide Template / 마이그레이션 가이드 템플릿

Every deprecated API with a replacement must include a migration guide. Use the following template.

대체 API가 존재하는 모든 폐기 API에 대해 마이그레이션 가이드를 작성해야 합니다. 아래 템플릿을 사용합니다.

```markdown
### Migration: `oldApiName` → `newApiName`

**Deprecated**: YYYY-MM-DD | **Removal target**: YYYY-MM-DD (vX.0.0)

#### What changed / 변경 사항
Brief description of why the old API is being replaced.

#### Before (deprecated) / 변경 전 (폐기됨)
```javascript
const result = window._sdacs.oldApiName(param1, param2);
```

#### After (recommended) / 변경 후 (권장)
```javascript
const result = window._sdacs.newApiName({ key1: param1, key2: param2 });
```

#### Key differences / 주요 차이점
- Difference 1
- Difference 2

#### Edge cases / 예외 상황
Notes on any behavioral differences that may affect existing usage.
```

---

## 9. Versioning Alignment / 버전 관리 연동

This policy aligns with the Semantic Versioning (SemVer) scheme introduced in Phase 210.

본 정책은 Phase 210에서 도입되는 유의적 버전 관리(SemVer)와 연동됩니다.

| Version Component / 버전 구성 | API Policy Implication / API 정책 영향 |
|---|---|
| **Major** (X.0.0) | Deprecated APIs may be removed. All removals happen in major releases only. / 폐기된 API를 제거할 수 있습니다. 모든 제거는 메이저 릴리스에서만 수행합니다. |
| **Minor** (0.X.0) | New APIs may be added. Existing APIs may be marked deprecated. Maturity promotions occur here. / 새 API를 추가할 수 있습니다. 기존 API를 폐기 표기할 수 있습니다. 성숙도 승격이 이 단계에서 발생합니다. |
| **Patch** (0.0.X) | Bug fixes only. No deprecations or removals — except emergency security deprecations (Section 7). / 버그 수정만 수행합니다. 폐기 또는 제거 없음 — 긴급 보안 폐기(섹션 7)는 예외입니다. |

### Deprecation-to-Removal Timeline Example / 폐기-제거 일정 예시

```
v1.5.0 (2026-07)  — atcCommand marked deprecated (production, 12-month grace)
v1.6.0 (2026-10)  — Minor release, atcCommand still functional with warnings
v1.7.0 (2027-01)  — Minor release, atcCommand still functional with warnings
v2.0.0 (2027-07+) — Major release after grace period: atcCommand removed
```

---

## 10. Current API Distribution / 현재 API 분포

As of Phase 200 (Unity), the `window._sdacs` namespace contains:

Phase 200 (Unity) 기준, `window._sdacs` 네임스페이스의 구성:

| Maturity / 성숙도 | Count / 개수 | Deprecation Notice / 폐기 공지 |
|---|---|---|
| 🟢 production | 93 | 12 months required / 12개월 사전 공지 필요 |
| 🔵 beta | 98 | 6 months required / 6개월 사전 공지 필요 |
| 🟡 mock | 110 | 1 month required / 1개월 사전 공지 필요 |
| ⚪ speculative | 103 | No notice required / 사전 공지 불필요 |
| 🛠 helper | 3 | Exempt / 면제 |
| **Total** | **407** | |

---

## Appendix A: DEPRECATION_LOG.md Format / 부록 A: DEPRECATION_LOG.md 형식

The canonical deprecation log (`docs/DEPRECATION_LOG.md`) uses the following table format:

정식 폐기 로그(`docs/DEPRECATION_LOG.md`)는 아래 표 형식을 사용합니다:

```markdown
# SDACS API Deprecation Log

| API | Deprecated | Maturity | Removal Target | Version | Reason | Replacement | Status |
|-----|-----------|----------|---------------|---------|--------|-------------|--------|
| exampleApi | 2026-07-01 | production | 2027-07-01 | v2.0.0 | Replaced by V2 with options object | exampleApiV2 | deprecated |
```

**Status values**: `deprecated` (active, within grace period), `removed` (deleted from codebase).

**상태 값**: `deprecated` (활성, 유예 기간 내), `removed` (코드베이스에서 삭제됨).

---

## Appendix B: Policy Revision / 부록 B: 정책 개정

This policy itself follows SemVer. Changes to grace periods or the deprecation process constitute a major policy revision and require a 3-month notice period before taking effect.

본 정책 자체도 SemVer를 따릅니다. 유예 기간 또는 폐기 절차의 변경은 주요 정책 개정으로 간주하며, 시행 전 3개월의 공지 기간이 필요합니다.

| Policy Version / 정책 버전 | Date / 날짜 | Change / 변경 사항 |
|---|---|---|
| 1.0.0 | 2026-06-18 | Initial release (Phase 209 TRANSCENDENCE) / 초기 릴리스 |

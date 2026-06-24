# SDACS Semantic Versioning Policy / 시맨틱 버전 관리 정책

**TRANSCENDENCE Phase 210** | Swarm Drone Airspace Control System  
**Mokpo National University Capstone Project**  
*Last updated: 2026-06-18*

---

## 1. Overview / 개요

본 문서는 SDACS(군집드론 공역통제 자동화 시스템) 프로젝트의 시맨틱 버전 관리 정책을 정의합니다.
SDACS는 SemVer 2.0.0 규격을 채택하며, `window._sdacs` 네임스페이스 하에 407개의 JavaScript API를 관리합니다.

This document defines the semantic versioning policy for the SDACS (Swarm Drone Airspace Control System) project.
SDACS adopts the SemVer 2.0.0 specification and manages 407 JavaScript APIs under the `window._sdacs` namespace.

**Current Version / 현재 버전:** v1.5.0 (Desktop)

---

## 2. SemVer 2.0.0 Adoption / SemVer 2.0.0 채택

SDACS는 `MAJOR.MINOR.PATCH` 형식의 시맨틱 버전을 사용합니다.

```
MAJOR.MINOR.PATCH[-prerelease][+build]
예: 2.0.0-beta.1+20260618
```

모든 버전 번호는 음이 아닌 정수이며, 선행 0 없이 증가합니다.
SemVer 2.0.0 전체 규격은 https://semver.org 을 참조하십시오.

All version numbers are non-negative integers that increment without leading zeros.
Refer to https://semver.org for the full SemVer 2.0.0 specification.

---

## 3. SDACS Version Increment Rules / SDACS 버전 증가 규칙

### 3.1 API Maturity Classification / API 성숙도 분류

| Maturity / 성숙도 | Count / 수량 | Description / 설명 |
|---|---|---|
| **Production** | 93 | 안정된 공개 API. 하위 호환성 보장 대상입니다. |
| **Beta** | 98 | 테스트 단계 API. 사전 공지 후 변경될 수 있습니다. |
| **Mock** | 110 | 시뮬레이션 전용 스텁. 내부 구현이며 외부 의존 금지입니다. |
| **Speculative** | 103 | 실험적 API. 예고 없이 변경 또는 제거될 수 있습니다. |

> **총 407개 API** (`window._sdacs` 네임스페이스)

### 3.2 MAJOR Version / 메이저 버전 (X.0.0)

다음 중 하나라도 해당하면 MAJOR 버전을 증가시킵니다.

The MAJOR version MUST be incremented when any of the following occurs:

| Trigger / 트리거 | Example / 예시 |
|---|---|
| Production API의 시그니처(매개변수, 반환값, 동작) 변경 | `_sdacs.drone.getPosition()` 반환 형식 변경 |
| Production API 제거 | `_sdacs.airspace.legacyQuery()` 삭제 |
| Phase 209 Deprecation Policy에 따라 사용 중단된 API의 최종 제거 | 사용 중단 공지 후 2 마이너 릴리스 경과, 해당 API 삭제 |
| Production API의 기본값(default) 변경으로 기존 동작이 달라지는 경우 | `conflictRadius` 기본값 50m에서 100m으로 변경 |
| 필수 매개변수 추가 | `_sdacs.simulation.run()` 에 필수 `config` 인자 추가 |

**MAJOR 증가 시 MINOR와 PATCH는 0으로 초기화합니다.**

When MAJOR increments, MINOR and PATCH reset to 0.

### 3.3 MINOR Version / 마이너 버전 (x.Y.0)

다음 중 하나라도 해당하면 MINOR 버전을 증가시킵니다.

The MINOR version MUST be incremented when any of the following occurs:

| Trigger / 트리거 | Example / 예시 |
|---|---|
| 새로운 Production API 추가 | `_sdacs.weather.getWindField()` 신규 |
| 새로운 Beta API 추가 | `_sdacs.swarm.formationControl()` 베타 공개 |
| 기존 Production API에 선택적(optional) 매개변수 추가 | `_sdacs.drone.getPosition({format?: 'lla'})` |
| Mock에서 Beta로 승격 | `_sdacs.sensor.lidar` mock에서 beta로 승격 |
| Beta에서 Production으로 승격 | `_sdacs.telemetry.stream` beta에서 production으로 승격 |
| Production API의 사용 중단(deprecated) 표시 | `@deprecated` 주석 추가 (Phase 209 정책 연계) |
| 하위 호환성이 유지되는 기능 개선 | 기존 API에 새 반환 필드 추가 |

**MINOR 증가 시 PATCH는 0으로 초기화합니다.**

When MINOR increments, PATCH resets to 0.

### 3.4 PATCH Version / 패치 버전 (x.y.Z)

다음에 해당하면 PATCH 버전을 증가시킵니다.

The PATCH version MUST be incremented for:

| Trigger / 트리거 | Example / 예시 |
|---|---|
| Production/Beta API의 버그 수정 (동작 변경 없음) | `_sdacs.collision.detect()` 오탐 수정 |
| 문서 수정 | JSDoc 주석 오류 수정 |
| Speculative API 추가, 변경, 또는 제거 | 실험적 API는 외부 계약에 포함되지 않습니다 |
| Mock API 내부 구현 변경 | 스텁 반환값 조정 |
| 테스트 추가 또는 수정 | 회귀 테스트 보강 |
| 빌드 설정 또는 CI 파이프라인 변경 | Electron builder 설정 수정 |
| 성능 개선 (외부 동작 동일) | APF 계산 최적화 |

---

## 4. Pre-release Identifiers / 프리릴리스 식별자

SemVer 2.0.0에 따라 프리릴리스 버전은 하이픈(`-`) 뒤에 식별자를 붙여 표기합니다.

Pre-release versions are denoted by appending a hyphen and identifier per SemVer 2.0.0.

| Identifier / 식별자 | Meaning / 의미 | Stability / 안정성 |
|---|---|---|
| `-alpha.N` | Speculative API가 포함된 내부 빌드입니다 | 불안정. 테스트 목적 전용입니다. |
| `-beta.N` | Beta API가 포함된 공개 테스트 빌드입니다 | 준안정. API 변경 가능성이 있습니다. |
| `-rc.N` | 릴리스 후보입니다. Production API 확정 상태입니다 | 안정. 치명적 버그 수정만 허용됩니다. |

**Examples / 예시:**

```
2.0.0-alpha.1    → 실험적 기능 포함 내부 빌드
2.0.0-beta.3     → 베타 테스트 3차 빌드
2.0.0-rc.1       → 릴리스 후보 1차
2.0.0            → 정식 릴리스
```

**Precedence / 우선순위:**  
`1.5.0` > `2.0.0-rc.1` > `2.0.0-beta.3` > `2.0.0-alpha.1` (정식 > RC > Beta > Alpha, 동일 버전 내)

> 프리릴리스 버전은 정식 릴리스보다 낮은 우선순위를 가집니다.
> Pre-release versions have lower precedence than the associated normal version.

---

## 5. Version Tracking / 버전 추적

SDACS는 다음 세 곳에서 버전을 동기화하여 관리합니다.

SDACS tracks versions across three synchronized sources:

### 5.1 VERSION.md — Human-Readable Changelog / 사람이 읽을 수 있는 변경 이력

프로젝트 루트의 `VERSION.md`에 릴리스별 변경 사항을 기록합니다.

```markdown
# SDACS Version History

## v2.0.0 (2026-XX-XX)
### Breaking Changes
- `_sdacs.airspace.query()` 시그니처 변경: `query(type)` → `query({type, region})`
- `_sdacs.legacy.*` 네임스페이스 제거 (v1.4.0 에서 deprecated)

### New Features
- `_sdacs.weather.getWindField()` 추가 (Production)

### Bug Fixes
- `_sdacs.collision.detect()` 경계 조건 수정
```

### 5.2 `_sdacs.version()` — Runtime Version Query / 런타임 버전 조회 API

시뮬레이터 내에서 프로그래밍 방식으로 버전을 조회할 수 있습니다.

```javascript
// 버전 문자열 반환
_sdacs.version()
// → "2.0.0"

// 상세 버전 정보 객체 반환
_sdacs.version({ detailed: true })
// → {
//     version: "2.0.0",
//     major: 2,
//     minor: 0,
//     patch: 0,
//     prerelease: null,
//     apiCount: { production: 93, beta: 98, mock: 110, speculative: 103 },
//     buildDate: "2026-06-18T00:00:00Z"
//   }
```

### 5.3 Package Manifests / 패키지 매니페스트

| File / 파일 | Scope / 범위 | Field / 필드 |
|---|---|---|
| `package.json` | Electron Desktop 앱 | `"version": "2.0.0"` |
| `pyproject.toml` | Python 시뮬레이션 코어 | `version = "2.0.0"` |

> 릴리스 시 위 세 곳(`VERSION.md`, `_sdacs.version()` 반환값, 패키지 매니페스트)의 버전이 반드시 일치해야 합니다.
> All three sources MUST agree at release time.

---

## 6. Breaking Change Detection / 호환성 파괴 변경 감지

### 6.1 CI Gate — API Surface Comparison / CI 게이트 — API 표면 비교

모든 PR에서 API 표면(surface) 비교를 CI 파이프라인에서 자동 수행합니다.

Every PR triggers an automated API surface comparison in the CI pipeline.

```
┌─────────────────────────────────────────────────────┐
│                CI API Diff Pipeline                  │
│                                                     │
│  1. 이전 릴리스의 API 스냅샷 로드                      │
│     Load previous release API snapshot              │
│                                                     │
│  2. 현재 브랜치의 API 표면 추출                        │
│     Extract current branch API surface              │
│                                                     │
│  3. 차이 비교 (diff)                                 │
│     Compare surfaces                                │
│                                                     │
│  4. 변경 유형 분류                                    │
│     Classify change type                            │
│                                                     │
│  5. 버전 범프 검증                                    │
│     Validate version bump                           │
└─────────────────────────────────────────────────────┘
```

**API Snapshot Format / API 스냅샷 형식:**

```json
{
  "version": "1.5.0",
  "timestamp": "2026-06-05T00:00:00Z",
  "apis": {
    "_sdacs.drone.getPosition": {
      "maturity": "production",
      "params": ["options?"],
      "returns": "Position3D",
      "since": "1.0.0"
    }
  }
}
```

스냅샷은 `api-snapshots/v{version}.json` 에 저장되며, 태그 생성 시 자동 생성됩니다.

Snapshots are stored in `api-snapshots/v{version}.json` and auto-generated on tag creation.

### 6.2 Auto-Bump Logic / 자동 버전 범프 로직

CI에서 감지된 변경 유형에 따라 필요한 최소 버전 범프를 자동으로 판별합니다.

The CI pipeline automatically determines the minimum required version bump based on detected changes.

```
감지된 변경                           → 필요한 범프
─────────────────────────────────────────────────
Production API 제거됨                 → MAJOR
Production API 시그니처 변경됨        → MAJOR
Production API 기본값 변경됨          → MAJOR
필수 매개변수 추가됨                  → MAJOR
─────────────────────────────────────────────────
새 Production/Beta API 추가됨        → MINOR
선택적 매개변수 추가됨               → MINOR
Mock→Beta 또는 Beta→Production 승격  → MINOR
Production API deprecated 표시       → MINOR
─────────────────────────────────────────────────
버그 수정만                          → PATCH
문서 변경만                          → PATCH
Mock/Speculative 내부 변경만         → PATCH
─────────────────────────────────────────────────
```

**Validation Rule / 검증 규칙:**

PR에 명시된 버전이 자동 판별된 최소 범프보다 낮으면 CI가 실패합니다.

If the version specified in the PR is lower than the auto-detected minimum bump, CI fails.

```
예: Production API가 제거되었는데 MINOR 범프만 했을 경우
    → CI 실패 (MAJOR 범프 필요)
    → "ERROR: Breaking change detected. Expected MAJOR bump (>=2.0.0), found 1.6.0"
```

---

## 7. Release Cadence / 릴리스 주기

| Release Type / 유형 | Cadence / 주기 | Description / 설명 |
|---|---|---|
| **MAJOR** | 필요 시 (호환성 파괴 변경 발생 시) | Production API 호환성 파괴 시에만 릴리스합니다. 최소 1개 마이너 릴리스 전에 사용 중단 공지를 합니다. |
| **MINOR** | 분기별 (3개월) | 새 기능, API 추가, 승격 등을 포함합니다. 일정: 3월, 6월, 9월, 12월 릴리스를 목표로 합니다. |
| **PATCH** | 필요 시 (수시) | 버그 수정, 문서 갱신 등 긴급 수정을 포함합니다. 보안 패치는 발견 후 72시간 이내에 릴리스합니다. |

**Release Process / 릴리스 프로세스:**

```
1. 릴리스 브랜치 생성: release/v{version}
2. VERSION.md 갱신
3. package.json, pyproject.toml 버전 동기화
4. _sdacs.version() 반환값 갱신
5. 회귀 테스트 전체 통과 확인 (pytest tests/ -v)
6. API 스냅샷 생성
7. Git 태그 생성: git tag -a v{version}
8. 태그 푸시 → CI 자동 빌드 및 릴리스 발행
```

---

## 8. Compatibility Matrix / 호환성 매트릭스

시뮬레이터 버전과 API 버전 간의 호환성을 다음 매트릭스로 관리합니다.

The following matrix tracks compatibility between simulator versions and API versions.

| Simulator Version / 시뮬레이터 버전 | API Version / API 버전 | Production APIs | Beta APIs | Status / 상태 |
|---|---|---|---|---|
| v1.0.0 | 1.0.0 | 45 | 12 | EOL (지원 종료) |
| v1.1.0 | 1.1.0 | 58 | 30 | EOL |
| v1.2.0 | 1.2.0 | 67 | 45 | EOL |
| v1.5.0 | 1.5.0 | 93 | 98 | **Current (현재)** |
| v2.0.0 | 2.0.0 | TBD | TBD | Planned (계획) |

**Support Policy / 지원 정책:**

| Support Level / 지원 수준 | Duration / 기간 | Scope / 범위 |
|---|---|---|
| **Active** (활성) | 현재 + 직전 마이너 릴리스 | 버그 수정, 보안 패치, 기능 개선 |
| **Maintenance** (유지보수) | 직전 메이저 릴리스의 마지막 마이너 | 보안 패치만 제공합니다 |
| **EOL** (지원 종료) | 그 외 | 패치가 제공되지 않습니다 |

> **캡스톤 프로젝트 특이사항:** 본 프로젝트는 목포대학교 캡스톤 프로젝트로, 지원 기간은 프로젝트 활동 기간에 의해 제한될 수 있습니다.

> **Capstone note:** As a Mokpo National University capstone project, support durations may be limited by the project activity period.

---

## 9. Major Version Migration Guide Template / 메이저 버전 마이그레이션 가이드 템플릿

새로운 MAJOR 버전 릴리스 시 아래 템플릿에 따라 마이그레이션 가이드를 작성합니다.

When a new MAJOR version is released, a migration guide MUST be created following this template.

---

```markdown
# Migration Guide: v{OLD} → v{NEW}
# 마이그레이션 가이드: v{OLD} → v{NEW}

## Breaking Changes Summary / 호환성 파괴 변경 요약

| API | Change / 변경 | Migration Action / 마이그레이션 조치 |
|-----|---------------|--------------------------------------|
| `_sdacs.example.oldMethod()` | 제거됨 | `_sdacs.example.newMethod()` 사용 |
| `_sdacs.example.query(type)` | 시그니처 변경 | `_sdacs.example.query({type})` 로 변경 |

## Step-by-Step Migration / 단계별 마이그레이션

### Step 1: Update Dependencies / 의존성 갱신
- `package.json` 의 SDACS 버전을 v{NEW}으로 갱신합니다.

### Step 2: Replace Removed APIs / 제거된 API 교체
- 제거된 API 호출을 대체 API로 교체합니다.
- 검색 패턴: `grep -r "oldMethod" src/`

### Step 3: Update Changed Signatures / 변경된 시그니처 갱신
- 시그니처가 변경된 API의 호출부를 수정합니다.

### Step 4: Verify / 검증
- 전체 테스트 실행: `pytest tests/ -v`
- API 호환성 검증: `_sdacs.version()` 으로 버전 확인

## Deprecated APIs Removed in This Version / 이번 버전에서 제거된 사용 중단 API

| API | Deprecated Since / 사용 중단 시점 | Replacement / 대체 API |
|-----|-----------------------------------|------------------------|
| (해당 API 목록) | v{X.Y.0} | (대체 API 경로) |

## Compatibility Notes / 호환성 참고 사항

- 이전 버전의 저장 데이터(시나리오, 설정 파일 등)와의 호환성 여부를 기술합니다.
- Python 코어(`pyproject.toml`)와 Electron 앱(`package.json`) 간 버전 동기화를 확인합니다.
```

---

## 10. Alignment with Phase 209 Deprecation Policy / Phase 209 사용 중단 정책과의 연계

본 정책은 TRANSCENDENCE Phase 209에서 정의하는 사용 중단(Deprecation) 정책과 밀접하게 연계됩니다.

This policy is tightly aligned with the Deprecation Policy defined in TRANSCENDENCE Phase 209.

### 10.1 Deprecation-to-Removal Lifecycle / 사용 중단에서 제거까지의 생명 주기

```
v1.5.0  API가 deprecated 표시 (MINOR 범프)
  │
  ├── v1.6.0  경고 메시지 활성화, 대체 API 안내
  │
  ├── v1.7.0  최소 유예 기간 (2 마이너 릴리스) 경과
  │
  └── v2.0.0  API 최종 제거 (MAJOR 범프)
```

### 10.2 Rules / 규칙

| Rule / 규칙 | Description / 설명 |
|---|---|
| **사용 중단 표시 = MINOR** | Production API에 `@deprecated` 표시를 추가하는 것은 MINOR 범프입니다. |
| **최소 유예 기간** | 사용 중단 표시 후 최소 2회의 마이너 릴리스(약 6개월)가 경과해야 제거할 수 있습니다. |
| **제거 = MAJOR** | 사용 중단된 API의 최종 제거는 반드시 MAJOR 범프와 함께 수행합니다. |
| **런타임 경고** | 사용 중단된 API 호출 시 콘솔에 경고 메시지를 출력합니다. |
| **마이그레이션 가이드 필수** | API 제거 시 Section 9의 템플릿에 따라 마이그레이션 가이드를 함께 제공합니다. |

### 10.3 Deprecation Notice Format / 사용 중단 공지 형식

```javascript
/**
 * @deprecated since v1.5.0 — Use _sdacs.airspace.queryV2() instead.
 *   Will be removed in v2.0.0.
 *   See: docs/migration/v1-to-v2.md
 */
_sdacs.airspace.query = function(type) {
  console.warn(
    '[SDACS] _sdacs.airspace.query() is deprecated since v1.5.0. ' +
    'Use _sdacs.airspace.queryV2() instead. ' +
    'This API will be removed in v2.0.0.'
  );
  // ... 기존 구현
};
```

---

## Appendix A: Version Decision Flowchart / 부록 A: 버전 결정 플로차트

```
                    변경 사항 발생
                         │
                         ▼
              Production API에 영향?
                    │          │
                   Yes         No
                    │          │
                    ▼          ▼
             하위 호환?    Beta API에 영향?
              │      │       │         │
             Yes     No     Yes        No
              │      │       │         │
              ▼      ▼       ▼         ▼
           MINOR   MAJOR   MINOR   Mock/Speculative만?
                                      │         │
                                     Yes        No
                                      │         │
                                      ▼         ▼
                                    PATCH     PATCH
```

---

## Appendix B: Quick Reference / 부록 B: 빠른 참조

| I want to... / 하고 싶은 작업 | Version Bump / 버전 범프 |
|---|---|
| Production API 시그니처 변경 | **MAJOR** |
| Deprecated Production API 제거 | **MAJOR** |
| 새 Production API 추가 | **MINOR** |
| 새 Beta API 추가 | **MINOR** |
| Mock을 Beta로 승격 | **MINOR** |
| Production API에 선택적 매개변수 추가 | **MINOR** |
| Production API에 deprecated 표시 | **MINOR** |
| Production API 버그 수정 | **PATCH** |
| Speculative API 추가/변경/제거 | **PATCH** |
| Mock API 내부 변경 | **PATCH** |
| 문서 수정 | **PATCH** |
| 테스트 추가 | **PATCH** |
| CI/빌드 설정 변경 | **PATCH** |

---

*본 정책은 SemVer 2.0.0 (https://semver.org) 규격을 기반으로 하며, SDACS 프로젝트의 API 성숙도 체계에 맞게 확장한 것입니다.*

*This policy is based on the SemVer 2.0.0 specification (https://semver.org), extended to fit the SDACS API maturity framework.*

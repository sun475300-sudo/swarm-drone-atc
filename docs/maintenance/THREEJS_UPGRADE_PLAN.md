# 🎨 SDACS Three.js 메이저 업그레이드 리허설 (Phase 483)

*ODYSSEY Track ♾️ Continuum — Phase 483 산출물*
*Created: 2026-06-25 · 현 r162 → 최신 호환 셰임*

## 1. 현황

SDACS 시뮬레이터는 **Three.js r162** 사용 (`docs/vendor/three/three.module.js` 동봉).

### 1.1 현재 사용 API

| API | 위치 | 영향 |
|---|---|---|
| `THREE.Scene` | 기본 씬 그래프 | 안정 |
| `THREE.WebGLRenderer` | 렌더링 | r155+ Lighting 변경 |
| `THREE.InstancedMesh` | 대규모 군집 (1K+) | r140+ 안정 |
| `THREE.PerspectiveCamera` + `OrbitControls` | 카메라 | 안정 |
| `THREE.BufferGeometry` | 메시 데이터 | 안정 |
| `THREE.MeshStandardMaterial` | PBR 재질 | r155+ Lighting 영향 |
| `THREE.AmbientLight` + `THREE.DirectionalLight` | 조명 | r155+ 변경 |
| `THREE.Group` | 드론 컨테이너 | 안정 |
| `THREE.Line` + `THREE.LineBasicMaterial` | 근접선 풀 | 안정 |

### 1.2 알려진 deprecation (r162 시점)

```
WebGLRenderer.useLegacyLights deprecated (r155+)
  → 마이그레이션 가이드: https://discourse.threejs.org/t/updates-to-lighting-in-three-js-r155/53733
```

본 deprecation 은 시뮬레이터에 영향 (조명 강도 자동 변환).

---

## 2. r163 → r170 변경 사항 (요약)

| 버전 | 주요 변경 |
|---|---|
| **r163** | `WebGPURenderer` 안정화 진행 |
| **r164** | BufferGeometryUtils 신규 메서드 (mergeAttributes 등) |
| **r165** | `Renderer` 추상 베이스 (WebGL/WebGPU 통합) |
| **r166** | `ColorManagement` 기본 활성 (sRGB 명시 권장) |
| **r167** | `ShaderMaterial` glsl3 기본 |
| **r168** | `MeshPhysicalMaterial` clearcoat 개선 |
| **r169** | `Three.js TSL` (Three.js Shading Language) 도입 |
| **r170** | `WebGPURenderer` 정식 (현재 진행 중) |

---

## 3. 리허설 절차 (Dry-Run)

### 3.1 단계별 업그레이드 (r162 → r170)

```
Step 1: r162 → r164 (마이너 1단계)
  - useLegacyLights deprecation 제거 (조명 강도 정규화)
  - 4 사본 md5 일치 + API 게이트 통과 확인
  - 회귀: replay_cursor·smoke_sim·E2E 전체

Step 2: r164 → r166 (마이너 2단계)
  - ColorManagement = true 명시 (`renderer.outputColorSpace = THREE.SRGBColorSpace`)
  - 색상 정합성 시각 비교 (스크린샷 diff)

Step 3: r166 → r168 (마이너 3단계)
  - ShaderMaterial glsl3 마이그레이션 (현재 사용 없음 — 영향 없음)
  - Material clearcoat 옵션 (현재 사용 없음)

Step 4: r168 → r170 (메이저)
  - WebGPURenderer 옵트인 시도 (기존 WebGL 유지 + canary 검증)
  - 4 사본 동기화 + 헤드리스 검증
```

### 3.2 호환 셰임 패턴

```javascript
// Three.js r155+ useLegacyLights 호환 셰임
function configureRenderer(renderer, options = {}) {
  // 신 API (r155+)
  if ('useLegacyLights' in renderer) {
    // r155-r169: deprecated property
    renderer.useLegacyLights = false;
  }
  // r166+: ColorManagement 명시
  if (THREE.ColorManagement) {
    THREE.ColorManagement.enabled = true;
  }
  // r166+: outputColorSpace (이전 outputEncoding 대체)
  if ('outputColorSpace' in renderer) {
    renderer.outputColorSpace = THREE.SRGBColorSpace;
  } else if ('outputEncoding' in renderer) {
    renderer.outputEncoding = THREE.sRGBEncoding;  // r163-
  }
  return renderer;
}
```

---

## 4. 호환성 회귀 매트릭스

각 업그레이드 단계에서 자동 검증:

| 게이트 | 명령 | 합격 기준 |
|---|---|---|
| JS 구문 | `node --check /tmp/sim.mjs` | 0 syntax error |
| 4 사본 md5 | `md5sum sim*.html \| sort -u` | 단일 hash |
| 헤드리스 부팅 | `playwright launch + waitForFunction droneCount > 0` | 30s 내 |
| replay_cursor | `pytest tests/e2e/test_simulator_replay_cursor.py` | 6/6 PASS |
| smoke_sim | `node tests/e2e/smoke_sim.mjs` | 모든 단계 PASS |
| mega_swarm_1k | smoke_sim 섹션 8b' | DC ≤ 800 · cpuMs ≤ 8.0 |
| 브라우저 API 카나리 | `python scripts/browser_api_canary.py --check` | exit 0 |

---

## 5. WebGPURenderer 마이그레이션 (r170+ 미래)

### 5.1 현재 SDACS WebGPU 사용

- **APF 힘 계산** GPU 가속 (`_gpuDevice`, `dispatchGpuCompute`) — **이미 사용**
- **렌더링**: WebGLRenderer (Three.js) — **현재**

### 5.2 r170+ WebGPURenderer 옵트인

```javascript
// 카나리 코드 (옵트인 — 기본은 WebGL 유지)
async function createRenderer() {
  // r170+ WebGPU 시도
  if (window.GPU && THREE.WebGPURenderer) {
    try {
      const renderer = new THREE.WebGPURenderer({ antialias: true });
      await renderer.init();
      console.log('[SDACS] Three.js WebGPURenderer 활성');
      return renderer;
    } catch (e) {
      console.warn('[SDACS] WebGPURenderer 실패, WebGL 폴백:', e);
    }
  }
  return new THREE.WebGLRenderer({ antialias: true });
}
```

**가치**: APF GPU compute + 렌더링 GPU 의 **단일 디바이스 통합** → 데이터 전송 비용 감소.
**위험**: WebGPURenderer 안정화 시점 (r172+ 추정) 까지 보류.

---

## 6. 업그레이드 일정 (제안)

| 시점 | Three.js | 사유 |
|---|---|---|
| **현재** | r162 | 안정·검증 완료 |
| 2026-Q4 | r164 (1단계 마이너) | useLegacyLights 제거 |
| 2027-Q1 | r166 (2단계 마이너) | ColorManagement 명시 |
| 2027-Q2 | r168 (3단계 마이너) | 안정성 점검 |
| 2027-Q3 | r170 (메이저) | WebGPURenderer 안정화 (조건부) |
| 2027-Q4+ | 분기마다 1 단계 | 점진 + 보안 패치 흡수 |

**제약**: 시각적 회귀 (스크린샷 diff) 는 사용자 검증 의존 (헤드리스 SwiftShader 와 실 GPU 차이 가능).

---

## 7. 롤백 절차

업그레이드 후 회귀 발견 시:

1. **즉시**: `git revert <upgrade-commit>`
2. 4 사본 md5 재계산
3. 회귀 게이트 재확인
4. upstream issue 보고 (Three.js GitHub)
5. workaround 패치 또는 다음 마이너 대기

---

## 8. 한계 (정직성 공시)

- 본 리허설은 *문서 + 호환 셰임 패턴* 만 정의 — 실 업그레이드는 별도 PR.
- 시각 회귀는 헤드리스에서 부분 검증 (SwiftShader 한계).
- WebGPURenderer 는 r170+ 안정화 시점까지 옵트인만 (필수 아님).
- `docs/vendor/three/` 의 ~55,000 LOC 는 1회성 업그레이드마다 갱신 필요 (저장소 무게 증가 — 다음 마이너 시 git LFS 검토 후보).

---

## 9. 참조

- Three.js Releases: <https://github.com/mrdoob/three.js/releases>
- r155 Lighting Migration: <https://discourse.threejs.org/t/updates-to-lighting-in-three-js-r155/53733>
- WebGPURenderer Status: <https://github.com/mrdoob/three.js/wiki/WebGPURenderer>
- `swarm_3d_simulator.html` line 1599 importmap (`./vendor/three/three.module.js`)
- `docs/CONTINUUM_ELECTRON_LTS_TRACKING.md` — Phase 484 (Electron 마이너 사이클 정합)
- `scripts/browser_api_canary.py` — Phase 482 (브라우저 API 카나리)
- `docs/SIMULATOR_ODYSSEY_PLAN.md` Track ♾️ — Phase 481-500

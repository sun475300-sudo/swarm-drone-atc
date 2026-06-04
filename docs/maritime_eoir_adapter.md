# Maritime EO/IR Adapter Pattern (P735)

`maritime_detection_simulator.html`의 C3 EO/IR 카메라 뷰에 실 카메라 SDK를 연동하기 위한 어댑터 패턴.

## 개요

기존 `drawEOIR()`는 합성(`synth`) 프레임만 그렸으나, P735에서 **소스 레지스트리**를 도입하여 외부 SDK(FLIR, Hikvision, Axis 등) 영상 스트림을 주입할 수 있도록 함.

```
synth (default) ──┐
                  ├─ eoirSources[]  ──→  drawEOIR() dispatcher
mock-sdk ─────────┤
                  │
your-sdk ─────────┘
```

## 인터페이스

### 등록

```js
window._mds.registerEOIRSource('your-sdk', (ctx, w, h, info) => {
    // ctx: 2D rendering context (캔버스 240×150)
    // w, h: 캔버스 크기
    // info: {
    //   eoMode: 'EO' | 'IR',
    //   vessel: { id, wx, wz, vx, vz, type, classified, cpaWarn, ... },
    //   NM: 1NM의 픽셀 단위
    //   distNM: 표적까지 거리(NM)
    //   speedKn: 표적 속도(노트)
    //   sourceLabel: 현재 활성 소스명
    // }

    // 예시: SDK 프레임 ImageBitmap을 캔버스에 그리기
    const frame = await yourSdk.latestFrame(info.eoMode);
    ctx.drawImage(frame, 0, 0, w, h);

    // 오버레이는 직접 추가
    ctx.font = '9px JetBrains Mono'; ctx.fillStyle = '#0fb';
    ctx.fillText(`${info.eoMode}  ${info.vessel.id}`, 6, 13);
});
```

### 전환

```js
window._mds.selectEOIRSource('your-sdk');  // 활성화 (null 반환 시 미존재)
window._mds.selectEOIRSource('synth');     // 기본 합성으로 복귀
```

### 조회

```js
window._mds.eoirSource;    // 현재 활성 소스명 (예: 'your-sdk')
window._mds.eoirSources;   // 등록된 모든 소스 ['synth', 'mock-sdk', 'your-sdk']
```

## 안전망

- handler가 `throw`하면 자동 `console.warn` + `synth` fallback → 화면이 빈 검정으로 가지 않음
- 등록 시 `typeof handler === 'function'` 검사

## 구현 예시 — Mock SDK (테스트 용)

```js
window._mds.registerEOIRSource('mock-sdk', (ctx, w, h, info) => {
    ctx.fillStyle = info.eoMode === 'EO' ? '#1a4a6e' : '#5a0f3d';
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = '#fff'; ctx.font = '11px sans-serif';
    ctx.fillText(`MOCK-SDK ${info.eoMode}`, 8, 18);
    ctx.fillText(info.vessel.id, w - 50, 18);
});
window._mds.selectEOIRSource('mock-sdk');
```

## 실 SDK 연동 가이드 (예: FLIR Boson)

1. FLIR Boson SDK Web bridge 또는 WebSocket으로 프레임 스트리밍 수신
2. `OffscreenCanvas`에 디코딩
3. handler 안에서 `ctx.drawImage(offscreen, 0, 0, w, h)` 로 합성
4. 거리·CPA 오버레이는 `info`에서 직접 그리기 (SDK는 raw 영상만 제공)

## 검증 (CI/headless)

`tests/e2e/smoke_maritime.mjs`에서 다음 시나리오 권장:
- `registerEOIRSource('test', handler)` 등록 후 `selectEOIRSource('test')` → 캔버스 픽셀 검증
- 잘못된 source 선택 → null 반환 확인
- 실패하는 source 등록 + 선택 → synth fallback 확인

## 한계

- 현재 240×150 픽셀 고정 — 고해상도 영상은 다운샘플 필요
- WebGL 영상 가속 미지원 — 2D 컨텍스트만 사용
- 향후: WebRTC 직접 연결로 실시간 영상 60fps 가능 (`MediaStreamTrack` → canvas)

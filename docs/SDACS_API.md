# 📚 `window._sdacs` API 레퍼런스

*자동 생성: 2026-06-05 — `swarm_3d_simulator.html` v1.1.0*

**전체 항목 수: 92개** (Phase 0-9 통합)

---

## 📋 Phase별 분류

### Phase 0 — 코어

| Kind | Name | Signature |
|---|---|---|
| `get` | **`stats`** | `get stats() { return { ...stats }; },` |
| `get` | **`simTime`** | `get simTime() { return simTime; },` |
| `get` | **`simRunning`** | `get simRunning() { return simRunning; },` |
| `get` | **`droneCount`** | `get droneCount() { return drones.length; },` |
| `get` | **`weather`** | `get weather() { return { icing: weather.icing, microbursts: weather.microbursts.length, stormCells: weather.stormCells.length, typhoonWind: weather.typhoonWind, turbulence: weather.turbulence, windSpd` |
| `get` | **`airborne`** | `get airborne() { return drones.filter(d => d.phase !== 'GROUNDED' && d.phase !== 'FAILED').length; },` |
| `get` | **`failed`** | `get failed() { return drones.filter(d => d.phase === 'FAILED').length; },` |
| `get` | **`landed`** | `get landed() { return drones.filter(d => d.phase === 'GROUNDED').length; },` |
| `method` | **`startSim`** | `startSim() { simRunning = true; },` |
| `method` | **`stopSim`** | `stopSim() { simRunning = false; },` |
| `get` | **`lang`** | `get lang() { return currentLang; },` |
| `method` | **`setLang`** | `setLang(lang) { setLang(lang); return currentLang; },` |
| `method` | **`selectScenario`** | `selectScenario(name) { document.getElementById('scenario-select').value = name; document.getElementById('scenario-select').dispatchEvent(new Event('change')); },` |
| `method` | **`captureScreenshot`** | `captureScreenshot() { renderer.render(scene, camera); return renderer.domElement.toDataURL('image/png'); },` |

### Phase 0 — 선택·호버

| Kind | Name | Signature |
|---|---|---|
| `method` | **`selectDrone`** | `selectDrone(idOrIndex) { const d = selectDrone(idOrIndex); return d ? d.id : null; },` |
| `method` | **`deselectDrone`** | `deselectDrone() { deselectDrone(); },` |
| `method` | **`multiSelect`** | `multiSelect(ids) { for (const id of ids) { const d = drones.find(x => x.id === id) \|\| drones[id]; if (d) multiSel.add(d); } updateMultiPanel(); return multiSel.size; }, // B4` |
| `method` | **`clearMulti`** | `clearMulti() { clearMulti(); },` |
| `get` | **`multiSelection`** | `get multiSelection() { return [...multiSel].map(d => d.id); },` |
| `method` | **`getSelected`** | `getSelected() { return selectedDrone ? { ...selectedDrone, group: undefined, body: undefined, rotor: undefined, glow: undefined } : null; },` |
| `method` | **`hoverDrone`** | `hoverDrone(idOrIndex) { let d = idOrIndex; if (typeof idOrIndex === 'string') d = drones.find(x => x.id === idOrIndex); else if (typeof idOrIndex === 'number') d = drones[idOrIndex]; setHover(d); retu` |
| `method` | **`clearHover`** | `clearHover() { setHover(null); },` |
| `method` | **`focusDrone`** | `focusDrone(idOrIndex) { let d = idOrIndex; if (typeof idOrIndex === 'string') d = drones.find(x => x.id === idOrIndex); else if (typeof idOrIndex === 'number') d = drones[idOrIndex]; if (d) focusDrone` |

### Phase 0 — 분석·리플레이

| Kind | Name | Signature |
|---|---|---|
| `method` | **`setAnalysisView`** | `setAnalysisView(on) { toggleAnalysis(!!on); return analysisMode; },` |
| `get` | **`analysisMode`** | `get analysisMode() { return analysisMode; },` |
| `method-async` | **`reportDataURL`** | `async reportDataURL() { return (await buildReportCanvas()).toDataURL('image/png'); },` |
| `get` | **`replayFrames`** | `get replayFrames() { return recorder.frames.length; },` |
| `method` | **`replaySeek`** | `replaySeek(idx) { enterReplay(); replayIdx = Math.max(0, Math.min(idx, recorder.frames.length - 1)); applyFrame(replayIdx); return replayIdx; },` |
| `ref` | **`goLive`** | `goLive,` |
| `get` | **`replay`** | `get replay() {` |
| `method` | **`replayStep`** | `replayStep(delta = 1) {` |

### Phase 0 — 메가/성능

| Kind | Name | Signature |
|---|---|---|
| `get` | **`megaMode`** | `get megaMode() { return megaMode; },` |
| `get` | **`instanceCount`** | `get instanceCount() { return bodyInst.count; },` |
| `get` | **`visibleInstances`** | `get visibleInstances() { return _visibleInst; },` |
| `get` | **`perf`** | `get perf() { return { fps: perfMetrics.fps, cpuMs: +perfMetrics.cpuMs.toFixed(2), gpuMs: +perfMetrics.gpuMs.toFixed(2), drawCalls: perfMetrics.drawCalls, triangles: perfMetrics.triangles, drones: dron` |
| `set` | **`megaCull`** | `set megaCull(v) { megaCull = !!v; },` |
| `get` | **`megaCull`** | `get megaCull() { return megaCull; },` |
| `get` | **`dni`** | `get dni() { return { ...dniStats, objects: externalObjs.length }; },` |

### Phase 0 — 라이브/WS

| Kind | Name | Signature |
|---|---|---|
| `get` | **`wsConnected`** | `get wsConnected() { return _wsConnected; },` |
| `get` | **`wsFrames`** | `get wsFrames() { return _wsFrames; },` |
| `get` | **`liveMode`** | `get liveMode() { return _wsConnected && _wsData != null; },` |

### Phase 0 — 레이어

| Kind | Name | Signature |
|---|---|---|
| `method` | **`setLayer`** | `setLayer(name, on) {` |
| `get` | **`layers`** | `get layers() { return { ...layerVisibility }; },` |
| `get` | **`conflictPairs`** | `get conflictPairs() { return _cvLineIdx; },` |

### Phase 1 — ATC 콘솔

| Kind | Name | Signature |
|---|---|---|
| `method` | **`atcCommand`** | `atcCommand(did, cmd, params, source) { return window.atcCommand(did, cmd, params, source); },` |
| `get` | **`atcLog`** | `get atcLog() { return atcLog.slice(); },` |
| `get` | **`atcControlled`** | `get atcControlled() { return drones.filter(d => d.atc && d.atc.cmd).map(d => ({ id: d.id, cmd: d.atc.cmd, lockUntil: d.atc.lockUntil })); },` |
| `method` | **`setAtcAudio`** | `setAtcAudio(on) {` |
| `get` | **`atcAudio`** | `get atcAudio() { return atcAudioEnabled; },` |
| `method` | **`clearAllAtc`** | `clearAllAtc() { let n = 0; for (const d of drones) { if (d.atc && d.atc.cmd) { window.atcCommand(d, 'CLEAR'); n++; } } return n; },` |

### Phase 2 — TAC 전술 시각화

| Kind | Name | Signature |
|---|---|---|
| `method` | **`setPredTrail`** | `setPredTrail(on) { _predTrailEnabled = !!on; const e = document.getElementById('tg-pred-trail'); if (e) e.checked = _predTrailEnabled; return _predTrailEnabled; },` |
| `get` | **`predTrail`** | `get predTrail() { return _predTrailEnabled; },` |
| `method` | **`setPredHorizon`** | `setPredHorizon(s) { _predHorizon = Math.max(2, Math.min(20, +s)); return _predHorizon; },` |
| `get` | **`predHorizon`** | `get predHorizon() { return _predHorizon; },` |
| `method` | **`setVelArrow`** | `setVelArrow(on) { _velArrowEnabled = !!on; const e = document.getElementById('tg-vel-arrow'); if (e) e.checked = _velArrowEnabled; return _velArrowEnabled; },` |
| `get` | **`velArrow`** | `get velArrow() { return _velArrowEnabled; },` |
| `method` | **`setCpaMarker`** | `setCpaMarker(on) { _cpaMarkerEnabled = !!on; const e = document.getElementById('tg-cpa-marker'); if (e) e.checked = _cpaMarkerEnabled; return _cpaMarkerEnabled; },` |
| `get` | **`cpaMarker`** | `get cpaMarker() { return _cpaMarkerEnabled; },` |
| `get` | **`cpaPairsCount`** | `get cpaPairsCount() { return _cpaMarkerIdx; },` |

### Phase 3 — CIN 시네마틱

| Kind | Name | Signature |
|---|---|---|
| `method` | **`setSunCycle`** | `setSunCycle(on) { sunCycle.enabled = !!on; const e = document.getElementById('tg-sun-cycle'); if (e) e.checked = sunCycle.enabled; return sunCycle.enabled; },` |
| `method` | **`setSunHour`** | `setSunHour(h) { sunCycle.hour = Math.max(0, Math.min(24, +h)); const sl = document.getElementById('sun-hour'); if (sl) sl.value = sunCycle.hour; return sunCycle.hour; },` |
| `method` | **`setSunAuto`** | `setSunAuto(on) { sunCycle.auto = !!on; if (sunCycle.auto) sunCycle.enabled = true; return sunCycle.auto; },` |
| `get` | **`sunHour`** | `get sunHour() { return sunCycle.hour; },` |
| `get` | **`sunEnabled`** | `get sunEnabled() { return sunCycle.enabled; },` |
| `method` | **`setRain`** | `setRain(on, intensity) { cinParticles.rain.enabled = !!on; if (intensity != null) cinParticles.rain.intensity = Math.max(0, Math.min(1, intensity)); const e = document.getElementById('tg-rain'); if (e` |
| `method` | **`setSnow`** | `setSnow(on, intensity) { cinParticles.snow.enabled = !!on; if (intensity != null) cinParticles.snow.intensity = Math.max(0, Math.min(1, intensity)); const e = document.getElementById('tg-snow'); if (e` |
| `method` | **`startRecording`** | `startRecording() { return startRecording(); },` |
| `method` | **`stopRecording`** | `stopRecording() { return stopRecording(); },` |
| `get` | **`recording`** | `get recording() { return cinRecorder.recording; },` |

### Phase 4 — CAM 카메라

| Kind | Name | Signature |
|---|---|---|
| `method` | **`setCamMode`** | `setCamMode(mode) { setCamMode(mode); return camMode; },` |
| `get` | **`camMode`** | `get camMode() { return camMode; },` |

### Phase 5 — MIS 임무

| Kind | Name | Signature |
|---|---|---|
| `method` | **`missionAdd`** | `missionAdd(droneId, waypoints, templateName) { return missionAdd(droneId, waypoints, templateName); },` |
| `method` | **`missionTemplate`** | `missionTemplate(name, originX, originZ) { return _missionGenerateTemplate(name, originX \|\| 0, originZ \|\| 0); },` |
| `method` | **`missionAssignTemplate`** | `missionAssignTemplate(droneId, templateName) {` |
| `method` | **`missionClearAll`** | `missionClearAll() { missionClearAll(); return missions.length; },` |
| `get` | **`missions`** | `get missions() { return missions.map(m => ({ id: m.id, droneId: m.droneId, wpCount: m.waypoints.length, currentIdx: m.currentIdx, completion: m.completion, template: m.template })); },` |

### Phase 6 — INJ 장애 주입

| Kind | Name | Signature |
|---|---|---|
| `method` | **`injectFault`** | `injectFault(droneId, type, opts) { return injectFault(droneId, type, opts); },` |
| `method` | **`injectRogue`** | `injectRogue() { return injectRogue(); },` |
| `method` | **`injectDynamicNFZ`** | `injectDynamicNFZ(x, z, r, dur) { return injectDynamicNFZ(x, z, r, dur); },` |
| `method` | **`injectScenario`** | `injectScenario(name) { return injectScenario(name); },` |
| `method` | **`injClearAll`** | `injClearAll() { return injClearAll(); },` |
| `get` | **`injStats`** | `get injStats() { return { ...injStats }; },` |
| `get` | **`dynamicNfzList`** | `get dynamicNfzList() { return _dynNfzList.slice(); },` |

### Phase 7 — ANA 분석 강화

| Kind | Name | Signature |
|---|---|---|
| `method` | **`setAnaHeatmap`** | `setAnaHeatmap(on) { anaHeatmap.enabled = !!on; const e = document.getElementById('tg-ana-heatmap'); if (e) e.checked = anaHeatmap.enabled; return anaHeatmap.enabled; },` |
| `get` | **`anaHeatmap`** | `get anaHeatmap() { return anaHeatmap.enabled; },` |
| `get` | **`anaKpiWindow`** | `get anaKpiWindow() { return { time: anaKpiWindow.time.slice(), cr: anaKpiWindow.cr.slice(), avgBat: anaKpiWindow.avgBat.slice(), fps: anaKpiWindow.fps.slice() }; },` |
| `method` | **`exportLatexKpi`** | `exportLatexKpi() { return exportLatexKpi(); },` |

### Phase 8 — AUD 환경 사운드

| Kind | Name | Signature |
|---|---|---|
| `method` | **`setAmbientAudio`** | `setAmbientAudio(on) { audAmbient.enabled = !!on; const b = document.getElementById('btn-aud-ambient'); if (b) { b.classList.toggle('off', !audAmbient.enabled); b.textContent = audAmbient.enabled ? '🌬 ` |
| `get` | **`ambientAudio`** | `get ambientAudio() { return audAmbient.enabled; },` |

### Phase 9 — MOB 모바일/PWA

| Kind | Name | Signature |
|---|---|---|
| `get` | **`isMobile`** | `get isMobile() { return mobConfig.isMobile; },` |
| `get` | **`mobileLOD`** | `get mobileLOD() { return mobConfig.autoLOD; },` |
| `method` | **`applyMobileLOD`** | `applyMobileLOD() { applyMobileLOD(); return mobConfig.autoLOD; },` |

## 🔎 전체 알파벳순

| Kind | Name | Signature |
|---|---|---|
| `get` | **`airborne`** | `get airborne() { return drones.filter(d => d.phase !== 'GROUNDED' && d.phase !== 'FAILED').length; },` |
| `get` | **`ambientAudio`** | `get ambientAudio() { return audAmbient.enabled; },` |
| `get` | **`anaHeatmap`** | `get anaHeatmap() { return anaHeatmap.enabled; },` |
| `get` | **`anaKpiWindow`** | `get anaKpiWindow() { return { time: anaKpiWindow.time.slice(), cr: anaKpiWindow.cr.slice(), avgBat: anaKpiWindow.avgBat.slice(), fps: anaKpiWindow.fps.slice() }; },` |
| `get` | **`analysisMode`** | `get analysisMode() { return analysisMode; },` |
| `method` | **`applyMobileLOD`** | `applyMobileLOD() { applyMobileLOD(); return mobConfig.autoLOD; },` |
| `get` | **`atcAudio`** | `get atcAudio() { return atcAudioEnabled; },` |
| `method` | **`atcCommand`** | `atcCommand(did, cmd, params, source) { return window.atcCommand(did, cmd, params, source); },` |
| `get` | **`atcControlled`** | `get atcControlled() { return drones.filter(d => d.atc && d.atc.cmd).map(d => ({ id: d.id, cmd: d.atc.cmd, lockUntil: d.atc.lockUntil })); },` |
| `get` | **`atcLog`** | `get atcLog() { return atcLog.slice(); },` |
| `get` | **`camMode`** | `get camMode() { return camMode; },` |
| `method` | **`captureScreenshot`** | `captureScreenshot() { renderer.render(scene, camera); return renderer.domElement.toDataURL('image/png'); },` |
| `method` | **`clearAllAtc`** | `clearAllAtc() { let n = 0; for (const d of drones) { if (d.atc && d.atc.cmd) { window.atcCommand(d, 'CLEAR'); n++; } } return n; },` |
| `method` | **`clearHover`** | `clearHover() { setHover(null); },` |
| `method` | **`clearMulti`** | `clearMulti() { clearMulti(); },` |
| `get` | **`conflictPairs`** | `get conflictPairs() { return _cvLineIdx; },` |
| `get` | **`cpaMarker`** | `get cpaMarker() { return _cpaMarkerEnabled; },` |
| `get` | **`cpaPairsCount`** | `get cpaPairsCount() { return _cpaMarkerIdx; },` |
| `method` | **`deselectDrone`** | `deselectDrone() { deselectDrone(); },` |
| `get` | **`dni`** | `get dni() { return { ...dniStats, objects: externalObjs.length }; },` |
| `get` | **`droneCount`** | `get droneCount() { return drones.length; },` |
| `get` | **`dynamicNfzList`** | `get dynamicNfzList() { return _dynNfzList.slice(); },` |
| `method` | **`exportLatexKpi`** | `exportLatexKpi() { return exportLatexKpi(); },` |
| `get` | **`failed`** | `get failed() { return drones.filter(d => d.phase === 'FAILED').length; },` |
| `method` | **`focusDrone`** | `focusDrone(idOrIndex) { let d = idOrIndex; if (typeof idOrIndex === 'string') d = drones.find(x => x.id === idOrIndex); else if (typeof idOrIndex === 'number') d = drones[idOrIndex]; if (d) focusDrone` |
| `method` | **`getSelected`** | `getSelected() { return selectedDrone ? { ...selectedDrone, group: undefined, body: undefined, rotor: undefined, glow: undefined } : null; },` |
| `ref` | **`goLive`** | `goLive,` |
| `method` | **`hoverDrone`** | `hoverDrone(idOrIndex) { let d = idOrIndex; if (typeof idOrIndex === 'string') d = drones.find(x => x.id === idOrIndex); else if (typeof idOrIndex === 'number') d = drones[idOrIndex]; setHover(d); retu` |
| `method` | **`injClearAll`** | `injClearAll() { return injClearAll(); },` |
| `method` | **`injectDynamicNFZ`** | `injectDynamicNFZ(x, z, r, dur) { return injectDynamicNFZ(x, z, r, dur); },` |
| `method` | **`injectFault`** | `injectFault(droneId, type, opts) { return injectFault(droneId, type, opts); },` |
| `method` | **`injectRogue`** | `injectRogue() { return injectRogue(); },` |
| `method` | **`injectScenario`** | `injectScenario(name) { return injectScenario(name); },` |
| `get` | **`injStats`** | `get injStats() { return { ...injStats }; },` |
| `get` | **`instanceCount`** | `get instanceCount() { return bodyInst.count; },` |
| `get` | **`isMobile`** | `get isMobile() { return mobConfig.isMobile; },` |
| `get` | **`landed`** | `get landed() { return drones.filter(d => d.phase === 'GROUNDED').length; },` |
| `get` | **`lang`** | `get lang() { return currentLang; },` |
| `get` | **`layers`** | `get layers() { return { ...layerVisibility }; },` |
| `get` | **`liveMode`** | `get liveMode() { return _wsConnected && _wsData != null; },` |
| `set` | **`megaCull`** | `set megaCull(v) { megaCull = !!v; },` |
| `get` | **`megaCull`** | `get megaCull() { return megaCull; },` |
| `get` | **`megaMode`** | `get megaMode() { return megaMode; },` |
| `method` | **`missionAdd`** | `missionAdd(droneId, waypoints, templateName) { return missionAdd(droneId, waypoints, templateName); },` |
| `method` | **`missionAssignTemplate`** | `missionAssignTemplate(droneId, templateName) {` |
| `method` | **`missionClearAll`** | `missionClearAll() { missionClearAll(); return missions.length; },` |
| `get` | **`missions`** | `get missions() { return missions.map(m => ({ id: m.id, droneId: m.droneId, wpCount: m.waypoints.length, currentIdx: m.currentIdx, completion: m.completion, template: m.template })); },` |
| `method` | **`missionTemplate`** | `missionTemplate(name, originX, originZ) { return _missionGenerateTemplate(name, originX \|\| 0, originZ \|\| 0); },` |
| `get` | **`mobileLOD`** | `get mobileLOD() { return mobConfig.autoLOD; },` |
| `method` | **`multiSelect`** | `multiSelect(ids) { for (const id of ids) { const d = drones.find(x => x.id === id) \|\| drones[id]; if (d) multiSel.add(d); } updateMultiPanel(); return multiSel.size; }, // B4` |
| `get` | **`multiSelection`** | `get multiSelection() { return [...multiSel].map(d => d.id); },` |
| `get` | **`perf`** | `get perf() { return { fps: perfMetrics.fps, cpuMs: +perfMetrics.cpuMs.toFixed(2), gpuMs: +perfMetrics.gpuMs.toFixed(2), drawCalls: perfMetrics.drawCalls, triangles: perfMetrics.triangles, drones: dron` |
| `get` | **`predHorizon`** | `get predHorizon() { return _predHorizon; },` |
| `get` | **`predTrail`** | `get predTrail() { return _predTrailEnabled; },` |
| `get` | **`recording`** | `get recording() { return cinRecorder.recording; },` |
| `get` | **`replay`** | `get replay() {` |
| `get` | **`replayFrames`** | `get replayFrames() { return recorder.frames.length; },` |
| `method` | **`replaySeek`** | `replaySeek(idx) { enterReplay(); replayIdx = Math.max(0, Math.min(idx, recorder.frames.length - 1)); applyFrame(replayIdx); return replayIdx; },` |
| `method` | **`replayStep`** | `replayStep(delta = 1) {` |
| `method-async` | **`reportDataURL`** | `async reportDataURL() { return (await buildReportCanvas()).toDataURL('image/png'); },` |
| `method` | **`selectDrone`** | `selectDrone(idOrIndex) { const d = selectDrone(idOrIndex); return d ? d.id : null; },` |
| `method` | **`selectScenario`** | `selectScenario(name) { document.getElementById('scenario-select').value = name; document.getElementById('scenario-select').dispatchEvent(new Event('change')); },` |
| `method` | **`setAmbientAudio`** | `setAmbientAudio(on) { audAmbient.enabled = !!on; const b = document.getElementById('btn-aud-ambient'); if (b) { b.classList.toggle('off', !audAmbient.enabled); b.textContent = audAmbient.enabled ? '🌬 ` |
| `method` | **`setAnaHeatmap`** | `setAnaHeatmap(on) { anaHeatmap.enabled = !!on; const e = document.getElementById('tg-ana-heatmap'); if (e) e.checked = anaHeatmap.enabled; return anaHeatmap.enabled; },` |
| `method` | **`setAnalysisView`** | `setAnalysisView(on) { toggleAnalysis(!!on); return analysisMode; },` |
| `method` | **`setAtcAudio`** | `setAtcAudio(on) {` |
| `method` | **`setCamMode`** | `setCamMode(mode) { setCamMode(mode); return camMode; },` |
| `method` | **`setCpaMarker`** | `setCpaMarker(on) { _cpaMarkerEnabled = !!on; const e = document.getElementById('tg-cpa-marker'); if (e) e.checked = _cpaMarkerEnabled; return _cpaMarkerEnabled; },` |
| `method` | **`setLang`** | `setLang(lang) { setLang(lang); return currentLang; },` |
| `method` | **`setLayer`** | `setLayer(name, on) {` |
| `method` | **`setPredHorizon`** | `setPredHorizon(s) { _predHorizon = Math.max(2, Math.min(20, +s)); return _predHorizon; },` |
| `method` | **`setPredTrail`** | `setPredTrail(on) { _predTrailEnabled = !!on; const e = document.getElementById('tg-pred-trail'); if (e) e.checked = _predTrailEnabled; return _predTrailEnabled; },` |
| `method` | **`setRain`** | `setRain(on, intensity) { cinParticles.rain.enabled = !!on; if (intensity != null) cinParticles.rain.intensity = Math.max(0, Math.min(1, intensity)); const e = document.getElementById('tg-rain'); if (e` |
| `method` | **`setSnow`** | `setSnow(on, intensity) { cinParticles.snow.enabled = !!on; if (intensity != null) cinParticles.snow.intensity = Math.max(0, Math.min(1, intensity)); const e = document.getElementById('tg-snow'); if (e` |
| `method` | **`setSunAuto`** | `setSunAuto(on) { sunCycle.auto = !!on; if (sunCycle.auto) sunCycle.enabled = true; return sunCycle.auto; },` |
| `method` | **`setSunCycle`** | `setSunCycle(on) { sunCycle.enabled = !!on; const e = document.getElementById('tg-sun-cycle'); if (e) e.checked = sunCycle.enabled; return sunCycle.enabled; },` |
| `method` | **`setSunHour`** | `setSunHour(h) { sunCycle.hour = Math.max(0, Math.min(24, +h)); const sl = document.getElementById('sun-hour'); if (sl) sl.value = sunCycle.hour; return sunCycle.hour; },` |
| `method` | **`setVelArrow`** | `setVelArrow(on) { _velArrowEnabled = !!on; const e = document.getElementById('tg-vel-arrow'); if (e) e.checked = _velArrowEnabled; return _velArrowEnabled; },` |
| `get` | **`simRunning`** | `get simRunning() { return simRunning; },` |
| `get` | **`simTime`** | `get simTime() { return simTime; },` |
| `method` | **`startRecording`** | `startRecording() { return startRecording(); },` |
| `method` | **`startSim`** | `startSim() { simRunning = true; },` |
| `get` | **`stats`** | `get stats() { return { ...stats }; },` |
| `method` | **`stopRecording`** | `stopRecording() { return stopRecording(); },` |
| `method` | **`stopSim`** | `stopSim() { simRunning = false; },` |
| `get` | **`sunEnabled`** | `get sunEnabled() { return sunCycle.enabled; },` |
| `get` | **`sunHour`** | `get sunHour() { return sunCycle.hour; },` |
| `get` | **`velArrow`** | `get velArrow() { return _velArrowEnabled; },` |
| `get` | **`visibleInstances`** | `get visibleInstances() { return _visibleInst; },` |
| `get` | **`weather`** | `get weather() { return { icing: weather.icing, microbursts: weather.microbursts.length, stormCells: weather.stormCells.length, typhoonWind: weather.typhoonWind, turbulence: weather.turbulence, windSpd` |
| `get` | **`wsConnected`** | `get wsConnected() { return _wsConnected; },` |
| `get` | **`wsFrames`** | `get wsFrames() { return _wsFrames; },` |

## 🧪 사용 예시

```javascript
// 시뮬 시작 + 첫 드론 선택 + ATC HOLD 명령
window._sdacs.startSim();
const id = window._sdacs.selectDrone(0);
window._sdacs.atcCommand(id, 'HOLD');

// 시네마틱 모드: 동적 태양 + 비 + 녹화 시작
window._sdacs.setSunCycle(true);
window._sdacs.setSunAuto(true);
window._sdacs.setRain(true, 0.7);
window._sdacs.startRecording();

// 임무 5종 템플릿 일괄 할당
['search_grid', 'recon_orbit', 'delivery', 'spray_voronoi', 'medical_heap']
  .forEach((tmpl, i) => window._sdacs.missionAssignTemplate(i, tmpl));

// 장애 시나리오 EMP + LaTeX 표 출력
window._sdacs.injectScenario('EMP');
window._sdacs.exportLatexKpi();
```

## 🔗 관련 문서

- [`SIMULATOR_MEGA_PLAN.md`](SIMULATOR_MEGA_PLAN.md) — Phase 1-9 마스터
- [`SIMULATOR_PHASE_PLANS.md`](SIMULATOR_PHASE_PLANS.md) — 상세 명세
- [`SIMULATOR_HYPER_PLAN.md`](SIMULATOR_HYPER_PLAN.md) — Phase 10-50 미래
- [`RELEASE_GUIDE.md`](RELEASE_GUIDE.md) — 데스크탑 v1.1 빌드 절차

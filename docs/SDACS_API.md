# 📚 `window._sdacs` API 레퍼런스 — MEGA 9 + HYPER 41 = 50 Phase 통합

*자동 생성: 2026-06-05 — `swarm_3d_simulator.html`*

**전체 항목 수: 231개**

---

## Phase 0 — 코어

| Kind | Name | Signature |
|---|---|---|
| `get` | **`stats`** | `get stats() { return { ...stats }; },` |
| `get` | **`simTime`** | `get simTime() { return simTime; },` |
| `get` | **`simRunning`** | `get simRunning() { return simRunning; },` |
| `get` | **`droneCount`** | `get droneCount() { return drones.length; },` |
| `get` | **`weather`** | `get weather() { return { icing: weather.icing, microbursts: weather.microbursts.length, stormCells: weather.stormCells.length, typhoonWind: weather.typhoonWind, turbulence: weather` |
| `get` | **`airborne`** | `get airborne() { return drones.filter(d => d.phase !== 'GROUNDED' && d.phase !== 'FAILED').length; },` |
| `get` | **`failed`** | `get failed() { return drones.filter(d => d.phase === 'FAILED').length; },` |
| `get` | **`landed`** | `get landed() { return drones.filter(d => d.phase === 'GROUNDED').length; },` |
| `method` | **`startSim`** | `startSim() { simRunning = true; },` |
| `method` | **`stopSim`** | `stopSim() { simRunning = false; },` |
| `get` | **`lang`** | `get lang() { return currentLang; },` |
| `method` | **`setLang`** | `setLang(lang) { setLang(lang); return currentLang; },` |
| `get` | **`availableLangs`** | `get availableLangs() { return LANG_ORDER.slice(); },` |
| `method` | **`selectScenario`** | `selectScenario(name) { document.getElementById('scenario-select').value = name; document.getElementById('scenario-select').dispatchEvent(new Event('change')); },` |
| `method` | **`setLayer`** | `setLayer(name, on) {` |
| `get` | **`layers`** | `get layers() { return { ...layerVisibility }; },` |
| `method` | **`captureScreenshot`** | `captureScreenshot() { renderer.render(scene, camera); return renderer.domElement.toDataURL('image/png'); },` |

## Phase 0 — 선택·호버

| Kind | Name | Signature |
|---|---|---|
| `method` | **`selectDrone`** | `selectDrone(idOrIndex) { const d = selectDrone(idOrIndex); return d ? d.id : null; },` |
| `method` | **`deselectDrone`** | `deselectDrone() { deselectDrone(); },` |
| `method` | **`multiSelect`** | `multiSelect(ids) { for (const id of ids) { const d = drones.find(x => x.id === id) \|\| drones[id]; if (d) multiSel.add(d); } updateMultiPanel(); return multiSel.size; }, // B4` |
| `method` | **`clearMulti`** | `clearMulti() { clearMulti(); },` |
| `get` | **`multiSelection`** | `get multiSelection() { return [...multiSel].map(d => d.id); },` |
| `method` | **`getSelected`** | `getSelected() { return selectedDrone ? { ...selectedDrone, group: undefined, body: undefined, rotor: undefined, glow: undefined } : null; },` |
| `method` | **`hoverDrone`** | `hoverDrone(idOrIndex) { let d = idOrIndex; if (typeof idOrIndex === 'string') d = drones.find(x => x.id === idOrIndex); else if (typeof idOrIndex === 'number') d = drones[idOrIndex` |
| `method` | **`clearHover`** | `clearHover() { setHover(null); },` |
| `method` | **`focusDrone`** | `focusDrone(idOrIndex) { let d = idOrIndex; if (typeof idOrIndex === 'string') d = drones.find(x => x.id === idOrIndex); else if (typeof idOrIndex === 'number') d = drones[idOrIndex` |

## Phase 0 — 분석·리플레이

| Kind | Name | Signature |
|---|---|---|
| `method` | **`setAnalysisView`** | `setAnalysisView(on) { toggleAnalysis(!!on); return analysisMode; },` |
| `get` | **`analysisMode`** | `get analysisMode() { return analysisMode; },` |
| `method-async` | **`reportDataURL`** | `async reportDataURL() { return (await buildReportCanvas()).toDataURL('image/png'); },` |
| `get` | **`replayFrames`** | `get replayFrames() { return recorder.frames.length; },` |
| `get` | **`dni`** | `get dni() { return { ...dniStats, objects: externalObjs.length }; },` |
| `method` | **`replaySeek`** | `replaySeek(idx) { enterReplay(); replayIdx = Math.max(0, Math.min(idx, recorder.frames.length - 1)); applyFrame(replayIdx); return replayIdx; },` |
| `ref` | **`goLive`** | `goLive,` |
| `get` | **`conflictPairs`** | `get conflictPairs() { return _cvLineIdx; },` |
| `get` | **`replay`** | `get replay() {` |
| `method` | **`replayStep`** | `replayStep(delta = 1) {` |

## Phase 0 — 메가/성능

| Kind | Name | Signature |
|---|---|---|
| `get` | **`megaMode`** | `get megaMode() { return megaMode; },` |
| `get` | **`instanceCount`** | `get instanceCount() { return bodyInst.count; },` |
| `get` | **`visibleInstances`** | `get visibleInstances() { return _visibleInst; },` |
| `get` | **`wsConnected`** | `get wsConnected() { return _wsConnected; },` |
| `get` | **`wsFrames`** | `get wsFrames() { return _wsFrames; },` |
| `get` | **`liveMode`** | `get liveMode() { return _wsConnected && _wsData != null; },` |
| `get` | **`perf`** | `get perf() { return { fps: perfMetrics.fps, cpuMs: +perfMetrics.cpuMs.toFixed(2), gpuMs: +perfMetrics.gpuMs.toFixed(2), drawCalls: perfMetrics.drawCalls, triangles: perfMetrics.tri` |
| `set` | **`megaCull`** | `set megaCull(v) { megaCull = !!v; },` |
| `get` | **`megaCull`** | `get megaCull() { return megaCull; },` |

## Phase 1 — ATC 콘솔

| Kind | Name | Signature |
|---|---|---|
| `method` | **`atcCommand`** | `atcCommand(did, cmd, params, source) { return window.atcCommand(did, cmd, params, source); },` |
| `get` | **`atcLog`** | `get atcLog() { return atcLog.slice(); },` |
| `get` | **`atcControlled`** | `get atcControlled() { return drones.filter(d => d.atc && d.atc.cmd).map(d => ({ id: d.id, cmd: d.atc.cmd, lockUntil: d.atc.lockUntil })); },` |
| `method` | **`setAtcAudio`** | `setAtcAudio(on) {` |
| `get` | **`atcAudio`** | `get atcAudio() { return atcAudioEnabled; },` |
| `method` | **`clearAllAtc`** | `clearAllAtc() { let n = 0; for (const d of drones) { if (d.atc && d.atc.cmd) { window.atcCommand(d, 'CLEAR'); n++; } } return n; },` |

## Phase 2 — TAC 전술 시각화

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

## Phase 3 — CIN 시네마틱

| Kind | Name | Signature |
|---|---|---|
| `method` | **`setSunCycle`** | `setSunCycle(on) { sunCycle.enabled = !!on; const e = document.getElementById('tg-sun-cycle'); if (e) e.checked = sunCycle.enabled; return sunCycle.enabled; },` |
| `method` | **`setSunHour`** | `setSunHour(h) { sunCycle.hour = Math.max(0, Math.min(24, +h)); const sl = document.getElementById('sun-hour'); if (sl) sl.value = sunCycle.hour; return sunCycle.hour; },` |
| `method` | **`setSunAuto`** | `setSunAuto(on) { sunCycle.auto = !!on; if (sunCycle.auto) sunCycle.enabled = true; return sunCycle.auto; },` |
| `get` | **`sunHour`** | `get sunHour() { return sunCycle.hour; },` |
| `get` | **`sunEnabled`** | `get sunEnabled() { return sunCycle.enabled; },` |
| `method` | **`setRain`** | `setRain(on, intensity) { cinParticles.rain.enabled = !!on; if (intensity != null) cinParticles.rain.intensity = Math.max(0, Math.min(1, intensity)); const e = document.getElementBy` |
| `method` | **`setSnow`** | `setSnow(on, intensity) { cinParticles.snow.enabled = !!on; if (intensity != null) cinParticles.snow.intensity = Math.max(0, Math.min(1, intensity)); const e = document.getElementBy` |
| `method` | **`startRecording`** | `startRecording() { return startRecording(); },` |
| `method` | **`stopRecording`** | `stopRecording() { return stopRecording(); },` |
| `get` | **`recording`** | `get recording() { return cinRecorder.recording; },` |

## Phase 4 — CAM 카메라

| Kind | Name | Signature |
|---|---|---|
| `method` | **`setCamMode`** | `setCamMode(mode) { setCamMode(mode); return camMode; },` |
| `get` | **`camMode`** | `get camMode() { return camMode; },` |

## Phase 5 — MIS 임무

| Kind | Name | Signature |
|---|---|---|
| `method` | **`missionAdd`** | `missionAdd(droneId, waypoints, templateName) { return missionAdd(droneId, waypoints, templateName); },` |
| `method` | **`missionTemplate`** | `missionTemplate(name, originX, originZ) { return _missionGenerateTemplate(name, originX \|\| 0, originZ \|\| 0); },` |
| `method` | **`missionAssignTemplate`** | `missionAssignTemplate(droneId, templateName) {` |
| `method` | **`missionClearAll`** | `missionClearAll() { missionClearAll(); return missions.length; },` |
| `get` | **`missions`** | `get missions() { return missions.map(m => ({ id: m.id, droneId: m.droneId, wpCount: m.waypoints.length, currentIdx: m.currentIdx, completion: m.completion, template: m.template }))` |

## Phase 6 — INJ 장애 주입

| Kind | Name | Signature |
|---|---|---|
| `method` | **`injectFault`** | `injectFault(droneId, type, opts) { return injectFault(droneId, type, opts); },` |
| `method` | **`injectRogue`** | `injectRogue() { return injectRogue(); },` |
| `method` | **`injectDynamicNFZ`** | `injectDynamicNFZ(x, z, r, dur) { return injectDynamicNFZ(x, z, r, dur); },` |
| `method` | **`injectScenario`** | `injectScenario(name) { return injectScenario(name); },` |
| `method` | **`injClearAll`** | `injClearAll() { return injClearAll(); },` |
| `get` | **`injStats`** | `get injStats() { return { ...injStats }; },` |
| `get` | **`dynamicNfzList`** | `get dynamicNfzList() { return _dynNfzList.slice(); },` |

## Phase 7 — ANA 분석 강화

| Kind | Name | Signature |
|---|---|---|
| `method` | **`setAnaHeatmap`** | `setAnaHeatmap(on) { anaHeatmap.enabled = !!on; const e = document.getElementById('tg-ana-heatmap'); if (e) e.checked = anaHeatmap.enabled; return anaHeatmap.enabled; },` |
| `get` | **`anaHeatmap`** | `get anaHeatmap() { return anaHeatmap.enabled; },` |
| `get` | **`anaKpiWindow`** | `get anaKpiWindow() { return { time: anaKpiWindow.time.slice(), cr: anaKpiWindow.cr.slice(), avgBat: anaKpiWindow.avgBat.slice(), fps: anaKpiWindow.fps.slice() }; },` |
| `method` | **`exportLatexKpi`** | `exportLatexKpi() { return exportLatexKpi(); },` |

## Phase 8 — AUD 환경 사운드

| Kind | Name | Signature |
|---|---|---|
| `method` | **`setAmbientAudio`** | `setAmbientAudio(on) { audAmbient.enabled = !!on; const b = document.getElementById('btn-aud-ambient'); if (b) { b.classList.toggle('off', !audAmbient.enabled); b.textContent = audA` |
| `get` | **`ambientAudio`** | `get ambientAudio() { return audAmbient.enabled; },` |

## Phase 9 — MOB 모바일/PWA

| Kind | Name | Signature |
|---|---|---|
| `get` | **`isMobile`** | `get isMobile() { return mobConfig.isMobile; },` |
| `get` | **`mobileLOD`** | `get mobileLOD() { return mobConfig.autoLOD; },` |
| `method` | **`applyMobileLOD`** | `applyMobileLOD() { applyMobileLOD(); return mobConfig.autoLOD; },` |

## HYPER 13 — WebGPU 50K

| Kind | Name | Signature |
|---|---|---|
| `method` | **`enableGpu50k`** | `enableGpu50k(on) { gpu50k.enabled = !!on; return gpu50k.enabled; },` |
| `method` | **`gpu50kBuild`** | `gpu50kBuild() { return gpu50kBuildHash(); },` |
| `method` | **`gpu50kQuery`** | `gpu50kQuery(idx, radius) { return gpu50kQueryNeighbors(idx, radius \|\| 200); },` |
| `get` | **`gpu50kEnabled`** | `get gpu50kEnabled() { return gpu50k.enabled; },` |
| `get` | **`gpu50kStats`** | `get gpu50kStats() { return { cellSize: gpu50k.cellSize, gridSize: gpu50k.gridSize, lastBuildMs: gpu50k.statsLastMs, bucketCount: gpu50k.buckets ? gpu50k.buckets.size : 0, targetCap` |

## HYPER 14 — 시나리오 갤러리

| Kind | Name | Signature |
|---|---|---|
| `method` | **`openGallery`** | `openGallery() { openScenarioGallery(); return true; },` |
| `method` | **`closeGallery`** | `closeGallery() { closeScenarioGallery(); return true; },` |
| `get` | **`galleryOpen`** | `get galleryOpen() { return document.getElementById('scenario-gallery-modal')?.style.display === 'block'; },` |
| `get` | **`scenarioCategories`** | `get scenarioCategories() { return Object.keys(SCENARIO_CATEGORIES); },` |

## HYPER 16 — CRDT 다중 관제

| Kind | Name | Signature |
|---|---|---|
| `method` | **`enableCrdt`** | `enableCrdt(on) { crdtState.enabled = !!on; return crdtState.enabled; },` |
| `method` | **`crdtAddOp`** | `crdtAddOp(target, cmd, params) { return crdtAddOp(target, cmd, params); },` |
| `method` | **`crdtMerge`** | `crdtMerge(remoteOps) { return crdtMerge(remoteOps); },` |
| `method` | **`crdtSnapshot`** | `crdtSnapshot() { return crdtSnapshot(); },` |
| `get` | **`crdtEnabled`** | `get crdtEnabled() { return crdtState.enabled; },` |
| `get` | **`crdtSiteId`** | `get crdtSiteId() { return crdtState.siteId; },` |

## HYPER 17 — WebXR VR

| Kind | Name | Signature |
|---|---|---|
| `get` | **`xrSupported`** | `get xrSupported() { return !!(navigator.xr && renderer.xr && renderer.xr.enabled); },` |
| `get` | **`xrPresenting`** | `get xrPresenting() { return !!(renderer.xr && renderer.xr.isPresenting); },` |

## HYPER 18 — AR Overlay

| Kind | Name | Signature |
|---|---|---|
| `method` | **`arEnter`** | `arEnter() { return arEnter(); },` |
| `method` | **`arExit`** | `arExit() { return arExit(); },` |
| `method` | **`arAddPin`** | `arAddPin(lat, lon, label) { return arAddPin(lat, lon, label); },` |
| `method` | **`arClearPins`** | `arClearPins() { return arClearPins(); },` |
| `get` | **`arEnabled`** | `get arEnabled() { return arOverlay.enabled; },` |
| `get` | **`arPins`** | `get arPins() { return arOverlay.cameraPins.slice(); },` |

## HYPER 19 — Mission Recorder

| Kind | Name | Signature |
|---|---|---|
| `method` | **`exportMission`** | `exportMission() { return exportMission(); },` |
| `method` | **`importMission`** | `importMission(jsonText) { return importMission(jsonText); },` |
| `method` | **`triggerMissionImport`** | `triggerMissionImport() { return triggerMissionImport(); },` |

## HYPER 20 — AI Copilot

| Kind | Name | Signature |
|---|---|---|
| `method` | **`copilotPlan`** | `copilotPlan(prompt) { return _copilotPlan(prompt); },` |
| `method` | **`copilotExecute`** | `copilotExecute(plan) { return _copilotExecute(plan); },` |
| `get` | **`copilotHistory`** | `get copilotHistory() { return copilotHistory.slice(); },` |

## HYPER 21 — 적대 드론

| Kind | Name | Signature |
|---|---|---|
| `method` | **`spawnAdversarial`** | `spawnAdversarial(policy) { return spawnAdversarial(policy); },` |
| `method` | **`clearAdversarial`** | `clearAdversarial() { clearAdversarial(); return adversarialState.droneIds.length; },` |
| `get` | **`adversarialPolicy`** | `get adversarialPolicy() { return adversarialState.activePolicy; },` |
| `get` | **`adversarialDrones`** | `get adversarialDrones() { return adversarialState.droneIds.slice(); },` |
| `get` | **`adversarialSafetyResponse`** | `get adversarialSafetyResponse() { return adversarialState.safetyResponseTimes.slice(); },` |
| `get` | **`adversarialPolicies`** | `get adversarialPolicies() { return Object.keys(ADVERSARIAL_POLICIES); },` |

## HYPER 22 — Digital Twin Pixhawk

| Kind | Name | Signature |
|---|---|---|
| `method` | **`enableDtwin`** | `enableDtwin(on) { dtwin.enabled = !!on; return dtwin.enabled; },` |
| `method` | **`dtwinDecodeGPI`** | `dtwinDecodeGPI(buf) { return dtwinDecodeGPI(buf); },` |
| `method` | **`dtwinApplyGPI`** | `dtwinApplyGPI(payload, idx) { return dtwinApplyGPI(payload, idx); },` |
| `method` | **`dtwinSetOrigin`** | `dtwinSetOrigin(lat, lon) { return dtwinSetOrigin(lat, lon); },` |
| `get` | **`dtwinEnabled`** | `get dtwinEnabled() { return dtwin.enabled; },` |
| `get` | **`dtwinStats`** | `get dtwinStats() { return { linkedDroneId: dtwin.linkedDroneId, packetCount: dtwin.packetCount, lastMessage: dtwin.lastMessage, origin: { ...dtwinOrigin } }; },` |

## HYPER 23 — Wind Field

| Kind | Name | Signature |
|---|---|---|
| `method` | **`enableWindField`** | `enableWindField(on) { windField.enabled = !!on; if (on && !windField.u) initWindField(); return windField.enabled; },` |
| `method` | **`setWindRegime`** | `setWindRegime(name) { return setWindRegime(name); },` |
| `method` | **`sampleWindAt`** | `sampleWindAt(wx, wz) { return sampleWindAt(wx, wz); },` |
| `get` | **`windFieldEnabled`** | `get windFieldEnabled() { return windField.enabled; },` |
| `get` | **`windRegime`** | `get windRegime() { return windField.regime; },` |
| `get` | **`windFieldStats`** | `get windFieldStats() {` |

## HYPER 24 — NOTAM

| Kind | Name | Signature |
|---|---|---|
| `method` | **`notamAdd`** | `notamAdd(entry) { return notamAdd(entry); },` |
| `method` | **`notamImportJson`** | `notamImportJson(text) { return notamImportJson(text); },` |
| `get` | **`notams`** | `get notams() { return notams.slice(); },` |
| `get` | **`notamCount`** | `get notamCount() { return notams.length; },` |

## HYPER 25 — Battery Aging

| Kind | Name | Signature |
|---|---|---|
| `get` | **`batteryAgeStats`** | `get batteryAgeStats() { return batteryAgeStats(); },` |

## HYPER 26 — Acoustic Propagation

| Kind | Name | Signature |
|---|---|---|
| `method` | **`enableAcoustic`** | `enableAcoustic(on) { acoustic.enabled = !!on; return acoustic.enabled; },` |
| `method` | **`acousticAddObserver`** | `acousticAddObserver(x, z, label) { return acousticAddObserver(x, z, label); },` |
| `get` | **`acousticEnabled`** | `get acousticEnabled() { return acoustic.enabled; },` |
| `get` | **`acousticObservers`** | `get acousticObservers() { return acoustic.observerPoints.slice(); },` |
| `get` | **`acousticStats`** | `get acousticStats() { return acousticStats(); },` |

## HYPER 27 — Counter-UAS

| Kind | Name | Signature |
|---|---|---|
| `method` | **`enableCuas`** | `enableCuas(on) { return enableCuas(on); },` |
| `method` | **`setCuasMode`** | `setCuasMode(m) { return setCuasMode(m); },` |
| `method` | **`cuasEngage`** | `cuasEngage() { return cuasEngage(); },` |
| `method` | **`cuasDetect`** | `cuasDetect() { return cuasDetect().map(t => ({ id: t.drone.id, dist: Math.round(t.dist) })); },` |
| `get` | **`cuasEnabled`** | `get cuasEnabled() { return cuasState.enabled; },` |
| `get` | **`cuasMode`** | `get cuasMode() { return cuasState.mode; },` |
| `get` | **`cuasEngagements`** | `get cuasEngagements() { return cuasState.engagementCount; },` |
| `get` | **`cuasLog`** | `get cuasLog() { return cuasState.log.slice(); },` |
| `get` | **`cuasModes`** | `get cuasModes() { return Object.keys(CUAS_MODES); },` |

## HYPER 28 — Choreography

| Kind | Name | Signature |
|---|---|---|
| `method` | **`startChoreography`** | `startChoreography(pattern) { return startChoreography(pattern); },` |
| `method` | **`clearChoreography`** | `clearChoreography() { clearChoreography(); return true; },` |
| `get` | **`choreoPattern`** | `get choreoPattern() { return choreoState.pattern; },` |
| `get` | **`choreoPatterns`** | `get choreoPatterns() { return Object.keys(CHOREOGRAPHY_PATTERNS); },` |

## HYPER 29 — Forecast

| Kind | Name | Signature |
|---|---|---|
| `method` | **`generateForecast`** | `generateForecast(hours) { return generateForecast(hours); },` |
| `method` | **`forecastQueryHour`** | `forecastQueryHour(h) { return forecastQueryHour(h); },` |
| `method` | **`forecastFlyableHours`** | `forecastFlyableHours(windMax, precipMax) { return forecastFlyableHours(windMax, precipMax); },` |
| `get` | **`forecastData`** | `get forecastData() { return forecast.data ? forecast.data.slice(0, 5) : null; },` |

## HYPER 30 — UTM Federation

| Kind | Name | Signature |
|---|---|---|
| `method` | **`utmFederationAdd`** | `utmFederationAdd(id, label, region) { return utmFederationAdd(id, label, region); },` |
| `method` | **`utmFederationHandoff`** | `utmFederationHandoff(droneId, fromUtm, toUtm) { return utmFederationHandoff(droneId, fromUtm, toUtm); },` |
| `method` | **`utmFederationSync`** | `utmFederationSync() { return utmFederationSync(); },` |
| `get` | **`utmFederationInstances`** | `get utmFederationInstances() { return utmFederation.instances.slice(); },` |
| `get` | **`utmFederationHandoffLog`** | `get utmFederationHandoffLog() { return utmFederation.handoffLog.slice(); },` |

## HYPER 31 — PQC Telemetry

| Kind | Name | Signature |
|---|---|---|
| `method` | **`enablePqc`** | `enablePqc(on) { pqc.enabled = !!on; return pqc.enabled; },` |
| `get` | **`pqcStats`** | `get pqcStats() { return pqcStats(); },` |
| `get` | **`pqcEnabled`** | `get pqcEnabled() { return pqc.enabled; },` |

## HYPER 32 — Satellite

| Kind | Name | Signature |
|---|---|---|
| `method` | **`satelliteInit`** | `satelliteInit(name) { return satelliteInit(name); },` |
| `method` | **`satelliteVisibleAt`** | `satelliteVisibleAt(lat, lon) { return satelliteVisibleAt(lat, lon).map(s => s.id); },` |
| `method` | **`satelliteHandoff`** | `satelliteHandoff() { return satelliteHandoff(); },` |
| `get` | **`satelliteConstellation`** | `get satelliteConstellation() { return satellite.constellation; },` |
| `get` | **`satelliteCount`** | `get satelliteCount() { return satellite.satellites.length; },` |

## HYPER 33 — UUV

| Kind | Name | Signature |
|---|---|---|
| `method` | **`uuvAdd`** | `uuvAdd(x, z, depth) { return uuvAdd(x, z, depth); },` |
| `method` | **`uuvAcousticBudget`** | `uuvAcousticBudget() { return uuvAcousticBudget(); },` |
| `get` | **`uuvVehicles`** | `get uuvVehicles() { return uuv.vehicles.slice(); },` |

## HYPER 34 — Sensor Fusion

| Kind | Name | Signature |
|---|---|---|
| `method` | **`sensorFusionToggle`** | `sensorFusionToggle(sensor, on) { return sensorFusionToggle(sensor, on); },` |
| `method` | **`sensorFusionSetFilter`** | `sensorFusionSetFilter(name) { return sensorFusionSetFilter(name); },` |
| `method` | **`sensorFusionEffectiveNoise`** | `sensorFusionEffectiveNoise() { return sensorFusionEffectiveNoise(); },` |
| `get` | **`sensorFusionState`** | `get sensorFusionState() { return { sensors: { ...sensorFusion.sensors }, filter: sensorFusion.filter }; },` |

## HYPER 35 — MEC

| Kind | Name | Signature |
|---|---|---|
| `method` | **`mecAdd`** | `mecAdd(x, z, cap, lat) { return mecAdd(x, z, cap, lat); },` |
| `method` | **`mecAssign`** | `mecAssign(droneId, sizeKB) { const r = mecAssign(droneId, sizeKB); return r ? r.id : null; },` |
| `get` | **`mecNodes`** | `get mecNodes() { return mec.nodes.slice(); },` |
| `get` | **`mecWorkloads`** | `get mecWorkloads() { return mec.workloads.slice(); },` |

## HYPER 36 — Federated Learning

| Kind | Name | Signature |
|---|---|---|
| `method` | **`fedLearnRound`** | `fedLearnRound(n, loss) { return fedLearnRound(n, loss); },` |
| `get` | **`fedLearnState`** | `get fedLearnState() { return { round: fedLearn.round, loss: fedLearn.aggregatedModel.loss, epsilon: fedLearn.privacyEpsilon }; },` |
| `get` | **`fedLearnHistory`** | `get fedLearnHistory() { return fedLearn.history.slice(); },` |

## HYPER 37 — Multi-Domain

| Kind | Name | Signature |
|---|---|---|
| `method` | **`ugvAdd`** | `ugvAdd(x, z, label) { return ugvAdd(x, z, label); },` |
| `method` | **`multiDomainHandoff`** | `multiDomainHandoff(droneId, fromD, toD, missionId) { return multiDomainHandoff(droneId, fromD, toD, missionId); },` |
| `get` | **`ugvs`** | `get ugvs() { return multiDomain.ugv.slice(); },` |
| `get` | **`multiDomainHandoffLog`** | `get multiDomainHandoffLog() { return multiDomain.handoffLog.slice(); },` |

## HYPER 38 — Doppler Audio

| Kind | Name | Signature |
|---|---|---|
| `method` | **`audioDopplerShift`** | `audioDopplerShift(droneIdx, freq) { const d = drones[droneIdx]; return d ? audioDopplerShift(d, freq) : null; },` |
| `method` | **`audioSetListener`** | `audioSetListener(x, z) { return audioSetListener(x, z); },` |
| `get` | **`audioEngineState`** | `get audioEngineState() { return { ...audioEngine }; },` |

## HYPER 39 — Photogrammetry

| Kind | Name | Signature |
|---|---|---|
| `method` | **`photogrammetryImport`** | `photogrammetryImport(name, bboxKm, url) { return photogrammetryImport(name, bboxKm, url); },` |
| `get` | **`photogrammetryScenes`** | `get photogrammetryScenes() { return photogrammetry.importedScenes.slice(); },` |

## HYPER 40 — Esports

| Kind | Name | Signature |
|---|---|---|
| `method` | **`esportsAddPlayer`** | `esportsAddPlayer(name, role) { return esportsAddPlayer(name, role); },` |
| `method` | **`esportsScore`** | `esportsScore(playerId, delta) { return esportsScore(playerId, delta); },` |
| `get` | **`esportsPlayers`** | `get esportsPlayers() { return esports.players.slice(); },` |

## HYPER 41 — Procedural City

| Kind | Name | Signature |
|---|---|---|
| `method` | **`procCityGenerate`** | `procCityGenerate(sizeKm, density) { return procCityGenerate(sizeKm, density); },` |
| `get` | **`procCityBuildingCount`** | `get procCityBuildingCount() { return procCity.buildings.length; },` |

## HYPER 42 — Eye-Tracking

| Kind | Name | Signature |
|---|---|---|
| `method` | **`eyeTrackAdd`** | `eyeTrackAdd(x, y) { return eyeTrackAdd(x, y); },` |
| `method` | **`eyeTrackBuildHeatmap`** | `eyeTrackBuildHeatmap() { return eyeTrackBuildHeatmap(); },` |
| `get` | **`eyeTrackPointCount`** | `get eyeTrackPointCount() { return eyeTrack.gazePoints.length; },` |

## HYPER 43 — Voice Macros

| Kind | Name | Signature |
|---|---|---|
| `method` | **`voiceMacroDefine`** | `voiceMacroDefine(name, ops) { return voiceMacroDefine(name, ops); },` |
| `method` | **`voiceMacroExecute`** | `voiceMacroExecute(name) { return voiceMacroExecute(name); },` |
| `get` | **`voiceMacros`** | `get voiceMacros() { return Object.keys(voiceMacros.macros); },` |

## HYPER 44 — Time Compression

| Kind | Name | Signature |
|---|---|---|
| `method` | **`timeCompressSet`** | `timeCompressSet(f) { return timeCompressSet(f); },` |
| `method` | **`timeCompressReset`** | `timeCompressReset() { return timeCompressReset(); },` |

## HYPER 45 — HITL Cluster

| Kind | Name | Signature |
|---|---|---|
| `method` | **`hitlAdd`** | `hitlAdd(id, label) { return hitlAdd(id, label); },` |
| `method` | **`hitlConnect`** | `hitlConnect(id) { return hitlConnect(id); },` |
| `get` | **`hitlNodes`** | `get hitlNodes() { return hitlCluster.nodes.slice(); },` |

## HYPER 46 — National Airspace

| Kind | Name | Signature |
|---|---|---|
| `method` | **`nationalASInitKorea`** | `nationalASInitKorea() { return nationalASInitKorea(); },` |
| `method` | **`nationalASAddAirport`** | `nationalASAddAirport(icao, lat, lon, name) { return nationalASAddAirport(icao, lat, lon, name); },` |
| `get` | **`nationalASAirports`** | `get nationalASAirports() { return nationalAS.airports.slice(); },` |

## HYPER 47 — Climate Impact

| Kind | Name | Signature |
|---|---|---|
| `method` | **`enableClimate`** | `enableClimate(on) { climate.enabled = !!on; return climate.enabled; },` |
| `get` | **`climateScore`** | `get climateScore() { return climateScore(); },` |

## HYPER 48 — Cross-Border

| Kind | Name | Signature |
|---|---|---|
| `method` | **`crossBorderTransit`** | `crossBorderTransit(droneId, fromC, toC, approved) { return crossBorderTransit(droneId, fromC, toC, approved); },` |
| `get` | **`crossBorderTransitsLog`** | `get crossBorderTransitsLog() { return crossBorder.transitsLog.slice(); },` |

## HYPER 49 — Planetary

| Kind | Name | Signature |
|---|---|---|
| `method` | **`planetarySetBody`** | `planetarySetBody(name) { return planetarySetBody(name); },` |
| `get` | **`planetaryState`** | `get planetaryState() { return { ...planetary }; },` |

## HYPER 50 — Public Demo

| Kind | Name | Signature |
|---|---|---|
| `method` | **`publicDemoLeaderboardAdd`** | `publicDemoLeaderboardAdd(name, score) { return publicDemoLeaderboardAdd(name, score); },` |
| `method` | **`publicDemoDailyChallenge`** | `publicDemoDailyChallenge() { return publicDemoDailyChallenge(); },` |
| `get` | **`publicDemoLeaderboard`** | `get publicDemoLeaderboard() { return publicDemo.leaderboard.slice(); },` |

## 🔗 참고 문서

- [`SIMULATOR_MEGA_PLAN.md`](SIMULATOR_MEGA_PLAN.md)
- [`SIMULATOR_HYPER_PLAN.md`](SIMULATOR_HYPER_PLAN.md)
- [`RELEASE_GUIDE.md`](RELEASE_GUIDE.md)

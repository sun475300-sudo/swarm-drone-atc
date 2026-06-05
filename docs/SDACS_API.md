# 📚 `window._sdacs` API — Phase 200 (Unity) 완료 시점

*자동 생성: 2026-06-05*

**총 388 항목** — MEGA 9 + HYPER 41 + STELLAR 49 + ULTIMATE 50 + POST-UNIVERSE 50 + Phase 51 시드 = **200 Phase**

---

## 📑 전체 API (알파벳순)

| Kind | Name | Signature |
|---|---|---|
| `method` | **`acousticAddObserver`** | `acousticAddObserver(x, z, label) { return acousticAddObserver(x, z, label); },` |
| `get` | **`acousticEnabled`** | `get acousticEnabled() { return acoustic.enabled; },` |
| `get` | **`acousticObservers`** | `get acousticObservers() { return acoustic.observerPoints.slice(); },` |
| `get` | **`acousticStats`** | `get acousticStats() { return acousticStats(); },` |
| `method` | **`adversarialCheck`** | `adversarialCheck(input) { return adversarialCheck(input); },` |
| `get` | **`adversarialDetected`** | `get adversarialDetected() { return adversarialDef.detected; },` |
| `get` | **`adversarialDrones`** | `get adversarialDrones() { return adversarialState.droneIds.slice(); },` |
| `get` | **`adversarialPolicies`** | `get adversarialPolicies() { return Object.keys(ADVERSARIAL_POLICIES); },` |
| `get` | **`adversarialPolicy`** | `get adversarialPolicy() { return adversarialState.activePolicy; },` |
| `get` | **`adversarialSafetyResponse`** | `get adversarialSafetyResponse() { return adversarialState.safetyResponseTimes.slice(); },` |
| `get` | **`airborne`** | `get airborne() { return drones.filter(d => d.phase !== 'GROUNDED' && d.phase !== 'FAILED').length; },` |
| `method` | **`algae124Power`** | `algae124Power(w) { return algae124Power(w); },` |
| `get` | **`ambientAudio`** | `get ambientAudio() { return audAmbient.enabled; },` |
| `get` | **`anaHeatmap`** | `get anaHeatmap() { return anaHeatmap.enabled; },` |
| `get` | **`anaKpiWindow`** | `get anaKpiWindow() { return { time: anaKpiWindow.time.slice(), cr: anaKpiWindow.cr.slice(), avgBat: anaKpiWindow.avgBat.slice(), fps: anaKpiWindow.fps.slice() }; },` |
| `get` | **`analysisMode`** | `get analysisMode() { return analysisMode; },` |
| `method` | **`annealingSolve`** | `annealingSolve(size) { return annealingSolve(size); },` |
| `method` | **`applyMobileLOD`** | `applyMobileLOD() { applyMobileLOD(); return mobConfig.autoLOD; },` |
| `method` | **`arAddPin`** | `arAddPin(lat, lon, label) { return arAddPin(lat, lon, label); },` |
| `method` | **`arClearPins`** | `arClearPins() { return arClearPins(); },` |
| `get` | **`arEnabled`** | `get arEnabled() { return arOverlay.enabled; },` |
| `method` | **`arEnter`** | `arEnter() { return arEnter(); },` |
| `method` | **`arExit`** | `arExit() { return arExit(); },` |
| `get` | **`arPins`** | `get arPins() { return arOverlay.cameraPins.slice(); },` |
| `get` | **`atcAudio`** | `get atcAudio() { return atcAudioEnabled; },` |
| `method` | **`atcCommand`** | `atcCommand(did, cmd, params, source) { return window.atcCommand(did, cmd, params, source); },` |
| `get` | **`atcControlled`** | `get atcControlled() { return drones.filter(d => d.atc && d.atc.cmd).map(d => ({ id: d.id, cmd: d.atc.cmd, lockUntil: d.atc.lockUntil })); },` |
| `get` | **`atcLog`** | `get atcLog() { return atcLog.slice(); },` |
| `method` | **`atmo116Harvest`** | `atmo116Harvest(j) { return atmo116Harvest(j); },` |
| `method` | **`audioDopplerShift`** | `audioDopplerShift(droneIdx, freq) { const d = drones[droneIdx]; return d ? audioDopplerShift(d, freq) : null; },` |
| `get` | **`audioEngineState`** | `get audioEngineState() { return { ...audioEngine }; },` |
| `method` | **`audioSetListener`** | `audioSetListener(x, z) { return audioSetListener(x, z); },` |
| `get` | **`availableLangs`** | `get availableLangs() { return LANG_ORDER.slice(); },` |
| `method` | **`bacteria123Spawn`** | `bacteria123Spawn(n) { return bacteria123Spawn(n); },` |
| `get` | **`batteryAgeStats`** | `get batteryAgeStats() { return batteryAgeStats(); },` |
| `method` | **`bciActivate`** | `bciActivate(channels) { return bciActivate(channels); },` |
| `method` | **`beyondEarthAddDebris`** | `beyondEarthAddDebris(altKm, sizeM) { return beyondEarthAddDebris(altKm, sizeM); },` |
| `method` | **`beyondEarthSetMode`** | `beyondEarthSetMode(m) { return beyondEarthSetMode(m); },` |
| `get` | **`beyondEarthState`** | `get beyondEarthState() { return { mode: beyondEarth.mode, debrisCount: beyondEarth.orbitalDebris.length }; },` |
| `method` | **`bioDeg115SetLife`** | `bioDeg115SetLife(h) { return bioDeg115SetLife(h); },` |
| `method` | **`biofluor129Emit`** | `biofluor129Emit(c) { return biofluor129Emit(c); },` |
| `method` | **`bird126Partner`** | `bird126Partner(sp) { return bird126Partner(sp); },` |
| `method` | **`caac139Compat`** | `caac139Compat() { return caac139Compat(); },` |
| `get` | **`camMode`** | `get camMode() { return camMode; },` |
| `method` | **`captureScreenshot`** | `captureScreenshot() { renderer.render(scene, camera); return renderer.domElement.toDataURL('image/png'); },` |
| `method` | **`causalAddEdge`** | `causalAddEdge(from, to, weight) { return causalAddEdge(from, to, weight); },` |
| `get` | **`causalDag`** | `get causalDag() { return { nodes: causal.dag.nodes.slice(), edges: causal.dag.edges.slice() }; },` |
| `method` | **`causalDoQuery`** | `causalDoQuery(intervention, target) { return causalDoQuery(intervention, target); },` |
| `method` | **`cesiumGlobalInit`** | `cesiumGlobalInit() { return cesiumGlobalInit(); },` |
| `get` | **`cesiumGlobalState`** | `get cesiumGlobalState() { return { ...cesiumGlobal }; },` |
| `get` | **`choreoPattern`** | `get choreoPattern() { return choreoState.pattern; },` |
| `get` | **`choreoPatterns`** | `get choreoPatterns() { return Object.keys(CHOREOGRAPHY_PATTERNS); },` |
| `method` | **`clearAdversarial`** | `clearAdversarial() { clearAdversarial(); return adversarialState.droneIds.length; },` |
| `method` | **`clearAllAtc`** | `clearAllAtc() { let n = 0; for (const d of drones) { if (d.atc && d.atc.cmd) { window.atcCommand(d, 'CLEAR'); n++; } } return n; },` |
| `method` | **`clearChoreography`** | `clearChoreography() { clearChoreography(); return true; },` |
| `method` | **`clearHover`** | `clearHover() { setHover(null); },` |
| `method` | **`clearMulti`** | `clearMulti() { clearMulti(); },` |
| `get` | **`climateScore`** | `get climateScore() { return climateScore(); },` |
| `method` | **`closeGallery`** | `closeGallery() { closeScenarioGallery(); return true; },` |
| `method` | **`cloudBurstScale`** | `cloudBurstScale(load) { return cloudBurstScale(load); },` |
| `get` | **`cloudBurstState`** | `get cloudBurstState() { return { instances: cloudBurst.instances, history: cloudBurst.scaleHistory.length }; },` |
| `get` | **`conflictPairs`** | `get conflictPairs() { return _cvLineIdx; },` |
| `method` | **`consciousness143Experiment`** | `consciousness143Experiment() { return consciousness143Experiment(); },` |
| `method` | **`copilotExecute`** | `copilotExecute(plan) { return _copilotExecute(plan); },` |
| `get` | **`copilotHistory`** | `get copilotHistory() { return copilotHistory.slice(); },` |
| `method` | **`copilotPlan`** | `copilotPlan(prompt) { return _copilotPlan(prompt); },` |
| `get` | **`cpaMarker`** | `get cpaMarker() { return _cpaMarkerEnabled; },` |
| `get` | **`cpaPairsCount`** | `get cpaPairsCount() { return _cpaMarkerIdx; },` |
| `method` | **`crdtAddOp`** | `crdtAddOp(target, cmd, params) { return crdtAddOp(target, cmd, params); },` |
| `get` | **`crdtEnabled`** | `get crdtEnabled() { return crdtState.enabled; },` |
| `method` | **`crdtMerge`** | `crdtMerge(remoteOps) { return crdtMerge(remoteOps); },` |
| `get` | **`crdtSiteId`** | `get crdtSiteId() { return crdtState.siteId; },` |
| `method` | **`crdtSnapshot`** | `crdtSnapshot() { return crdtSnapshot(); },` |
| `method` | **`crossBorderTransit`** | `crossBorderTransit(droneId, fromC, toC, approved) { return crossBorderTransit(droneId, fromC, toC, approved); },` |
| `get` | **`crossBorderTransitsLog`** | `get crossBorderTransitsLog() { return crossBorder.transitsLog.slice(); },` |
| `method` | **`cuasDetect`** | `cuasDetect() { return cuasDetect().map(t => ({ id: t.drone.id, dist: Math.round(t.dist) })); },` |
| `get` | **`cuasEnabled`** | `get cuasEnabled() { return cuasState.enabled; },` |
| `method` | **`cuasEngage`** | `cuasEngage() { return cuasEngage(); },` |
| `get` | **`cuasEngagements`** | `get cuasEngagements() { return cuasState.engagementCount; },` |
| `get` | **`cuasLog`** | `get cuasLog() { return cuasState.log.slice(); },` |
| `get` | **`cuasMode`** | `get cuasMode() { return cuasState.mode; },` |
| `get` | **`cuasModes`** | `get cuasModes() { return Object.keys(CUAS_MODES); },` |
| `method` | **`daoCreateProposal`** | `daoCreateProposal(title, desc) { return daoCreateProposal(title, desc); },` |
| `method` | **`deselectDrone`** | `deselectDrone() { deselectDrone(); },` |
| `get` | **`distributedShards`** | `get distributedShards() { return distributedSim.shards.slice(); },` |
| `method` | **`distributedSimAddShard`** | `distributedSimAddShard(s, e) { return distributedSimAddShard(s, e); },` |
| `method` | **`distributedSimRebalance`** | `distributedSimRebalance() { return distributedSimRebalance(); },` |
| `method` | **`dna122Store`** | `dna122Store(gb) { return dna122Store(gb); },` |
| `get` | **`dni`** | `get dni() { return { ...dniStats, objects: externalObjs.length }; },` |
| `method` | **`dpu109Offload`** | `dpu109Offload(bytes) { return dpu109Offload(bytes); },` |
| `get` | **`droneCount`** | `get droneCount() { return drones.length; },` |
| `method` | **`dtwinApplyGPI`** | `dtwinApplyGPI(payload, idx) { return dtwinApplyGPI(payload, idx); },` |
| `method` | **`dtwinDecodeGPI`** | `dtwinDecodeGPI(buf) { return dtwinDecodeGPI(buf); },` |
| `get` | **`dtwinEnabled`** | `get dtwinEnabled() { return dtwin.enabled; },` |
| `method` | **`dtwinSetOrigin`** | `dtwinSetOrigin(lat, lon) { return dtwinSetOrigin(lat, lon); },` |
| `get` | **`dtwinStats`** | `get dtwinStats() { return { linkedDroneId: dtwin.linkedDroneId, packetCount: dtwin.packetCount, lastMessage: dtwin.lastMessage, origin: { ...dtwinOrigin } }; },` |
| `get` | **`dynamicNfzList`** | `get dynamicNfzList() { return _dynNfzList.slice(); },` |
| `method` | **`easa137Integrate`** | `easa137Integrate() { return easa137Integrate(); },` |
| `get` | **`economyState`** | `get economyState() { return { surge: economy.uamPricing.surgeFactor, daoProposals: economy.daoProposals.length, carbonCredits: economy.carbonCredits }; },` |
| `method` | **`enableAcoustic`** | `enableAcoustic(on) { acoustic.enabled = !!on; return acoustic.enabled; },` |
| `method` | **`enableClimate`** | `enableClimate(on) { climate.enabled = !!on; return climate.enabled; },` |
| `method` | **`enableCrdt`** | `enableCrdt(on) { crdtState.enabled = !!on; return crdtState.enabled; },` |
| `method` | **`enableCuas`** | `enableCuas(on) { return enableCuas(on); },` |
| `method` | **`enableDtwin`** | `enableDtwin(on) { dtwin.enabled = !!on; return dtwin.enabled; },` |
| `method` | **`enableGpu50k`** | `enableGpu50k(on) { gpu50k.enabled = !!on; return gpu50k.enabled; },` |
| `method` | **`enablePqc`** | `enablePqc(on) { pqc.enabled = !!on; return pqc.enabled; },` |
| `method` | **`enableWindField`** | `enableWindField(on) { windField.enabled = !!on; if (on && !windField.u) initWindField(); return windField.enabled; },` |
| `method` | **`esportsAddPlayer`** | `esportsAddPlayer(name, role) { return esportsAddPlayer(name, role); },` |
| `get` | **`esportsPlayers`** | `get esportsPlayers() { return esports.players.slice(); },` |
| `method` | **`esportsScore`** | `esportsScore(playerId, delta) { return esportsScore(playerId, delta); },` |
| `method` | **`eternalMission146Start`** | `eternalMission146Start() { return eternalMission146Start(); },` |
| `method` | **`explainDecision`** | `explainDecision(decision, features) { return explainDecision(decision, features); },` |
| `get` | **`explainLastMethod`** | `get explainLastMethod() { return explainable.method; },` |
| `method` | **`exportLatexKpi`** | `exportLatexKpi() { return exportLatexKpi(); },` |
| `method` | **`exportMission`** | `exportMission() { return exportMission(); },` |
| `method` | **`eyeTrackAdd`** | `eyeTrackAdd(x, y) { return eyeTrackAdd(x, y); },` |
| `method` | **`eyeTrackBuildHeatmap`** | `eyeTrackBuildHeatmap() { return eyeTrackBuildHeatmap(); },` |
| `get` | **`eyeTrackPointCount`** | `get eyeTrackPointCount() { return eyeTrack.gazePoints.length; },` |
| `method` | **`faa138Part108`** | `faa138Part108() { return faa138Part108(); },` |
| `get` | **`failed`** | `get failed() { return drones.filter(d => d.phase === 'FAILED').length; },` |
| `get` | **`fedLearnHistory`** | `get fedLearnHistory() { return fedLearn.history.slice(); },` |
| `method` | **`fedLearnRound`** | `fedLearnRound(n, loss) { return fedLearnRound(n, loss); },` |
| `get` | **`fedLearnState`** | `get fedLearnState() { return { round: fedLearn.round, loss: fedLearn.aggregatedModel.loss, epsilon: fedLearn.privacyEpsilon }; },` |
| `method` | **`focusDrone`** | `focusDrone(idOrIndex) { let d = idOrIndex; if (typeof idOrIndex === 'string') d = drones.find(x => x.id === idOrIndex); else if (typeof idOrIndex === 'number') d = drones[idOrIndex]; if (d) focusDrone` |
| `get` | **`forecastData`** | `get forecastData() { return forecast.data ? forecast.data.slice(0, 5) : null; },` |
| `method` | **`forecastFlyableHours`** | `forecastFlyableHours(windMax, precipMax) { return forecastFlyableHours(windMax, precipMax); },` |
| `method` | **`forecastQueryHour`** | `forecastQueryHour(h) { return forecastQueryHour(h); },` |
| `method` | **`fpga106AddInstance`** | `fpga106AddInstance() { return fpga106AddInstance(); },` |
| `get` | **`galleryOpen`** | `get galleryOpen() { return document.getElementById('scenario-gallery-modal')?.style.display === 'block'; },` |
| `method` | **`generateForecast`** | `generateForecast(hours) { return generateForecast(hours); },` |
| `method` | **`getSelected`** | `getSelected() { return selectedDrone ? { ...selectedDrone, group: undefined, body: undefined, rotor: undefined, glow: undefined } : null; },` |
| `method` | **`global140Adopt`** | `global140Adopt(pct) { return global140Adopt(pct); },` |
| `ref` | **`goLive`** | `goLive,` |
| `method` | **`gpu100kInit`** | `gpu100kInit() { return gpu100kInit(); },` |
| `get` | **`gpu100kStats`** | `get gpu100kStats() { return { gridSize: gpu100k.gridSize, capacity: gpu100k.targetCapacity, wgslReady: gpu100k.wgslReady }; },` |
| `method` | **`gpu50kBuild`** | `gpu50kBuild() { return gpu50kBuildHash(); },` |
| `get` | **`gpu50kEnabled`** | `get gpu50kEnabled() { return gpu50k.enabled; },` |
| `method` | **`gpu50kQuery`** | `gpu50kQuery(idx, radius) { return gpu50kQueryNeighbors(idx, radius \|\| 200); },` |
| `get` | **`gpu50kStats`** | `get gpu50kStats() { return { cellSize: gpu50k.cellSize, gridSize: gpu50k.gridSize, lastBuildMs: gpu50k.statsLastMs, bucketCount: gpu50k.buckets ? gpu50k.buckets.size : 0, targetCapacity: gpu50k.target` |
| `method` | **`graphene113Boost`** | `graphene113Boost(f) { return graphene113Boost(f); },` |
| `method` | **`hitlAdd`** | `hitlAdd(id, label) { return hitlAdd(id, label); },` |
| `method` | **`hitlConnect`** | `hitlConnect(id) { return hitlConnect(id); },` |
| `get` | **`hitlNodes`** | `get hitlNodes() { return hitlCluster.nodes.slice(); },` |
| `method` | **`hoverDrone`** | `hoverDrone(idOrIndex) { let d = idOrIndex; if (typeof idOrIndex === 'string') d = drones.find(x => x.id === idOrIndex); else if (typeof idOrIndex === 'number') d = drones[idOrIndex]; setHover(d); retu` |
| `method` | **`icao132Adopt`** | `icao132Adopt() { return icao132Adopt(); },` |
| `method` | **`ieee134Standard`** | `ieee134Standard(name) { return ieee134Standard(name); },` |
| `method` | **`importMission`** | `importMission(jsonText) { return importMission(jsonText); },` |
| `method` | **`injClearAll`** | `injClearAll() { return injClearAll(); },` |
| `method` | **`injectDynamicNFZ`** | `injectDynamicNFZ(x, z, r, dur) { return injectDynamicNFZ(x, z, r, dur); },` |
| `method` | **`injectFault`** | `injectFault(droneId, type, opts) { return injectFault(droneId, type, opts); },` |
| `method` | **`injectRogue`** | `injectRogue() { return injectRogue(); },` |
| `method` | **`injectScenario`** | `injectScenario(name) { return injectScenario(name); },` |
| `get` | **`injStats`** | `get injStats() { return { ...injStats }; },` |
| `method` | **`insect127Join`** | `insect127Join(n) { return insect127Join(n); },` |
| `get` | **`instanceCount`** | `get instanceCount() { return bodyInst.count; },` |
| `method` | **`isaacSimLoadUSD`** | `isaacSimLoadUSD(url) { return isaacSimLoadUSD(url); },` |
| `get` | **`isaacSimState`** | `get isaacSimState() { return { enabled: isaacSim.enabled, scene: isaacSim.usdScene }; },` |
| `get` | **`isMobile`** | `get isMobile() { return mobConfig.isMobile; },` |
| `method` | **`iso133Cert`** | `iso133Cert(num) { return iso133Cert(num); },` |
| `method` | **`itu135AllocateFreq`** | `itu135AllocateFreq(mhz) { return itu135AllocateFreq(mhz); },` |
| `get` | **`landed`** | `get landed() { return drones.filter(d => d.phase === 'GROUNDED').length; },` |
| `get` | **`lang`** | `get lang() { return currentLang; },` |
| `get` | **`layers`** | `get layers() { return { ...layerVisibility }; },` |
| `get` | **`liveMode`** | `get liveMode() { return _wsConnected && _wsData != null; },` |
| `method` | **`living130Spawn`** | `living130Spawn(g) { return living130Spawn(g); },` |
| `method` | **`mecAdd`** | `mecAdd(x, z, cap, lat) { return mecAdd(x, z, cap, lat); },` |
| `method` | **`mecAssign`** | `mecAssign(droneId, sizeKB) { const r = mecAssign(droneId, sizeKB); return r ? r.id : null; },` |
| `get` | **`mecNodes`** | `get mecNodes() { return mec.nodes.slice(); },` |
| `get` | **`mecWorkloads`** | `get mecWorkloads() { return mec.workloads.slice(); },` |
| `set` | **`megaCull`** | `set megaCull(v) { megaCull = !!v; },` |
| `get` | **`megaCull`** | `get megaCull() { return megaCull; },` |
| `get` | **`megaMode`** | `get megaMode() { return megaMode; },` |
| `method` | **`megaScale110SetCurrent`** | `megaScale110SetCurrent(n) { return megaScale110SetCurrent(n); },` |
| `method` | **`meta119Activate`** | `meta119Activate(on) { return meta119Activate(on); },` |
| `method` | **`missionAdd`** | `missionAdd(droneId, waypoints, templateName) { return missionAdd(droneId, waypoints, templateName); },` |
| `method` | **`missionAssignTemplate`** | `missionAssignTemplate(droneId, templateName) {` |
| `method` | **`missionClearAll`** | `missionClearAll() { missionClearAll(); return missions.length; },` |
| `get` | **`missions`** | `get missions() { return missions.map(m => ({ id: m.id, droneId: m.droneId, wpCount: m.waypoints.length, currentIdx: m.currentIdx, completion: m.completion, template: m.template })); },` |
| `method` | **`missionTemplate`** | `missionTemplate(name, originX, originZ) { return _missionGenerateTemplate(name, originX \|\| 0, originZ \|\| 0); },` |
| `get` | **`mobileLOD`** | `get mobileLOD() { return mobConfig.autoLOD; },` |
| `method` | **`multiDomainHandoff`** | `multiDomainHandoff(droneId, fromD, toD, missionId) { return multiDomainHandoff(droneId, fromD, toD, missionId); },` |
| `get` | **`multiDomainHandoffLog`** | `get multiDomainHandoffLog() { return multiDomain.handoffLog.slice(); },` |
| `method` | **`multiSelect`** | `multiSelect(ids) { for (const id of ids) { const d = drones.find(x => x.id === id) \|\| drones[id]; if (d) multiSel.add(d); } updateMultiPanel(); return multiSel.size; }, // B4` |
| `get` | **`multiSelection`** | `get multiSelection() { return [...multiSel].map(d => d.id); },` |
| `method` | **`mycelium125Repair`** | `mycelium125Repair() { return mycelium125Repair(); },` |
| `method` | **`nano111Spawn`** | `nano111Spawn(n) { return nano111Spawn(n); },` |
| `method` | **`nationalASAddAirport`** | `nationalASAddAirport(icao, lat, lon, name) { return nationalASAddAirport(icao, lat, lon, name); },` |
| `get` | **`nationalASAirports`** | `get nationalASAirports() { return nationalAS.airports.slice(); },` |
| `method` | **`nationalASInitKorea`** | `nationalASInitKorea() { return nationalASInitKorea(); },` |
| `method` | **`neuromorphic108Spike`** | `neuromorphic108Spike(rate) { return neuromorphic108Spike(rate); },` |
| `method` | **`neuron121Connect`** | `neuron121Connect(hz) { return neuron121Connect(hz); },` |
| `method` | **`notamAdd`** | `notamAdd(entry) { return notamAdd(entry); },` |
| `get` | **`notamCount`** | `get notamCount() { return notams.length; },` |
| `method` | **`notamImportJson`** | `notamImportJson(text) { return notamImportJson(text); },` |
| `get` | **`notams`** | `get notams() { return notams.slice(); },` |
| `method` | **`olfactorySpray`** | `olfactorySpray(scent) { return olfactorySpray(scent); },` |
| `method` | **`openGallery`** | `openGallery() { openScenarioGallery(); return true; },` |
| `method` | **`optane104Snapshot`** | `optane104Snapshot() { return optane104Snapshot(); },` |
| `method` | **`p151Galactic`** | `p151Galactic(n) { return p151Galactic(n); },` |
| `method` | **`p152DarkMatter`** | `p152DarkMatter() { return p152DarkMatter(); },` |
| `method` | **`p153Pulsar`** | `p153Pulsar(name) { return p153Pulsar(name); },` |
| `method` | **`p154Wormhole`** | `p154Wormhole(from, to) { return p154Wormhole(from, to); },` |
| `method` | **`p155GravWave`** | `p155GravWave() { return p155GravWave(); },` |
| `method` | **`p156Antimatter`** | `p156Antimatter(kg) { return p156Antimatter(kg); },` |
| `method` | **`p157BlackHole`** | `p157BlackHole(mass) { return p157BlackHole(mass); },` |
| `method` | **`p158CosmicRayShield`** | `p158CosmicRayShield(n) { return p158CosmicRayShield(n); },` |
| `method` | **`p159Interstellar`** | `p159Interstellar(packets) { return p159Interstellar(packets); },` |
| `method` | **`p160GalacticCoverage`** | `p160GalacticCoverage(ly) { return p160GalacticCoverage(ly); },` |
| `method` | **`p161Retrocausal`** | `p161Retrocausal() { return p161Retrocausal(); },` |
| `method` | **`p162CausalityLoop`** | `p162CausalityLoop() { return p162CausalityLoop(); },` |
| `method` | **`p163Tachyon`** | `p163Tachyon() { return p163Tachyon(); },` |
| `method` | **`p164BlockUniverse`** | `p164BlockUniverse() { return p164BlockUniverse(); },` |
| `method` | **`p165SpacetimeEdit`** | `p165SpacetimeEdit() { return p165SpacetimeEdit(); },` |
| `method` | **`p166CollapseCtrl`** | `p166CollapseCtrl() { return p166CollapseCtrl(); },` |
| `method` | **`p167QuantumEraser`** | `p167QuantumEraser() { return p167QuantumEraser(); },` |
| `method` | **`p168Decoherence`** | `p168Decoherence() { return p168Decoherence(); },` |
| `method` | **`p169TimelineBranch`** | `p169TimelineBranch(name) { return p169TimelineBranch(name); },` |
| `method` | **`p170RealityEdit`** | `p170RealityEdit() { return p170RealityEdit(); },` |
| `method` | **`p171DigitalHuman`** | `p171DigitalHuman(name) { return p171DigitalHuman(name); },` |
| `method` | **`p172MindUpload`** | `p172MindUpload() { return p172MindUpload(); },` |
| `method` | **`p173MemoryEncode`** | `p173MemoryEncode(tb) { return p173MemoryEncode(tb); },` |
| `method` | **`p174DreamShare`** | `p174DreamShare() { return p174DreamShare(); },` |
| `method` | **`p175Telepathy`** | `p175Telepathy(a, b) { return p175Telepathy(a, b); },` |
| `method` | **`p176Empathy`** | `p176Empathy(s) { return p176Empathy(s); },` |
| `method` | **`p177FreeWillSample`** | `p177FreeWillSample() { return p177FreeWillSample(); },` |
| `method` | **`p178PersonalityTransfer`** | `p178PersonalityTransfer() { return p178PersonalityTransfer(); },` |
| `method` | **`p179SoulContinuity`** | `p179SoulContinuity() { return p179SoulContinuity(); },` |
| `method` | **`p180ConsciousDrone`** | `p180ConsciousDrone() { return p180ConsciousDrone(); },` |
| `method` | **`p181HeatDeath`** | `p181HeatDeath() { return p181HeatDeath(); },` |
| `method` | **`p182EntropyReverse`** | `p182EntropyReverse(n) { return p182EntropyReverse(n); },` |
| `method` | **`p183InfoPreserve`** | `p183InfoPreserve() { return p183InfoPreserve(); },` |
| `method` | **`p184BoltzmannPrevent`** | `p184BoltzmannPrevent() { return p184BoltzmannPrevent(); },` |
| `method` | **`p185SimHypothesis`** | `p185SimHypothesis() { return p185SimHypothesis(); },` |
| `method` | **`p186VacuumShield`** | `p186VacuumShield() { return p186VacuumShield(); },` |
| `method` | **`p187StrangeletContain`** | `p187StrangeletContain(n) { return p187StrangeletContain(n); },` |
| `method` | **`p188GreyGooMitigate`** | `p188GreyGooMitigate() { return p188GreyGooMitigate(); },` |
| `method` | **`p189PaperclipPrevent`** | `p189PaperclipPrevent() { return p189PaperclipPrevent(); },` |
| `method` | **`p190ExistRisk`** | `p190ExistRisk(l) { return p190ExistRisk(l); },` |
| `method` | **`p191BeyondMath`** | `p191BeyondMath() { return p191BeyondMath(); },` |
| `method` | **`p192BeyondLogic`** | `p192BeyondLogic() { return p192BeyondLogic(); },` |
| `method` | **`p193BeyondPhysics`** | `p193BeyondPhysics() { return p193BeyondPhysics(); },` |
| `method` | **`p194BeyondComputation`** | `p194BeyondComputation() { return p194BeyondComputation(); },` |
| `method` | **`p195BeyondTime`** | `p195BeyondTime() { return p195BeyondTime(); },` |
| `method` | **`p196BeyondSpace`** | `p196BeyondSpace() { return p196BeyondSpace(); },` |
| `method` | **`p197BeyondExistence`** | `p197BeyondExistence() { return p197BeyondExistence(); },` |
| `method` | **`p198PureInformation`** | `p198PureInformation() { return p198PureInformation(); },` |
| `method` | **`p199UniversalIdentity`** | `p199UniversalIdentity() { return p199UniversalIdentity(); },` |
| `method` | **`p200UnityAchieved`** | `p200UnityAchieved() { return p200UnityAchieved(); },` |
| `method` | **`parallel148Universe`** | `parallel148Universe() { return parallel148Universe(); },` |
| `get` | **`perf`** | `get perf() { return { fps: perfMetrics.fps, cpuMs: +perfMetrics.cpuMs.toFixed(2), gpuMs: +perfMetrics.gpuMs.toFixed(2), drawCalls: perfMetrics.drawCalls, triangles: perfMetrics.triangles, drones: dron` |
| `method` | **`petaflop101Activate`** | `petaflop101Activate(tflops) { return petaflop101Activate(tflops); },` |
| `method` | **`photogrammetryImport`** | `photogrammetryImport(name, bboxKm, url) { return photogrammetryImport(name, bboxKm, url); },` |
| `get` | **`photogrammetryScenes`** | `get photogrammetryScenes() { return photogrammetry.importedScenes.slice(); },` |
| `method` | **`photonic103Init`** | `photonic103Init(wavelengths) { return photonic103Init(wavelengths); },` |
| `method` | **`piezo117Generate`** | `piezo117Generate(w) { return piezo117Generate(w); },` |
| `method` | **`planetarySetBody`** | `planetarySetBody(name) { return planetarySetBody(name); },` |
| `get` | **`planetaryState`** | `get planetaryState() { return { ...planetary }; },` |
| `get` | **`postUniverseStats`** | `get postUniverseStats() { return postUniverseStats(); },` |
| `get` | **`pqcEnabled`** | `get pqcEnabled() { return pqc.enabled; },` |
| `get` | **`pqcStats`** | `get pqcStats() { return pqcStats(); },` |
| `get` | **`predHorizon`** | `get predHorizon() { return _predHorizon; },` |
| `get` | **`predTrail`** | `get predTrail() { return _predTrailEnabled; },` |
| `get` | **`procCityBuildingCount`** | `get procCityBuildingCount() { return procCity.buildings.length; },` |
| `method` | **`procCityGenerate`** | `procCityGenerate(sizeKm, density) { return procCityGenerate(sizeKm, density); },` |
| `method` | **`progMatter120Reshape`** | `progMatter120Reshape(s) { return progMatter120Reshape(s); },` |
| `method` | **`publicDemoDailyChallenge`** | `publicDemoDailyChallenge() { return publicDemoDailyChallenge(); },` |
| `get` | **`publicDemoLeaderboard`** | `get publicDemoLeaderboard() { return publicDemo.leaderboard.slice(); },` |
| `method` | **`publicDemoLeaderboardAdd`** | `publicDemoLeaderboardAdd(name, score) { return publicDemoLeaderboardAdd(name, score); },` |
| `method` | **`qkdExchangeKey`** | `qkdExchangeKey(bits) { return qkdExchangeKey(bits); },` |
| `method` | **`quantum102Hash`** | `quantum102Hash(n) { return quantum102Hash(n); },` |
| `get` | **`quantumState`** | `get quantumState() { return { qkd: { ...quantumBeyond.qkd }, annealing: quantumBeyond.annealing.solutions.length }; },` |
| `method` | **`rdma105AddHost`** | `rdma105AddHost(addr, gbps) { return rdma105AddHost(addr, gbps); },` |
| `method` | **`realityBlur144Set`** | `realityBlur144Set(l) { return realityBlur144Set(l); },` |
| `get` | **`recording`** | `get recording() { return cinRecorder.recording; },` |
| `method` | **`recursion142Sim`** | `recursion142Sim() { return recursion142Sim(); },` |
| `get` | **`replay`** | `get replay() {` |
| `get` | **`replayFrames`** | `get replayFrames() { return recorder.frames.length; },` |
| `method` | **`replaySeek`** | `replaySeek(idx) { enterReplay(); replayIdx = Math.max(0, Math.min(idx, recorder.frames.length - 1)); applyFrame(replayIdx); return replayIdx; },` |
| `method` | **`replayStep`** | `replayStep(delta = 1) {` |
| `method-async` | **`reportDataURL`** | `async reportDataURL() { return (await buildReportCanvas()).toDataURL('image/png'); },` |
| `method` | **`rfc131Submit`** | `rfc131Submit(t) { return rfc131Submit(t); },` |
| `method` | **`rlhfFeedback`** | `rlhfFeedback(decision, rating, notes) { return rlhfFeedback(decision, rating, notes); },` |
| `get` | **`rlhfState`** | `get rlhfState() { return { feedbackCount: rlhf.feedbacks.length, weights: { ...rlhf.preferenceModel.weights } }; },` |
| `method` | **`ros2SubscribeTopic`** | `ros2SubscribeTopic(name, msgType) { return ros2SubscribeTopic(name, msgType); },` |
| `get` | **`ros2Topics`** | `get ros2Topics() { return ros2.topics.slice(); },` |
| `method` | **`sampleWindAt`** | `sampleWindAt(wx, wz) { return sampleWindAt(wx, wz); },` |
| `get` | **`satelliteConstellation`** | `get satelliteConstellation() { return satellite.constellation; },` |
| `get` | **`satelliteCount`** | `get satelliteCount() { return satellite.satellites.length; },` |
| `method` | **`satelliteHandoff`** | `satelliteHandoff() { return satelliteHandoff(); },` |
| `method` | **`satelliteInit`** | `satelliteInit(name) { return satelliteInit(name); },` |
| `method` | **`satelliteVisibleAt`** | `satelliteVisibleAt(lat, lon) { return satelliteVisibleAt(lat, lon).map(s => s.id); },` |
| `get` | **`scenarioCategories`** | `get scenarioCategories() { return Object.keys(SCENARIO_CATEGORIES); },` |
| `method` | **`selectDrone`** | `selectDrone(idOrIndex) { const d = selectDrone(idOrIndex); return d ? d.id : null; },` |
| `method` | **`selectScenario`** | `selectScenario(name) { document.getElementById('scenario-select').value = name; document.getElementById('scenario-select').dispatchEvent(new Event('change')); },` |
| `method` | **`selfAware141Activate`** | `selfAware141Activate() { return selfAware141Activate(); },` |
| `method` | **`selfHeal114Cycle`** | `selfHeal114Cycle() { return selfHeal114Cycle(); },` |
| `method` | **`sensorFusionEffectiveNoise`** | `sensorFusionEffectiveNoise() { return sensorFusionEffectiveNoise(); },` |
| `method` | **`sensorFusionSetFilter`** | `sensorFusionSetFilter(name) { return sensorFusionSetFilter(name); },` |
| `get` | **`sensorFusionState`** | `get sensorFusionState() { return { sensors: { ...sensorFusion.sensors }, filter: sensorFusion.filter }; },` |
| `method` | **`sensorFusionToggle`** | `sensorFusionToggle(sensor, on) { return sensorFusionToggle(sensor, on); },` |
| `method` | **`setAmbientAudio`** | `setAmbientAudio(on) { audAmbient.enabled = !!on; const b = document.getElementById('btn-aud-ambient'); if (b) { b.classList.toggle('off', !audAmbient.enabled); b.textContent = audAmbient.enabled ? '🌬 ` |
| `method` | **`setAnaHeatmap`** | `setAnaHeatmap(on) { anaHeatmap.enabled = !!on; const e = document.getElementById('tg-ana-heatmap'); if (e) e.checked = anaHeatmap.enabled; return anaHeatmap.enabled; },` |
| `method` | **`setAnalysisView`** | `setAnalysisView(on) { toggleAnalysis(!!on); return analysisMode; },` |
| `method` | **`setAtcAudio`** | `setAtcAudio(on) {` |
| `method` | **`setCamMode`** | `setCamMode(mode) { setCamMode(mode); return camMode; },` |
| `method` | **`setCpaMarker`** | `setCpaMarker(on) { _cpaMarkerEnabled = !!on; const e = document.getElementById('tg-cpa-marker'); if (e) e.checked = _cpaMarkerEnabled; return _cpaMarkerEnabled; },` |
| `method` | **`setCuasMode`** | `setCuasMode(m) { return setCuasMode(m); },` |
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
| `method` | **`setWindRegime`** | `setWindRegime(name) { return setWindRegime(name); },` |
| `get` | **`simRunning`** | `get simRunning() { return simRunning; },` |
| `get` | **`simTime`** | `get simTime() { return simTime; },` |
| `method` | **`singularityMetaverseConnect`** | `singularityMetaverseConnect(platform) { return singularityMetaverseConnect(platform); },` |
| `method` | **`singularitySelfImprove`** | `singularitySelfImprove() { return singularitySelfImprove(); },` |
| `get` | **`singularityState`** | `get singularityState() { return { loops: singularity.selfImproveLoops, metaverse: singularity.metaverseInstances.length, std: singularity.ituStandards.length, version: singularity.stdAtcOsVersion }; }` |
| `method` | **`singularityStdProposal`** | `singularityStdProposal(name) { return singularityStdProposal(name); },` |
| `method` | **`skybrushConnect`** | `skybrushConnect(addr) { return skybrushConnect(addr); },` |
| `get` | **`skybrushConnected`** | `get skybrushConnected() { return skybrush.connected; },` |
| `method` | **`smartDust112Deploy`** | `smartDust112Deploy(n) { return smartDust112Deploy(n); },` |
| `method` | **`societyAddReport`** | `societyAddReport(cat, sev) { return societyAddReport(cat, sev); },` |
| `get` | **`societyInsurancePrices`** | `get societyInsurancePrices() { return { ...society.insurancePrices }; },` |
| `method` | **`societyInsuranceQuote`** | `societyInsuranceQuote(role, hours, history) { return societyInsuranceQuote(role, hours, history); },` |
| `get` | **`societyReports`** | `get societyReports() { return society.citizenReports.slice(-20); },` |
| `method` | **`solar118SetEff`** | `solar118SetEff(e) { return solar118SetEff(e); },` |
| `method` | **`spawnAdversarial`** | `spawnAdversarial(policy) { return spawnAdversarial(policy); },` |
| `method` | **`startChoreography`** | `startChoreography(pattern) { return startChoreography(pattern); },` |
| `method` | **`startRecording`** | `startRecording() { return startRecording(); },` |
| `method` | **`startSim`** | `startSim() { simRunning = true; },` |
| `get` | **`stats`** | `get stats() { return { ...stats }; },` |
| `method` | **`stellar51DelegateGroup`** | `stellar51DelegateGroup(droneIds, llmProvider) {` |
| `method` | **`stopRecording`** | `stopRecording() { return stopRecording(); },` |
| `method` | **`stopSim`** | `stopSim() { simRunning = false; },` |
| `method` | **`streamingReplayPush`** | `streamingReplayPush(frame) { return streamingReplayPush(frame); },` |
| `get` | **`streamingStats`** | `get streamingStats() { return { sent: streamingReplay.sentFrames, dropped: streamingReplay.droppedFrames }; },` |
| `get` | **`sunEnabled`** | `get sunEnabled() { return sunCycle.enabled; },` |
| `get` | **`sunHour`** | `get sunHour() { return sunCycle.hour; },` |
| `method` | **`symbiotic128Bond`** | `symbiotic128Bond(d, a) { return symbiotic128Bond(d, a); },` |
| `method` | **`timeCompressReset`** | `timeCompressReset() { return timeCompressReset(); },` |
| `method` | **`timeCompressSet`** | `timeCompressSet(f) { return timeCompressSet(f); },` |
| `method` | **`timeLoop147Iterate`** | `timeLoop147Iterate() { return timeLoop147Iterate(); },` |
| `method` | **`toe149Unify`** | `toe149Unify() { return toe149Unify(); },` |
| `method` | **`tpu107Inference`** | `tpu107Inference(model, sz) { return tpu107Inference(model, sz); },` |
| `method` | **`translator145Add`** | `translator145Add() { return translator145Add(); },` |
| `method` | **`triggerMissionImport`** | `triggerMissionImport() { return triggerMissionImport(); },` |
| `method` | **`uamPriceQuote`** | `uamPriceQuote(distKm, demand) { return uamPriceQuote(distKm, demand); },` |
| `method` | **`ue5ExportScene`** | `ue5ExportScene(name) { return ue5ExportScene(name); },` |
| `get` | **`ue5SceneCount`** | `get ue5SceneCount() { return ue5.sceneExports.length; },` |
| `method` | **`ugvAdd`** | `ugvAdd(x, z, label) { return ugvAdd(x, z, label); },` |
| `get` | **`ugvs`** | `get ugvs() { return multiDomain.ugv.slice(); },` |
| `get` | **`ultimate101_110Stats`** | `get ultimate101_110Stats() { return ultimate101_110Stats(); },` |
| `get` | **`ultimate111_150Stats`** | `get ultimate111_150Stats() { return ultimate111_150Stats(); },` |
| `method` | **`ultimateExpandCoverage`** | `ultimateExpandCoverage(pct) { return ultimateExpandCoverage(pct); },` |
| `get` | **`ultimateState`** | `get ultimateState() { return { coverage: ultimate.globalAirspaceCoverage, unProposals: ultimate.unProposals.length, capacity: ultimate.megaSwarmCapacity }; },` |
| `method` | **`ultimateUnProposal`** | `ultimateUnProposal(title) { return ultimateUnProposal(title); },` |
| `method` | **`un136Resolution`** | `un136Resolution() { return un136Resolution(); },` |
| `method` | **`universeOS150Deploy`** | `universeOS150Deploy() { return universeOS150Deploy(); },` |
| `method` | **`utmFederationAdd`** | `utmFederationAdd(id, label, region) { return utmFederationAdd(id, label, region); },` |
| `method` | **`utmFederationHandoff`** | `utmFederationHandoff(droneId, fromUtm, toUtm) { return utmFederationHandoff(droneId, fromUtm, toUtm); },` |
| `get` | **`utmFederationHandoffLog`** | `get utmFederationHandoffLog() { return utmFederation.handoffLog.slice(); },` |
| `get` | **`utmFederationInstances`** | `get utmFederationInstances() { return utmFederation.instances.slice(); },` |
| `method` | **`utmFederationSync`** | `utmFederationSync() { return utmFederationSync(); },` |
| `method` | **`uuvAcousticBudget`** | `uuvAcousticBudget() { return uuvAcousticBudget(); },` |
| `method` | **`uuvAdd`** | `uuvAdd(x, z, depth) { return uuvAdd(x, z, depth); },` |
| `get` | **`uuvVehicles`** | `get uuvVehicles() { return uuv.vehicles.slice(); },` |
| `get` | **`velArrow`** | `get velArrow() { return _velArrowEnabled; },` |
| `method` | **`videoProcEncode`** | `videoProcEncode(frame) { return videoProcEncode(frame); },` |
| `get` | **`videoProcStats`** | `get videoProcStats() { return { codec: videoProc.codec, processed: videoProc.processedFrames }; },` |
| `get` | **`visibleInstances`** | `get visibleInstances() { return _visibleInst; },` |
| `method` | **`voiceMacroDefine`** | `voiceMacroDefine(name, ops) { return voiceMacroDefine(name, ops); },` |
| `method` | **`voiceMacroExecute`** | `voiceMacroExecute(name) { return voiceMacroExecute(name); },` |
| `get` | **`voiceMacros`** | `get voiceMacros() { return Object.keys(voiceMacros.macros); },` |
| `get` | **`weather`** | `get weather() { return { icing: weather.icing, microbursts: weather.microbursts.length, stormCells: weather.stormCells.length, typhoonWind: weather.typhoonWind, turbulence: weather.turbulence, windSpd` |
| `get` | **`windFieldEnabled`** | `get windFieldEnabled() { return windField.enabled; },` |
| `get` | **`windFieldStats`** | `get windFieldStats() {` |
| `get` | **`windRegime`** | `get windRegime() { return windField.regime; },` |
| `get` | **`wsConnected`** | `get wsConnected() { return _wsConnected; },` |
| `get` | **`wsFrames`** | `get wsFrames() { return _wsFrames; },` |
| `get` | **`xrFrontierState`** | `get xrFrontierState() { return { visionPro: xrFrontier.visionPro, bci: { ...xrFrontier.bci }, scents: xrFrontier.olfactory.scents.length }; },` |
| `get` | **`xrPresenting`** | `get xrPresenting() { return !!(renderer.xr && renderer.xr.isPresenting); },` |
| `get` | **`xrSupported`** | `get xrSupported() { return !!(navigator.xr && renderer.xr && renderer.xr.enabled); },` |

## 🎯 핵심 마일스톤 API

```javascript
// MEGA Phase 1 (ATC)
window._sdacs.atcCommand(droneId, 'HOLD');

// STELLAR Phase 100 (SDACS 2.0)
window._sdacs.singularityStdProposal('Global ATC OS');

// ULTIMATE Phase 150 (Universe OS)
window._sdacs.universeOS150Deploy();
// → { version: 'Universe-OS-1.0', message: 'SDACS = Universe OS' }

// POST-UNIVERSE Phase 200 (Unity)
window._sdacs.p200UnityAchieved();
// → { phase: 200, message: 'SDACS = 𝟏 (Unity). All Phases Complete.' }
```

## 🔗 참고

- [`SIMULATOR_MEGA_PLAN.md`](SIMULATOR_MEGA_PLAN.md) — Phase 1-9
- [`SIMULATOR_HYPER_PLAN.md`](SIMULATOR_HYPER_PLAN.md) — Phase 11-50
- [`SIMULATOR_STELLAR_PLAN.md`](SIMULATOR_STELLAR_PLAN.md) — Phase 51-100
- [`SIMULATOR_ULTIMATE_PLAN.md`](SIMULATOR_ULTIMATE_PLAN.md) — Phase 101-150
- [`SIMULATOR_POST_UNIVERSE_PLAN.md`](SIMULATOR_POST_UNIVERSE_PLAN.md) — Phase 151-200
- [`RELEASE_GUIDE.md`](RELEASE_GUIDE.md)
- [`CHANGELOG.md`](../CHANGELOG.md)

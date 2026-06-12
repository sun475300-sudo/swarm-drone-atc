# 📒 SDACS 기술 부채 대장 (GENESIS Phase 388)

*자동 생성: 2026-06-12 (`scripts/extract_sdacs_api.py --ledger` 라이브 실측)*

> 정직성 공시: 아래 API는 **결정적 mock 또는 speculative 스텁**이다. 인터페이스는 안정적이나 실측 알고리즘/외부 연동이 없다. 호출 시 console.warn 1회 + `maturityReport().mockCalls` 카운트 (Phase 203 Mock Detector).

## 요약 — mock 110 + speculative 103 = 213 항목

| 구분 | 의미 | 격상 경로 |
|---|---|---|
| 🟡 mock (110) | 결정적 가짜 구현 | TRANSCENDENCE Track 🔬 (221-240) 실측 교체 |
| ⚪ speculative (103) | 미래 비전 스텁 | `_sdacs.experimental.*` 격리 (Phase 206) — 격상 비목표 |

## 🟡 mock 그룹별 격상 난이도

| 접두사 그룹 | API 수 | 난이도 | 격상 메모 |
|---|:-:|:-:|---|
| `annealing*` | 1 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `audio*` | 3 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `bci*` | 1 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `beyond*` | 3 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `causal*` | 3 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `cesium*` | 2 | ⭐⭐⭐ | Cesium ion 토큰 + 외부 타일셋 의존 |
| `climate*` | 1 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `cloud*` | 2 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `cross*` | 2 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `dao*` | 1 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `distributed*` | 2 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `economy*` | 1 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `esports*` | 3 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `explain*` | 2 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `eye*` | 3 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `fed*` | 3 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `gpu*` | 2 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `hitl*` | 3 | ⭐⭐⭐⭐ | 실 Pixhawk HW 필요 (TRANSCENDENCE 261-270) |
| `isaac*` | 2 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `mec*` | 4 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `multi*` | 2 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `national*` | 3 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `olfactory*` | 1 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `photogrammetry*` | 2 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `planetary*` | 2 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `proc*` | 2 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `public*` | 3 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `qkd*` | 1 | ⭐⭐⭐⭐⭐ | 실 양자 채널 없음 — 영구 mock 후보 |
| `quantum*` | 1 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `rlhf*` | 2 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `ros*` | 2 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `satellite*` | 5 | ⭐⭐⭐⭐⭐ | 위성 링크 — 영구 mock 후보 |
| `sensor*` | 4 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `singularity*` | 4 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `skybrush*` | 2 | ⭐⭐⭐ | Skybrush 라이브러리 통합 |
| `society*` | 4 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `stellar*` | 6 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `streaming*` | 1 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `time*` | 2 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `uam*` | 1 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `ue*` | 2 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `ugv*` | 1 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `ugvs*` | 1 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `ultimate*` | 3 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `uuv*` | 3 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `video*` | 2 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `voice*` | 3 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |
| `xr*` | 1 | ⭐⭐ | 결정적 mock — 실 데이터/라이브러리 연결로 격상 가능 |

## 🟡 mock 전체 목록

<details><summary>펼치기</summary>

- `annealingSolve`
- `audioDopplerShift`
- `audioEngineState`
- `audioSetListener`
- `bciActivate`
- `beyondEarthAddDebris`
- `beyondEarthSetMode`
- `beyondEarthState`
- `causalAddEdge`
- `causalDag`
- `causalDoQuery`
- `cesiumGlobalInit`
- `cesiumGlobalState`
- `climateScore`
- `cloudBurstScale`
- `cloudBurstState`
- `crossBorderTransit`
- `crossBorderTransitsLog`
- `daoCreateProposal`
- `distributedSimAddShard`
- `distributedSimRebalance`
- `economyState`
- `esportsAddPlayer`
- `esportsPlayers`
- `esportsScore`
- `explainDecision`
- `explainLastMethod`
- `eyeTrackAdd`
- `eyeTrackBuildHeatmap`
- `eyeTrackPointCount`
- `fedLearnHistory`
- `fedLearnRound`
- `fedLearnState`
- `gpu100kInit`
- `gpu100kStats`
- `hitlAdd`
- `hitlConnect`
- `hitlNodes`
- `isaacSimLoadUSD`
- `isaacSimState`
- `mecAdd`
- `mecAssign`
- `mecNodes`
- `mecWorkloads`
- `multiDomainHandoff`
- `multiDomainHandoffLog`
- `nationalASAddAirport`
- `nationalASAirports`
- `nationalASInitKorea`
- `olfactorySpray`
- `photogrammetryImport`
- `photogrammetryScenes`
- `planetarySetBody`
- `planetaryState`
- `procCityBuildingCount`
- `procCityGenerate`
- `publicDemoDailyChallenge`
- `publicDemoLeaderboard`
- `publicDemoLeaderboardAdd`
- `qkdExchangeKey`
- `quantumState`
- `rlhfFeedback`
- `rlhfState`
- `ros2SubscribeTopic`
- `ros2Topics`
- `satelliteConstellation`
- `satelliteCount`
- `satelliteHandoff`
- `satelliteInit`
- `satelliteVisibleAt`
- `sensorFusionEffectiveNoise`
- `sensorFusionSetFilter`
- `sensorFusionState`
- `sensorFusionToggle`
- `singularityMetaverseConnect`
- `singularitySelfImprove`
- `singularityState`
- `singularityStdProposal`
- `skybrushConnect`
- `skybrushConnected`
- `societyAddReport`
- `societyInsurancePrices`
- `societyInsuranceQuote`
- `societyReports`
- `stellar51DelegateGroup`
- `stellar51DelegatedGroups`
- `stellar51Groups`
- `stellar51Recommend`
- `stellar51Revoke`
- `stellar51Tick`
- `streamingReplayPush`
- `timeCompressReset`
- `timeCompressSet`
- `uamPriceQuote`
- `ue5ExportScene`
- `ue5SceneCount`
- `ugvAdd`
- `ugvs`
- `ultimateExpandCoverage`
- `ultimateState`
- `ultimateUnProposal`
- `uuvAcousticBudget`
- `uuvAdd`
- `uuvVehicles`
- `videoProcEncode`
- `videoProcStats`
- `voiceMacroDefine`
- `voiceMacroExecute`
- `voiceMacros`
- `xrFrontierState`

</details>

## ⚪ speculative 전체 목록 (experimental.* 경유 접근)

<details><summary>펼치기</summary>

- `algae124Power`
- `atmo116Harvest`
- `bacteria123Spawn`
- `bioDeg115SetLife`
- `biofluor129Emit`
- `bird126Partner`
- `caac139Compat`
- `consciousness143Experiment`
- `dna122Store`
- `dpu109Offload`
- `easa137Integrate`
- `eternalMission146Start`
- `faa138Part108`
- `fpga106AddInstance`
- `global140Adopt`
- `graphene113Boost`
- `icao132Adopt`
- `ieee134Standard`
- `insect127Join`
- `iso133Cert`
- `itu135AllocateFreq`
- `living130Spawn`
- `megaScale110SetCurrent`
- `meta119Activate`
- `mycelium125Repair`
- `nano111Spawn`
- `neuromorphic108Spike`
- `neuron121Connect`
- `optane104Snapshot`
- `p151Galactic`
- `p152DarkMatter`
- `p153Pulsar`
- `p154Wormhole`
- `p155GravWave`
- `p156Antimatter`
- `p157BlackHole`
- `p158CosmicRayShield`
- `p159Interstellar`
- `p160GalacticCoverage`
- `p161Retrocausal`
- `p162CausalityLoop`
- `p163Tachyon`
- `p164BlockUniverse`
- `p165SpacetimeEdit`
- `p166CollapseCtrl`
- `p167QuantumEraser`
- `p168Decoherence`
- `p169TimelineBranch`
- `p170RealityEdit`
- `p171DigitalHuman`
- `p172MindUpload`
- `p173MemoryEncode`
- `p174DreamShare`
- `p175Telepathy`
- `p176Empathy`
- `p177FreeWillSample`
- `p178PersonalityTransfer`
- `p179SoulContinuity`
- `p180ConsciousDrone`
- `p181HeatDeath`
- `p182EntropyReverse`
- `p183InfoPreserve`
- `p184BoltzmannPrevent`
- `p185SimHypothesis`
- `p186VacuumShield`
- `p187StrangeletContain`
- `p188GreyGooMitigate`
- `p189PaperclipPrevent`
- `p190ExistRisk`
- `p191BeyondMath`
- `p192BeyondLogic`
- `p193BeyondPhysics`
- `p194BeyondComputation`
- `p195BeyondTime`
- `p196BeyondSpace`
- `p197BeyondExistence`
- `p198PureInformation`
- `p199UniversalIdentity`
- `p200UnityAchieved`
- `parallel148Universe`
- `petaflop101Activate`
- `photonic103Init`
- `piezo117Generate`
- `postUniverseStats`
- `progMatter120Reshape`
- `quantum102Hash`
- `rdma105AddHost`
- `realityBlur144Set`
- `recursion142Sim`
- `rfc131Submit`
- `selfAware141Activate`
- `selfHeal114Cycle`
- `smartDust112Deploy`
- `solar118SetEff`
- `symbiotic128Bond`
- `timeLoop147Iterate`
- `toe149Unify`
- `tpu107Inference`
- `translator145Add`
- `ultimate101_110Stats`
- `ultimate111_150Stats`
- `un136Resolution`
- `universeOS150Deploy`

</details>

## 🔗 관련
- [`SDACS_API.md`](SDACS_API.md) — 전체 API maturity 레퍼런스
- [`SIMULATOR_TRANSCENDENCE_PLAN.md`](SIMULATOR_TRANSCENDENCE_PLAN.md) — 격상 로드맵 (Track 🔬)
- [`SIMULATOR_GENESIS_PLAN.md`](SIMULATOR_GENESIS_PLAN.md) — Phase 388 본 대장 정의

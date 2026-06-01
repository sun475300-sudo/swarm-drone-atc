// Phase 528 — Cooperative Perception Module: Sensor Fusion and Detection
// F# module implementing multi-drone cooperative perception with sensor data fusion.

module CooperativePerception

open System

// ===== Types =====

/// Detection result from a single drone sensor
type Detection = {
    DroneId: string
    ObjectId: string
    X: float
    Y: float
    Z: float
    Confidence: float
    Timestamp: float
    SensorType: string
}

/// Fused perception result combining multiple detections
type FusedObservation = {
    ObjectId: string
    X: float
    Y: float
    Z: float
    AggregatedConfidence: float
    SourceCount: int
    Timestamp: float
}

/// Sensor model for a single drone
type SensorModel = {
    DroneId: string
    Range: float
    FieldOfView: float     // degrees
    NoiseStd: float
    DetectionRate: float   // probability of detecting a target in range
}

/// Fusion configuration
type FusionConfig = {
    MinConfidence: float
    MaxPositionError: float
    WeightByConfidence: bool
}

/// Perception state for the cooperative swarm
type PerceptionState = {
    Detections: Detection list
    FusedObservations: FusedObservation list
    StepCount: int
    DroneCount: int
}

// ===== Sensor Utilities =====

let defaultFusionConfig = {
    MinConfidence = 0.3
    MaxPositionError = 5.0
    WeightByConfidence = true
}

/// Compute Euclidean distance between two detections
let distance (d1: Detection) (d2: Detection) =
    let dx = d1.X - d2.X
    let dy = d1.Y - d2.Y
    let dz = d1.Z - d2.Z
    Math.Sqrt(dx*dx + dy*dy + dz*dz)

/// Simulate a drone detecting a target (stub)
let simulateDetection (sensor: SensorModel) (targetId: string) (tx: float) (ty: float) (tz: float) (t: float) =
    let rng = Random(sensor.DroneId.GetHashCode() + int t)
    let noise () = (rng.NextDouble() - 0.5) * 2.0 * sensor.NoiseStd
    let detected = rng.NextDouble() < sensor.DetectionRate
    if detected then
        Some {
            DroneId = sensor.DroneId
            ObjectId = targetId
            X = tx + noise()
            Y = ty + noise()
            Z = tz + noise()
            Confidence = 0.5 + rng.NextDouble() * 0.5
            Timestamp = t
            SensorType = "camera"
        }
    else None

// ===== Sensor Fusion =====

/// Group detections by object ID for fusion
let groupByObject (detections: Detection list) =
    detections
    |> List.groupBy (fun d -> d.ObjectId)
    |> Map.ofList

/// Fuse multiple detections of the same object using weighted average
let fuseDetections (config: FusionConfig) (objectId: string) (dets: Detection list) : FusedObservation option =
    let valid = dets |> List.filter (fun d -> d.Confidence >= config.MinConfidence)
    if valid.IsEmpty then None
    else
        let totalWeight =
            if config.WeightByConfidence then valid |> List.sumBy (fun d -> d.Confidence)
            else float valid.Length

        let weightFn d = if config.WeightByConfidence then d.Confidence else 1.0

        let fusedX = valid |> List.sumBy (fun d -> d.X * weightFn d) |> fun s -> s / totalWeight
        let fusedY = valid |> List.sumBy (fun d -> d.Y * weightFn d) |> fun s -> s / totalWeight
        let fusedZ = valid |> List.sumBy (fun d -> d.Z * weightFn d) |> fun s -> s / totalWeight
        let aggConf = Math.Min(1.0, valid |> List.averageBy (fun d -> d.Confidence) * Math.Sqrt(float valid.Length))
        let latestTs = valid |> List.maxBy (fun d -> d.Timestamp) |> fun d -> d.Timestamp

        Some {
            ObjectId = objectId
            X = fusedX
            Y = fusedY
            Z = fusedZ
            AggregatedConfidence = aggConf
            SourceCount = valid.Length
            Timestamp = latestTs
        }

/// Run full sensor fusion over all detections
let runFusion (config: FusionConfig) (detections: Detection list) : FusedObservation list =
    groupByObject detections
    |> Map.toList
    |> List.choose (fun (objId, dets) -> fuseDetections config objId dets)

// ===== Perception System =====

/// Initialize perception state
let initState (droneCount: int) : PerceptionState =
    { Detections = []; FusedObservations = []; StepCount = 0; DroneCount = droneCount }

/// Add detections to state and run fusion
let processDetections (config: FusionConfig) (state: PerceptionState) (newDets: Detection list) : PerceptionState =
    let allDets = state.Detections @ newDets
    let fused = runFusion config allDets
    { state with
        Detections = allDets
        FusedObservations = fused
        StepCount = state.StepCount + 1 }

/// Get summary statistics
let summary (state: PerceptionState) =
    let avgConf =
        if state.FusedObservations.IsEmpty then 0.0
        else state.FusedObservations |> List.averageBy (fun o -> o.AggregatedConfidence)
    printfn "Phase 528 CooperativePerception | Drones: %d | Detections: %d | Fused objects: %d | Avg conf: %.2f"
        state.DroneCount state.Detections.Length state.FusedObservations.Length avgConf
    avgConf

// ===== Entry Point =====
[<EntryPoint>]
let main _ =
    printfn "Phase 528: Cooperative Perception with Sensor Fusion"

    let sensors = [
        { DroneId = "D1"; Range = 100.0; FieldOfView = 60.0; NoiseStd = 1.5; DetectionRate = 0.8 }
        { DroneId = "D2"; Range = 120.0; FieldOfView = 45.0; NoiseStd = 1.0; DetectionRate = 0.9 }
        { DroneId = "D3"; Range = 80.0;  FieldOfView = 90.0; NoiseStd = 2.0; DetectionRate = 0.7 }
    ]

    let targets = [("T1", 50.0, 30.0, 100.0); ("T2", 80.0, 60.0, 95.0)]
    let mutable state = initState sensors.Length
    let config = defaultFusionConfig

    for t in 0..4 do
        let newDets =
            [ for sensor in sensors do
                for (tid, tx, ty, tz) in targets do
                    match simulateDetection sensor tid tx ty tz (float t) with
                    | Some d -> yield d
                    | None -> () ]
        state <- processDetections config state newDets

    let _ = summary state
    0

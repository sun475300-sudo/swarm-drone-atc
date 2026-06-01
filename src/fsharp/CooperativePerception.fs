// Phase 528: Cooperative Perception — 군집 드론 협력 지각 (F#)
// Sensor fusion and cooperative object detection for drone swarms.
module SDACS.CooperativePerception

open System
open System.Collections.Generic

let PHASE = 528

// ── Detection types ────────────────────────────────────────────────

type ObjectClass =
    | Drone | Building | Vehicle | Person | Unknown

type Detection = {
    Id        : int
    DroneId   : int
    Class     : ObjectClass
    X         : float
    Y         : float
    Z         : float
    Confidence: float
    Timestamp : DateTime
}

// ── Sensor fusion types ────────────────────────────────────────────

type FusionMethod = WeightedAverage | KalmanFusion | BayesianFusion

type FusedObject = {
    TrackId   : int
    Class     : ObjectClass
    X         : float
    Y         : float
    Z         : float
    Confidence: float
    Sources   : int list   // drone IDs that contributed
}

// ── Fusion algorithms ──────────────────────────────────────────────

/// Weighted-average fusion of detections from multiple drones.
let fuseDetections (detections: Detection list) (trackId: int) : FusedObject =
    if detections.IsEmpty then
        failwith "No detections to fuse"
    let totalConf = detections |> List.sumBy (fun d -> d.Confidence)
    let wx = detections |> List.sumBy (fun d -> d.X * d.Confidence)
    let wy = detections |> List.sumBy (fun d -> d.Y * d.Confidence)
    let wz = detections |> List.sumBy (fun d -> d.Z * d.Confidence)
    let cls = detections |> List.maxBy (fun d -> d.Confidence) |> (fun d -> d.Class)
    {
        TrackId    = trackId
        Class      = cls
        X          = wx / totalConf
        Y          = wy / totalConf
        Z          = wz / totalConf
        Confidence = min 1.0 (totalConf / float detections.Length)
        Sources    = detections |> List.map (fun d -> d.DroneId) |> List.distinct
    }

/// Cluster nearby detections (greedy, threshold-based).
let clusterDetections (dets: Detection list) (threshold: float) : Detection list list =
    let used = Array.create dets.Length false
    let clusters = ResizeArray<Detection list>()
    let dets_arr = List.toArray dets
    for i in 0 .. dets_arr.Length - 1 do
        if not used.[i] then
            let cluster = ResizeArray<Detection>()
            cluster.Add(dets_arr.[i])
            used.[i] <- true
            for j in i+1 .. dets_arr.Length - 1 do
                if not used.[j] then
                    let dx = dets_arr.[i].X - dets_arr.[j].X
                    let dy = dets_arr.[i].Y - dets_arr.[j].Y
                    let dz = dets_arr.[i].Z - dets_arr.[j].Z
                    let dist = sqrt (dx*dx + dy*dy + dz*dz)
                    if dist < threshold then
                        cluster.Add(dets_arr.[j])
                        used.[j] <- true
            clusters.Add(List.ofSeq cluster)
    List.ofSeq clusters

// ── Cooperative Perception Engine ─────────────────────────────────

type CooperativePerceptionEngine(nDrones: int, seed: int) =
    let rng = Random(seed)
    let mutable tracks : FusedObject list = []
    let mutable allDetections : Detection list = []
    let mutable detectionCount = 0

    /// Simulate detections from all drones in the fleet.
    member _.GenerateDetections(nObjects: int) =
        let dets = ResizeArray<Detection>()
        for obj_i in 0 .. nObjects - 1 do
            let true_x = rng.NextDouble() * 500.0
            let true_y = rng.NextDouble() * 500.0
            let true_z = 50.0 + rng.NextDouble() * 50.0
            for d in 0 .. nDrones - 1 do
                let noise = 2.0
                let conf  = 0.6 + rng.NextDouble() * 0.4
                dets.Add {
                    Id         = detectionCount
                    DroneId    = d
                    Class      = if obj_i % 3 = 0 then Drone else Vehicle
                    X          = true_x + (rng.NextDouble() - 0.5) * noise
                    Y          = true_y + (rng.NextDouble() - 0.5) * noise
                    Z          = true_z + (rng.NextDouble() - 0.5) * noise * 0.3
                    Confidence = conf
                    Timestamp  = DateTime.UtcNow
                }
                detectionCount <- detectionCount + 1
        allDetections <- List.ofSeq dets

    /// Fuse all current detections into tracks.
    member _.FuseAll() =
        let clusters = clusterDetections allDetections 15.0
        tracks <- clusters |> List.mapi (fun i cluster -> fuseDetections cluster i)

    member _.Tracks = tracks
    member _.DetectionCount = detectionCount

    member _.Summary() =
        Map [
            "phase",       box PHASE
            "drones",      box nDrones
            "detections",  box detectionCount
            "tracks",      box tracks.Length
        ]

// ── Entry point ───────────────────────────────────────────────────

[<EntryPoint>]
let main _ =
    printfn "Phase %d: Cooperative Perception — 협력 드론 지각 및 센서 융합 (Fusion)" PHASE
    let engine = CooperativePerceptionEngine(5, 42)
    engine.GenerateDetections(8)
    engine.FuseAll()
    printfn "Detections: %d, Fused tracks: %d" engine.DetectionCount engine.Tracks.Length
    0

// Phase 528 — Cooperative perception with sensor fusion and Detection for drone swarm.
// Multiple drones share object Detection reports; a central fusion layer merges them
// into a unified environmental picture for airspace deconfliction.

namespace SDACS.Perception

open System
open System.Collections.Generic

// ---- Phase marker ----
[<Literal>]
let PhaseMarker = 528

// ---- Object Detection report from a single drone sensor ----
[<Struct>]
type BoundingBox = { X: float; Y: float; Z: float; Width: float; Height: float; Depth: float }

type DetectionClass =
    | UnknownObject
    | DroneHostile
    | DroneAllied
    | StaticObstacle
    | WeatherPhenomenon

/// A single-drone Detection event.
type DetectionReport = {
    DroneId       : string
    Timestamp     : DateTimeOffset
    ObjectClass   : DetectionClass
    BoundingBox   : BoundingBox
    Confidence    : float          // [0.0, 1.0]
    SensorType    : string         // "lidar" | "camera" | "radar"
}

// ---- Fused track (output of the fusion layer) ----
type FusedTrack = {
    TrackId       : Guid
    Position      : float * float * float   // fused centroid (x, y, z)
    ObjectClass   : DetectionClass
    FusedConfidence : float
    ContributingDrones : string list
    LastUpdated   : DateTimeOffset
}

// ---- Spatial helper: 3D Euclidean distance ----
let private distance3d (ax, ay, az) (bx, by, bz) =
    let dx = ax - bx
    let dy = ay - by
    let dz = az - bz
    Math.Sqrt(dx*dx + dy*dy + dz*dz)

let private centroid (box: BoundingBox) =
    (box.X + box.Width  / 2.0,
     box.Y + box.Height / 2.0,
     box.Z + box.Depth  / 2.0)

// ---- Weighted centroid fusion of multiple bounding boxes ----
/// Fuse a list of (weight, position) tuples into a single weighted centroid.
let private weightedCentroid (weighted: (float * (float * float * float)) list) =
    let totalWeight = weighted |> List.sumBy fst
    if totalWeight < 1e-9 then (0.0, 0.0, 0.0)
    else
        let sumX = weighted |> List.sumBy (fun (w, (x, _, _)) -> w * x)
        let sumY = weighted |> List.sumBy (fun (w, (_, y, _)) -> w * y)
        let sumZ = weighted |> List.sumBy (fun (w, (_, _, z)) -> w * z)
        (sumX / totalWeight, sumY / totalWeight, sumZ / totalWeight)

// ---- Confidence fusion: product rule (independent sensors) ----
let private fuseConfidences (confidences: float list) =
    // Use product of (1 - false-alarm probability) as combined confidence
    let combined = confidences |> List.fold (fun acc c -> acc * c) 1.0
    combined

// ---- Detection fusion engine ----

/// Association threshold: Detection reports within this 3D distance (metres)
/// are considered to observe the same object.
[<Literal>]
let AssociationThresholdMetres = 5.0

type FusionEngine() =
    let tracks = Dictionary<Guid, FusedTrack>()
    let mutable nextTick = DateTimeOffset.UtcNow

    /// Fuse a batch of Detection reports into the track registry.
    member _.Fuse(reports: DetectionReport list) : FusedTrack list =
        if reports.IsEmpty then []
        else
            // Group reports by proximity (greedy single-linkage clustering)
            let clusters = ResizeArray<ResizeArray<DetectionReport>>()
            for report in reports do
                let pos = centroid report.BoundingBox
                let matched =
                    clusters
                    |> Seq.tryFind (fun cluster ->
                        cluster
                        |> Seq.exists (fun r ->
                            distance3d (centroid r.BoundingBox) pos < AssociationThresholdMetres))
                match matched with
                | Some cluster -> cluster.Add(report)
                | None         ->
                    let c = ResizeArray<DetectionReport>()
                    c.Add(report)
                    clusters.Add(c)

            // Build a FusedTrack per cluster
            let newTracks =
                clusters
                |> Seq.map (fun cluster ->
                    let rpts = cluster |> Seq.toList
                    let weighted =
                        rpts |> List.map (fun r -> (r.Confidence, centroid r.BoundingBox))
                    let pos = weightedCentroid weighted
                    let fusedConf = fuseConfidences (rpts |> List.map _.Confidence)
                    let dominantClass =
                        rpts
                        |> List.groupBy _.ObjectClass
                        |> List.maxBy (fun (_, g) -> g |> List.sumBy _.Confidence)
                        |> fst
                    {
                        TrackId             = Guid.NewGuid()
                        Position            = pos
                        ObjectClass         = dominantClass
                        FusedConfidence     = fusedConf
                        ContributingDrones  = rpts |> List.map _.DroneId |> List.distinct
                        LastUpdated         = DateTimeOffset.UtcNow
                    })
                |> Seq.toList

            // Merge into track registry (upsert by nearest existing track)
            for track in newTracks do
                let existingKey =
                    tracks.Keys
                    |> Seq.tryFind (fun k ->
                        distance3d tracks.[k].Position track.Position < AssociationThresholdMetres)
                match existingKey with
                | Some k -> tracks.[k] <- { track with TrackId = k }
                | None   -> tracks.[track.TrackId] <- track

            nextTick <- DateTimeOffset.UtcNow
            newTracks

    /// Return all currently tracked objects.
    member _.AllTracks() : FusedTrack list =
        tracks.Values |> Seq.toList

    /// Prune tracks older than [maxAgeSeconds].
    member _.PruneStaleTracks(maxAgeSeconds: float) =
        let cutoff = DateTimeOffset.UtcNow.AddSeconds(-maxAgeSeconds)
        let stale = tracks |> Seq.filter (fun kv -> kv.Value.LastUpdated < cutoff) |> Seq.toList
        for kv in stale do tracks.Remove(kv.Key) |> ignore

// ---- Cooperative perception coordinator ----
/// Coordinates Detection report collection across the swarm and drives the FusionEngine.
type CooperativePerceptionCoordinator(fusionEngine: FusionEngine) =

    let pendingReports = ResizeArray<DetectionReport>()
    let mutable flushIntervalMs = 200  // batch flush every 200 ms

    member _.Submit(report: DetectionReport) =
        pendingReports.Add(report)

    member _.FlushAndFuse() : FusedTrack list =
        let batch = pendingReports |> Seq.toList
        pendingReports.Clear()
        if batch.IsEmpty then []
        else fusionEngine.Fuse(batch)

    member _.FlushIntervalMs with get() = flushIntervalMs
                              and  set(v) = flushIntervalMs <- v

// ---- Smoke test helpers (module-level) ----
module SmokeTest =

    let makeReport droneId x y z conf =
        {
            DroneId     = droneId
            Timestamp   = DateTimeOffset.UtcNow
            ObjectClass = DroneHostile
            BoundingBox = { X = x; Y = y; Z = z; Width = 1.0; Height = 1.0; Depth = 1.0 }
            Confidence  = conf
            SensorType  = "radar"
        }

    let run () =
        printfn "[Phase %d] CooperativePerception smoke test" PhaseMarker
        let engine = FusionEngine()
        let coord  = CooperativePerceptionCoordinator(engine)

        coord.Submit(makeReport "drone-1"  10.0 20.0 50.0 0.9)
        coord.Submit(makeReport "drone-2"  10.5 20.2 50.1 0.85)  // same object
        coord.Submit(makeReport "drone-3" 100.0 200.0 80.0 0.7)  // different object

        let tracks = coord.FlushAndFuse()
        printfn "  Fused %d tracks from 3 Detection reports" tracks.Length
        for t in tracks do
            let (x, y, z) = t.Position
            printfn "  Track %s pos=(%.1f,%.1f,%.1f) conf=%.3f drones=%A"
                (string t.TrackId).[..7] x y z t.FusedConfidence t.ContributingDrones
        printfn "[Phase %d] done." PhaseMarker

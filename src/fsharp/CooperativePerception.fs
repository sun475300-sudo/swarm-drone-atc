// Phase 528: Cooperative Perception — F#
// SDACS multi-drone sensor fusion for cooperative obstacle detection

module SDACS.CooperativePerception

open System
open System.Collections.Generic

// Phase 528 marker — cooperative perception with sensor Fuse and Detection

/// 3D bounding box for detected objects
type BoundingBox = {
    CenterX : float
    CenterY : float
    CenterZ : float
    Width   : float
    Depth   : float
    Height  : float
}

/// Detection from a single drone sensor
type Detection = {
    DetectionId  : Guid
    DroneId      : string
    Timestamp    : DateTimeOffset
    ObjectClass  : string
    Confidence   : float
    BBox         : BoundingBox
    Velocity     : float * float * float
}

/// Fused detection result from multiple drones
type FusedDetection = {
    FusionId      : Guid
    Timestamp     : DateTimeOffset
    ObjectClass   : string
    Confidence    : float
    BBox          : BoundingBox
    ContribDrones : string list
    FusionMethod  : string
}

/// IoU (Intersection over Union) for 2D bounding boxes (xy-plane)
let iou2D (a: BoundingBox) (b: BoundingBox) : float =
    let ax1 = a.CenterX - a.Width  / 2.0
    let ax2 = a.CenterX + a.Width  / 2.0
    let ay1 = a.CenterY - a.Depth  / 2.0
    let ay2 = a.CenterY + a.Depth  / 2.0
    let bx1 = b.CenterX - b.Width  / 2.0
    let bx2 = b.CenterX + b.Width  / 2.0
    let by1 = b.CenterY - b.Depth  / 2.0
    let by2 = b.CenterY + b.Depth  / 2.0

    let ix1 = max ax1 bx1
    let iy1 = max ay1 by1
    let ix2 = min ax2 bx2
    let iy2 = min ay2 by2

    let intersection = max 0.0 (ix2 - ix1) * max 0.0 (iy2 - iy1)
    let areaA = a.Width * a.Depth
    let areaB = b.Width * b.Depth
    let union  = areaA + areaB - intersection
    if union < 1e-6 then 0.0 else intersection / union

/// Weighted average fusion of bounding boxes
let fuseBBoxes (detections: Detection list) : BoundingBox =
    let totalW = detections |> List.sumBy (fun d -> d.Confidence)
    let w d = d.Confidence / totalW
    {
        CenterX = detections |> List.sumBy (fun d -> w d * d.BBox.CenterX)
        CenterY = detections |> List.sumBy (fun d -> w d * d.BBox.CenterY)
        CenterZ = detections |> List.sumBy (fun d -> w d * d.BBox.CenterZ)
        Width   = detections |> List.sumBy (fun d -> w d * d.BBox.Width)
        Depth   = detections |> List.sumBy (fun d -> w d * d.BBox.Depth)
        Height  = detections |> List.sumBy (fun d -> w d * d.BBox.Height)
    }

/// Non-maximum suppression over detections
let nms (detections: Detection list) (iouThreshold: float) : Detection list =
    let sorted = detections |> List.sortByDescending (fun d -> d.Confidence)
    let kept = ResizeArray<Detection>()
    for det in sorted do
        let overlaps = kept |> Seq.exists (fun k ->
            k.ObjectClass = det.ObjectClass &&
            iou2D k.BBox det.BBox > iouThreshold)
        if not overlaps then kept.Add(det)
    kept |> Seq.toList

/// Fuse detections from multiple drones using IoU clustering
let fuseDetections
    (detections: Detection list)
    (iouThreshold: float)
    (minDrones: int)
    : FusedDetection list =

    if detections.IsEmpty then []
    else
        // Group detections by class
        let byClass = detections |> List.groupBy (fun d -> d.ObjectClass)

        [ for (cls, dets) in byClass do
            // Build clusters: group nearby detections
            let used = HashSet<Guid>()
            let clusters = ResizeArray<Detection list>()

            for det in dets |> List.sortByDescending (fun d -> d.Confidence) do
                if not (used.Contains det.DetectionId) then
                    let cluster =
                        dets
                        |> List.filter (fun d ->
                            not (used.Contains d.DetectionId) &&
                            (d.DetectionId = det.DetectionId ||
                             iou2D d.BBox det.BBox > iouThreshold))
                    cluster |> List.iter (fun d -> used.Add d.DetectionId |> ignore)
                    if cluster.Length >= minDrones then
                        clusters.Add(cluster)

            for cluster in clusters do
                let fusedConf  = cluster |> List.averageBy (fun d -> d.Confidence)
                let fusedBBox  = fuseBBoxes cluster
                let contribs   = cluster |> List.map (fun d -> d.DroneId) |> List.distinct
                yield {
                    FusionId      = Guid.NewGuid()
                    Timestamp     = DateTimeOffset.UtcNow
                    ObjectClass   = cls
                    Confidence    = fusedConf
                    BBox          = fusedBBox
                    ContribDrones = contribs
                    FusionMethod  = "weighted_iou_cluster"
                }
        ]

/// Cooperative perception processor
type PerceptionProcessor() =
    let mutable pendingDetections : Detection list = []
    let mutable fusedHistory      : FusedDetection list = []
    let mutable processedCount    = 0

    member _.Submit(detection: Detection) =
        pendingDetections <- detection :: pendingDetections

    member _.Fuse(iouThreshold: float, minDrones: int) : FusedDetection list =
        let results = fuseDetections pendingDetections iouThreshold minDrones
        fusedHistory <- fusedHistory @ results
        processedCount <- processedCount + pendingDetections.Length
        pendingDetections <- []
        results

    member _.History = fusedHistory

    member _.Stats() = {|
        ProcessedDetections = processedCount
        FusedObjects        = fusedHistory.Length
        Pending             = pendingDetections.Length
    |}

// Demo
[<EntryPoint>]
let main _ =
    let proc = PerceptionProcessor()

    let makeDetection droneId cls cx cy conf = {
        DetectionId  = Guid.NewGuid()
        DroneId      = droneId
        Timestamp    = DateTimeOffset.UtcNow
        ObjectClass  = cls
        Confidence   = conf
        BBox         = { CenterX=cx; CenterY=cy; CenterZ=30.0;
                         Width=3.0; Depth=3.0; Height=2.0 }
        Velocity     = (0.0, 0.0, 0.0)
    }

    proc.Submit(makeDetection "D1" "obstacle" 100.0 200.0 0.92)
    proc.Submit(makeDetection "D2" "obstacle" 101.0 201.0 0.88)
    proc.Submit(makeDetection "D3" "obstacle"  99.5 199.5 0.85)

    let fused = proc.Fuse(0.3, 2)
    printfn "Phase 528: Cooperative Perception — Fused %d objects" fused.Length
    for f in fused do
        printfn "  %s @ (%.1f, %.1f) conf=%.2f drones=%d"
            f.ObjectClass f.BBox.CenterX f.BBox.CenterY f.Confidence f.ContribDrones.Length
    printfn "Stats: %A" (proc.Stats())
    0

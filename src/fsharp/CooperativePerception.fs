// CooperativePerception.fs - Cooperative perception for SDACS (Phase 528)
// F# multi-drone sensor fusion and cooperative object detection

module CooperativePerception

open System
open System.Collections.Generic

// Detection result from a single drone
type Detection = {
    DroneId:    string
    ObjectId:   string
    Position:   float * float * float
    Confidence: float
    Timestamp:  DateTime
    ObjectClass: string
}

// Fused detection from multiple drones
type FusedDetection = {
    ObjectId:         string
    FusedPosition:    float * float * float
    FusedConfidence:  float
    ContributingDrones: string list
    Timestamp:        DateTime
}

// Kalman filter state for single object tracking
type TrackState = {
    mutable X:  float[]   // state vector
    mutable P:  float[]   // covariance (flattened 6x6)
    mutable Age: int
    mutable Confidence: float
}

// Sensor fusion using weighted least squares
let fuseDetections (detections: Detection list) : FusedDetection option =
    if detections.IsEmpty then None
    else
        let weights = detections |> List.map (fun d -> d.Confidence)
        let totalW = List.sum weights
        let fused =
            detections
            |> List.zip weights
            |> List.fold (fun (ax, ay, az) (w, d) ->
                let x, y, z = d.Position
                ax + w*x/totalW, ay + w*y/totalW, az + w*z/totalW
            ) (0.0, 0.0, 0.0)
        Some {
            ObjectId          = detections.[0].ObjectId
            FusedPosition     = fused
            FusedConfidence   = totalW / float detections.Length
            ContributingDrones = detections |> List.map (fun d -> d.DroneId)
            Timestamp         = DateTime.UtcNow
        }

// Non-maximum suppression for overlapping detections
let nms (detections: Detection list) (iouThreshold: float) : Detection list =
    detections
    |> List.sortByDescending (fun d -> d.Confidence)
    |> List.fold (fun acc d ->
        let overlaps =
            acc |> List.exists (fun existing ->
                let x1, y1, _ = d.Position
                let x2, y2, _ = existing.Position
                let dist = sqrt((x1-x2)**2.0 + (y1-y2)**2.0)
                dist < 10.0)
        if overlaps then acc else d :: acc
    ) []

// Cooperative perception pipeline
type CooperativePerceptionSystem(droneIds: string list) =
    let detectionBuffer = Dictionary<string, Detection list>()
    let fusedObjects = Dictionary<string, FusedDetection>()
    let mutable frameCount = 0

    // Register detection from a drone
    member _.AddDetection(d: Detection) =
        let existing =
            if detectionBuffer.ContainsKey(d.ObjectId)
            then detectionBuffer.[d.ObjectId]
            else []
        detectionBuffer.[d.ObjectId] <- d :: existing

    // Fuse all buffered detections for an object
    member _.FuseAll() =
        for kvp in detectionBuffer do
            match fuseDetections kvp.Value with
            | Some fd -> fusedObjects.[fd.ObjectId] <- fd
            | None -> ()
        frameCount <- frameCount + 1
        fusedObjects.Count

    // Get cooperative detection summary
    member _.Summary() =
        {| FrameCount = frameCount
           TotalDetections = detectionBuffer.Values |> Seq.sumBy List.length
           FusedObjects = fusedObjects.Count
           Drones = droneIds.Length |}

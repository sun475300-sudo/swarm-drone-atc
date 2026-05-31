// P528: CooperativePerception - F# cooperative sensing for drone swarms
// Phase 528: Sensor fusion and Detection pipeline using reactive programming

module SDACS.CooperativePerception

open System
open System.Collections.Generic

// Detection types
type DetectionType =
    | Obstacle
    | Drone
    | NfzBoundary
    | UnknownObject

type Detection = {
    Id: string
    Type: DetectionType
    Position: float * float * float
    Confidence: float
    SourceDroneId: string
    Timestamp: DateTime
}

// Sensor fusion input
type SensorReading = {
    DroneId: string
    Detections: Detection list
    Timestamp: DateTime
}

// Fused world model
type WorldModel = {
    Detections: Dictionary<string, Detection>
    LastUpdated: DateTime
}

// Fusion strategy
let fusionThreshold = 5.0  // meters

let distance3d (x1,y1,z1) (x2,y2,z2) =
    let dx, dy, dz = x2-x1, y2-y1, z2-z1
    sqrt (dx*dx + dy*dy + dz*dz)

// Fuse a new detection with an existing one
let fuseDetections (existing: Detection) (incoming: Detection) : Detection =
    let w = incoming.Confidence / (existing.Confidence + incoming.Confidence)
    let (x1,y1,z1) = existing.Position
    let (x2,y2,z2) = incoming.Position
    { existing with
        Position = (x1*(1.0-w) + x2*w, y1*(1.0-w) + y2*w, z1*(1.0-w) + z2*w)
        Confidence = max existing.Confidence incoming.Confidence
        Timestamp = max existing.Timestamp incoming.Timestamp }

// Process a new sensor reading and update the world model
let processReading (model: WorldModel) (reading: SensorReading) : WorldModel =
    for det in reading.Detections do
        let mutable fused = false
        for kvp in model.Detections do
            if not fused && distance3d kvp.Value.Position det.Position < fusionThreshold then
                model.Detections[kvp.Key] <- fuseDetections kvp.Value det
                fused <- true
        if not fused then
            model.Detections[det.Id] <- det
    { model with LastUpdated = DateTime.UtcNow }

// Pipeline: process a stream of readings
let buildPipeline () =
    let model = { Detections = Dictionary<string, Detection>(); LastUpdated = DateTime.UtcNow }
    let mutable currentModel = model

    let processStep reading =
        currentModel <- processReading currentModel reading
        currentModel

    let getModel () = currentModel
    processStep, getModel

// Pipeline builder for reactive detection streams
type Pipeline =
    | Empty
    | Stage of string * (SensorReading -> SensorReading list) * Pipeline

let buildDetectionPipeline stages =
    List.fold (fun acc stage -> Stage(stage, id, acc)) Empty stages

let runPipeline (pipeline: Pipeline) (input: SensorReading) : SensorReading list =
    match pipeline with
    | Empty -> [input]
    | Stage(_, fn, _) -> fn input

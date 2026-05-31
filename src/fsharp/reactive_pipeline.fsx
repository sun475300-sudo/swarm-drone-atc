// reactive_pipeline.fsx - Reactive Pipeline for SDACS drone telemetry
// F# functional reactive programming for drone swarm data processing

open System
open System.Collections.Generic

// Telemetry data types
type DroneId = string
type Timestamp = DateTimeOffset

type Position = { X: float; Y: float; Z: float }
type Velocity = { Vx: float; Vy: float; Vz: float }

type TelemetryFrame = {
    DroneId   : DroneId
    Timestamp : Timestamp
    Position  : Position
    Velocity  : Velocity
    Battery   : int
    Status    : string
}

type ConflictEvent = {
    DroneA    : DroneId
    DroneB    : DroneId
    Distance  : float
    Severity  : string
    Timestamp : Timestamp
}

// Pipeline stage type
type PipelineStage<'TIn, 'TOut> = {
    Name    : string
    Process : 'TIn -> 'TOut option
}

// Pipeline builder
type Pipeline<'T> = {
    Stages : string list
    Source : unit -> 'T seq
}

module Pipeline =
    // Create a new pipeline from a source sequence
    let create name source =
        { Stages = [name]; Source = source }

    // Add a filtering stage to the pipeline
    let filter predicate pipeline =
        { pipeline with
            Stages = pipeline.Stages @ ["filter"]
            Source = fun () -> pipeline.Source() |> Seq.filter predicate }

    // Add a mapping transformation stage
    let map transform pipeline =
        { pipeline with
            Stages = pipeline.Stages @ ["map"]
            Source = fun () -> pipeline.Source() |> Seq.map transform }

    // Add a batching stage
    let batch size pipeline =
        { pipeline with
            Stages = pipeline.Stages @ [sprintf "batch(%d)" size]
            Source = fun () ->
                pipeline.Source()
                |> Seq.chunkBySize size
                |> Seq.map Array.toList }

    // Execute the pipeline and collect results
    let run pipeline =
        pipeline.Source() |> Seq.toList

    // Get pipeline stage count
    let stageCount pipeline = List.length pipeline.Stages

// Telemetry processing pipeline
module TelemetryPipeline =
    let filterLowBattery threshold frames =
        frames |> Seq.filter (fun f -> f.Battery >= threshold)

    let computeSpeed frame =
        let v = frame.Velocity
        let speed = Math.Sqrt(v.Vx*v.Vx + v.Vy*v.Vy + v.Vz*v.Vz)
        {| Frame = frame; Speed = speed |}

    let detectConflicts minSep frames =
        let frameList = Seq.toList frames
        [ for a in frameList do
            for b in frameList do
                if a.DroneId < b.DroneId then
                    let dx = a.Position.X - b.Position.X
                    let dy = a.Position.Y - b.Position.Y
                    let dz = a.Position.Z - b.Position.Z
                    let dist = Math.Sqrt(dx*dx + dy*dy + dz*dz)
                    if dist < minSep then
                        yield {
                            DroneA    = a.DroneId
                            DroneB    = b.DroneId
                            Distance  = dist
                            Severity  = if dist < 10.0 then "critical" else "warning"
                            Timestamp = DateTimeOffset.UtcNow
                        }
        ]

    // Build complete processing pipeline
    let buildPipeline (frames: TelemetryFrame seq) =
        Pipeline.create "telemetry-source" (fun () -> frames)
        |> Pipeline.filter (fun f -> f.Status = "active")
        |> Pipeline.filter (fun f -> f.Battery > 10)
        |> Pipeline.map computeSpeed

// Statistics aggregator
type PipelineStats = {
    FramesProcessed : int
    ConflictsFound  : int
    LowBatteryAlerts: int
    ThroughputHz    : float
}

let computeStats frames startTime =
    let elapsed = (DateTimeOffset.UtcNow - startTime).TotalSeconds
    {
        FramesProcessed  = Seq.length frames
        ConflictsFound   = 0
        LowBatteryAlerts = frames |> Seq.filter (fun f -> f.Battery < 20) |> Seq.length
        ThroughputHz     = if elapsed > 0.0 then float (Seq.length frames) / elapsed else 0.0
    }

// Entry point
printfn "SDACS Reactive Pipeline initialized"
printfn "Pipeline stages: create -> filter -> map -> batch"

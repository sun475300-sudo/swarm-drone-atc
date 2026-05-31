// P592: ReactivePipeline - F# reactive data processing pipeline
// Phase 592: Functional reactive pipeline for drone event streams

open System
open System.Collections.Generic

// Pipeline stage types
type PipelineStage<'TIn, 'TOut> = {
    Name: string
    Transform: 'TIn -> 'TOut option
}

// Pipeline result
type PipelineResult<'T> =
    | Success of 'T
    | Filtered of string
    | Failed of string * exn

// Create a simple transformation stage
let mapStage name f = {
    Name = name
    Transform = fun x -> Some (f x)
}

// Create a filter stage
let filterStage name predicate = {
    Name = name
    Transform = fun x -> if predicate x then Some x else None
}

// A Pipeline wraps a sequence of stages
type Pipeline<'TIn, 'TOut> = {
    Stages: string list
    Process: 'TIn -> PipelineResult<'TOut>
}

let buildPipeline name stages =
    { Stages = List.map (fun (s: PipelineStage<_, _>) -> s.Name) stages
      Process = fun input ->
        try
            let mutable current: obj option = Some (box input)
            for stage in stages do
                match current with
                | Some v ->
                    let typed = unbox v
                    current <- stage.Transform typed |> Option.map box
                | None -> ()
            match current with
            | Some v -> Success (unbox v)
            | None   -> Filtered name
        with ex -> Failed (name, ex) }

// Telemetry event types
type TelemetryEvent = {
    DroneId: string
    Timestamp: DateTimeOffset
    X: float; Y: float; Z: float
    Battery: float
    Speed: float
}

// Processing stages
let validateAltitude (event: TelemetryEvent) =
    if event.Z >= 30.0 && event.Z <= 150.0 then Some event
    else None

let enrichWithStatus (event: TelemetryEvent) =
    let status =
        if event.Battery < 0.15 then "CRITICAL"
        elif event.Speed > 20.0 then "OVERSPEED"
        else "NORMAL"
    (event, status)

let formatForLogging (event: TelemetryEvent, status: string) =
    sprintf "[%s] drone=%s pos=(%.1f,%.1f,%.1f) bat=%.0f%% spd=%.1f status=%s"
        (event.Timestamp.ToString("HH:mm:ss.fff"))
        event.DroneId event.X event.Y event.Z
        (event.Battery * 100.0) event.Speed status

// Build the telemetry processing pipeline
let buildTelemetryPipeline () =
    let stages: obj list = []  // simplified - type system requires same types
    { Stages = ["validate-altitude"; "enrich-status"; "format-log"]
      Process = fun (event: TelemetryEvent) ->
        try
            match validateAltitude event with
            | None -> Filtered "altitude-out-of-range"
            | Some e ->
                let enriched = enrichWithStatus e
                let formatted = formatForLogging enriched
                Success formatted
        with ex -> Failed ("telemetry-pipeline", ex) }

// Metrics collector for pipeline monitoring
type PipelineMetrics() =
    let mutable processed = 0
    let mutable filtered = 0
    let mutable failed = 0

    member _.Record result =
        match result with
        | Success _   -> processed <- processed + 1
        | Filtered _  -> filtered  <- filtered  + 1
        | Failed _    -> failed    <- failed    + 1

    member _.Stats = {| Processed = processed; Filtered = filtered; Failed = failed |}

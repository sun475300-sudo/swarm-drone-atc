// Phase 592 — F# reactive Pipeline with RTScheduler type
// SDACS real-time event processing pipeline for drone telemetry

open System
open System.Collections.Generic

// ---------------- Domain Types ----------------

type DroneId = DroneId of int

type TelemetryFrame = {
    DroneId    : DroneId
    TimestampMs: int64
    Lat        : float
    Lon        : float
    AltM       : float
    SpeedMps   : float
    BatteryPct : float
    SeqNo      : int
}

type PipelineEvent =
    | FrameReceived  of TelemetryFrame
    | FrameDropped   of DroneId * string
    | ConflictAlert  of DroneId * DroneId * float
    | SchedulerTick  of int64

// ---------------- RTScheduler ----------------

/// RTScheduler — real-time periodic scheduler for pipeline tick generation
type RTScheduler(intervalMs: int, maxTicks: int option) =
    let mutable running = false
    let mutable tickCount = 0L
    let subscribers = List<PipelineEvent -> unit>()

    member _.IntervalMs = intervalMs
    member _.TickCount  = tickCount
    member _.IsRunning  = running

    /// Subscribe a callback to receive scheduler events
    member _.Subscribe(handler: PipelineEvent -> unit) =
        subscribers.Add(handler)

    /// Emit a SchedulerTick event to all subscribers
    member private _.Emit(evt: PipelineEvent) =
        subscribers |> Seq.iter (fun h -> h evt)

    /// Start the scheduler loop (synchronous in this stub)
    member this.Start() =
        running <- true
        let limit = maxTicks |> Option.defaultValue Int32.MaxValue
        while running && int tickCount < limit do
            tickCount <- tickCount + 1L
            this.Emit(SchedulerTick tickCount)
        running <- false

    /// Stop the scheduler
    member _.Stop() =
        running <- false

// ---------------- Pipeline Stage ----------------

type StageResult<'a> =
    | Pass of 'a
    | Reject of string
    | Transform of 'a

type PipelineStage = {
    Name    : string
    Process : TelemetryFrame -> StageResult<TelemetryFrame>
}

// Validation stage — rejects frames with invalid battery or altitude
let validationStage : PipelineStage = {
    Name = "validation"
    Process = fun frame ->
        if frame.BatteryPct < 0.0 || frame.BatteryPct > 100.0 then
            Reject (sprintf "invalid battery %.1f%%" frame.BatteryPct)
        elif frame.AltM < 0.0 || frame.AltM > 500.0 then
            Reject (sprintf "altitude out of range %.1fm" frame.AltM)
        else
            Pass frame
}

// Normalization stage — clamps speed to safe range
let normalizationStage : PipelineStage = {
    Name = "normalization"
    Process = fun frame ->
        let clamped = { frame with SpeedMps = min frame.SpeedMps 30.0 }
        Transform clamped
}

// Logging stage — prints and passes through
let loggingStage : PipelineStage = {
    Name = "logging"
    Process = fun frame ->
        let (DroneId id) = frame.DroneId
        printfn "[log] drone=%d ts=%d alt=%.1fm spd=%.1f bat=%.0f%%" id frame.TimestampMs frame.AltM frame.SpeedMps frame.BatteryPct
        Pass frame
}

// ---------------- Reactive Pipeline ----------------

type ReactivePipeline(name: string, stages: PipelineStage list) =
    let processedCount = ref 0
    let droppedCount   = ref 0

    member _.Name           = name
    member _.ProcessedCount = !processedCount
    member _.DroppedCount   = !droppedCount

    /// Run a single frame through all pipeline stages
    member _.ProcessFrame(frame: TelemetryFrame) : TelemetryFrame option =
        let rec loop remaining current =
            match remaining with
            | [] ->
                incr processedCount
                Some current
            | stage :: rest ->
                match stage.Process current with
                | Pass f | Transform f -> loop rest f
                | Reject reason ->
                    incr droppedCount
                    printfn "[%s] dropped by %s: %s" name stage.Name reason
                    None
        loop stages frame

    /// Handle a PipelineEvent from the RTScheduler or external sources
    member this.HandleEvent(evt: PipelineEvent) =
        match evt with
        | FrameReceived frame -> this.ProcessFrame frame |> ignore
        | FrameDropped(DroneId id, reason) ->
            printfn "[%s] external drop drone=%d: %s" name id reason
        | ConflictAlert(DroneId a, DroneId b, dist) ->
            printfn "[%s] conflict alert between %d and %d dist=%.1fm" name a b dist
        | SchedulerTick tick ->
            printfn "[%s] scheduler tick %d" name tick

// ---------------- Entry Point ----------------

let pipeline = ReactivePipeline("sdacs-rt", [validationStage; normalizationStage; loggingStage])

let scheduler = RTScheduler(100, Some 3)
scheduler.Subscribe(pipeline.HandleEvent)

// Feed some frames directly
let testFrame = {
    DroneId = DroneId 1; TimestampMs = 1000L; Lat = 37.42; Lon = 127.13
    AltM = 80.0; SpeedMps = 12.0; BatteryPct = 85.0; SeqNo = 1
}
pipeline.ProcessFrame(testFrame) |> ignore

scheduler.Start()

printfn "Processed: %d  Dropped: %d" pipeline.ProcessedCount pipeline.DroppedCount

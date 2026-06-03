// Phase 582: Reactive Pipeline — F# Functional Reactive
// SDACS real-time drone data processing pipeline

open System
open System.Collections.Concurrent

// Domain types
type DroneId = DroneId of string

type Vector3 = { X: float; Y: float; Z: float }

type TelemetryFrame = {
    DroneId   : DroneId
    Timestamp : DateTimeOffset
    Position  : Vector3
    Velocity  : Vector3
    Heading   : float
    Battery   : float
    Mode      : string
}

type PipelineEvent =
    | Telemetry   of TelemetryFrame
    | Alert       of DroneId * string * string  // drone, severity, message
    | Conflict    of DroneId * DroneId * float  // d1, d2, separation_m
    | BatteryLow  of DroneId * float
    | ModeChange  of DroneId * string * string  // drone, old_mode, new_mode

type PipelineStage<'T, 'U> = 'T -> 'U option

// Pipeline combinator
module Pipeline =
    let map f = fun x -> Some (f x)

    let filter pred = fun x -> if pred x then Some x else None

    let bind f = fun x ->
        match f x with
        | Some y -> Some y
        | None   -> None

    let compose (stages: PipelineStage<'a, 'a> list) : PipelineStage<'a, 'a> =
        List.fold (fun acc stage ->
            fun x ->
                match acc x with
                | Some y -> stage y
                | None   -> None
        ) (fun x -> Some x) stages

    let run (pipeline: PipelineStage<'a, 'b>) input =
        pipeline input

// Telemetry filters
module TelemetryFilter =
    let validBattery frame =
        if frame.Battery >= 0.0 && frame.Battery <= 100.0 then Some frame
        else None

    let validAltitude minAlt maxAlt frame =
        if frame.Position.Z >= minAlt && frame.Position.Z <= maxAlt then Some frame
        else None

    let validSpeed maxSpeed frame =
        let speed = sqrt (frame.Velocity.X**2.0 + frame.Velocity.Y**2.0 + frame.Velocity.Z**2.0)
        if speed <= maxSpeed then Some frame
        else None

// Alert generators
module AlertGen =
    let batteryAlert threshold frame =
        if frame.Battery < threshold then
            Some (BatteryLow (frame.DroneId, frame.Battery))
        else None

    let altitudeAlert maxAlt frame =
        if frame.Position.Z > maxAlt then
            Some (Alert (frame.DroneId, "WARNING", sprintf "Altitude %.1f exceeds max %.1f" frame.Position.Z maxAlt))
        else None

// Main reactive pipeline processor
type ReactiveProcessor() =
    let mutable eventCount = 0
    let mutable alertCount = 0
    let eventQueue = ConcurrentQueue<PipelineEvent>()
    let handlers = ConcurrentDictionary<string, PipelineEvent -> unit>()

    member _.Publish(event: PipelineEvent) =
        eventQueue.Enqueue(event)
        eventCount <- eventCount + 1

    member _.Subscribe(name: string, handler: PipelineEvent -> unit) =
        handlers.[name] <- handler

    member _.Unsubscribe(name: string) =
        handlers.TryRemove(name) |> ignore

    member _.Process() =
        let mutable event = Unchecked.defaultof<PipelineEvent>
        while eventQueue.TryDequeue(&event) do
            for kvp in handlers do
                try kvp.Value event
                with ex -> eprintfn "Handler %s error: %s" kvp.Key ex.Message

    member _.ProcessTelemetry(frame: TelemetryFrame) =
        let pipeline = Pipeline.compose [
            TelemetryFilter.validBattery
            TelemetryFilter.validAltitude 0.0 400.0
            TelemetryFilter.validSpeed 30.0
        ]
        match Pipeline.run pipeline frame with
        | Some validFrame ->
            this.Publish(Telemetry validFrame)
            // Generate derived alerts
            AlertGen.batteryAlert 20.0 validFrame |> Option.iter this.Publish
            AlertGen.altitudeAlert 120.0 validFrame |> Option.iter (fun _ -> alertCount <- alertCount + 1)
        | None ->
            eprintfn "Invalid telemetry frame from %A" frame.DroneId

    member _.Stats() = {|
        EventCount = eventCount
        AlertCount = alertCount
        QueueDepth = eventQueue.Count
        Handlers   = handlers.Count
    |}

// Conflict detection stage
let detectConflicts (frames: TelemetryFrame list) : PipelineEvent list =
    [ for i in 0..frames.Length-2 do
        for j in i+1..frames.Length-1 do
            let a = frames.[i]
            let b = frames.[j]
            let dx = a.Position.X - b.Position.X
            let dy = a.Position.Y - b.Position.Y
            let dz = a.Position.Z - b.Position.Z
            let dist = sqrt (dx*dx + dy*dy + dz*dz)
            if dist < 50.0 then
                yield Conflict (a.DroneId, b.DroneId, dist) ]

// Demo
let demo () =
    let processor = ReactiveProcessor()
    processor.Subscribe("logger", fun evt ->
        match evt with
        | Telemetry f -> printfn "[TELEM] %A bat=%.0f%%" f.DroneId f.Battery
        | Alert (id, sev, msg) -> printfn "[ALERT] %A %s: %s" id sev msg
        | BatteryLow (id, pct) -> printfn "[LOW BAT] %A %.0f%%" id pct
        | Conflict (a, b, d) -> printfn "[CONFLICT] %A <-> %A sep=%.1fm" a b d
        | ModeChange (id, old, nw) -> printfn "[MODE] %A %s->%s" id old nw
    )

    let frame = {
        DroneId   = DroneId "D001"
        Timestamp = DateTimeOffset.UtcNow
        Position  = { X = 100.0; Y = 200.0; Z = 60.0 }
        Velocity  = { X = 5.0; Y = 0.0; Z = 0.0 }
        Heading   = 90.0
        Battery   = 18.5
        Mode      = "AUTO"
    }
    processor.ProcessTelemetry(frame)
    processor.Process()
    printfn "Stats: %A" (processor.Stats())

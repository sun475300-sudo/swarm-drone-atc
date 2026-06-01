// Phase 592: Reactive Pipeline — 드론 반응형 데이터 파이프라인 (F#)
// Reactive stream processing pipeline for drone telemetry.
module SDACS.ReactivePipeline

open System
open System.Collections.Generic

let PHASE = 592

// ── Pipeline stage types ───────────────────────────────────────────

type PipelineItem<'T> = {
    Value     : 'T
    Timestamp : DateTime
    Source    : string
}

type PipelineResult<'T> =
    | Success of 'T
    | FilteredOut
    | TransformError of string

// ── Pipeline stage ─────────────────────────────────────────────────

type Pipeline<'TIn, 'TOut>(transform: 'TIn -> PipelineResult<'TOut>) =
    member _.Process(item: PipelineItem<'TIn>) : PipelineItem<'TOut> option =
        match transform item.Value with
        | Success v    -> Some { Value = v; Timestamp = item.Timestamp; Source = item.Source }
        | FilteredOut  -> None
        | TransformError _ -> None

    member _.ProcessMany(items: seq<PipelineItem<'TIn>>) : seq<PipelineItem<'TOut>> =
        items |> Seq.choose (fun item ->
            match transform item.Value with
            | Success v    -> Some { Value = v; Timestamp = item.Timestamp; Source = item.Source }
            | FilteredOut  -> None
            | TransformError _ -> None)

// ── Drone telemetry types ──────────────────────────────────────────

type RawTelemetry = {
    DroneId  : int
    X        : float
    Y        : float
    Z        : float
    Battery  : float
    Velocity : float
}

type NormalizedTelemetry = {
    DroneId    : int
    Position   : float * float * float
    Battery    : float
    Velocity   : float
    IsLowBat   : bool
    RiskScore  : float
}

// ── Pipeline stages ────────────────────────────────────────────────

let validateStage : Pipeline<RawTelemetry, RawTelemetry> =
    Pipeline(fun raw ->
        if raw.Battery < 0.0 || raw.Battery > 100.0 then FilteredOut
        elif raw.Z < 0.0 then FilteredOut
        else Success raw)

let normalizeStage : Pipeline<RawTelemetry, NormalizedTelemetry> =
    Pipeline(fun raw ->
        let risk = max 0.0 (1.0 - raw.Battery / 100.0 + raw.Velocity / 30.0)
        Success {
            DroneId    = raw.DroneId
            Position   = (raw.X, raw.Y, raw.Z)
            Battery    = raw.Battery
            Velocity   = raw.Velocity
            IsLowBat   = raw.Battery < 20.0
            RiskScore  = min 1.0 risk
        })

// ── Stream generator ───────────────────────────────────────────────

let generateStream (nDrones: int) (nSteps: int) (seed: int) : seq<PipelineItem<RawTelemetry>> =
    let rng = Random(seed)
    seq {
        for drone in 0..nDrones-1 do
            for step in 0..nSteps-1 do
                yield {
                    Value = {
                        DroneId  = drone
                        X        = float drone * 50.0 + float step * 1.0
                        Y        = float drone * 30.0
                        Z        = 50.0 + rng.NextDouble() * 20.0
                        Battery  = 100.0 - float step * 0.5
                        Velocity = 5.0 + rng.NextDouble() * 10.0
                    }
                    Timestamp = DateTime.UtcNow
                    Source    = sprintf "drone-%d" drone
                }
    }

// ── Pipeline runner ────────────────────────────────────────────────

type PipelineRunner() =
    let results = List<NormalizedTelemetry>()
    let alerts  = List<string>()

    member _.Run(stream: seq<PipelineItem<RawTelemetry>>) =
        let validated  = validateStage.ProcessMany(stream)
        let normalized = normalizeStage.ProcessMany(validated)
        for item in normalized do
            results.Add(item.Value)
            if item.Value.IsLowBat then
                alerts.Add(sprintf "LOW BAT drone-%d: %.1f%%" item.Value.DroneId item.Value.Battery)

    member _.Results = results :> IReadOnlyList<_>
    member _.Alerts  = alerts  :> IReadOnlyList<_>

    member _.Summary() =
        Map [
            "phase",   box PHASE
            "records", box results.Count
            "alerts",  box alerts.Count
            "low_bat", box (results |> Seq.filter (fun r -> r.IsLowBat) |> Seq.length)
        ]

// ── Entry point ────────────────────────────────────────────────────

let runner = PipelineRunner()
let stream = generateStream 5 30 42
runner.Run(stream)
let summary = runner.Summary()
printfn "Phase %d: Reactive Pipeline — 드론 반응형 파이프라인" PHASE
printfn "Records: %d, Alerts: %d" runner.Results.Count runner.Alerts.Count
printfn "Summary: %A" (Map.toList summary)

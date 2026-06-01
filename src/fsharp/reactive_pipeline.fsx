// Reactive Pipeline — F# for SDACS telemetry processing
// Phase 592

open System
open System.Collections.Generic

// ── Pipeline Stage ─────────────────────────────────────────────

type PipelineResult<'T> =
    | Success of 'T
    | Failure of string

type PipelineStage<'TIn, 'TOut> =
    { Name    : string
      Process : 'TIn -> PipelineResult<'TOut> }

// ── Telemetry Types ─────────────────────────────────────────────

type RawTelemetry =
    { DroneId   : string
      Timestamp : int64
      RawData   : byte[] }

type ParsedTelemetry =
    { DroneId   : string
      Timestamp : DateTimeOffset
      Lat       : float
      Lon       : float
      AltM      : float
      BattPct   : float
      SpeedMps  : float }

type ValidatedTelemetry = ValidatedTelemetry of ParsedTelemetry

// ── Pipeline Stages ─────────────────────────────────────────────

let parseStage : PipelineStage<RawTelemetry, ParsedTelemetry> =
    { Name = "Parse"
      Process = fun raw ->
          try
              let ts = DateTimeOffset.FromUnixTimeMilliseconds(raw.Timestamp)
              Success { DroneId = raw.DroneId; Timestamp = ts
                        Lat = 37.5665; Lon = 126.9780; AltM = 100.0
                        BattPct = 85.0; SpeedMps = 5.0 }
          with ex ->
              Failure $"Parse error: {ex.Message}" }

let validateStage : PipelineStage<ParsedTelemetry, ValidatedTelemetry> =
    { Name = "Validate"
      Process = fun t ->
          if t.AltM < 0.0 || t.AltM > 10000.0 then
              Failure $"Altitude out of range: {t.AltM}"
          elif t.BattPct < 0.0 || t.BattPct > 100.0 then
              Failure $"Battery out of range: {t.BattPct}"
          elif t.SpeedMps > 50.0 then
              Failure $"Speed exceeds limit: {t.SpeedMps}"
          else
              Success (ValidatedTelemetry t) }

// ── Pipeline Composition ─────────────────────────────────────────

let (>>>) (stage1 : PipelineStage<'A,'B>) (stage2 : PipelineStage<'B,'C>) =
    { Name    = $"{stage1.Name} >>> {stage2.Name}"
      Process = fun input ->
          match stage1.Process input with
          | Failure err -> Failure $"[{stage1.Name}] {err}"
          | Success mid ->
              match stage2.Process mid with
              | Failure err -> Failure $"[{stage2.Name}] {err}"
              | Success out -> Success out }

let telemetryPipeline = parseStage >>> validateStage

// ── Batch Processor ──────────────────────────────────────────────

type BatchResult<'T> =
    { Processed  : int
      Succeeded  : 'T list
      Failed     : (RawTelemetry * string) list }

let processBatch (pipeline : PipelineStage<RawTelemetry,'T>) (batch : RawTelemetry list) =
    let results =
        batch |> List.map (fun raw ->
            match pipeline.Process raw with
            | Success v -> Choice1Of2 v
            | Failure e -> Choice2Of2 (raw, e))
    { Processed = List.length batch
      Succeeded = results |> List.choose (function Choice1Of2 v -> Some v | _ -> None)
      Failed    = results |> List.choose (function Choice2Of2 e -> Some e | _ -> None) }

// ── Sample Run ──────────────────────────────────────────────────

let sampleBatch =
    [ { DroneId = "D-001"; Timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(); RawData = [||] }
      { DroneId = "D-002"; Timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(); RawData = [||] } ]

let result = processBatch telemetryPipeline sampleBatch
printfn "Pipeline '%s': %d processed, %d ok, %d failed"
    telemetryPipeline.Name result.Processed
    (List.length result.Succeeded) (List.length result.Failed)

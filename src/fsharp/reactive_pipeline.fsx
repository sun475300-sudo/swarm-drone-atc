// Phase 592: reactive_pipeline — F# 기반 반응형 파이프라인
// SDACS Reactive Pipeline for Real-Time Drone Data Processing

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 반응형 스트림 기본 타입
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

type DroneEvent =
    | TelemetryUpdate of int * float * float * float * float  // droneId, lat, lon, alt, battery
    | ConflictDetected of int * int * float                   // droneA, droneB, distance
    | BatteryAlert of int * float                             // droneId, level
    | ModeChanged of int * string                             // droneId, newMode
    | SystemHeartbeat of float                                // timestamp

type PipelineResult<'a> =
    | Success of 'a
    | FilteredOut
    | Error of string

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Pipeline 단계 정의
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// 파이프라인 스테이지 타입
type Stage<'a, 'b> = 'a -> PipelineResult<'b>

// Pipeline 컴포지션 연산자 (>>)
let (>>>) (stage1: Stage<'a, 'b>) (stage2: Stage<'b, 'c>) : Stage<'a, 'c> =
    fun input ->
        match stage1 input with
        | Success v    -> stage2 v
        | FilteredOut  -> FilteredOut
        | Error e      -> Error e

// Pipeline 클래스 (순서대로 단계 적용)
type Pipeline<'a, 'b>(transform: Stage<'a, 'b>) =
    member _.Run(input: 'a) = transform input
    member _.Map(f: 'b -> 'c) =
        Pipeline(fun x ->
            match transform x with
            | Success v   -> Success (f v)
            | FilteredOut -> FilteredOut
            | Error e     -> Error e)
    member _.Filter(pred: 'b -> bool) =
        Pipeline(fun x ->
            match transform x with
            | Success v when pred v -> Success v
            | Success _             -> FilteredOut
            | FilteredOut           -> FilteredOut
            | Error e               -> Error e)

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 드론 이벤트 처리 Pipeline 단계들
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// 이벤트 유효성 검사
let validateEvent (event: DroneEvent) : PipelineResult<DroneEvent> =
    match event with
    | TelemetryUpdate(id, _, _, alt, bat) when id < 0   -> Error "유효하지 않은 드론 ID"
    | TelemetryUpdate(_, _, _, alt, _)   when alt > 500.0 -> Error "고도 한계 초과"
    | TelemetryUpdate(_, _, _, _, bat)   when bat < 0.0  -> Error "배터리 음수값"
    | _ -> Success event

// 저배터리 경보 생성
let enrichBatteryAlerts (event: DroneEvent) : PipelineResult<DroneEvent list> =
    match event with
    | TelemetryUpdate(id, _, _, _, bat) when bat < 20.0 ->
        Success [event; BatteryAlert(id, bat)]
    | _ -> Success [event]

// 이벤트 우선순위 분류
type Priority = Low | Medium | High | Critical

let classifyPriority (events: DroneEvent list) : PipelineResult<(Priority * DroneEvent) list> =
    let classify = function
        | BatteryAlert(_, bat) when bat < 10.0 -> Critical
        | BatteryAlert _                        -> High
        | ConflictDetected(_, _, dist) when dist < 5.0 -> Critical
        | ConflictDetected _                    -> High
        | TelemetryUpdate _                     -> Low
        | ModeChanged _                         -> Medium
        | SystemHeartbeat _                     -> Low
    Success (events |> List.map (fun e -> (classify e, e)))

// 이벤트 포매터
let formatEvent (priority: Priority, event: DroneEvent) : string =
    let pStr = sprintf "%A" priority
    let eStr = match event with
               | TelemetryUpdate(id, lat, lon, alt, bat) ->
                   sprintf "Telemetry D%d: lat=%.3f lon=%.3f alt=%.1fm bat=%.1f%%" id lat lon alt bat
               | ConflictDetected(a, b, d) ->
                   sprintf "Conflict D%d↔D%d: dist=%.1fm" a b d
               | BatteryAlert(id, lvl) ->
                   sprintf "Battery ALERT D%d: %.1f%%" id lvl
               | ModeChanged(id, mode) ->
                   sprintf "Mode D%d → %s" id mode
               | SystemHeartbeat ts ->
                   sprintf "Heartbeat t=%.0f" ts
    sprintf "[%s] %s" pStr eStr

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 스트림 처리기
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

type StreamProcessor() =
    let mutable processedCount = 0
    let mutable errorCount     = 0
    let mutable filteredCount  = 0

    member _.Process(events: DroneEvent seq) : string list =
        events
        |> Seq.toList
        |> List.collect (fun event ->
            match validateEvent event with
            | Error e ->
                errorCount <- errorCount + 1
                printfn "  [Error] %s" e
                []
            | FilteredOut ->
                filteredCount <- filteredCount + 1
                []
            | Success v ->
                match enrichBatteryAlerts v with
                | Error _ -> []
                | FilteredOut -> []
                | Success enriched ->
                    match classifyPriority enriched with
                    | Error _ -> []
                    | FilteredOut -> []
                    | Success classified ->
                        processedCount <- processedCount + (List.length classified)
                        classified |> List.map formatEvent)

    member _.Stats() =
        sprintf "processed=%d errors=%d filtered=%d" processedCount errorCount filteredCount

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 메인 실행
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

printfn "SDACS Reactive Pipeline — Phase 592\n"

let events = [
    TelemetryUpdate(0, 37.500, 127.000, 50.0, 95.0)
    TelemetryUpdate(1, 37.501, 127.001, 52.0, 15.0)
    TelemetryUpdate(2, 37.502, 127.002, 130.0, 88.0)
    ConflictDetected(0, 1, 8.5)
    ModeChanged(1, "RTL")
    SystemHeartbeat(1748563200.0)
    TelemetryUpdate(-1, 0.0, 0.0, 0.0, 0.0)  // 유효하지 않은 ID
]

let processor = StreamProcessor()
let output = processor.Process(events)

printfn "Pipeline 출력 (%d개):" (List.length output)
output |> List.iter (printfn "  %s")
printfn "\n통계: %s" (processor.Stats())
printfn "반응형 파이프라인 완료."

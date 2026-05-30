// SDACS Reactive Pipeline — F#
// 군집드론 반응형 데이터 파이프라인

open System
open System.Collections.Generic

// 파이프라인 단계 타입 정의
type StageResult<'T> =
    | Success of 'T
    | Failure of string

// 파이프라인 설정
type PipelineConfig = {
    Name: string
    MaxRetries: int
    TimeoutMs: int
    Parallel: bool
}

// 파이프라인 단계 정의
type Stage<'TIn, 'TOut> = {
    Name: string
    Process: 'TIn -> StageResult<'TOut>
}

// Pipeline 클래스 (제네릭 파이프라인)
type Pipeline<'T>(config: PipelineConfig) =
    let mutable stages: (string * ('T -> StageResult<'T>)) list = []
    let mutable results: Dictionary<string, string> = Dictionary<string, string>()

    member _.Name = config.Name

    member this.AddStage(name: string, proc: 'T -> StageResult<'T>) =
        stages <- stages @ [(name, proc)]
        this

    member _.Run(input: 'T) =
        printfn "Starting Pipeline: %s" config.Name
        let mutable current = Success input
        for (name, proc) in stages do
            match current with
            | Success value ->
                printfn "  Stage [%s]: Running..." name
                current <- proc value
                match current with
                | Success _ -> results.[name] <- "SUCCESS"
                | Failure msg -> results.[name] <- sprintf "FAILED: %s" msg
            | Failure _ ->
                results.[name] <- "SKIPPED"
        current

    member _.GetResults() = results

// 드론 텔레메트리 데이터 타입
type DroneFrame = {
    DroneId: string
    Timestamp: DateTime
    Lat: float
    Lon: float
    Alt: float
    Battery: int
}

// 텔레메트리 파이프라인 생성
let createTelemetryPipeline () =
    let config = {
        Name = "TelemetryPipeline"
        MaxRetries = 3
        TimeoutMs = 5000
        Parallel = false
    }

    let pipeline = Pipeline<DroneFrame>(config)

    pipeline
        .AddStage("Validate", fun frame ->
            if frame.Battery < 0 || frame.Battery > 100 then
                Failure "Invalid battery level"
            elif frame.Alt < 0.0 then
                Failure "Negative altitude"
            else
                Success frame)
        .AddStage("Filter", fun frame ->
            if frame.Battery < 10 then
                printfn "  Warning: Low battery for %s" frame.DroneId
            Success frame)
        .AddStage("Enrich", fun frame ->
            printfn "  Enriching frame for drone %s" frame.DroneId
            Success frame)
        .AddStage("Store", fun frame ->
            printfn "  Storing frame: %s @ (%.4f, %.4f)" frame.DroneId frame.Lat frame.Lon
            Success frame)

// 실행 예시
let pipeline = createTelemetryPipeline()
let testFrame = {
    DroneId = "DRONE-001"
    Timestamp = DateTime.UtcNow
    Lat = 37.5665
    Lon = 126.978
    Alt = 100.0
    Battery = 85
}

let result = pipeline.Run(testFrame)
match result with
| Success _ -> printfn "Pipeline completed successfully"
| Failure msg -> printfn "Pipeline failed: %s" msg

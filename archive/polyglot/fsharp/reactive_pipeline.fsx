// Phase 592: Reactive Pipeline — F#
// 반응형 데이터 파이프라인: Observable 패턴,
// 이벤트 스트림 변환, 비동기 파이프라인.

open System

// ─── 도메인 타입 ───
type DroneId = string

type TelemetryData = {
    DroneId: DroneId
    Latitude: float
    Longitude: float
    Altitude: float
    Speed: float
    Battery: float
    Timestamp: DateTime
}

type Alert =
    | LowBattery of DroneId * float
    | SpeedViolation of DroneId * float
    | AltitudeViolation of DroneId * float
    | ProximityWarning of DroneId * DroneId * float

type PipelineStats = {
    Processed: int
    Alerts: int
    Filtered: int
    AvgLatency: float
}

// ─── 파이프라인 연산자 ───
module Pipeline =
    let filter predicate source =
        source |> Seq.filter predicate

    let map transform source =
        source |> Seq.map transform

    let window size source =
        source |> Seq.windowed size

    let throttle interval source =
        source
        |> Seq.mapi (fun i x -> (i, x))
        |> Seq.filter (fun (i, _) -> i % interval = 0)
        |> Seq.map snd

    let aggregate folder initial source =
        source |> Seq.fold folder initial

// ─── 텔레메트리 생성 ───
let generateTelemetry (rng: Random) (droneId: DroneId) count =
    [| for i in 0..count-1 ->
        { DroneId = droneId
          Latitude = 37.5665 + rng.NextDouble() * 0.01
          Longitude = 126.978 + rng.NextDouble() * 0.01
          Altitude = 50.0 + rng.NextDouble() * 350.0
          Speed = rng.NextDouble() * 30.0
          Battery = 100.0 - (float i * 0.5) + rng.NextDouble() * 5.0
          Timestamp = DateTime.UtcNow.AddSeconds(float i) }
    |]

// ─── 경보 감지 파이프라인 ───
let detectAlerts (telemetry: TelemetryData seq) : Alert list =
    let mutable alerts = []

    for t in telemetry do
        if t.Battery < 20.0 then
            alerts <- LowBattery(t.DroneId, t.Battery) :: alerts
        if t.Speed > 25.0 then
            alerts <- SpeedViolation(t.DroneId, t.Speed) :: alerts
        if t.Altitude > 400.0 then
            alerts <- AltitudeViolation(t.DroneId, t.Altitude) :: alerts

    alerts |> List.rev

// ─── 통계 집계 ───
let computeStats (telemetry: TelemetryData[]) (alerts: Alert list) =
    let avgAlt =
        if telemetry.Length > 0 then
            telemetry |> Array.averageBy (fun t -> t.Altitude)
        else 0.0
    let avgSpeed =
        if telemetry.Length > 0 then
            telemetry |> Array.averageBy (fun t -> t.Speed)
        else 0.0
    {| Processed = telemetry.Length
       Alerts = alerts.Length
       AvgAltitude = Math.Round(avgAlt, 2)
       AvgSpeed = Math.Round(avgSpeed, 2)
       DroneCount =
           telemetry
           |> Array.map (fun t -> t.DroneId)
           |> Array.distinct
           |> Array.length |}

// ─── 메시지 포맷 ───
let formatAlert = function
    | LowBattery(id, pct) -> sprintf "LOW_BATTERY: %s (%.1f%%)" id pct
    | SpeedViolation(id, spd) -> sprintf "SPEED_VIOLATION: %s (%.1f m/s)" id spd
    | AltitudeViolation(id, alt) -> sprintf "ALT_VIOLATION: %s (%.1f m)" id alt
    | ProximityWarning(a, b, dist) -> sprintf "PROXIMITY: %s <-> %s (%.1f m)" a b dist

// ─── 실행 ───
let rng = Random(42)
let droneIds = [| for i in 0..9 -> sprintf "DRONE_%03d" i |]

printfn "=== SDACS Reactive Pipeline ==="

// 텔레메트리 생성
let allTelemetry =
    droneIds
    |> Array.collect (fun id -> generateTelemetry rng id 50)

// 파이프라인 처리
let filtered =
    allTelemetry
    |> Pipeline.filter (fun t -> t.Battery > 5.0)
    |> Seq.toArray

let alerts = detectAlerts filtered
let stats = computeStats filtered alerts

printfn "  Processed: %d" stats.Processed
printfn "  Alerts: %d" stats.Alerts
printfn "  Avg Altitude: %.2f m" stats.AvgAltitude
printfn "  Avg Speed: %.2f m/s" stats.AvgSpeed
printfn "  Drones: %d" stats.DroneCount

printfn "\n  Recent alerts:"
alerts |> List.take (min 5 alerts.Length) |> List.iter (fun a ->
    printfn "    %s" (formatAlert a))

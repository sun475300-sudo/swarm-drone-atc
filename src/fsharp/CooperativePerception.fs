// Phase 528: CooperativePerception — F# 기반 협력 인지 시스템
// SDACS Cooperative Perception with Sensor Fusion

module SDACS.CooperativePerception

open System
open System.Collections.Generic

// 탐지 결과 (Detection)
type Detection = {
    DroneId: int
    ObjectId: int
    Confidence: float
    X: float
    Y: float
    Z: float
    Timestamp: float
    ObjectClass: string
}

// 센서 융합(Fusion) 결과
type FusionResult = {
    ObjectId: int
    X: float
    Y: float
    Z: float
    Confidence: float
    ContributingDrones: int list
    FusionMethod: string
}

// 협력 인지 에이전트 (Cooperative Perception Agent)
type PerceptionAgent(droneId: int, sensorRange: float) =
    let mutable detections = List<Detection>()

    member _.DroneId = droneId
    member _.SensorRange = sensorRange

    member _.AddDetection(det: Detection) =
        detections.Add(det)

    member _.GetDetections() = detections |> Seq.toList

    member _.Detect(objectId: int, x: float, y: float, z: float, timestamp: float) =
        let conf = 0.7 + (float droneId % 3) * 0.1
        let det = {
            DroneId = droneId
            ObjectId = objectId
            Confidence = conf
            X = x + (float droneId - 1.5) * 0.5
            Y = y + (float droneId % 2) * 0.3
            Z = z
            Timestamp = timestamp
            ObjectClass = "unknown_object"
        }
        detections.Add(det)
        det

// 센서 퓨전 모듈 (Fuse multiple drone detections)
module SensorFusion =

    // 가중 평균 융합 (Weighted Average Fusion)
    let fuseDetections (dets: Detection list) : FusionResult option =
        if dets.IsEmpty then None
        else
            let totalConf = dets |> List.sumBy (fun d -> d.Confidence)
            let fusedX = dets |> List.sumBy (fun d -> d.X * d.Confidence) |> fun s -> s / totalConf
            let fusedY = dets |> List.sumBy (fun d -> d.Y * d.Confidence) |> fun s -> s / totalConf
            let fusedZ = dets |> List.sumBy (fun d -> d.Z * d.Confidence) |> fun s -> s / totalConf
            let avgConf = totalConf / float dets.Length
            let drones = dets |> List.map (fun d -> d.DroneId) |> List.distinct
            Some {
                ObjectId = dets.Head.ObjectId
                X = fusedX
                Y = fusedY
                Z = fusedZ
                Confidence = min 1.0 (avgConf * (1.0 + float drones.Length * 0.1))
                ContributingDrones = drones
                FusionMethod = "WeightedAverage"
            }

    // 최대 신뢰도 선택 (Max Confidence Selection)
    let selectBestDetection (dets: Detection list) : Detection option =
        dets |> List.sortByDescending (fun d -> d.Confidence) |> List.tryHead

    // 그룹별 Detection 융합
    let fuseByObject (dets: Detection list) : FusionResult list =
        dets
        |> List.groupBy (fun d -> d.ObjectId)
        |> List.choose (fun (_, group) -> fuseDetections group)

// 협력 인지 오케스트레이터
type CooperativePerceptionOrchestrator(droneCount: int) =
    let agents = [0 .. droneCount - 1] |> List.map (fun i -> PerceptionAgent(i, 100.0))

    member _.Agents = agents

    member _.RunPerceptionCycle(objects: (int * float * float * float) list, t: float) =
        let allDetections =
            agents |> List.collect (fun agent ->
                objects |> List.map (fun (objId, x, y, z) ->
                    agent.Detect(objId, x, y, z, t)
                )
            )
        let fused = SensorFusion.fuseByObject allDetections
        fused

    member this.GenerateSummary(results: FusionResult list) =
        let avgConf = results |> List.averageBy (fun r -> r.Confidence)
        let totalDrones = results |> List.collect (fun r -> r.ContributingDrones) |> List.distinct |> List.length
        sprintf "Detection count=%d avg_confidence=%.3f contributing_drones=%d fusion_method=%s"
            results.Length avgConf totalDrones "WeightedAverage"

[<EntryPoint>]
let main _ =
    printfn "SDACS Cooperative Perception — Phase 528\n"

    let orchestrator = CooperativePerceptionOrchestrator(5)
    printfn "드론 에이전트 수: %d" orchestrator.Agents.Length

    let objects = [(1, 200.0, 150.0, 50.0); (2, 300.0, 200.0, 60.0)]
    let results = orchestrator.RunPerceptionCycle(objects, 0.0)

    printfn "\n센서 퓨전(Fuse) 결과:"
    for r in results do
        printfn "  Object %d: pos=(%.1f, %.1f, %.1f) conf=%.3f drones=%A"
            r.ObjectId r.X r.Y r.Z r.Confidence r.ContributingDrones

    let summary = orchestrator.GenerateSummary(results)
    printfn "\n요약: %s" summary
    printfn "협력 인지 처리 완료."
    0

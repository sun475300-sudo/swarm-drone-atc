// SDACS Cooperative Perception — F# (Phase 528)
// 드론 군집 협동 인식: 센서 퓨전 + Detection

module SDACS.CooperativePerception

open System

// Detection 결과
type Detection = {
    ObjectId: string
    X: float
    Y: float
    Z: float
    Confidence: float
    SensorId: string
    Timestamp: DateTime
}

// 센서 데이터
type SensorFrame = {
    SensorId: string
    Detections: Detection list
    Timestamp: DateTime
}

// 퓨전(Fuse) 알고리즘 — 가중 평균
let fuseDetections (detections: Detection list) : Detection option =
    if detections.IsEmpty then None
    else
        let totalWeight = detections |> List.sumBy (fun d -> d.Confidence)
        if totalWeight < 1e-6 then None
        else
            let wx = detections |> List.sumBy (fun d -> d.X * d.Confidence) |> (/) <| totalWeight
            let wy = detections |> List.sumBy (fun d -> d.Y * d.Confidence) |> (/) <| totalWeight
            let wz = detections |> List.sumBy (fun d -> d.Z * d.Confidence) |> (/) <| totalWeight
            let avgConf = totalWeight / float detections.Length
            Some {
                ObjectId = detections |> List.head |> (fun d -> d.ObjectId)
                X = wx; Y = wy; Z = wz
                Confidence = avgConf
                SensorId = "FUSED"
                Timestamp = DateTime.UtcNow
            }

// NMS (Non-Maximum Suppression) 충돌 검출 중복 제거
let nms (detections: Detection list) (threshold: float) : Detection list =
    let rec filter remaining kept =
        match remaining with
        | [] -> kept
        | d :: rest ->
            let overlapping = kept |> List.filter (fun k ->
                let dist = Math.Sqrt((d.X - k.X)**2.0 + (d.Y - k.Y)**2.0 + (d.Z - k.Z)**2.0)
                dist < threshold
            )
            if overlapping.IsEmpty then filter rest (d :: kept)
            else
                let best = overlapping @ [d] |> List.maxBy (fun x -> x.Confidence)
                filter rest (if kept |> List.contains best then kept else best :: (kept |> List.filter (fun k -> k <> best)))
    detections
    |> List.sortByDescending (fun d -> d.Confidence)
    |> fun sorted -> filter sorted []
    |> List.rev

// 협동 퓨전 파이프라인
type PerceptionPipeline(nmsThreshold: float) =
    let mutable frames: SensorFrame list = []
    let mutable fusedDetections: Detection list = []

    member _.IngestFrame(frame: SensorFrame) =
        frames <- frame :: frames

    member _.Fuse() =
        let allDetections = frames |> List.collect (fun f -> f.Detections)
        let byObject = allDetections |> List.groupBy (fun d -> d.ObjectId)
        fusedDetections <-
            byObject
            |> List.choose (fun (_, dets) -> fuseDetections dets)
            |> fun fused -> nms fused nmsThreshold
        fusedDetections

    member _.FusedDetections = fusedDetections
    member _.SensorCount = frames |> List.map (fun f -> f.SensorId) |> List.distinct |> List.length
    member _.DetectionCount = fusedDetections.Length

    member _.HighConfidenceDetections(minConf: float) =
        fusedDetections |> List.filter (fun d -> d.Confidence >= minConf)

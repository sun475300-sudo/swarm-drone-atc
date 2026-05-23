// Phase 528: F# Cooperative Perception — Multi-View Fusion
module CooperativePerception

open System

type ObjectClass = Vehicle | Pedestrian | Drone | Building | Unknown

type Detection = {
    DetectorId: string
    ObjectId: string
    ObjClass: ObjectClass
    Position: float * float * float
    Confidence: float
}

type TrackedObject = {
    TrackId: string
    ObjClass: ObjectClass
    Position: float * float * float
    Confidence: float
    Detections: int
}

type PRNG = { mutable State: uint64 }

let createPRNG seed = { State = seed ^^^ 0x6c62272e07bb0142UL }

let nextRng (rng: PRNG) =
    rng.State <- rng.State ^^^ (rng.State <<< 13)
    rng.State <- rng.State ^^^ (rng.State >>> 7)
    rng.State <- rng.State ^^^ (rng.State <<< 17)
    rng.State

let rngFloat (rng: PRNG) =
    float (nextRng rng &&& 0x7FFFFFFFUL) / float 0x7FFFFFFF

let rngNormal (rng: PRNG) =
    let u1 = max (rngFloat rng) 1e-10
    let u2 = rngFloat rng
    sqrt(-2.0 * log u1) * cos(2.0 * Math.PI * u2)

let distance (x1,y1,z1) (x2,y2,z2) =
    sqrt((x1-x2)**2.0 + (y1-y2)**2.0 + (z1-z2)**2.0)

let fuseDetections (detections: Detection list) threshold =
    let mutable clusters: Detection list list = []
    let mutable used = Set.empty

    for i in 0..detections.Length-1 do
        if not (Set.contains i used) then
            let mutable cluster = [detections.[i]]
            used <- Set.add i used
            for j in i+1..detections.Length-1 do
                if not (Set.contains j used) then
                    let dist = distance detections.[i].Position detections.[j].Position
                    if dist < threshold then
                        cluster <- detections.[j] :: cluster
                        used <- Set.add j used
            clusters <- cluster :: clusters

    clusters |> List.mapi (fun idx cluster ->
        let totalConf = cluster |> List.sumBy (fun d -> d.Confidence)
        let (cx, cy, cz) =
            cluster |> List.fold (fun (ax,ay,az) d ->
                let (dx,dy,dz) = d.Position
                let w = d.Confidence / totalConf
                (ax + dx*w, ay + dy*w, az + dz*w)
            ) (0.0, 0.0, 0.0)
        let fusedConf = 1.0 - (cluster |> List.fold (fun acc d -> acc * (1.0 - d.Confidence)) 1.0)
        let bestClass = cluster |> List.countBy (fun d -> d.ObjClass) |> List.maxBy snd |> fst
        { TrackId = sprintf "T-%04d" idx; ObjClass = bestClass;
          Position = (cx, cy, cz); Confidence = fusedConf;
          Detections = cluster.Length })

let simulateDetections (rng: PRNG) nDrones nObjects =
    let objects = [| for _ in 0..nObjects-1 ->
        (rngNormal rng * 100.0, rngNormal rng * 100.0, 0.0) |]
    let classes = [| Vehicle; Pedestrian; Drone; Building |]
    let mutable detections = []
    for droneIdx in 0..nDrones-1 do
        let dronePos = (rngNormal rng * 50.0, rngNormal rng * 50.0, 50.0 + rngFloat rng * 50.0)
        for objIdx in 0..nObjects-1 do
            let dist = distance dronePos objects.[objIdx]
            if dist < 200.0 && rngFloat rng < (1.0 - dist / 250.0) then
                let noise = rngNormal rng * (dist / 100.0)
                let (ox,oy,oz) = objects.[objIdx]
                let det = { DetectorId = sprintf "drone_%d" droneIdx
                            ObjectId = sprintf "obj_%d" objIdx
                            ObjClass = classes.[int (nextRng rng) % 4]
                            Position = (ox+noise, oy+noise, oz)
                            Confidence = max 0.2 (1.0 - dist/250.0 - rngFloat rng * 0.2) }
                detections <- det :: detections
    detections

[<EntryPoint>]
let main _ =
    let rng = createPRNG 42UL
    let detections = simulateDetections rng 6 20
    let tracks = fuseDetections detections 15.0
    printfn "Raw detections: %d" detections.Length
    printfn "Fused tracks: %d" tracks.Length
    let avgConf = if tracks.IsEmpty then 0.0
                  else tracks |> List.averageBy (fun t -> t.Confidence)
    printfn "Avg confidence: %.4f" avgConf
    0

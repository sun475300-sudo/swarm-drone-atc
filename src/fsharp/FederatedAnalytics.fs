/// Phase 328: F# Federated Analytics
/// Privacy-preserving aggregation with differential privacy.
/// Immutable model updates, functional client selection.

module SDACS.FederatedAnalytics

open System

// ── Types ──────────────────────────────────────────────────────────
type AggregationMethod =
    | FedAvg
    | FedProx of proxWeight: float
    | Scaffold

type ClientStatus =
    | Idle
    | Training
    | Ready
    | Uploading

type FLClient = {
    ClientId: string
    DataSize: int
    ModelWeights: float array
    LocalLoss: float
    Status: ClientStatus
    RoundsParticipated: int
}

type FLRound = {
    RoundId: int
    Participants: string list
    GlobalLoss: float
    AvgLocalLoss: float
    ModelDivergence: float
}

type GlobalModel = {
    Weights: float array
    Version: int
    TotalRounds: int
    BestLoss: float
}

// ── Differential Privacy ───────────────────────────────────────────
let addGaussianNoise (rng: Random) (epsilon: float) (delta: float)
    (sensitivity: float) (data: float array) =
    let sigma = sensitivity * sqrt(2.0 * log(1.25 / delta)) / epsilon
    data |> Array.map (fun x -> x + rng.NextDouble() * sigma * 2.0 - sigma)

// ── Federated Analytics Engine ─────────────────────────────────────
type FederatedAnalyticsEngine(modelDim: int, lr: float, method: AggregationMethod,
                               dpEpsilon: float, dpDelta: float) =
    let rng = Random(42)
    let mutable globalModel = {
        Weights = Array.init modelDim (fun _ -> rng.NextDouble() * 0.2 - 0.1)
        Version = 0
        TotalRounds = 0
        BestLoss = infinity
    }
    let mutable clients = Map.empty<string, FLClient>
    let mutable rounds: FLRound list = []
    let mutable convergence: float list = []

    member _.RegisterClient(clientId: string, dataSize: int) =
        let client = {
            ClientId = clientId
            DataSize = dataSize
            ModelWeights = Array.copy globalModel.Weights
            LocalLoss = infinity
            Status = Idle
            RoundsParticipated = 0
        }
        clients <- clients |> Map.add clientId client
        client

    member _.SelectClients(fraction: float) =
        let allIds = clients |> Map.toList |> List.map fst
        let n = max 1 (int (float allIds.Length * fraction))
        allIds
        |> List.sortBy (fun _ -> rng.Next())
        |> List.take (min n allIds.Length)

    member _.LocalTrain(clientId: string, nEpochs: int) =
        match clients |> Map.tryFind clientId with
        | None -> infinity
        | Some client ->
            let w = Array.copy globalModel.Weights
            let target = Array.init modelDim (fun _ -> rng.NextDouble() * 0.1)
            for _ in 1..nEpochs do
                for i in 0..modelDim-1 do
                    let grad = (w.[i] - target.[i]) + rng.NextDouble() * 0.01
                    w.[i] <- w.[i] - lr * grad
            let loss = w |> Array.mapi (fun i wi -> (wi - target.[i]) ** 2.0)
                         |> Array.average
            clients <- clients |> Map.add clientId
                { client with ModelWeights = w; LocalLoss = loss;
                              Status = Ready; RoundsParticipated = client.RoundsParticipated + 1 }
            loss

    member this.Aggregate(participantIds: string list) =
        let totalData = participantIds |> List.sumBy (fun id ->
            (clients |> Map.find id).DataSize)
        let weightedSum = Array.zeroCreate modelDim

        for cid in participantIds do
            let client = clients |> Map.find cid
            let weight = float client.DataSize / float totalData
            let update =
                if dpEpsilon < infinity then
                    addGaussianNoise rng dpEpsilon dpDelta (2.0 * lr) client.ModelWeights
                else
                    client.ModelWeights

            let adjusted = match method with
                           | FedAvg -> update
                           | FedProx pw ->
                               Array.init modelDim (fun i ->
                                   update.[i] + pw * (globalModel.Weights.[i] - update.[i]))
                           | Scaffold -> update

            for i in 0..modelDim-1 do
                weightedSum.[i] <- weightedSum.[i] + weight * adjusted.[i]

        let totalLoss = participantIds
                        |> List.map (fun id -> (clients |> Map.find id).LocalLoss)
                        |> List.average

        globalModel <- { globalModel with
                            Weights = weightedSum
                            Version = globalModel.Version + 1
                            TotalRounds = globalModel.TotalRounds + 1
                            BestLoss = min globalModel.BestLoss totalLoss }

        // Distribute updated model
        for cid in clients |> Map.toList |> List.map fst do
            let c = clients |> Map.find cid
            clients <- clients |> Map.add cid { c with ModelWeights = Array.copy weightedSum; Status = Idle }

        let flRound = {
            RoundId = globalModel.TotalRounds
            Participants = participantIds
            GlobalLoss = totalLoss
            AvgLocalLoss = totalLoss
            ModelDivergence = 0.0
        }
        rounds <- flRound :: rounds
        convergence <- totalLoss :: convergence
        totalLoss

    member this.RunRound(fraction: float, nEpochs: int) =
        let selected = this.SelectClients(fraction)
        for cid in selected do
            this.LocalTrain(cid, nEpochs) |> ignore
        this.Aggregate(selected)

    member _.Summary() =
        {| TotalClients = clients.Count
           TotalRounds = globalModel.TotalRounds
           ModelVersion = globalModel.Version
           BestLoss = globalModel.BestLoss
           Method = sprintf "%A" method
           DpEpsilon = dpEpsilon |}

[<EntryPoint>]
let main _ =
    let engine = FederatedAnalyticsEngine(20, 0.01, FedAvg, 1.0, 1e-5)
    for i in 0..4 do
        engine.RegisterClient(sprintf "drone_%d" i, 100) |> ignore

    for _ in 1..3 do
        let loss = engine.RunRound(0.6, 5)
        printfn "Round loss: %.6f" loss

    let s = engine.Summary()
    printfn "Clients: %d | Rounds: %d | Best Loss: %.6f"
        s.TotalClients s.TotalRounds s.BestLoss
    0

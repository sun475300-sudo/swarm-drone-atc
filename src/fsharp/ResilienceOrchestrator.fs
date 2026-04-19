// Phase 498: Resilience Orchestrator (F#)
// 카오스 엔지니어링, 자가치유, 불변 이벤트 체인

namespace SDACS.Resilience

open System
open System.Security.Cryptography
open System.Text

type FaultType =
    | NodeCrash
    | NetworkPartition
    | LatencySpike
    | CpuOverload
    | MemoryLeak
    | SensorDrift
    | CommLoss

type HealingAction =
    | Restart
    | Failover
    | ScaleUp
    | Reroute
    | Isolate
    | Recalibrate

type SystemHealth =
    | Healthy
    | Degraded
    | Critical
    | Recovering

type FaultInjection = {
    FaultId: string
    FaultType: FaultType
    Target: string
    Severity: float
    Duration: float
    InjectedAt: float
    Resolved: bool
}

type HealingEvent = {
    FaultId: string
    Action: HealingAction
    Success: bool
    LatencyMs: float
    Timestamp: float
}

type ServiceNode = {
    NodeId: string
    Health: SystemHealth
    CpuUsage: float
    MemoryUsage: float
    Uptime: float
    FaultCount: int
    RestartCount: int
}

module ResilienceOrchestrator =

    let defaultNode id = {
        NodeId = id; Health = Healthy; CpuUsage = 0.2;
        MemoryUsage = 0.3; Uptime = 0.0; FaultCount = 0; RestartCount = 0
    }

    let healingRules = Map.ofList [
        NodeCrash, Restart
        NetworkPartition, Reroute
        LatencySpike, ScaleUp
        CpuOverload, ScaleUp
        MemoryLeak, Restart
        SensorDrift, Recalibrate
        CommLoss, Failover
    ]

    let applyFault (node: ServiceNode) (fault: FaultInjection) : ServiceNode =
        let newHealth =
            match fault.FaultType with
            | NodeCrash | NetworkPartition | CommLoss -> Critical
            | _ -> Degraded
        let newCpu =
            match fault.FaultType with
            | CpuOverload -> min 1.0 (node.CpuUsage + fault.Severity * 0.6)
            | _ -> node.CpuUsage
        let newMem =
            match fault.FaultType with
            | MemoryLeak -> min 1.0 (node.MemoryUsage + fault.Severity * 0.5)
            | _ -> node.MemoryUsage
        { node with
            Health = newHealth
            CpuUsage = newCpu
            MemoryUsage = newMem
            FaultCount = node.FaultCount + 1 }

    let attemptHealing (fault: FaultInjection) (node: ServiceNode) (rngVal: float) : HealingEvent * ServiceNode * FaultInjection =
        let action = Map.tryFind fault.FaultType healingRules |> Option.defaultValue Restart
        let baseProbability = max 0.3 (0.85 - (if fault.Severity > 0.7 then 0.2 else 0.0) -
                                              (if node.RestartCount > 3 then 0.1 else 0.0))
        let success = rngVal < baseProbability
        let latency =
            match action with
            | Restart -> 750.0 | Failover -> 550.0 | _ -> 250.0

        let healedNode =
            if success then
                { node with
                    Health = Recovering
                    CpuUsage = max 0.1 (node.CpuUsage - fault.Severity * 0.4)
                    MemoryUsage = max 0.1 (node.MemoryUsage - fault.Severity * 0.3)
                    RestartCount = if action = Restart then node.RestartCount + 1 else node.RestartCount }
            else node

        let healedFault = if success then { fault with Resolved = true } else fault
        let event = {
            FaultId = fault.FaultId; Action = action;
            Success = success; LatencyMs = latency; Timestamp = 0.0
        }
        (event, healedNode, healedFault)

    let resilienceScore (faults: FaultInjection list) (events: HealingEvent list) : float =
        match faults with
        | [] -> 1.0
        | _ ->
            let resolved = faults |> List.filter (fun f -> f.Resolved) |> List.length
            let score = float resolved / float (List.length faults)
            let avgLatency =
                if List.isEmpty events then 0.0
                else events |> List.map (fun e -> e.LatencyMs) |> List.average
            let penalty = min 0.2 (avgLatency / 5000.0)
            max 0.0 (score - penalty)

    let hashChain (events: HealingEvent list) : string =
        events
        |> List.fold (fun (acc: string) (e: HealingEvent) ->
            let data = sprintf "%s|%s|%A|%b" acc e.FaultId e.Action e.Success
            use sha = SHA256.Create()
            let hash = sha.ComputeHash(Encoding.UTF8.GetBytes(data))
            BitConverter.ToString(hash).Replace("-", "").[..15]
        ) "GENESIS"

    let summary (nodes: ServiceNode list) (faults: FaultInjection list) (events: HealingEvent list) =
        {| Nodes = List.length nodes
           TotalFaults = List.length faults
           ActiveFaults = faults |> List.filter (fun f -> not f.Resolved) |> List.length
           HealingEvents = List.length events
           ResilienceScore = resilienceScore faults events
           AvgHealingLatency =
               if List.isEmpty events then 0.0
               else events |> List.map (fun e -> e.LatencyMs) |> List.average |}

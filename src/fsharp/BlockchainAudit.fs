/// Phase 309: F# Blockchain Audit Trail
/// Immutable hash chain with pattern matching,
/// discriminated unions for event types, LINQ-style queries.

module SDACS.BlockchainAudit

open System
open System.Security.Cryptography
open System.Text

// ── Types ──────────────────────────────────────────────────────────
type EventType =
    | Command
    | StateChange
    | Alert
    | Decision
    | ConfigChange

type AuditEvent = {
    EventType: EventType
    Actor: string
    Description: string
    Data: Map<string, string>
    Timestamp: float
}

type Block = {
    Index: int
    Timestamp: float
    Data: AuditEvent option
    PreviousHash: string
    Nonce: int
    Hash: string
}

type ChainValidation =
    | Valid
    | Invalid of string

// ── Hash Computation ───────────────────────────────────────────────
let computeHash (block: Block) =
    let content =
        sprintf "%d|%f|%A|%s|%d"
            block.Index block.Timestamp block.Data block.PreviousHash block.Nonce
    use sha256 = SHA256.Create()
    let bytes = Encoding.UTF8.GetBytes(content)
    let hash = sha256.ComputeHash(bytes)
    BitConverter.ToString(hash).Replace("-", "").ToLowerInvariant()

// ── Mining ─────────────────────────────────────────────────────────
let mineBlock (difficulty: int) (block: Block) =
    let target = String.replicate difficulty "0"
    let rec mine nonce =
        let candidate = { block with Nonce = nonce }
        let hash = computeHash candidate
        if hash.StartsWith(target) then
            { candidate with Hash = hash }
        else
            mine (nonce + 1)
    mine 0

// ── Blockchain ─────────────────────────────────────────────────────
type BlockchainAuditTrail = {
    Chain: Block list
    Difficulty: int
    PendingEvents: AuditEvent list
}

let createGenesis () =
    let genesis = {
        Index = 0
        Timestamp = float (DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()) / 1000.0
        Data = None
        PreviousHash = String.replicate 64 "0"
        Nonce = 0
        Hash = ""
    }
    { genesis with Hash = computeHash genesis }

let newChain difficulty =
    let genesis = createGenesis ()
    { Chain = [genesis]; Difficulty = difficulty; PendingEvents = [] }

let recordEvent (event: AuditEvent) (chain: BlockchainAuditTrail) =
    let prev = List.head chain.Chain
    let block = {
        Index = prev.Index + 1
        Timestamp = float (DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()) / 1000.0
        Data = Some event
        PreviousHash = prev.Hash
        Nonce = 0
        Hash = ""
    }
    let mined = mineBlock chain.Difficulty block
    { chain with
        Chain = mined :: chain.Chain
        PendingEvents = event :: chain.PendingEvents }

let verifyChain (chain: BlockchainAuditTrail) : ChainValidation =
    let sorted = List.rev chain.Chain
    let rec verify = function
        | [] | [_] -> Valid
        | prev :: current :: rest ->
            let recomputed = computeHash current
            if recomputed <> current.Hash then
                Invalid (sprintf "Block %d hash mismatch" current.Index)
            elif current.PreviousHash <> prev.Hash then
                Invalid (sprintf "Block %d previous hash mismatch" current.Index)
            else
                verify (current :: rest)
    verify sorted

// ── Queries ────────────────────────────────────────────────────────
let queryByType (eventType: EventType) (chain: BlockchainAuditTrail) =
    chain.Chain
    |> List.filter (fun b ->
        match b.Data with
        | Some e -> e.EventType = eventType
        | None -> false)

let queryByActor (actor: string) (chain: BlockchainAuditTrail) =
    chain.Chain
    |> List.filter (fun b ->
        match b.Data with
        | Some e -> e.Actor = actor
        | None -> false)

let queryByTimeRange (startTime: float) (endTime: float) (chain: BlockchainAuditTrail) =
    chain.Chain
    |> List.filter (fun b -> b.Timestamp >= startTime && b.Timestamp <= endTime)

let chainLength (chain: BlockchainAuditTrail) = List.length chain.Chain
let latestBlock (chain: BlockchainAuditTrail) = List.head chain.Chain

let summary (chain: BlockchainAuditTrail) =
    let eventCounts =
        chain.Chain
        |> List.choose (fun b -> b.Data)
        |> List.groupBy (fun e -> e.EventType)
        |> List.map (fun (t, es) -> (t, List.length es))
    let isValid = match verifyChain chain with Valid -> true | _ -> false
    {| ChainLength = chainLength chain
       IsValid = isValid
       EventCounts = eventCounts
       LatestHash = (latestBlock chain).Hash.[..15] + "..." |}

// ── Entry Point ────────────────────────────────────────────────────
[<EntryPoint>]
let main _ =
    let chain =
        newChain 2
        |> recordEvent { EventType = Command; Actor = "atc_1"
                         Description = "Clear drone_1 for takeoff"
                         Data = Map.ofList [("drone", "drone_1")]
                         Timestamp = 0.0 }
        |> recordEvent { EventType = Alert; Actor = "system"
                         Description = "Collision warning"
                         Data = Map.empty; Timestamp = 0.0 }
        |> recordEvent { EventType = Decision; Actor = "ai_engine"
                         Description = "Reroute drone_3"
                         Data = Map.empty; Timestamp = 0.0 }

    let s = summary chain
    printfn "Chain: %d blocks | Valid: %b" s.ChainLength s.IsValid
    s.EventCounts |> List.iter (fun (t, c) -> printfn "  %A: %d" t c)

    match verifyChain chain with
    | Valid -> printfn "Chain integrity: VALID"
    | Invalid msg -> printfn "Chain integrity: INVALID — %s" msg

    0

/// Phase 348: F# Drone Encryption
/// Group key management with immutable key chains.
/// Functional encryption/decryption pipeline.

module SDACS.DroneEncryption

open System
open System.Security.Cryptography
open System.Text

// ── Types ──────────────────────────────────────────────────────────
type CipherSuite =
    | AES256GCM
    | ChaCha20
    | HybridPQ

type KeyPair = {
    PublicKey: byte array
    PrivateKey: byte array
    Algorithm: string
}

type GroupKey = {
    KeyId: string
    KeyData: byte array
    Epoch: int
    MemberIds: string list
    CreatedAt: DateTime
}

type EncryptedMessage = {
    MsgId: string
    SenderId: string
    Recipients: string list
    Ciphertext: byte array
    Nonce: byte array
    Tag: byte array
    KeyId: string
}

type SecurityEvent = {
    EventType: string
    DroneId: string
    Description: string
    Timestamp: DateTime
}

// ── Key Manager ────────────────────────────────────────────────────
type KeyManager(seed: int) =
    let rng = Random(seed)
    let mutable keys = Map.empty<string, GroupKey>
    let mutable epoch = 0

    member _.GenerateGroupKey(memberIds: string list) =
        epoch <- epoch + 1
        let keyData = Array.init 32 (fun _ -> byte (rng.Next(256)))
        let gk = {
            KeyId = sprintf "GK-%06d" epoch
            KeyData = keyData
            Epoch = epoch
            MemberIds = memberIds
            CreatedAt = DateTime.UtcNow
        }
        keys <- keys |> Map.add gk.KeyId gk
        gk

    member _.GetKey(keyId: string) = keys |> Map.tryFind keyId
    member _.Epoch = epoch

    member _.RotateKey(oldKeyId: string, ?excludeMembers: string list) =
        match keys |> Map.tryFind oldKeyId with
        | None -> None
        | Some old ->
            let exclude = defaultArg excludeMembers []
            let members = old.MemberIds |> List.filter (fun m -> not (List.contains m exclude))
            Some (KeyManager.GenerateGroupKeyStatic rng &epoch &keys members)

    static member private GenerateGroupKeyStatic (rng: Random) (epoch: int byref) (keys: Map<string, GroupKey> byref) (memberIds: string list) =
        epoch <- epoch + 1
        let keyData = Array.init 32 (fun _ -> byte (rng.Next(256)))
        let gk = {
            KeyId = sprintf "GK-%06d" epoch
            KeyData = keyData
            Epoch = epoch
            MemberIds = memberIds
            CreatedAt = DateTime.UtcNow
        }
        keys <- keys |> Map.add gk.KeyId gk
        gk

// ── Crypto Functions ───────────────────────────────────────────────
let computeHash (data: byte array) =
    use sha = SHA256.Create()
    sha.ComputeHash(data)

let xorEncrypt (key: byte array) (nonce: byte array) (plaintext: byte array) =
    use sha = SHA256.Create()
    let keyStream = sha.ComputeHash(Array.append key nonce)
    let extended = Array.init plaintext.Length (fun i -> keyStream.[i % keyStream.Length])
    Array.init plaintext.Length (fun i -> plaintext.[i] ^^^ extended.[i])

let computeTag (key: byte array) (ciphertext: byte array) (nonce: byte array) =
    use sha = SHA256.Create()
    sha.ComputeHash(Array.concat [key; ciphertext; nonce]).[..15]

// ── Encryption System ──────────────────────────────────────────────
type DroneEncryptionSystem(cipher: CipherSuite, seed: int) =
    let rng = Random(seed)
    let keyManager = KeyManager(seed)
    let mutable droneKeys = Map.empty<string, KeyPair>
    let mutable activeGroupKey: GroupKey option = None
    let mutable events: SecurityEvent list = []
    let mutable msgCounter = 0

    let logEvent evtType droneId desc =
        events <- { EventType = evtType; DroneId = droneId;
                    Description = desc; Timestamp = DateTime.UtcNow } :: events

    member _.RegisterDrone(droneId: string) =
        let kp = {
            PublicKey = Array.init 32 (fun _ -> byte (rng.Next(256)))
            PrivateKey = Array.init 32 (fun _ -> byte (rng.Next(256)))
            Algorithm = "sim-kyber"
        }
        droneKeys <- droneKeys |> Map.add droneId kp
        kp

    member _.EstablishGroup(memberIds: string list) =
        let gk = keyManager.GenerateGroupKey(memberIds)
        activeGroupKey <- Some gk
        logEvent "group_established" "system" (sprintf "Group %s for %d members" gk.KeyId memberIds.Length)
        gk

    member _.Encrypt(senderId: string, plaintext: byte array) =
        match activeGroupKey with
        | None -> failwith "No active group key"
        | Some gk ->
            msgCounter <- msgCounter + 1
            let nonce = Array.init 12 (fun _ -> byte (rng.Next(256)))
            let ciphertext = xorEncrypt gk.KeyData nonce plaintext
            let tag = computeTag gk.KeyData ciphertext nonce
            {
                MsgId = sprintf "MSG-%08d" msgCounter
                SenderId = senderId
                Recipients = gk.MemberIds
                Ciphertext = ciphertext
                Nonce = nonce
                Tag = tag
                KeyId = gk.KeyId
            }

    member _.Decrypt(msg: EncryptedMessage, droneId: string) =
        if not (List.contains droneId msg.Recipients) then None
        else
            match keyManager.GetKey(msg.KeyId) with
            | None -> None
            | Some gk ->
                let expectedTag = computeTag gk.KeyData msg.Ciphertext msg.Nonce
                if expectedTag <> msg.Tag then
                    logEvent "integrity_fail" droneId (sprintf "Msg %s tag mismatch" msg.MsgId)
                    None
                else
                    Some (xorEncrypt gk.KeyData msg.Nonce msg.Ciphertext)

    member _.RotateKey() =
        match activeGroupKey with
        | None -> None
        | Some gk ->
            let newKey = keyManager.GenerateGroupKey(gk.MemberIds)
            activeGroupKey <- Some newKey
            logEvent "key_rotation" "system" (sprintf "Rotated to %s" newKey.KeyId)
            Some newKey

    member _.RevokeDrone(droneId: string) =
        match activeGroupKey with
        | None -> None
        | Some gk ->
            logEvent "revocation" droneId (sprintf "Drone %s revoked" droneId)
            droneKeys <- droneKeys |> Map.remove droneId
            let members = gk.MemberIds |> List.filter ((<>) droneId)
            let newKey = keyManager.GenerateGroupKey(members)
            activeGroupKey <- Some newKey
            Some newKey

    member _.Summary() =
        {| CipherSuite = sprintf "%A" cipher
           RegisteredDrones = droneKeys.Count
           GroupKeys = keyManager.Epoch
           CurrentEpoch = keyManager.Epoch
           MessagesEncrypted = msgCounter
           SecurityEvents = events.Length |}

[<EntryPoint>]
let main _ =
    let enc = DroneEncryptionSystem(HybridPQ, 42)
    let drones = [for i in 0..4 -> sprintf "drone_%d" i]
    drones |> List.iter (fun d -> enc.RegisterDrone(d) |> ignore)

    enc.EstablishGroup(drones) |> ignore

    let msg = enc.Encrypt("drone_0", Encoding.UTF8.GetBytes("Formation alpha"))
    let decrypted = enc.Decrypt(msg, "drone_1")
    match decrypted with
    | Some data -> printfn "Decrypted: %s" (Encoding.UTF8.GetString(data))
    | None -> printfn "Decryption failed"

    enc.RotateKey() |> ignore
    enc.RevokeDrone("drone_4") |> ignore

    let s = enc.Summary()
    printfn "Drones: %d | Keys: %d | Msgs: %d | Events: %d"
        s.RegisteredDrones s.GroupKeys s.MessagesEncrypted s.SecurityEvents
    0

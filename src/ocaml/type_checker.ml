(* Type Checker — SDACS Phase 660 *)
type message =
  | Telemetry of { drone_id: string }
  | Command of { action: string }

type check_result = Ok | Error of string

let check (msg : message) : check_result =
  match msg with
  | Telemetry { drone_id } when String.length drone_id > 0 -> Ok
  | Command { action } when String.length action > 0 -> Ok
  | _ -> Error "invalid message"

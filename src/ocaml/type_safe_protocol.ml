(* Type-safe Protocol — SDACS Phase 591 *)
(* Defines a type-safe message protocol for drone communication *)

type message =
  | Telemetry of {
      drone_id : string;
      lat      : float;
      lon      : float;
      alt      : float;
      battery  : int;
    }
  | Command of {
      target   : string;
      action   : string;
      params   : (string * string) list;
    }
  | Ack of {
      seq      : int;
      ok       : bool;
      reason   : string option;
    }
  | Heartbeat of { ts : float }

let encode_message (msg : message) : string =
  match msg with
  | Telemetry t ->
    Printf.sprintf "TEL:%s:%.6f:%.6f:%.2f:%d" t.drone_id t.lat t.lon t.alt t.battery
  | Command c ->
    Printf.sprintf "CMD:%s:%s" c.target c.action
  | Ack a ->
    Printf.sprintf "ACK:%d:%b" a.seq a.ok
  | Heartbeat h ->
    Printf.sprintf "HB:%.3f" h.ts

let is_valid (msg : message) : bool =
  match msg with
  | Telemetry t -> String.length t.drone_id > 0 && t.alt >= 0.0
  | Command c   -> String.length c.target > 0
  | Ack a       -> a.seq >= 0
  | Heartbeat h -> h.ts > 0.0
(* end *)
(* end *)
(* end *)
(* end *)
(* end *)
(* end *)
(* end *)
(* end *)
(* end *)
(* end *)
(* end *)
(* end *)

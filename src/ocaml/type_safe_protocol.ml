(* Phase 591: Type-Safe Protocol — 드론 통신 타입 안전 프로토콜 (OCaml) *)
(* Type-safe message passing protocol for swarm drone communication. *)

(** Protocol message variants — type message discriminates all traffic. *)
type message =
  | Heartbeat  of { drone_id: int; battery: float; ts: float }
  | Telemetry  of { drone_id: int; x: float; y: float; z: float; vx: float; vy: float }
  | Command    of { target_id: int; cmd: command_kind; params: float list }
  | Alert      of { drone_id: int; severity: severity_level; detail: string }
  | Ack        of { seq_id: int; ok: bool }
  | MissionItem of { drone_id: int; wp_id: int; lat: float; lon: float; alt: float }

and command_kind =
  | Takeoff | Land | Hover | MoveTo | ReturnHome | EmergencyStop

and severity_level =
  | Info | Warning | Critical

(** Sequence-numbered envelope wraps any message. *)
type 'a envelope = {
  seq  : int;
  from : int;
  to_  : int;
  msg  : 'a;
}

(** Protocol codec: encode / decode messages to/from string representations. *)
module Codec = struct
  let encode_command_kind = function
    | Takeoff       -> "TAKEOFF"
    | Land          -> "LAND"
    | Hover         -> "HOVER"
    | MoveTo        -> "MOVE_TO"
    | ReturnHome    -> "RTH"
    | EmergencyStop -> "ESTOP"

  let encode_severity = function
    | Info     -> "INFO"
    | Warning  -> "WARN"
    | Critical -> "CRIT"

  let encode (msg : message) : string =
    match msg with
    | Heartbeat  h -> Printf.sprintf "HB|%d|%.2f|%.3f" h.drone_id h.battery h.ts
    | Telemetry  t -> Printf.sprintf "TM|%d|%.2f|%.2f|%.2f|%.2f|%.2f"
                        t.drone_id t.x t.y t.z t.vx t.vy
    | Command    c -> Printf.sprintf "CMD|%d|%s|%d"
                        c.target_id (encode_command_kind c.cmd) (List.length c.params)
    | Alert      a -> Printf.sprintf "ALT|%d|%s|%s"
                        a.drone_id (encode_severity a.severity) a.detail
    | Ack        a -> Printf.sprintf "ACK|%d|%s" a.seq_id (if a.ok then "OK" else "FAIL")
    | MissionItem m -> Printf.sprintf "MI|%d|%d|%.6f|%.6f|%.1f"
                        m.drone_id m.wp_id m.lat m.lon m.alt
end

(** Type-safe channel: only well-typed messages can be sent. *)
type channel = {
  id       : int;
  buffer   : message Queue.t;
  capacity : int;
}

let create_channel id cap = { id; buffer = Queue.create (); capacity = cap }

let send_message ch (msg : message) : bool =
  if Queue.length ch.buffer >= ch.capacity then false
  else (Queue.push msg ch.buffer; true)

let recv_message ch : message option =
  if Queue.is_empty ch.buffer then None
  else Some (Queue.pop ch.buffer)

(** Dispatch: route message to appropriate handler. *)
let dispatch (msg : message) ~on_hb ~on_telem ~on_cmd ~on_alert ~on_other =
  match msg with
  | Heartbeat  h -> on_hb h.drone_id h.battery
  | Telemetry  t -> on_telem t.drone_id t.x t.y t.z
  | Command    c -> on_cmd c.target_id c.cmd
  | Alert      a -> on_alert a.drone_id a.severity a.detail
  | _            -> on_other ()

(** Phase 591 demo. *)
let () =
  Printf.printf "Phase 591: Type-Safe Protocol — 드론 타입 안전 통신\n";
  let ch = create_channel 0 100 in
  let msgs = [
    Heartbeat  { drone_id = 1; battery = 82.5; ts = 1700000000.0 };
    Telemetry  { drone_id = 1; x = 100.0; y = 200.0; z = 50.0; vx = 5.0; vy = 0.0 };
    Command    { target_id = 2; cmd = Hover; params = [] };
    Alert      { drone_id = 3; severity = Warning; detail = "low battery" };
  ] in
  List.iter (fun m -> ignore (send_message ch m)) msgs;
  Printf.printf "Buffered: %d messages\n" (Queue.length ch.buffer);
  let encoded = List.map Codec.encode msgs in
  List.iter (fun s -> Printf.printf "  %s\n" s) encoded

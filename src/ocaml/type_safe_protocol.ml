(* Type-safe protocol — OCaml for SDACS drone communication *)
(* Phase 591 *)

(* ── Message Types ─────────────────────────────────────────────── *)

type message_id = string

type message =
  | Heartbeat    of { drone_id: string; timestamp: float; battery: float }
  | Telemetry    of { drone_id: string; lat: float; lon: float; alt: float }
  | Command      of { target_id: string; action: command_action }
  | Ack          of { ref_id: message_id; success: bool }
  | Alert        of { drone_id: string; severity: int; description: string }

and command_action =
  | Takeoff      of float   (* altitude *)
  | Land
  | GoTo         of float * float * float  (* lat, lon, alt *)
  | Return
  | Hold
  | EmergencyStop

(* ── Protocol Codec ────────────────────────────────────────────── *)

type codec_error =
  | InvalidFormat of string
  | UnknownType   of int
  | Truncated

let encode_message (msg : message) : (bytes, codec_error) result =
  match msg with
  | Heartbeat { drone_id; timestamp; battery } ->
      Ok (Bytes.of_string (Printf.sprintf "HB|%s|%.3f|%.1f" drone_id timestamp battery))
  | Telemetry { drone_id; lat; lon; alt } ->
      Ok (Bytes.of_string (Printf.sprintf "TM|%s|%.6f|%.6f|%.1f" drone_id lat lon alt))
  | Command { target_id; action = Takeoff alt } ->
      Ok (Bytes.of_string (Printf.sprintf "CMD|%s|TAKEOFF|%.1f" target_id alt))
  | Command { target_id; action = Land } ->
      Ok (Bytes.of_string (Printf.sprintf "CMD|%s|LAND" target_id))
  | Command { target_id; action = GoTo (lat, lon, alt) } ->
      Ok (Bytes.of_string (Printf.sprintf "CMD|%s|GOTO|%.6f|%.6f|%.1f" target_id lat lon alt))
  | Command { target_id; action = Return } ->
      Ok (Bytes.of_string (Printf.sprintf "CMD|%s|RTL" target_id))
  | Command { target_id; action = Hold } ->
      Ok (Bytes.of_string (Printf.sprintf "CMD|%s|HOLD" target_id))
  | Command { target_id; action = EmergencyStop } ->
      Ok (Bytes.of_string (Printf.sprintf "CMD|%s|ESTOP" target_id))
  | Ack { ref_id; success } ->
      Ok (Bytes.of_string (Printf.sprintf "ACK|%s|%s" ref_id (if success then "OK" else "FAIL")))
  | Alert { drone_id; severity; description } ->
      Ok (Bytes.of_string (Printf.sprintf "ALT|%s|%d|%s" drone_id severity description))

(* ── Message Queue ─────────────────────────────────────────────── *)

type 'a queue = {
  mutable head : 'a list;
  mutable tail : 'a list;
}

let create_queue () = { head = []; tail = [] }

let enqueue q x = q.tail <- x :: q.tail

let dequeue q =
  match q.head with
  | x :: rest -> q.head <- rest; Some x
  | [] ->
      match List.rev q.tail with
      | [] -> None
      | x :: rest ->
          q.head <- rest;
          q.tail <- [];
          Some x

(* ── Protocol State Machine ────────────────────────────────────── *)

type connection_state = Connected | Disconnected | Authenticated

type session = {
  drone_id  : string;
  mutable state : connection_state;
  inbox     : message queue;
  outbox    : message queue;
}

let create_session drone_id = {
  drone_id;
  state   = Disconnected;
  inbox   = create_queue ();
  outbox  = create_queue ();
}

let send_message session msg =
  enqueue session.outbox msg

let receive_message session =
  dequeue session.inbox

(* P591: TypeSafeProtocol - OCaml type-safe communication protocol
   Phase 591: Algebraic data types for drone communication protocol *)

(* Protocol version *)
let protocol_version = "1.0.0"

(* type message: the core message type *)
type message =
  | Heartbeat of { drone_id: string; timestamp: float; seq: int }
  | Telemetry  of { drone_id: string; position: float * float * float;
                    velocity: float * float * float; battery: float }
  | Command    of { target: string; command: string; params: (string * string) list }
  | Ack        of { message_id: string; success: bool; reason: string option }
  | Alert      of { drone_id: string; level: alert_level; description: string }
  | Conflict   of { drone_a: string; drone_b: string; distance: float }

and alert_level = Info | Warning | Critical | Emergency

(* Protocol frame *)
type frame = {
  version    : int;
  seq_num    : int;
  source     : string;
  dest       : string;
  payload    : message;
  checksum   : int;
}

(* Serialize a message to string *)
let message_type_of = function
  | Heartbeat _ -> "HEARTBEAT"
  | Telemetry _ -> "TELEMETRY"
  | Command _   -> "COMMAND"
  | Ack _       -> "ACK"
  | Alert _     -> "ALERT"
  | Conflict _  -> "CONFLICT"

(* Compute simple checksum *)
let compute_checksum (source: string) (dest: string) (seq: int) : int =
  let sum = ref seq in
  String.iter (fun c -> sum := !sum + Char.code c) source;
  String.iter (fun c -> sum := !sum + Char.code c) dest;
  !sum land 0xFFFF

(* Build a frame *)
let make_frame ?(version=1) ~seq ~source ~dest payload =
  let checksum = compute_checksum source dest seq in
  { version; seq_num = seq; source; dest; payload; checksum }

(* Validate a frame *)
let validate_frame frame =
  let expected = compute_checksum frame.source frame.dest frame.seq_num in
  if frame.checksum = expected then Ok frame
  else Error (Printf.sprintf "Checksum mismatch: expected %d, got %d" expected frame.checksum)

(* Route message to handler *)
let route_message handlers frame =
  match validate_frame frame with
  | Error e -> Error e
  | Ok f ->
    let msg_type = message_type_of f.payload in
    match List.assoc_opt msg_type handlers with
    | None    -> Error (Printf.sprintf "No handler for %s" msg_type)
    | Some h  -> Ok (h f.payload)

(* Command parser *)
let parse_command_str s =
  match String.split_on_char ' ' (String.trim s) with
  | cmd :: rest ->
    let params = List.filter_map (fun p ->
      match String.split_on_char '=' p with
      | [k; v] -> Some (k, v)
      | _       -> None
    ) rest in
    Some (cmd, params)
  | [] -> None

(* Alert level to string *)
let alert_level_to_string = function
  | Info      -> "INFO"
  | Warning   -> "WARNING"
  | Critical  -> "CRITICAL"
  | Emergency -> "EMERGENCY"

(** Phase 581: Type-Safe Protocol — OCaml
    SDACS type-safe communication protocol using phantom types and GADTs *)

(** Message direction phantom types *)
type request
type response
type notification

(** Protocol version *)
type version = V1 | V2 | V3

(** Drone command types *)
type command =
  | Arm
  | Disarm
  | TakeOff of float          (** altitude in meters *)
  | Land
  | GoTo of float * float * float  (** lat, lon, alt *)
  | RTL
  | Hold
  | SetSpeed of float
  | SetHeading of float

(** Telemetry data *)
type telemetry = {
  drone_id  : string;
  timestamp : float;
  lat       : float;
  lon       : float;
  alt       : float;
  speed     : float;
  heading   : float;
  battery   : float;
  mode      : string;
}

(** Alert severity *)
type severity = Info | Warning | Critical | Emergency

(** Alert type *)
type alert = {
  alert_id   : string;
  drone_id   : string;
  severity   : severity;
  message    : string;
  timestamp  : float;
}

(** GADT message type — direction-indexed *)
type _ message =
  | Command      : string * command           -> request message
  | TelemetryMsg : telemetry                  -> notification message
  | AlertMsg     : alert                      -> notification message
  | CommandAck   : string * bool * string     -> response message
  | QueryDrones  : string                     -> request message
  | DroneList    : string list                -> response message

(** Protocol frame wraps any message with routing info *)
type 'dir frame = {
  frame_id : string;
  version  : version;
  payload  : 'dir message;
}

(** Encode a message to a string representation *)
let encode_command = function
  | Arm              -> "ARM"
  | Disarm           -> "DISARM"
  | TakeOff alt      -> Printf.sprintf "TAKEOFF %.1f" alt
  | Land             -> "LAND"
  | GoTo (la,lo,al)  -> Printf.sprintf "GOTO %.6f %.6f %.1f" la lo al
  | RTL              -> "RTL"
  | Hold             -> "HOLD"
  | SetSpeed spd     -> Printf.sprintf "SPEED %.1f" spd
  | SetHeading hdg   -> Printf.sprintf "HEADING %.1f" hdg

let encode_severity = function
  | Info      -> "INFO"
  | Warning   -> "WARN"
  | Critical  -> "CRIT"
  | Emergency -> "EMER"

let encode_message : type d. d message -> string = function
  | Command (drone_id, cmd) ->
      Printf.sprintf "CMD|%s|%s" drone_id (encode_command cmd)
  | TelemetryMsg t ->
      Printf.sprintf "TELEM|%s|%.6f|%.6f|%.1f|%.1f|%.1f|%.1f"
        t.drone_id t.lat t.lon t.alt t.speed t.heading t.battery
  | AlertMsg a ->
      Printf.sprintf "ALERT|%s|%s|%s|%s"
        a.drone_id (encode_severity a.severity) a.alert_id a.message
  | CommandAck (msg_id, ok, err) ->
      Printf.sprintf "ACK|%s|%b|%s" msg_id ok err
  | QueryDrones filter ->
      Printf.sprintf "QUERY|DRONES|%s" filter
  | DroneList ids ->
      Printf.sprintf "DRONES|%s" (String.concat "," ids)

(** Frame encoder *)
let encode_frame (frame : 'dir frame) : string =
  let ver = match frame.version with V1 -> "1" | V2 -> "2" | V3 -> "3" in
  Printf.sprintf "%s|v%s|%s" frame.frame_id ver (encode_message frame.payload)

(** Make a request frame *)
let make_request ?(version=V3) frame_id payload =
  { frame_id; version; payload = (payload : request message) }

(** Make a notification frame *)
let make_notification ?(version=V3) frame_id payload =
  { frame_id; version; payload = (payload : notification message) }

(** Telemetry update builder *)
let make_telemetry drone_id lat lon alt speed heading battery mode =
  { drone_id; timestamp = Unix.gettimeofday ();
    lat; lon; alt; speed; heading; battery; mode }

(** Protocol handler type *)
type handler = {
  on_command      : string -> command -> unit;
  on_telemetry    : telemetry -> unit;
  on_alert        : alert -> unit;
}

(** Dispatch a message to the appropriate handler *)
let dispatch : type d. handler -> d message -> unit = fun h msg ->
  match msg with
  | Command (drone_id, cmd) -> h.on_command drone_id cmd
  | TelemetryMsg t          -> h.on_telemetry t
  | AlertMsg a              -> h.on_alert a
  | CommandAck _            -> ()
  | QueryDrones _           -> ()
  | DroneList _             -> ()

(** Default no-op handler *)
let noop_handler = {
  on_command   = (fun _ _ -> ());
  on_telemetry = (fun _ -> ());
  on_alert     = (fun _ -> ());
}

(** Protocol statistics *)
type stats = {
  mutable messages_sent : int;
  mutable messages_recv : int;
  mutable errors        : int;
}

let make_stats () = { messages_sent = 0; messages_recv = 0; errors = 0 }

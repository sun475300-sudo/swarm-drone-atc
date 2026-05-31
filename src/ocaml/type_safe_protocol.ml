(* type_safe_protocol.ml - Type-safe communication protocol for SDACS *)
(* OCaml implementation using GADTs for drone swarm communication *)

(* Core message type definitions *)
type message_priority = Low | Normal | High | Critical

(* Variant type for all drone messages *)
type message =
  | Telemetry of {
      drone_id  : string;
      position  : float * float * float;
      velocity  : float * float * float;
      battery   : int;
      timestamp : float;
    }
  | Command of {
      target    : string;
      command   : string;
      params    : (string * string) list;
      priority  : message_priority;
    }
  | ConflictAlert of {
      drone_a   : string;
      drone_b   : string;
      distance  : float;
      severity  : string;
    }
  | Acknowledge of {
      message_id : int;
      status     : [ `ok | `error | `timeout ];
    }
  | Heartbeat of {
      drone_id : string;
      seq_num  : int;
    }

(* Message serialization *)
type serialized = { id : int; payload : string; priority : message_priority }

(* Protocol state machine type *)
type protocol_state =
  | Disconnected
  | Handshaking
  | Connected of { session_id : string; drone_count : int }
  | Error of string

(* GADT for typed protocol commands *)
type 'a command_t =
  | GetPosition  : (float * float * float) command_t
  | GetBattery   : int command_t
  | GetStatus    : string command_t
  | SetWaypoint  : (float * float * float) -> unit command_t
  | EmergencyStop : unit command_t

module MessageQueue : sig
  type t
  val create     : int -> t
  val push       : t -> message -> unit
  val pop        : t -> message option
  val length     : t -> int
  val is_empty   : t -> bool
end = struct
  type t = { mutable data : message Queue.t; capacity : int }

  let create cap = { data = Queue.create (); capacity = cap }

  let push q msg =
    if Queue.length q.data < q.capacity then
      Queue.push msg q.data

  let pop q =
    if Queue.is_empty q.data then None
    else Some (Queue.pop q.data)

  let length q = Queue.length q.data
  let is_empty q = Queue.is_empty q.data
end

(* Protocol handler *)
module Protocol = struct
  type t = {
    state       : protocol_state ref;
    send_queue  : MessageQueue.t;
    recv_queue  : MessageQueue.t;
    seq_num     : int ref;
  }

  let create () = {
    state      = ref Disconnected;
    send_queue = MessageQueue.create 1000;
    recv_queue = MessageQueue.create 1000;
    seq_num    = ref 0;
  }

  let connect t drone_id =
    t.state := Handshaking;
    let session = Printf.sprintf "sess-%s-%d" drone_id (int_of_float (Unix.gettimeofday ())) in
    t.state := Connected { session_id = session; drone_count = 1 };
    Ok session

  let send_message t msg =
    match !(t.state) with
    | Connected _ ->
      MessageQueue.push t.send_queue msg;
      incr t.seq_num;
      Ok !(t.seq_num)
    | _ -> Error "Not connected"

  let receive_message t =
    MessageQueue.pop t.recv_queue

  let disconnect t =
    t.state := Disconnected

  let get_state t = !(t.state)
end

(* Telemetry message builder *)
let make_telemetry drone_id pos vel bat ts =
  Telemetry {
    drone_id  = drone_id;
    position  = pos;
    velocity  = vel;
    battery   = bat;
    timestamp = ts;
  }

(* Message priority classifier *)
let classify_priority = function
  | ConflictAlert { severity = "critical"; _ } -> Critical
  | ConflictAlert _                             -> High
  | Command { priority; _ }                     -> priority
  | Heartbeat _                                 -> Low
  | _                                           -> Normal

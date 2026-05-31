(* Phase 591 — OCaml type-safe protocol with message type and Pipeline *)
(* SDACS inter-component communication protocol definitions *)

(** Drone identifiers and coordinates *)
type drone_id = DroneId of int

type position = {
  lat : float;
  lon : float;
  alt : float;
}

type velocity = {
  vx : float;
  vy : float;
  vz : float;
}

(** Core protocol message type — all inter-component messages are variants *)
type message =
  | Telemetry of {
      drone : drone_id;
      ts_ms : int64;
      pos   : position;
      vel   : velocity;
      batt  : float;
    }
  | Command of {
      drone  : drone_id;
      action : string;
      params : (string * string) list;
    }
  | Conflict of {
      drone_a : drone_id;
      drone_b : drone_id;
      severity : float;
      pos     : position;
    }
  | Ack of {
      msg_id : int;
      ok     : bool;
      reason : string option;
    }
  | Heartbeat of {
      drone   : drone_id;
      ts_ms   : int64;
      seq_no  : int;
    }
  | Shutdown of drone_id

(** Protocol frame wrapping a message with metadata *)
type frame = {
  frame_id : int;
  src      : string;
  dst      : string;
  payload  : message;
  checksum : int32;
}

(** Pipeline stage processing result *)
type 'a pipeline_result =
  | Ok of 'a
  | Err of string
  | Drop of string

(** Pipeline stage — transforms frames *)
type stage = {
  name    : string;
  process : frame -> frame pipeline_result;
}

(** Pipeline chains stages over a sequence of frames *)
module Pipeline = struct
  type t = {
    name   : string;
    stages : stage list;
  }

  let create name stages = { name; stages }

  let run_stage stage frame =
    stage.process frame

  (** Feed a single frame through all Pipeline stages *)
  let process pipeline frame =
    List.fold_left
      (fun acc stage ->
        match acc with
        | Ok f -> run_stage stage f
        | Err _ as e -> e
        | Drop _ as d -> d)
      (Ok frame)
      pipeline.stages

  (** Process a list of frames, collecting Ok results *)
  let process_all pipeline frames =
    List.filter_map
      (fun f ->
        match process pipeline f with
        | Ok result -> Some result
        | Err msg ->
            Printf.eprintf "[Pipeline:%s] Error: %s\n" pipeline.name msg;
            None
        | Drop reason ->
            Printf.eprintf "[Pipeline:%s] Dropped: %s\n" pipeline.name reason;
            None)
      frames
end

(** Validation stage — rejects frames with empty src/dst *)
let validation_stage : stage = {
  name = "validation";
  process = (fun frame ->
    if frame.src = "" then Err "missing src"
    else if frame.dst = "" then Err "missing dst"
    else Ok frame);
}

(** Logging stage — prints frame metadata and passes through *)
let logging_stage : stage = {
  name = "logging";
  process = (fun frame ->
    Printf.printf "[frame %d] %s -> %s\n" frame.frame_id frame.src frame.dst;
    Ok frame);
}

(** Heartbeat filter — drops heartbeat messages in low-priority mode *)
let heartbeat_filter_stage : stage = {
  name = "heartbeat_filter";
  process = (fun frame ->
    match frame.payload with
    | Heartbeat _ -> Drop "heartbeat filtered"
    | _ -> Ok frame);
}

(** Build the default SDACS message Pipeline *)
let default_pipeline =
  Pipeline.create "sdacs_default"
    [ validation_stage; logging_stage ]

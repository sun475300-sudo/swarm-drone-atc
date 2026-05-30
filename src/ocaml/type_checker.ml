(* Phase 660 — OCaml Type Checker (ADT-based flight command type system) *)

type altitude = float
type heading = float  (* degrees 0-360 *)
type speed = float    (* m/s *)

type command =
  | Takeoff of altitude
  | Land
  | Goto of { lat: float; lon: float; alt: altitude }
  | SetHeading of heading
  | SetSpeed of speed
  | Hover of float  (* seconds *)
  | RTL             (* Return to Launch *)

type check_result = Ok | Error of string

let check_altitude alt =
  if alt < 0.0 then Error "Altitude must be non-negative"
  else if alt > 400.0 then Error "Altitude exceeds 400m limit"
  else Ok

let check_heading h =
  if h < 0.0 || h > 360.0 then Error "Heading must be 0-360 degrees"
  else Ok

let check_command = function
  | Takeoff alt -> check_altitude alt
  | Land | RTL -> Ok
  | Goto { alt; _ } -> check_altitude alt
  | SetHeading h -> check_heading h
  | SetSpeed s -> if s < 0.0 || s > 30.0 then Error "Speed 0-30 m/s" else Ok
  | Hover t -> if t < 0.0 then Error "Duration must be positive" else Ok

let () =
  let cmds = [Takeoff 50.0; Goto {lat=37.5; lon=127.0; alt=100.0}; RTL] in
  List.iter (fun cmd ->
    match check_command cmd with
    | Ok -> print_endline "OK"
    | Error msg -> Printf.printf "Error: %s\n" msg
  ) cmds

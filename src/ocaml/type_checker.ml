(* Phase 660: Type Checker — OCaml Flight Plan Type Verifier *)
(* 비행 계획 타입 검증기: ADT 기반 안전한 비행 명령 타입 시스템 *)

(* ── 기본 타입 정의 ───────────────────────────────── *)

type position = {
  x : float;
  y : float;
  z : float;
}

type velocity = {
  vx : float;
  vy : float;
  vz : float;
}

type drone_id = DroneId of string

type altitude_band = {
  min_alt : float;
  max_alt : float;
}

(* ── 비행 명령 ADT ──────────────────────────────── *)

type flight_command =
  | Takeoff of { target_alt : float }
  | Land of { descent_rate : float }
  | Hover of { duration_s : float }
  | MoveTo of { target : position; speed : float }
  | AvoidClimb of { delta_alt : float }
  | AvoidDescend of { delta_alt : float }
  | AvoidTurnLeft of { angle_deg : float }
  | AvoidTurnRight of { angle_deg : float }
  | EmergencyStop
  | ReturnToLaunch

(* ── 비행 계획 ──────────────────────────────────── *)

type flight_plan = {
  drone : drone_id;
  commands : flight_command list;
  altitude_band : altitude_band;
}

(* ── 타입 검증 결과 ──────────────────────────────── *)

type check_result =
  | Ok
  | Error of string
  | Warning of string

(* ── 검증 함수 ──────────────────────────────────── *)

let check_altitude_bounds (band : altitude_band) (cmd : flight_command) : check_result =
  match cmd with
  | Takeoff { target_alt } ->
    if target_alt > band.max_alt then
      Error (Printf.sprintf "Takeoff target %.1fm exceeds max %.1fm" target_alt band.max_alt)
    else if target_alt < band.min_alt then
      Warning (Printf.sprintf "Takeoff target %.1fm below min %.1fm" target_alt band.min_alt)
    else Ok
  | MoveTo { target; _ } ->
    if target.z > band.max_alt then
      Error (Printf.sprintf "MoveTo altitude %.1fm exceeds max %.1fm" target.z band.max_alt)
    else if target.z < band.min_alt then
      Warning (Printf.sprintf "MoveTo altitude %.1fm below min %.1fm" target.z band.min_alt)
    else Ok
  | AvoidClimb { delta_alt } ->
    if delta_alt > 50.0 then
      Warning (Printf.sprintf "Large climb delta: %.1fm" delta_alt)
    else Ok
  | AvoidDescend { delta_alt } ->
    if delta_alt > 50.0 then
      Warning (Printf.sprintf "Large descend delta: %.1fm" delta_alt)
    else Ok
  | _ -> Ok

let check_speed_limit (cmd : flight_command) : check_result =
  match cmd with
  | MoveTo { speed; _ } ->
    if speed > 25.0 then
      Error (Printf.sprintf "Speed %.1f m/s exceeds limit 25.0 m/s" speed)
    else if speed > 20.0 then
      Warning (Printf.sprintf "Speed %.1f m/s near limit" speed)
    else Ok
  | Land { descent_rate } ->
    if descent_rate > 5.0 then
      Error (Printf.sprintf "Descent rate %.1f m/s too fast (max 5.0)" descent_rate)
    else Ok
  | _ -> Ok

let check_sequence_validity (commands : flight_command list) : check_result list =
  let rec check_seq cmds has_takeoff =
    match cmds with
    | [] -> []
    | Takeoff _ :: rest ->
      if has_takeoff then
        Error "Duplicate Takeoff command" :: check_seq rest true
      else
        Ok :: check_seq rest true
    | Land _ :: rest ->
      if not has_takeoff then
        Error "Land before Takeoff" :: check_seq rest false
      else
        Ok :: check_seq rest false
    | MoveTo _ :: rest ->
      if not has_takeoff then
        Warning "MoveTo before Takeoff" :: check_seq rest has_takeoff
      else
        Ok :: check_seq rest has_takeoff
    | _ :: rest -> Ok :: check_seq rest has_takeoff
  in
  check_seq commands false

(* ── 전체 검증 ──────────────────────────────────── *)

let verify_plan (plan : flight_plan) : check_result list =
  let alt_checks = List.map (check_altitude_bounds plan.altitude_band) plan.commands in
  let speed_checks = List.map check_speed_limit plan.commands in
  let seq_checks = check_sequence_validity plan.commands in
  alt_checks @ speed_checks @ seq_checks

let count_errors (results : check_result list) : int * int * int =
  List.fold_left (fun (ok, warn, err) r ->
    match r with
    | Ok -> (ok + 1, warn, err)
    | Warning _ -> (ok, warn + 1, err)
    | Error _ -> (ok, warn, err + 1)
  ) (0, 0, 0) results

(* ── 메인 ──────────────────────────────────────── *)

let () =
  let plan = {
    drone = DroneId "D-0001";
    altitude_band = { min_alt = 30.0; max_alt = 120.0 };
    commands = [
      Takeoff { target_alt = 60.0 };
      MoveTo { target = { x = 100.0; y = 200.0; z = 80.0 }; speed = 15.0 };
      AvoidClimb { delta_alt = 20.0 };
      Hover { duration_s = 10.0 };
      MoveTo { target = { x = 0.0; y = 0.0; z = 50.0 }; speed = 12.0 };
      Land { descent_rate = 2.0 };
    ];
  } in
  let results = verify_plan plan in
  let (ok, warn, err) = count_errors results in
  Printf.printf "=== Flight Plan Type Checker ===\n";
  Printf.printf "  OK: %d  Warnings: %d  Errors: %d\n" ok warn err;

  (* Test with invalid plan *)
  let bad_plan = {
    drone = DroneId "D-BAD";
    altitude_band = { min_alt = 30.0; max_alt = 120.0 };
    commands = [
      Land { descent_rate = 8.0 };  (* Land before takeoff *)
      Takeoff { target_alt = 150.0 };  (* Exceeds max altitude *)
      MoveTo { target = { x = 0.0; y = 0.0; z = 60.0 }; speed = 30.0 }; (* Over speed *)
    ];
  } in
  let bad_results = verify_plan bad_plan in
  let (ok2, warn2, err2) = count_errors bad_results in
  Printf.printf "\n  Bad plan: OK: %d  Warnings: %d  Errors: %d\n" ok2 warn2 err2;
  List.iter (fun r ->
    match r with
    | Error msg -> Printf.printf "    [ERROR] %s\n" msg
    | Warning msg -> Printf.printf "    [WARN]  %s\n" msg
    | Ok -> ()
  ) bad_results

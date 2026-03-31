(* Phase 591: Type-Safe Communication Protocol — OCaml *)
(* 타입 안전 드론 통신 프로토콜: 대수적 데이터 타입, 패턴 매칭, 직렬화. *)

(* ─── 메시지 타입 ─── *)
type drone_id = string

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

type battery_status = {
  voltage : float;
  current : float;
  remaining : int;  (* percent *)
}

type alert_level = Low | Medium | High | Critical

type conflict_info = {
  drone_a : drone_id;
  drone_b : drone_id;
  distance : float;
  time_to_collision : float;
}

type advisory_action =
  | Climb of float
  | Descend of float
  | TurnLeft of float
  | TurnRight of float
  | Hold
  | ReturnToBase

(* ─── 프로토콜 메시지 (Sum Type) ─── *)
type message =
  | Heartbeat of drone_id * float  (* drone_id, timestamp *)
  | PositionReport of drone_id * position * velocity
  | BatteryReport of drone_id * battery_status
  | ConflictAlert of conflict_info * alert_level
  | ResolutionAdvisory of drone_id * advisory_action
  | MissionAssign of drone_id * string * position list
  | MissionComplete of drone_id * string * float  (* mission_id, duration *)
  | EmergencyLand of drone_id * string  (* reason *)
  | Acknowledge of drone_id * int  (* message_id *)
  | Ping of drone_id
  | Pong of drone_id * float  (* latency_ms *)

(* ─── 직렬화 ─── *)
let string_of_position p =
  Printf.sprintf "(%.6f, %.6f, %.1f)" p.lat p.lon p.alt

let string_of_advisory = function
  | Climb h -> Printf.sprintf "CLIMB %.1fm" h
  | Descend h -> Printf.sprintf "DESCEND %.1fm" h
  | TurnLeft d -> Printf.sprintf "TURN_LEFT %.1f°" d
  | TurnRight d -> Printf.sprintf "TURN_RIGHT %.1f°" d
  | Hold -> "HOLD"
  | ReturnToBase -> "RTB"

let string_of_alert = function
  | Low -> "LOW"
  | Medium -> "MEDIUM"
  | High -> "HIGH"
  | Critical -> "CRITICAL"

let serialize_message = function
  | Heartbeat (id, ts) ->
    Printf.sprintf "HB|%s|%.3f" id ts
  | PositionReport (id, pos, vel) ->
    Printf.sprintf "POS|%s|%s|vx=%.2f,vy=%.2f,vz=%.2f"
      id (string_of_position pos) vel.vx vel.vy vel.vz
  | BatteryReport (id, bat) ->
    Printf.sprintf "BAT|%s|%.1fV|%.1fA|%d%%" id bat.voltage bat.current bat.remaining
  | ConflictAlert (info, level) ->
    Printf.sprintf "CONFLICT|%s|%s-%s|dist=%.1f|ttc=%.1f"
      (string_of_alert level) info.drone_a info.drone_b
      info.distance info.time_to_collision
  | ResolutionAdvisory (id, action) ->
    Printf.sprintf "RA|%s|%s" id (string_of_advisory action)
  | MissionAssign (id, mission, wps) ->
    Printf.sprintf "MISSION|%s|%s|waypoints=%d" id mission (List.length wps)
  | MissionComplete (id, mission, dur) ->
    Printf.sprintf "DONE|%s|%s|%.1fs" id mission dur
  | EmergencyLand (id, reason) ->
    Printf.sprintf "EMERGENCY|%s|%s" id reason
  | Acknowledge (id, msg_id) ->
    Printf.sprintf "ACK|%s|%d" id msg_id
  | Ping id ->
    Printf.sprintf "PING|%s" id
  | Pong (id, lat) ->
    Printf.sprintf "PONG|%s|%.1fms" id lat

(* ─── 메시지 검증 ─── *)
let validate_message = function
  | PositionReport (_, pos, _) ->
    pos.lat >= -90.0 && pos.lat <= 90.0 &&
    pos.lon >= -180.0 && pos.lon <= 180.0 &&
    pos.alt >= 0.0 && pos.alt <= 10000.0
  | BatteryReport (_, bat) ->
    bat.voltage > 0.0 && bat.remaining >= 0 && bat.remaining <= 100
  | ConflictAlert (info, _) ->
    info.distance >= 0.0 && info.time_to_collision >= 0.0
  | _ -> true

(* ─── 메시지 우선순위 ─── *)
let priority_of = function
  | EmergencyLand _ -> 0
  | ConflictAlert (_, Critical) -> 1
  | ConflictAlert (_, High) -> 2
  | ResolutionAdvisory _ -> 3
  | ConflictAlert _ -> 4
  | PositionReport _ -> 5
  | BatteryReport _ -> 6
  | MissionAssign _ -> 7
  | MissionComplete _ -> 8
  | Heartbeat _ -> 9
  | Acknowledge _ -> 10
  | Ping _ | Pong _ -> 11

(* ─── 테스트 ─── *)
let () =
  let messages = [
    Heartbeat ("DRONE_001", 1000.0);
    PositionReport ("DRONE_001",
      { lat = 37.5665; lon = 126.978; alt = 100.0 },
      { vx = 5.0; vy = 3.0; vz = 0.0 });
    BatteryReport ("DRONE_002",
      { voltage = 11.8; current = 5.2; remaining = 72 });
    ConflictAlert (
      { drone_a = "DRONE_001"; drone_b = "DRONE_003";
        distance = 45.0; time_to_collision = 12.5 },
      High);
    ResolutionAdvisory ("DRONE_001", Climb 30.0);
    EmergencyLand ("DRONE_005", "motor_failure");
    Ping "DRONE_002";
    Pong ("DRONE_002", 2.3);
  ] in
  Printf.printf "=== Type-Safe Protocol ===\n";
  List.iter (fun msg ->
    let valid = if validate_message msg then "OK" else "INVALID" in
    let pri = priority_of msg in
    Printf.printf "  [P%02d][%s] %s\n" pri valid (serialize_message msg)
  ) messages;
  Printf.printf "Messages: %d\n" (List.length messages)

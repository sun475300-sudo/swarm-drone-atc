(* SDACS Type-Safe Protocol — OCaml *)
(* 군집드론 타입 안전 프로토콜 모듈 *)

(* 메시지 타입 정의 *)
type message =
  | Heartbeat of { drone_id: string; timestamp: float }
  | TelemetryData of { drone_id: string; lat: float; lon: float; alt: float; battery: int }
  | Command of { target: string; action: string; params: (string * string) list }
  | Acknowledgment of { msg_id: string; status: bool }
  | Alert of { level: string; description: string; drone_id: string }
  | ConflictWarning of { drone_a: string; drone_b: string; distance: float }

(* 드론 상태 타입 *)
type drone_state =
  | Idle
  | Flying of { speed: float; heading: float }
  | Hovering of { position: float * float * float }
  | Landing
  | Emergency

(* 우선순위 큐 항목 타입 *)
type priority_item = {
  priority: int;
  msg: message;
  timestamp: float;
}

(* 메시지 직렬화 *)
let serialize_message msg =
  match msg with
  | Heartbeat { drone_id; timestamp } ->
    Printf.sprintf "HB|%s|%.3f" drone_id timestamp
  | TelemetryData { drone_id; lat; lon; alt; battery } ->
    Printf.sprintf "TEL|%s|%.6f|%.6f|%.2f|%d" drone_id lat lon alt battery
  | Command { target; action; _ } ->
    Printf.sprintf "CMD|%s|%s" target action
  | Acknowledgment { msg_id; status } ->
    Printf.sprintf "ACK|%s|%b" msg_id status
  | Alert { level; description; drone_id } ->
    Printf.sprintf "ALERT|%s|%s|%s" level drone_id description
  | ConflictWarning { drone_a; drone_b; distance } ->
    Printf.sprintf "CONFLICT|%s|%s|%.2f" drone_a drone_b distance

(* 메시지 우선순위 계산 *)
let message_priority msg =
  match msg with
  | Alert { level; _ } when level = "CRITICAL" -> 0
  | Alert _ -> 1
  | ConflictWarning _ -> 2
  | Command _ -> 3
  | TelemetryData _ -> 4
  | Heartbeat _ -> 5
  | Acknowledgment _ -> 6

(* 메시지 검증 *)
let validate_message msg =
  match msg with
  | Heartbeat { drone_id; _ } -> String.length drone_id > 0
  | TelemetryData { lat; lon; alt; battery; _ } ->
    lat >= -90.0 && lat <= 90.0 &&
    lon >= -180.0 && lon <= 180.0 &&
    alt >= 0.0 &&
    battery >= 0 && battery <= 100
  | Command { target; action; _ } ->
    String.length target > 0 && String.length action > 0
  | _ -> true

(* 테스트 실행 *)
let () =
  let hb = Heartbeat { drone_id = "DRONE-001"; timestamp = 1234567890.0 } in
  let tel = TelemetryData { drone_id = "DRONE-001"; lat = 37.5665; lon = 126.978; alt = 100.0; battery = 85 } in
  Printf.printf "Message: %s\n" (serialize_message hb);
  Printf.printf "Priority: %d\n" (message_priority tel);
  Printf.printf "Valid: %b\n" (validate_message tel)

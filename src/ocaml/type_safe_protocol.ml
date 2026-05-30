(* Phase 591: type_safe_protocol — OCaml 타입 안전 통신 프로토콜 *)
(* SDACS Type-Safe Protocol for Drone Communication *)

(* 메시지 타입 정의 (type message) *)
type message =
  | Telemetry of telemetry_data
  | Command   of command_msg
  | Alert     of alert_msg
  | Ack       of ack_msg
  | Heartbeat of heartbeat_msg

and telemetry_data = {
  drone_id  : int;
  timestamp : float;
  lat       : float;
  lon       : float;
  alt       : float;
  battery   : float;
  speed     : float;
}

and command_msg = {
  cmd_id     : string;
  target_id  : int;
  command    : string;
  params     : (string * string) list;
}

and alert_msg = {
  alert_id   : string;
  drone_id   : int;
  severity   : severity_level;
  alert_code : string;
  details    : string;
}

and ack_msg = {
  ack_cmd_id : string;
  drone_id   : int;
  success    : bool;
  reason     : string option;
}

and heartbeat_msg = {
  hb_drone_id : int;
  hb_time     : float;
  hb_status   : string;
}

and severity_level = Info | Warning | Critical | Emergency

(* 메시지 직렬화 *)
let severity_to_string = function
  | Info      -> "INFO"
  | Warning   -> "WARNING"
  | Critical  -> "CRITICAL"
  | Emergency -> "EMERGENCY"

let message_type_name = function
  | Telemetry _ -> "TELEMETRY"
  | Command   _ -> "COMMAND"
  | Alert     _ -> "ALERT"
  | Ack       _ -> "ACK"
  | Heartbeat _ -> "HEARTBEAT"

(* 메시지 직렬화 → 문자열 *)
let serialize_message = function
  | Telemetry t ->
    Printf.sprintf "TELEM|%d|%.3f|%.6f|%.6f|%.2f|%.1f|%.2f"
      t.drone_id t.timestamp t.lat t.lon t.alt t.battery t.speed
  | Command c ->
    let params_str = String.concat "," (List.map (fun (k,v) -> k ^ "=" ^ v) c.params) in
    Printf.sprintf "CMD|%s|%d|%s|%s" c.cmd_id c.target_id c.command params_str
  | Alert a ->
    Printf.sprintf "ALERT|%s|%d|%s|%s|%s"
      a.alert_id a.drone_id (severity_to_string a.severity) a.alert_code a.details
  | Ack a ->
    Printf.sprintf "ACK|%s|%d|%b|%s"
      a.ack_cmd_id a.drone_id a.success (Option.value a.reason ~default:"")
  | Heartbeat h ->
    Printf.sprintf "HB|%d|%.3f|%s" h.hb_drone_id h.hb_time h.hb_status

(* 프로토콜 유효성 검사 *)
let validate_message = function
  | Telemetry t ->
    if t.battery < 0.0 || t.battery > 100.0 then Error "배터리 범위 오류"
    else if t.alt < -10.0 || t.alt > 500.0  then Error "고도 범위 오류"
    else Ok ()
  | Command c ->
    if String.length c.cmd_id = 0 then Error "명령 ID 누락"
    else if c.target_id < 0       then Error "대상 ID 음수"
    else Ok ()
  | Alert a ->
    if String.length a.alert_code = 0 then Error "경보 코드 누락"
    else Ok ()
  | Ack _ | Heartbeat _ -> Ok ()

(* 메시지 라우터 *)
type handler = message -> unit

let route_message handlers msg =
  match List.assoc_opt (message_type_name msg) handlers with
  | Some handler -> handler msg
  | None         -> Printf.printf "  [Router] 핸들러 없음: %s\n" (message_type_name msg)

(* 프로토콜 통계 *)
type protocol_stats = {
  mutable sent     : int;
  mutable received : int;
  mutable errors   : int;
}

let make_stats () = { sent = 0; received = 0; errors = 0 }

let process_message stats handlers msg =
  stats.received <- stats.received + 1;
  match validate_message msg with
  | Error e ->
    stats.errors <- stats.errors + 1;
    Printf.printf "  [Protocol] 검증 오류: %s\n" e
  | Ok () ->
    route_message handlers msg;
    stats.sent <- stats.sent + 1

(* 메인 실행 *)
let () =
  Printf.printf "SDACS Type-Safe Protocol — Phase 591\n\n";

  let messages = [
    Telemetry { drone_id = 0; timestamp = 1748563200.0;
                lat = 37.5; lon = 127.0; alt = 50.0; battery = 95.0; speed = 5.0 };
    Command   { cmd_id = "CMD-001"; target_id = 1; command = "RTL";
                params = [("reason", "low_battery"); ("priority", "high")] };
    Alert     { alert_id = "ALT-001"; drone_id = 2; severity = Warning;
                alert_code = "BATTERY_LOW"; details = "배터리 15% 미만" };
    Heartbeat { hb_drone_id = 0; hb_time = 1748563205.0; hb_status = "GUIDED" };
    Ack       { ack_cmd_id = "CMD-001"; drone_id = 1; success = true; reason = None };
  ] in

  let stats = make_stats () in
  let handlers = [
    ("TELEMETRY", fun msg -> Printf.printf "  [Telem] %s\n" (serialize_message msg));
    ("COMMAND",   fun msg -> Printf.printf "  [Cmd]   %s\n" (serialize_message msg));
    ("ALERT",     fun msg -> Printf.printf "  [Alert] %s\n" (serialize_message msg));
    ("ACK",       fun msg -> Printf.printf "  [Ack]   %s\n" (serialize_message msg));
    ("HEARTBEAT", fun msg -> Printf.printf "  [HB]    %s\n" (serialize_message msg));
  ] in

  Printf.printf "메시지 처리 시작 (%d개):\n" (List.length messages);
  List.iter (process_message stats handlers) messages;

  Printf.printf "\n프로토콜 통계: 수신=%d 전송=%d 오류=%d\n"
    stats.received stats.sent stats.errors;
  Printf.printf "타입 안전 프로토콜 완료.\n"

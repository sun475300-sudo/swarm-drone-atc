(* SDACS Type Checker — OCaml *)
(* 군집드론 프로토콜 타입 검사기 *)

(* 기본 타입 정의 *)
type base_type =
  | TInt
  | TFloat
  | TBool
  | TString
  | TUnit

type drone_type =
  | TDroneId
  | TCoordinate
  | TAltitude
  | TBattery
  | TTimestamp
  | TBase of base_type

(* 타입 검사 결과 *)
type check_result =
  | Ok of drone_type
  | TypeError of string

(* 타입 환경 *)
type type_env = (string * drone_type) list

(* 타입 조회 *)
let lookup env name =
  try Some (List.assoc name env)
  with Not_found -> None

(* 타입 비교 *)
let types_equal t1 t2 = (t1 = t2)

(* 기본 타입 검사 *)
let check_coordinate v =
  if v >= -180.0 && v <= 180.0 then Ok TCoordinate
  else TypeError (Printf.sprintf "Coordinate out of range: %f" v)

let check_altitude v =
  if v >= 0.0 && v <= 500.0 then Ok TAltitude
  else TypeError (Printf.sprintf "Altitude out of range: %f" v)

let check_battery v =
  if v >= 0 && v <= 100 then Ok TBattery
  else TypeError (Printf.sprintf "Battery level invalid: %d" v)

(* 메시지 타입 검사 *)
let check_telemetry_message lat lon alt battery =
  match (check_coordinate lat, check_coordinate lon, check_altitude alt, check_battery battery) with
  | (Ok _, Ok _, Ok _, Ok _) -> Ok TDroneId
  | (TypeError e, _, _, _) -> TypeError ("lat: " ^ e)
  | (_, TypeError e, _, _) -> TypeError ("lon: " ^ e)
  | (_, _, TypeError e, _) -> TypeError ("alt: " ^ e)
  | (_, _, _, TypeError e) -> TypeError ("battery: " ^ e)

(* 환경에서 타입 추론 *)
let infer_type env name =
  match lookup env name with
  | Some t -> Ok t
  | None -> TypeError (Printf.sprintf "Undefined variable: %s" name)

let () =
  let env = [
    ("drone_id", TDroneId);
    ("latitude", TCoordinate);
    ("altitude", TAltitude);
  ] in
  (match infer_type env "drone_id" with
  | Ok t -> Printf.printf "drone_id type: ok\n"
  | TypeError e -> Printf.printf "Error: %s\n" e);
  (match check_telemetry_message 37.5 126.9 100.0 85 with
  | Ok _ -> Printf.printf "Telemetry message: valid\n"
  | TypeError e -> Printf.printf "Invalid: %s\n" e)

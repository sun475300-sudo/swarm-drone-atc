(* Phase 660 — ADT-based Flight Command Type Checker in OCaml *)

type altitude = { meters: float; above: [`Ground | `SeaLevel] }
type heading  = Degrees of float | Cardinal of [`N|`S|`E|`W]
type speed_ms = float

type command =
  | TakeOff   of altitude
  | Land
  | HoverAt   of altitude
  | FlyTo     of { heading: heading; speed: speed_ms; altitude: altitude }
  | ReturnHome
  | Emergency of string

type type_error =
  | NegativeAltitude of float
  | SpeedOutOfRange  of speed_ms
  | InvalidHeading   of float

let check_altitude a =
  if a.meters < 0.0 then Error (NegativeAltitude a.meters) else Ok a

let check_speed s =
  if s < 0.0 || s > 50.0 then Error (SpeedOutOfRange s) else Ok s

let type_check = function
  | TakeOff alt | HoverAt alt -> check_altitude alt |> Result.map (fun _ -> ())
  | FlyTo { speed; altitude; _ } ->
      let ( let* ) = Result.bind in
      let* _ = check_altitude altitude in
      let* _ = check_speed speed in
      Ok ()
  | Land | ReturnHome | Emergency _ -> Ok ()

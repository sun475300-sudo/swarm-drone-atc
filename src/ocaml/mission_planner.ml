(** Phase 309: OCaml Functional Mission Planner
    Algebraic data types for mission modeling,
    immutable waypoint graph, TSP nearest-neighbor solver. *)

(* ── Types ──────────────────────────────────────────────────────── *)
type vec3 = { x : float; y : float; z : float }

type waypoint_action =
  | Transit
  | Scan
  | Photograph
  | Deliver
  | Land

type waypoint = {
  position : vec3;
  altitude : float;
  action : waypoint_action;
  priority : int;
  loiter_sec : float;
}

type mission_objective =
  | MinimizeTime
  | MinimizeEnergy
  | MaximizeCoverage
  | Balanced

type mission_plan = {
  plan_id : string;
  waypoints : waypoint list;
  drone_ids : string list;
  objective : mission_objective;
  total_distance : float;
  estimated_duration : float;
  feasible : bool;
  score : float;
}

type nfz = { center : vec3; radius : float }

(* ── Vec3 Operations ────────────────────────────────────────────── *)
let vec3_sub a b = { x = a.x -. b.x; y = a.y -. b.y; z = a.z -. b.z }
let vec3_add a b = { x = a.x +. b.x; y = a.y +. b.y; z = a.z +. b.z }
let vec3_scale v s = { x = v.x *. s; y = v.y *. s; z = v.z *. s }

let vec3_length v =
  sqrt (v.x *. v.x +. v.y *. v.y +. v.z *. v.z)

let vec3_distance a b = vec3_length (vec3_sub a b)

(* ── Coverage Grid Generator ────────────────────────────────────── *)
let generate_coverage_waypoints ~area_min ~area_max ~spacing ~altitude =
  let wps = ref [] in
  let x = ref area_min.x in
  let row = ref 0 in
  while !x <= area_max.x do
    let y_start = if !row mod 2 = 0 then area_min.y else area_max.y in
    let y_end = if !row mod 2 = 0 then area_max.y else area_min.y in
    let y_step = if !row mod 2 = 0 then spacing else (-.spacing) in
    let y = ref y_start in
    let continue_loop () =
      if !row mod 2 = 0 then !y <= y_end
      else !y >= y_end
    in
    while continue_loop () do
      wps := { position = { x = !x; y = !y; z = altitude };
               altitude; action = Scan; priority = 5; loiter_sec = 0.0 } :: !wps;
      y := !y +. y_step
    done;
    x := !x +. spacing;
    incr row
  done;
  List.rev !wps

(* ── TSP Nearest-Neighbor ───────────────────────────────────────── *)
let solve_tsp waypoints start_pos =
  let n = List.length waypoints in
  let arr = Array.of_list waypoints in
  let visited = Array.make n false in
  let order = Array.make n 0 in
  let current = ref start_pos in
  for step = 0 to n - 1 do
    let best_idx = ref (-1) in
    let best_dist = ref infinity in
    for i = 0 to n - 1 do
      if not visited.(i) then begin
        let d = vec3_distance !current arr.(i).position in
        if d < !best_dist then begin
          best_dist := d;
          best_idx := i
        end
      end
    done;
    if !best_idx >= 0 then begin
      visited.(!best_idx) <- true;
      order.(step) <- !best_idx;
      current := arr.(!best_idx).position
    end
  done;
  Array.to_list order

(* ── NFZ Check ──────────────────────────────────────────────────── *)
let in_nfz nfzs pos =
  List.exists (fun nfz ->
    let dx = pos.x -. nfz.center.x in
    let dy = pos.y -. nfz.center.y in
    sqrt (dx *. dx +. dy *. dy) < nfz.radius
  ) nfzs

let filter_nfz nfzs waypoints =
  List.filter (fun wp -> not (in_nfz nfzs wp.position)) waypoints

(* ── Distance Calculation ───────────────────────────────────────── *)
let calculate_route_distance waypoints start_pos =
  match waypoints with
  | [] -> 0.0
  | first :: rest ->
    let d0 = vec3_distance start_pos first.position in
    let _, total = List.fold_left
      (fun (prev, acc) wp ->
        (wp.position, acc +. vec3_distance prev wp.position))
      (first.position, d0) rest
    in
    total

(* ── Plan Builder ───────────────────────────────────────────────── *)
let create_coverage_plan ~plan_id ~area_min ~area_max ~drone_ids ~start_pos
    ?(objective=Balanced) ?(nfzs=[]) () =
  let raw_wps = generate_coverage_waypoints ~area_min ~area_max
      ~spacing:75.0 ~altitude:50.0 in
  let filtered = filter_nfz nfzs raw_wps in
  let order = solve_tsp filtered start_pos in
  let arr = Array.of_list filtered in
  let ordered = List.map (fun i -> arr.(i)) order in
  let dist = calculate_route_distance ordered start_pos in
  let duration = dist /. 10.0 in
  let score = match objective with
    | MinimizeTime -> max 0.0 (1.0 -. duration /. 3600.0) *. 0.6 +. 0.4
    | MinimizeEnergy -> max 0.0 (1.0 -. dist /. 10000.0) *. 0.6 +. 0.4
    | MaximizeCoverage -> float_of_int (List.length ordered) /.
                          float_of_int (max (List.length ordered) 1)
    | Balanced -> (max 0.0 (1.0 -. duration /. 3600.0) +.
                   max 0.0 (1.0 -. dist /. 10000.0) +. 1.0) /. 3.0
  in
  { plan_id; waypoints = ordered; drone_ids; objective;
    total_distance = dist; estimated_duration = duration;
    feasible = dist <= 10000.0 && duration <= 3600.0;
    score }

(* ── Entry Point ────────────────────────────────────────────────── *)
let () =
  let plan = create_coverage_plan
    ~plan_id:"survey_alpha"
    ~area_min:{ x = 0.0; y = 0.0; z = 0.0 }
    ~area_max:{ x = 300.0; y = 300.0; z = 0.0 }
    ~drone_ids:["drone_1"; "drone_2"]
    ~start_pos:{ x = 0.0; y = 0.0; z = 0.0 }
    ()
  in
  Printf.printf "Plan: %s | Waypoints: %d | Distance: %.1f m | Duration: %.1f s | Feasible: %b\n"
    plan.plan_id (List.length plan.waypoints) plan.total_distance
    plan.estimated_duration plan.feasible

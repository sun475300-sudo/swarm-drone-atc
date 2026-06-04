(** Phase 327: OCaml Algebraic Formation Optimizer
    Purely functional formation geometry computation.
    Pattern matching for formation type dispatch.
    Immutable coordinate transforms. *)

(* ── Types ──────────────────────────────────────────────────────── *)
type vec3 = { x : float; y : float; z : float }

type formation_type =
  | V_Formation
  | Line
  | Grid
  | Circle
  | Diamond
  | Wedge
  | Column

type drone_role = Leader | Follower | Scout | Relay

type formation_drone = {
  drone_id : string;
  position : vec3;
  target : vec3;
  role : drone_role;
  offset : vec3;
}

type formation_config = {
  formation : formation_type;
  spacing : float;
  altitude : float;
  heading_deg : float;
  speed : float;
}

type formation_state = {
  drones : formation_drone list;
  config : formation_config;
  step_count : int;
  cohesion : float;
}

(* ── Vec3 Operations ────────────────────────────────────────────── *)
let vec3_zero = { x = 0.0; y = 0.0; z = 0.0 }
let vec3_add a b = { x = a.x +. b.x; y = a.y +. b.y; z = a.z +. b.z }
let vec3_sub a b = { x = a.x -. b.x; y = a.y -. b.y; z = a.z -. b.z }
let vec3_scale v s = { x = v.x *. s; y = v.y *. s; z = v.z *. s }
let vec3_length v = sqrt (v.x *. v.x +. v.y *. v.y +. v.z *. v.z)
let vec3_distance a b = vec3_length (vec3_sub a b)

let vec3_normalize v =
  let len = vec3_length v in
  if len < 1e-12 then vec3_zero
  else vec3_scale v (1.0 /. len)

(* ── Formation Offset Computation ───────────────────────────────── *)
let compute_offset config idx n =
  let s = config.spacing in
  let raw = match config.formation with
    | V_Formation ->
      let side = if idx mod 2 = 0 then 1.0 else -1.0 in
      let row = float_of_int ((idx + 1) / 2) in
      { x = -.row *. s *. cos (Float.pi /. 6.0);
        y = side *. row *. s *. sin (Float.pi /. 6.0);
        z = 0.0 }
    | Line ->
      { x = -.(float_of_int idx) *. s; y = 0.0; z = 0.0 }
    | Grid ->
      let cols = max 1 (int_of_float (ceil (sqrt (float_of_int n)))) in
      let row = idx / cols and col = idx mod cols in
      { x = -.(float_of_int row) *. s;
        y = (float_of_int col -. float_of_int cols /. 2.0) *. s;
        z = 0.0 }
    | Circle ->
      let angle = 2.0 *. Float.pi *. float_of_int idx /. float_of_int (max (n - 1) 1) in
      let r = s *. float_of_int n /. (2.0 *. Float.pi) in
      { x = r *. cos angle; y = r *. sin angle; z = 0.0 }
    | Diamond ->
      if idx < n / 2 then
        { x = -.(float_of_int idx) *. s *. 0.7;
          y = (float_of_int idx) *. s *. 0.7; z = 0.0 }
      else
        let j = idx - n / 2 in
        { x = -.(float_of_int j) *. s *. 0.7;
          y = -.(float_of_int j) *. s *. 0.7; z = 0.0 }
    | Wedge ->
      let side = if idx mod 2 = 0 then 1.0 else -1.0 in
      { x = -.(float_of_int idx) *. s;
        y = float_of_int idx *. s *. 0.5 *. side; z = 0.0 }
    | Column ->
      { x = -.(float_of_int idx) *. s; y = 0.0; z = 0.0 }
  in
  (* Rotate by heading *)
  let h = config.heading_deg *. Float.pi /. 180.0 in
  let ch = cos h and sh = sin h in
  { x = raw.x *. ch -. raw.y *. sh;
    y = raw.x *. sh +. raw.y *. ch;
    z = raw.z }

(* ── Formation State Creation ───────────────────────────────────── *)
let create_formation config drone_positions =
  let n = List.length drone_positions in
  let drones = List.mapi (fun i (id, pos) ->
    let role = if i = 0 then Leader else Follower in
    let offset = if i = 0 then vec3_zero else compute_offset config (i - 1) (n - 1) in
    { drone_id = id; position = pos; target = vec3_add pos offset;
      role; offset }
  ) drone_positions in
  { drones; config; step_count = 0; cohesion = 1.0 }

(* ── Cohesion Measurement ───────────────────────────────────────── *)
let measure_cohesion state =
  match state.drones with
  | [] | [_] -> 1.0
  | leader :: followers ->
    let errors = List.map (fun d ->
      let target = vec3_add leader.position d.offset in
      vec3_distance d.position target
    ) followers in
    let avg_error = List.fold_left (+.) 0.0 errors /. float_of_int (List.length errors) in
    max 0.0 (1.0 -. avg_error /. (state.config.spacing *. 2.0))

(* ── Step (pure function) ───────────────────────────────────────── *)
let step_formation state dt =
  let h = state.config.heading_deg *. Float.pi /. 180.0 in
  let leader_vel = { x = state.config.speed *. cos h;
                     y = state.config.speed *. sin h; z = 0.0 } in
  let new_drones = List.map (fun drone ->
    match drone.role with
    | Leader ->
      let new_pos = vec3_add drone.position (vec3_scale leader_vel dt) in
      { drone with position = new_pos; target = new_pos }
    | _ ->
      let leader = List.hd state.drones in
      let target = vec3_add leader.position drone.offset in
      let target = { target with z = state.config.altitude } in
      let to_target = vec3_sub target drone.position in
      let dist = vec3_length to_target in
      let vel = if dist > 0.1 then
        vec3_scale (vec3_normalize to_target) (min dist state.config.speed)
      else vec3_zero in
      let new_pos = vec3_add drone.position (vec3_scale vel dt) in
      { drone with position = new_pos; target }
  ) state.drones in
  let new_state = { state with drones = new_drones; step_count = state.step_count + 1 } in
  { new_state with cohesion = measure_cohesion new_state }

(* ── Entry Point ────────────────────────────────────────────────── *)
let () =
  let config = { formation = V_Formation; spacing = 20.0;
                 altitude = 50.0; heading_deg = 0.0; speed = 10.0 } in
  let positions = [
    ("leader", { x = 0.0; y = 0.0; z = 50.0 });
    ("f1", { x = -10.0; y = 10.0; z = 50.0 });
    ("f2", { x = -10.0; y = -10.0; z = 50.0 });
    ("f3", { x = -20.0; y = 20.0; z = 50.0 });
    ("f4", { x = -20.0; y = -20.0; z = 50.0 });
  ] in
  let state = create_formation config positions in
  let final_state = List.init 10 Fun.id |>
    List.fold_left (fun s _ -> step_formation s 0.1) state in
  Printf.printf "Formation: V | Drones: %d | Steps: %d | Cohesion: %.4f\n"
    (List.length final_state.drones) final_state.step_count final_state.cohesion

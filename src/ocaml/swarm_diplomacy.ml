(* Phase 527: Swarm Diplomacy — 군집 드론 게임이론 외교 (OCaml) *)
(* Nash equilibrium-based diplomacy for multi-faction drone swarms. *)

(** Faction represents a group of drones with shared objectives. *)
type faction = {
  id       : int;
  name     : string;
  strength : float;
  resources : float;
}

(** Action that a faction can take. *)
type action =
  | Cooperate
  | Defect
  | Negotiate
  | Retreat

(** Payoff matrix entry for a pair of actions. *)
type payoff = {
  row_gain : float;
  col_gain : float;
}

(** Diplomacy game state. *)
type game_state = {
  factions : faction list;
  round    : int;
  history  : (string * action * action * float * float) list;
}

(** Compute payoff for a pair of faction actions (Prisoner's-dilemma style). *)
let payoff_matrix (a1 : action) (a2 : action) : payoff =
  match a1, a2 with
  | Cooperate, Cooperate -> { row_gain = 3.0; col_gain = 3.0 }
  | Cooperate, Defect    -> { row_gain = 0.0; col_gain = 5.0 }
  | Defect,    Cooperate -> { row_gain = 5.0; col_gain = 0.0 }
  | Defect,    Defect    -> { row_gain = 1.0; col_gain = 1.0 }
  | Negotiate, _         -> { row_gain = 2.5; col_gain = 2.5 }
  | _,         Negotiate -> { row_gain = 2.5; col_gain = 2.5 }
  | Retreat,   _         -> { row_gain = 1.5; col_gain = 2.0 }
  | _,         Retreat   -> { row_gain = 2.0; col_gain = 1.5 }

(** Choose action based on simple Nash-equilibrium heuristic. *)
let choose_action (f : faction) (opponent : faction) : action =
  if f.strength > opponent.strength *. 1.5 then Defect
  else if opponent.strength > f.strength *. 1.5 then Retreat
  else if f.resources > 50.0 then Negotiate
  else Cooperate

(** Play one round between two factions. Returns updated game state. *)
let play_round (state : game_state) (i : int) (j : int) : game_state =
  let f1 = List.nth state.factions i in
  let f2 = List.nth state.factions j in
  let a1 = choose_action f1 f2 in
  let a2 = choose_action f2 f1 in
  let p  = payoff_matrix a1 a2 in
  let label = Printf.sprintf "round%d_%s_vs_%s" state.round f1.name f2.name in
  let new_hist = (label, a1, a2, p.row_gain, p.col_gain) :: state.history in
  { state with round = state.round + 1; history = new_hist }

(** Compute Nash equilibrium check: is (Cooperate, Cooperate) a NE? *)
let is_nash_equilibrium (state : game_state) : bool =
  (* Simple check: majority of rounds ended in mutual cooperation or negotiation *)
  let mutual = List.filter (fun (_, a1, a2, _, _) ->
    a1 = Cooperate && a2 = Cooperate || a1 = Negotiate && a2 = Negotiate)
    state.history in
  let ratio = float_of_int (List.length mutual) /. float_of_int (max 1 (List.length state.history)) in
  ratio >= 0.4

(** Pretty-print action. *)
let string_of_action = function
  | Cooperate -> "COOP" | Defect -> "DFCT" | Negotiate -> "NEGO" | Retreat -> "RETR"

(** Run a full diplomacy simulation. Phase 527. *)
let () =
  Printf.printf "Phase 527: Swarm Diplomacy — 군집 드론 게임이론 외교\n";
  let factions = [
    { id = 0; name = "alpha"; strength = 80.0; resources = 100.0 };
    { id = 1; name = "beta";  strength = 60.0; resources = 80.0  };
    { id = 2; name = "gamma"; strength = 70.0; resources = 55.0  };
  ] in
  let init_state = { factions; round = 0; history = [] } in

  (* Play 6 rounds (all pairs) *)
  let state = ref init_state in
  let pairs = [(0,1); (1,2); (0,2); (0,1); (1,2); (0,2)] in
  List.iter (fun (i, j) ->
    state := play_round !state i j
  ) pairs;

  Printf.printf "Rounds played: %d\n" !state.round;
  Printf.printf "Nash equilibrium achieved: %b\n" (is_nash_equilibrium !state);
  List.iteri (fun idx (lbl, a1, a2, g1, g2) ->
    if idx < 3 then
      Printf.printf "  %s: %s vs %s → gains (%.1f, %.1f)\n"
        lbl (string_of_action a1) (string_of_action a2) g1 g2
  ) (List.rev !state.history)

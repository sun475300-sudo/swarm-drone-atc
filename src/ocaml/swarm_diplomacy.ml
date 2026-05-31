(* Phase 527 — Swarm diplomacy game theory using Nash equilibrium.
   faction definitions, negotiation protocol, and payoff matrix solving.
   Each faction represents a cluster of drones with shared objectives. *)

(* ---- Phase marker ---- *)
let phase_marker = 527

(* ---- Faction definition ----
   A faction is a named group of drones sharing a common objective zone. *)
type faction = {
  id       : string;
  label    : string;
  drone_ids: int list;
  priority : float;   (* higher = more aggressive negotiation stance *)
}

let make_faction id label drones priority =
  { id; label; drone_ids = drones; priority }

(* ---- Default factions for a 3-faction scenario ---- *)
let default_factions = [
  make_faction "F_ALPHA"   "Alpha Squadron"  [1;2;3;4;5]     1.0;
  make_faction "F_BRAVO"   "Bravo Recon"     [6;7;8]         0.8;
  make_faction "F_CHARLIE" "Charlie Relay"   [9;10;11;12]    0.6;
]

(* ---- Strategy type ----
   Each faction can Cooperate (yield airspace) or Defect (assert priority). *)
type strategy = Cooperate | Defect

let strategy_to_string = function
  | Cooperate -> "Cooperate"
  | Defect    -> "Defect"

(* ---- Payoff matrix (2-player, 2-strategy form) ----
   payoff.(s_i).(s_j) = (utility_i, utility_j)
   Represents a Chicken-game variant appropriate for airspace contention:
   mutual Defect => both lose; mutual Cooperate => moderate gain. *)
type payoff_matrix = {
  cc : float * float;  (* Cooperate vs Cooperate *)
  cd : float * float;  (* Cooperate vs Defect    *)
  dc : float * float;  (* Defect    vs Cooperate *)
  dd : float * float;  (* Defect    vs Defect    *)
}

let default_payoff = {
  cc = (3.0, 3.0);
  cd = (0.0, 5.0);
  dc = (5.0, 0.0);
  dd = (1.0, 1.0);
}

(* ---- Lookup payoff for a strategy pair ---- *)
let payoff pm s_i s_j =
  match s_i, s_j with
  | Cooperate, Cooperate -> pm.cc
  | Cooperate, Defect    -> pm.cd
  | Defect,    Cooperate -> pm.dc
  | Defect,    Defect    -> pm.dd

(* ---- Nash equilibrium check ----
   A pure-strategy Nash equilibrium exists when neither player can
   unilaterally improve their payoff by switching strategy.
   Returns all (s_i, s_j) pairs that constitute a Nash equilibrium. *)
let nash_equilibria pm =
  let strategies = [Cooperate; Defect] in
  let is_nash si sj =
    let (ui, _uj) = payoff pm si sj in
    (* Player i cannot improve: no other strategy gives strictly higher ui *)
    let i_ok = List.for_all
      (fun si' -> fst (payoff pm si' sj) <= ui) strategies in
    let (_, uj) = payoff pm si sj in
    (* Player j cannot improve *)
    let j_ok = List.for_all
      (fun sj' -> snd (payoff pm si sj') <= uj) strategies in
    i_ok && j_ok
  in
  List.concat_map
    (fun si -> List.filter_map
      (fun sj -> if is_nash si sj then Some (si, sj) else None)
      strategies)
    strategies

(* ---- Mixed Nash equilibrium (2x2 closed-form) ----
   For the 2-strategy case, the mixed NE probability p for row-player to
   Cooperate satisfies: p * u(C,C) + (1-p) * u(C,D) = p * u(D,C) + (1-p) * u(D,D)
   Returns None if denom is zero (pure-strategy NE only). *)
let mixed_nash_prob pm =
  let (cc, _) = pm.cc in
  let (cd, _) = pm.cd in
  let (dc, _) = pm.dc in
  let (dd, _) = pm.dd in
  let denom = (cc -. cd) -. (dc -. dd) in
  if Float.abs denom < 1e-9 then None
  else
    let p = (dd -. cd) /. denom in
    if p >= 0.0 && p <= 1.0 then Some p else None

(* ---- Negotiation round ----
   Given two factions and a payoff matrix, determines their strategy choices
   (greedy: each faction plays the strategy maximising its own expected payoff
   assuming 50/50 prior over opponent strategy). *)
let negotiate_round pm (fi : faction) (fj : faction) =
  let expected_util s =
    let (u_c, _) = payoff pm s Cooperate in
    let (u_d, _) = payoff pm s Defect in
    (u_c +. u_d) /. 2.0
  in
  let choose_strategy f =
    let _ = f.priority in  (* priority can break ties in extended versions *)
    if expected_util Defect > expected_util Cooperate then Defect else Cooperate
  in
  let si = choose_strategy fi in
  let sj = choose_strategy fj in
  (si, sj, payoff pm si sj)

(* ---- Multi-faction tournament ----
   Each pair of factions negotiates once; results recorded in a list. *)
type negotiation_result = {
  faction_a  : string;
  faction_b  : string;
  strategy_a : strategy;
  strategy_b : strategy;
  utility_a  : float;
  utility_b  : float;
}

let run_tournament factions pm =
  let rec pairs = function
    | [] | [_] -> []
    | x :: rest ->
      List.map (fun y -> (x, y)) rest @ pairs rest
  in
  List.map (fun (fi, fj) ->
    let (si, sj, (ua, ub)) = negotiate_round pm fi fj in
    { faction_a  = fi.id;
      faction_b  = fj.id;
      strategy_a = si;
      strategy_b = sj;
      utility_a  = ua;
      utility_b  = ub }
  ) (pairs factions)

(* ---- Reporter ---- *)
let print_result r =
  Printf.printf
    "  %s(%s) vs %s(%s) => util=(%.1f, %.1f)\n"
    r.faction_a (strategy_to_string r.strategy_a)
    r.faction_b (strategy_to_string r.strategy_b)
    r.utility_a r.utility_b

(* ---- Entry point smoke test ---- *)
let () =
  Printf.printf "[Phase %d] Swarm Diplomacy — Nash equilibrium solver\n" phase_marker;

  let eqs = nash_equilibria default_payoff in
  Printf.printf "Pure Nash equilibria (%d found):\n" (List.length eqs);
  List.iter (fun (si, sj) ->
    Printf.printf "  (%s, %s)\n"
      (strategy_to_string si) (strategy_to_string sj)
  ) eqs;

  (match mixed_nash_prob default_payoff with
  | Some p -> Printf.printf "Mixed Nash p(Cooperate) = %.4f\n" p
  | None   -> Printf.printf "No interior mixed NE\n");

  let results = run_tournament default_factions default_payoff in
  Printf.printf "Tournament results (%d matches):\n" (List.length results);
  List.iter print_result results;

  Printf.printf "[Phase %d] done. faction count=%d\n"
    phase_marker (List.length default_factions)

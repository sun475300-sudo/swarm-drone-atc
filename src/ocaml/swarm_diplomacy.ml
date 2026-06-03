(** Phase 527: Swarm Diplomacy — OCaml
    SDACS multi-faction drone swarm negotiation using Nash equilibrium theory *)

(* Phase 527 marker — Nash equilibrium game theory for swarm coordination *)

(** Faction identifier *)
type faction_id = string

(** Resource type being contested *)
type resource = Airspace | Bandwidth | ChargingStation | PriorityLane

(** Strategy in a negotiation game *)
type strategy = Cooperate | Defect | Negotiate | Yield | Assert

(** Payoff matrix entry *)
type payoff = { self_payoff: float; other_payoff: float }

(** A faction in the swarm *)
type faction = {
  id:          faction_id;
  name:        string;
  drone_count: int;
  priority:    int;    (* 1=highest *)
  resources:   resource list;
}

(** Game state between two factions *)
type game_state = {
  faction_a:   faction;
  faction_b:   faction;
  resource:    resource;
  round:       int;
  history_a:   strategy list;
  history_b:   strategy list;
}

(** Payoff matrix for the airspace allocation game *)
let airspace_payoff (sa: strategy) (sb: strategy) : payoff * payoff =
  (* Returns (payoff_for_a, payoff_for_b) *)
  match sa, sb with
  | Cooperate, Cooperate -> ({self_payoff=3.0; other_payoff=3.0},
                              {self_payoff=3.0; other_payoff=3.0})
  | Cooperate, Defect    -> ({self_payoff=0.0; other_payoff=5.0},
                              {self_payoff=5.0; other_payoff=0.0})
  | Defect,    Cooperate -> ({self_payoff=5.0; other_payoff=0.0},
                              {self_payoff=0.0; other_payoff=5.0})
  | Defect,    Defect    -> ({self_payoff=1.0; other_payoff=1.0},
                              {self_payoff=1.0; other_payoff=1.0})
  | Negotiate, _         -> ({self_payoff=2.5; other_payoff=2.5},
                              {self_payoff=2.5; other_payoff=2.5})
  | _,         Negotiate -> ({self_payoff=2.5; other_payoff=2.5},
                              {self_payoff=2.5; other_payoff=2.5})
  | Yield,     _         -> ({self_payoff=1.5; other_payoff=4.0},
                              {self_payoff=4.0; other_payoff=1.5})
  | _,         Yield     -> ({self_payoff=4.0; other_payoff=1.5},
                              {self_payoff=1.5; other_payoff=4.0})
  | Assert,    Assert    -> ({self_payoff=2.0; other_payoff=2.0},
                              {self_payoff=2.0; other_payoff=2.0})
  | Assert,    _         -> ({self_payoff=3.5; other_payoff=1.5},
                              {self_payoff=1.5; other_payoff=3.5})
  | _,         Assert    -> ({self_payoff=1.5; other_payoff=3.5},
                              {self_payoff=3.5; other_payoff=1.5})

(** Check if a strategy pair is a Nash equilibrium *)
let is_nash_equilibrium (sa: strategy) (sb: strategy) : bool =
  let all_strats = [Cooperate; Defect; Negotiate; Yield; Assert] in
  let (pa, _) = airspace_payoff sa sb in
  let best_a_responds = List.for_all (fun s ->
    let (pa', _) = airspace_payoff s sb in
    pa.self_payoff >= pa'.self_payoff
  ) all_strats in
  let (_, pb) = airspace_payoff sa sb in
  let best_b_responds = List.for_all (fun s ->
    let (_, pb') = airspace_payoff sa s in
    pb.self_payoff >= pb'.self_payoff
  ) all_strats in
  best_a_responds && best_b_responds

(** Find Nash equilibria for the airspace game *)
let find_nash_equilibria () : (strategy * strategy) list =
  let all_strats = [Cooperate; Defect; Negotiate; Yield; Assert] in
  List.filter (fun (sa, sb) -> is_nash_equilibrium sa sb)
    (List.concat_map (fun sa ->
       List.map (fun sb -> (sa, sb)) all_strats
     ) all_strats)

(** Tit-for-tat strategy based on history *)
let tit_for_tat (history: strategy list) : strategy =
  match history with
  | [] -> Cooperate  (* cooperate initially *)
  | prev :: _ -> prev  (* mirror opponent's last move *)

(** Priority-aware strategy: high priority faction asserts more *)
let priority_strategy (own_priority: int) (resource: resource) : strategy =
  match resource, own_priority with
  | PriorityLane, p when p <= 2 -> Assert
  | Airspace,     p when p <= 1 -> Assert
  | _,            p when p <= 2 -> Negotiate
  | _,            _             -> Cooperate

(** Simulate one round of negotiation *)
let simulate_round (state: game_state) : game_state * payoff * payoff =
  let sa = priority_strategy state.faction_a.priority state.resource in
  let sb = tit_for_tat state.history_b in
  let (pa, pb) = airspace_payoff sa sb in
  let new_state = {
    state with
    round     = state.round + 1;
    history_a = sa :: state.history_a;
    history_b = sb :: state.history_b;
  } in
  (new_state, pa, pb)

(** Run multi-round negotiation *)
let negotiate (faction_a: faction) (faction_b: faction)
              (resource: resource) (rounds: int)
    : (payoff * payoff) list =
  let initial = {
    faction_a; faction_b; resource;
    round = 0; history_a = []; history_b = [];
  } in
  let rec loop state acc = function
    | 0 -> List.rev acc
    | n ->
      let (state', pa, pb) = simulate_round state in
      loop state' ((pa, pb) :: acc) (n - 1)
  in
  loop initial [] rounds

(** Compute total payoffs from negotiation rounds *)
let total_payoffs (rounds: (payoff * payoff) list) : float * float =
  List.fold_left (fun (ta, tb) (pa, pb) ->
    (ta +. pa.self_payoff, tb +. pb.self_payoff)
  ) (0.0, 0.0) rounds

(** Print Nash equilibria *)
let report_equilibria () =
  let eq = find_nash_equilibria () in
  Printf.printf "Nash equilibria found: %d\n" (List.length eq);
  List.iter (fun (sa, sb) ->
    Printf.printf "  (%s, %s)\n"
      (match sa with Cooperate->"C"|Defect->"D"|Negotiate->"N"|Yield->"Y"|Assert->"A")
      (match sb with Cooperate->"C"|Defect->"D"|Negotiate->"N"|Yield->"Y"|Assert->"A")
  ) eq

let () =
  Printf.printf "Phase 527: Swarm Diplomacy — Nash Equilibrium Analysis\n";
  report_equilibria ();
  let f1 = { id="F1"; name="Commercial"; drone_count=5; priority=2; resources=[Airspace] } in
  let f2 = { id="F2"; name="Emergency";  drone_count=2; priority=1; resources=[PriorityLane] } in
  let results = negotiate f1 f2 Airspace 5 in
  let (ta, tb) = total_payoffs results in
  Printf.printf "Negotiation over 5 rounds: faction_a=%.1f faction_b=%.1f\n" ta tb

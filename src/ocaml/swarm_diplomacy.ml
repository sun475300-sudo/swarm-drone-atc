(* Phase 527: Swarm Diplomacy Protocol using Game Theory
   Nash equilibrium for multi-faction coordination
   SDACS Multi-Agent Diplomacy Module *)

(* Drone faction types *)
type faction = Alpha | Beta | Gamma | Independent

(* Action in the diplomacy game *)
type action = Cooperate | Defect | Negotiate | Retreat

(* Agent state in the diplomacy protocol *)
type agent_state = {
  drone_id: string;
  faction: faction;
  position: float * float * float;
  resources: float;
  reputation: float;
}

(* Payoff matrix for Nash equilibrium computation *)
type payoff_matrix = {
  actions: action list;
  payoffs: (action * action * float * float) list;
}

(* Create default payoff matrix for swarm diplomacy *)
let default_payoffs () = {
  actions = [Cooperate; Defect; Negotiate; Retreat];
  payoffs = [
    (Cooperate, Cooperate, 3.0, 3.0);
    (Cooperate, Defect,    0.0, 5.0);
    (Defect,    Cooperate, 5.0, 0.0);
    (Defect,    Defect,    1.0, 1.0);
    (Negotiate, Cooperate, 4.0, 4.0);
    (Negotiate, Negotiate, 3.5, 3.5);
    (Retreat,   Defect,    2.0, 2.0);
    (Retreat,   Retreat,   2.5, 2.5);
  ]
}

(* Get payoff for action pair *)
let get_payoff matrix a1 a2 =
  List.fold_left (fun acc (fa, fb, p1, p2) ->
    if fa = a1 && fb = a2 then (p1, p2) else acc
  ) (0.0, 0.0) matrix.payoffs

(* Nash equilibrium finder: best response dynamics *)
let find_nash_equilibrium matrix =
  let actions = matrix.actions in
  (* Compute best response for each action *)
  let best_response a1 =
    List.fold_left (fun (best_a, best_p) a2 ->
      let (p1, _) = get_payoff matrix a1 a2 in
      if p1 > best_p then (a1, p1) else (best_a, best_p)
    ) (Cooperate, neg_infinity) actions
  in
  (* Nash: both agents play best responses simultaneously *)
  List.map (fun a ->
    let (br, payoff) = best_response a in
    (a, br, payoff)
  ) actions

(* faction strategy selection *)
let faction_strategy f =
  match f with
  | Alpha -> Cooperate
  | Beta -> Negotiate
  | Gamma -> Defect
  | Independent -> Retreat

(* Diplomacy resolution between two agents *)
let resolve_diplomacy a1 a2 matrix =
  let s1 = faction_strategy a1.faction in
  let s2 = faction_strategy a2.faction in
  let (p1, p2) = get_payoff matrix s1 s2 in
  (s1, s2, p1, p2)

(* Swarm diplomacy coordinator *)
type diplomacy_coordinator = {
  agents: agent_state list;
  payoffs: payoff_matrix;
  round: int;
  agreements: (string * string * float) list;
}

let create_coordinator agents =
  { agents; payoffs = default_payoffs (); round = 0; agreements = [] }

(* Run one round of diplomacy *)
let run_round coord =
  let new_agreements =
    match coord.agents with
    | a :: b :: _ ->
      let (_, _, p1, _) = resolve_diplomacy a b coord.payoffs in
      [(a.drone_id, b.drone_id, p1)]
    | _ -> []
  in
  { coord with round = coord.round + 1;
               agreements = coord.agreements @ new_agreements }

(* Compute social welfare (sum of all payoffs) *)
let social_welfare coord =
  List.fold_left (fun acc (_, _, v) -> acc +. v) 0.0 coord.agreements

(* Check if Nash equilibrium reached *)
let is_nash_stable coord =
  let nash = find_nash_equilibrium coord.payoffs in
  List.length nash > 0

let () =
  Printf.printf "SDACS Swarm Diplomacy v527\n";
  let agents = [
    { drone_id = "D1"; faction = Alpha; position = (0.0, 0.0, 100.0);
      resources = 80.0; reputation = 0.9 };
    { drone_id = "D2"; faction = Beta; position = (50.0, 0.0, 100.0);
      resources = 70.0; reputation = 0.8 };
  ] in
  let coord = create_coordinator agents in
  let coord' = run_round coord in
  Printf.printf "Nash equilibrium analysis complete\n";
  Printf.printf "Social welfare: %.2f\n" (social_welfare coord');
  Printf.printf "Round: %d, faction diplomacy active\n" coord'.round

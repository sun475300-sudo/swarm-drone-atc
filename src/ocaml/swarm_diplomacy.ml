(* Phase 527 — Swarm Diplomacy Module with Nash Equilibrium and Faction Concepts *)
(* OCaml module for multi-agent strategic negotiation in drone swarms *)

(* ===== Types and Data Structures ===== *)

(** A faction represents a coalition of drones with shared objectives *)
type faction = {
  id: string;
  name: string;
  drone_ids: int list;
  priority: float;
  resources: float;
}

(** A strategic action available to each faction *)
type action =
  | Cooperate
  | Defect
  | Negotiate of float  (* offer value *)
  | Abstain

(** Payoff matrix entry for a two-faction game *)
type payoff_entry = {
  faction_a: string;
  faction_b: string;
  action_a: action;
  action_b: action;
  payoff_a: float;
  payoff_b: float;
}

(** Nash equilibrium solution *)
type nash_solution = {
  strategy_a: action;
  strategy_b: action;
  payoff_a: float;
  payoff_b: float;
  is_dominant: bool;
}

(** Negotiation state between two factions *)
type negotiation_state = {
  round: int;
  offer_a: float;
  offer_b: float;
  agreed: bool;
}

(** Diplomacy session tracking all interactions *)
type diplomacy_session = {
  factions: faction list;
  history: negotiation_state list;
  solutions: nash_solution list;
  round_count: int;
}

(* ===== Faction Operations ===== *)

(** Create a new faction *)
let make_faction id name drone_ids priority resources =
  { id; name; drone_ids; priority; resources }

(** Get the resource total for a faction *)
let faction_strength f = f.resources *. f.priority

(** Merge two factions into a coalition *)
let merge_factions f1 f2 =
  { id = f1.id ^ "_" ^ f2.id;
    name = f1.name ^ "+" ^ f2.name;
    drone_ids = f1.drone_ids @ f2.drone_ids;
    priority = (f1.priority +. f2.priority) /. 2.0;
    resources = f1.resources +. f2.resources }

(* ===== Payoff Matrix (Prisoner's Dilemma variant) ===== *)

(** Compute payoff for cooperation/defection scenarios *)
let compute_payoff action_a action_b =
  match (action_a, action_b) with
  | (Cooperate, Cooperate) -> (3.0, 3.0)    (* Nash equilibrium mutual benefit *)
  | (Cooperate, Defect)    -> (0.0, 5.0)    (* Cooperator exploited *)
  | (Defect, Cooperate)    -> (5.0, 0.0)    (* Defector gains *)
  | (Defect, Defect)       -> (1.0, 1.0)    (* Mutual defection *)
  | (Negotiate v, _)       -> (v, v)        (* Negotiated split *)
  | (Abstain, _)           -> (0.5, 0.5)    (* Both abstain *)
  | _                      -> (0.5, 0.5)

(* ===== Nash Equilibrium Solver ===== *)

(** All possible actions for a faction *)
let all_actions = [Cooperate; Defect; Abstain]

(** Find Nash equilibrium: neither player can improve by unilaterally changing *)
let find_nash_equilibrium () =
  (* Check all action pairs for a dominant strategy Nash equilibrium *)
  let best = ref None in
  List.iter (fun a ->
    List.iter (fun b ->
      let (pa, pb) = compute_payoff a b in
      (* Nash condition: no unilateral deviation improves payoff *)
      let a_can_improve = List.exists (fun a' ->
        let (pa', _) = compute_payoff a' b in pa' > pa
      ) all_actions in
      let b_can_improve = List.exists (fun b' ->
        let (_, pb') = compute_payoff a b' in pb' > pb
      ) all_actions in
      if not a_can_improve && not b_can_improve then begin
        let sol = { strategy_a = a; strategy_b = b;
                    payoff_a = pa; payoff_b = pb;
                    is_dominant = true } in
        match !best with
        | None -> best := Some sol
        | Some prev -> if pa +. pb > prev.payoff_a +. prev.payoff_b then
                         best := Some sol
      end
    ) all_actions
  ) all_actions;
  match !best with
  | Some s -> s
  | None -> { strategy_a = Cooperate; strategy_b = Cooperate;
               payoff_a = 3.0; payoff_b = 3.0; is_dominant = false }

(* ===== Negotiation Protocol ===== *)

(** Run one round of negotiation between two factions *)
let negotiate_round round f1 f2 =
  let offer_a = f1.resources *. 0.4 in
  let offer_b = f2.resources *. 0.4 in
  let agreed = abs_float (offer_a -. offer_b) < (offer_a +. offer_b) *. 0.1 in
  { round; offer_a; offer_b; agreed }

(** Initialize a diplomacy session *)
let init_session factions =
  { factions; history = []; solutions = []; round_count = 0 }

(** Run negotiation for N rounds *)
let run_diplomacy session n_rounds =
  let rec loop s r =
    if r >= n_rounds then s
    else begin
      match s.factions with
      | f1 :: f2 :: _ ->
        let ns = negotiate_round r f1 f2 in
        let eq = find_nash_equilibrium () in
        loop { s with
               history = s.history @ [ns];
               solutions = s.solutions @ [eq];
               round_count = r + 1 } (r + 1)
      | _ -> s
    end
  in
  loop session 0

(** Summarize diplomacy session *)
let summary session =
  let agreed_count = List.length (List.filter (fun n -> n.agreed) session.history) in
  Printf.sprintf "Phase 527 Diplomacy | Factions: %d | Rounds: %d | Agreements: %d | Nash solutions: %d"
    (List.length session.factions)
    session.round_count
    agreed_count
    (List.length session.solutions)

(* ===== Main Entry Point ===== *)
let () =
  let f1 = make_faction "alpha" "Alpha Faction" [1; 2; 3] 0.8 100.0 in
  let f2 = make_faction "beta"  "Beta Faction"  [4; 5; 6] 0.6  80.0 in
  let f3 = make_faction "gamma" "Gamma Faction" [7; 8]    0.7  60.0 in
  let session = init_session [f1; f2; f3] in
  let result = run_diplomacy session 5 in
  print_endline (summary result);
  let eq = find_nash_equilibrium () in
  Printf.printf "Nash equilibrium payoff: (%.1f, %.1f)\n" eq.payoff_a eq.payoff_b;
  let merged = merge_factions f1 f2 in
  Printf.printf "Coalition '%s' strength: %.1f\n" merged.name (faction_strength merged)

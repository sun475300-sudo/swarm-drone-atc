(* swarm_diplomacy.ml - Game theory diplomacy for SDACS swarm (Phase 527) *)
(* Nash equilibrium computation for drone faction negotiations *)

type faction_id = string

(* Drone faction with interests and capabilities *)
type faction = {
  id:           faction_id;
  drones:       int;
  territory:    float * float;  (* lat, lon center *)
  interests:    string list;
  reputation:   float;
}

(* Action available to a faction *)
type action =
  | Cooperate
  | Defect
  | Negotiate of faction_id
  | Cede of float  (* airspace cession *)
  | Assert of float

(* Payoff matrix entry *)
type payoff = { self_payoff: float; other_payoff: float }

(* Nash equilibrium state *)
type nash_equilibrium = {
  faction_a:    faction_id;
  faction_b:    faction_id;
  action_a:     action;
  action_b:     action;
  payoff_a:     float;
  payoff_b:     float;
  is_nash:      bool;
}

(* Payoff function for two factions *)
let compute_payoff action_self action_other =
  match action_self, action_other with
  | Cooperate, Cooperate -> { self_payoff = 3.0; other_payoff = 3.0 }
  | Cooperate, Defect    -> { self_payoff = 0.0; other_payoff = 5.0 }
  | Defect, Cooperate    -> { self_payoff = 5.0; other_payoff = 0.0 }
  | Defect, Defect       -> { self_payoff = 1.0; other_payoff = 1.0 }
  | Negotiate _, _       -> { self_payoff = 2.5; other_payoff = 2.5 }
  | Cede v, _            -> { self_payoff = 1.0 -. v; other_payoff = 2.0 +. v }
  | Assert v, _          -> { self_payoff = 2.0 +. v; other_payoff = 1.0 -. v }

(* Find Nash equilibria in 2x2 game *)
let find_nash_equilibria (a : faction) (b : faction) : nash_equilibrium list =
  let actions = [Cooperate; Defect; Negotiate b.id] in
  let equilibria = ref [] in
  List.iter (fun act_a ->
    List.iter (fun act_b ->
      let pay_a = compute_payoff act_a act_b in
      let pay_b = compute_payoff act_b act_a in
      (* Check if neither player wants to deviate *)
      let a_best = List.for_all (fun other_act ->
        (compute_payoff act_a act_b).self_payoff >=
        (compute_payoff other_act act_b).self_payoff) actions in
      let b_best = List.for_all (fun other_act ->
        (compute_payoff act_b act_a).self_payoff >=
        (compute_payoff other_act act_a).self_payoff) actions in
      if a_best && b_best then
        equilibria := {
          faction_a  = a.id;
          faction_b  = b.id;
          action_a   = act_a;
          action_b   = act_b;
          payoff_a   = pay_a.self_payoff;
          payoff_b   = pay_b.self_payoff;
          is_nash    = true;
        } :: !equilibria
    ) actions
  ) actions;
  !equilibria

(* Compute negotiated airspace partition *)
let negotiate_airspace (factions : faction list) : (faction_id * float) list =
  let n = List.length factions in
  let total = List.fold_left (fun acc f -> acc +. float_of_int f.drones) 0.0 factions in
  List.map (fun f ->
    (f.id, float_of_int f.drones /. total)
  ) factions

(* Diplomacy session state *)
type diplomacy_session = {
  factions:     faction list;
  round:        int;
  agreements:   (faction_id * faction_id * action) list;
  equilibria:   nash_equilibrium list;
}

let create_session factions = {
  factions   = factions;
  round      = 0;
  agreements = [];
  equilibria = [];
}

let run_negotiation session =
  let all_equilibria = ref [] in
  List.iter (fun fa ->
    List.iter (fun fb ->
      if fa.id < fb.id then begin
        let eq = find_nash_equilibria fa fb in
        all_equilibria := eq @ !all_equilibria
      end
    ) session.factions
  ) session.factions;
  { session with equilibria = !all_equilibria; round = session.round + 1 }

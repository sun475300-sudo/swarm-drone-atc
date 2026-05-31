(* P527: SwarmDiplomacy - OCaml Nash equilibrium swarm diplomacy
   Phase 527: Game-theoretic faction negotiation for multi-swarm airspace *)

(* Faction types representing different drone operator groups *)
type faction_id = string

type faction = {
  id: faction_id;
  name: string;
  priority: int;
  airspace_demand: float;   (* fraction of airspace requested *)
  cooperativeness: float;   (* 0..1 willingness to cooperate *)
}

(* Strategy in negotiation: how much airspace to claim *)
type strategy = {
  claimed_fraction: float;
  cooperative: bool;
}

(* Payoff matrix entry *)
type payoff = {
  own_payoff: float;
  other_payoff: float;
}

(* Compute payoff for two factions with given strategies *)
let compute_payoffs (f1: faction) (s1: strategy) (f2: faction) (s2: strategy) : payoff * payoff =
  let total = s1.claimed_fraction +. s2.claimed_fraction in
  if total <= 1.0 then
    (* Both fit: mutual gain *)
    let p1 = { own_payoff = s1.claimed_fraction; other_payoff = s2.claimed_fraction } in
    let p2 = { own_payoff = s2.claimed_fraction; other_payoff = s1.claimed_fraction } in
    (p1, p2)
  else
    (* Conflict: penalty proportional to overclaim *)
    let penalty = total -. 1.0 in
    let p1 = { own_payoff = s1.claimed_fraction -. penalty *. f1.cooperativeness;
               other_payoff = s2.claimed_fraction -. penalty *. (1.0 -. f1.cooperativeness) } in
    let p2 = { own_payoff = s2.claimed_fraction -. penalty *. f2.cooperativeness;
               other_payoff = s1.claimed_fraction -. penalty *. (1.0 -. f2.cooperativeness) } in
    (p1, p2)

(* Find Nash equilibrium by iterated best response *)
let find_nash (f1: faction) (f2: faction) ~steps : strategy * strategy =
  let s1 = ref { claimed_fraction = f1.airspace_demand; cooperative = f1.cooperativeness > 0.5 } in
  let s2 = ref { claimed_fraction = f2.airspace_demand; cooperative = f2.cooperativeness > 0.5 } in
  for _ = 1 to steps do
    (* f1 best responds to f2's strategy *)
    let (p_coop, _) = compute_payoffs f1 { claimed_fraction = 0.4; cooperative = true } f2 !s2 in
    let (p_def, _) = compute_payoffs f1 { claimed_fraction = 0.7; cooperative = false } f2 !s2 in
    s1 := if p_coop.own_payoff >= p_def.own_payoff
          then { claimed_fraction = 0.4; cooperative = true }
          else { claimed_fraction = 0.7; cooperative = false };
    (* f2 best responds to f1's strategy *)
    let (_, q_coop) = compute_payoffs f1 !s1 f2 { claimed_fraction = 0.4; cooperative = true } in
    let (_, q_def)  = compute_payoffs f1 !s1 f2 { claimed_fraction = 0.7; cooperative = false } in
    s2 := if q_coop.other_payoff >= q_def.other_payoff
          then { claimed_fraction = 0.4; cooperative = true }
          else { claimed_fraction = 0.7; cooperative = false };
  done;
  (!s1, !s2)

(* Mediate between multiple factions to allocate airspace *)
let mediate (factions: faction list) : (faction_id * float) list =
  let n = List.length factions in
  if n = 0 then []
  else
    let share = 1.0 /. float_of_int n in
    List.map (fun f ->
      (* Weight by cooperativeness *)
      let allocated = share *. (0.5 +. f.cooperativeness *. 0.5) in
      (f.id, allocated)
    ) factions

(* Negotiate pairwise using Nash equilibrium *)
let negotiate (f1: faction) (f2: faction) : string =
  let (s1, s2) = find_nash f1 f2 ~steps:20 in
  Printf.sprintf "Nash: %s claims %.0f%%, %s claims %.0f%%"
    f1.id (s1.claimed_fraction *. 100.0)
    f2.id (s2.claimed_fraction *. 100.0)

(* Phase 527: OCaml Swarm Diplomacy — Nash Bargaining Solution *)

type faction = {
  id: string;
  name: string;
  n_drones: int;
  resources: float;
  reputation: float;
  power: float;
}

type treaty_type = AirspaceSharing | ResourceExchange | NonAggression | MutualAid
type action = Cooperate | Defect | Negotiate

type event = {
  event_id: string;
  factions: string * string;
  action: action;
  outcome: string;
  payoff_a: float;
  payoff_b: float;
}

type treaty = {
  treaty_id: string;
  ttype: treaty_type;
  parties: string * string;
  active: bool;
}

type prng = { mutable state: int }

let make_prng seed = { state = seed lxor 0x6c62272e }

let next_int rng =
  rng.state <- rng.state lxor (rng.state lsl 13);
  rng.state <- rng.state lxor (rng.state asr 7);
  rng.state <- rng.state lxor (rng.state lsl 17);
  abs rng.state

let next_float rng =
  float_of_int (next_int rng mod 10000) /. 10000.0

(* Nash bargaining: maximize (u_a - d_a) * (u_b - d_b) *)
let nash_bargain rng n_options =
  let ua = Array.init n_options (fun _ -> next_float rng) in
  let ub = Array.init n_options (fun _ -> next_float rng) in
  let best = ref (-1.0, 0.0, 0.0) in
  Array.iteri (fun i _ ->
    let product = ua.(i) *. ub.(i) in
    let (best_p, _, _) = !best in
    if product > best_p then
      best := (product, ua.(i), ub.(i))
  ) ua;
  let (_, a, b) = !best in (a, b)

let create_factions rng n =
  let names = [|"Alpha";"Bravo";"Charlie";"Delta";"Echo";"Foxtrot";"Golf";"Hotel"|] in
  Array.init n (fun i ->
    { id = Printf.sprintf "faction_%d" i;
      name = names.(i mod Array.length names);
      n_drones = 5 + next_int rng mod 45;
      resources = 50.0 +. next_float rng *. 150.0;
      reputation = 0.3 +. next_float rng *. 0.5;
      power = 0.2 +. next_float rng *. 0.7; })

let negotiate rng fa fb =
  let (pay_a, pay_b) = nash_bargain rng 10 in
  let coop_prob = (fa.reputation +. fb.reputation) /. 2.0 in
  if next_float rng < coop_prob then
    { event_id = Printf.sprintf "EVT-%05d" (next_int rng mod 99999);
      factions = (fa.id, fb.id); action = Cooperate;
      outcome = "Treaty signed"; payoff_a = pay_a; payoff_b = pay_b }
  else
    { event_id = Printf.sprintf "EVT-%05d" (next_int rng mod 99999);
      factions = (fa.id, fb.id); action = Defect;
      outcome = "Negotiation failed"; payoff_a = 0.0; payoff_b = 0.0 }

let () =
  let rng = make_prng 42 in
  let factions = create_factions rng 5 in
  let events = ref [] in
  let treaties = ref 0 in

  for _ = 0 to 9 do
    let i = next_int rng mod Array.length factions in
    let j = (i + 1 + next_int rng mod (Array.length factions - 1)) mod Array.length factions in
    let ev = negotiate rng factions.(i) factions.(j) in
    events := ev :: !events;
    if ev.action = Cooperate then incr treaties;
  done;

  Printf.printf "Factions: %d\n" (Array.length factions);
  Printf.printf "Negotiations: %d\n" (List.length !events);
  Printf.printf "Treaties signed: %d\n" !treaties;
  Printf.printf "Cooperation rate: %.2f\n"
    (float_of_int !treaties /. float_of_int (max 1 (List.length !events)))

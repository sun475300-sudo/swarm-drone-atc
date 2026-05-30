(* SDACS Swarm Diplomacy — OCaml (Phase 527)
   드론 군집 외교 프로토콜 — 나시 균형 기반 협상 *)

(* 파벌(faction) 정의 *)
type faction = {
  id: string;
  members: string list;
  priority: float;
  resources: float;
}

(* 협상 제안 *)
type proposal = {
  from_faction: string;
  to_faction: string;
  airspace_allocation: float;  (* 0..1 *)
  timestamp: float;
}

(* 나시 균형 결과 *)
type nash_outcome = {
  factions: faction list;
  allocations: (string * float) list;
  stability: float;
}

(* 나시 균형 계산 (단순 2-player 버전) *)
let compute_nash_equilibrium factions =
  let n = List.length factions in
  if n = 0 then []
  else begin
    let total = List.fold_left (fun acc f -> acc +. f.priority) 0.0 factions in
    List.map (fun f ->
      let share = if total > 0.0 then f.priority /. total else 1.0 /. float_of_int n in
      (f.id, share)
    ) factions
  end

(* 균형 안정성 측정 (편차 합) *)
let stability_score allocations target =
  let n = float_of_int (List.length allocations) in
  if n = 0.0 then 1.0
  else begin
    let dev = List.fold_left (fun acc (_, v) ->
      acc +. abs_float (v -. target)
    ) 0.0 allocations in
    1.0 -. (dev /. n)
  end

(* 외교 협상 라운드 *)
let negotiate_airspace factions =
  let allocs = compute_nash_equilibrium factions in
  let target = 1.0 /. (max 1.0 (float_of_int (List.length factions))) in
  let stab = stability_score allocs target in
  { factions; allocations = allocs; stability = stab }

(* 파벌 병합 제안 *)
let propose_merge f1 f2 =
  {
    from_faction = f1.id;
    to_faction = f2.id;
    airspace_allocation = (f1.resources +. f2.resources) /. 2.0;
    timestamp = Unix.gettimeofday ();
  }

(* 연합 형성 *)
let form_coalition factions threshold =
  List.filter (fun f -> f.priority >= threshold) factions

(* 자원 재분배 *)
let redistribute_resources factions total =
  let sum = List.fold_left (fun a f -> a +. f.priority) 0.0 factions in
  List.map (fun f ->
    let share = if sum > 0.0 then f.priority /. sum *. total else 0.0 in
    { f with resources = share }
  ) factions

(* 외교 히스토리 *)
type diplomacy_log = {
  rounds: int;
  proposals: proposal list;
  outcomes: nash_outcome list;
}

let empty_log = { rounds = 0; proposals = []; outcomes = [] }

let add_round log factions =
  let outcome = negotiate_airspace factions in
  {
    rounds = log.rounds + 1;
    proposals = log.proposals;
    outcomes = outcome :: log.outcomes;
  }

let latest_stability log =
  match log.outcomes with
  | [] -> 0.0
  | o :: _ -> o.stability

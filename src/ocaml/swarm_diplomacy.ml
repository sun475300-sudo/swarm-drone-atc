(* Phase 527: swarm_diplomacy — OCaml 기반 군집 드론 외교 협상 *)
(* SDACS Swarm Diplomacy via Nash Equilibrium Game Theory *)

(* 드론 파벌(Faction) 정의 *)
type faction = {
  id: int;
  name: string;
  territory: float * float * float * float;  (* lat_min, lat_max, lon_min, lon_max *)
  priority: int;
}

(* 협상 행동 집합 *)
type action =
  | Cooperate
  | Defect
  | Negotiate
  | Yield

(* 보수 행렬 (payoff matrix) *)
type payoff_matrix = {
  rows: int;
  cols: int;
  data: float array array;
}

let make_payoff rows cols f =
  { rows; cols; cols; data = Array.init rows (fun i -> Array.init cols (f i)) }

(* 2인 게임 보수 정의 (협력/배반) *)
let airspace_payoff () =
  (* Prisoner's Dilemma 변형 *)
  [|
    [| 3.0; 0.0; 2.0; 1.5 |];   (* Cooperate vs {C,D,N,Y} *)
    [| 5.0; 1.0; 2.5; 4.0 |];   (* Defect    vs {C,D,N,Y} *)
    [| 2.5; 0.5; 2.0; 2.0 |];   (* Negotiate vs {C,D,N,Y} *)
    [| 1.0; 0.0; 1.5; 1.0 |];   (* Yield     vs {C,D,N,Y} *)
  |]

let action_to_idx = function
  | Cooperate -> 0
  | Defect    -> 1
  | Negotiate -> 2
  | Yield     -> 3

let idx_to_action = function
  | 0 -> Cooperate
  | 1 -> Defect
  | 2 -> Negotiate
  | _ -> Yield

let action_name = function
  | Cooperate -> "협력"
  | Defect    -> "배반"
  | Negotiate -> "협상"
  | Yield     -> "양보"

(* Nash 균형 탐색 (순수 전략) *)
let find_nash_equilibrium payoff n_actions =
  (* 최선 응답 함수 *)
  let best_response_row col_action =
    let scores = Array.init n_actions (fun r -> payoff.(r).(col_action)) in
    let max_val = Array.fold_left max neg_infinity scores in
    let idx = ref 0 in
    Array.iteri (fun i v -> if v = max_val then idx := i) scores;
    !idx
  in
  let best_response_col row_action =
    let scores = payoff.(row_action) in
    let max_val = Array.fold_left max neg_infinity scores in
    let idx = ref 0 in
    Array.iteri (fun i v -> if v = max_val then idx := i) scores;
    !idx
  in
  (* Nash 균형 찾기: (r,c)에서 둘 다 이탈 인센티브 없음 *)
  let equilibria = ref [] in
  for r = 0 to n_actions - 1 do
    for c = 0 to n_actions - 1 do
      if best_response_row c = r && best_response_col r = c then
        equilibria := (r, c) :: !equilibria
    done
  done;
  !equilibria

(* 협상 프로토콜 *)
type negotiation_result = {
  faction_a: int;
  faction_b: int;
  action_a: action;
  action_b: action;
  payoff_a: float;
  payoff_b: float;
  is_nash: bool;
}

let negotiate_factions fa fb payoff =
  let n = 4 in
  let nash_list = find_nash_equilibrium payoff n in
  let (ra, rb) = match nash_list with
    | (r, c) :: _ -> (r, c)
    | []           -> (0, 0)  (* 기본값: 협력 *)
  in
  let is_nash = List.mem (ra, rb) nash_list in
  {
    faction_a = fa.id;
    faction_b = fb.id;
    action_a  = idx_to_action ra;
    action_b  = idx_to_action rb;
    payoff_a  = payoff.(ra).(rb);
    payoff_b  = payoff.(rb).(ra);
    is_nash   = is_nash;
  }

(* 메인 실행 *)
let () =
  Printf.printf "SDACS Swarm Diplomacy — Phase 527\n\n";

  let factions = [
    { id = 0; name = "Alpha"; territory = (37.49, 37.51, 126.98, 127.00); priority = 1 };
    { id = 1; name = "Beta";  territory = (37.50, 37.52, 126.99, 127.01); priority = 2 };
    { id = 2; name = "Gamma"; territory = (37.51, 37.53, 127.00, 127.02); priority = 3 };
  ] in

  Printf.printf "등록된 파벌(faction): %d개\n" (List.length factions);
  List.iter (fun f ->
    Printf.printf "  파벌 %d [%s]: 우선순위=%d\n" f.id f.name f.priority
  ) factions;

  let payoff = airspace_payoff () in

  Printf.printf "\n공역 협상 시뮬레이션 (Nash 균형):\n";
  let fa = List.nth factions 0 in
  let fb = List.nth factions 1 in
  let result = negotiate_factions fa fb payoff in

  Printf.printf "  파벌 %d vs 파벌 %d:\n" result.faction_a result.faction_b;
  Printf.printf "    행동: [%s] vs [%s]\n" (action_name result.action_a) (action_name result.action_b);
  Printf.printf "    보수: %.1f / %.1f\n" result.payoff_a result.payoff_b;
  Printf.printf "    Nash 균형: %b\n" result.is_nash;

  let nash_list = find_nash_equilibrium payoff 4 in
  Printf.printf "\n전체 Nash 균형 수: %d\n" (List.length nash_list);
  Printf.printf "군집 외교 협상 완료.\n"

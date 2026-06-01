(* Phase 650: Type Checker — 드론 미션 명령 타입 검사기 (OCaml) *)
(* Hindley-Milner style type inference for swarm drone mission DSL. *)

(** Primitive types in the drone mission language. *)
type prim_type =
  | TInt
  | TFloat
  | TBool
  | TString
  | TUnit

(** Compound types and type variables. *)
type ty =
  | TPrim   of prim_type
  | TList   of ty
  | TTuple  of ty list
  | TArrow  of ty * ty
  | TVar    of string
  | TDrone
  | TWaypoint
  | TMission

(** A type environment maps variable names to types. *)
type type_env = (string * ty) list

(** Type error description. *)
type type_error =
  | UnboundVar of string
  | TypeMismatch of ty * ty
  | ArityMismatch of int * int
  | InvalidOperation of string

(** Result type for type checking. *)
type check_result =
  | Ok    of ty
  | Error of type_error

(** Pretty-print a type to string. *)
let rec string_of_ty = function
  | TPrim TInt    -> "Int"
  | TPrim TFloat  -> "Float"
  | TPrim TBool   -> "Bool"
  | TPrim TString -> "String"
  | TPrim TUnit   -> "Unit"
  | TList t       -> "List[" ^ string_of_ty t ^ "]"
  | TTuple ts     -> "(" ^ String.concat " * " (List.map string_of_ty ts) ^ ")"
  | TArrow (a, b) -> string_of_ty a ^ " -> " ^ string_of_ty b
  | TVar v        -> "'" ^ v
  | TDrone        -> "Drone"
  | TWaypoint     -> "Waypoint"
  | TMission      -> "Mission"

(** Look up a variable in a type environment. *)
let lookup env name =
  match List.assoc_opt name env with
  | Some ty -> Ok ty
  | None    -> Error (UnboundVar name)

(** Check that two types unify (simple equality for now). *)
let unify t1 t2 =
  if t1 = t2 then Ok t1
  else Error (TypeMismatch (t1, t2))

(** Built-in type signatures for drone operations. *)
let builtins : type_env = [
  ("move_to",    TArrow (TDrone,   TArrow (TWaypoint, TUnit)));
  ("hover",      TArrow (TDrone,   TArrow (TPrim TFloat, TUnit)));
  ("land",       TArrow (TDrone,   TUnit));
  ("takeoff",    TArrow (TDrone,   TArrow (TPrim TFloat, TUnit)));
  ("get_battery", TArrow (TDrone,  TPrim TFloat));
  ("get_pos",    TArrow (TDrone,   TTuple [TPrim TFloat; TPrim TFloat; TPrim TFloat]));
  ("mk_waypoint", TArrow (TPrim TFloat, TArrow (TPrim TFloat, TArrow (TPrim TFloat, TWaypoint))));
  ("mk_mission", TArrow (TList TMission, TMission));
]

(** Drone mission expression AST. *)
type expr =
  | Var    of string
  | Lit    of ty * string   (* type and literal value *)
  | App    of expr * expr
  | Let    of string * expr * expr
  | Seq    of expr list
  | If     of expr * expr * expr

(** Infer the type of an expression given an environment. *)
let rec infer (env : type_env) = function
  | Var name ->
    (match List.assoc_opt name (env @ builtins) with
     | Some t -> Ok t
     | None   -> Error (UnboundVar name))
  | Lit (t, _) -> Ok t
  | App (f, arg) ->
    (match infer env f, infer env arg with
     | Ok (TArrow (param_ty, ret_ty)), Ok arg_ty ->
       (match unify param_ty arg_ty with
        | Ok _  -> Ok ret_ty
        | Error e -> Error e)
     | Ok t, _ -> Error (InvalidOperation ("Not a function: " ^ string_of_ty t))
     | Error e, _ -> Error e)
  | Let (name, rhs, body) ->
    (match infer env rhs with
     | Ok t  -> infer ((name, t) :: env) body
     | Error e -> Error e)
  | Seq []    -> Ok (TPrim TUnit)
  | Seq exprs -> List.fold_left (fun _ e -> infer env e) (Ok (TPrim TUnit)) exprs
  | If (cond, thn, els) ->
    (match infer env cond with
     | Ok (TPrim TBool) ->
       (match infer env thn, infer env els with
        | Ok t1, Ok t2 -> unify t1 t2
        | Error e, _ | _, Error e -> Error e)
     | Ok t -> Error (TypeMismatch (TPrim TBool, t))
     | Error e -> Error e)

(** Run the type checker and print results. Phase 650 marker. *)
let () =
  Printf.printf "Phase 650: Type Checker — 드론 미션 타입 검사기\n";

  let sample_env = [("d0", TDrone); ("wp1", TWaypoint)] in
  let test_cases = [
    ("move_to d0",         App (Var "move_to", Var "d0"));
    ("get_battery d0",     App (Var "get_battery", Var "d0"));
    ("unbound var",        Var "undefined_var");
    ("let x = 1.0 in x",  Let ("x", Lit (TPrim TFloat, "1.0"), Var "x"));
  ] in

  List.iter (fun (name, expr) ->
    match infer sample_env expr with
    | Ok ty    -> Printf.printf "  [OK]    %s : %s\n" name (string_of_ty ty)
    | Error (UnboundVar v)     -> Printf.printf "  [ERR]   %s : unbound '%s'\n" name v
    | Error (TypeMismatch(a,b)) -> Printf.printf "  [ERR]   %s : type mismatch %s vs %s\n" name (string_of_ty a) (string_of_ty b)
    | Error (InvalidOperation s) -> Printf.printf "  [ERR]   %s : %s\n" name s
    | Error (ArityMismatch(e,g)) -> Printf.printf "  [ERR]   %s : arity expected %d got %d\n" name e g
  ) test_cases

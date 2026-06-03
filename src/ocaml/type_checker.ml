(** Phase 650: Type Checker — OCaml
    SDACS static type analysis for drone mission script validation *)

(** Primitive types in the mission scripting language *)
type prim_type =
  | TInt
  | TFloat
  | TBool
  | TString
  | TUnit

(** Compound types *)
type drone_type =
  | TPrim    of prim_type
  | TList    of drone_type
  | TTuple   of drone_type list
  | TFun     of drone_type list * drone_type
  | TRecord  of (string * drone_type) list
  | TVar     of string

(** Type environment *)
type type_env = (string * drone_type) list

(** Type error *)
type type_error =
  | UnboundVar   of string
  | TypeMismatch of drone_type * drone_type
  | ArityError   of int * int
  | NotCallable  of drone_type

exception TypeError of type_error

(** Pretty-print a type *)
let rec pp_type = function
  | TPrim TInt    -> "Int"
  | TPrim TFloat  -> "Float"
  | TPrim TBool   -> "Bool"
  | TPrim TString -> "String"
  | TPrim TUnit   -> "Unit"
  | TList t       -> Printf.sprintf "List[%s]" (pp_type t)
  | TTuple ts     -> Printf.sprintf "(%s)" (String.concat " * " (List.map pp_type ts))
  | TFun (args, ret) ->
      Printf.sprintf "(%s) -> %s"
        (String.concat ", " (List.map pp_type args)) (pp_type ret)
  | TRecord fields ->
      Printf.sprintf "{%s}" (String.concat "; "
        (List.map (fun (n, t) -> Printf.sprintf "%s: %s" n (pp_type t)) fields))
  | TVar v        -> Printf.sprintf "'%s" v

(** Check if two types are compatible *)
let rec types_equal t1 t2 = match t1, t2 with
  | TPrim p1, TPrim p2      -> p1 = p2
  | TList a,  TList b       -> types_equal a b
  | TTuple l1, TTuple l2    ->
      List.length l1 = List.length l2 && List.for_all2 types_equal l1 l2
  | TFun (a1, r1), TFun (a2, r2) ->
      List.length a1 = List.length a2 &&
      List.for_all2 types_equal a1 a2 && types_equal r1 r2
  | TVar v1, TVar v2        -> v1 = v2
  | _,        _             -> false

(** Look up a variable in the type environment *)
let env_lookup env name =
  match List.assoc_opt name env with
  | Some t -> t
  | None   -> raise (TypeError (UnboundVar name))

(** Assert two types match or raise *)
let unify t1 t2 =
  if not (types_equal t1 t2) then
    raise (TypeError (TypeMismatch (t1, t2)))

(** Built-in drone API type environment *)
let builtin_env : type_env = [
  ("takeoff",    TFun ([TPrim TFloat], TPrim TUnit));
  ("land",       TFun ([],            TPrim TUnit));
  ("goto",       TFun ([TPrim TFloat; TPrim TFloat; TPrim TFloat], TPrim TUnit));
  ("rtl",        TFun ([],            TPrim TUnit));
  ("battery",    TFun ([],            TPrim TFloat));
  ("altitude",   TFun ([],            TPrim TFloat));
  ("speed",      TFun ([],            TPrim TFloat));
  ("set_speed",  TFun ([TPrim TFloat], TPrim TUnit));
  ("sleep",      TFun ([TPrim TFloat], TPrim TUnit));
  ("log",        TFun ([TPrim TString], TPrim TUnit));
  ("min_sep",    TPrim TFloat);
  ("max_alt",    TPrim TFloat);
  ("drone_id",   TPrim TString);
]

(** Simple expression AST *)
type expr =
  | Lit_int   of int
  | Lit_float of float
  | Lit_bool  of bool
  | Lit_str   of string
  | Var       of string
  | Call      of string * expr list
  | If        of expr * expr * expr
  | Let       of string * expr * expr

(** Type-check an expression *)
let rec type_of env = function
  | Lit_int _   -> TPrim TInt
  | Lit_float _ -> TPrim TFloat
  | Lit_bool _  -> TPrim TBool
  | Lit_str _   -> TPrim TString
  | Var name    -> env_lookup env name
  | Call (fn_name, args) ->
      let fn_type = env_lookup env fn_name in
      (match fn_type with
       | TFun (param_types, ret_type) ->
           if List.length param_types <> List.length args then
             raise (TypeError (ArityError (List.length param_types, List.length args)));
           List.iter2 (fun pt arg ->
             unify pt (type_of env arg)
           ) param_types args;
           ret_type
       | t -> raise (TypeError (NotCallable t)))
  | If (cond, then_e, else_e) ->
      unify (TPrim TBool) (type_of env cond);
      let t_then = type_of env then_e in
      let t_else = type_of env else_e in
      unify t_then t_else;
      t_then
  | Let (name, value_e, body_e) ->
      let vt = type_of env value_e in
      type_of ((name, vt) :: env) body_e

(** Check a list of expressions against expected types *)
let check_program env exprs =
  List.map (fun e ->
    try Ok (type_of env e)
    with TypeError err ->
      Error (match err with
        | UnboundVar v     -> Printf.sprintf "Unbound variable: %s" v
        | TypeMismatch (e,g) -> Printf.sprintf "Type mismatch: expected %s, got %s"
                                  (pp_type e) (pp_type g)
        | ArityError (e,g) -> Printf.sprintf "Arity error: expected %d args, got %d" e g
        | NotCallable t    -> Printf.sprintf "Not callable: %s" (pp_type t))
  ) exprs

let () =
  Printf.printf "Phase 650: OCaml Type Checker\n";
  let env = builtin_env in
  let program = [
    Call ("takeoff", [Lit_float 60.0]);
    Call ("set_speed", [Lit_float 10.0]);
    Var "battery";
  ] in
  let results = check_program env program in
  List.iteri (fun i r ->
    match r with
    | Ok t    -> Printf.printf "  expr[%d]: %s\n" i (pp_type t)
    | Error m -> Printf.printf "  expr[%d] ERROR: %s\n" i m
  ) results

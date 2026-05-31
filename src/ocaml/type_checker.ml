(* type_checker.ml - Type checker for SDACS drone protocol messages *)
(* OCaml implementation of type-safe message validation *)

type base_type = TInt | TFloat | TString | TBool | TUnit

type drone_type =
  | TBase of base_type
  | TList of drone_type
  | TOption of drone_type
  | TPair of drone_type * drone_type
  | TRecord of (string * drone_type) list
  | TFun of drone_type * drone_type

type type_error =
  | TypeMismatch of { expected: drone_type; got: drone_type }
  | UnboundVariable of string
  | ArityError of { expected: int; got: int }

type type_result = Ok of drone_type | Err of type_error

(* Type environment *)
module TypeEnv = Map.Make(String)
type env = drone_type TypeEnv.t

(* Type checking expressions *)
type expr =
  | Lit_int of int
  | Lit_float of float
  | Lit_str of string
  | Lit_bool of bool
  | Var of string
  | App of expr * expr
  | Lam of string * drone_type * expr
  | Let of string * expr * expr
  | If of expr * expr * expr

let rec check_type (env : env) (e : expr) : type_result =
  match e with
  | Lit_int _   -> Ok (TBase TInt)
  | Lit_float _ -> Ok (TBase TFloat)
  | Lit_str _   -> Ok (TBase TString)
  | Lit_bool _  -> Ok (TBase TBool)
  | Var x ->
    (match TypeEnv.find_opt x env with
     | Some t -> Ok t
     | None   -> Err (UnboundVariable x))
  | Lam (x, t, body) ->
    let env' = TypeEnv.add x t env in
    (match check_type env' body with
     | Ok ret_t -> Ok (TFun (t, ret_t))
     | err      -> err)
  | App (f, arg) ->
    (match check_type env f with
     | Ok (TFun (param_t, ret_t)) ->
       (match check_type env arg with
        | Ok arg_t when arg_t = param_t -> Ok ret_t
        | Ok arg_t -> Err (TypeMismatch { expected = param_t; got = arg_t })
        | err -> err)
     | Ok t  -> Err (TypeMismatch { expected = TFun (TBase TUnit, TBase TUnit); got = t })
     | err   -> err)
  | Let (x, e1, e2) ->
    (match check_type env e1 with
     | Ok t   -> check_type (TypeEnv.add x t env) e2
     | err    -> err)
  | If (cond, then_, else_) ->
    (match check_type env cond with
     | Ok (TBase TBool) ->
       (match check_type env then_, check_type env else_ with
        | Ok t1, Ok t2 when t1 = t2 -> Ok t1
        | Ok t1, Ok t2 ->
          Err (TypeMismatch { expected = t1; got = t2 })
        | Err e, _ | _, Err e -> Err e)
     | Ok t -> Err (TypeMismatch { expected = TBase TBool; got = t })
     | err  -> err)

let type_check_message (fields : (string * expr) list) : (string * type_result) list =
  List.map (fun (name, expr) -> (name, check_type TypeEnv.empty expr)) fields

let type_name = function
  | TBase TInt   -> "int"
  | TBase TFloat -> "float"
  | TBase TString -> "string"
  | TBase TBool  -> "bool"
  | TBase TUnit  -> "unit"
  | TList inner  -> Printf.sprintf "list(%s)" (type_name inner)
  | TOption inner -> Printf.sprintf "option(%s)" (type_name inner)
  | TFun (a, b)  -> Printf.sprintf "%s -> %s" (type_name a) (type_name b)
  | _            -> "complex"

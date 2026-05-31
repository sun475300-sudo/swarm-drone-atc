(* P660: Type Checker - OCaml stub *)
(* Type inference and checking for SDACS configuration DSL *)

type ty =
  | TInt
  | TFloat
  | TBool
  | TString
  | TList of ty
  | TOption of ty
  | TFun of ty * ty
  | TVar of string

type expr =
  | EInt of int
  | EFloat of float
  | EBool of bool
  | EString of string
  | EVar of string
  | EApp of expr * expr
  | ELam of string * ty option * expr
  | ELet of string * expr * expr
  | EIf of expr * expr * expr
  | EList of expr list

type type_error =
  | UnboundVariable of string
  | TypeMismatch of ty * ty
  | NotAFunction of ty
  | InferenceFailed of string

exception TypeError of type_error

module Env = Map.Make(String)

type env = ty Env.t

let rec type_of (env : env) (e : expr) : ty =
  match e with
  | EInt _    -> TInt
  | EFloat _  -> TFloat
  | EBool _   -> TBool
  | EString _ -> TString
  | EVar x ->
    (match Env.find_opt x env with
     | Some t -> t
     | None   -> raise (TypeError (UnboundVariable x)))
  | ELet (x, e1, e2) ->
    let t1 = type_of env e1 in
    type_of (Env.add x t1 env) e2
  | EIf (cond, then_e, else_e) ->
    let tc = type_of env cond in
    if tc <> TBool then raise (TypeError (TypeMismatch (TBool, tc)));
    let tt = type_of env then_e in
    let te = type_of env else_e in
    if tt <> te then raise (TypeError (TypeMismatch (tt, te)));
    tt
  | EList [] -> TList (TVar "a")
  | EList (hd :: tl) ->
    let t = type_of env hd in
    List.iter (fun e ->
      let te = type_of env e in
      if te <> t then raise (TypeError (TypeMismatch (t, te)))
    ) tl;
    TList t
  | EApp (f, arg) ->
    (match type_of env f with
     | TFun (param_t, ret_t) ->
       let arg_t = type_of env arg in
       if arg_t <> param_t then raise (TypeError (TypeMismatch (param_t, arg_t)));
       ret_t
     | t -> raise (TypeError (NotAFunction t)))
  | ELam (x, ann, body) ->
    let param_t = match ann with Some t -> t | None -> TVar x in
    let ret_t = type_of (Env.add x param_t env) body in
    TFun (param_t, ret_t)

let check (e : expr) : (ty, type_error) result =
  try Ok (type_of Env.empty e)
  with TypeError err -> Error err

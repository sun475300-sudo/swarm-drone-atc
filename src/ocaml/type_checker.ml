(* Phase 660 — Type Checker (OCaml)
   드론 임무 명령 DSL을 위한 간이 타입 검사기 *)

(** 명령 DSL의 타입 *)
type ty =
  | TInt
  | TFloat
  | TBool
  | TString
  | TPos3D
  | TList  of ty
  | TFun   of ty * ty
  | TUnit

(** DSL 표현식 *)
type expr =
  | EInt    of int
  | EFloat  of float
  | EBool   of bool
  | EString of string
  | EVar    of string
  | EApp    of expr * expr
  | ELet    of string * expr * expr
  | EIf     of expr * expr * expr
  | EList   of expr list

(** 타입 환경 *)
type env = (string * ty) list

exception TypeError of string

let lookup env x =
  match List.assoc_opt x env with
  | Some t -> t
  | None   -> raise (TypeError (Printf.sprintf "Unbound variable: %s" x))

(** 타입 추론 (단형 Hindley-Milner 부분집합) *)
let rec infer env = function
  | EInt    _ -> TInt
  | EFloat  _ -> TFloat
  | EBool   _ -> TBool
  | EString _ -> TString
  | EVar x    -> lookup env x
  | EList []  -> TList TUnit
  | EList (h :: t) ->
    let th = infer env h in
    List.iter (fun e ->
      let te = infer env e in
      if te <> th then raise (TypeError "Heterogeneous list")
    ) t;
    TList th
  | ELet (x, e1, e2) ->
    let t1 = infer env e1 in
    infer ((x, t1) :: env) e2
  | EIf (cond, e_then, e_else) ->
    (match infer env cond with
     | TBool -> ()
     | t     -> raise (TypeError (Printf.sprintf "If condition must be Bool, got %s" (show_ty t))));
    let tt = infer env e_then in
    let te = infer env e_else in
    if tt <> te then raise (TypeError "If branches have different types");
    tt
  | EApp (f, arg) ->
    (match infer env f with
     | TFun (param_t, ret_t) ->
       let arg_t = infer env arg in
       if arg_t <> param_t then
         raise (TypeError (Printf.sprintf "Argument type mismatch: expected %s, got %s"
                             (show_ty param_t) (show_ty arg_t)));
       ret_t
     | t -> raise (TypeError (Printf.sprintf "Expected function type, got %s" (show_ty t))))

and show_ty = function
  | TInt      -> "Int"
  | TFloat    -> "Float"
  | TBool     -> "Bool"
  | TString   -> "String"
  | TPos3D    -> "Pos3D"
  | TList t   -> Printf.sprintf "List[%s]" (show_ty t)
  | TFun(a,b) -> Printf.sprintf "%s -> %s" (show_ty a) (show_ty b)
  | TUnit     -> "Unit"

(** 표현식을 타입 검사하고 결과를 반환한다. *)
let type_check expr =
  let builtins = [
    ("goto",    TFun (TPos3D,  TUnit));
    ("hover",   TFun (TFloat,  TUnit));
    ("land",    TFun (TUnit,   TUnit));
  ] in
  try
    let t = infer builtins expr in
    Ok t
  with TypeError msg -> Error msg

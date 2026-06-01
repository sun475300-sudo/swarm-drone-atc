(* Type checker stub for SDACS configuration DSL — OCaml *)

type sdacs_type =
  | TInt
  | TFloat
  | TString
  | TBool
  | TList of sdacs_type
  | TRecord of (string * sdacs_type) list

type value =
  | VInt of int
  | VFloat of float
  | VString of string
  | VBool of bool
  | VList of value list
  | VRecord of (string * value) list

let rec type_of = function
  | VInt _    -> TInt
  | VFloat _  -> TFloat
  | VString _ -> TString
  | VBool _   -> TBool
  | VList []  -> TList TString
  | VList (h :: _) -> TList (type_of h)
  | VRecord fields -> TRecord (List.map (fun (k, v) -> (k, type_of v)) fields)

let check expected actual =
  if expected = type_of actual then Ok actual
  else Error (Printf.sprintf "type mismatch: expected %s" (match expected with TInt -> "int" | TFloat -> "float" | _ -> "other"))

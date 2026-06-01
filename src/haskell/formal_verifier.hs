-- Formal Verifier — Haskell stub for Phase 615
-- Haskell module for formal property verification of swarm drone behavior.

module FormalVerifier where

import Data.List (nub, sort, intercalate)
import Data.Maybe (mapMaybe, catMaybes)

-- ===== Property Types =====

-- | A propositional formula for safety/liveness properties
data Formula
    = Atom String
    | Not Formula
    | And Formula Formula
    | Or  Formula Formula
    | Implies Formula Formula
    | Always Formula        -- G (globally)
    | Eventually Formula    -- F (finally/eventually)
    | Next Formula          -- X (next state)
    | Until Formula Formula -- U (until)
    deriving (Show, Eq)

-- | A system state snapshot
data SystemState = SystemState
    { stateId     :: Int
    , predicates  :: [String]   -- true predicates in this state
    , successors  :: [Int]      -- valid next states
    } deriving (Show, Eq)

-- | A transition system (Kripke structure)
data TransitionSystem = TransitionSystem
    { states      :: [SystemState]
    , initial     :: [Int]
    } deriving (Show)

-- | Verification outcome
data VerifyResult
    = Satisfied String
    | Violated  String String  -- formula, counterexample
    | Unknown   String
    deriving (Show, Eq)

-- ===== Formula Helpers =====

-- | Check if a predicate holds in a given state
holdsPred :: String -> SystemState -> Bool
holdsPred p s = p `elem` predicates s

-- | Evaluate an atomic formula in a state
evalAtom :: String -> SystemState -> Bool
evalAtom = holdsPred

-- | Pretty-print a formula
showFormula :: Formula -> String
showFormula (Atom p)        = p
showFormula (Not f)         = "¬(" ++ showFormula f ++ ")"
showFormula (And f1 f2)     = "(" ++ showFormula f1 ++ " ∧ " ++ showFormula f2 ++ ")"
showFormula (Or  f1 f2)     = "(" ++ showFormula f1 ++ " ∨ " ++ showFormula f2 ++ ")"
showFormula (Implies f1 f2) = "(" ++ showFormula f1 ++ " → " ++ showFormula f2 ++ ")"
showFormula (Always f)      = "G(" ++ showFormula f ++ ")"
showFormula (Eventually f)  = "F(" ++ showFormula f ++ ")"
showFormula (Next f)        = "X(" ++ showFormula f ++ ")"
showFormula (Until f1 f2)   = "(" ++ showFormula f1 ++ " U " ++ showFormula f2 ++ ")"

-- ===== Bounded Model Checker =====

-- | Bounded model checking up to depth k
type StateMap = [(Int, SystemState)]

lookupState :: Int -> StateMap -> Maybe SystemState
lookupState i sm = lookup i sm

-- | Evaluate a formula at a state with bounded depth
evalFormula :: Formula -> SystemState -> StateMap -> Int -> Bool
evalFormula (Atom p) s _ _ = holdsPred p s
evalFormula (Not f) s sm k = not (evalFormula f s sm k)
evalFormula (And f1 f2) s sm k = evalFormula f1 s sm k && evalFormula f2 s sm k
evalFormula (Or f1 f2) s sm k = evalFormula f1 s sm k || evalFormula f2 s sm k
evalFormula (Implies f1 f2) s sm k = not (evalFormula f1 s sm k) || evalFormula f2 s sm k
evalFormula (Always f) s sm 0 = evalFormula f s sm 0
evalFormula (Always f) s sm k =
    evalFormula f s sm k &&
    all (\sid -> maybe False (\ns -> evalFormula (Always f) ns sm (k-1)) (lookupState sid sm))
        (successors s)
evalFormula (Eventually f) s sm 0 = evalFormula f s sm 0
evalFormula (Eventually f) s sm k =
    evalFormula f s sm k ||
    any (\sid -> maybe False (\ns -> evalFormula (Eventually f) ns sm (k-1)) (lookupState sid sm))
        (successors s)
evalFormula (Next f) s sm k =
    case successors s of
        []    -> False
        (i:_) -> maybe False (\ns -> evalFormula f ns sm (max 0 (k-1))) (lookupState i sm)
evalFormula (Until f1 f2) s sm 0 = evalFormula f2 s sm 0
evalFormula (Until f1 f2) s sm k =
    evalFormula f2 s sm k ||
    (evalFormula f1 s sm k &&
     any (\sid -> maybe False (\ns -> evalFormula (Until f1 f2) ns sm (k-1)) (lookupState sid sm))
         (successors s))

-- ===== Formal Verifier =====

-- | Verify a formula against a transition system
verify :: TransitionSystem -> Formula -> Int -> VerifyResult
verify ts formula depth =
    let sm = map (\s -> (stateId s, s)) (states ts)
        initStates = mapMaybe (`lookup` sm) (initial ts)
        results = map (\s -> evalFormula formula s sm depth) initStates
    in if all id results
       then Satisfied (showFormula formula)
       else Violated  (showFormula formula) "Counterexample: initial state violation"

-- | Run a batch of safety checks
verifyBatch :: TransitionSystem -> [(String, Formula)] -> Int -> [(String, VerifyResult)]
verifyBatch ts props depth = map (\(name, f) -> (name, verify ts f depth)) props

-- ===== Example Drone System =====

buildDroneSystem :: TransitionSystem
buildDroneSystem = TransitionSystem
    { states =
        [ SystemState 0 ["idle", "safe", "battery_ok"] [1, 2]
        , SystemState 1 ["flying", "safe", "battery_ok"] [2, 3]
        , SystemState 2 ["flying", "safe", "low_battery"] [3]
        , SystemState 3 ["landing", "safe", "battery_ok"] [0]
        ]
    , initial = [0]
    }

droneProperties :: [(String, Formula)]
droneProperties =
    [ ("Safety: always safe", Always (Atom "safe"))
    , ("Liveness: eventually lands", Eventually (Atom "landing"))
    , ("Battery: safe implies battery checked",
       Always (Implies (Atom "flying") (Or (Atom "battery_ok") (Atom "low_battery"))))
    , ("Reachability: idle state reachable", Eventually (Atom "idle"))
    ]

-- ===== Main =====

main :: IO ()
main = do
    putStrLn "Phase 615: Formal Verifier — Drone Safety Properties"
    let ts = buildDroneSystem
    putStrLn $ "States: " ++ show (length (states ts))
    putStrLn $ "Initial states: " ++ show (initial ts)
    putStrLn ""
    let results = verifyBatch ts droneProperties 10
    mapM_ (\(name, res) -> do
        let outcome = case res of
                Satisfied _ -> "PASS"
                Violated _ ce -> "FAIL (" ++ ce ++ ")"
                Unknown _ -> "UNKNOWN"
        putStrLn $ "  [" ++ outcome ++ "] " ++ name
    ) results
    let passed = length [ () | (_, Satisfied _) <- results ]
    putStrLn $ "\nResult: " ++ show passed ++ "/" ++ show (length results) ++ " properties verified"

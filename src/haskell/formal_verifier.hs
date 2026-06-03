-- Phase 615: Formal Verifier — Haskell
-- SDACS LTL (Linear Temporal Logic) property verification for drone missions

module FormalVerifier
  ( LTL(..)
  , State(..)
  , Trace
  , verify
  , checkSafety
  , checkLiveness
  ) where

data State = State
  { stDroneId  :: String
  , stAlt      :: Double
  , stBattery  :: Double
  , stMode     :: String
  , stTick     :: Int
  } deriving (Show, Eq)

data LTL a
  = Atom     (a -> Bool)
  | Not      (LTL a)
  | And      (LTL a) (LTL a)
  | Or       (LTL a) (LTL a)
  | Always   (LTL a)
  | Eventually (LTL a)
  | Next     (LTL a)
  | Until    (LTL a) (LTL a)

type Trace a = [a]

verify :: LTL a -> Trace a -> Bool
verify (Atom p)        (x:_)  = p x
verify (Not f)         tr     = not (verify f tr)
verify (And f g)       tr     = verify f tr && verify g tr
verify (Or f g)        tr     = verify f tr || verify g tr
verify (Always f)      []     = True
verify (Always f)      tr@(_:rest) = verify f tr && verify (Always f) rest
verify (Eventually f)  []     = False
verify (Eventually f)  tr@(_:rest) = verify f tr || verify (Eventually f) rest
verify (Next f)        (_:rest)    = verify f rest
verify (Next _)        []          = False
verify (Until f g)     []          = False
verify (Until f g)     tr@(_:rest) = verify g tr || (verify f tr && verify (Until f g) rest)
verify _ []                        = True

checkSafety :: Trace State -> [(String, Bool)]
checkSafety trace =
  [ ("altitude_safe",  verify (Always (Atom (\s -> stAlt s <= 120.0))) trace)
  , ("battery_ok",     verify (Always (Atom (\s -> stBattery s >= 0.0))) trace)
  , ("no_crash",       verify (Always (Atom (\s -> stAlt s >= 0.0))) trace)
  ]

checkLiveness :: Trace State -> [(String, Bool)]
checkLiveness trace =
  [ ("eventually_land", verify (Eventually (Atom (\s -> stMode s == "idle"))) trace)
  , ("battery_drains",  verify (Eventually (Atom (\s -> stBattery s < 50.0))) trace)
  ]

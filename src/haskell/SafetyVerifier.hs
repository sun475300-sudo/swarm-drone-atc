-- Phase 552: Safety Verifier — 드론 안전 검증기 (Haskell)
-- Monadic safety property verification for swarm drone operations.
module SafetyVerifier
  ( DroneState(..)
  , SafetyError(..)
  , SafetyResult
  , SafetyCheck
  , verifySafety
  , verifyAltitude
  , verifyBattery
  , verifyVelocity
  , verifySeparation
  , runChecks
  ) where

import Data.List (minimumBy)
import Data.Ord  (comparing)

-- Phase marker: 552

-- ── Data types ─────────────────────────────────────────────────────

data DroneState = DroneState
  { droneId   :: Int
  , posX      :: Double
  , posY      :: Double
  , posZ      :: Double
  , velocity  :: Double
  , battery   :: Double
  } deriving (Show, Eq)

data SafetyError
  = AltitudeTooLow    Int Double
  | BatteryCritical   Int Double
  | VelocityExceeded  Int Double
  | SeparationViolation Int Int Double
  deriving (Show, Eq)

-- ── Monadic result type ────────────────────────────────────────────

-- SafetyResult uses Either monad: Left = error, Right = validated state.
type SafetyResult a = Either SafetyError a

-- SafetyCheck is a function from DroneState to SafetyResult
type SafetyCheck = DroneState -> SafetyResult DroneState

-- ── Safety thresholds ──────────────────────────────────────────────

minAltitude  :: Double
minAltitude  = 10.0

criticalBat  :: Double
criticalBat  = 10.0

maxVelocity  :: Double
maxVelocity  = 30.0

minSeparation :: Double
minSeparation = 5.0

-- ── Individual checks ─────────────────────────────────────────────

verifyAltitude :: SafetyCheck
verifyAltitude d
  | posZ d < minAltitude = Left (AltitudeTooLow (droneId d) (posZ d))
  | otherwise            = Right d

verifyBattery :: SafetyCheck
verifyBattery d
  | battery d < criticalBat = Left (BatteryCritical (droneId d) (battery d))
  | otherwise               = Right d

verifyVelocity :: SafetyCheck
verifyVelocity d
  | velocity d > maxVelocity = Left (VelocityExceeded (droneId d) (velocity d))
  | otherwise                = Right d

-- ── Chained verification (monadic bind) ───────────────────────────

verifySafety :: DroneState -> SafetyResult DroneState
verifySafety d =
  verifyAltitude d >>= verifyBattery >>= verifyVelocity

-- ── Fleet separation check ─────────────────────────────────────────

distance3D :: DroneState -> DroneState -> Double
distance3D a b =
  let dx = posX a - posX b
      dy = posY a - posY b
      dz = posZ a - posZ b
  in sqrt (dx*dx + dy*dy + dz*dz)

verifySeparation :: [DroneState] -> Maybe SafetyError
verifySeparation drones =
  let pairs = [(a,b) | (i,a) <- zip [0..] drones
                      , (j,b) <- zip [0..] drones
                      , i < j]
      violations = filter (\(a,b) -> distance3D a b < minSeparation) pairs
  in case violations of
       []       -> Nothing
       ((a,b):_) -> Just (SeparationViolation (droneId a) (droneId b) (distance3D a b))

-- ── Batch verification ─────────────────────────────────────────────

runChecks :: [DroneState] -> ([SafetyError], [DroneState])
runChecks drones =
  let results = map verifySafety drones
      errors  = [e | Left e  <- results]
      safes   = [d | Right d <- results]
  in (errors, safes)

-- ── Demo ───────────────────────────────────────────────────────────

main :: IO ()
main = do
  putStrLn "Phase 552: Safety Verifier — 드론 안전 검증기 (Haskell)"
  let fleet =
        [ DroneState 0 0.0   0.0   50.0 10.0 80.0
        , DroneState 1 50.0  50.0  55.0  8.0 75.0
        , DroneState 2 5.0   5.0    5.0 35.0  8.0  -- altitude + vel + battery fail
        , DroneState 3 100.0 100.0 60.0 12.0 50.0
        ]
  let (errs, safes) = runChecks fleet
  putStrLn $ "Safe drones: " ++ show (length safes)
  putStrLn $ "Violations:  " ++ show (length errs)
  mapM_ print errs
  case verifySeparation fleet of
    Nothing  -> putStrLn "No separation violations."
    Just err -> print err

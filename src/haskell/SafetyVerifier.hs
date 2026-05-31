-- SafetyVerifier.hs - Safety verification for SDACS (Phase 552)
-- Haskell monadic safety checks using Either monad

module SafetyVerifier where

import Data.List (nub, sortBy, minimumBy)
import Data.Ord (comparing)

-- Safety violation type
data SafetyViolation
    = AltitudeViolation String Double
    | SeparationViolation String String Double
    | BatteryViolation String Int
    | BoundaryViolation String
    deriving (Show, Eq)

-- Drone state
data Drone = Drone
    { droneId  :: String
    , posX     :: Double
    , posY     :: Double
    , posZ     :: Double
    , battery  :: Int
    , status   :: String
    } deriving (Show)

-- Safety check using Either monad
type SafetyResult a = Either SafetyViolation a

-- Check altitude constraint
checkAltitude :: Drone -> SafetyResult Drone
checkAltitude d
    | posZ d > 400.0 = Left  (AltitudeViolation (droneId d) (posZ d))
    | posZ d < 0.0   = Left  (AltitudeViolation (droneId d) (posZ d))
    | otherwise      = Right d

-- Check battery level using Maybe-like logic
checkBattery :: Drone -> SafetyResult Drone
checkBattery d
    | battery d < 5  = Left  (BatteryViolation (droneId d) (battery d))
    | otherwise      = Right d

-- Check boundary constraints
checkBoundary :: Double -> Drone -> SafetyResult Drone
checkBoundary maxCoord d
    | abs (posX d) > maxCoord = Left (BoundaryViolation (droneId d))
    | abs (posY d) > maxCoord = Left (BoundaryViolation (droneId d))
    | otherwise               = Right d

-- Compose safety checks
safetyCheck :: Drone -> SafetyResult Drone
safetyCheck d = checkAltitude d >>= checkBattery >>= checkBoundary 50000.0

-- Run all checks and collect results
runAllChecks :: [Drone] -> ([Drone], [SafetyViolation])
runAllChecks drones =
    let results = map safetyCheck drones
        safe    = [d | Right d <- results]
        violations = [v | Left v <- results]
    in (safe, violations)

-- Compute distance between two drones
distance3d :: Drone -> Drone -> Double
distance3d a b =
    let dx = posX a - posX b
        dy = posY a - posY b
        dz = posZ a - posZ b
    in sqrt (dx*dx + dy*dy + dz*dz)

-- Check separation between all drone pairs
checkSeparation :: Double -> [Drone] -> [SafetyViolation]
checkSeparation minSep drones =
    [ SeparationViolation (droneId a) (droneId b) d
    | a <- drones
    , b <- drones
    , droneId a < droneId b
    , let d = distance3d a b
    , d < minSep
    ]

-- Full safety audit
safetyAudit :: [Drone] -> Either [SafetyViolation] [Drone]
safetyAudit drones =
    let (safe, violations) = runAllChecks drones
        sepViolations = checkSeparation 30.0 safe
        allViolations = violations ++ sepViolations
    in if null allViolations
       then Right safe
       else Left allViolations

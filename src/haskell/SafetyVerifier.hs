-- Phase 552 — Safety Verifier with Monadic Error Handling
-- Haskell module for formal safety property verification in drone swarm systems.

module SafetyVerifier where

import Data.List (nub, sort)
import Data.Maybe (mapMaybe, fromMaybe)

-- ===== Types =====

-- | Safety property categories
data SafetyCategory
    = Collision
    | Geofence
    | BatteryLevel
    | SignalLoss
    | Separation
    deriving (Show, Eq, Ord)

-- | A safety constraint that must hold
data SafetyConstraint = SafetyConstraint
    { constraintId   :: String
    , category       :: SafetyCategory
    , description    :: String
    , threshold      :: Double
    } deriving (Show, Eq)

-- | Drone telemetry snapshot
data DroneTelemetry = DroneTelemetry
    { droneId    :: String
    , posX       :: Double
    , posY       :: Double
    , posZ       :: Double
    , battery    :: Double
    , signalRSSI :: Double
    } deriving (Show, Eq)

-- | Verification result using Either for monadic error handling
data VerificationError
    = ConstraintViolated String String   -- constraintId, details
    | InsufficientData String
    | ConfigurationError String
    deriving (Show, Eq)

-- | Safety property check result
data SafetyResult = SafetyResult
    { checkedConstraint :: String
    , passed            :: Bool
    , details           :: String
    , severity          :: Int   -- 1=info, 2=warning, 3=critical
    } deriving (Show, Eq)

-- ===== Either Monad Utilities =====

-- | Lift a Maybe to Either with an error message
maybeToEither :: e -> Maybe a -> Either e a
maybeToEither err Nothing  = Left err
maybeToEither _   (Just x) = Right x

-- | Run a list of checks, collecting all failures
checkAll :: [Either e a] -> Either [e] [a]
checkAll results =
    let (errs, oks) = foldr collectEither ([], []) results
    in if null errs then Right oks else Left errs
  where
    collectEither (Left e)  (es, as_) = (e : es, as_)
    collectEither (Right a) (es, as_) = (es, a : as_)

-- ===== Safety Constraints =====

defaultConstraints :: [SafetyConstraint]
defaultConstraints =
    [ SafetyConstraint "C001" Separation  "Minimum drone separation" 5.0
    , SafetyConstraint "C002" BatteryLevel "Minimum battery level"  20.0
    , SafetyConstraint "C003" SignalLoss  "Minimum signal strength" (-85.0)
    , SafetyConstraint "C004" Geofence   "Maximum altitude"        120.0
    , SafetyConstraint "C005" Collision   "Collision risk threshold" 2.0
    ]

-- ===== Constraint Checkers =====

-- | Check battery level constraint using Either
checkBattery :: SafetyConstraint -> DroneTelemetry -> Either VerificationError SafetyResult
checkBattery c t
    | battery t < threshold c =
        Left $ ConstraintViolated (constraintId c)
               ("Battery " ++ show (battery t) ++ "% < " ++ show (threshold c) ++ "%")
    | otherwise =
        Right $ SafetyResult (constraintId c) True
                    ("Battery OK: " ++ show (battery t) ++ "%") 1

-- | Check signal strength using Either monad
checkSignal :: SafetyConstraint -> DroneTelemetry -> Either VerificationError SafetyResult
checkSignal c t
    | signalRSSI t < threshold c =
        Left $ ConstraintViolated (constraintId c)
               ("Signal " ++ show (signalRSSI t) ++ " dBm below threshold")
    | otherwise =
        Right $ SafetyResult (constraintId c) True "Signal OK" 1

-- | Check geofence altitude constraint
checkGeofence :: SafetyConstraint -> DroneTelemetry -> Either VerificationError SafetyResult
checkGeofence c t
    | posZ t > threshold c =
        Left $ ConstraintViolated (constraintId c)
               ("Altitude " ++ show (posZ t) ++ "m exceeds " ++ show (threshold c) ++ "m")
    | otherwise =
        Right $ SafetyResult (constraintId c) True "Geofence OK" 1

-- | Compute 3D distance between two telemetry points
droneDistance :: DroneTelemetry -> DroneTelemetry -> Double
droneDistance a b =
    let dx = posX a - posX b
        dy = posY a - posY b
        dz = posZ a - posZ b
    in sqrt (dx*dx + dy*dy + dz*dz)

-- | Check separation between all drone pairs using Either
checkSeparation :: SafetyConstraint -> [DroneTelemetry] -> [Either VerificationError SafetyResult]
checkSeparation c telems =
    [ let dist = droneDistance a b
      in if dist < threshold c
         then Left $ ConstraintViolated (constraintId c)
                ("Drones " ++ droneId a ++ " and " ++ droneId b ++
                 " too close: " ++ show dist ++ "m")
         else Right $ SafetyResult (constraintId c) True
                ("Sep OK: " ++ droneId a ++ "-" ++ droneId b) 1
    | (a, i) <- zip telems [0..], (b, j) <- zip telems [0..], i < j ]

-- ===== Verifier =====

-- | Run all safety checks for a single drone
verifyDrone :: [SafetyConstraint] -> DroneTelemetry -> [Either VerificationError SafetyResult]
verifyDrone constraints telem =
    mapMaybe (\c -> case category c of
        BatteryLevel -> Just $ checkBattery c telem
        SignalLoss   -> Just $ checkSignal c telem
        Geofence     -> Just $ checkGeofence c telem
        _            -> Nothing
    ) constraints

-- | Full swarm safety verification
verifySwarm :: [SafetyConstraint] -> [DroneTelemetry] -> Either [VerificationError] [SafetyResult]
verifySwarm constraints telems =
    let perDrone = concatMap (verifyDrone constraints) telems
        sepConstraints = filter (\c -> category c == Separation) constraints
        sepChecks = concatMap (\c -> checkSeparation c telems) sepConstraints
        allChecks = perDrone ++ sepChecks
    in checkAll allChecks

-- | Safety verification report
data VerificationReport = VerificationReport
    { totalChecks  :: Int
    , passedChecks :: Int
    , violations   :: [VerificationError]
    , isSafe       :: Bool
    } deriving (Show)

-- | Generate full report
generateReport :: [SafetyConstraint] -> [DroneTelemetry] -> VerificationReport
generateReport constraints telems =
    let result = verifySwarm constraints telems
    in case result of
        Right results ->
            VerificationReport (length results) (length results) [] True
        Left errs ->
            VerificationReport 0 0 errs False

-- ===== Main =====

main :: IO ()
main = do
    putStrLn "Phase 552: Safety Verifier with Either/Maybe monadic handling"
    let telems =
            [ DroneTelemetry "D1" 0.0  0.0  50.0 85.0 (-70.0)
            , DroneTelemetry "D2" 10.0 0.0  55.0 15.0 (-80.0)  -- low battery
            , DroneTelemetry "D3" 20.0 0.0  60.0 90.0 (-90.0)  -- weak signal
            ]
    let report = generateReport defaultConstraints telems
    putStrLn $ "Safety check: " ++ (if isSafe report then "PASS" else "FAIL")
    putStrLn $ "Total checks: " ++ show (totalChecks report)
    putStrLn $ "Violations: " ++ show (length (violations report))
    mapM_ (putStrLn . ("  - " ++) . show) (violations report)

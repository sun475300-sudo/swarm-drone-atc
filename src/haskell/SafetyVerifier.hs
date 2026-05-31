-- Phase 552 — Haskell functional Safety verifier
-- Uses Either/Maybe monads for type-safe drone constraint checking

module SafetyVerifier
  ( DroneState(..)
  , Constraint(..)
  , VerificationResult
  , verifyDrone
  , verifySwarm
  , checkAltitudeBounds
  , checkSpeedLimit
  , checkGeofence
  , checkBatteryLevel
  , checkSeparation
  , runAllChecks
  ) where

import Data.List (find, minimumBy)
import Data.Ord  (comparing)

-- ── Domain types ────────────────────────────────────────────────────────────

data DroneState = DroneState
  { droneId      :: String
  , posX         :: Double   -- metres, East
  , posY         :: Double   -- metres, North
  , posZ         :: Double   -- metres, altitude AGL
  , speedMs      :: Double   -- m/s horizontal ground speed
  , batteryPct   :: Double   -- 0–100
  , timestamp    :: Integer  -- Unix millis
  } deriving (Show, Eq)

data Constraint
  = AltitudeMin Double
  | AltitudeMax Double
  | SpeedMax    Double
  | BatteryMin  Double
  | GeofenceRadius Double Double Double  -- centerX, centerY, radiusM
  | SeparationMin Double
  deriving (Show, Eq)

data SafetyViolation
  = BelowMinAltitude  { violDrone :: String, actual :: Double, limit :: Double }
  | AboveMaxAltitude  { violDrone :: String, actual :: Double, limit :: Double }
  | ExceedsSpeedLimit { violDrone :: String, actual :: Double, limit :: Double }
  | LowBattery        { violDrone :: String, actual :: Double, limit :: Double }
  | OutsideGeofence   { violDrone :: String, distM  :: Double, limit :: Double }
  | ProximityViolation{ droneA    :: String, droneB :: String, distM :: Double, limit :: Double }
  deriving (Show, Eq)

-- Either-based: Right = safe, Left = violation list
type VerificationResult = Either [SafetyViolation] ()

-- ── Individual constraint checkers ──────────────────────────────────────────

-- 552: Safety check via Either monad

checkAltitudeBounds :: Double -> Double -> DroneState -> Maybe SafetyViolation
checkAltitudeBounds minAlt maxAlt ds
  | posZ ds < minAlt = Just $ BelowMinAltitude (droneId ds) (posZ ds) minAlt
  | posZ ds > maxAlt = Just $ AboveMaxAltitude (droneId ds) (posZ ds) maxAlt
  | otherwise        = Nothing

checkSpeedLimit :: Double -> DroneState -> Maybe SafetyViolation
checkSpeedLimit maxSpd ds
  | speedMs ds > maxSpd = Just $ ExceedsSpeedLimit (droneId ds) (speedMs ds) maxSpd
  | otherwise            = Nothing

checkBatteryLevel :: Double -> DroneState -> Maybe SafetyViolation
checkBatteryLevel minBat ds
  | batteryPct ds < minBat = Just $ LowBattery (droneId ds) (batteryPct ds) minBat
  | otherwise               = Nothing

checkGeofence :: Double -> Double -> Double -> DroneState -> Maybe SafetyViolation
checkGeofence cx cy radius ds =
  let dx   = posX ds - cx
      dy   = posY ds - cy
      dist = sqrt (dx * dx + dy * dy)
  in if dist > radius
       then Just $ OutsideGeofence (droneId ds) dist radius
       else Nothing

checkSeparation :: Double -> DroneState -> DroneState -> Maybe SafetyViolation
checkSeparation minSep a b =
  let dx   = posX a - posX b
      dy   = posY a - posY b
      dz   = posZ a - posZ b
      dist = sqrt (dx*dx + dy*dy + dz*dz)
  in if dist < minSep
       then Just $ ProximityViolation (droneId a) (droneId b) dist minSep
       else Nothing

-- ── Aggregate verifier ────────────────────────────────────────────────────

applyConstraint :: DroneState -> Constraint -> Maybe SafetyViolation
applyConstraint ds c = case c of
  AltitudeMin lo              -> checkAltitudeBounds lo 9999 ds
  AltitudeMax hi              -> checkAltitudeBounds 0    hi   ds
  SpeedMax    ms              -> checkSpeedLimit ms ds
  BatteryMin  pct             -> checkBatteryLevel pct ds
  GeofenceRadius cx cy r      -> checkGeofence cx cy r ds
  SeparationMin _             -> Nothing   -- handled at swarm level

verifyDrone :: [Constraint] -> DroneState -> VerificationResult
verifyDrone constraints ds =
  let violations = [v | c <- constraints, Just v <- [applyConstraint ds c]]
  in if null violations then Right () else Left violations

verifySwarm :: [Constraint] -> [DroneState] -> VerificationResult
verifySwarm constraints drones =
  let perDrone  = concatMap (\ds -> case verifyDrone constraints ds of
                                      Left vs -> vs
                                      Right _ -> []) drones
      sepMin    = findSepMin constraints
      pairViolations = case sepMin of
        Nothing  -> []
        Just sep -> [ v
                    | (a:rest) <- tails drones
                    , b <- rest
                    , Just v <- [checkSeparation sep a b] ]
      allViolations = perDrone ++ pairViolations
  in if null allViolations then Right () else Left allViolations
  where
    tails []     = []
    tails xs@(_:rest) = xs : tails rest
    findSepMin cs = case [s | SeparationMin s <- cs] of
      [] -> Nothing
      ss -> Just (minimum ss)

runAllChecks :: [Constraint] -> [DroneState] -> IO ()
runAllChecks constraints drones = do
  putStrLn "[552] Safety Verifier — running checks"
  case verifySwarm constraints drones of
    Right () -> putStrLn "[552] All Safety checks PASSED."
    Left vs  -> do
      putStrLn $ "[552] Safety VIOLATIONS detected: " ++ show (length vs)
      mapM_ (putStrLn . ("  - " ++) . show) vs

-- ── Example entry point ──────────────────────────────────────────────────────

exampleConstraints :: [Constraint]
exampleConstraints =
  [ AltitudeMin 5.0
  , AltitudeMax 120.0
  , SpeedMax    15.0
  , BatteryMin  20.0
  , GeofenceRadius 0 0 500
  , SeparationMin  3.0
  ]

exampleDrones :: [DroneState]
exampleDrones =
  [ DroneState "D001" 10.0 20.0  30.0 5.0  85.0 1717200000000
  , DroneState "D002" 10.5 20.3  30.2 4.8  80.0 1717200000000
  , DroneState "D003"  0.0  0.0 130.0 20.0 15.0 1717200000000  -- violates altitude+speed+battery
  ]

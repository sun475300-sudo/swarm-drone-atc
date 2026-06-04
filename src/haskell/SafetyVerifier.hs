-- Phase 552: Safety Verifier — Haskell
-- SDACS formal safety property verification using Either/Maybe monad chains

module SafetyVerifier
  ( DroneState(..)
  , SafetyProperty(..)
  , SafetyResult(..)
  , verifyAll
  , verifyState
  , altitudeProperty
  , batteryProperty
  , separationProperty
  , speedProperty
  , geofenceProperty
  ) where

-- Phase 552 marker — Safety verification with Either/Maybe monadic composition

import Data.List (intercalate)

-- ============================================================
-- Domain types

data DroneState = DroneState
  { droneId    :: String
  , latitude   :: Double
  , longitude  :: Double
  , altitude   :: Double
  , speed      :: Double
  , battery    :: Double
  , mode       :: String
  , heading    :: Double
  } deriving (Show, Eq)

data Severity = Info | Warning | Critical | Emergency
  deriving (Show, Eq, Ord)

data SafetyViolation = SafetyViolation
  { violationId   :: String
  , property      :: String
  , severity      :: Severity
  , description   :: String
  , actualValue   :: Double
  , limitValue    :: Double
  } deriving (Show, Eq)

data SafetyResult
  = Safe
  | Violation SafetyViolation
  deriving (Show, Eq)

type SafetyProperty = DroneState -> SafetyResult

-- ============================================================
-- Safety properties

altitudeProperty :: Double -> Double -> SafetyProperty
altitudeProperty minAlt maxAlt state
  | altitude state > maxAlt =
      Violation $ SafetyViolation
        { violationId   = "ALT-001"
        , property      = "max_altitude"
        , severity      = Critical
        , description   = "Altitude exceeds maximum limit"
        , actualValue   = altitude state
        , limitValue    = maxAlt
        }
  | altitude state < minAlt && mode state /= "LAND" =
      Violation $ SafetyViolation
        { violationId   = "ALT-002"
        , property      = "min_altitude"
        , severity      = Warning
        , description   = "Altitude below minimum during non-landing"
        , actualValue   = altitude state
        , limitValue    = minAlt
        }
  | otherwise = Safe

batteryProperty :: Double -> Double -> SafetyProperty
batteryProperty criticalPct rtlPct state
  | battery state <= criticalPct =
      Violation $ SafetyViolation
        { violationId   = "BAT-001"
        , property      = "critical_battery"
        , severity      = Emergency
        , description   = "Battery critically low — immediate landing required"
        , actualValue   = battery state
        , limitValue    = criticalPct
        }
  | battery state <= rtlPct =
      Violation $ SafetyViolation
        { violationId   = "BAT-002"
        , property      = "rtl_battery"
        , severity      = Critical
        , description   = "Battery low — RTL required"
        , actualValue   = battery state
        , limitValue    = rtlPct
        }
  | otherwise = Safe

speedProperty :: Double -> SafetyProperty
speedProperty maxSpeed state
  | speed state > maxSpeed =
      Violation $ SafetyViolation
        { violationId   = "SPD-001"
        , property      = "max_speed"
        , severity      = Warning
        , description   = "Speed exceeds safety limit"
        , actualValue   = speed state
        , limitValue    = maxSpeed
        }
  | otherwise = Safe

-- Haversine distance between two positions in meters
haversine :: Double -> Double -> Double -> Double -> Double
haversine lat1 lon1 lat2 lon2 =
  let earthR  = 6_371_000
      toRad x = x * pi / 180
      dLat    = toRad (lat2 - lat1)
      dLon    = toRad (lon2 - lon1)
      a       = sin (dLat/2)^2
              + cos (toRad lat1) * cos (toRad lat2) * sin (dLon/2)^2
  in earthR * 2 * atan2 (sqrt a) (sqrt (1 - a))

geofenceProperty :: Double -> Double -> Double -> SafetyProperty
geofenceProperty centerLat centerLon radiusM state =
  let dist = haversine (latitude state) (longitude state) centerLat centerLon
  in if dist > radiusM
     then Violation $ SafetyViolation
            { violationId   = "GEO-001"
            , property      = "geofence"
            , severity      = Critical
            , description   = "Drone outside geofence boundary"
            , actualValue   = dist
            , limitValue    = radiusM
            }
     else Safe

separationProperty :: Double -> [DroneState] -> SafetyProperty
separationProperty minSepM others state =
  let violations = do
        other <- others
        let dist = haversine (latitude state) (longitude state)
                              (latitude other) (longitude other)
            altDiff = abs (altitude state - altitude other)
            sep3d = sqrt (dist^2 + altDiff^2)
        if droneId other /= droneId state && sep3d < minSepM
        then [Violation $ SafetyViolation
               { violationId   = "SEP-001"
               , property      = "minimum_separation"
               , severity      = Critical
               , description   = "Separation below minimum with " ++ droneId other
               , actualValue   = sep3d
               , limitValue    = minSepM
               }]
        else []
  in case violations of
       (v:_) -> v
       []    -> Safe

-- ============================================================
-- Verification runner

verifyState :: DroneState -> [SafetyProperty] -> [SafetyViolation]
verifyState state props =
  [ v | prop <- props
      , Violation v <- [prop state]
  ]

verifyAll :: [DroneState] -> [SafetyProperty] -> Either [SafetyViolation] ()
verifyAll states props =
  let allViolations = concatMap (\s -> verifyState s props) states
  in if null allViolations
     then Right ()
     else Left allViolations

-- ============================================================
-- Default property set

defaultProperties :: [DroneState] -> [SafetyProperty]
defaultProperties allDrones =
  [ altitudeProperty 10.0 120.0
  , batteryProperty 10.0 20.0
  , speedProperty 15.0
  , geofenceProperty 37.5665 126.978 1000.0
  , separationProperty 30.0 allDrones
  ]

-- ============================================================
-- Report

formatViolation :: SafetyViolation -> String
formatViolation v =
  "[" ++ show (severity v) ++ "] " ++ violationId v ++
  ": " ++ description v ++
  " (actual=" ++ show (actualValue v) ++
  ", limit=" ++ show (limitValue v) ++ ")"

printReport :: Either [SafetyViolation] () -> IO ()
printReport (Right ()) = putStrLn "Safety check PASSED — all properties satisfied"
printReport (Left vs)  = do
  putStrLn $ "Safety check FAILED — " ++ show (length vs) ++ " violation(s):"
  mapM_ (putStrLn . ("  " ++) . formatViolation) vs

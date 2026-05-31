-- P552: SafetyVerifier - Haskell formal safety verification
-- Phase 552: Type-safe verification using monadic composition

module SafetyVerifier where

import Data.Either (lefts, rights)
import Data.Maybe (mapMaybe)
import Data.List (nub, sortBy)
import Data.Ord (comparing)

-- Safety constraint types
data SafetyViolation
  = AltitudeViolation DroneId Double Double
  | SeparationViolation DroneId DroneId Double
  | SpeedViolation DroneId Double
  | BatteryViolation DroneId Double
  deriving (Show, Eq)

type DroneId = String
type Position = (Double, Double, Double)
type Velocity = (Double, Double, Double)

data DroneState = DroneState
  { droneId   :: DroneId
  , position  :: Position
  , velocity  :: Velocity
  , battery   :: Double
  , active    :: Bool
  } deriving (Show, Eq)

data SafetyConfig = SafetyConfig
  { minAltitude    :: Double
  , maxAltitude    :: Double
  , minSeparation  :: Double
  , minBattery     :: Double
  , maxSpeed       :: Double
  } deriving (Show)

defaultSafetyConfig :: SafetyConfig
defaultSafetyConfig = SafetyConfig
  { minAltitude   = 30.0
  , maxAltitude   = 150.0
  , minSeparation = 5.0
  , minBattery    = 0.15
  , maxSpeed      = 20.0
  }

-- Monadic safety check
type SafetyCheck a = Either [SafetyViolation] a

dist3d :: Position -> Position -> Double
dist3d (x1,y1,z1) (x2,y2,z2) =
  sqrt $ (x2-x1)^2 + (y2-y1)^2 + (z2-z1)^2

speed3d :: Velocity -> Double
speed3d (vx,vy,vz) = sqrt $ vx^2 + vy^2 + vz^2

checkAltitude :: SafetyConfig -> DroneState -> Maybe SafetyViolation
checkAltitude cfg d
  | z < minAltitude cfg = Just $ AltitudeViolation (droneId d) z (minAltitude cfg)
  | z > maxAltitude cfg = Just $ AltitudeViolation (droneId d) z (maxAltitude cfg)
  | otherwise           = Nothing
  where (_,_,z) = position d

checkSpeed :: SafetyConfig -> DroneState -> Maybe SafetyViolation
checkSpeed cfg d
  | spd > maxSpeed cfg = Just $ SpeedViolation (droneId d) spd
  | otherwise          = Nothing
  where spd = speed3d (velocity d)

checkBattery :: SafetyConfig -> DroneState -> Maybe SafetyViolation
checkBattery cfg d
  | battery d < minBattery cfg = Just $ BatteryViolation (droneId d) (battery d)
  | otherwise                  = Nothing

checkSeparation :: SafetyConfig -> DroneState -> DroneState -> Maybe SafetyViolation
checkSeparation cfg a b
  | d < minSeparation cfg = Just $ SeparationViolation (droneId a) (droneId b) d
  | otherwise             = Nothing
  where d = dist3d (position a) (position b)

verifySwarm :: SafetyConfig -> [DroneState] -> [SafetyViolation]
verifySwarm cfg drones = perDrone ++ pairwise
  where
    activeDrones = filter active drones
    perDrone = mapMaybe (\d ->
        checkAltitude cfg d <> checkSpeed cfg d <> checkBattery cfg d
      ) activeDrones
    pairwise = [ v
               | (i, a) <- zip [0..] activeDrones
               , (j, b) <- zip [0..] activeDrones
               , i < j
               , Just v <- [checkSeparation cfg a b]
               ]

isSafe :: [SafetyViolation] -> Bool
isSafe = null

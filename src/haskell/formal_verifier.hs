-- formal_verifier.hs - Formal verification for SDACS safety properties
module FormalVerifier where

import Data.List (nub, sortBy)
import Data.Ord (comparing)

data DroneState = DroneState
    { droneId  :: String
    , posX     :: Double
    , posY     :: Double
    , posZ     :: Double
    , battery  :: Int
    , status   :: String
    } deriving (Show, Eq)

data SafetyProperty
    = MinSeparation Double
    | MaxAltitude Double
    | BatteryAbove Int
    deriving Show

verify :: SafetyProperty -> [DroneState] -> Bool
verify (MinSeparation minDist) drones =
    all (\(a,b) -> distance3d a b >= minDist)
        [(a,b) | a <- drones, b <- drones, droneId a < droneId b]
verify (MaxAltitude maxAlt) drones = all (\d -> posZ d <= maxAlt) drones
verify (BatteryAbove minBat) drones = all (\d -> battery d > minBat) drones

distance3d :: DroneState -> DroneState -> Double
distance3d a b =
    sqrt $ (posX a - posX b)^2 + (posY a - posY b)^2 + (posZ a - posZ b)^2

verifyAll :: [SafetyProperty] -> [DroneState] -> [(SafetyProperty, Bool)]
verifyAll props drones = map (\p -> (p, verify p drones)) props

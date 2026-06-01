-- Phase 615 — Haskell Formal Verifier for SDACS Safety Properties
-- Verifies separation and collision-avoidance invariants using type-safe predicates

module FormalVerifier
  ( DroneState(..)
  , SafetyProperty(..)
  , verify
  , checkSeparation
  , checkBatteryInvariant
  , runVerification
  ) where

import Data.List (minimumBy)
import Data.Ord (comparing)

data DroneState = DroneState
  { droneId     :: String
  , posX        :: Double
  , posY        :: Double
  , posZ        :: Double
  , batteryPct  :: Double
  , flightPhase :: String
  } deriving (Show, Eq)

data SafetyProperty
  = MinSeparation Double
  | BatteryAbove Double
  | AltitudeBetween Double Double
  deriving (Show, Eq)

data VerifyResult = Safe | Unsafe String deriving (Show, Eq)

distance :: DroneState -> DroneState -> Double
distance a b = sqrt $ (posX a - posX b)^2 + (posY a - posY b)^2 + (posZ a - posZ b)^2

checkSeparation :: Double -> [DroneState] -> VerifyResult
checkSeparation minDist drones
  | length drones < 2 = Safe
  | minPairDist >= minDist = Safe
  | otherwise = Unsafe $ "Minimum separation " ++ show minPairDist ++ " < " ++ show minDist
  where
    pairs = [(a, b) | (a:bs) <- tails drones, b <- bs]
    tails [] = []; tails (x:xs) = (x:xs) : tails xs
    minPairDist = minimum [distance a b | (a, b) <- pairs]

checkBatteryInvariant :: Double -> [DroneState] -> VerifyResult
checkBatteryInvariant threshold drones =
  case filter (\d -> batteryPct d < threshold && flightPhase d == "ENROUTE") drones of
    []    -> Safe
    (d:_) -> Unsafe $ droneId d ++ " battery " ++ show (batteryPct d) ++ "% below " ++ show threshold

verify :: [DroneState] -> SafetyProperty -> VerifyResult
verify drones (MinSeparation d)      = checkSeparation d drones
verify drones (BatteryAbove t)       = checkBatteryInvariant t drones
verify drones (AltitudeBetween lo hi) =
  case filter (\d -> posZ d < lo || posZ d > hi) drones of
    []    -> Safe
    (d:_) -> Unsafe $ droneId d ++ " altitude " ++ show (posZ d) ++ " out of range"

runVerification :: [DroneState] -> [SafetyProperty] -> [(SafetyProperty, VerifyResult)]
runVerification drones props = [(p, verify drones p) | p <- props]

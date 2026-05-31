-- SDACS Phase 615 — Haskell formal verification of airspace safety properties
module FormalVerifier where
data DroneState = DroneState { droneId :: String, altitude :: Double, speed :: Double } deriving (Show)
safeAltitude :: Double -> Bool
safeAltitude alt = alt >= 30.0 && alt <= 200.0
noCollision :: DroneState -> DroneState -> Double -> Bool
noCollision a b minDist = sqrt ((altitude a - altitude b)^2) >= minDist

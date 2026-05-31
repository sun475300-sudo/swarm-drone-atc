-- Formal Verifier — SDACS Phase 615
module FormalVerifier where

data DroneState = DroneState
  { droneId :: String
  , lat :: Double
  , lon :: Double
  , alt :: Double
  } deriving (Show, Eq)

verify :: DroneState -> Bool
verify d = alt d >= 0 && not (null (droneId d))

safeZone :: Double -> Double -> Bool
safeZone la lo = la >= -90 && la <= 90 && lo >= -180 && lo <= 180

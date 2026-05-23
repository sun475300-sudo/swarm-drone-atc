-- Phase 615: Formal Verifier — Haskell Type-Safe Safety Proofs
-- 형식 검증 기반 안전성 증명 (타입 시스템)

module FormalVerifier where

-- | Drone state representation
data DroneState = DroneState
  { droneId    :: Int
  , posX       :: Double
  , posY       :: Double
  , posZ       :: Double
  , velX       :: Double
  , velY       :: Double
  , velZ       :: Double
  , battery    :: Double
  } deriving (Show, Eq)

-- | Safety property types
data SafetyProperty
  = MinSeparation Double     -- minimum distance between drones
  | MaxAltitude Double       -- altitude ceiling
  | MinBattery Double        -- minimum battery for operation
  | GeofenceBound Double     -- max distance from origin
  deriving (Show, Eq)

-- | Verification result
data VerifyResult
  = Verified String
  | Violated String DroneState
  | Unknown String
  deriving (Show)

-- | Distance between two drones
distance :: DroneState -> DroneState -> Double
distance a b = sqrt $ (posX a - posX b)^2 + (posY a - posY b)^2 + (posZ a - posZ b)^2

-- | Check separation between all drone pairs
verifySeparation :: Double -> [DroneState] -> [VerifyResult]
verifySeparation minDist drones =
  [ if dist >= minDist
    then Verified $ "Pair (" ++ show (droneId a) ++ "," ++ show (droneId b) ++ ") safe: " ++ show dist
    else Violated ("Pair (" ++ show (droneId a) ++ "," ++ show (droneId b) ++ ") violated: " ++ show dist) a
  | a <- drones, b <- drones, droneId a < droneId b
  , let dist = distance a b
  ]

-- | Check single property for one drone
verifyProperty :: SafetyProperty -> DroneState -> VerifyResult
verifyProperty (MinSeparation _) d = Unknown $ "Separation requires pair check for drone " ++ show (droneId d)
verifyProperty (MaxAltitude maxAlt) d
  | posZ d <= maxAlt = Verified $ "Drone " ++ show (droneId d) ++ " altitude OK: " ++ show (posZ d)
  | otherwise        = Violated ("Drone " ++ show (droneId d) ++ " exceeds altitude: " ++ show (posZ d)) d
verifyProperty (MinBattery minBat) d
  | battery d >= minBat = Verified $ "Drone " ++ show (droneId d) ++ " battery OK: " ++ show (battery d)
  | otherwise           = Violated ("Drone " ++ show (droneId d) ++ " low battery: " ++ show (battery d)) d
verifyProperty (GeofenceBound maxR) d
  | r <= maxR   = Verified $ "Drone " ++ show (droneId d) ++ " in geofence: " ++ show r
  | otherwise   = Violated ("Drone " ++ show (droneId d) ++ " outside geofence: " ++ show r) d
  where r = sqrt $ posX d ^ 2 + posY d ^ 2

-- | Verify all properties for all drones
verifyAll :: [SafetyProperty] -> [DroneState] -> [VerifyResult]
verifyAll props drones = concatMap (\p -> case p of
  MinSeparation d -> verifySeparation d drones
  _               -> map (verifyProperty p) drones
  ) props

-- | Count violations
countViolations :: [VerifyResult] -> Int
countViolations = length . filter isViolated
  where
    isViolated (Violated _ _) = True
    isViolated _              = False

-- | Check if system is safe (no violations)
isSystemSafe :: [VerifyResult] -> Bool
isSystemSafe = all (not . isViolated)
  where
    isViolated (Violated _ _) = True
    isViolated _              = False

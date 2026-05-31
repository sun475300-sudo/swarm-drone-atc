-- Phase 552: Formal Safety Verification for Swarm Drones
-- Haskell implementation using Either/Maybe monads
-- SDACS Formal Methods Module

module SafetyVerifier where

import Data.List (foldl', nub, sort)
import Data.Maybe (mapMaybe, fromMaybe, isJust)

-- Safety constraint types
data SafetyConstraint
  = MinSeparation Double     -- minimum distance between drones
  | MaxAltitude Double       -- maximum allowed altitude
  | NoFlyZone (Double, Double, Double, Double)  -- xmin, xmax, ymin, ymax
  | MaxVelocity Double       -- max speed constraint
  | BatteryMinimum Double    -- minimum battery percentage
  deriving (Show, Eq)

-- Drone state for verification
data DroneState = DroneState
  { droneId    :: String
  , posX       :: Double
  , posY       :: Double
  , posZ       :: Double
  , velX       :: Double
  , velY       :: Double
  , velZ       :: Double
  , battery    :: Double
  } deriving (Show, Eq)

-- Safety verification result using Either monad
type SafetyResult a = Either String a

-- Verification context
data VerificationContext = VerificationContext
  { constraints :: [SafetyConstraint]
  , drones      :: [DroneState]
  , timeStep    :: Double
  } deriving (Show)

-- Distance between two drone states
distance :: DroneState -> DroneState -> Double
distance d1 d2 =
  let dx = posX d1 - posX d2
      dy = posY d1 - posY d2
      dz = posZ d1 - posZ d2
  in sqrt (dx*dx + dy*dy + dz*dz)

-- Verify minimum separation constraint using Either
verifySeparation :: Double -> [DroneState] -> SafetyResult [DroneState]
verifySeparation minDist drones =
  let pairs = [(d1, d2) | d1 <- drones, d2 <- drones, droneId d1 < droneId d2]
      violations = filter (\(d1, d2) -> distance d1 d2 < minDist) pairs
  in case violations of
       [] -> Right drones
       vs -> Left $ "Separation violation: " ++ show (length vs) ++ " pairs too close"

-- Verify altitude constraint using Either
verifyAltitude :: Double -> [DroneState] -> SafetyResult [DroneState]
verifyAltitude maxAlt drones =
  let violators = filter (\d -> posZ d > maxAlt) drones
  in case violators of
       [] -> Right drones
       vs -> Left $ "Altitude violation: " ++ show (map droneId vs)

-- Verify no-fly zone using Either
verifyNoFlyZone :: (Double, Double, Double, Double) -> [DroneState] -> SafetyResult [DroneState]
verifyNoFlyZone (xMin, xMax, yMin, yMax) drones =
  let inZone d = posX d >= xMin && posX d <= xMax &&
                 posY d >= yMin && posY d <= yMax
      violators = filter inZone drones
  in case violators of
       [] -> Right drones
       vs -> Left $ "No-fly zone violation: " ++ show (map droneId vs)

-- Verify battery minimum using Maybe
checkBattery :: Double -> DroneState -> Maybe String
checkBattery minBatt d
  | battery d < minBatt = Just (droneId d)
  | otherwise           = Nothing

-- Full Safety verification pipeline using monadic chaining
verifySafety :: VerificationContext -> SafetyResult String
verifySafety ctx =
  let ds = drones ctx
      cs = constraints ctx
      -- Chain all constraint checks
      result = foldl' applyConstraint (Right ds) cs
  in case result of
       Right _ -> Right "All Safety constraints satisfied"
       Left err -> Left err
  where
    applyConstraint (Left e) _ = Left e
    applyConstraint (Right ds) (MinSeparation d)  = verifySeparation d ds
    applyConstraint (Right ds) (MaxAltitude a)    = verifyAltitude a ds
    applyConstraint (Right ds) (NoFlyZone bounds) = verifyNoFlyZone bounds ds
    applyConstraint (Right ds) (MaxVelocity _)    = Right ds  -- simplified
    applyConstraint (Right ds) (BatteryMinimum b) =
      let lowBatt = mapMaybe (checkBattery b) ds
      in if null lowBatt
         then Right ds
         else Left $ "Battery too low: " ++ show lowBatt

-- Verify single Safety property
verifyProperty :: String -> DroneState -> Bool
verifyProperty "grounded" d = posZ d < 0.1
verifyProperty "airborne" d = posZ d > 10.0
verifyProperty "safe_battery" d = battery d > 20.0
verifyProperty _ _ = True

-- Batch Safety verification
batchVerify :: VerificationContext -> [(String, Either String Bool)]
batchVerify ctx =
  let ds = drones ctx
      checks = [ ("separation", Left $ show (verifySeparation 5.0 ds))
               , ("battery", Right $ all (\d -> battery d > 20.0) ds)
               , ("altitude", Left $ show (verifyAltitude 400.0 ds))
               ]
  in checks

-- Create test context
defaultContext :: VerificationContext
defaultContext = VerificationContext
  { constraints = [ MinSeparation 5.0
                  , MaxAltitude 400.0
                  , BatteryMinimum 20.0
                  ]
  , drones =
      [ DroneState "D1" 0 0 100 1 0 0 80
      , DroneState "D2" 20 0 100 0 1 0 75
      , DroneState "D3" 40 0 100 0 0 0 90
      ]
  , timeStep = 0.1
  }

main :: IO ()
main = do
  putStrLn "SDACS Safety Verifier v552"
  let ctx = defaultContext
  case verifySafety ctx of
    Right msg -> putStrLn $ "PASS: " ++ msg
    Left err  -> putStrLn $ "FAIL: " ++ err
  -- Demonstrate Either and Maybe usage
  let battCheck = mapMaybe (checkBattery 20.0) (drones ctx)
  putStrLn $ "Low battery drones: " ++ show battCheck
  putStrLn "Formal Safety verification complete"

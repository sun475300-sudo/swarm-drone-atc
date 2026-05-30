-- SDACS Safety Verifier — Haskell (Phase 552)
-- 드론 군집 형식적 안전성 검증 (Maybe/Either 모나드)

module SafetyVerifier
  ( DroneState(..)
  , SafetyRule(..)
  , SafetyError(..)
  , verifySafety
  , verifyAll
  , checkSeparation
  , checkAltitude
  , checkBattery
  , safetyReport
  ) where

import Data.List (intercalate)

-- 드론 상태
data DroneState = DroneState
  { droneId   :: String
  , posX      :: Double
  , posY      :: Double
  , posZ      :: Double
  , battery   :: Double
  , speed     :: Double
  , maxAlt    :: Double
  } deriving (Show, Eq)

-- Safety 오류 타입
data SafetyError
  = SeparationViolation String String Double
  | AltitudeViolation String Double Double
  | BatteryLow String Double
  | SpeedExceeded String Double Double
  deriving (Show, Eq)

-- Safety 규칙 타입
data SafetyRule = SafetyRule
  { ruleName   :: String
  , check      :: DroneState -> Either SafetyError ()
  }

-- 개별 Safety 검사들

checkSeparation :: DroneState -> DroneState -> Either SafetyError ()
checkSeparation a b =
  let dx = posX a - posX b
      dy = posY a - posY b
      dz = posZ a - posZ b
      dist = sqrt (dx*dx + dy*dy + dz*dz)
      minSep = 30.0
  in if dist < minSep
     then Left (SeparationViolation (droneId a) (droneId b) dist)
     else Right ()

checkAltitude :: DroneState -> Either SafetyError ()
checkAltitude drone =
  let alt = posZ drone
      limit = maxAlt drone
  in if alt > limit
     then Left (AltitudeViolation (droneId drone) alt limit)
     else Right ()

checkBattery :: DroneState -> Either SafetyError ()
checkBattery drone =
  let batt = battery drone
      threshold = 15.0
  in if batt < threshold
     then Left (BatteryLow (droneId drone) batt)
     else Right ()

checkSpeed :: DroneState -> Either SafetyError ()
checkSpeed drone =
  let spd = speed drone
      maxSpd = 20.0
  in if spd > maxSpd
     then Left (SpeedExceeded (droneId drone) spd maxSpd)
     else Right ()

-- 전체 Safety 검증 파이프라인 (Maybe 모나드 스타일)
verifySafety :: DroneState -> Maybe SafetyError
verifySafety drone =
  case checkAltitude drone of
    Left err -> Just err
    Right () ->
      case checkBattery drone of
        Left err -> Just err
        Right () ->
          case checkSpeed drone of
            Left err -> Just err
            Right () -> Nothing

-- 다중 드론 교차 검증 (Either 모나드)
verifyAll :: [DroneState] -> [SafetyError]
verifyAll drones =
  let selfChecks = concatMap (\d ->
        case verifySafety d of
          Just err -> [err]
          Nothing  -> []
        ) drones
      pairChecks = [ err
        | (i, a) <- zip [0..] drones
        , (j, b) <- zip [0..] drones
        , i < j
        , let result = checkSeparation a b
        , Left err <- [result]
        ]
  in selfChecks ++ pairChecks

-- 보고서 생성
safetyReport :: [DroneState] -> String
safetyReport drones =
  let errors = verifyAll drones
      status = if null errors then "SAFE" else "UNSAFE"
  in "=== Safety Report ===\n"
  ++ "Status: " ++ status ++ "\n"
  ++ "Drones checked: " ++ show (length drones) ++ "\n"
  ++ "Violations: " ++ show (length errors) ++ "\n"
  ++ if null errors then "" else "Issues:\n" ++ unlines (map show errors)

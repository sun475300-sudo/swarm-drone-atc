-- Phase 552: SafetyVerifier — Haskell 기반 군집 드론 안전 검증
-- SDACS Safety Verification Module using Monadic Composition
module SafetyVerifier where

import Data.Maybe (mapMaybe, fromMaybe)
import Data.List (minimumBy)
import Data.Ord (comparing)
import Control.Monad (when, forM_)
import Data.Map.Strict (Map)
import qualified Data.Map.Strict as Map

-- | 드론 상태 타입
data DroneState = DroneState
  { droneId    :: Int
  , latitude   :: Double
  , longitude  :: Double
  , altitude   :: Double
  , battery    :: Double
  , isArmed    :: Bool
  , flightMode :: String
  } deriving (Show, Eq)

-- | 안전 위반 타입
data SafetyViolation
  = BatteryLow      { violDroneId :: Int, batteryLevel :: Double }
  | AltitudeTooHigh { violDroneId :: Int, currentAlt :: Double }
  | GeofenceBreach  { violDroneId :: Int, distance :: Double }
  | ProximityAlert  { violDroneId1 :: Int, violDroneId2 :: Int, separation :: Double }
  | SignalLost      { violDroneId :: Int }
  deriving (Show)

-- | 안전 임계값 설정
data SafetyThresholds = SafetyThresholds
  { minBattery      :: Double  -- 최소 배터리 (%)
  , maxAltitude     :: Double  -- 최대 고도 (m)
  , geofenceRadius  :: Double  -- 지오펜스 반경 (m)
  , minSeparation   :: Double  -- 최소 분리 거리 (m)
  } deriving (Show)

defaultThresholds :: SafetyThresholds
defaultThresholds = SafetyThresholds
  { minBattery     = 20.0
  , maxAltitude    = 120.0
  , geofenceRadius = 500.0
  , minSeparation  = 5.0
  }

-- | Safety 검증 모나드 (Either 기반 오류 처리)
type SafetyCheck a = Either String a

-- | 배터리 수준 검증
checkBattery :: SafetyThresholds -> DroneState -> SafetyCheck (Maybe SafetyViolation)
checkBattery thresholds drone
  | battery drone < minBattery thresholds =
      Right $ Just $ BatteryLow (droneId drone) (battery drone)
  | otherwise = Right Nothing

-- | 고도 한계 검증
checkAltitude :: SafetyThresholds -> DroneState -> SafetyCheck (Maybe SafetyViolation)
checkAltitude thresholds drone
  | altitude drone > maxAltitude thresholds =
      Right $ Just $ AltitudeTooHigh (droneId drone) (altitude drone)
  | altitude drone < 0 =
      Left $ "Invalid altitude for drone " ++ show (droneId drone)
  | otherwise = Right Nothing

-- | 지오펜스 검증 (원점 기준)
checkGeofence :: SafetyThresholds -> DroneState -> SafetyCheck (Maybe SafetyViolation)
checkGeofence thresholds drone =
  let dist = sqrt (latitude drone ^ 2 + longitude drone ^ 2) * 111320.0
  in if dist > geofenceRadius thresholds
     then Right $ Just $ GeofenceBreach (droneId drone) dist
     else Right Nothing

-- | 충돌 위험 검증
checkProximity :: SafetyThresholds -> DroneState -> [DroneState] -> [SafetyViolation]
checkProximity thresholds drone others =
  mapMaybe check others
  where
    check other =
      let sep = euclideanDist drone other
      in if sep < minSeparation thresholds
         then Just $ ProximityAlert (droneId drone) (droneId other) sep
         else Nothing

-- | 유클리드 거리 계산
euclideanDist :: DroneState -> DroneState -> Double
euclideanDist d1 d2 =
  let dlat = (latitude d1 - latitude d2) * 111320.0
      dlon = (longitude d1 - longitude d2) * 111320.0 * cos (latitude d1 * pi / 180.0)
      dalt = altitude d1 - altitude d2
  in sqrt (dlat^2 + dlon^2 + dalt^2)

-- | 전체 드론에 대한 안전 검증 실행 (Maybe 활용)
verifySafety :: SafetyThresholds -> [DroneState] -> Either String [SafetyViolation]
verifySafety thresholds drones = do
  individualViolations <- mapM (verifyDrone thresholds drones) drones
  return $ concat individualViolations

-- | 개별 드론 안전 검증
verifyDrone :: SafetyThresholds -> [DroneState] -> DroneState -> Either String [SafetyViolation]
verifyDrone thresholds allDrones drone = do
  battViol  <- checkBattery thresholds drone
  altViol   <- checkAltitude thresholds drone
  fenceViol <- checkGeofence thresholds drone
  let others   = filter ((/= droneId drone) . droneId) allDrones
      proxViols = checkProximity thresholds drone others
  return $ mapMaybe id [battViol, altViol, fenceViol] ++ proxViols

-- | 안전 보고서 생성
generateSafetyReport :: [SafetyViolation] -> String
generateSafetyReport [] = "Safety check passed: No violations detected."
generateSafetyReport violations =
  unlines $ "Safety violations detected:" : map showViolation violations
  where
    showViolation (BatteryLow did lvl) =
      "  CRITICAL: Drone " ++ show did ++ " battery at " ++ show lvl ++ "%"
    showViolation (AltitudeTooHigh did alt) =
      "  WARNING: Drone " ++ show did ++ " altitude " ++ show alt ++ "m exceeds limit"
    showViolation (GeofenceBreach did dist) =
      "  ALERT: Drone " ++ show did ++ " breached geofence at " ++ show dist ++ "m"
    showViolation (ProximityAlert d1 d2 sep) =
      "  DANGER: Drones " ++ show d1 ++ " and " ++ show d2 ++ " separation " ++ show sep ++ "m"
    showViolation (SignalLost did) =
      "  ERROR: Signal lost for drone " ++ show did

-- | 메인 검증 실행
main :: IO ()
main = do
  let thresholds = defaultThresholds
  let drones =
        [ DroneState 0 37.5 127.0 50.0 85.0 True  "GUIDED"
        , DroneState 1 37.5 127.0 52.0 15.0 True  "GUIDED"  -- 낮은 배터리
        , DroneState 2 37.5 127.0 130.0 90.0 True "AUTO"    -- 고도 초과
        ]
  putStrLn "SDACS Safety Verification System — Phase 552"
  case verifySafety thresholds drones of
    Left err     -> putStrLn $ "Verification error: " ++ err
    Right viols  -> putStr $ generateSafetyReport viols

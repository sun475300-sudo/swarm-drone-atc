-- Phase 615: formal_verifier — Haskell 기반 형식 검증기
-- SDACS Formal Verification Module using Temporal Logic

module FormalVerifier where

import Data.Maybe (mapMaybe, fromMaybe, isJust)
import Data.List (nub, sort, group)
import Control.Monad (guard)

-- 드론 상태 타입
data DroneState = DroneState
  { stateId      :: Int
  , stateBattery :: Double
  , stateAlt     :: Double
  , stateArmed   :: Bool
  , stateMode    :: String
  } deriving (Show, Eq, Ord)

-- 시스템 속성 (LTL 형식)
data Property
  = Always Predicate        -- □P: 항상 P 성립
  | Eventually Predicate    -- ◇P: 언젠가 P 성립
  | Until Predicate Predicate -- P U Q: Q가 될 때까지 P 성립
  | Not Property
  | And Property Property
  | Or Property Property
  deriving (Show)

-- 예측 함수 타입
type Predicate = DroneState -> Bool

-- 안전 속성 정의
batteryAbove20 :: Predicate
batteryAbove20 = \s -> stateBattery s > 20.0

altBelow120 :: Predicate
altBelow120 = \s -> stateAlt s < 120.0

notArmedOnGround :: Predicate
notArmedOnGround = \s -> not (stateArmed s && stateAlt s <= 0.5)

validMode :: Predicate
validMode = \s -> stateMode s `elem` ["STABILIZE","GUIDED","AUTO","RTL","LAND","HOLD"]

-- 활성화 상태 확인 (Either 기반 오류 처리)
checkBatteryLevel :: DroneState -> Either String ()
checkBatteryLevel s
  | stateBattery s < 0    = Left $ "Invalid battery " ++ show (stateBattery s)
  | stateBattery s > 100  = Left $ "Battery exceeds 100%"
  | otherwise             = Right ()

checkAltitude :: DroneState -> Either String ()
checkAltitude s
  | stateAlt s < 0   = Left $ "Negative altitude: " ++ show (stateAlt s)
  | stateAlt s > 500 = Left $ "Altitude exceeds safe limit: " ++ show (stateAlt s)
  | otherwise        = Right ()

checkArmedState :: DroneState -> Either String ()
checkArmedState s
  | not (notArmedOnGround s) = Left $ "Drone " ++ show (stateId s) ++ " armed on ground"
  | otherwise               = Right ()

-- 시스템 상태 추적 검증
verifyTrace :: [DroneState] -> Property -> Bool
verifyTrace [] _             = True
verifyTrace trace (Always p) = all p trace
verifyTrace trace (Eventually p) = any p trace
verifyTrace trace (Not prop)  = not (verifyTrace trace prop)
verifyTrace trace (And p1 p2) = verifyTrace trace p1 && verifyTrace trace p2
verifyTrace trace (Or  p1 p2) = verifyTrace trace p1 || verifyTrace trace p2
verifyTrace trace (Until p q) = verifyUntil trace p q

verifyUntil :: [DroneState] -> Predicate -> Predicate -> Bool
verifyUntil [] _ q           = False
verifyUntil (s:rest) p q
  | q s       = True
  | p s       = verifyUntil rest p q
  | otherwise = False

-- 다중 드론 시스템 검증
data SystemSpec = SystemSpec
  { specProperties :: [Property]
  , specDroneCount :: Int
  , specMinSep     :: Double
  }

verifySystem :: SystemSpec -> [[DroneState]] -> [(Int, Bool, String)]
verifySystem spec traces = zipWith3 checkTrace [0..] traces (repeat spec)
  where
    checkTrace idx trace _ =
      let results = map (verifyTrace trace) (specProperties spec)
          allOk   = and results
          msg     = if allOk then "PASS" else "FAIL: " ++ show (filter (not . fst) (zip results (specProperties spec)))
      in (idx, allOk, msg)

-- 반례 생성 (Maybe 활용)
findCounterexample :: [DroneState] -> Predicate -> Maybe DroneState
findCounterexample trace p = case filter (not . p) trace of
  []    -> Nothing
  (x:_) -> Just x

-- 전체 검증 보고서
generateVerificationReport :: SystemSpec -> [[DroneState]] -> String
generateVerificationReport spec traces =
  let results = verifySystem spec traces
      passed  = length $ filter (\(_,ok,_) -> ok) results
      total   = length results
  in unlines $
       [ "=== SDACS Formal Verification Report (Phase 615) ==="
       , "Drones verified: " ++ show total
       , "Properties checked: " ++ show (length (specProperties spec))
       , "Passed: " ++ show passed ++ "/" ++ show total
       ] ++ map (\(i,ok,msg) -> "  Drone " ++ show i ++ ": " ++ msg) results

-- 메인
main :: IO ()
main = do
  putStrLn "SDACS Formal Verifier — Phase 615"
  let spec = SystemSpec
        { specProperties = [Always batteryAbove20, Always altBelow120, Always validMode]
        , specDroneCount = 3
        , specMinSep = 5.0
        }
  let traces =
        [ [ DroneState 0 85.0 50.0 True  "GUIDED"
          , DroneState 0 82.0 55.0 True  "GUIDED"
          , DroneState 0 80.0 60.0 True  "AUTO"   ]
        , [ DroneState 1 90.0 50.0 True  "AUTO"
          , DroneState 1 15.0 50.0 True  "AUTO"   -- 배터리 부족!
          , DroneState 1 12.0 30.0 False "RTL"    ]
        ]
  putStr $ generateVerificationReport spec traces

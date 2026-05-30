-- SDACS Formal Verifier — Haskell (Phase 615)
-- 드론 군집 형식 검증 (LTL 속성 검사 + 모델 체킹)

module FormalVerifier
  ( DroneModel(..)
  , LTLProp(..)
  , SystemTrace
  , verify
  , checkSafetyInvariant
  , checkLivenessProperty
  , generateTrace
  , verifyAll
  , modelCheck
  ) where

import Data.List (nub, intercalate)

-- 드론 추상 모델
data DroneModel = DroneModel
  { dmId       :: String
  , dmAltitude :: Double
  , dmBattery  :: Double
  , dmState    :: String
  } deriving (Show, Eq)

-- LTL 속성 타입
data LTLProp
  = Atom String (DroneModel -> Bool)
  | Always LTLProp
  | Eventually LTLProp
  | Next LTLProp
  | Until LTLProp LTLProp
  | Not LTLProp
  | And LTLProp LTLProp
  | Or LTLProp LTLProp

-- 시스템 트레이스 (상태 열)
type SystemTrace = [[DroneModel]]

-- 원자 명제 평가
evalAtom :: (DroneModel -> Bool) -> [DroneModel] -> Bool
evalAtom p state = any p state

-- 안전성 불변식 검사 (G φ)
checkSafetyInvariant :: (DroneModel -> Bool) -> SystemTrace -> Bool
checkSafetyInvariant p trace = all (evalAtom p) trace

-- 활성성 속성 검사 (F φ)
checkLivenessProperty :: (DroneModel -> Bool) -> SystemTrace -> Bool
checkLivenessProperty p trace = any (evalAtom p) trace

-- 속성 검증 (단순 경계 모델 체킹)
verify :: LTLProp -> SystemTrace -> Bool
verify prop trace =
  case prop of
    Atom _ p     -> any (evalAtom p) trace
    Always q     -> all (verify q . (:[])) trace  -- G
    Eventually q -> any (verify q . (:[])) trace  -- F
    Not q        -> not (verify q trace)
    And q1 q2    -> verify q1 trace && verify q2 trace
    Or  q1 q2    -> verify q1 trace || verify q2 trace
    Next q       -> case trace of
                      (_:rest) -> verify q rest
                      []       -> False
    Until q1 q2  -> verifyUntil q1 q2 trace

verifyUntil :: LTLProp -> LTLProp -> SystemTrace -> Bool
verifyUntil _ q2 [] = False
verifyUntil q1 q2 (s:rest)
  | verify q2 [s] = True
  | verify q1 [s] = verifyUntil q1 q2 rest
  | otherwise     = False

-- 모델 체킹 주 진입점
modelCheck :: [LTLProp] -> SystemTrace -> [(Int, Bool)]
modelCheck props trace = zip [1..] (map (`verify` trace) props)

-- 테스트용 트레이스 생성
generateTrace :: Int -> Int -> SystemTrace
generateTrace nDrones nSteps =
  [ [ DroneModel
        { dmId       = "D-" ++ show d
        , dmAltitude = 100.0 + fromIntegral (step * 2)
        , dmBattery  = max 0.0 (100.0 - fromIntegral step * 0.5)
        , dmState    = if step < nSteps - 2 then "FLYING" else "LANDING"
        }
    | d <- [1..nDrones]
    ]
  | step <- [0..nSteps - 1]
  ]

-- 일괄 검증 + 보고서
verifyAll :: [LTLProp] -> SystemTrace -> String
verifyAll props trace =
  let results = modelCheck props trace
      passed  = length (filter snd results)
      total   = length results
  in "=== Formal Verification (Phase 615) ===\n"
  ++ "Properties: " ++ show total ++ "  Passed: " ++ show passed ++ "\n"
  ++ concatMap (\(i, ok) ->
       "  P" ++ show i ++ ": " ++ (if ok then "SATISFIED" else "VIOLATED") ++ "\n"
    ) results

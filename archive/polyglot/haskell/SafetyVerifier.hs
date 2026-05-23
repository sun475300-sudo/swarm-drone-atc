-- Phase 552: Haskell Monadic Safety Verification
-- 모나드 기반 안전성 검증: Maybe/Either로 실패 전파, State 모나드로 검증 상태 추적

module SafetyVerifier where

import Data.List (foldl')

-- Types
data SafetyLevel = Safe | Warning | Critical | Failed deriving (Show, Eq, Ord)

data DroneState = DroneState
  { dsId       :: String
  , dsAltitude :: Double
  , dsBattery  :: Double
  , dsSpeed    :: Double
  , dsTemp     :: Double
  } deriving (Show)

data VerifyResult = VerifyResult
  { vrDroneId :: String
  , vrLevel   :: SafetyLevel
  , vrChecks  :: Int
  , vrPassed  :: Int
  , vrMessage :: String
  } deriving (Show)

data PRNG = PRNG { prngState :: Int }

mkPRNG :: Int -> PRNG
mkPRNG seed = PRNG (seed `xor` 0x6c62272e)
  where xor = Data.Bits.xor

nextPRNG :: PRNG -> (Int, PRNG)
nextPRNG (PRNG s) = let s1 = s `xor` (s `shiftL` 13)
                        s2 = s1 `xor` (s1 `shiftR` 7)
                        s3 = s2 `xor` (s2 `shiftL` 17)
                    in (abs s3, PRNG s3)
  where xor = Data.Bits.xor
        shiftL = Data.Bits.shiftL
        shiftR = Data.Bits.shiftR

-- Pure safety checks using Maybe/Either pattern
checkAltitude :: DroneState -> Either String ()
checkAltitude ds
  | dsAltitude ds < 0    = Left "Altitude below ground"
  | dsAltitude ds > 400  = Left "Altitude exceeds ceiling"
  | otherwise            = Right ()

checkBattery :: DroneState -> Either String ()
checkBattery ds
  | dsBattery ds < 5     = Left "Critical battery"
  | dsBattery ds < 20    = Left "Low battery warning"
  | otherwise            = Right ()

checkSpeed :: DroneState -> Either String ()
checkSpeed ds
  | dsSpeed ds > 30      = Left "Speed exceeds limit"
  | dsSpeed ds < 0       = Left "Invalid negative speed"
  | otherwise            = Right ()

checkTemp :: DroneState -> Either String ()
checkTemp ds
  | dsTemp ds > 60       = Left "Overheating"
  | dsTemp ds < -10      = Left "Too cold for operation"
  | otherwise            = Right ()

-- Monadic composition of checks
verifyDrone :: DroneState -> VerifyResult
verifyDrone ds =
  let checks = [ ("altitude", checkAltitude ds)
               , ("battery",  checkBattery ds)
               , ("speed",    checkSpeed ds)
               , ("temp",     checkTemp ds)
               ]
      results = map snd checks
      nChecks = length checks
      nPassed = length (filter isRight results)
      level   = if nPassed == nChecks then Safe
                else if nPassed >= nChecks - 1 then Warning
                else if nPassed >= 1 then Critical
                else Failed
      msgs    = concatMap showErr results
  in VerifyResult (dsId ds) level nChecks nPassed (if null msgs then "All clear" else unwords msgs)
  where
    isRight (Right _) = True
    isRight _         = False
    showErr (Left e)  = [e]
    showErr _         = []

-- Generate test drones
generateDrones :: Int -> [DroneState]
generateDrones n = map mkDrone [0..n-1]
  where
    mkDrone i = DroneState
      { dsId       = "drone_" ++ show i
      , dsAltitude = 30 + fromIntegral (i * 17 `mod` 370)
      , dsBattery  = 10 + fromIntegral (i * 23 `mod` 90)
      , dsSpeed    = 2 + fromIntegral (i * 7 `mod` 28)
      , dsTemp     = 20 + fromIntegral (i * 11 `mod` 45)
      }

-- Run verification
runVerification :: Int -> [VerifyResult]
runVerification n = map verifyDrone (generateDrones n)

-- Statistics
data Stats = Stats { statTotal :: Int, statSafe :: Int, statWarning :: Int, statCritical :: Int }
  deriving (Show)

computeStats :: [VerifyResult] -> Stats
computeStats vrs = foldl' accum (Stats 0 0 0 0) vrs
  where
    accum (Stats t s w c) vr = Stats (t+1)
      (if vrLevel vr == Safe then s+1 else s)
      (if vrLevel vr == Warning then w+1 else w)
      (if vrLevel vr == Critical then c+1 else c)

main :: IO ()
main = do
  let results = runVerification 15
      stats   = computeStats results
  putStrLn $ "Drones verified: " ++ show (statTotal stats)
  putStrLn $ "Safe: " ++ show (statSafe stats)
  putStrLn $ "Warning: " ++ show (statWarning stats)
  putStrLn $ "Critical: " ++ show (statCritical stats)

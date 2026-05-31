-- formal_verifier.hs
-- Haskell stub for formal verification of SDACS airspace control properties.
-- Checks safety invariants (separation minima, collision-free paths) over
-- symbolic drone state trajectories.

module FormalVerifier
  ( DroneState (..)
  , Trajectory
  , separationOk
  , noCollisionInvariant
  , verifyTrajectories
  ) where

-- ---------------------------------------------------------------------------
-- Types
-- ---------------------------------------------------------------------------

data DroneState = DroneState
  { droneId  :: String
  , posX     :: Double
  , posY     :: Double
  , posZ     :: Double
  , velMs    :: Double
  } deriving (Show, Eq)

type Trajectory = [DroneState]

-- Minimum horizontal separation in metres (ICAO-inspired threshold)
minSeparationM :: Double
minSeparationM = 5.0

-- ---------------------------------------------------------------------------
-- Core predicates
-- ---------------------------------------------------------------------------

-- | Euclidean distance between two drone states (XY plane).
horizontalDistance :: DroneState -> DroneState -> Double
horizontalDistance a b =
  sqrt ((posX a - posX b) ^ (2 :: Int) + (posY a - posY b) ^ (2 :: Int))

-- | True when two drones maintain the required horizontal separation.
separationOk :: DroneState -> DroneState -> Bool
separationOk a b = horizontalDistance a b >= minSeparationM

-- | Check the no-collision invariant across a list of simultaneous states.
noCollisionInvariant :: [DroneState] -> Bool
noCollisionInvariant states =
  and [ separationOk a b
      | (i, a) <- zip [0..] states
      , (j, b) <- zip [0..] states
      , i < j
      ]

-- ---------------------------------------------------------------------------
-- Trajectory verification
-- ---------------------------------------------------------------------------

-- | Verify that every time-step in a set of parallel trajectories satisfies
--   the no-collision invariant.  Returns the indices of violating steps.
verifyTrajectories :: [Trajectory] -> [Int]
verifyTrajectories trajs =
  let timeSteps = transpose trajs
  in  [ t | (t, snapshot) <- zip [0..] timeSteps
          , not (noCollisionInvariant snapshot)
          ]
  where
    -- Minimal transpose for ragged lists
    transpose [] = []
    transpose xss
      | all null xss = []
      | otherwise    = map safeHead xss : transpose (map safeTail xss)
    safeHead []    = error "verifyTrajectories: mismatched trajectory lengths"
    safeHead (x:_) = x
    safeTail []     = []
    safeTail (_:xs) = xs

-- ---------------------------------------------------------------------------
-- Entry point (stub)
-- ---------------------------------------------------------------------------

main :: IO ()
main = do
  putStrLn "SDACS Formal Verifier — stub"
  putStrLn "TODO: load trajectory data and invoke verifyTrajectories"

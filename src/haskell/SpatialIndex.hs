{-|
Module      : SDACS.SpatialIndex
Description : 공간 인덱싱 — Haskell 순수 함수형 구현
Copyright   : SDACS Team, 2026

기능:
  - 순수 함수형 KD-Tree
  - 범위 검색 (O(log N) 평균)
  - 최근접 이웃 검색 (k-NN)
  - 불변 데이터 구조 (Thread-Safe)
-}

module SpatialIndex
  ( Vec3(..)
  , KDTree
  , DroneEntry(..)
  , buildTree
  , rangeSearch
  , kNearest
  , treeSize
  , distance3D
  ) where

-- | 3D 벡터
data Vec3 = Vec3
  { vx :: !Double
  , vy :: !Double
  , vz :: !Double
  } deriving (Show, Eq)

-- | 두 점 사이 거리
distance3D :: Vec3 -> Vec3 -> Double
distance3D (Vec3 x1 y1 z1) (Vec3 x2 y2 z2) =
  sqrt ((x1-x2)^2 + (y1-y2)^2 + (z1-z2)^2)

-- | 수평 거리
horizontalDistance :: Vec3 -> Vec3 -> Double
horizontalDistance (Vec3 x1 y1 _) (Vec3 x2 y2 _) =
  sqrt ((x1-x2)^2 + (y1-y2)^2)

-- | 드론 엔트리
data DroneEntry = DroneEntry
  { droneId  :: !String
  , position :: !Vec3
  , priority :: !Int
  } deriving (Show, Eq)

-- | KD-Tree 노드
data KDTree
  = Leaf
  | Node
    { nodeEntry :: !DroneEntry
    , splitDim  :: !Int        -- 0=x, 1=y, 2=z
    , leftTree  :: !KDTree
    , rightTree :: !KDTree
    } deriving (Show)

-- | 좌표 접근
getCoord :: Vec3 -> Int -> Double
getCoord (Vec3 x _ _) 0 = x
getCoord (Vec3 _ y _) 1 = y
getCoord (Vec3 _ _ z) _ = z

-- | KD-Tree 구축 — O(N log N)
buildTree :: [DroneEntry] -> KDTree
buildTree = build 0
  where
    build _ [] = Leaf
    build depth entries =
      let dim = depth `mod` 3
          sorted = sortByDim dim entries
          mid = length sorted `div` 2
          (lefts, pivot:rights) = splitAt mid sorted
      in Node
        { nodeEntry = pivot
        , splitDim  = dim
        , leftTree  = build (depth + 1) lefts
        , rightTree = build (depth + 1) rights
        }

    sortByDim dim = mergeSort (\a b ->
      getCoord (position a) dim <= getCoord (position b) dim)

-- | 범위 검색 — 반경 내 모든 드론
rangeSearch :: KDTree -> Vec3 -> Double -> [(DroneEntry, Double)]
rangeSearch Leaf _ _ = []
rangeSearch (Node entry dim left right) center radius =
  let dist = distance3D (position entry) center
      inRange = if dist <= radius
                then [(entry, dist)]
                else []

      centerCoord = getCoord center dim
      nodeCoord = getCoord (position entry) dim
      diff = centerCoord - nodeCoord

      (near, far) = if diff < 0
                    then (left, right)
                    else (right, left)

      nearResults = rangeSearch near center radius
      farResults  = if abs diff <= radius
                    then rangeSearch far center radius
                    else []

  in inRange ++ nearResults ++ farResults

-- | k-최근접 이웃 검색
kNearest :: KDTree -> Vec3 -> Int -> [(DroneEntry, Double)]
kNearest tree center k =
  let allInRange = rangeSearch tree center 1e9  -- 전체 검색
      sorted = mergeSort (\a b -> snd a <= snd b) allInRange
  in take k sorted

-- | 트리 크기
treeSize :: KDTree -> Int
treeSize Leaf = 0
treeSize (Node _ _ l r) = 1 + treeSize l + treeSize r

-- | 안정 병합 정렬 (순수 함수형)
mergeSort :: (a -> a -> Bool) -> [a] -> [a]
mergeSort _ [] = []
mergeSort _ [x] = [x]
mergeSort cmp xs =
  let mid = length xs `div` 2
      (left, right) = splitAt mid xs
  in merge cmp (mergeSort cmp left) (mergeSort cmp right)

merge :: (a -> a -> Bool) -> [a] -> [a] -> [a]
merge _ [] ys = ys
merge _ xs [] = xs
merge cmp (x:xs) (y:ys)
  | cmp x y  = x : merge cmp xs (y:ys)
  | otherwise = y : merge cmp (x:xs) ys

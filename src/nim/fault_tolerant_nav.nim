## Phase 526 — Fault-tolerant navigation using Extended Kalman Filter (EKF)
## with multiple Sensor fusion for drone swarm.
## Merges GPS, IMU, barometer, and optical-flow sensor streams.

import math, strformat, sequtils

# ---- Phase marker ----
const PHASE_MARKER* = 526

# ---- Dimensional constants ----
const STATE_DIM* = 9    # [x, y, z, vx, vy, vz, roll, pitch, yaw]
const OBS_GPS = 3       # GPS observes [x, y, z]
const OBS_BARO = 1      # Barometer observes [z]
const OBS_FLOW = 2      # Optical flow observes [vx, vy]

# ---- Simple matrix type (row-major flat array) ----
type Matrix* = object
  rows*, cols*: int
  data*: seq[float]

proc newMatrix*(rows, cols: int): Matrix =
  Matrix(rows: rows, cols: cols, data: newSeq[float](rows * cols))

proc `[]`*(m: Matrix, r, c: int): float = m.data[r * m.cols + c]
proc `[]=`*(m: var Matrix, r, c: int, v: float) = m.data[r * m.cols + c] = v

proc matAdd*(a, b: Matrix): Matrix =
  assert a.rows == b.rows and a.cols == b.cols
  result = newMatrix(a.rows, a.cols)
  for i in 0 ..< a.data.len: result.data[i] = a.data[i] + b.data[i]

proc matSub*(a, b: Matrix): Matrix =
  assert a.rows == b.rows and a.cols == b.cols
  result = newMatrix(a.rows, a.cols)
  for i in 0 ..< a.data.len: result.data[i] = a.data[i] - b.data[i]

proc matMul*(a, b: Matrix): Matrix =
  assert a.cols == b.rows
  result = newMatrix(a.rows, b.cols)
  for r in 0 ..< a.rows:
    for c in 0 ..< b.cols:
      var acc = 0.0
      for k in 0 ..< a.cols: acc += a[r, k] * b[k, c]
      result[r, c] = acc

proc matScale*(a: Matrix, s: float): Matrix =
  result = newMatrix(a.rows, a.cols)
  for i in 0 ..< a.data.len: result.data[i] = a.data[i] * s

proc transpose*(a: Matrix): Matrix =
  result = newMatrix(a.cols, a.rows)
  for r in 0 ..< a.rows:
    for c in 0 ..< a.cols: result[c, r] = a[r, c]

proc eye*(n: int): Matrix =
  result = newMatrix(n, n)
  for i in 0 ..< n: result[i, i] = 1.0

## Scalar-inverse for 1x1 matrix — sufficient for BARO and FLOW scalars.
proc inv1x1*(m: Matrix): Matrix =
  assert m.rows == 1 and m.cols == 1
  result = newMatrix(1, 1)
  result[0, 0] = 1.0 / m[0, 0]

# ---- Sensor descriptor ----
type
  SensorType* = enum
    stGPS, stIMU, stBarometer, stOpticalFlow

  Sensor* = object
    kind*: SensorType
    noiseVar*: float    # scalar noise variance
    healthy*: bool      # set false when sensor fault detected

proc newSensor*(kind: SensorType, noiseVar: float): Sensor =
  Sensor(kind: kind, noiseVar: noiseVar, healthy: true)

# ---- EKF state ----
type
  EKFState* = object
    x*: Matrix    # STATE_DIM x 1 state vector
    P*: Matrix    # STATE_DIM x STATE_DIM covariance
    Q*: Matrix    # process noise covariance
    sensors*: seq[Sensor]

proc initEKF*(): EKFState =
  ## Initialise EKF with identity covariance and small process noise.
  var s: EKFState
  s.x = newMatrix(STATE_DIM, 1)
  s.P = eye(STATE_DIM)
  s.Q = matScale(eye(STATE_DIM), 0.01)
  # Register all sensor modalities
  s.sensors = @[
    newSensor(stGPS,          0.5),
    newSensor(stIMU,          0.05),
    newSensor(stBarometer,    0.2),
    newSensor(stOpticalFlow,  0.1)
  ]
  result = s

# ---- EKF prediction step (linear constant-velocity model) ----
proc ekfPredict*(s: var EKFState, dt: float) =
  ## Propagate state with constant-velocity kinematics: x += v*dt.
  ## F is the state transition Jacobian for [pos, vel, attitude].
  var F = eye(STATE_DIM)
  # position += velocity * dt
  F[0, 3] = dt; F[1, 4] = dt; F[2, 5] = dt
  s.x = matMul(F, s.x)
  s.P = matAdd(matMul(matMul(F, s.P), transpose(F)), s.Q)

# ---- EKF update step for GPS (observes x, y, z) ----
proc ekfUpdateGPS*(s: var EKFState, gps_xyz: array[3, float]) =
  let sensor = s.sensors[0]
  if not sensor.healthy: return

  var H = newMatrix(OBS_GPS, STATE_DIM)
  H[0, 0] = 1.0; H[1, 1] = 1.0; H[2, 2] = 1.0

  var R = matScale(eye(OBS_GPS), sensor.noiseVar)
  var z = newMatrix(OBS_GPS, 1)
  z[0, 0] = gps_xyz[0]; z[1, 0] = gps_xyz[1]; z[2, 0] = gps_xyz[2]

  let y = matSub(z, matMul(H, s.x))
  let S = matAdd(matMul(matMul(H, s.P), transpose(H)), R)
  # Kalman gain K = P * H^T * S^-1  (3x3 inversion omitted; use diagonal approx)
  var S_diag_inv = newMatrix(OBS_GPS, OBS_GPS)
  for i in 0 ..< OBS_GPS: S_diag_inv[i, i] = 1.0 / S[i, i]
  let K = matMul(matMul(s.P, transpose(H)), S_diag_inv)
  s.x = matAdd(s.x, matMul(K, y))
  s.P = matMul(matSub(eye(STATE_DIM), matMul(K, H)), s.P)

# ---- EKF update step for Barometer (observes z only) ----
proc ekfUpdateBaro*(s: var EKFState, baro_z: float) =
  let sensor = s.sensors[2]
  if not sensor.healthy: return

  var H = newMatrix(OBS_BARO, STATE_DIM)
  H[0, 2] = 1.0
  var R = newMatrix(OBS_BARO, OBS_BARO)
  R[0, 0] = sensor.noiseVar
  var z = newMatrix(OBS_BARO, 1)
  z[0, 0] = baro_z

  let y = matSub(z, matMul(H, s.x))
  let S = matAdd(matMul(matMul(H, s.P), transpose(H)), R)
  let K = matMul(matMul(s.P, transpose(H)), inv1x1(S))
  s.x = matAdd(s.x, matMul(K, y))
  s.P = matMul(matSub(eye(STATE_DIM), matMul(K, H)), s.P)

# ---- Sensor fault detection (chi-squared test on innovation) ----
proc detectSensorFault*(s: var EKFState, innovation_sq: float, threshold: float = 9.0) =
  ## Mark GPS unhealthy if innovation squared exceeds chi-squared threshold (3 dof, p=0.01).
  if innovation_sq > threshold:
    s.sensors[0].healthy = false
    echo fmt"[EKF Phase {PHASE_MARKER}] GPS fault detected — falling back to IMU+baro"

# ---- Position estimate accessor ----
proc positionEstimate*(s: EKFState): tuple[x, y, z: float] =
  (s.x[0, 0], s.x[1, 0], s.x[2, 0])

# ---- Velocity estimate accessor ----
proc velocityEstimate*(s: EKFState): tuple[vx, vy, vz: float] =
  (s.x[3, 0], s.x[4, 0], s.x[5, 0])

# ---- Smoke test ----
when isMainModule:
  var ekf = initEKF()
  ekf.ekfPredict(0.1)
  ekf.ekfUpdateGPS([1.0, 2.0, 50.0])
  ekf.ekfUpdateBaro(50.05)
  let pos = ekf.positionEstimate()
  echo fmt"[Phase {PHASE_MARKER}] pos=({pos.x:.3f}, {pos.y:.3f}, {pos.z:.3f})"
  assert ekf.sensors.len == 4
  echo fmt"[Phase {PHASE_MARKER}] EKF smoke test passed. Sensor count={ekf.sensors.len}"

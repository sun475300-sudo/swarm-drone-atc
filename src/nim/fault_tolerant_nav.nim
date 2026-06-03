# Phase 526: Fault-Tolerant Navigation — Nim
# SDACS EKF-based fault-tolerant state estimator for drone navigation

import std/[math, tables, strformat]

# Phase 526 marker — EKF Kalman filter for fault-tolerant navigation

const
  STATE_DIM  = 9  # [x, y, z, vx, vy, vz, ax, ay, az]
  SENSOR_DIM = 6  # [gps_x, gps_y, gps_z, baro_alt, acc_x, acc_y]

type
  Vec9  = array[STATE_DIM, float]
  Vec6  = array[SENSOR_DIM, float]
  Mat9  = array[STATE_DIM, array[STATE_DIM, float]]
  Mat6  = array[SENSOR_DIM, array[SENSOR_DIM, float]]
  Mat96 = array[STATE_DIM, array[SENSOR_DIM, float]]
  Mat69 = array[SENSOR_DIM, array[STATE_DIM, float]]

  SensorHealth* = enum
    shGood, shDegraded, shFailed

  Sensor* = object
    id*:        string
    kind*:      string
    health*:    SensorHealth
    last_value*: Vec6
    fail_count*: int

  EKFState* = object
    x*:  Vec9   # state estimate
    P*:  Mat9   # covariance
    Q*:  Mat9   # process noise
    R*:  Mat6   # measurement noise

  FaultTolerantNav* = object
    ekf*:      EKFState
    sensors*:  Table[string, Sensor]
    dt*:       float
    fault_log*: seq[string]

# Matrix helpers
proc zeros9(): Mat9 =
  for i in 0..<STATE_DIM:
    for j in 0..<STATE_DIM: result[i][j] = 0.0

proc eye9(scale: float = 1.0): Mat9 =
  for i in 0..<STATE_DIM:
    result[i][i] = scale

proc matMul9(a, b: Mat9): Mat9 =
  for i in 0..<STATE_DIM:
    for j in 0..<STATE_DIM:
      var s = 0.0
      for k in 0..<STATE_DIM: s += a[i][k] * b[k][j]
      result[i][j] = s

proc matAdd9(a, b: Mat9): Mat9 =
  for i in 0..<STATE_DIM:
    for j in 0..<STATE_DIM:
      result[i][j] = a[i][j] + b[i][j]

proc transpose9(a: Mat9): Mat9 =
  for i in 0..<STATE_DIM:
    for j in 0..<STATE_DIM:
      result[i][j] = a[j][i]

# EKF predict step
proc predict*(nav: var FaultTolerantNav) =
  let dt = nav.dt
  # State transition matrix (constant velocity model)
  var F = eye9(1.0)
  F[0][3] = dt; F[1][4] = dt; F[2][5] = dt  # pos += vel*dt
  F[3][6] = dt; F[4][7] = dt; F[5][8] = dt  # vel += acc*dt

  # x = F*x
  var x_new: Vec9
  for i in 0..<STATE_DIM:
    var s = 0.0
    for j in 0..<STATE_DIM: s += F[i][j] * nav.ekf.x[j]
    x_new[i] = s
  nav.ekf.x = x_new

  # P = F*P*F^T + Q
  let FP   = matMul9(F, nav.ekf.P)
  let FT   = transpose9(F)
  let FPFT = matMul9(FP, FT)
  nav.ekf.P = matAdd9(FPFT, nav.ekf.Q)

# EKF update step (simplified)
proc update*(nav: var FaultTolerantNav, z: Vec6) =
  # Observation matrix H (6x9 — simplified)
  var H: Mat69
  H[0][0] = 1.0  # GPS x
  H[1][1] = 1.0  # GPS y
  H[2][2] = 1.0  # GPS z
  H[3][2] = 1.0  # baro alt ≈ z
  H[4][6] = 1.0  # accel x
  H[5][7] = 1.0  # accel y

  # Innovation: y = z - H*x
  var y: Vec6
  for i in 0..<SENSOR_DIM:
    var Hx = 0.0
    for j in 0..<STATE_DIM: Hx += H[i][j] * nav.ekf.x[j]
    y[i] = z[i] - Hx

  # Simple scalar Kalman gain approximation per sensor
  for i in 0..<SENSOR_DIM:
    let Pii = nav.ekf.P[i][i]
    let Rii = nav.ekf.R[i][i]
    let K   = Pii / (Pii + Rii)
    if i < STATE_DIM:
      nav.ekf.x[i] += K * y[i]
      nav.ekf.P[i][i] *= (1.0 - K)

# Sensor health monitor
proc checkSensorHealth*(nav: var FaultTolerantNav, sensorId: string,
                        innovation: float, threshold: float = 3.0) =
  if sensorId notin nav.sensors: return
  var s = nav.sensors[sensorId]
  if abs(innovation) > threshold:
    s.fail_count += 1
    if s.fail_count > 5:
      s.health = shFailed
      nav.fault_log.add(fmt"FAULT: sensor {sensorId} failed (innov={innovation:.2f})")
    elif s.fail_count > 2:
      s.health = shDegraded
  else:
    s.fail_count = max(0, s.fail_count - 1)
    if s.fail_count == 0: s.health = shGood
  nav.sensors[sensorId] = s

proc initNav*(dt: float = 0.1): FaultTolerantNav =
  result.dt = dt
  result.ekf.x = [0.0, 0.0, 60.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
  result.ekf.P = eye9(10.0)
  result.ekf.Q = eye9(0.1)
  result.ekf.R[0][0] = 1.5  # GPS noise
  result.ekf.R[1][1] = 1.5
  result.ekf.R[2][2] = 2.0
  result.ekf.R[3][3] = 0.5  # baro noise
  result.ekf.R[4][4] = 0.3  # accel noise
  result.ekf.R[5][5] = 0.3
  result.sensors = initTable[string, Sensor]()
  result.fault_log = @[]

  for kind in ["gps", "baro", "imu"]:
    result.sensors[kind] = Sensor(id: kind, kind: kind, health: shGood)

when isMainModule:
  var nav = initNav(0.1)
  echo fmt"Phase 526: EKF Kalman nav initialized"
  echo fmt"State: pos=({nav.ekf.x[0]:.1f}, {nav.ekf.x[1]:.1f}, {nav.ekf.x[2]:.1f})"

  nav.predict()
  let z: Vec6 = [0.1, 0.05, 60.2, 60.1, 0.01, 0.02]
  nav.update(z)
  nav.checkSensorHealth("gps", 0.2)
  echo fmt"After update: pos=({nav.ekf.x[0]:.3f}, {nav.ekf.x[1]:.3f}, {nav.ekf.x[2]:.3f})"
  echo fmt"GPS health: {nav.sensors[\"gps\"].health}"

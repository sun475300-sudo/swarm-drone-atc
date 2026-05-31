# fault_tolerant_nav.nim - Fault-tolerant navigation for SDACS (Phase 526)
# Extended Kalman Filter (EKF) based navigation with sensor fusion

import std/[math, strformat, tables, sequtils]

type
  SensorType* = enum
    stGPS, stIMU, stBarometer, stMagnetometer, stOpticalFlow

  SensorReading* = object
    sensor_type*: SensorType
    value*:       array[3, float64]
    noise_std*:   float64
    valid*:       bool
    timestamp*:   float64

  NavState* = object
    position*:    array[3, float64]
    velocity*:    array[3, float64]
    attitude*:    array[3, float64]
    timestamp*:   float64

  EKFState* = object
    x*:     array[9, float64]   # [pos_x, pos_y, pos_z, vel_x, vel_y, vel_z, att_r, att_p, att_y]
    P*:     array[81, float64]  # 9x9 covariance matrix (flattened)
    Q*:     array[81, float64]  # process noise
    R*:     array[9, float64]   # measurement noise diagonal

  FaultTolerantNavigator* = ref object
    ekf_state*:       EKFState
    sensor_states*:   Table[SensorType, bool]
    nav_history*:     seq[NavState]
    fault_count*:     int
    recovery_count*:  int
    dt*:              float64

proc newNavigator*(dt: float64 = 0.01): FaultTolerantNavigator =
  var nav = FaultTolerantNavigator(dt: dt)
  for st in SensorType: nav.sensor_states[st] = true
  nav.ekf_state.R = [1.0, 1.0, 0.5, 0.1, 0.1, 0.1, 0.01, 0.01, 0.01]
  for i in 0..8:
    nav.ekf_state.P[i*9 + i] = 1.0
    nav.ekf_state.Q[i*9 + i] = 0.01
  nav

proc predict*(nav: FaultTolerantNavigator) =
  # EKF predict step: integrate dynamics
  let dt = nav.dt
  nav.ekf_state.x[0] += nav.ekf_state.x[3] * dt
  nav.ekf_state.x[1] += nav.ekf_state.x[4] * dt
  nav.ekf_state.x[2] += nav.ekf_state.x[5] * dt

proc update*(nav: FaultTolerantNavigator; reading: SensorReading) =
  # EKF update step with Sensor measurement
  if not reading.valid: return
  let innovation = [
    reading.value[0] - nav.ekf_state.x[0],
    reading.value[1] - nav.ekf_state.x[1],
    reading.value[2] - nav.ekf_state.x[2]
  ]
  let kalman_gain = reading.noise_std
  nav.ekf_state.x[0] += innovation[0] / (1.0 + kalman_gain)
  nav.ekf_state.x[1] += innovation[1] / (1.0 + kalman_gain)
  nav.ekf_state.x[2] += innovation[2] / (1.0 + kalman_gain)

proc detectFault*(nav: FaultTolerantNavigator; st: SensorType;
                  reading: SensorReading): bool =
  let residual = sqrt(
    reading.value[0]^2 + reading.value[1]^2 + reading.value[2]^2
  )
  let threshold = 50.0
  if residual > threshold:
    nav.sensor_states[st] = false
    inc nav.fault_count
    return true
  return false

proc recoverFault*(nav: FaultTolerantNavigator; st: SensorType) =
  nav.sensor_states[st] = true
  inc nav.recovery_count

proc getNavState*(nav: FaultTolerantNavigator): NavState =
  NavState(
    position:  [nav.ekf_state.x[0], nav.ekf_state.x[1], nav.ekf_state.x[2]],
    velocity:  [nav.ekf_state.x[3], nav.ekf_state.x[4], nav.ekf_state.x[5]],
    attitude:  [nav.ekf_state.x[6], nav.ekf_state.x[7], nav.ekf_state.x[8]],
    timestamp: 0.0
  )

proc summary*(nav: FaultTolerantNavigator): string =
  fmt"FaultTolerantNav (Phase 526): ekf=active, faults={nav.fault_count}, recoveries={nav.recovery_count}"

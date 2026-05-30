# SDACS Fault-Tolerant Navigation — Nim (Phase 526)
# 드론 내결함성 항법 시스템 (EKF + 센서 중복)

import math, strformat, sequtils

# Sensor 데이터 타입
type
  SensorReading* = object
    id*: string
    x*, y*, z*: float64
    timestamp*: float64
    quality*: float64   # 0..1

  NavState* = object
    x*, y*, z*: float64
    vx*, vy*, vz*: float64
    ax*, ay*, az*: float64

# EKF 상태 (Phase 526 — 6DOF 단순화)
type
  EKFState* = object
    state: array[6, float64]    # [x, y, z, vx, vy, vz]
    P: array[6, array[6, float64]]  # 공분산
    Q: float64  # 프로세스 노이즈
    R: float64  # 측정 노이즈

proc initEKF*(x0, y0, z0: float64): EKFState =
  result.state = [x0, y0, z0, 0.0, 0.0, 0.0]
  result.Q = 0.01
  result.R = 0.1
  for i in 0..5:
    result.P[i][i] = 1.0

proc predict*(ekf: var EKFState, dt: float64) =
  # 상태 전파 (등속 모델)
  ekf.state[0] += ekf.state[3] * dt
  ekf.state[1] += ekf.state[4] * dt
  ekf.state[2] += ekf.state[5] * dt
  # 공분산 증가 (프로세스 노이즈)
  for i in 0..5:
    ekf.P[i][i] += ekf.Q * dt

proc update*(ekf: var EKFState, sensor: SensorReading) =
  # 칼만 이득 계산 (대각선 단순화)
  let K = ekf.P[0][0] / (ekf.P[0][0] + ekf.R)
  ekf.state[0] += K * (sensor.x - ekf.state[0])
  ekf.state[1] += K * (sensor.y - ekf.state[1])
  ekf.state[2] += K * (sensor.z - ekf.state[2])
  for i in 0..5:
    ekf.P[i][i] *= (1.0 - K)

proc getPosition*(ekf: EKFState): tuple[x, y, z: float64] =
  (ekf.state[0], ekf.state[1], ekf.state[2])

# 센서 관리자 (다중 Sensor 중복)
type
  SensorManager* = object
    sensors*: seq[SensorReading]
    threshold*: float64  # 최소 품질

proc addSensor*(mgr: var SensorManager, s: SensorReading) =
  mgr.sensors.add(s)

proc validSensors*(mgr: SensorManager): seq[SensorReading] =
  mgr.sensors.filterIt(it.quality >= mgr.threshold)

proc fusedReading*(mgr: SensorManager): SensorReading =
  let valid = mgr.validSensors()
  if valid.len == 0:
    return SensorReading(id: "NONE", quality: 0.0)
  var x, y, z, w = 0.0
  for s in valid:
    x += s.x * s.quality
    y += s.y * s.quality
    z += s.z * s.quality
    w += s.quality
  SensorReading(id: "FUSED", x: x/w, y: y/w, z: z/w,
                timestamp: valid[0].timestamp, quality: w/float(valid.len))

# 내결함성 항법 컨트롤러
type
  FaultTolerantNav* = object
    ekf*: EKFState
    sensorMgr*: SensorManager
    state*: NavState
    faultCount*: int

proc initNav*(x0, y0, z0: float64, qualThresh = 0.3): FaultTolerantNav =
  result.ekf = initEKF(x0, y0, z0)
  result.sensorMgr.threshold = qualThresh

proc update*(nav: var FaultTolerantNav, dt: float64) =
  nav.ekf.predict(dt)
  let fused = nav.sensorMgr.fusedReading()
  if fused.quality > 0:
    nav.ekf.update(fused)
  else:
    nav.faultCount += 1
  let pos = nav.ekf.getPosition()
  nav.state.x = pos.x; nav.state.y = pos.y; nav.state.z = pos.z

proc isFaultDetected*(nav: FaultTolerantNav): bool = nav.faultCount > 3

when isMainModule:
  var nav = initNav(0.0, 0.0, 100.0)
  echo fmt"Nav initialized at ({nav.state.x:.1f}, {nav.state.y:.1f}, {nav.state.z:.1f})"

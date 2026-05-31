# P526: FaultTolerantNav - Nim EKF-based fault tolerant navigation
# Phase 526: Extended Kalman Filter for multi-sensor fusion navigation

import math
import tables
import times
import strformat

type
  SensorType = enum
    GPS, IMU, Barometer, Optical

  SensorReading = object
    sensor: SensorType
    timestamp: float
    values: seq[float]
    noise_std: float

  NavState = object
    x, y, z: float
    vx, vy, vz: float
    roll, pitch, yaw: float
    timestamp: float

  # Extended Kalman Filter state
  EKF = ref object
    state: seq[float]         # 9-dim state: [x,y,z, vx,vy,vz, roll,pitch,yaw]
    covariance: seq[seq[float]] # 9x9 covariance matrix
    process_noise: float
    sensor_failed: Table[SensorType, bool]

proc newEKF(process_noise: float = 0.1): EKF =
  result = EKF(
    state: newSeq[float](9),
    covariance: newSeqWith(9, newSeq[float](9)),
    process_noise: process_noise,
    sensor_failed: initTable[SensorType, bool]()
  )
  # Initialize identity covariance
  for i in 0..<9:
    result.covariance[i][i] = 1.0
  for s in SensorType:
    result.sensor_failed[s] = false

proc predict(ekf: EKF, dt: float) =
  # State transition: x += vx*dt, y += vy*dt, z += vz*dt
  ekf.state[0] += ekf.state[3] * dt
  ekf.state[1] += ekf.state[4] * dt
  ekf.state[2] += ekf.state[5] * dt
  # Add process noise to diagonal
  for i in 0..<9:
    ekf.covariance[i][i] += ekf.process_noise * dt

proc update(ekf: EKF, reading: SensorReading) =
  if ekf.sensor_failed.getOrDefault(reading.sensor, false):
    return
  case reading.sensor:
  of GPS:
    if reading.values.len >= 3:
      let k = 0.8  # Kalman gain (simplified)
      ekf.state[0] = ekf.state[0] * (1-k) + reading.values[0] * k
      ekf.state[1] = ekf.state[1] * (1-k) + reading.values[1] * k
      ekf.state[2] = ekf.state[2] * (1-k) + reading.values[2] * k
  of IMU:
    if reading.values.len >= 3:
      let k = 0.5
      ekf.state[6] = ekf.state[6] * (1-k) + reading.values[0] * k
      ekf.state[7] = ekf.state[7] * (1-k) + reading.values[1] * k
      ekf.state[8] = ekf.state[8] * (1-k) + reading.values[2] * k
  of Barometer:
    if reading.values.len >= 1:
      let k = 0.6
      ekf.state[2] = ekf.state[2] * (1-k) + reading.values[0] * k
  of Optical:
    discard

proc markSensorFailed(ekf: EKF, sensor: SensorType) =
  ekf.sensor_failed[sensor] = true

proc getNavState(ekf: EKF): NavState =
  NavState(
    x: ekf.state[0], y: ekf.state[1], z: ekf.state[2],
    vx: ekf.state[3], vy: ekf.state[4], vz: ekf.state[5],
    roll: ekf.state[6], pitch: ekf.state[7], yaw: ekf.state[8],
    timestamp: cpuTime()
  )

proc activeSensors(ekf: EKF): seq[SensorType] =
  for s in SensorType:
    if not ekf.sensor_failed.getOrDefault(s, false):
      result.add(s)

# RTScheduler stub for real-time scheduling integration
type
  RTScheduler = ref object
    tasks: seq[proc()]
    period_ms: float

proc newRTScheduler(period_ms: float): RTScheduler =
  RTScheduler(tasks: @[], period_ms: period_ms)

proc addTask(sched: RTScheduler, task: proc()) =
  sched.tasks.add(task)

proc run(sched: RTScheduler, iterations: int) =
  for i in 0..<iterations:
    for task in sched.tasks:
      task()

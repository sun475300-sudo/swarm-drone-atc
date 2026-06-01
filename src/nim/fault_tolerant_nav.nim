# Phase 526 — Fault-Tolerant Navigation with EKF and Sensor Fusion
# Nim module implementing Extended Kalman Filter (EKF) for robust drone navigation.

import math, strformat, sequtils

## Sensor reading from various measurement sources
type
  SensorType* = enum
    GPS, IMU, Barometer, Magnetometer

  SensorReading* = object
    sensorType*: SensorType
    timestamp*: float
    values*: seq[float]   # raw measurement vector
    noise*: float         # measurement noise std dev
    valid*: bool

  ## State vector: [x, y, z, vx, vy, vz]
  StateVector* = object
    x*, y*, z*: float
    vx*, vy*, vz*: float

  ## EKF covariance (simplified diagonal)
  Covariance* = object
    px*, py*, pz*: float
    pvx*, pvy*, pvz*: float

  ## Extended Kalman Filter for drone pose estimation
  EKF* = object
    state*: StateVector
    cov*: Covariance
    processNoise*: float
    dt*: float            # time step in seconds

  ## Sensor fusion result
  FusionResult* = object
    state*: StateVector
    confidence*: float
    activeSensors*: int

  ## Fault detector for individual sensors
  FaultDetector* = object
    threshold*: float
    windowSize*: int
    readings*: seq[float]

  ## Navigation system with fault tolerance
  FaultTolerantNavigator* = object
    ekf*: EKF
    sensors*: seq[SensorReading]
    faultDetectors*: seq[FaultDetector]
    fusionHistory*: seq[FusionResult]
    stepCount*: int

## Initialize EKF with default parameters
proc initEKF*(dt: float = 0.1, processNoise: float = 0.01): EKF =
  result.state = StateVector(x: 0, y: 0, z: 0, vx: 0, vy: 0, vz: 0)
  result.cov = Covariance(px: 1.0, py: 1.0, pz: 1.0, pvx: 0.1, pvy: 0.1, pvz: 0.1)
  result.processNoise = processNoise
  result.dt = dt

## EKF prediction step (constant velocity model)
proc predict*(ekf: var EKF) =
  let dt = ekf.dt
  # State propagation
  ekf.state.x  += ekf.state.vx * dt
  ekf.state.y  += ekf.state.vy * dt
  ekf.state.z  += ekf.state.vz * dt
  # Covariance growth from process noise
  ekf.cov.px   += ekf.processNoise * dt
  ekf.cov.py   += ekf.processNoise * dt
  ekf.cov.pz   += ekf.processNoise * dt
  ekf.cov.pvx  += ekf.processNoise
  ekf.cov.pvy  += ekf.processNoise
  ekf.cov.pvz  += ekf.processNoise

## EKF update with GPS measurement [x, y, z]
proc updateGPS*(ekf: var EKF, measurement: seq[float], noise: float) =
  if measurement.len < 3: return
  let r = noise * noise  # measurement variance
  # Kalman gain for position states
  let kx = ekf.cov.px / (ekf.cov.px + r)
  let ky = ekf.cov.py / (ekf.cov.py + r)
  let kz = ekf.cov.pz / (ekf.cov.pz + r)
  # State update
  ekf.state.x += kx * (measurement[0] - ekf.state.x)
  ekf.state.y += ky * (measurement[1] - ekf.state.y)
  ekf.state.z += kz * (measurement[2] - ekf.state.z)
  # Covariance update
  ekf.cov.px *= (1.0 - kx)
  ekf.cov.py *= (1.0 - ky)
  ekf.cov.pz *= (1.0 - kz)

## EKF update with IMU velocity measurement [vx, vy, vz]
proc updateIMU*(ekf: var EKF, measurement: seq[float], noise: float) =
  if measurement.len < 3: return
  let r = noise * noise
  let kvx = ekf.cov.pvx / (ekf.cov.pvx + r)
  let kvy = ekf.cov.pvy / (ekf.cov.pvy + r)
  let kvz = ekf.cov.pvz / (ekf.cov.pvz + r)
  ekf.state.vx += kvx * (measurement[0] - ekf.state.vx)
  ekf.state.vy += kvy * (measurement[1] - ekf.state.vy)
  ekf.state.vz += kvz * (measurement[2] - ekf.state.vz)
  ekf.cov.pvx *= (1.0 - kvx)
  ekf.cov.pvy *= (1.0 - kvy)
  ekf.cov.pvz *= (1.0 - kvz)

## Initialize fault detector for anomaly detection
proc initFaultDetector*(threshold: float, windowSize: int = 10): FaultDetector =
  FaultDetector(threshold: threshold, windowSize: windowSize, readings: @[])

## Detect if a sensor is faulty based on innovation threshold
proc isFaulty*(fd: var FaultDetector, newReading: float): bool =
  fd.readings.add(newReading)
  if fd.readings.len > fd.windowSize:
    fd.readings = fd.readings[^fd.windowSize .. ^1]
  if fd.readings.len < 2: return false
  let mu = fd.readings.foldl(a + b, 0.0) / float(fd.readings.len)
  let variance = fd.readings.foldl(a + (b - mu) * (b - mu), 0.0) / float(fd.readings.len)
  return sqrt(variance) > fd.threshold

## Create a sensor reading stub
proc makeSensorReading*(t: SensorType, ts: float, vals: seq[float], noise: float): SensorReading =
  SensorReading(sensorType: t, timestamp: ts, values: vals, noise: noise, valid: true)

## Initialize the fault-tolerant navigator
proc initNavigator*(): FaultTolerantNavigator =
  result.ekf = initEKF()
  result.faultDetectors = @[
    initFaultDetector(2.0, 10),  # GPS fault detector
    initFaultDetector(1.0, 10),  # IMU fault detector
    initFaultDetector(5.0, 10)   # Barometer fault detector
  ]
  result.fusionHistory = @[]
  result.stepCount = 0

## Run one navigation step with sensor fusion
proc step*(nav: var FaultTolerantNavigator, readings: seq[SensorReading]): FusionResult =
  nav.ekf.predict()
  var activeSensors = 0
  for reading in readings:
    if not reading.valid: continue
    case reading.sensorType
    of GPS:
      nav.ekf.updateGPS(reading.values, reading.noise)
      activeSensors += 1
    of IMU:
      nav.ekf.updateIMU(reading.values, reading.noise)
      activeSensors += 1
    of Barometer, Magnetometer:
      activeSensors += 1  # simplified fusion
  let conf = float(activeSensors) / 4.0
  result = FusionResult(state: nav.ekf.state, confidence: conf, activeSensors: activeSensors)
  nav.fusionHistory.add(result)
  nav.stepCount += 1

## Print navigation summary
proc summary*(nav: FaultTolerantNavigator): string =
  let avgConf = if nav.fusionHistory.len == 0: 0.0
    else: nav.fusionHistory.foldl(a + b.confidence, 0.0) / float(nav.fusionHistory.len)
  fmt"Phase 526 EKF Nav | Steps: {nav.stepCount} | Avg confidence: {avgConf:.2f}"

when isMainModule:
  var nav = initNavigator()
  for i in 0..9:
    let ts = float(i) * 0.1
    let readings = @[
      makeSensorReading(GPS, ts, @[float(i), 0.0, 50.0], 0.5),
      makeSensorReading(IMU, ts, @[1.0, 0.0, 0.0], 0.1)
    ]
    let r = nav.step(readings)
    echo fmt"Step {i}: pos=({r.state.x:.1f},{r.state.y:.1f},{r.state.z:.1f}) sensors={r.activeSensors}"
  echo nav.summary()

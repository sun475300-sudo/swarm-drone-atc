# Phase 526: Fault-Tolerant Navigation — 드론 내결함성 항법 (Nim)
# EKF-based fault-tolerant navigation with sensor fusion.

import std/[math, random, strformat, tables]

const PHASE* = 526

# ── Sensor types ───────────────────────────────────────────────────

type
  SensorKind* = enum GPS, IMU, Barometer, Magnetometer

  SensorReading* = object
    kind*:  SensorKind
    x*, y*, z*: float64
    valid*: bool
    noise*: float64

  SensorFusion* = object
    weights*: Table[SensorKind, float64]
    readings*: seq[SensorReading]

# ── EKF State ─────────────────────────────────────────────────────

type
  EKFState* = object
    x*, y*, z*: float64     # position
    vx*, vy*, vz*: float64  # velocity
    P*: array[6, float64]   # diagonal covariance

  EKFNavigation* = ref object
    state*: EKFState
    process_noise*: float64
    meas_noise*: float64
    rng*: Rand
    steps*: int
    fault_count*: int

# ── EKF operations ─────────────────────────────────────────────────

proc newEKF*(seed: int64): EKFNavigation =
  result = EKFNavigation(
    state: EKFState(x: 0, y: 0, z: 50, vx: 0, vy: 0, vz: 0,
                    P: [1.0, 1.0, 1.0, 0.1, 0.1, 0.1]),
    process_noise: 0.01,
    meas_noise:    0.5,
    rng:           initRand(seed),
    steps:         0,
    fault_count:   0
  )

proc predict*(ekf: EKFNavigation, dt: float64) =
  ## Predict step: propagate state with constant velocity model.
  ekf.state.x += ekf.state.vx * dt
  ekf.state.y += ekf.state.vy * dt
  ekf.state.z += ekf.state.vz * dt
  # Increase covariance
  for i in 0..5:
    ekf.state.P[i] += ekf.process_noise

proc update*(ekf: EKFNavigation, reading: SensorReading) =
  ## Update step: incorporate sensor measurement.
  if not reading.valid:
    ekf.fault_count += 1
    return
  let K = ekf.state.P[0] / (ekf.state.P[0] + ekf.meas_noise)
  ekf.state.x += K * (reading.x - ekf.state.x)
  ekf.state.y += K * (reading.y - ekf.state.y)
  ekf.state.z += K * (reading.z - ekf.state.z)
  ekf.state.P[0] *= (1.0 - K)
  ekf.state.P[1] *= (1.0 - K)
  ekf.state.P[2] *= (1.0 - K)
  ekf.steps += 1

# ── Sensor generator ───────────────────────────────────────────────

proc generateSensor*(rng: var Rand, kind: SensorKind, true_x, true_y, true_z: float64,
                     fault_prob: float64 = 0.05): SensorReading =
  let faulty = rng.rand(1.0) < fault_prob
  let noise  = rng.rand(1.0) * 2.0 - 1.0
  SensorReading(
    kind:  kind,
    x:     if faulty: true_x + 100.0 else: true_x + noise * 0.5,
    y:     if faulty: true_y + 100.0 else: true_y + noise * 0.5,
    z:     if faulty: true_z + 100.0 else: true_z + noise * 0.3,
    valid: not faulty,
    noise: abs(noise)
  )

# ── Fault-tolerant nav wrapper ────────────────────────────────────

type
  FaultTolerantNav* = ref object
    ekf*:       EKFNavigation
    sensors*:   seq[SensorKind]
    trajectory*: seq[(float64, float64, float64)]
    rng*:       Rand

proc newFaultTolerantNav*(seed: int64): FaultTolerantNav =
  result = FaultTolerantNav(
    ekf:       newEKF(seed),
    sensors:   @[GPS, IMU, Barometer],
    trajectory: @[],
    rng:       initRand(seed)
  )

proc step*(nav: FaultTolerantNav, true_x, true_y, true_z: float64) =
  nav.ekf.predict(0.1)
  for sk in nav.sensors:
    let reading = generateSensor(nav.rng, sk, true_x, true_y, true_z)
    nav.ekf.update(reading)
  nav.trajectory.add((nav.ekf.state.x, nav.ekf.state.y, nav.ekf.state.z))

proc run*(nav: FaultTolerantNav, n_steps: int) =
  for i in 0 ..< n_steps:
    let t = float64(i) * 0.1
    nav.step(t * 2.0, t * 1.5, 50.0 + sin(t) * 5.0)

proc summary*(nav: FaultTolerantNav): string =
  fmt"Phase {PHASE}: EKF steps={nav.ekf.steps} faults={nav.ekf.fault_count} trajectory_len={nav.trajectory.len}"

# ── Entry point ────────────────────────────────────────────────────

when isMainModule:
  echo fmt"Phase {PHASE}: Fault-Tolerant Navigation — EKF 내결함성 항법"
  let nav = newFaultTolerantNav(42)
  nav.run(50)
  echo nav.summary()

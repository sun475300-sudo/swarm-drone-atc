# Phase 526: Nim Fault-Tolerant Navigation — EKF Sensor Fusion
import math, strformat

type
  NavSensor = enum
    GPS, IMU, Vision, Barometer, Magnetometer, Lidar

  NavHealth = enum
    Nominal, Degraded, Failed

  Vec3 = object
    x, y, z: float64

  SensorState = object
    sensor: NavSensor
    health: NavHealth
    position: Vec3
    confidence: float64

  NavSolution = object
    position: Vec3
    velocity: Vec3
    heading: float64
    confidence: float64
    integrity: float64
    sensorsUsed: int

  PRNG = object
    state: uint64

proc initPRNG(seed: uint64): PRNG =
  result.state = seed xor 0x6c62272e07bb0142'u64

proc next(rng: var PRNG): uint64 =
  rng.state = rng.state xor (rng.state shl 13)
  rng.state = rng.state xor (rng.state shr 7)
  rng.state = rng.state xor (rng.state shl 17)
  result = rng.state

proc uniform(rng: var PRNG): float64 =
  float64(rng.next() and 0x7FFFFFFF'u64) / float64(0x7FFFFFFF)

proc normal(rng: var PRNG): float64 =
  let u1 = max(rng.uniform(), 1e-10)
  let u2 = rng.uniform()
  sqrt(-2.0 * ln(u1)) * cos(2.0 * PI * u2)

proc vec3(x, y, z: float64): Vec3 = Vec3(x: x, y: y, z: z)
proc add(a, b: Vec3): Vec3 = vec3(a.x+b.x, a.y+b.y, a.z+b.z)
proc scale(a: Vec3, s: float64): Vec3 = vec3(a.x*s, a.y*s, a.z*s)
proc norm(a: Vec3): float64 = sqrt(a.x*a.x + a.y*a.y + a.z*a.z)

type EKF = object
  pos, vel: Vec3
  pDiag: array[6, float64]

proc initEKF(): EKF =
  result.pos = vec3(0, 0, 50)
  result.vel = vec3(2, 1, 0)
  for i in 0..5: result.pDiag[i] = 10.0

proc predict(ekf: var EKF, dt: float64) =
  ekf.pos = add(ekf.pos, scale(ekf.vel, dt))
  for i in 0..5: ekf.pDiag[i] += 0.01 * dt

proc update(ekf: var EKF, measurement: Vec3, noise: float64) =
  let k = ekf.pDiag[0] / (ekf.pDiag[0] + noise * noise)
  ekf.pos.x += k * (measurement.x - ekf.pos.x)
  ekf.pos.y += k * (measurement.y - ekf.pos.y)
  ekf.pos.z += k * (measurement.z - ekf.pos.z)
  for i in 0..2: ekf.pDiag[i] *= (1.0 - k)

proc simulateSensor(rng: var PRNG, truePos: Vec3, sensor: NavSensor,
                     health: NavHealth): SensorState =
  let noiseMap = [2.0, 0.5, 1.0, 3.0, 5.0, 0.3]  # GPS,IMU,Vision,Baro,Mag,Lidar
  var noise = noiseMap[ord(sensor)]
  if health == Degraded: noise *= 5.0
  elif health == Failed: noise *= 50.0

  let pos = vec3(
    truePos.x + rng.normal() * noise,
    truePos.y + rng.normal() * noise,
    truePos.z + rng.normal() * noise
  )
  let conf = max(0.1, 1.0 - noise / 20.0)
  SensorState(sensor: sensor, health: health, position: pos,
              confidence: if health == Failed: 0.05 else: conf)

proc vote(states: seq[SensorState]): (Vec3, float64) =
  var totalW = 0.0
  var pos = vec3(0, 0, 0)
  var healthy = 0
  for s in states:
    if s.health != Failed:
      pos = add(pos, scale(s.position, s.confidence))
      totalW += s.confidence
      healthy += 1
  if totalW > 0:
    pos = scale(pos, 1.0 / totalW)
  let integrity = if healthy >= 2: 0.95 else: 0.5
  (pos, integrity)

when isMainModule:
  var rng = initPRNG(42)
  var ekf = initEKF()
  var truePos = vec3(0, 0, 50)
  var trueVel = vec3(2, 1, 0)
  let sensorHealths = [Nominal, Nominal, Nominal, Nominal, Nominal, Nominal]
  var totalConf = 0.0

  for step in 0..<100:
    let dt = 0.1
    truePos = add(truePos, scale(trueVel, dt))
    trueVel = add(trueVel, vec3(rng.normal()*0.05, rng.normal()*0.05, rng.normal()*0.01))
    ekf.predict(dt)

    var states: seq[SensorState] = @[]
    for sensor in [GPS, IMU, Vision]:
      let health = sensorHealths[ord(sensor)]
      let s = simulateSensor(rng, truePos, sensor, health)
      states.add(s)
      if health != Failed:
        ekf.update(s.position, if health == Degraded: 10.0 else: 2.0)

    let (votedPos, integrity) = vote(states)
    totalConf += integrity

  echo fmt"Nav steps: 100"
  echo fmt"Final pos: ({ekf.pos.x:.1f}, {ekf.pos.y:.1f}, {ekf.pos.z:.1f})"
  echo fmt"True pos:  ({truePos.x:.1f}, {truePos.y:.1f}, {truePos.z:.1f})"
  echo fmt"Avg integrity: {totalConf / 100.0:.4f}"

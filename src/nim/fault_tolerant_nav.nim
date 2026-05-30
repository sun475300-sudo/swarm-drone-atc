# Phase 526: fault_tolerant_nav — Nim 기반 결함 허용 항법 시스템
# SDACS Fault-Tolerant Navigation with EKF (Extended Kalman Filter)

import math, strformat

# 센서 데이터 구조체
type
  SensorReading = object
    timestamp: float
    gps_lat: float
    gps_lon: float
    gps_alt: float
    barometer_alt: float
    imu_accel_x: float
    imu_accel_y: float
    imu_accel_z: float
    sensor_status: int  # 비트마스크: GPS=1, Baro=2, IMU=4

  Sensor = enum
    GPS, Barometer, IMU

  NavigationState = object
    lat: float
    lon: float
    alt: float
    vel_x: float
    vel_y: float
    vel_z: float
    timestamp: float

# EKF 상태 벡터 (6차원: lat, lon, alt, vx, vy, vz)
type
  EKFState = object
    x: array[6, float]   # 상태 벡터
    P: array[36, float]  # 공분산 행렬 (6x6, 행 우선)

proc initEKF(): EKFState =
  result.x = [0.0, 0.0, 50.0, 0.0, 0.0, 0.0]
  # 단위 행렬 초기화
  for i in 0..5:
    result.P[i * 6 + i] = 1.0

proc ekfPredict(state: var EKFState, dt: float, accel: array[3, float]) =
  ## EKF 예측 단계 (kalman filter predict)
  # 상태 전이: 위치 += 속도*dt, 속도 += 가속도*dt
  state.x[0] += state.x[3] * dt
  state.x[1] += state.x[4] * dt
  state.x[2] += state.x[5] * dt
  state.x[3] += accel[0] * dt
  state.x[4] += accel[1] * dt
  state.x[5] += accel[2] * dt
  # 공분산 증가 (단순화)
  for i in 0..5:
    state.P[i * 6 + i] += 0.01

proc ekfUpdate(state: var EKFState, z_lat, z_lon, z_alt: float) =
  ## EKF 업데이트 단계 (kalman filter update)
  let R = 0.5  # 측정 노이즈
  # GPS 위치 측정
  let y_lat = z_lat - state.x[0]
  let y_lon = z_lon - state.x[1]
  let y_alt = z_alt - state.x[2]
  # 칼만 이득 (단순화)
  let K = state.P[0] / (state.P[0] + R)
  state.x[0] += K * y_lat
  state.x[1] += K * y_lon
  state.x[2] += K * y_alt
  state.P[0] *= (1.0 - K)
  state.P[7] *= (1.0 - K)
  state.P[14] *= (1.0 - K)

# 결함 감지 및 센서 융합
type
  FaultDetector = object
    threshold: float
    fault_counts: array[3, int]

proc initFaultDetector(threshold: float): FaultDetector =
  result.threshold = threshold

proc detectFault(det: var FaultDetector, sensor: Sensor, value, reference: float): bool =
  let residual = abs(value - reference)
  if residual > det.threshold:
    det.fault_counts[ord(sensor)] += 1
    return true
  if det.fault_counts[ord(sensor)] > 0:
    det.fault_counts[ord(sensor)] -= 1
  return false

# 결함 허용 항법 시스템
type
  FaultTolerantNavigator = object
    ekf_state: EKFState
    fault_detector: FaultDetector
    nav_state: NavigationState
    active_sensors: int

proc initNavigator(): FaultTolerantNavigator =
  result.ekf_state = initEKF()
  result.fault_detector = initFaultDetector(5.0)
  result.active_sensors = 7  # 모든 센서 활성화

proc update(nav: var FaultTolerantNavigator, reading: SensorReading) =
  let dt = 0.1
  let accel = [reading.imu_accel_x, reading.imu_accel_y, reading.imu_accel_z - 9.81]
  ekfPredict(nav.ekf_state, dt, accel)

  # GPS 결함 검사
  let gps_fault = detectFault(nav.fault_detector, GPS,
    reading.gps_alt, nav.ekf_state.x[2])
  if not gps_fault and (reading.sensor_status and 1) != 0:
    ekfUpdate(nav.ekf_state, reading.gps_lat, reading.gps_lon, reading.gps_alt)

  nav.nav_state = NavigationState(
    lat: nav.ekf_state.x[0] + 37.5,
    lon: nav.ekf_state.x[1] + 127.0,
    alt: nav.ekf_state.x[2],
    vel_x: nav.ekf_state.x[3],
    vel_y: nav.ekf_state.x[4],
    vel_z: nav.ekf_state.x[5],
    timestamp: reading.timestamp
  )

when isMainModule:
  echo "SDACS Fault-Tolerant Navigation — Phase 526\n"
  echo "EKF 기반 결함 허용 항법 초기화..."

  var nav = initNavigator()

  # 시뮬레이션 센서 데이터
  let readings = [
    SensorReading(timestamp: 0.0, gps_lat: 0.001, gps_lon: 0.001, gps_alt: 50.5,
      barometer_alt: 50.3, imu_accel_x: 0.1, imu_accel_y: 0.0, imu_accel_z: 9.81, sensor_status: 7),
    SensorReading(timestamp: 0.1, gps_lat: 0.002, gps_lon: 0.002, gps_alt: 51.0,
      barometer_alt: 50.8, imu_accel_x: 0.2, imu_accel_y: 0.1, imu_accel_z: 9.82, sensor_status: 7),
    SensorReading(timestamp: 0.2, gps_lat: 0.003, gps_lon: 0.003, gps_alt: 150.0,  # GPS 오류!
      barometer_alt: 51.2, imu_accel_x: 0.1, imu_accel_y: 0.0, imu_accel_z: 9.80, sensor_status: 7),
  ]

  for r in readings:
    nav.update(r)
    echo &"  t={r.timestamp:.1f}s: alt={nav.nav_state.alt:.2f}m vel_z={nav.nav_state.vel_z:.3f}m/s"

  echo &"\n결함 감지 횟수: GPS={nav.fault_detector.fault_counts[0]}"
  echo "결함 허용 항법 완료."

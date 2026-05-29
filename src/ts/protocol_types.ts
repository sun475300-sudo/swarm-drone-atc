/**
 * SDACS 통신 프로토콜 타입 정의
 * ================================
 * 드론 ↔ 관제 ↔ 대시보드 간 메시지 스키마
 *
 * Python protobuf 대안 — TypeScript 타입 안전 보장
 */

// ── 기본 메시지 프레임 ──────────────────────────────────

export interface MessageFrame<T = unknown> {
  version: 1;
  messageId: string;
  sourceId: string;
  targetId: string | "*";  // "*" = broadcast
  timestamp: number;        // Unix ms
  ttl: number;              // hop count
  payload: T;
  checksum: string;         // SHA-256 hex
}

// ── 드론→관제 메시지 ────────────────────────────────────

export interface TelemetryReport {
  type: "TELEMETRY";
  droneId: string;
  position: Vec3;
  velocity: Vec3;
  acceleration: Vec3;
  heading: number;
  batteryPct: number;
  batteryVoltage: number;
  motorRpm: [number, number, number, number];
  gpsFixQuality: number;   // 1-5
  satellites: number;
  temperature: number;
  vibration: Vec3;
  flightMode: "MANUAL" | "AUTO" | "RTL" | "HOVER" | "LAND";
}

export interface StatusReport {
  type: "STATUS";
  droneId: string;
  state: "IDLE" | "PREFLIGHT" | "ARMED" | "TAKEOFF" | "CRUISE" | "APPROACH" | "LANDING" | "FAULT";
  missionId: string | null;
  waypointIndex: number;
  totalWaypoints: number;
  fuelRemaining: number;    // minutes
  payloadKg: number;
  errorCodes: number[];
}

export interface EmergencyReport {
  type: "EMERGENCY";
  droneId: string;
  emergencyType: "ENGINE_FAILURE" | "BATTERY_CRITICAL" | "GPS_LOST" | "COMM_DEGRADED" | "COLLISION_IMMINENT" | "GEOFENCE_BREACH";
  severity: 1 | 2 | 3 | 4 | 5;
  position: Vec3;
  description: string;
}

// ── 관제→드론 명령 ──────────────────────────────────────

export interface NavigationCommand {
  type: "NAV_CMD";
  commandType: "GOTO" | "ORBIT" | "RTL" | "HOLD" | "LAND" | "TAKEOFF";
  targetPosition?: Vec3;
  speed?: number;
  altitude?: number;
  orbitRadius?: number;
  holdDuration?: number;
  priority: number;
}

export interface ResolutionAdvisory {
  type: "RA";
  advisoryId: string;
  droneId: string;
  maneuver: "CLIMB" | "DESCEND" | "TURN_LEFT" | "TURN_RIGHT" | "SPEED_UP" | "SLOW_DOWN" | "HOLD";
  magnitude: number;         // 각도 또는 m/s
  urgency: "PREVENTIVE" | "CORRECTIVE" | "IMMEDIATE";
  conflictDroneId: string;
  expiresAt: number;
}

export interface MissionAssignment {
  type: "MISSION";
  missionId: string;
  droneId: string;
  waypoints: Vec3[];
  speeds: number[];           // 각 구간 속도
  altitudes: number[];
  actions: WaypointAction[];
  deadline: number;           // Unix ms
  priority: number;
}

export interface WaypointAction {
  waypointIndex: number;
  action: "PHOTO" | "VIDEO_START" | "VIDEO_STOP" | "PAYLOAD_DROP" | "HOVER" | "SCAN" | "RELAY";
  params: Record<string, number | string>;
}

// ── 관제 내부 메시지 ────────────────────────────────────

export interface ConflictDetection {
  type: "CONFLICT";
  conflictId: string;
  droneA: string;
  droneB: string;
  cpaDistance: number;
  cpaTime: number;
  positionA: Vec3;
  positionB: Vec3;
  velocityA: Vec3;
  velocityB: Vec3;
  horizontalSep: number;
  verticalSep: number;
  conflictType: "LOSS_OF_SEP" | "POTENTIAL" | "PREDICTED" | "PROXIMATE";
}

export interface AirspaceUpdate {
  type: "AIRSPACE";
  zones: ZoneDefinition[];
  voronoiCells: VoronoiCell[];
  sectorLoads: Record<string, number>;
}

export interface ZoneDefinition {
  zoneId: string;
  zoneType: "NFZ" | "TFR" | "CORRIDOR" | "LANDING" | "RESTRICTED" | "DANGER";
  geometry: "CYLINDER" | "POLYGON" | "BOX";
  center?: Vec3;
  radius?: number;
  vertices?: Vec3[];
  minAlt: number;
  maxAlt: number;
  active: boolean;
  schedule?: { start: number; end: number };
}

export interface VoronoiCell {
  droneId: string;
  vertices: [number, number][];  // 2D polygon
  area: number;
  neighbors: string[];
}

// ── 유틸리티 타입 ───────────────────────────────────────

export type Vec3 = [number, number, number];

export type DroneId = `D${string}`;

export interface Timestamp {
  unix: number;
  iso: string;
}

/** CPA (Closest Point of Approach) 계산 결과 */
export interface CPAResult {
  distance: number;
  timeToClosest: number;
  pointA: Vec3;
  pointB: Vec3;
  horizontalDistance: number;
  verticalDistance: number;
}

/** 시뮬레이션 결과 요약 */
export interface SimulationResult {
  scenarioName: string;
  duration: number;
  droneCount: number;
  totalConflicts: number;
  resolvedConflicts: number;
  collisions: number;
  collisionRate: number;
  resolutionRate: number;
  avgResponseTime: number;
  p50Latency: number;
  p99Latency: number;
  avgBattery: number;
  minSeparation: number;
  energyEfficiency: number;
  slaCompliance: boolean;
}

/** Monte Carlo 결과 집계 */
export interface MonteCarloSummary {
  totalRuns: number;
  configs: number;
  seedsPerConfig: number;
  avgCollisionRate: number;
  maxCollisionRate: number;
  slaPassRate: number;
  confidenceInterval: [number, number];
  worstConfig: string;
  bestConfig: string;
}

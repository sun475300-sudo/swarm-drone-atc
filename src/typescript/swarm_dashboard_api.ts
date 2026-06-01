// Swarm Dashboard API — TypeScript REST API types and request handlers
// Phase 611: TypeScript type definitions for the swarm monitoring dashboard API.

// ===== Core Domain Types =====

export interface DroneStatus {
  droneId: string;
  status: 'active' | 'idle' | 'returning' | 'error' | 'offline';
  battery: number;
  altitude: number;
  position: { x: number; y: number; z: number };
  speed: number;
  heading: number;
  missionId: string | null;
  lastSeen: string;
}

export interface FleetSummary {
  totalDrones: number;
  activeDrones: number;
  idleDrones: number;
  errorDrones: number;
  avgBattery: number;
  activeMissions: number;
  timestamp: string;
}

export interface MissionData {
  missionId: string;
  name: string;
  status: 'pending' | 'active' | 'complete' | 'aborted';
  assignedDrones: string[];
  progress: number;  // 0-100
  startTime: string | null;
  endTime: string | null;
  waypoints: Array<{ x: number; y: number; z: number }>;
}

export interface TelemetryRecord {
  droneId: string;
  timestamp: string;
  x: number;
  y: number;
  z: number;
  vx: number;
  vy: number;
  vz: number;
  battery: number;
  signalRssi: number;
  temperature: number;
}

export interface AlertRecord {
  alertId: string;
  droneId: string;
  alertType: 'collision_risk' | 'low_battery' | 'geofence' | 'signal_loss' | 'hardware_fault';
  severity: 'info' | 'warning' | 'critical';
  message: string;
  timestamp: string;
  resolved: boolean;
}

// ===== API Request/Response Types =====

export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error: string | null;
  timestamp: string;
  requestId: string;
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  total: number;
  page: number;
  limit: number;
}

export interface CommandRequest {
  droneId: string;
  commandType: 'move' | 'hover' | 'land' | 'rtl' | 'emergency_stop' | 'set_altitude';
  parameters: Record<string, number | string>;
  priority: 'low' | 'normal' | 'high' | 'emergency';
}

export interface CommandResponse {
  commandId: string;
  droneId: string;
  accepted: boolean;
  estimatedExecutionTime: number;
  rejectionReason?: string;
}

// ===== Dashboard Metrics =====

export interface DashboardMetrics {
  fleet: FleetSummary;
  recentAlerts: AlertRecord[];
  performanceKPIs: {
    missionSuccessRate: number;
    avgResponseTime: number;
    collisionsPrevented: number;
    geofenceViolations: number;
    uptimePercent: number;
  };
  systemHealth: {
    controllerLoad: number;
    networkLatency: number;
    dataIngestionRate: number;
    storageUsed: number;
  };
}

// ===== API Endpoint Definitions =====

export interface SwarmDashboardEndpoints {
  // Drone fleet endpoints
  'GET /api/v1/drones': () => Promise<PaginatedResponse<DroneStatus>>;
  'GET /api/v1/drones/:id': (id: string) => Promise<ApiResponse<DroneStatus>>;
  'GET /api/v1/drones/:id/telemetry': (id: string) => Promise<PaginatedResponse<TelemetryRecord>>;

  // Mission endpoints
  'GET /api/v1/missions': () => Promise<PaginatedResponse<MissionData>>;
  'POST /api/v1/missions': (data: Partial<MissionData>) => Promise<ApiResponse<MissionData>>;
  'PUT /api/v1/missions/:id': (id: string, data: Partial<MissionData>) => Promise<ApiResponse<MissionData>>;

  // Alert endpoints
  'GET /api/v1/alerts': () => Promise<PaginatedResponse<AlertRecord>>;
  'PUT /api/v1/alerts/:id/resolve': (id: string) => Promise<ApiResponse<AlertRecord>>;

  // Command endpoints
  'POST /api/v1/commands': (cmd: CommandRequest) => Promise<ApiResponse<CommandResponse>>;

  // Dashboard endpoint
  'GET /api/v1/dashboard': () => Promise<ApiResponse<DashboardMetrics>>;
}

// ===== Helper Utilities =====

export function createApiResponse<T>(data: T, requestId: string): ApiResponse<T> {
  return {
    success: true,
    data,
    error: null,
    timestamp: new Date().toISOString(),
    requestId,
  };
}

export function createErrorResponse(error: string, requestId: string): ApiResponse<null> {
  return {
    success: false,
    data: null,
    error,
    timestamp: new Date().toISOString(),
    requestId,
  };
}

export function createPaginatedResponse<T>(
  items: T[],
  total: number,
  page: number,
  limit: number,
  requestId: string
): PaginatedResponse<T> {
  return {
    success: true,
    data: items,
    error: null,
    timestamp: new Date().toISOString(),
    requestId,
    total,
    page,
    limit,
  };
}

console.log('Swarm Dashboard API types loaded successfully.');

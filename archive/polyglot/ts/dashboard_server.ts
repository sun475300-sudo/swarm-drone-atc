/**
 * SDACS 실시간 대시보드 WebSocket 서버
 * ==========================================
 * Python 시뮬레이터 → WebSocket → React 3D 프론트엔드
 *
 * 기능:
 *   - 드론 위치/상태 실시간 브로드캐스트
 *   - 충돌 경보 이벤트 스트림
 *   - KPI 집계 및 히스토리
 *   - 클라이언트 구독/필터링
 *
 * Usage:
 *   npx ts-node src/ts/dashboard_server.ts
 */

// ── 타입 정의 ───────────────────────────────────────────

export interface DroneState {
  droneId: string;
  position: [number, number, number];
  velocity: [number, number, number];
  heading: number;
  batteryPct: number;
  status: "FLYING" | "HOVERING" | "LANDING" | "GROUNDED" | "EMERGENCY";
  timestamp: number;
}

export interface CollisionAlert {
  alertId: string;
  droneA: string;
  droneB: string;
  cpaDistance: number;
  cpaTime: number;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  advisoryType: "CLIMB" | "DESCEND" | "TURN_LEFT" | "TURN_RIGHT" | "HOLD" | "SPEED_UP" | "SLOW_DOWN";
  timestamp: number;
}

export interface KPISnapshot {
  activeDrones: number;
  totalConflicts: number;
  resolvedConflicts: number;
  collisionRate: number;
  avgBattery: number;
  throughput: number;
  p50Latency: number;
  p99Latency: number;
  timestamp: number;
}

export interface AirspaceZone {
  zoneId: string;
  type: "NFZ" | "RESTRICTED" | "CORRIDOR" | "LANDING";
  bounds: { min: [number, number, number]; max: [number, number, number] };
  active: boolean;
}

export type MessageType =
  | { type: "drone_update"; payload: DroneState[] }
  | { type: "collision_alert"; payload: CollisionAlert }
  | { type: "kpi_snapshot"; payload: KPISnapshot }
  | { type: "zone_update"; payload: AirspaceZone[] }
  | { type: "subscribe"; payload: { channels: string[] } }
  | { type: "ping"; payload: {} };

// ── 서버 구현 ───────────────────────────────────────────

interface Client {
  id: string;
  channels: Set<string>;
  send: (data: string) => void;
  lastPing: number;
}

class DashboardServer {
  private clients: Map<string, Client> = new Map();
  private kpiHistory: KPISnapshot[] = [];
  private droneStates: Map<string, DroneState> = new Map();
  private activeAlerts: CollisionAlert[] = [];
  private zones: AirspaceZone[] = [];
  private broadcastInterval: ReturnType<typeof setInterval> | null = null;

  constructor(private maxHistorySize: number = 1000) {}

  /** 클라이언트 등록 */
  addClient(clientId: string, sendFn: (data: string) => void): void {
    this.clients.set(clientId, {
      id: clientId,
      channels: new Set(["drone_update", "collision_alert", "kpi_snapshot"]),
      send: sendFn,
      lastPing: Date.now(),
    });
    // 초기 상태 전송
    const initMsg: MessageType = {
      type: "drone_update",
      payload: Array.from(this.droneStates.values()),
    };
    sendFn(JSON.stringify(initMsg));
  }

  /** 클라이언트 제거 */
  removeClient(clientId: string): void {
    this.clients.delete(clientId);
  }

  /** 채널 구독 업데이트 */
  updateSubscription(clientId: string, channels: string[]): void {
    const client = this.clients.get(clientId);
    if (client) {
      client.channels = new Set(channels);
    }
  }

  /** 드론 상태 수신 (Python 시뮬레이터에서) */
  ingestDroneStates(states: DroneState[]): void {
    for (const state of states) {
      this.droneStates.set(state.droneId, state);
    }
    this.broadcast({ type: "drone_update", payload: states });
  }

  /** 충돌 경보 수신 */
  ingestAlert(alert: CollisionAlert): void {
    this.activeAlerts.push(alert);
    if (this.activeAlerts.length > 100) {
      this.activeAlerts = this.activeAlerts.slice(-100);
    }
    this.broadcast({ type: "collision_alert", payload: alert });
  }

  /** KPI 스냅샷 수신 */
  ingestKPI(kpi: KPISnapshot): void {
    this.kpiHistory.push(kpi);
    if (this.kpiHistory.length > this.maxHistorySize) {
      this.kpiHistory = this.kpiHistory.slice(-this.maxHistorySize);
    }
    this.broadcast({ type: "kpi_snapshot", payload: kpi });
  }

  /** 공역 존 업데이트 */
  updateZones(zones: AirspaceZone[]): void {
    this.zones = zones;
    this.broadcast({ type: "zone_update", payload: zones });
  }

  /** 채널 기반 브로드캐스트 */
  private broadcast(msg: MessageType): void {
    const data = JSON.stringify(msg);
    for (const client of this.clients.values()) {
      if (client.channels.has(msg.type)) {
        try {
          client.send(data);
        } catch {
          this.removeClient(client.id);
        }
      }
    }
  }

  /** 메시지 수신 처리 */
  handleMessage(clientId: string, raw: string): void {
    try {
      const msg = JSON.parse(raw) as MessageType;
      switch (msg.type) {
        case "subscribe":
          this.updateSubscription(clientId, msg.payload.channels);
          break;
        case "ping": {
          const client = this.clients.get(clientId);
          if (client) {
            client.lastPing = Date.now();
            client.send(JSON.stringify({ type: "pong", payload: {} }));
          }
          break;
        }
      }
    } catch {
      // ignore malformed messages
    }
  }

  /** 비활성 클라이언트 정리 (30초 타임아웃) */
  pruneStaleClients(timeoutMs: number = 30000): number {
    const now = Date.now();
    let pruned = 0;
    for (const [id, client] of this.clients) {
      if (now - client.lastPing > timeoutMs) {
        this.clients.delete(id);
        pruned++;
      }
    }
    return pruned;
  }

  /** 서버 통계 */
  stats(): {
    clients: number;
    drones: number;
    alerts: number;
    kpiPoints: number;
    zones: number;
  } {
    return {
      clients: this.clients.size,
      drones: this.droneStates.size,
      alerts: this.activeAlerts.length,
      kpiPoints: this.kpiHistory.length,
      zones: this.zones.length,
    };
  }
}

// ── React 3D 프론트엔드 타입 정의 ───────────────────────

/** Three.js 씬 설정 */
export interface Scene3DConfig {
  airspaceSize: [number, number, number];  // x, y, z 범위
  gridSpacing: number;
  backgroundColor: string;
  ambientLightIntensity: number;
  cameraPosition: [number, number, number];
  cameraTarget: [number, number, number];
  enableShadows: boolean;
  maxVisibleDrones: number;
}

/** 드론 3D 렌더링 옵션 */
export interface DroneRenderOptions {
  modelType: "arrow" | "quad" | "fixed_wing" | "custom";
  colorByStatus: Record<DroneState["status"], string>;
  trailLength: number;          // 궤적 포인트 수
  trailOpacity: number;
  labelVisible: boolean;
  scaleByAltitude: boolean;
  collisionRadiusVisible: boolean;
}

/** 히트맵 오버레이 설정 */
export interface HeatmapConfig {
  resolution: number;           // 그리드 해상도
  opacity: number;
  colorScale: "density" | "risk" | "battery" | "speed";
  altitudeSlice: number;        // 표시 고도
  updateIntervalMs: number;
}

/** 대시보드 패널 레이아웃 */
export interface DashboardLayout {
  panels: Array<{
    id: string;
    type: "3d_view" | "kpi_chart" | "alert_log" | "drone_table" | "zone_map" | "battery_gauge";
    position: { x: number; y: number; w: number; h: number };
    config: Record<string, unknown>;
  }>;
  theme: "dark" | "light" | "blue";
  refreshRateMs: number;
}

/** 사용자 인터랙션 이벤트 */
export type UserAction =
  | { action: "select_drone"; droneId: string }
  | { action: "pan_camera"; delta: [number, number] }
  | { action: "zoom"; level: number }
  | { action: "toggle_layer"; layer: string; visible: boolean }
  | { action: "filter_status"; statuses: DroneState["status"][] }
  | { action: "time_travel"; timestamp: number }
  | { action: "trigger_scenario"; scenarioId: string };

export default DashboardServer;

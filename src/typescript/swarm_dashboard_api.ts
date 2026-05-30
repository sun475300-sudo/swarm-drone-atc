// Phase 611: swarm_dashboard_api — TypeScript 기반 스웜 대시보드 API
// SDACS Swarm Dashboard API Types and Client

export interface DroneStatus {
  droneId: number;
  lat: number;
  lon: number;
  alt: number;
  battery: number;
  speed: number;
  flightMode: string;
  isArmed: boolean;
  timestamp: number;
}

export interface ConflictAlert {
  droneId1: number;
  droneId2: number;
  separation: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  timestamp: number;
}

export interface AirspaceSnapshot {
  drones: DroneStatus[];
  conflicts: ConflictAlert[];
  totalDrones: number;
  activeDrones: number;
  conflictCount: number;
  resolutionRate: number;
  timestamp: number;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error: string | null;
  meta?: { total?: number; page?: number; limit?: number };
}

export interface DroneCommand {
  droneId: number;
  command: 'TAKEOFF' | 'LAND' | 'GOTO' | 'RTL' | 'HOLD' | 'ARM' | 'DISARM';
  params?: Record<string, number | string>;
}

// API 클라이언트 클래스
export class SwarmDashboardApiClient {
  private baseUrl: string;
  private wsUrl: string;
  private ws: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private destroyed = false;

  constructor(baseUrl: string, wsUrl: string) {
    this.baseUrl = baseUrl;
    this.wsUrl = wsUrl;
  }

  // 공역 스냅샷 조회
  async getSnapshot(): Promise<ApiResponse<AirspaceSnapshot>> {
    const res = await fetch(`${this.baseUrl}/api/airspace/snapshot`, {
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) {
      return { success: false, data: null, error: `HTTP ${res.status}` };
    }
    return res.json();
  }

  // 드론 명령 전송
  async sendCommand(cmd: DroneCommand): Promise<ApiResponse<{ queued: boolean }>> {
    const res = await fetch(
      `${this.baseUrl}/api/drones/${cmd.droneId}/command`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd.command, params: cmd.params }),
        signal: AbortSignal.timeout(5000),
      }
    );
    if (!res.ok) {
      return { success: false, data: null, error: `HTTP ${res.status}` };
    }
    return res.json();
  }

  // WebSocket 실시간 연결
  connectWebSocket(
    onSnapshot: (snap: AirspaceSnapshot) => void,
    onError?: (err: Event) => void
  ): void {
    if (this.destroyed) return;
    this.ws = new WebSocket(this.wsUrl);

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const snap = JSON.parse(event.data as string) as AirspaceSnapshot;
        onSnapshot(snap);
      } catch (e) {
        console.error('WebSocket parse error:', e);
      }
    };

    this.ws.onerror = (err: Event) => {
      onError?.(err);
    };

    this.ws.onclose = () => {
      if (!this.destroyed) {
        this.reconnectTimer = setTimeout(() => this.connectWebSocket(onSnapshot, onError), 3000);
      }
    };
  }

  // 연결 정리
  destroy(): void {
    this.destroyed = true;
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
  }
}

// Prometheus 메트릭 파서
export function parsePrometheusMetrics(text: string): Map<string, number> {
  const metrics = new Map<string, number>();
  const lines = text.split('\n');
  for (const line of lines) {
    if (line.startsWith('#') || !line.trim()) continue;
    const match = line.match(/^(\w+)(?:\{[^}]*\})?\s+([\d.e+-]+)/);
    if (match) {
      metrics.set(match[1], parseFloat(match[2]));
    }
  }
  return metrics;
}

// 사용 예시 (Phase 611)
const client = new SwarmDashboardApiClient(
  'http://localhost:8080',
  'ws://localhost:8765'
);
console.log('SDACS Swarm Dashboard API Client — Phase 611');
console.log('Client initialized:', client !== null);

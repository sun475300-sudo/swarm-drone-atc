// SDACS Swarm Dashboard API — TypeScript (Phase 611)
// 드론 군집 대시보드 REST/WebSocket API 정의

export interface DroneData {
  id: string;
  x: number;
  y: number;
  z: number;
  vx: number;
  vy: number;
  vz: number;
  battery: number;
  state: 'IDLE' | 'FLYING' | 'HOVERING' | 'LANDING' | 'EMERGENCY';
  timestamp: number;
}

export interface FleetSnapshot {
  timestamp: number;
  drones: DroneData[];
  conflicts: ConflictEvent[];
  stats: FleetStats;
}

export interface ConflictEvent {
  id: string;
  droneA: string;
  droneB: string;
  distance: number;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  resolvedAt?: number;
}

export interface FleetStats {
  total: number;
  active: number;
  lowBattery: number;
  avgAltitude: number;
  avgBattery: number;
  conflictsActive: number;
}

// API 응답 래퍼
export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error?: string;
  meta?: { total?: number; page?: number };
}

// 대시보드 API 서비스
export class DashboardApiService {
  private drones = new Map<string, DroneData>();
  private conflicts = new Map<string, ConflictEvent>();
  private history: FleetSnapshot[] = [];
  private readonly maxHistory = 1000;

  updateDrone(data: DroneData): void {
    this.drones.set(data.id, { ...data, timestamp: Date.now() });
  }

  addConflict(event: ConflictEvent): void {
    this.conflicts.set(event.id, event);
  }

  resolveConflict(id: string): void {
    const c = this.conflicts.get(id);
    if (c) {
      this.conflicts.set(id, { ...c, resolvedAt: Date.now() });
    }
  }

  getSnapshot(): FleetSnapshot {
    const drones = [...this.drones.values()];
    const activeConflicts = [...this.conflicts.values()].filter((c) => !c.resolvedAt);
    const stats = this.computeStats(drones, activeConflicts);
    const snap: FleetSnapshot = { timestamp: Date.now(), drones, conflicts: activeConflicts, stats };
    this.history.push(snap);
    if (this.history.length > this.maxHistory) this.history.shift();
    return snap;
  }

  private computeStats(drones: DroneData[], conflicts: ConflictEvent[]): FleetStats {
    const active = drones.filter((d) => d.state === 'FLYING' || d.state === 'HOVERING');
    const lowBat = drones.filter((d) => d.battery < 20);
    const avgAlt = drones.length ? drones.reduce((s, d) => s + d.z, 0) / drones.length : 0;
    const avgBat = drones.length ? drones.reduce((s, d) => s + d.battery, 0) / drones.length : 0;
    return { total: drones.length, active: active.length, lowBattery: lowBat.length, avgAltitude: avgAlt, avgBattery: avgBat, conflictsActive: conflicts.length };
  }

  getDrone(id: string): ApiResponse<DroneData> {
    const d = this.drones.get(id);
    return d ? { success: true, data: d } : { success: false, data: null, error: 'Not found' };
  }

  listDrones(): ApiResponse<DroneData[]> {
    return { success: true, data: [...this.drones.values()], meta: { total: this.drones.size } };
  }

  historyLength(): number { return this.history.length; }
  droneCount(): number { return this.drones.size; }
}

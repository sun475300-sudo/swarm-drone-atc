// Phase 611 — TypeScript Swarm Dashboard API
// REST API client for SDACS real-time swarm monitoring

export interface DroneState {
  id: string;
  position: [number, number, number];
  batteryPct: number;
  flightPhase: string;
  velocity: [number, number, number];
}

export interface SwarmMetrics {
  totalDrones: number;
  activeDrones: number;
  collisionCount: number;
  conflictResolutionRate: number;
}

export class SwarmDashboardApi {
  private readonly baseUrl: string;

  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  async getDroneStates(): Promise<DroneState[]> {
    const resp = await fetch(`${this.baseUrl}/api/drones`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
  }

  async getMetrics(): Promise<SwarmMetrics> {
    const resp = await fetch(`${this.baseUrl}/api/metrics`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
  }

  async runScenario(scenario: string, duration: number): Promise<Record<string, unknown>> {
    const resp = await fetch(`${this.baseUrl}/api/scenario`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario, duration }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
  }

  subscribeToTelemetry(onUpdate: (state: DroneState[]) => void): WebSocket {
    const ws = new WebSocket(`ws://${this.baseUrl.replace(/^https?:\/\//, '')}/ws/telemetry`);
    ws.onmessage = (evt) => onUpdate(JSON.parse(evt.data));
    return ws;
  }
}

export default SwarmDashboardApi;

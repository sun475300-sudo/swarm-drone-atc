// swarm_dashboard_api.ts - TypeScript API client for SDACS dashboard
import type { DroneState, TelemetryFrame, ConflictEvent } from "./types";

export interface ApiConfig {
  baseUrl: string;
  timeout: number;
  authToken?: string;
}

export interface SwarmSnapshot {
  drones: DroneState[];
  conflicts: number;
  timestamp: string;
}

export class SwarmDashboardApi {
  private config: ApiConfig;

  constructor(config: ApiConfig) {
    this.config = config;
  }

  async getSnapshot(): Promise<SwarmSnapshot> {
    const resp = await fetch(`${this.config.baseUrl}/api/v1/snapshot`);
    return resp.json();
  }

  async getTelemetry(droneId: string): Promise<TelemetryFrame[]> {
    const resp = await fetch(`${this.config.baseUrl}/api/v1/telemetry/${droneId}`);
    return resp.json();
  }

  async getConflicts(): Promise<ConflictEvent[]> {
    const resp = await fetch(`${this.config.baseUrl}/api/v1/conflicts`);
    return resp.json();
  }
}

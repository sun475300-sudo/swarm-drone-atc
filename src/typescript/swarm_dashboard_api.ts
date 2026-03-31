// Phase 611: Swarm Dashboard API — Express + WebSocket
// 실시간 대시보드 REST API

interface DroneStatus {
  id: string;
  position: { x: number; y: number; z: number };
  velocity: { vx: number; vy: number; vz: number };
  battery: number;
  state: "idle" | "flying" | "avoiding" | "landing" | "emergency";
}

interface ConflictAlert {
  droneA: string;
  droneB: string;
  cpa_distance: number;
  cpa_time: number;
  severity: "low" | "medium" | "high" | "critical";
}

interface Advisory {
  drone_id: string;
  type: "CLIMB" | "DESCEND" | "TURN_LEFT" | "TURN_RIGHT" | "EVADE_APF" | "HOLD";
  issued_at: number;
}

class DashboardState {
  drones: Map<string, DroneStatus> = new Map();
  conflicts: ConflictAlert[] = [];
  advisories: Advisory[] = [];
  tickCount: number = 0;

  updateDrone(status: DroneStatus): void {
    this.drones.set(status.id, status);
  }

  addConflict(alert: ConflictAlert): void {
    this.conflicts.push(alert);
    if (this.conflicts.length > 100) {
      this.conflicts = this.conflicts.slice(-50);
    }
  }

  addAdvisory(adv: Advisory): void {
    this.advisories.push(adv);
  }

  getActiveDrones(): DroneStatus[] {
    return Array.from(this.drones.values()).filter(
      (d) => d.state !== "idle"
    );
  }

  getSummary(): {
    total: number;
    active: number;
    conflicts: number;
    advisories: number;
  } {
    return {
      total: this.drones.size,
      active: this.getActiveDrones().length,
      conflicts: this.conflicts.length,
      advisories: this.advisories.length,
    };
  }
}

// API Route Handlers
class SwarmDashboardAPI {
  private state: DashboardState;

  constructor() {
    this.state = new DashboardState();
  }

  handleGetStatus(): { status: string; summary: ReturnType<DashboardState["getSummary"]> } {
    return {
      status: "ok",
      summary: this.state.getSummary(),
    };
  }

  handleGetDrones(): DroneStatus[] {
    return Array.from(this.state.drones.values());
  }

  handleGetConflicts(): ConflictAlert[] {
    return this.state.conflicts;
  }

  handlePostUpdate(data: DroneStatus): void {
    this.state.updateDrone(data);
    this.state.tickCount++;
  }

  handleWebSocketMessage(msg: string): string {
    const parsed = JSON.parse(msg);
    if (parsed.type === "subscribe") {
      return JSON.stringify({ type: "ack", channel: parsed.channel });
    }
    if (parsed.type === "drone_update") {
      this.state.updateDrone(parsed.data);
      return JSON.stringify({ type: "updated", id: parsed.data.id });
    }
    return JSON.stringify({ type: "error", message: "unknown type" });
  }
}

export { SwarmDashboardAPI, DashboardState, DroneStatus, ConflictAlert, Advisory };

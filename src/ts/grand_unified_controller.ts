// Phase 500: Grand Unified Controller (TypeScript)
// 전체 시스템 통합 오케스트레이터, 타입 안전 이벤트 버스

export enum SystemModule {
  FlightControl = "flight_control",
  PathPlanning = "path_planning",
  CollisionAvoid = "collision_avoidance",
  Communication = "communication",
  Weather = "weather",
  Battery = "battery",
  Mission = "mission",
  Defense = "defense",
  Compliance = "compliance",
  Telemetry = "telemetry",
  AIDecision = "ai_decision",
  SwarmCoord = "swarm_coordination",
}

export enum SystemState {
  Nominal = "nominal",
  Degraded = "degraded",
  Emergency = "emergency",
  Shutdown = "shutdown",
}

export enum Priority {
  Safety = 0,
  Mission = 1,
  Efficiency = 2,
  Comfort = 3,
}

export interface ModuleStatus {
  module: SystemModule;
  health: number;
  latencyMs: number;
  lastUpdate: number;
  active: boolean;
  errorCount: number;
}

export interface SystemEvent {
  eventId: string;
  source: SystemModule;
  priority: Priority;
  message: string;
  timestamp: number;
  data: Record<string, unknown>;
}

export interface ControlDecision {
  decisionId: string;
  affectedDrones: string[];
  action: string;
  priority: Priority;
  reason: string;
  timestamp: number;
}

export interface DroneState {
  position: [number, number, number];
  velocity: [number, number, number];
  battery: number;
  status: string;
  mission: string | null;
}

type EventHandler = (event: SystemEvent) => void;

class PRNG {
  private state: number;
  constructor(seed: number) {
    this.state = seed;
  }
  next(): number {
    this.state = (this.state * 1103515245 + 12345) & 0x7fffffff;
    return this.state / 0x7fffffff;
  }
  gaussian(): number {
    const u1 = Math.max(this.next(), 1e-10);
    const u2 = this.next();
    return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
  }
}

export class EventBus {
  private handlers: Map<SystemModule, EventHandler[]> = new Map();

  subscribe(module: SystemModule, handler: EventHandler): void {
    if (!this.handlers.has(module)) this.handlers.set(module, []);
    this.handlers.get(module)!.push(handler);
  }

  publish(event: SystemEvent): void {
    const handlers = this.handlers.get(event.source) ?? [];
    handlers.forEach((h) => h(event));
    // Also notify global listeners
    const global = this.handlers.get(SystemModule.Telemetry) ?? [];
    if (event.source !== SystemModule.Telemetry) {
      global.forEach((h) => h(event));
    }
  }
}

export class GrandUnifiedController {
  readonly nDrones: number;
  private rng: PRNG;
  private modules: Map<SystemModule, ModuleStatus> = new Map();
  private droneStates: Map<string, DroneState> = new Map();
  private eventLog: SystemEvent[] = [];
  private decisions: ControlDecision[] = [];
  private eventBus: EventBus = new EventBus();
  private time = 0;
  private eventCounter = 0;
  private decisionCounter = 0;
  state: SystemState = SystemState.Nominal;

  constructor(nDrones: number = 20, seed: number = 42) {
    this.nDrones = nDrones;
    this.rng = new PRNG(seed);

    for (const mod of Object.values(SystemModule)) {
      this.modules.set(mod, {
        module: mod,
        health: 1.0,
        latencyMs: this.rng.next() * 10 + 1,
        lastUpdate: 0,
        active: true,
        errorCount: 0,
      });
    }

    for (let i = 0; i < nDrones; i++) {
      const id = `drone_${String(i).padStart(3, "0")}`;
      this.droneStates.set(id, {
        position: [
          (this.rng.next() - 0.5) * 200,
          (this.rng.next() - 0.5) * 200,
          this.rng.next() * 40 + 10,
        ],
        velocity: [0, 0, 0],
        battery: 60 + this.rng.next() * 40,
        status: "nominal",
        mission: null,
      });
    }
  }

  private emitEvent(
    source: SystemModule,
    priority: Priority,
    message: string,
    data: Record<string, unknown> = {}
  ): SystemEvent {
    this.eventCounter++;
    const event: SystemEvent = {
      eventId: `EVT-${String(this.eventCounter).padStart(6, "0")}`,
      source,
      priority,
      message,
      timestamp: this.time,
      data,
    };
    this.eventLog.push(event);
    this.eventBus.publish(event);
    return event;
  }

  private makeDecision(
    drones: string[],
    action: string,
    priority: Priority,
    reason: string
  ): ControlDecision {
    this.decisionCounter++;
    const decision: ControlDecision = {
      decisionId: `DEC-${String(this.decisionCounter).padStart(6, "0")}`,
      affectedDrones: drones,
      action,
      priority,
      reason,
      timestamp: this.time,
    };
    this.decisions.push(decision);
    return decision;
  }

  private assessState(): SystemState {
    const healths = [...this.modules.values()]
      .filter((m) => m.active)
      .map((m) => m.health);
    if (healths.length === 0) return SystemState.Shutdown;

    const avg = healths.reduce((a, b) => a + b, 0) / healths.length;
    const minH = Math.min(...healths);

    const criticalModules: SystemModule[] = [
      SystemModule.FlightControl,
      SystemModule.CollisionAvoid,
      SystemModule.Communication,
    ];
    const criticalDown = criticalModules.some(
      (m) => (this.modules.get(m)?.health ?? 1) < 0.3
    );

    if (criticalDown || minH < 0.1) return SystemState.Emergency;
    if (avg < 0.6 || minH < 0.3) return SystemState.Degraded;
    return SystemState.Nominal;
  }

  private safetyChecks(): ControlDecision[] {
    const decisions: ControlDecision[] = [];
    for (const [id, state] of this.droneStates) {
      if (state.battery < 15) {
        decisions.push(
          this.makeDecision(
            [id],
            "RETURN_TO_HOME",
            Priority.Safety,
            `Battery critical: ${state.battery.toFixed(0)}%`
          )
        );
      }
      const dist = Math.sqrt(
        state.position[0] ** 2 + state.position[1] ** 2
      );
      if (dist > 3000) {
        decisions.push(
          this.makeDecision(
            [id],
            "GEOFENCE_RETURN",
            Priority.Safety,
            `Outside geofence: ${dist.toFixed(0)}m`
          )
        );
      }
    }
    return decisions;
  }

  private proximityChecks(): ControlDecision[] {
    const decisions: ControlDecision[] = [];
    const drones = [...this.droneStates.entries()];
    for (let i = 0; i < drones.length; i++) {
      for (let j = i + 1; j < drones.length; j++) {
        const p1 = drones[i][1].position;
        const p2 = drones[j][1].position;
        const dist = Math.sqrt(
          (p1[0] - p2[0]) ** 2 +
            (p1[1] - p2[1]) ** 2 +
            (p1[2] - p2[2]) ** 2
        );
        if (dist < 5.0) {
          decisions.push(
            this.makeDecision(
              [drones[i][0], drones[j][0]],
              "SEPARATION_INCREASE",
              Priority.Safety,
              `Proximity alert: ${dist.toFixed(1)}m`
            )
          );
        }
      }
    }
    return decisions;
  }

  tick(dt: number = 1.0): {
    time: number;
    state: string;
    safetyDecisions: number;
    proximityDecisions: number;
  } {
    this.time += dt;

    // Update modules
    for (const ms of this.modules.values()) {
      ms.health = Math.max(0, Math.min(1, ms.health + this.rng.gaussian() * 0.01));
      ms.latencyMs = Math.max(0.5, ms.latencyMs + this.rng.gaussian() * 0.5);
    }

    // Update drones
    for (const state of this.droneStates.values()) {
      state.battery -= this.rng.next() * 0.04 + 0.01;
      for (let k = 0; k < 3; k++) {
        state.position[k] += this.rng.gaussian() * 0.5;
      }
    }

    const oldState = this.state;
    this.state = this.assessState();
    if (this.state !== oldState) {
      this.emitEvent(
        SystemModule.FlightControl,
        Priority.Safety,
        `System state: ${oldState} → ${this.state}`
      );
    }

    const safety = this.safetyChecks();
    const proximity = this.proximityChecks();

    return {
      time: Math.round(this.time * 10) / 10,
      state: this.state,
      safetyDecisions: safety.length,
      proximityDecisions: proximity.length,
    };
  }

  run(
    duration: number = 60,
    dt: number = 1.0
  ): { stateDist: Record<string, number>; totalDecisions: number; totalEvents: number } {
    const stateDist: Record<string, number> = {};
    for (const s of Object.values(SystemState)) stateDist[s] = 0;
    let totalDecisions = 0;

    const steps = Math.floor(duration / dt);
    for (let i = 0; i < steps; i++) {
      const info = this.tick(dt);
      stateDist[this.state] = (stateDist[this.state] ?? 0) + 1;
      totalDecisions += info.safetyDecisions + info.proximityDecisions;
    }

    return { stateDist, totalDecisions, totalEvents: this.eventLog.length };
  }

  summary(): Record<string, unknown> {
    const avgHealth =
      [...this.modules.values()].reduce((a, m) => a + m.health, 0) /
      this.modules.size;
    return {
      state: this.state,
      drones: this.nDrones,
      modules: this.modules.size,
      avgModuleHealth: Math.round(avgHealth * 10000) / 10000,
      totalEvents: this.eventLog.length,
      totalDecisions: this.decisions.length,
    };
  }
}

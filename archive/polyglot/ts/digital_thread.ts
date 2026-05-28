/**
 * Phase 350: TypeScript Digital Thread
 * Drone lifecycle tracking with immutable event chain.
 * Type-safe phase transitions and PLM data management.
 */

// ── Enums ─────────────────────────────────────────────────────────

enum LifecyclePhase {
  Design = "design",
  Manufacturing = "manufacturing",
  Testing = "testing",
  Deployment = "deployment",
  Operational = "operational",
  Maintenance = "maintenance",
  Decommission = "decommission",
}

enum EventType {
  Created = "created",
  DesignUpdate = "design_update",
  FirmwareFlash = "firmware_flash",
  Calibration = "calibration",
  FlightTest = "flight_test",
  Deployed = "deployed",
  MissionComplete = "mission_complete",
  FaultDetected = "fault_detected",
  Repair = "repair",
  ComponentReplaced = "component_replaced",
  SoftwareUpdate = "software_update",
  Decommissioned = "decommissioned",
}

// ── Interfaces ────────────────────────────────────────────────────

interface ThreadEvent {
  eventId: string;
  droneId: string;
  eventType: EventType;
  phase: LifecyclePhase;
  timestamp: number;
  description: string;
  metadata: Record<string, unknown>;
  prevHash: string;
  eventHash: string;
}

interface ComponentRecord {
  componentId: string;
  componentType: string;
  serialNumber: string;
  installDate: number;
  flightHours: number;
  maxFlightHours: number;
  status: string;
}

interface DroneThread {
  droneId: string;
  model: string;
  serialNumber: string;
  currentPhase: LifecyclePhase;
  events: ThreadEvent[];
  components: Map<string, ComponentRecord>;
  totalFlightHours: number;
  totalMissions: number;
  firmwareVersion: string;
  createdAt: number;
}

interface FleetHealth {
  totalDrones: number;
  operational: number;
  inMaintenance: number;
  totalFlightHours: number;
  totalMissions: number;
  faultyComponents: number;
  totalEvents: number;
}

// ── Valid Phase Transitions ───────────────────────────────────────

const VALID_TRANSITIONS: Record<string, LifecyclePhase[]> = {
  [LifecyclePhase.Design]: [LifecyclePhase.Manufacturing],
  [LifecyclePhase.Manufacturing]: [LifecyclePhase.Testing],
  [LifecyclePhase.Testing]: [LifecyclePhase.Deployment, LifecyclePhase.Manufacturing],
  [LifecyclePhase.Deployment]: [LifecyclePhase.Operational],
  [LifecyclePhase.Operational]: [LifecyclePhase.Maintenance, LifecyclePhase.Decommission],
  [LifecyclePhase.Maintenance]: [LifecyclePhase.Operational, LifecyclePhase.Decommission],
};

// ── Simple Hash ───────────────────────────────────────────────────

function simpleHash(input: string): string {
  let hash = 0;
  for (let i = 0; i < input.length; i++) {
    const chr = input.charCodeAt(i);
    hash = ((hash << 5) - hash + chr) | 0;
  }
  return Math.abs(hash).toString(16).padStart(8, "0");
}

// ── Digital Thread Manager ────────────────────────────────────────

class DigitalThreadManager {
  private threads = new Map<string, DroneThread>();
  private eventCounter = 0;

  createThread(droneId: string, model: string, serialNumber: string): DroneThread {
    const thread: DroneThread = {
      droneId,
      model,
      serialNumber,
      currentPhase: LifecyclePhase.Design,
      events: [],
      components: new Map(),
      totalFlightHours: 0,
      totalMissions: 0,
      firmwareVersion: "1.0.0",
      createdAt: Date.now(),
    };
    this.threads.set(droneId, thread);
    this.addEvent(droneId, EventType.Created, LifecyclePhase.Design,
      `Thread created for ${model} (SN: ${serialNumber})`);
    return thread;
  }

  addComponent(droneId: string, componentId: string,
    componentType: string, serialNumber: string,
    maxHours: number = 500): ComponentRecord | null {
    const thread = this.threads.get(droneId);
    if (!thread) return null;

    const comp: ComponentRecord = {
      componentId,
      componentType,
      serialNumber,
      installDate: Date.now(),
      flightHours: 0,
      maxFlightHours: maxHours,
      status: "operational",
    };
    thread.components.set(componentId, comp);
    this.addEvent(droneId, EventType.ComponentReplaced, thread.currentPhase,
      `Component installed: ${componentType} (${serialNumber})`,
      { componentId, type: componentType });
    return comp;
  }

  transitionPhase(droneId: string, newPhase: LifecyclePhase): boolean {
    const thread = this.threads.get(droneId);
    if (!thread) return false;

    const allowed = VALID_TRANSITIONS[thread.currentPhase] || [];
    if (!allowed.includes(newPhase)) return false;

    const oldPhase = thread.currentPhase;
    thread.currentPhase = newPhase;
    this.addEvent(droneId, EventType.Deployed, newPhase,
      `Phase transition: ${oldPhase} → ${newPhase}`);
    return true;
  }

  recordFlight(droneId: string, durationHours: number,
    missionType: string = "patrol"): boolean {
    const thread = this.threads.get(droneId);
    if (!thread || thread.currentPhase !== LifecyclePhase.Operational) return false;

    thread.totalFlightHours += durationHours;
    thread.totalMissions += 1;

    for (const comp of thread.components.values()) {
      comp.flightHours += durationHours;
      if (comp.flightHours > comp.maxFlightHours * 0.9) {
        comp.status = "wear_warning";
      }
    }

    this.addEvent(droneId, EventType.MissionComplete,
      LifecyclePhase.Operational,
      `Mission: ${missionType} (${durationHours.toFixed(1)}h)`,
      { duration: durationHours, type: missionType });
    return true;
  }

  recordFault(droneId: string, faultDesc: string,
    componentId?: string): boolean {
    const thread = this.threads.get(droneId);
    if (!thread) return false;

    if (componentId) {
      const comp = thread.components.get(componentId);
      if (comp) comp.status = "faulty";
    }

    this.addEvent(droneId, EventType.FaultDetected, thread.currentPhase,
      `Fault: ${faultDesc}`, { fault: faultDesc, component: componentId });
    return true;
  }

  updateFirmware(droneId: string, version: string): boolean {
    const thread = this.threads.get(droneId);
    if (!thread) return false;
    const oldVer = thread.firmwareVersion;
    thread.firmwareVersion = version;
    this.addEvent(droneId, EventType.SoftwareUpdate, thread.currentPhase,
      `Firmware: ${oldVer} → ${version}`);
    return true;
  }

  getMaintenanceNeeds(droneId: string): Array<{
    component: string; type: string; usagePct: number;
    status: string; action: string;
  }> {
    const thread = this.threads.get(droneId);
    if (!thread) return [];

    const needs: Array<{
      component: string; type: string; usagePct: number;
      status: string; action: string;
    }> = [];

    for (const comp of thread.components.values()) {
      const usage = (comp.flightHours / comp.maxFlightHours) * 100;
      if (usage > 80 || comp.status === "wear_warning" || comp.status === "faulty") {
        needs.push({
          component: comp.componentId,
          type: comp.componentType,
          usagePct: Math.round(usage * 10) / 10,
          status: comp.status,
          action: comp.status === "faulty" ? "replace" : "inspect",
        });
      }
    }
    return needs;
  }

  fleetHealth(): FleetHealth {
    let operational = 0, inMaintenance = 0, totalHours = 0;
    let totalMissions = 0, faultyComponents = 0;

    for (const t of this.threads.values()) {
      if (t.currentPhase === LifecyclePhase.Operational) operational++;
      if (t.currentPhase === LifecyclePhase.Maintenance) inMaintenance++;
      totalHours += t.totalFlightHours;
      totalMissions += t.totalMissions;
      for (const c of t.components.values()) {
        if (c.status === "faulty") faultyComponents++;
      }
    }

    return {
      totalDrones: this.threads.size,
      operational,
      inMaintenance,
      totalFlightHours: Math.round(totalHours * 10) / 10,
      totalMissions,
      faultyComponents,
      totalEvents: this.eventCounter,
    };
  }

  private addEvent(droneId: string, eventType: EventType,
    phase: LifecyclePhase, description: string,
    metadata: Record<string, unknown> = {}): ThreadEvent {
    this.eventCounter++;
    const thread = this.threads.get(droneId)!;
    const prevHash = thread.events.length > 0
      ? thread.events[thread.events.length - 1].eventHash
      : "genesis";

    const event: ThreadEvent = {
      eventId: `EVT-${String(this.eventCounter).padStart(8, "0")}`,
      droneId,
      eventType,
      phase,
      timestamp: Date.now(),
      description,
      metadata,
      prevHash,
      eventHash: simpleHash(`${this.eventCounter}${prevHash}${description}`),
    };
    thread.events.push(event);
    return event;
  }
}

// ── Main ──────────────────────────────────────────────────────────

function main(): void {
  const mgr = new DigitalThreadManager();

  for (let i = 0; i < 5; i++) {
    mgr.createThread(`drone_${i}`, "QuadX-500", `SN-${1000 + i}`);
    mgr.addComponent(`drone_${i}`, `motor_${i}`, "motor", `MOT-${i}00`);
    mgr.addComponent(`drone_${i}`, `batt_${i}`, "battery", `BAT-${i}00`, 200);

    mgr.transitionPhase(`drone_${i}`, LifecyclePhase.Manufacturing);
    mgr.transitionPhase(`drone_${i}`, LifecyclePhase.Testing);
    mgr.transitionPhase(`drone_${i}`, LifecyclePhase.Deployment);
    mgr.transitionPhase(`drone_${i}`, LifecyclePhase.Operational);
    mgr.recordFlight(`drone_${i}`, 10 + i * 5);
  }

  mgr.recordFault("drone_2", "Motor vibration anomaly", "motor_2");
  console.log("Maintenance:", JSON.stringify(mgr.getMaintenanceNeeds("drone_2")));
  console.log("Fleet Health:", JSON.stringify(mgr.fleetHealth(), null, 2));
}

main();

export { DigitalThreadManager, LifecyclePhase, EventType };

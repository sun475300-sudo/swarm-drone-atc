"""
Phase 336: Digital Thread Manager
드론 수명주기 추적 + PLM 데이터 연결.
설계→제조→운영→정비→퇴역 전체 이력 관리.
"""

import hashlib
import time
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any


class LifecyclePhase(Enum):
    DESIGN = "design"
    MANUFACTURING = "manufacturing"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    OPERATIONAL = "operational"
    MAINTENANCE = "maintenance"
    DECOMMISSION = "decommission"


class EventType(Enum):
    CREATED = "created"
    DESIGN_UPDATE = "design_update"
    FIRMWARE_FLASH = "firmware_flash"
    CALIBRATION = "calibration"
    FLIGHT_TEST = "flight_test"
    DEPLOYED = "deployed"
    MISSION_COMPLETE = "mission_complete"
    FAULT_DETECTED = "fault_detected"
    REPAIR = "repair"
    COMPONENT_REPLACED = "component_replaced"
    SOFTWARE_UPDATE = "software_update"
    DECOMMISSIONED = "decommissioned"


@dataclass
class ThreadEvent:
    event_id: str
    drone_id: str
    event_type: EventType
    phase: LifecyclePhase
    timestamp: float
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    prev_hash: str = ""
    event_hash: str = ""


@dataclass
class ComponentRecord:
    component_id: str
    component_type: str  # motor, esc, battery, frame, sensor, fc
    serial_number: str
    install_date: float
    flight_hours: float = 0.0
    max_flight_hours: float = 500.0
    status: str = "operational"


@dataclass
class DroneThread:
    drone_id: str
    model: str
    serial_number: str
    current_phase: LifecyclePhase
    events: List[ThreadEvent] = field(default_factory=list)
    components: Dict[str, ComponentRecord] = field(default_factory=dict)
    total_flight_hours: float = 0.0
    total_missions: int = 0
    firmware_version: str = "1.0.0"
    created_at: float = 0.0


class DigitalThreadManager:
    """Manages complete lifecycle digital threads for drone fleet."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.threads: Dict[str, DroneThread] = {}
        self._event_counter = 0

    def create_thread(self, drone_id: str, model: str,
                      serial_number: str) -> DroneThread:
        ts = time.time()
        thread = DroneThread(
            drone_id=drone_id, model=model,
            serial_number=serial_number,
            current_phase=LifecyclePhase.DESIGN,
            created_at=ts
        )
        self.threads[drone_id] = thread
        self._add_event(drone_id, EventType.CREATED, LifecyclePhase.DESIGN,
                        f"Thread created for {model} (SN: {serial_number})")
        return thread

    def add_component(self, drone_id: str, component_id: str,
                      component_type: str, serial_number: str,
                      max_hours: float = 500.0) -> Optional[ComponentRecord]:
        thread = self.threads.get(drone_id)
        if not thread:
            return None
        comp = ComponentRecord(
            component_id=component_id,
            component_type=component_type,
            serial_number=serial_number,
            install_date=time.time(),
            max_flight_hours=max_hours
        )
        thread.components[component_id] = comp
        self._add_event(drone_id, EventType.COMPONENT_REPLACED,
                        thread.current_phase,
                        f"Component installed: {component_type} ({serial_number})",
                        {"component_id": component_id, "type": component_type})
        return comp

    def transition_phase(self, drone_id: str,
                         new_phase: LifecyclePhase) -> bool:
        thread = self.threads.get(drone_id)
        if not thread:
            return False

        valid_transitions = {
            LifecyclePhase.DESIGN: [LifecyclePhase.MANUFACTURING],
            LifecyclePhase.MANUFACTURING: [LifecyclePhase.TESTING],
            LifecyclePhase.TESTING: [LifecyclePhase.DEPLOYMENT, LifecyclePhase.MANUFACTURING],
            LifecyclePhase.DEPLOYMENT: [LifecyclePhase.OPERATIONAL],
            LifecyclePhase.OPERATIONAL: [LifecyclePhase.MAINTENANCE, LifecyclePhase.DECOMMISSION],
            LifecyclePhase.MAINTENANCE: [LifecyclePhase.OPERATIONAL, LifecyclePhase.DECOMMISSION],
        }
        allowed = valid_transitions.get(thread.current_phase, [])
        if new_phase not in allowed:
            return False

        old_phase = thread.current_phase
        thread.current_phase = new_phase
        self._add_event(drone_id, EventType.DEPLOYED, new_phase,
                        f"Phase transition: {old_phase.value} → {new_phase.value}")
        return True

    def record_flight(self, drone_id: str, duration_hours: float,
                      mission_type: str = "patrol") -> bool:
        thread = self.threads.get(drone_id)
        if not thread or thread.current_phase != LifecyclePhase.OPERATIONAL:
            return False

        thread.total_flight_hours += duration_hours
        thread.total_missions += 1

        for comp in thread.components.values():
            comp.flight_hours += duration_hours
            if comp.flight_hours > comp.max_flight_hours * 0.9:
                comp.status = "wear_warning"

        self._add_event(drone_id, EventType.MISSION_COMPLETE,
                        LifecyclePhase.OPERATIONAL,
                        f"Mission complete: {mission_type} ({duration_hours:.1f}h)",
                        {"duration": duration_hours, "type": mission_type})
        return True

    def record_fault(self, drone_id: str, fault_desc: str,
                     component_id: Optional[str] = None) -> bool:
        thread = self.threads.get(drone_id)
        if not thread:
            return False

        meta: Dict[str, Any] = {"fault": fault_desc}
        if component_id and component_id in thread.components:
            thread.components[component_id].status = "faulty"
            meta["component"] = component_id

        self._add_event(drone_id, EventType.FAULT_DETECTED,
                        thread.current_phase, f"Fault: {fault_desc}", meta)
        return True

    def update_firmware(self, drone_id: str, version: str) -> bool:
        thread = self.threads.get(drone_id)
        if not thread:
            return False
        old_ver = thread.firmware_version
        thread.firmware_version = version
        self._add_event(drone_id, EventType.SOFTWARE_UPDATE,
                        thread.current_phase,
                        f"Firmware: {old_ver} → {version}",
                        {"old_version": old_ver, "new_version": version})
        return True

    def get_maintenance_needs(self, drone_id: str) -> List[Dict]:
        thread = self.threads.get(drone_id)
        if not thread:
            return []
        needs = []
        for comp in thread.components.values():
            usage_pct = comp.flight_hours / max(comp.max_flight_hours, 1) * 100
            if usage_pct > 80 or comp.status in ("wear_warning", "faulty"):
                needs.append({
                    "component": comp.component_id,
                    "type": comp.component_type,
                    "usage_pct": round(usage_pct, 1),
                    "status": comp.status,
                    "action": "replace" if comp.status == "faulty" else "inspect"
                })
        return needs

    def get_thread_history(self, drone_id: str,
                           event_type: Optional[EventType] = None) -> List[ThreadEvent]:
        thread = self.threads.get(drone_id)
        if not thread:
            return []
        if event_type:
            return [e for e in thread.events if e.event_type == event_type]
        return thread.events

    def fleet_health(self) -> Dict:
        operational = sum(1 for t in self.threads.values()
                        if t.current_phase == LifecyclePhase.OPERATIONAL)
        maintenance = sum(1 for t in self.threads.values()
                         if t.current_phase == LifecyclePhase.MAINTENANCE)
        total_hours = sum(t.total_flight_hours for t in self.threads.values())
        total_missions = sum(t.total_missions for t in self.threads.values())
        faulty_components = sum(
            1 for t in self.threads.values()
            for c in t.components.values() if c.status == "faulty"
        )
        return {
            "total_drones": len(self.threads),
            "operational": operational,
            "in_maintenance": maintenance,
            "total_flight_hours": round(total_hours, 1),
            "total_missions": total_missions,
            "faulty_components": faulty_components,
        }

    def _add_event(self, drone_id: str, event_type: EventType,
                   phase: LifecyclePhase, description: str,
                   metadata: Optional[Dict] = None) -> ThreadEvent:
        self._event_counter += 1
        thread = self.threads[drone_id]
        prev_hash = thread.events[-1].event_hash if thread.events else "genesis"

        event = ThreadEvent(
            event_id=f"EVT-{self._event_counter:08d}",
            drone_id=drone_id,
            event_type=event_type,
            phase=phase,
            timestamp=time.time(),
            description=description,
            metadata=metadata or {},
            prev_hash=prev_hash,
        )
        event.event_hash = hashlib.sha256(
            f"{event.event_id}{event.prev_hash}{event.description}".encode()
        ).hexdigest()[:16]
        thread.events.append(event)
        return event

    def summary(self) -> Dict:
        return {
            **self.fleet_health(),
            "total_events": self._event_counter,
        }


if __name__ == "__main__":
    mgr = DigitalThreadManager()
    for i in range(5):
        t = mgr.create_thread(f"drone_{i}", "QuadX-500", f"SN-{1000+i}")
        mgr.add_component(f"drone_{i}", f"motor_{i}_FL", "motor", f"MOT-{i}00")
        mgr.add_component(f"drone_{i}", f"batt_{i}", "battery", f"BAT-{i}00", 200)
        mgr.transition_phase(f"drone_{i}", LifecyclePhase.MANUFACTURING)
        mgr.transition_phase(f"drone_{i}", LifecyclePhase.TESTING)
        mgr.transition_phase(f"drone_{i}", LifecyclePhase.DEPLOYMENT)
        mgr.transition_phase(f"drone_{i}", LifecyclePhase.OPERATIONAL)
        mgr.record_flight(f"drone_{i}", 10.0 + i * 5)

    mgr.record_fault("drone_2", "Motor vibration anomaly", "motor_2_FL")
    print(f"Maintenance needs: {mgr.get_maintenance_needs('drone_2')}")
    print(f"Summary: {mgr.summary()}")

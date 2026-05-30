"""PostgreSQL + TimescaleDB schema definitions — Phase P714.

Provides DDL generation and a lightweight in-process store for testing
without a live database connection.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# DDL helpers
# ---------------------------------------------------------------------------

TELEMETRY_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS drone_telemetry (
    time        TIMESTAMPTZ     NOT NULL,
    drone_id    TEXT            NOT NULL,
    x           DOUBLE PRECISION NOT NULL,
    y           DOUBLE PRECISION NOT NULL,
    z           DOUBLE PRECISION NOT NULL,
    vx          DOUBLE PRECISION,
    vy          DOUBLE PRECISION,
    vz          DOUBLE PRECISION,
    battery_pct DOUBLE PRECISION,
    state       TEXT
);
SELECT create_hypertable('drone_telemetry', 'time', if_not_exists => TRUE);
"""

EVENTS_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS airspace_events (
    time        TIMESTAMPTZ     NOT NULL,
    event_type  TEXT            NOT NULL,
    drone_id    TEXT,
    severity    TEXT,
    payload     JSONB
);
SELECT create_hypertable('airspace_events', 'time', if_not_exists => TRUE);
"""

RETENTION_POLICY_DDL = """
SELECT add_retention_policy('drone_telemetry', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('airspace_events', INTERVAL '30 days', if_not_exists => TRUE);
"""


def get_schema_ddl() -> str:
    """Return the full DDL required to set up the TimescaleDB schema."""
    return TELEMETRY_TABLE_DDL + EVENTS_TABLE_DDL + RETENTION_POLICY_DDL


def get_table_names() -> list[str]:
    return ["drone_telemetry", "airspace_events"]


# ---------------------------------------------------------------------------
# In-memory store (for unit tests / offline use)
# ---------------------------------------------------------------------------

@dataclass
class TelemetryRecord:
    time: str
    drone_id: str
    x: float
    y: float
    z: float
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    battery_pct: float = 100.0
    state: str = "hover"

    def to_dict(self) -> dict[str, Any]:
        return {
            "time": self.time,
            "drone_id": self.drone_id,
            "x": self.x, "y": self.y, "z": self.z,
            "vx": self.vx, "vy": self.vy, "vz": self.vz,
            "battery_pct": self.battery_pct,
            "state": self.state,
        }


@dataclass
class EventRecord:
    time: str
    event_type: str
    drone_id: str = ""
    severity: str = "info"
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "time": self.time,
            "event_type": self.event_type,
            "drone_id": self.drone_id,
            "severity": self.severity,
            "payload": self.payload,
        }


class InMemoryStore:
    """Lightweight stand-in for TimescaleDB used in testing."""

    def __init__(self, retention_days: int = 30) -> None:
        self.retention_days = retention_days
        self._telemetry: list[TelemetryRecord] = []
        self._events: list[EventRecord] = []

    def insert_telemetry(self, record: TelemetryRecord) -> None:
        self._telemetry.append(record)

    def insert_event(self, record: EventRecord) -> None:
        self._events.append(record)

    def query_telemetry(
        self,
        drone_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        rows = self._telemetry
        if drone_id:
            rows = [r for r in rows if r.drone_id == drone_id]
        return [r.to_dict() for r in rows[-limit:]]

    def query_events(
        self,
        event_type: str | None = None,
        severity: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        rows = self._events
        if event_type:
            rows = [r for r in rows if r.event_type == event_type]
        if severity:
            rows = [r for r in rows if r.severity == severity]
        return [r.to_dict() for r in rows[-limit:]]

    def count_telemetry(self) -> int:
        return len(self._telemetry)

    def count_events(self) -> int:
        return len(self._events)

    def clear(self) -> None:
        self._telemetry.clear()
        self._events.clear()

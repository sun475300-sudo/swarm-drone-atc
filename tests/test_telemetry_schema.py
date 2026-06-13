"""ODYSSEY Phase 466 — Telemetry JSON Schema 적합성.

ws_bridge.py 가 외부로 송신하는 2Hz 스냅샷이 표준 스키마와 호환되는지 확인.
스키마 자체 + 표준 예제 페이로드를 jsonschema(또는 수동 검증) 양쪽으로 검증.
"""
from __future__ import annotations

import json
from pathlib import Path

SCHEMA = Path(__file__).resolve().parents[1] / "docs" / "schemas" / "telemetry.schema.json"

EXAMPLE = {
    "t": 12.5,
    "drones": [
        {
            "id": "D-001",
            "pos": [10.0, 0.5, -3.2],
            "vel": [1.1, 0.0, 0.0],
            "phase": "CRUISE",
            "battery": 87.4,
        }
    ],
    "stats": {
        "collisions": 0, "near_misses": 1, "conflicts": 3,
        "advisories": 2, "cbs_attempts": 5, "cbs_successes": 5,
    },
    "backend": "cpu",
}


def test_schema_file_loads_as_draft7():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema.get("$schema", "").endswith("draft-07/schema#")
    assert schema["required"] == ["t", "drones", "stats", "backend"]
    drone = schema["properties"]["drones"]["items"]
    assert drone["properties"]["pos"]["minItems"] == 3
    assert drone["properties"]["battery"]["maximum"] == 100


def test_example_payload_matches_schema_shape():
    """jsonschema 미설치 환경에서도 동작하는 핵심 형상 검증."""
    payload = EXAMPLE
    assert {"t", "drones", "stats", "backend"} <= payload.keys()
    assert isinstance(payload["t"], (int, float)) and payload["t"] >= 0
    for d in payload["drones"]:
        assert {"id", "pos", "vel", "phase", "battery"} <= d.keys()
        assert len(d["pos"]) == 3 and len(d["vel"]) == 3
        assert 0 <= d["battery"] <= 100
    s = payload["stats"]
    assert {"collisions", "near_misses", "conflicts", "advisories"} <= s.keys()
    assert all(s[k] >= 0 for k in s)


def test_ws_bridge_snapshot_matches_schema_keys():
    """simulation/ws_bridge.py 의 snapshot 코드가 스키마 필수 키를 모두 포함하는지 정적 검사."""
    bridge_src = (Path(__file__).resolve().parents[1] / "simulation" /
                  "ws_bridge.py").read_text(encoding="utf-8")
    for key in ['"t":', '"drones":', '"stats":', '"backend":']:
        assert key in bridge_src, f"ws_bridge.py 에 {key} 누락"
    for stat in ['"collisions":', '"near_misses":', '"conflicts":', '"advisories":']:
        assert stat in bridge_src
    for drone_key in ['"id":', '"pos":', '"vel":', '"phase":', '"battery":']:
        assert drone_key in bridge_src

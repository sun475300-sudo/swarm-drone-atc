"""
Flight Data Recorder
Phase 392 - Black Box, Data Logging, Forensic Analysis
"""

import json
from dataclasses import dataclass, asdict
from typing import List, Dict
import time


@dataclass
class FlightRecord:
    timestamp: float
    event: str
    data: Dict


class FlightRecorder:
    def __init__(self):
        self.records: List[FlightRecord] = []
        self.max_records = 100000

    def log(self, event: str, data: Dict):
        self.records.append(FlightRecord(time.time(), event, data))
        if len(self.records) > self.max_records:
            self.records.pop(0)

    def export(self, filename: str):
        with open(filename, "w") as f:
            json.dump([asdict(r) for r in self.records], f, indent=2)

    def analyze(self) -> Dict:
        events = {}
        for r in self.records:
            events[r.event] = events.get(r.event, 0) + 1
        return {"total": len(self.records), "events": events}


if __name__ == "__main__":
    rec = FlightRecorder()
    for i in range(100):
        rec.log("status", {"battery": 100 - i, "alt": 50})
    print(rec.analyze())

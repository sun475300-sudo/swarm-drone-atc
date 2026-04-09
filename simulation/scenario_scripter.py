"""
시나리오 스크립터 (YAML DSL)
===========================
시간 기반 이벤트를 정의하는 YAML DSL을 파싱하고
시뮬레이션 실행 중 자동으로 이벤트를 트리거.

지원 이벤트:
  - SPAWN_DRONES: 드론 생성
  - INJECT_ROGUE: 침입 드론 투입
  - SET_WIND: 풍속/풍향 변경
  - ADD_NFZ: 동적 NFZ 추가
  - REMOVE_NFZ: NFZ 제거
  - FAIL_DRONE: 드론 강제 장애
  - COMMS_JAM: 통신 교란
  - BATTERY_DRAIN: 배터리 급속 소모

사용법:
    scripter = ScenarioScripter()
    scripter.load_yaml(yaml_string)
    events = scripter.get_events_at(t=30.0)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import yaml


# 지원 이벤트 타입
VALID_EVENT_TYPES = frozenset({
    "SPAWN_DRONES",
    "INJECT_ROGUE",
    "SET_WIND",
    "ADD_NFZ",
    "REMOVE_NFZ",
    "FAIL_DRONE",
    "COMMS_JAM",
    "BATTERY_DRAIN",
})


@dataclass
class ScriptedEvent:
    """시간 트리거 이벤트"""
    time: float               # 트리거 시각 (초)
    event_type: str            # 이벤트 타입
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    fired: bool = False        # 발화 여부

    def __post_init__(self) -> None:
        if self.event_type not in VALID_EVENT_TYPES:
            raise ValueError(f"Unknown event type: {self.event_type}")
        if self.time < 0:
            raise ValueError(f"Event time must be >= 0, got {self.time}")


@dataclass
class ScenarioScript:
    """시나리오 스크립트 (이벤트 목록 + 메타데이터)"""
    name: str = "unnamed"
    description: str = ""
    duration: float = 120.0
    events: list[ScriptedEvent] = field(default_factory=list)

    @property
    def event_count(self) -> int:
        return len(self.events)

    @property
    def fired_count(self) -> int:
        return sum(1 for e in self.events if e.fired)


class ScenarioScripter:
    """
    YAML DSL 기반 시나리오 스크립터.

    YAML 포맷:
    ```yaml
    name: 복합_위협_시나리오
    description: 풍속 증가 + 침입 드론 + NFZ 추가
    duration: 120
    events:
      - time: 10
        type: SET_WIND
        params:
          speed: 15.0
          direction: [1, 0, 0]
      - time: 30
        type: INJECT_ROGUE
        params:
          count: 3
    ```
    """

    def __init__(self) -> None:
        self._script: ScenarioScript | None = None
        self._time_index: dict[float, list[int]] = {}  # time → event indices

    def load_yaml(self, yaml_str: str) -> ScenarioScript:
        """YAML 문자열에서 시나리오 로드"""
        data = yaml.safe_load(yaml_str)
        if not isinstance(data, dict):
            raise ValueError("YAML root must be a mapping")

        script = ScenarioScript(
            name=data.get("name", "unnamed"),
            description=data.get("description", ""),
            duration=float(data.get("duration", 120.0)),
        )

        for ev_data in data.get("events", []):
            event = ScriptedEvent(
                time=float(ev_data["time"]),
                event_type=ev_data["type"],
                params=ev_data.get("params", {}),
                description=ev_data.get("description", ""),
            )
            script.events.append(event)

        # 시간순 정렬
        script.events.sort(key=lambda e: e.time)

        # 시간 인덱스 구축
        self._time_index.clear()
        for i, ev in enumerate(script.events):
            self._time_index.setdefault(ev.time, []).append(i)

        self._script = script
        return script

    def load_dict(self, data: dict) -> ScenarioScript:
        """딕셔너리에서 시나리오 로드"""
        script = ScenarioScript(
            name=data.get("name", "unnamed"),
            description=data.get("description", ""),
            duration=float(data.get("duration", 120.0)),
        )

        for ev_data in data.get("events", []):
            event = ScriptedEvent(
                time=float(ev_data["time"]),
                event_type=ev_data["type"],
                params=ev_data.get("params", {}),
                description=ev_data.get("description", ""),
            )
            script.events.append(event)

        script.events.sort(key=lambda e: e.time)

        self._time_index.clear()
        for i, ev in enumerate(script.events):
            self._time_index.setdefault(ev.time, []).append(i)

        self._script = script
        return script

    def get_events_at(self, t: float) -> list[ScriptedEvent]:
        """
        시각 t에 트리거되어야 할 이벤트 반환.

        아직 발화되지 않은(fired=False) 이벤트 중
        time <= t 인 것들을 반환하고 fired=True로 마킹.
        """
        if self._script is None:
            return []

        triggered: list[ScriptedEvent] = []
        for ev in self._script.events:
            if not ev.fired and ev.time <= t:
                ev.fired = True
                triggered.append(ev)

        return triggered

    def get_events_in_range(
        self, t_start: float, t_end: float
    ) -> list[ScriptedEvent]:
        """시간 범위 내 이벤트 조회 (발화 여부 무관)"""
        if self._script is None:
            return []
        return [
            ev for ev in self._script.events
            if t_start <= ev.time <= t_end
        ]

    def peek_next(self, t: float) -> ScriptedEvent | None:
        """다음 미발화 이벤트 미리보기 (발화하지 않음)"""
        if self._script is None:
            return None
        for ev in self._script.events:
            if not ev.fired and ev.time > t:
                return ev
        return None

    def reset(self) -> None:
        """모든 이벤트 발화 상태 초기화"""
        if self._script is None:
            return
        for ev in self._script.events:
            ev.fired = False

    @property
    def script(self) -> ScenarioScript | None:
        return self._script

    def summary(self) -> dict[str, Any]:
        """스크립트 요약"""
        if self._script is None:
            return {"loaded": False}

        by_type: dict[str, int] = {}
        for ev in self._script.events:
            by_type[ev.event_type] = by_type.get(ev.event_type, 0) + 1

        return {
            "loaded": True,
            "name": self._script.name,
            "duration": self._script.duration,
            "event_count": self._script.event_count,
            "fired_count": self._script.fired_count,
            "events_by_type": by_type,
        }

    def to_yaml(self) -> str:
        """현재 스크립트를 YAML 문자열로 변환"""
        if self._script is None:
            return ""

        data = {
            "name": self._script.name,
            "description": self._script.description,
            "duration": self._script.duration,
            "events": [
                {
                    "time": ev.time,
                    "type": ev.event_type,
                    "params": ev.params,
                    "description": ev.description,
                }
                for ev in self._script.events
            ],
        }
        return yaml.dump(data, allow_unicode=True, default_flow_style=False)

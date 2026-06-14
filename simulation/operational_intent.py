"""
운영 의도(Operational Intent) 교환 포맷 — 4D 볼륨 직렬화
======================================================

ODYSSEY Phase 422 — 연합 운영(Federation Operations).

연합된 SDACS 인스턴스 간에 "어느 공역을, 언제, 어느 고도에서 점유할 것인가"를
교환하기 위한 **결정적 직렬화 포맷**이다. ASTM F3548-21 *operational intent*
구조(4D 볼륨 = 지리 외곽선 + 고도 밴드 + 시간 창)에 정렬한다.

`airspace_reservation.py`(내부 그리드-섹터 예약)와 달리, 본 모듈은 WGS84 위·경도
다각형 기반의 **인스턴스 간 교환·검증·충돌 사전판정** 포맷을 담당한다.

설계 원칙:
- 불변(frozen) 데이터클래스 — 직렬화 대상은 부작용 없이 복제·교환된다.
- 외부 의존성 0 (표준 라이브러리만).
- 충돌 사전판정은 **보수적 경계상자(bounding-box)** 교차로 한다. 거짓 음성(놓침)을
  내지 않도록 다각형을 외접 박스로 과대근사하며, 이는 협상 전 1차 필터 용도임을 명시.

사용법::

    vol = Volume4D(
        outline=((34.79, 126.39), (34.81, 126.39), (34.81, 126.41), (34.79, 126.41)),
        altitude_lower_m=0.0, altitude_upper_m=120.0,
        time_start_s=0.0, time_end_s=60.0,
    )
    oi = OperationalIntent(intent_id="OI-001", state="ACCEPTED", priority=3, volumes=(vol,))
    payload = oi.to_dict()                 # 교환용 dict
    restored = OperationalIntent.from_dict(payload)  # 라운드트립
    assert restored == oi
"""
from __future__ import annotations

from dataclasses import dataclass

# ASTM F3548-21 operational intent 상태 (정렬). ENDED 는 종료된 의도.
VALID_STATES = ("ACCEPTED", "ACTIVATED", "NONCONFORMING", "CONTINGENT", "ENDED")

_LAT_RANGE = (-90.0, 90.0)
_LON_RANGE = (-180.0, 180.0)
_MIN_VERTICES = 3  # 다각형 최소 꼭짓점


@dataclass(frozen=True)
class Volume4D:
    """4D 시공간 볼륨 — 지리 외곽선 + 고도 밴드 + 시간 창."""

    outline: tuple[tuple[float, float], ...]  # ((lat, lon), ...) WGS84
    altitude_lower_m: float
    altitude_upper_m: float
    time_start_s: float
    time_end_s: float

    def __post_init__(self) -> None:
        """경계에서 입력을 검증한다 (실패 시 ValueError)."""
        if len(self.outline) < _MIN_VERTICES:
            raise ValueError(
                f"외곽선은 최소 {_MIN_VERTICES} 꼭짓점이 필요합니다 (받음: {len(self.outline)})"
            )
        for lat, lon in self.outline:
            if not _LAT_RANGE[0] <= lat <= _LAT_RANGE[1]:
                raise ValueError(f"위도 범위 이탈: {lat}")
            if not _LON_RANGE[0] <= lon <= _LON_RANGE[1]:
                raise ValueError(f"경도 범위 이탈: {lon}")
        if self.altitude_lower_m >= self.altitude_upper_m:
            raise ValueError(
                f"고도 하한({self.altitude_lower_m})은 상한({self.altitude_upper_m})보다 낮아야 합니다"
            )
        if self.time_start_s >= self.time_end_s:
            raise ValueError(
                f"시작 시각({self.time_start_s})은 종료 시각({self.time_end_s})보다 앞서야 합니다"
            )

    def bbox(self) -> tuple[float, float, float, float]:
        """외곽선의 경계상자 (lat_min, lat_max, lon_min, lon_max)."""
        lats = [v[0] for v in self.outline]
        lons = [v[1] for v in self.outline]
        return (min(lats), max(lats), min(lons), max(lons))

    def to_dict(self) -> dict:
        """ASTM F3548 정렬 교환용 dict 로 직렬화."""
        return {
            "outline": [list(v) for v in self.outline],
            "altitude_lower_m": self.altitude_lower_m,
            "altitude_upper_m": self.altitude_upper_m,
            "time_start_s": self.time_start_s,
            "time_end_s": self.time_end_s,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Volume4D:
        """교환용 dict 에서 역직렬화 (검증 포함)."""
        try:
            outline = tuple((float(v[0]), float(v[1])) for v in data["outline"])
            return cls(
                outline=outline,
                altitude_lower_m=float(data["altitude_lower_m"]),
                altitude_upper_m=float(data["altitude_upper_m"]),
                time_start_s=float(data["time_start_s"]),
                time_end_s=float(data["time_end_s"]),
            )
        except (KeyError, TypeError, IndexError, ValueError) as exc:
            # 구조 오류(KeyError 등)와 값 오류(__post_init__ ValueError)를 일관되게 래핑
            raise ValueError(f"Volume4D 역직렬화 실패: {exc}") from exc


@dataclass(frozen=True)
class OperationalIntent:
    """연합 교환 단위 — 한 운영자의 의도(다수 4D 볼륨)."""

    intent_id: str
    state: str
    priority: int  # 1 = 최우선
    volumes: tuple[Volume4D, ...]  # 필수 — 최소 1개 (__post_init__ 검증)

    def __post_init__(self) -> None:
        """경계에서 입력을 검증한다 (실패 시 ValueError)."""
        if not self.intent_id:
            raise ValueError("intent_id 는 비어 있을 수 없습니다")
        if self.state not in VALID_STATES:
            raise ValueError(f"알 수 없는 상태: {self.state} (허용: {VALID_STATES})")
        if self.priority < 1:
            raise ValueError(f"priority 는 1 이상이어야 합니다 (받음: {self.priority})")
        if not self.volumes:
            raise ValueError("운영 의도는 최소 1개의 볼륨을 가져야 합니다")

    def to_dict(self) -> dict:
        """교환용 dict 로 직렬화."""
        return {
            "intent_id": self.intent_id,
            "state": self.state,
            "priority": self.priority,
            "volumes": [v.to_dict() for v in self.volumes],
        }

    @classmethod
    def from_dict(cls, data: dict) -> OperationalIntent:
        """교환용 dict 에서 역직렬화 (검증 포함, 라운드트립 보장)."""
        try:
            volumes = tuple(Volume4D.from_dict(v) for v in data["volumes"])
            return cls(
                intent_id=str(data["intent_id"]),
                state=str(data["state"]),
                priority=int(data["priority"]),
                volumes=volumes,
            )
        except (KeyError, TypeError) as exc:
            raise ValueError(f"OperationalIntent 역직렬화 실패: {exc}") from exc


def _interval_overlap(a_lo: float, a_hi: float, b_lo: float, b_hi: float) -> bool:
    """반열린 구간 [a_lo, a_hi), [b_lo, b_hi) 의 교차 여부 (경계 접촉은 비충돌)."""
    return a_lo < b_hi and b_lo < a_hi


def volumes_intersect(a: Volume4D, b: Volume4D) -> bool:
    """두 4D 볼륨의 보수적 교차 판정.

    시간·고도·지리(경계상자) 세 축이 **모두** 겹칠 때만 True.
    지리는 다각형 외접 박스로 과대근사하므로 거짓 양성은 가능하나 거짓 음성은 없다
    (협상 전 1차 필터로 안전).
    """
    if not _interval_overlap(a.time_start_s, a.time_end_s, b.time_start_s, b.time_end_s):
        return False
    # 고도도 반열린 구간으로 취급한다: 한 볼륨의 상한 == 다른 볼륨의 하한이면
    # 물리적으로 접하지만 점유 충돌은 아닌 것으로 본다(필터 보수성 일관 유지).
    if not _interval_overlap(
        a.altitude_lower_m, a.altitude_upper_m, b.altitude_lower_m, b.altitude_upper_m
    ):
        return False
    a_lat_min, a_lat_max, a_lon_min, a_lon_max = a.bbox()
    b_lat_min, b_lat_max, b_lon_min, b_lon_max = b.bbox()
    if not _interval_overlap(a_lat_min, a_lat_max, b_lat_min, b_lat_max):
        return False
    return _interval_overlap(a_lon_min, a_lon_max, b_lon_min, b_lon_max)


def intents_conflict(a: OperationalIntent, b: OperationalIntent) -> bool:
    """두 운영 의도 사이에 충돌하는 볼륨 쌍이 하나라도 있으면 True.

    종료(ENDED)된 의도는 공역을 점유하지 않으므로 충돌하지 않는다.
    """
    if a.state == "ENDED" or b.state == "ENDED":
        return False
    return any(volumes_intersect(va, vb) for va in a.volumes for vb in b.volumes)

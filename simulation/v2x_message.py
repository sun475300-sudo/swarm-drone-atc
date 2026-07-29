"""V2X (Vehicle-to-Everything) 드론 간 직접 통신 메시지 규격
==========================================================

GENESIS Phase 364 — 드론-투-드론 다이렉트 통신 프로토콜.

SAE J2735 BSM (Basic Safety Message) 을 UAS (무인항공시스템) 에 맞게 변환한
결정적 메시지 규격이다. 군집 드론이 10Hz 주기로 위치·속도·의도를 브로드캐스트하고,
긴급 상황 시 EVA (Emergency Vehicle Alert) 를 전파한다.

메시지 타입:
- BSM: 주기적 안전 메시지 (위치·속도·의도)
- EVA: 긴급 알림 (비상 상황 전파)
- TIM: 공역 정보 메시지 (공역 권고)
- SPaT: 신호 위상 및 타이밍 (복도 시퀀싱)

설계 원칙:
- 불변(frozen) 데이터클래스 — 메시지는 생성 후 변경 불가.
- ``np.random.default_rng(seed)`` — 채널 시뮬레이션의 결정적 랜덤.
- struct 모듈 — 바이너리 인코딩으로 대역폭 절감.
- 라운드트립 보장: ``decode(encode(msg)) == msg``.

CLI::

    python -m simulation.v2x_message --example-bsm
    python -m simulation.v2x_message --example-eva
    python -m simulation.v2x_message --encode
    python -m simulation.v2x_message --binary-size
"""
from __future__ import annotations

import math
import struct
import uuid
from dataclasses import dataclass

import numpy as np

# ── 메시지 타입 상수 ─────────────────────────────────────────────────────
BSM = "bsm"    # Basic Safety Message (주기적 위치·속도·의도 브로드캐스트)
EVA = "eva"    # Emergency Vehicle Alert (비상/비상 착륙 전파)
TIM = "tim"    # Traveler Information Message (공역 권고)
SPaT = "spat"  # Signal Phase and Timing (복도 타이밍/시퀀싱)

# ── 허용 값 집합 ─────────────────────────────────────────────────────────
VALID_INTENTS = ("cruise", "ascending", "descending", "hovering", "landing", "emergency")
VALID_EMERGENCY_TYPES = (
    "low_battery", "motor_failure", "gps_lost",
    "geofence_breach", "collision_imminent", "forced_landing",
)
VALID_SEVERITIES = ("warning", "critical", "mayday")
VALID_RECOMMENDED_ACTIONS = ("avoid_area", "yield_altitude", "clear_corridor", "no_action")

# ── 바이너리 포맷 정의 ───────────────────────────────────────────────────
# BSM: msg_id(36s) + timestamp(d) + drone_id(32s) + pos(3d) + vel(3d) +
#       heading(d) + altitude(d) + speed(d) + intent(16s) + battery(d) +
#       accuracy(d) + ttl(i) + msg_type(8s)
_BSM_FMT = "!36s d 32s 3d 3d d d d 16s d d i 8s"
_BSM_SIZE = struct.calcsize(_BSM_FMT)

# EVA: msg_id(36s) + timestamp(d) + drone_id(32s) + pos(3d) +
#       emergency_type(20s) + severity(10s) + recommended_action(16s) +
#       affected_radius(d) + msg_type(8s)
_EVA_FMT = "!36s d 32s 3d 20s 10s 16s d 8s"
_EVA_SIZE = struct.calcsize(_EVA_FMT)


def _pad(s: str, length: int) -> bytes:
    """문자열을 고정 길이 바이트로 패딩한다."""
    return s.encode("utf-8")[:length].ljust(length, b"\x00")


def _unpad(b: bytes) -> str:
    """패딩된 바이트에서 문자열을 복원한다."""
    return b.rstrip(b"\x00").decode("utf-8")


def generate_msg_id() -> str:
    """고유 메시지 식별자를 생성한다."""
    return str(uuid.uuid4())


# ── 데이터클래스 ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class DroneBasicSafetyMessage:
    """BSM (Basic Safety Message) — 드론 주기적 안전 메시지.

    10Hz 주기로 위치·속도·의도를 브로드캐스트한다.
    """

    msg_id: str
    msg_type: str  # 항상 "bsm"
    timestamp_s: float
    drone_id: str
    position: tuple[float, float, float]   # (x, y, z) 미터
    velocity: tuple[float, float, float]   # (vx, vy, vz) m/s
    heading_deg: float    # 0-360
    altitude_m: float     # AGL
    speed_ms: float       # 지면 속도 크기
    intent: str           # cruise | ascending | descending | hovering | landing | emergency
    battery_pct: float    # 0-100
    accuracy_m: float     # 위치 정확도 추정치
    ttl_hops: int = 1     # 멀티홉 릴레이 TTL (1 = 직접 전달만)

    def __post_init__(self) -> None:
        if self.msg_type != BSM:
            raise ValueError(f"BSM msg_type 은 '{BSM}' 이어야 함 (받음: {self.msg_type!r})")
        if not (0.0 <= self.heading_deg <= 360.0):
            raise ValueError(f"heading_deg 범위 이탈: {self.heading_deg} (허용: 0-360)")
        if not (0.0 <= self.battery_pct <= 100.0):
            raise ValueError(f"battery_pct 범위 이탈: {self.battery_pct} (허용: 0-100)")
        if self.ttl_hops < 1:
            raise ValueError(f"ttl_hops 는 1 이상이어야 함 (받음: {self.ttl_hops})")
        if self.speed_ms < 0.0:
            raise ValueError(f"speed_ms 는 0 이상이어야 함 (받음: {self.speed_ms})")
        if self.intent not in VALID_INTENTS:
            raise ValueError(f"알 수 없는 intent: {self.intent!r} (허용: {VALID_INTENTS})")


@dataclass(frozen=True)
class EmergencyAlert:
    """EVA (Emergency Vehicle Alert) — 긴급 알림 메시지.

    비상 상황 발생 시 주변 드론에게 회피 행동을 권고한다.
    """

    msg_id: str
    msg_type: str  # 항상 "eva"
    timestamp_s: float
    drone_id: str
    position: tuple[float, float, float]  # (x, y, z) 미터
    emergency_type: str   # low_battery | motor_failure | gps_lost | ...
    severity: str         # warning | critical | mayday
    recommended_action: str  # avoid_area | yield_altitude | clear_corridor | no_action
    affected_radius_m: float  # 회피 반경 (미터)

    def __post_init__(self) -> None:
        if self.msg_type != EVA:
            raise ValueError(f"EVA msg_type 은 '{EVA}' 이어야 함 (받음: {self.msg_type!r})")
        if self.emergency_type not in VALID_EMERGENCY_TYPES:
            raise ValueError(
                f"알 수 없는 emergency_type: {self.emergency_type!r} "
                f"(허용: {VALID_EMERGENCY_TYPES})"
            )
        if self.severity not in VALID_SEVERITIES:
            raise ValueError(
                f"알 수 없는 severity: {self.severity!r} (허용: {VALID_SEVERITIES})"
            )
        if self.recommended_action not in VALID_RECOMMENDED_ACTIONS:
            raise ValueError(
                f"알 수 없는 recommended_action: {self.recommended_action!r} "
                f"(허용: {VALID_RECOMMENDED_ACTIONS})"
            )
        if self.affected_radius_m < 0.0:
            raise ValueError(
                f"affected_radius_m 는 0 이상이어야 함 (받음: {self.affected_radius_m})"
            )


V2XMessageUnion = DroneBasicSafetyMessage | EmergencyAlert


# ── 코덱 ─────────────────────────────────────────────────────────────────


class V2XCodec:
    """V2X 메시지 직렬화/역직렬화 코덱.

    JSON dict 와 compact binary (struct pack) 양쪽을 지원한다.
    라운드트립 보장: ``decode(encode(msg)) == msg``.
    """

    @staticmethod
    def encode(msg: V2XMessageUnion) -> dict:
        """메시지를 JSON 직렬화 가능한 dict 로 변환한다."""
        if isinstance(msg, DroneBasicSafetyMessage):
            return {
                "msg_id": msg.msg_id,
                "msg_type": msg.msg_type,
                "timestamp_s": msg.timestamp_s,
                "drone_id": msg.drone_id,
                "position": list(msg.position),
                "velocity": list(msg.velocity),
                "heading_deg": msg.heading_deg,
                "altitude_m": msg.altitude_m,
                "speed_ms": msg.speed_ms,
                "intent": msg.intent,
                "battery_pct": msg.battery_pct,
                "accuracy_m": msg.accuracy_m,
                "ttl_hops": msg.ttl_hops,
            }
        if isinstance(msg, EmergencyAlert):
            return {
                "msg_id": msg.msg_id,
                "msg_type": msg.msg_type,
                "timestamp_s": msg.timestamp_s,
                "drone_id": msg.drone_id,
                "position": list(msg.position),
                "emergency_type": msg.emergency_type,
                "severity": msg.severity,
                "recommended_action": msg.recommended_action,
                "affected_radius_m": msg.affected_radius_m,
            }
        raise TypeError(f"지원하지 않는 메시지 타입: {type(msg).__name__}")

    @staticmethod
    def decode(data: dict) -> V2XMessageUnion:
        """dict 에서 메시지를 복원한다 (msg_type 기반 디스패치)."""
        msg_type = data.get("msg_type")
        if msg_type == BSM:
            return DroneBasicSafetyMessage(
                msg_id=str(data["msg_id"]),
                msg_type=BSM,
                timestamp_s=float(data["timestamp_s"]),
                drone_id=str(data["drone_id"]),
                position=tuple(float(v) for v in data["position"]),
                velocity=tuple(float(v) for v in data["velocity"]),
                heading_deg=float(data["heading_deg"]),
                altitude_m=float(data["altitude_m"]),
                speed_ms=float(data["speed_ms"]),
                intent=str(data["intent"]),
                battery_pct=float(data["battery_pct"]),
                accuracy_m=float(data["accuracy_m"]),
                ttl_hops=int(data["ttl_hops"]),
            )
        if msg_type == EVA:
            return EmergencyAlert(
                msg_id=str(data["msg_id"]),
                msg_type=EVA,
                timestamp_s=float(data["timestamp_s"]),
                drone_id=str(data["drone_id"]),
                position=tuple(float(v) for v in data["position"]),
                emergency_type=str(data["emergency_type"]),
                severity=str(data["severity"]),
                recommended_action=str(data["recommended_action"]),
                affected_radius_m=float(data["affected_radius_m"]),
            )
        raise ValueError(f"알 수 없는 msg_type: {msg_type!r} (허용: {BSM!r}, {EVA!r})")

    @staticmethod
    def encode_binary(msg: V2XMessageUnion) -> bytes:
        """메시지를 compact binary (struct pack) 로 인코딩한다."""
        if isinstance(msg, DroneBasicSafetyMessage):
            return struct.pack(
                _BSM_FMT,
                _pad(msg.msg_id, 36),
                msg.timestamp_s,
                _pad(msg.drone_id, 32),
                msg.position[0], msg.position[1], msg.position[2],
                msg.velocity[0], msg.velocity[1], msg.velocity[2],
                msg.heading_deg,
                msg.altitude_m,
                msg.speed_ms,
                _pad(msg.intent, 16),
                msg.battery_pct,
                msg.accuracy_m,
                msg.ttl_hops,
                _pad(msg.msg_type, 8),
            )
        if isinstance(msg, EmergencyAlert):
            return struct.pack(
                _EVA_FMT,
                _pad(msg.msg_id, 36),
                msg.timestamp_s,
                _pad(msg.drone_id, 32),
                msg.position[0], msg.position[1], msg.position[2],
                _pad(msg.emergency_type, 20),
                _pad(msg.severity, 10),
                _pad(msg.recommended_action, 16),
                msg.affected_radius_m,
                _pad(msg.msg_type, 8),
            )
        raise TypeError(f"지원하지 않는 메시지 타입: {type(msg).__name__}")

    @staticmethod
    def decode_binary(data: bytes) -> V2XMessageUnion:
        """compact binary 에서 메시지를 복원한다."""
        if len(data) == _BSM_SIZE:
            fields = struct.unpack(_BSM_FMT, data)
            msg_type_raw = _unpad(fields[-1])
            if msg_type_raw == BSM:
                return DroneBasicSafetyMessage(
                    msg_id=_unpad(fields[0]),
                    msg_type=BSM,
                    timestamp_s=fields[1],
                    drone_id=_unpad(fields[2]),
                    position=(fields[3], fields[4], fields[5]),
                    velocity=(fields[6], fields[7], fields[8]),
                    heading_deg=fields[9],
                    altitude_m=fields[10],
                    speed_ms=fields[11],
                    intent=_unpad(fields[12]),
                    battery_pct=fields[13],
                    accuracy_m=fields[14],
                    ttl_hops=fields[15],
                )
        if len(data) == _EVA_SIZE:
            fields = struct.unpack(_EVA_FMT, data)
            msg_type_raw = _unpad(fields[-1])
            if msg_type_raw == EVA:
                return EmergencyAlert(
                    msg_id=_unpad(fields[0]),
                    msg_type=EVA,
                    timestamp_s=fields[1],
                    drone_id=_unpad(fields[2]),
                    position=(fields[3], fields[4], fields[5]),
                    emergency_type=_unpad(fields[6]),
                    severity=_unpad(fields[7]),
                    recommended_action=_unpad(fields[8]),
                    affected_radius_m=fields[9],
                )
        raise ValueError(
            f"바이너리 디코딩 실패: 데이터 길이 {len(data)} "
            f"(BSM={_BSM_SIZE}, EVA={_EVA_SIZE})"
        )

    @staticmethod
    def binary_size(msg_type: str) -> int:
        """지정된 msg_type 의 예상 바이너리 크기를 반환한다."""
        if msg_type == BSM:
            return _BSM_SIZE
        if msg_type == EVA:
            return _EVA_SIZE
        raise ValueError(f"알 수 없는 msg_type: {msg_type!r}")


# ── 채널 시뮬레이션 ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class V2XChannelStats:
    """V2X 채널 통계 — 전송·수신·손실 카운트."""

    total_sent: int
    total_received: int
    total_lost: int
    delivery_rate: float  # 0.0 ~ 1.0


class V2XChannel:
    """V2X 브로드캐스트 채널 시뮬레이션.

    범위 기반 수신 필터링 + 확률적 패킷 손실을 결정적으로 모델링한다.
    """

    def __init__(
        self,
        range_m: float = 500.0,
        loss_rate: float = 0.0,
        seed: int = 42,
    ) -> None:
        self._range_m = range_m
        self._loss_rate = loss_rate
        self._rng = np.random.default_rng(seed)
        self._total_sent = 0
        self._total_received = 0
        self._total_lost = 0

    def broadcast(
        self,
        sender_pos: tuple[float, float, float],
        msg: V2XMessageUnion,
        all_drones: list[tuple[str, tuple[float, float, float]]],
    ) -> list[tuple[str, V2XMessageUnion]]:
        """메시지를 브로드캐스트하고 수신 성공한 드론 목록을 반환한다.

        Args:
            sender_pos: 송신자 위치 (x, y, z).
            msg: 전송할 V2X 메시지.
            all_drones: (drone_id, position) 쌍 목록 (수신 후보).

        Returns:
            수신 성공한 (drone_id, msg) 쌍 리스트.
        """
        received: list[tuple[str, V2XMessageUnion]] = []

        for drone_id, pos in all_drones:
            self._total_sent += 1

            # 거리 필터링
            dx = sender_pos[0] - pos[0]
            dy = sender_pos[1] - pos[1]
            dz = sender_pos[2] - pos[2]
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)

            if dist > self._range_m:
                self._total_lost += 1
                continue

            # 확률적 패킷 손실
            if self._loss_rate > 0.0 and self._rng.random() < self._loss_rate:
                self._total_lost += 1
                continue

            self._total_received += 1
            received.append((drone_id, msg))

        return received

    def stats(self) -> V2XChannelStats:
        """현재 채널 통계를 반환한다."""
        rate = (
            1.0
            if self._total_sent == 0
            else self._total_received / self._total_sent
        )
        return V2XChannelStats(
            total_sent=self._total_sent,
            total_received=self._total_received,
            total_lost=self._total_lost,
            delivery_rate=rate,
        )


# ── 예제 팩토리 ──────────────────────────────────────────────────────────


def example_bsm() -> DroneBasicSafetyMessage:
    """표준 BSM 예제를 생성한다."""
    return DroneBasicSafetyMessage(
        msg_id="bsm-example-001",
        msg_type=BSM,
        timestamp_s=10.5,
        drone_id="D-001",
        position=(100.0, 200.0, 50.0),
        velocity=(5.0, 0.0, -1.0),
        heading_deg=90.0,
        altitude_m=50.0,
        speed_ms=5.1,
        intent="cruise",
        battery_pct=87.4,
        accuracy_m=1.5,
        ttl_hops=1,
    )


def example_eva() -> EmergencyAlert:
    """표준 EVA 예제를 생성한다."""
    return EmergencyAlert(
        msg_id="eva-example-001",
        msg_type=EVA,
        timestamp_s=12.0,
        drone_id="D-003",
        position=(150.0, 300.0, 30.0),
        emergency_type="low_battery",
        severity="warning",
        recommended_action="avoid_area",
        affected_radius_m=100.0,
    )


# ── CLI ──────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    """CLI 엔트리포인트 — 예제 생성·인코딩·바이너리 크기 조회."""
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="SDACS V2X 메시지 규격 (GENESIS Phase 364)",
    )
    parser.add_argument("--example-bsm", action="store_true", help="BSM 예제 출력")
    parser.add_argument("--example-eva", action="store_true", help="EVA 예제 출력")
    parser.add_argument(
        "--encode", action="store_true",
        help="BSM+EVA 예제의 JSON 인코딩 라운드트립 검증",
    )
    parser.add_argument(
        "--binary-size", action="store_true",
        help="각 메시지 타입의 바이너리 크기 출력",
    )
    args = parser.parse_args(argv)

    if not any([args.example_bsm, args.example_eva, args.encode, args.binary_size]):
        parser.print_help()
        return 0

    codec = V2XCodec()

    if args.example_bsm:
        bsm = example_bsm()
        data = codec.encode(bsm)
        print(json.dumps(data, indent=2, ensure_ascii=False))

    if args.example_eva:
        eva = example_eva()
        data = codec.encode(eva)
        print(json.dumps(data, indent=2, ensure_ascii=False))

    if args.encode:
        bsm = example_bsm()
        eva = example_eva()
        for label, msg in [("BSM", bsm), ("EVA", eva)]:
            encoded = codec.encode(msg)
            decoded = codec.decode(encoded)
            ok = decoded == msg
            print(f"{label} JSON round-trip: {'PASS' if ok else 'FAIL'}")
            binary = codec.encode_binary(msg)
            decoded_bin = codec.decode_binary(binary)
            ok_bin = decoded_bin == msg
            print(f"{label} binary round-trip: {'PASS' if ok_bin else 'FAIL'} ({len(binary)} bytes)")

    if args.binary_size:
        for mt in [BSM, EVA]:
            print(f"{mt.upper()}: {codec.binary_size(mt)} bytes")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())

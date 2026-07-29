"""GENESIS Phase 364: 드론↔드론 직접 교신 V2X 메시지 와이어 스펙 (BSM 유사 포맷).

기존 `simulation/v2x_communication.py` 는 V2X *시스템/채널* 계층(전달률·지연·브로드캐스트)을
모델링하고 `V2XMessage` 를 메모리 내 데이터클래스로 다루지만, **인스턴스/구현 간 상호운용
가능한 정규 와이어 포맷**(고정소수점 필드 인코딩·결정적 직렬화·범위 검증·무결성 체크섬·
왕복 보장)은 정의하지 않는다. 본 모듈이 그 공백을 메운다.

SAE J2735 BSM(Basic Safety Message)의 고정소수점·고정 길이 프레임 설계를 군집 드론의
로컬 ENU(동-북-상) 좌표계에 맞춰 차용한다:

  * **고정소수점 양자화** — 위치 1 cm(int32), 속도 0.02 m/s(int16), 기수 0.0125°(uint16).
    부동소수 비트 표현의 플랫폼 의존성을 제거해 인스턴스 간 *바이트 동일* 직렬화를 보장.
  * **고정 길이 프레임** — magic(2) + version(1) + type(1) + station_id(2) + seq(2) +
    timestamp_ms(4) + pos x/y/z(4·3) + vel x/y/z(2·3) + heading(2) = `_BODY_FMT`,
    뒤에 CRC-32(4) 무결성 트레일러. 총 길이 불변.
  * **결정적·무작위성 0** — 같은 메시지는 항상 동일 바이트열로 인코딩된다.

핵심 불변식(테스트로 고정):
  1. ``decode(encode(m)) == m`` (양자화된 필드는 정확히 일치 — 왕복 항등).
  2. 양자화 오차는 해상도의 절반 이하로 유계(`|복원값 - 원본| <= 0.5*해상도`).
  3. 인코딩은 결정적 — 반복 인코딩은 바이트 동일.
  4. 프레임은 고정 길이(`FRAME_SIZE`)이며 CRC 트레일러가 단일 비트 변조도 검출.
  5. 정규 dict(`to_canonical_dict`)의 키 순서는 생성 방식과 무관하게 고정.
  6. 범위를 벗어난 위치·속도·기수·식별자는 생성 시 `ValueError` 로 fail-fast.
  7. magic/version 불일치 디코딩은 `ValueError` (전방 비호환 거부).

`v2x_communication.V2XMessage` 와는 `from_v2x_message`/`to_v2x_message` 어댑터로 연결하되
해당 모듈을 *읽기만* 하는 순수 추가 계층이다. 외부 네트워크 없이 동작한다.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from simulation.v2x_communication import V2XMessage

# --- 와이어 상수 (스펙 고정값) ----------------------------------------------

PROTOCOL_VERSION = 1
MAGIC = 0x5344  # 'SD' (SDACS) — 프레임 식별

# 고정소수점 해상도 (SAE J2735 정신을 드론 로컬 ENU 에 적용)
POSITION_RES_M = 0.01      # 1 cm, int32 → ±21,474,836 cm ≈ ±214 km
VELOCITY_RES_MS = 0.02     # 0.02 m/s, int16 → ±655.34 m/s
HEADING_RES_DEG = 0.0125   # 0.0125°, uint16 정수; 입력은 [0, 360) 정규화 후 저장

# 양자화 정수 필드의 유효 범위 (struct 가 던지기 전에 의미 있는 메시지로 검증)
_POS_MIN, _POS_MAX = -(2**31), 2**31 - 1          # int32
_VEL_MIN, _VEL_MAX = -(2**15), 2**15 - 1          # int16
_U16_MIN, _U16_MAX = 0, 2**16 - 1                  # uint16
_U32_MAX = 2**32 - 1                               # uint32

# 본문 레이아웃: big-endian, 고정 길이
#   magic(H) version(B) type(B) station(H) seq(H) ts(I) x(i) y(i) z(i) vx(h) vy(h) vz(h) hdg(H)
_BODY_FMT = ">HBBHHIiiihhhH"
_BODY_SIZE = struct.calcsize(_BODY_FMT)
_CRC_FMT = ">I"
FRAME_SIZE = _BODY_SIZE + struct.calcsize(_CRC_FMT)

# 메시지 타입 코드 (v2x_communication.MessageType 와 이름 정렬, 와이어는 정수 코드 사용)
MSG_TYPE_CODES: dict[str, int] = {
    "basic_safety_message": 0,
    "cooperative_awareness": 1,
    "decentralized_event_notification": 2,
    "collective_perception": 3,
    "heartbeat": 4,
}
_CODE_TO_TYPE = {code: name for name, code in MSG_TYPE_CODES.items()}


def _quantize(value: float, resolution: float, lo: int, hi: int, field: str) -> int:
    """물리값을 고정소수점 정수로 양자화한다(round-half-to-even, 결정적)."""
    q = round(value / resolution)
    if not (lo <= q <= hi):
        raise ValueError(
            f"{field}={value} 가 와이어 표현 범위를 벗어남 "
            f"(양자화 {q} ∉ [{lo}, {hi}])"
        )
    return q


def _dequantize(q: int, resolution: float) -> float:
    """고정소수점 정수를 물리값으로 복원한다."""
    return q * resolution


def _normalize_heading(heading_deg: float) -> float:
    """기수를 [0, 360) 으로 정규화한다(360° → 0°)."""
    return heading_deg % 360.0


@dataclass(frozen=True)
class BsmMessage:
    """드론 V2X BSM 유사 메시지의 정규 표현 (불변).

    물리 단위 필드를 보관하되, 와이어 직렬화 시 고정소수점으로 양자화되므로
    ``decode(encode(m))`` 는 양자화된 값과 정확히 일치한다(원본의 양자화 잔차는 버려짐).
    """

    station_id: int           # 0..65535, 송신 드론 식별자
    sequence: int             # 0..65535, 순환 시퀀스 번호
    timestamp_ms: int         # 0..2^32-1, 메시지 생성 시각(ms)
    x_m: float                # 로컬 ENU 동 (m)
    y_m: float                # 로컬 ENU 북 (m)
    z_m: float                # 로컬 ENU 상 (m)
    vx_ms: float = 0.0        # 속도 동 (m/s)
    vy_ms: float = 0.0        # 속도 북 (m/s)
    vz_ms: float = 0.0        # 속도 상 (m/s)
    heading_deg: float = 0.0  # 기수 (0..360, 생성 시 정규화)
    msg_type: str = "basic_safety_message"

    def __post_init__(self) -> None:
        # 정수 필드는 struct 가 던지기 전에 타입을 강제(float 가 범위 검사를 통과해
        # encode() 에서 불투명한 struct.error 로 터지는 것을 차단).
        for name in ("station_id", "sequence", "timestamp_ms"):
            if not isinstance(getattr(self, name), int):
                raise ValueError(f"{name} 는 int 여야 함: {getattr(self, name)!r}")
        if not (_U16_MIN <= self.station_id <= _U16_MAX):
            raise ValueError(f"station_id={self.station_id} ∉ [0, 65535]")
        if not (_U16_MIN <= self.sequence <= _U16_MAX):
            raise ValueError(f"sequence={self.sequence} ∉ [0, 65535]")
        if not (0 <= self.timestamp_ms <= _U32_MAX):
            raise ValueError(f"timestamp_ms={self.timestamp_ms} ∉ [0, {_U32_MAX}]")
        if self.msg_type not in MSG_TYPE_CODES:
            raise ValueError(f"미지원 msg_type: {self.msg_type!r}")
        # 기수 정규화(frozen 이므로 object.__setattr__ 로 후처리)
        object.__setattr__(self, "heading_deg", _normalize_heading(self.heading_deg))
        # 물리 필드를 한 번만 양자화해 캐시(범위 초과 시 여기서 fail-fast).
        # frozen·불변이므로 이후 encode/dict 는 재양자화 없이 이 튜플을 재사용.
        object.__setattr__(self, "_wire", self._encode_fields())

    def _encode_fields(self) -> tuple[int, ...]:
        """물리 필드를 와이어 정수 튜플로 양자화한다(범위 검증 포함)."""
        return (
            _quantize(self.x_m, POSITION_RES_M, _POS_MIN, _POS_MAX, "x_m"),
            _quantize(self.y_m, POSITION_RES_M, _POS_MIN, _POS_MAX, "y_m"),
            _quantize(self.z_m, POSITION_RES_M, _POS_MIN, _POS_MAX, "z_m"),
            _quantize(self.vx_ms, VELOCITY_RES_MS, _VEL_MIN, _VEL_MAX, "vx_ms"),
            _quantize(self.vy_ms, VELOCITY_RES_MS, _VEL_MIN, _VEL_MAX, "vy_ms"),
            _quantize(self.vz_ms, VELOCITY_RES_MS, _VEL_MIN, _VEL_MAX, "vz_ms"),
            _quantize(self.heading_deg, HEADING_RES_DEG, _U16_MIN, _U16_MAX, "heading_deg"),
        )

    def encode(self) -> bytes:
        """정규 고정 길이 프레임으로 직렬화한다(CRC-32 무결성 트레일러 포함, 결정적)."""
        xi, yi, zi, vxi, vyi, vzi, hdg = self._wire
        body = struct.pack(
            _BODY_FMT,
            MAGIC,
            PROTOCOL_VERSION,
            MSG_TYPE_CODES[self.msg_type],
            self.station_id,
            self.sequence,
            self.timestamp_ms,
            xi, yi, zi, vxi, vyi, vzi, hdg,
        )
        crc = zlib.crc32(body) & 0xFFFFFFFF
        return body + struct.pack(_CRC_FMT, crc)

    def to_canonical_dict(self) -> dict:
        """결정적 키 순서의 정규 dict 로 변환한다(JSON 상호운용용).

        값은 *복원된*(왕복 후) 물리값이라, 양자화를 거친 표현이 명시적으로 드러난다.
        """
        xi, yi, zi, vxi, vyi, vzi, hdg = self._wire
        # 키 순서는 와이어 레이아웃과 동일하게 고정
        return {
            "protocol_version": PROTOCOL_VERSION,
            "msg_type": self.msg_type,
            "station_id": self.station_id,
            "sequence": self.sequence,
            "timestamp_ms": self.timestamp_ms,
            "x_m": _dequantize(xi, POSITION_RES_M),
            "y_m": _dequantize(yi, POSITION_RES_M),
            "z_m": _dequantize(zi, POSITION_RES_M),
            "vx_ms": _dequantize(vxi, VELOCITY_RES_MS),
            "vy_ms": _dequantize(vyi, VELOCITY_RES_MS),
            "vz_ms": _dequantize(vzi, VELOCITY_RES_MS),
            "heading_deg": _dequantize(hdg, HEADING_RES_DEG),
        }


def decode(frame: bytes) -> BsmMessage:
    """정규 프레임을 `BsmMessage` 로 역직렬화한다(magic·version·CRC 검증)."""
    if len(frame) != FRAME_SIZE:
        raise ValueError(f"프레임 길이 {len(frame)} != 기대 {FRAME_SIZE}")
    body, trailer = frame[:_BODY_SIZE], frame[_BODY_SIZE:]
    (crc_expected,) = struct.unpack(_CRC_FMT, trailer)
    crc_actual = zlib.crc32(body) & 0xFFFFFFFF
    if crc_actual != crc_expected:
        raise ValueError("CRC 불일치 — 프레임 손상 또는 변조")
    (
        magic, version, type_code, station_id, sequence, ts,
        xi, yi, zi, vxi, vyi, vzi, hdg,
    ) = struct.unpack(_BODY_FMT, body)
    if magic != MAGIC:
        raise ValueError(f"magic 0x{magic:04X} != 0x{MAGIC:04X}")
    if version != PROTOCOL_VERSION:
        raise ValueError(f"미지원 protocol_version: {version}")
    if type_code not in _CODE_TO_TYPE:
        raise ValueError(f"미지원 msg_type 코드: {type_code}")
    return BsmMessage(
        station_id=station_id,
        sequence=sequence,
        timestamp_ms=ts,
        x_m=_dequantize(xi, POSITION_RES_M),
        y_m=_dequantize(yi, POSITION_RES_M),
        z_m=_dequantize(zi, POSITION_RES_M),
        vx_ms=_dequantize(vxi, VELOCITY_RES_MS),
        vy_ms=_dequantize(vyi, VELOCITY_RES_MS),
        vz_ms=_dequantize(vzi, VELOCITY_RES_MS),
        heading_deg=_dequantize(hdg, HEADING_RES_DEG),
        msg_type=_CODE_TO_TYPE[type_code],
    )


# --- v2x_communication.V2XMessage 어댑터 (해당 모듈 읽기 전용) --------------


def from_v2x_message(msg: V2XMessage, station_id: int, sequence: int) -> BsmMessage:
    """`v2x_communication.V2XMessage` 를 정규 BSM 메시지로 변환한다.

    `V2XMessage.sender` 는 문자열이라 와이어 정수 식별자(station_id)를 명시 인자로 받는다.
    position/velocity 는 길이 ≥3 의 인덱서블(np.ndarray 등)로 가정한다.
    """
    pos = msg.position
    vel = msg.velocity
    msg_type = getattr(msg.msg_type, "value", str(msg.msg_type))
    if msg_type not in MSG_TYPE_CODES:
        raise ValueError(f"V2XMessage.msg_type 를 와이어 코드로 매핑 불가: {msg_type!r}")
    return BsmMessage(
        station_id=station_id,
        sequence=sequence,
        timestamp_ms=int(round(msg.timestamp * 1000.0)),
        x_m=float(pos[0]),
        y_m=float(pos[1]),
        z_m=float(pos[2]),
        vx_ms=float(vel[0]),
        vy_ms=float(vel[1]),
        vz_ms=float(vel[2]),
        msg_type=msg_type,
    )

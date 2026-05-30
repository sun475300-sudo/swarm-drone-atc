"""RTK-GPS RTCM3 파서 + AirspaceController 피드백 모듈."""

from __future__ import annotations

from dataclasses import dataclass

# RTCM3 프리앰블 바이트
_RTCM3_PREAMBLE = 0xD3

# CRC-24Q 생성 다항식
_CRC24Q_POLY = 0x1864CFB


def crc24q(data: bytes) -> int:
    """RTCM3에서 사용하는 CRC-24Q를 계산한다.

    Args:
        data: CRC 계산 대상 바이트 시퀀스.

    Returns:
        24비트 CRC 정수.
    """
    crc = 0
    for byte in data:
        crc ^= byte << 16
        for _ in range(8):
            crc <<= 1
            if crc & 0x1000000:
                crc ^= _CRC24Q_POLY
    return crc & 0xFFFFFF


@dataclass
class RTCMMessage:
    """파싱된 RTCM3 메시지."""

    msg_type: int      # 메시지 타입 번호 (예: 1005, 1074)
    payload: bytes     # 헤더·CRC 제외 페이로드
    crc_ok: bool       # CRC 검증 통과 여부


def parse_rtcm3(data: bytes) -> RTCMMessage | None:
    """RTCM3 프레임 1개를 파싱한다.

    RTCM3 프레임 구조:
      [0]     0xD3          프리앰블 (1 byte)
      [1-2]   reserved(6b) + length(10b)
      [3..]   payload       (length bytes)
      [-3:]   CRC-24Q       (3 bytes)

    Args:
        data: 최소 1개의 RTCM3 프레임을 포함하는 바이트.

    Returns:
        RTCMMessage 또는 파싱 실패 시 None.
    """
    if len(data) < 6:  # 프리앰블(1) + 길이(2) + 최소 페이로드(0) + CRC(3)
        return None

    if data[0] != _RTCM3_PREAMBLE:
        return None

    # 상위 2비트는 예약 필드, 하위 10비트가 페이로드 길이
    length = ((data[1] & 0x03) << 8) | data[2]

    total_len = 3 + length + 3  # 헤더(3) + 페이로드 + CRC(3)
    if len(data) < total_len:
        return None

    header_and_payload = data[: 3 + length]
    received_crc_bytes = data[3 + length: 3 + length + 3]
    received_crc = (
        (received_crc_bytes[0] << 16)
        | (received_crc_bytes[1] << 8)
        | received_crc_bytes[2]
    )
    computed_crc = crc24q(header_and_payload)
    crc_ok = received_crc == computed_crc

    payload = bytes(data[3: 3 + length])

    # 메시지 타입: 페이로드 첫 12비트
    if len(payload) >= 2:
        msg_type = (payload[0] << 4) | (payload[1] >> 4)
    else:
        msg_type = 0

    return RTCMMessage(msg_type=msg_type, payload=payload, crc_ok=crc_ok)


class RTKGPSHandler:
    """RTCM3 스트림을 처리하고 AirspaceController에 RTK 정보를 제공한다."""

    def __init__(self) -> None:
        self._buffer = bytearray()
        self._last_message: RTCMMessage | None = None
        self.processed_count = 0
        self.error_count = 0

    def process(self, raw: bytes) -> RTCMMessage | None:
        """원시 바이트를 버퍼에 추가하고 RTCM3 메시지를 파싱한다.

        Args:
            raw: 수신된 원시 바이트 (부분 프레임 허용).

        Returns:
            완성된 RTCMMessage 또는 아직 완성 안 됐으면 None.
        """
        self._buffer.extend(raw)

        # 프리앰블 검색
        while self._buffer:
            if self._buffer[0] != _RTCM3_PREAMBLE:
                self._buffer.pop(0)
                self.error_count += 1
                continue

            msg = parse_rtcm3(bytes(self._buffer))
            if msg is None:
                # 데이터 부족 — 더 기다림
                break

            # 소비된 바이트 제거
            if len(self._buffer) >= 6:
                length = ((self._buffer[1] & 0x03) << 8) | self._buffer[2]
                consumed = 3 + length + 3
                self._buffer = self._buffer[consumed:]

            self.processed_count += 1
            self._last_message = msg
            return msg

        return None

    @property
    def last_message(self) -> RTCMMessage | None:
        """가장 최근에 파싱 성공한 메시지."""
        return self._last_message

"""
통신 품질 시뮬레이션
====================
거리 기반 신호 감쇠, 패킷 손실률, 지연 모델링.
통신 품질 저하 시 자동 경고 및 중계 추천.

사용법:
    comm = CommQualitySimulator()
    comm.update_link("drone_1", position=(100, 200, 50), t=10.0)
    quality = comm.get_quality("drone_1")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class LinkMetrics:
    """통신 링크 메트릭"""
    drone_id: str
    t: float
    signal_strength_dbm: float  # dBm
    packet_loss_rate: float  # 0~1
    latency_ms: float  # ms
    distance_m: float
    quality_score: float  # 0~100
    status: str = "GOOD"  # GOOD, DEGRADED, POOR, LOST


@dataclass
class CommConfig:
    """통신 파라미터"""
    base_station: tuple[float, float, float] = (0.0, 0.0, 0.0)
    max_range_m: float = 5000.0
    tx_power_dbm: float = 20.0
    frequency_ghz: float = 2.4
    path_loss_exponent: float = 2.8  # 도심 환경
    noise_floor_dbm: float = -90.0
    min_rssi_dbm: float = -80.0
    base_latency_ms: float = 5.0
    max_latency_ms: float = 500.0
    packet_size: int = 256  # bytes


class CommQualitySimulator:
    """
    통신 품질 시뮬레이터.

    거리 기반 경로 손실 모델 + 확률적 패킷 손실 + 거리 비례 지연.
    """

    def __init__(
        self,
        config: CommConfig | None = None,
        rng_seed: int = 42,
    ) -> None:
        self.config = config or CommConfig()
        self._rng = np.random.default_rng(rng_seed)

        # drone_id -> 최신 위치
        self._positions: dict[str, np.ndarray] = {}
        # drone_id -> 링크 이력
        self._history: dict[str, list[LinkMetrics]] = {}
        self._max_history = 300

    def update_link(
        self,
        drone_id: str,
        position: tuple[float, float, float],
        t: float,
    ) -> LinkMetrics:
        """드론 위치 업데이트 및 링크 품질 계산"""
        pos = np.array(position, dtype=float)
        self._positions[drone_id] = pos

        base = np.array(self.config.base_station, dtype=float)
        distance = float(np.linalg.norm(pos - base))

        # 경로 손실 (log-distance model)
        rssi = self._calculate_rssi(distance)

        # 패킷 손실률
        plr = self._calculate_packet_loss(rssi, distance)

        # 지연
        latency = self._calculate_latency(distance, plr)

        # 품질 점수
        quality = self._calculate_quality(rssi, plr, latency)

        # 상태 결정
        status = self._determine_status(quality, distance)

        metrics = LinkMetrics(
            drone_id=drone_id,
            t=t,
            signal_strength_dbm=rssi,
            packet_loss_rate=plr,
            latency_ms=latency,
            distance_m=distance,
            quality_score=quality,
            status=status,
        )

        if drone_id not in self._history:
            self._history[drone_id] = []
        self._history[drone_id].append(metrics)
        if len(self._history[drone_id]) > self._max_history:
            self._history[drone_id] = self._history[drone_id][-self._max_history:]

        return metrics

    def get_quality(self, drone_id: str) -> LinkMetrics | None:
        """최신 링크 품질"""
        history = self._history.get(drone_id, [])
        return history[-1] if history else None

    def get_all_qualities(self) -> dict[str, LinkMetrics]:
        """전체 드론 최신 링크 품질"""
        result = {}
        for did in self._history:
            q = self.get_quality(did)
            if q:
                result[did] = q
        return result

    def drones_in_danger(self) -> list[str]:
        """통신 품질 위험 드론 목록"""
        danger = []
        for did, history in self._history.items():
            if history and history[-1].status in ("POOR", "LOST"):
                danger.append(did)
        return danger

    def average_quality(self) -> float:
        """전체 평균 품질 점수"""
        scores = []
        for did in self._history:
            q = self.get_quality(did)
            if q:
                scores.append(q.quality_score)
        return float(np.mean(scores)) if scores else 0.0

    def link_budget(self, drone_id: str) -> dict[str, float]:
        """링크 버짓 분석"""
        q = self.get_quality(drone_id)
        if not q:
            return {}

        return {
            "tx_power_dbm": self.config.tx_power_dbm,
            "path_loss_db": self.config.tx_power_dbm - q.signal_strength_dbm,
            "rssi_dbm": q.signal_strength_dbm,
            "noise_floor_dbm": self.config.noise_floor_dbm,
            "snr_db": q.signal_strength_dbm - self.config.noise_floor_dbm,
            "margin_db": q.signal_strength_dbm - self.config.min_rssi_dbm,
            "distance_m": q.distance_m,
        }

    def recommend_relay(self, drone_id: str) -> bool:
        """중계 드론 필요 여부"""
        q = self.get_quality(drone_id)
        if not q:
            return False
        return q.status in ("POOR", "LOST") or q.quality_score < 30.0

    def inter_drone_link(
        self,
        drone_a: str,
        drone_b: str,
        t: float,
    ) -> LinkMetrics | None:
        """드론 간 통신 링크 품질"""
        pos_a = self._positions.get(drone_a)
        pos_b = self._positions.get(drone_b)
        if pos_a is None or pos_b is None:
            return None

        distance = float(np.linalg.norm(pos_a - pos_b))
        # 드론 간 통신은 저전력 (tx_power - 10dB)
        rssi = self._calculate_rssi(distance, tx_offset=-10.0)
        plr = self._calculate_packet_loss(rssi, distance)
        latency = self._calculate_latency(distance, plr)
        quality = self._calculate_quality(rssi, plr, latency)
        status = self._determine_status(quality, distance)

        return LinkMetrics(
            drone_id=f"{drone_a}<->{drone_b}",
            t=t,
            signal_strength_dbm=rssi,
            packet_loss_rate=plr,
            latency_ms=latency,
            distance_m=distance,
            quality_score=quality,
            status=status,
        )

    def _calculate_rssi(self, distance: float, tx_offset: float = 0.0) -> float:
        """경로 손실 기반 RSSI 계산 (log-distance model)"""
        if distance < 1.0:
            distance = 1.0

        tx = self.config.tx_power_dbm + tx_offset
        # 자유 공간 기준 1m 손실
        fspl_1m = 20 * np.log10(self.config.frequency_ghz * 1e9) + 20 * np.log10(1.0) - 147.55
        # log-distance 경로 손실
        path_loss = fspl_1m + 10 * self.config.path_loss_exponent * np.log10(distance)
        # 페이딩 (랜덤 변동 ±3dB)
        fading = self._rng.normal(0, 1.5)

        rssi = tx - path_loss + fading
        return float(rssi)

    def _calculate_packet_loss(self, rssi: float, distance: float) -> float:
        """RSSI 기반 패킷 손실률"""
        if rssi > self.config.min_rssi_dbm + 10:
            base_plr = 0.001  # 0.1%
        elif rssi > self.config.min_rssi_dbm:
            # 선형 증가
            margin = rssi - self.config.min_rssi_dbm
            base_plr = 0.001 + (10 - margin) * 0.01
        else:
            # 급격 증가
            deficit = self.config.min_rssi_dbm - rssi
            base_plr = min(0.5, 0.1 + deficit * 0.02)

        # 거리 비례 추가 손실
        range_ratio = distance / self.config.max_range_m
        if range_ratio > 0.8:
            base_plr += (range_ratio - 0.8) * 0.5

        return float(min(1.0, max(0.0, base_plr)))

    def _calculate_latency(self, distance: float, plr: float) -> float:
        """거리 및 재전송 기반 지연"""
        # 전파 지연 (빛의 속도)
        propagation = distance / 3e8 * 1000  # ms

        # 기본 처리 지연
        processing = self.config.base_latency_ms

        # 재전송 지연 (패킷 손실 시)
        avg_retransmits = plr / max(1 - plr, 0.01)
        retransmit_delay = avg_retransmits * 10.0  # 각 재전송 10ms

        # 랜덤 지터 (±2ms)
        jitter = abs(self._rng.normal(0, 1.0))

        total = propagation + processing + retransmit_delay + jitter
        return float(min(total, self.config.max_latency_ms))

    def _calculate_quality(
        self, rssi: float, plr: float, latency: float
    ) -> float:
        """종합 품질 점수 (0~100)"""
        # RSSI 점수 (0~40)
        rssi_range = self.config.tx_power_dbm - self.config.noise_floor_dbm
        rssi_norm = (rssi - self.config.noise_floor_dbm) / rssi_range
        rssi_score = max(0, min(40, rssi_norm * 40))

        # 패킷 손실 점수 (0~35)
        plr_score = max(0, 35 * (1 - plr * 5))

        # 지연 점수 (0~25)
        latency_norm = latency / self.config.max_latency_ms
        latency_score = max(0, 25 * (1 - latency_norm))

        return float(min(100.0, rssi_score + plr_score + latency_score))

    def _determine_status(self, quality: float, distance: float) -> str:
        """링크 상태 결정"""
        if distance > self.config.max_range_m:
            return "LOST"
        if quality >= 70:
            return "GOOD"
        if quality >= 40:
            return "DEGRADED"
        if quality >= 15:
            return "POOR"
        return "LOST"

    def summary(self) -> dict[str, Any]:
        """통신 품질 요약"""
        all_q = self.get_all_qualities()
        if not all_q:
            return {"total_drones": 0}

        statuses: dict[str, int] = {}
        for m in all_q.values():
            statuses[m.status] = statuses.get(m.status, 0) + 1

        qualities = [m.quality_score for m in all_q.values()]
        return {
            "total_drones": len(all_q),
            "avg_quality": round(float(np.mean(qualities)), 1),
            "min_quality": round(min(qualities), 1),
            "max_quality": round(max(qualities), 1),
            "by_status": statuses,
            "danger_count": len(self.drones_in_danger()),
        }

    def clear(self) -> None:
        self._positions.clear()
        self._history.clear()

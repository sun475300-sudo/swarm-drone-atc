"""
패시브 RF 탐지기 (Passive RF Detector)
======================================
실외 군집 환경에서 비협조 드론의 RF 방출(2.4/5.8GHz 영상·텔레메트리)을
다중 정적 패시브 수신 노드로 탐지·국지화.

영감:
- CMU "DensePose From WiFi" (arXiv:2301.00250)
- RuView (github.com/ruvnet/RuView) 멀티스태틱 CSI 융합

실내·저속 보행자 감지에 최적화된 원조 기법을 도플러 보정 및
자유공간 경로손실 모델로 재구성해 SDACS 안티드론 시나리오에 적용.

사용법:
    nodes = [RFNode("n1", 0, 0, 5), RFNode("n2", 1000, 0, 5),
             RFNode("n3", 0, 1000, 5), RFNode("n4", 1000, 1000, 5)]
    det = PassiveRFDetector(nodes=nodes, seed=42)
    det.add_emitter(RFEmitter("rogue1", 500, 300, 80, vx=15.0,
                              tx_power_w=0.1, freq_hz=2.4e9))
    contacts = det.scan(t=10.0)
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

SPEED_OF_LIGHT_MPS: float = 2.998e8
THERMAL_NOISE_DBM_PER_HZ: float = -174.0
DEFAULT_RX_BANDWIDTH_HZ: float = 20e6
DEFAULT_DETECTION_SNR_DB: float = 6.0
DEFAULT_NOISE_FIGURE_DB: float = 8.0
MIN_NODES_FOR_TDOA: int = 4


@dataclass
class RFEmitter:
    """RF 방출 드론 (비협조 표적)."""
    emitter_id: str
    x: float
    y: float
    z: float
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    tx_power_w: float = 0.1
    freq_hz: float = 2.4e9
    waveform_id: str = "generic_24g"


@dataclass
class RFNode:
    """지상 패시브 수신 노드."""
    node_id: str
    x: float
    y: float
    z: float = 5.0
    antenna_gain_dbi: float = 6.0


@dataclass
class RFDetection:
    """단일 노드의 단일 표적 탐지 측정."""
    node_id: str
    emitter_id: str
    timestamp: float
    rssi_dbm: float
    snr_db: float
    doppler_hz: float
    range_m: float


@dataclass
class RFContact:
    """다중 노드 융합 후 표적 컨택트."""
    emitter_id: str
    timestamp: float
    estimated_position: tuple[float, float, float]
    estimated_velocity_mps: float
    waveform_id: str
    contributing_nodes: list[str] = field(default_factory=list)
    confidence: float = 0.0
    position_error_m: float = 0.0


def _free_space_path_loss_db(distance_m: float, freq_hz: float) -> float:
    """자유공간 경로손실 (Friis equation)."""
    if distance_m <= 0:
        return 0.0
    wavelength = SPEED_OF_LIGHT_MPS / freq_hz
    return 20 * np.log10(4 * np.pi * distance_m / wavelength)


def _noise_floor_dbm(bandwidth_hz: float, noise_figure_db: float) -> float:
    """열잡음 + 수신기 잡음지수 합성 노이즈 플로어."""
    return THERMAL_NOISE_DBM_PER_HZ + 10 * np.log10(bandwidth_hz) + noise_figure_db


def _radial_velocity_mps(
    emitter: RFEmitter, node: RFNode
) -> tuple[float, float]:
    """노드 기준 방사 속도와 거리 반환."""
    dx = emitter.x - node.x
    dy = emitter.y - node.y
    dz = emitter.z - node.z
    r = float(np.sqrt(dx * dx + dy * dy + dz * dz))
    if r < 1e-6:
        return 0.0, r
    v_radial = (dx * emitter.vx + dy * emitter.vy + dz * emitter.vz) / r
    return v_radial, r


class PassiveRFDetector:
    """비협조 드론용 멀티스태틱 패시브 RF 탐지기.

    실외에서 도플러 시프트와 자유공간 손실을 적용한 RuView 영감 다중 정적 융합.
    실내 CSI 위상 정보 대신 RSSI + TDOA 다변측량으로 위치를 추정한다.
    """

    def __init__(
        self,
        nodes: list[RFNode],
        rx_bandwidth_hz: float = DEFAULT_RX_BANDWIDTH_HZ,
        detection_snr_db: float = DEFAULT_DETECTION_SNR_DB,
        noise_figure_db: float = DEFAULT_NOISE_FIGURE_DB,
        seed: int = 42,
    ) -> None:
        """인스턴스를 초기화한다."""
        if len(nodes) < 2:
            raise ValueError("패시브 RF 탐지에는 최소 2개 노드 필요")
        self.nodes: dict[str, RFNode] = {n.node_id: n for n in nodes}
        self.emitters: dict[str, RFEmitter] = {}
        self.rx_bandwidth_hz = rx_bandwidth_hz
        self.detection_snr_db = detection_snr_db
        self.noise_floor_dbm = _noise_floor_dbm(rx_bandwidth_hz, noise_figure_db)
        self.rng = np.random.default_rng(seed)
        self.detections: list[RFDetection] = []
        self.contacts: list[RFContact] = []

    def add_emitter(self, emitter: RFEmitter) -> None:
        """`emitter` 항목을 추가한다."""
        self.emitters[emitter.emitter_id] = emitter

    def remove_emitter(self, emitter_id: str) -> None:
        """`emitter` 상태를 정리한다."""
        self.emitters.pop(emitter_id, None)

    def _measure_one(
        self, emitter: RFEmitter, node: RFNode, t: float
    ) -> RFDetection | None:
        v_radial, r = _radial_velocity_mps(emitter, node)
        if r < 1.0:
            return None

        tx_power_dbm = 10 * np.log10(max(emitter.tx_power_w, 1e-12) * 1000)
        path_loss_db = _free_space_path_loss_db(r, emitter.freq_hz)
        rssi_dbm = tx_power_dbm + node.antenna_gain_dbi - path_loss_db
        rssi_dbm += float(self.rng.standard_normal()) * 2.0

        snr_db = rssi_dbm - self.noise_floor_dbm
        if snr_db < self.detection_snr_db:
            return None

        doppler_hz = -v_radial * emitter.freq_hz / SPEED_OF_LIGHT_MPS
        doppler_hz += float(self.rng.standard_normal()) * 5.0

        return RFDetection(
            node_id=node.node_id,
            emitter_id=emitter.emitter_id,
            timestamp=t,
            rssi_dbm=float(rssi_dbm),
            snr_db=float(snr_db),
            doppler_hz=float(doppler_hz),
            range_m=float(r),
        )

    def scan(self, t: float = 0.0) -> list[RFContact]:
        """모든 노드에서 모든 방출 드론 스캔 후 융합 컨택트 반환."""
        per_emitter: dict[str, list[RFDetection]] = {}
        for emitter in self.emitters.values():
            for node in self.nodes.values():
                det = self._measure_one(emitter, node, t)
                if det is None:
                    continue
                self.detections.append(det)
                per_emitter.setdefault(emitter.emitter_id, []).append(det)

        contacts: list[RFContact] = []
        for emitter_id, dets in per_emitter.items():
            contact = self._fuse(emitter_id, dets, t)
            if contact is not None:
                contacts.append(contact)
                self.contacts.append(contact)
        return contacts

    def _fuse(
        self, emitter_id: str, detections: list[RFDetection], t: float
    ) -> RFContact | None:
        if not detections:
            return None
        emitter = self.emitters[emitter_id]

        # RSSI 가중치 (선형 dB → 선형 전력비)
        weights = np.array([10 ** (d.snr_db / 10.0) for d in detections])
        weights /= max(weights.sum(), 1e-12)

        if len(detections) >= MIN_NODES_FOR_TDOA:
            position, pos_err = self._multilaterate(detections)
            confidence = float(min(1.0, len(detections) / len(self.nodes)))
        else:
            position, pos_err = self._weighted_centroid(detections, weights)
            confidence = float(0.4 * len(detections) / len(self.nodes))

        radial_speeds = np.array(
            [abs(d.doppler_hz * SPEED_OF_LIGHT_MPS / emitter.freq_hz)
             for d in detections]
        )
        v_estimate = float(np.average(radial_speeds, weights=weights))

        return RFContact(
            emitter_id=emitter_id,
            timestamp=t,
            estimated_position=position,
            estimated_velocity_mps=v_estimate,
            waveform_id=emitter.waveform_id,
            contributing_nodes=[d.node_id for d in detections],
            confidence=confidence,
            position_error_m=pos_err,
        )

    def _weighted_centroid(
        self, detections: list[RFDetection], weights: np.ndarray
    ) -> tuple[tuple[float, float, float], float]:
        positions = np.array([
            [self.nodes[d.node_id].x, self.nodes[d.node_id].y, self.nodes[d.node_id].z]
            for d in detections
        ])
        center = np.average(positions, axis=0, weights=weights)
        # 거친 추정: 가장 강한 노드 거리 사용
        strongest = max(detections, key=lambda d: d.snr_db)
        err = float(strongest.range_m * 0.4)
        return (float(center[0]), float(center[1]), float(center[2])), err

    def _multilaterate(
        self, detections: list[RFDetection]
    ) -> tuple[tuple[float, float, float], float]:
        """RSSI 기반 거리 추정 + 최소 자승 다변측량."""
        node_positions = np.array([
            [self.nodes[d.node_id].x, self.nodes[d.node_id].y, self.nodes[d.node_id].z]
            for d in detections
        ])
        ranges = np.array([d.range_m for d in detections])

        # 기준 노드 (가장 강한 신호)
        ref_idx = int(np.argmax([d.snr_db for d in detections]))
        ref = node_positions[ref_idx]
        ref_r = ranges[ref_idx]

        # 선형화: ||p - n_i||² - ||p - n_ref||² = r_i² - r_ref²
        # 2(n_ref - n_i)·p = r_i² - r_ref² - (||n_i||² - ||n_ref||²)
        rows = []
        rhs = []
        for i, (pos, r) in enumerate(zip(node_positions, ranges, strict=False)):
            if i == ref_idx:
                continue
            rows.append(2 * (ref - pos))
            rhs.append(r * r - ref_r * ref_r
                       - float(np.dot(pos, pos))
                       + float(np.dot(ref, ref)))
        a_matrix = np.array(rows)
        b_vector = np.array(rhs)
        try:
            solution, residuals, _, _ = np.linalg.lstsq(a_matrix, b_vector, rcond=None)
            err = float(np.sqrt(residuals[0])) if len(residuals) else float(ref_r * 0.2)
        except np.linalg.LinAlgError:
            return self._weighted_centroid(detections, np.ones(len(detections)) / len(detections))

        return (float(solution[0]), float(solution[1]), float(solution[2])), err

    def summary(self) -> dict:
        """현재 상태 요약을 반환한다."""
        return {
            "nodes": len(self.nodes),
            "emitters": len(self.emitters),
            "noise_floor_dbm": float(self.noise_floor_dbm),
            "detection_snr_db": self.detection_snr_db,
            "total_detections": len(self.detections),
            "total_contacts": len(self.contacts),
        }

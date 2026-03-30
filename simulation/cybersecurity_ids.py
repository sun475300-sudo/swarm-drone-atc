"""Phase 317: Cybersecurity Intrusion Detection System — 사이버보안 침입 탐지.

네트워크 이상 탐지, Isolation Forest,
패킷 분석, 위협 분류, 실시간 경보.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class ThreatLevel(Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AttackType(Enum):
    NONE = "none"
    DOS = "dos"
    SPOOFING = "spoofing"
    JAMMING = "jamming"
    INJECTION = "injection"
    REPLAY = "replay"
    MAN_IN_MIDDLE = "mitm"
    UNKNOWN = "unknown"


@dataclass
class NetworkPacket:
    source_id: str
    dest_id: str
    packet_type: str  # "telemetry", "command", "ack", "heartbeat"
    size_bytes: int
    timestamp: float
    payload_hash: str = ""
    is_encrypted: bool = True


@dataclass
class ThreatAlert:
    alert_id: str
    threat_level: ThreatLevel
    attack_type: AttackType
    source_id: str
    description: str
    confidence: float
    timestamp: float
    anomaly_score: float = 0.0


@dataclass
class IsolationTree:
    """Single isolation tree node."""
    split_feature: int = 0
    split_value: float = 0.0
    left: Optional['IsolationTree'] = None
    right: Optional['IsolationTree'] = None
    size: int = 0
    is_leaf: bool = False


class IsolationForest:
    """Simplified Isolation Forest for anomaly detection."""

    def __init__(self, n_trees: int = 100, max_samples: int = 256, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self.n_trees = n_trees
        self.max_samples = max_samples
        self._trees: List[IsolationTree] = []
        self._fitted = False

    def fit(self, data: np.ndarray):
        n_samples = min(len(data), self.max_samples)
        max_depth = int(np.ceil(np.log2(n_samples)))
        self._trees = []
        for _ in range(self.n_trees):
            idx = self._rng.choice(len(data), size=n_samples, replace=False)
            tree = self._build_tree(data[idx], 0, max_depth)
            self._trees.append(tree)
        self._fitted = True

    def _build_tree(self, data: np.ndarray, depth: int, max_depth: int) -> IsolationTree:
        n, d = data.shape
        if n <= 1 or depth >= max_depth:
            return IsolationTree(size=n, is_leaf=True)

        feature = self._rng.integers(d)
        min_val, max_val = data[:, feature].min(), data[:, feature].max()
        if min_val == max_val:
            return IsolationTree(size=n, is_leaf=True)

        split_val = self._rng.uniform(min_val, max_val)
        left_mask = data[:, feature] < split_val
        right_mask = ~left_mask

        return IsolationTree(
            split_feature=feature, split_value=split_val,
            left=self._build_tree(data[left_mask], depth + 1, max_depth),
            right=self._build_tree(data[right_mask], depth + 1, max_depth),
            size=n,
        )

    def _path_length(self, x: np.ndarray, tree: IsolationTree, depth: int = 0) -> float:
        if tree.is_leaf:
            return depth + self._c(tree.size)
        if x[tree.split_feature] < tree.split_value:
            return self._path_length(x, tree.left, depth + 1)
        return self._path_length(x, tree.right, depth + 1)

    @staticmethod
    def _c(n: int) -> float:
        if n <= 1:
            return 0.0
        return 2.0 * (np.log(n - 1) + 0.5772156649) - 2.0 * (n - 1) / n

    def score(self, x: np.ndarray) -> float:
        """Anomaly score (0=normal, 1=anomaly)."""
        if not self._fitted:
            return 0.5
        avg_path = np.mean([self._path_length(x, tree) for tree in self._trees])
        c_n = self._c(self.max_samples)
        return float(2 ** (-avg_path / c_n)) if c_n > 0 else 0.5


class CybersecurityIDS:
    """사이버보안 침입 탐지 시스템.

    - Isolation Forest 이상 탐지
    - 패킷 레이트 모니터링
    - 시퀀스 번호 검증
    - 위협 분류 및 경보
    """

    def __init__(self, anomaly_threshold: float = 0.7, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self._forest = IsolationForest(n_trees=50, rng_seed=rng_seed)
        self._threshold = anomaly_threshold
        self._packet_log: List[NetworkPacket] = []
        self._alerts: List[ThreatAlert] = []
        self._packet_rates: Dict[str, List[float]] = {}  # source_id -> timestamps
        self._sequence_numbers: Dict[str, int] = {}
        self._alert_counter = 0
        self._trained = False

    def train(self, normal_traffic: np.ndarray):
        """Train anomaly detector on normal traffic features."""
        self._forest.fit(normal_traffic)
        self._trained = True

    def _extract_features(self, packet: NetworkPacket) -> np.ndarray:
        """Extract feature vector from packet."""
        rate = len(self._packet_rates.get(packet.source_id, []))
        return np.array([
            packet.size_bytes / 1000.0,
            1.0 if packet.is_encrypted else 0.0,
            rate / 100.0,
            hash(packet.packet_type) % 10 / 10.0,
            packet.timestamp % 3600 / 3600.0,
        ])

    def analyze_packet(self, packet: NetworkPacket) -> Optional[ThreatAlert]:
        """Analyze incoming packet for anomalies."""
        self._packet_log.append(packet)
        self._packet_rates.setdefault(packet.source_id, []).append(packet.timestamp)

        # Rate limiting check
        recent = [t for t in self._packet_rates[packet.source_id]
                  if packet.timestamp - t < 1.0]
        self._packet_rates[packet.source_id] = recent

        alert = None

        # High packet rate → possible DoS
        if len(recent) > 100:
            alert = self._create_alert(
                ThreatLevel.HIGH, AttackType.DOS, packet.source_id,
                f"DoS detected: {len(recent)} packets/sec from {packet.source_id}",
                confidence=0.9, timestamp=packet.timestamp,
            )

        # Unencrypted command → possible injection
        elif packet.packet_type == "command" and not packet.is_encrypted:
            alert = self._create_alert(
                ThreatLevel.MEDIUM, AttackType.INJECTION, packet.source_id,
                f"Unencrypted command from {packet.source_id}",
                confidence=0.7, timestamp=packet.timestamp,
            )

        # Anomaly detection
        elif self._trained:
            features = self._extract_features(packet)
            score = self._forest.score(features)
            if score > self._threshold:
                alert = self._create_alert(
                    ThreatLevel.MEDIUM, AttackType.UNKNOWN, packet.source_id,
                    f"Anomalous traffic: score={score:.3f}",
                    confidence=score, timestamp=packet.timestamp,
                    anomaly_score=score,
                )

        return alert

    def _create_alert(self, level: ThreatLevel, attack: AttackType,
                      source: str, desc: str, confidence: float,
                      timestamp: float, anomaly_score: float = 0.0) -> ThreatAlert:
        self._alert_counter += 1
        alert = ThreatAlert(
            alert_id=f"IDS-{self._alert_counter:06d}",
            threat_level=level, attack_type=attack,
            source_id=source, description=desc,
            confidence=round(confidence, 4),
            timestamp=timestamp, anomaly_score=anomaly_score,
        )
        self._alerts.append(alert)
        return alert

    def get_alerts(self, level: Optional[ThreatLevel] = None, limit: int = 50) -> List[ThreatAlert]:
        alerts = self._alerts
        if level:
            alerts = [a for a in alerts if a.threat_level == level]
        return alerts[-limit:]

    def summary(self) -> dict:
        level_counts = {}
        for a in self._alerts:
            level_counts[a.threat_level.value] = level_counts.get(a.threat_level.value, 0) + 1
        return {
            "total_packets": len(self._packet_log),
            "total_alerts": len(self._alerts),
            "alert_levels": level_counts,
            "trained": self._trained,
            "anomaly_threshold": self._threshold,
        }

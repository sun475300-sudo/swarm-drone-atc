"""
CSI 어텐션 멀티스태틱 융합 (CSI Attention Multistatic Fusion)
=============================================================
RuView의 N×(N-1) 링크 어텐션 가중 평균 개념을 드론 군집 협업 인식에 적용.

원리:
- N개 드론이 같은 표적을 관측하면 N×(N-1)개 관측 쌍 링크가 만들어진다.
- 각 링크의 신뢰도는 두 드론의 신호 품질(SNR)과 기하학(베이스라인 길이)에
  의존한다.
- 어텐션 메커니즘으로 링크별 가중치를 학습 없이 결정론적으로 계산한다.

기존 cooperative_perception.MultiViewFusion의 단순 confidence 가중 평균보다
**기하학적 다이버시티**를 더 잘 반영한다. cooperative_perception이나
swarm_collaborative_perception 모듈에 보조 융합기로 플러그인할 수 있다.

사용법:
    fusion = CsiAttentionFusion()
    obs = [
        LinkObservation("d1", "d2", pos_estimate=(100, 200, 50), snr_db=20),
        LinkObservation("d1", "d3", pos_estimate=(102, 198, 51), snr_db=18),
        LinkObservation("d2", "d3", pos_estimate=(98, 202, 49), snr_db=22),
    ]
    drone_positions = {"d1": (0,0,80), "d2": (300,0,80), "d3": (0,300,80)}
    fused = fusion.fuse(obs, drone_positions)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

MIN_BASELINE_M: float = 5.0
TEMPERATURE_DEFAULT: float = 1.0


@dataclass
class LinkObservation:
    """드론 쌍 관측 (i, j) → 표적 위치 추정."""
    drone_a: str
    drone_b: str
    pos_estimate: tuple[float, float, float]
    snr_db: float
    timestamp: float = 0.0


@dataclass
class FusedEstimate:
    """어텐션 융합 결과."""
    position: tuple[float, float, float]
    confidence: float
    contributing_links: int
    attention_weights: list[float]
    geometric_diversity: float


class CsiAttentionFusion:
    """N×(N-1) 링크 어텐션 가중 평균 융합기.

    어텐션 점수는 다음 3가지 요인을 곱한다:
    1. 신호 품질 (두 드론 SNR의 기하평균)
    2. 베이스라인 기하 (적당한 길이일수록 위치 추정 정밀)
    3. 시간 동기 (최근 관측일수록 가중)
    """

    def __init__(
        self,
        temperature: float = TEMPERATURE_DEFAULT,
        optimal_baseline_m: float = 150.0,
        recency_decay_s: float = 5.0,
    ) -> None:
        """인스턴스를 초기화한다."""
        self.temperature = temperature
        self.optimal_baseline_m = optimal_baseline_m
        self.recency_decay_s = recency_decay_s

    def _baseline_score(
        self,
        drone_a: str,
        drone_b: str,
        drone_positions: dict[str, tuple[float, float, float]],
    ) -> float:
        if drone_a not in drone_positions or drone_b not in drone_positions:
            return 0.5
        pos_a = np.array(drone_positions[drone_a])
        pos_b = np.array(drone_positions[drone_b])
        baseline = float(np.linalg.norm(pos_a - pos_b))
        if baseline < MIN_BASELINE_M:
            return 0.1
        # 가우시안 기반 최적 베이스라인 선호도
        diff = baseline - self.optimal_baseline_m
        sigma = self.optimal_baseline_m * 0.6
        return float(np.exp(-(diff * diff) / (2 * sigma * sigma)))

    def _signal_score(self, snr_db: float) -> float:
        # SNR을 0~1로 정규화 (0dB → 0.0, 30dB → 1.0)
        return float(np.clip(snr_db / 30.0, 0.0, 1.0))

    def _recency_score(self, t_obs: float, t_now: float) -> float:
        if self.recency_decay_s <= 0:
            return 1.0
        dt = max(0.0, t_now - t_obs)
        return float(np.exp(-dt / self.recency_decay_s))

    def _attention_logits(
        self,
        observations: list[LinkObservation],
        drone_positions: dict[str, tuple[float, float, float]],
        t_now: float,
    ) -> np.ndarray:
        scores = []
        for obs in observations:
            sig = self._signal_score(obs.snr_db)
            geo = self._baseline_score(obs.drone_a, obs.drone_b, drone_positions)
            rec = self._recency_score(obs.timestamp, t_now)
            # 곱 결합 → 로그로 → softmax 입력
            combined = sig * geo * rec + 1e-9
            scores.append(np.log(combined))
        return np.array(scores)

    def _softmax(self, logits: np.ndarray) -> np.ndarray:
        if len(logits) == 0:
            return np.array([])
        scaled = logits / max(self.temperature, 1e-6)
        scaled -= scaled.max()
        exp = np.exp(scaled)
        return exp / exp.sum()

    def _geometric_diversity(
        self,
        observations: list[LinkObservation],
        drone_positions: dict[str, tuple[float, float, float]],
    ) -> float:
        """관측에 참여한 드론들의 공간 분산. 0~1로 정규화."""
        unique_drones = set()
        for obs in observations:
            unique_drones.add(obs.drone_a)
            unique_drones.add(obs.drone_b)
        positions = [
            drone_positions[d] for d in unique_drones if d in drone_positions
        ]
        if len(positions) < 2:
            return 0.0
        arr = np.array(positions)
        spread = float(np.linalg.norm(arr.std(axis=0)))
        return float(np.clip(spread / 300.0, 0.0, 1.0))

    def fuse(
        self,
        observations: list[LinkObservation],
        drone_positions: dict[str, tuple[float, float, float]],
        t_now: Optional[float] = None,
    ) -> Optional[FusedEstimate]:
        """N×(N-1) 어텐션 가중 융합 실행."""
        if not observations:
            return None
        if t_now is None:
            t_now = max(o.timestamp for o in observations)

        logits = self._attention_logits(observations, drone_positions, t_now)
        weights = self._softmax(logits)

        positions = np.array([obs.pos_estimate for obs in observations])
        fused_pos = (weights[:, None] * positions).sum(axis=0)

        # 신뢰도: 최대 가중치가 너무 높으면 다양성 부족 → 낮춤
        diversity = self._geometric_diversity(observations, drone_positions)
        peakiness = float(weights.max())
        confidence = float((1.0 - peakiness * 0.5) * (0.3 + 0.7 * diversity))

        return FusedEstimate(
            position=(float(fused_pos[0]), float(fused_pos[1]), float(fused_pos[2])),
            confidence=confidence,
            contributing_links=len(observations),
            attention_weights=weights.tolist(),
            geometric_diversity=diversity,
        )

    def summary(self) -> dict:
        """현재 상태 요약을 반환한다."""
        return {
            "temperature": self.temperature,
            "optimal_baseline_m": self.optimal_baseline_m,
            "recency_decay_s": self.recency_decay_s,
        }

"""
MERIDIAN 도메인 일반화 보정기 (MERIDIAN Calibrator)
===================================================
RuView의 MERIDIAN 도메인 일반화 시스템 (10초 자동 보정) 개념을
SDACS의 APF/CPA 파라미터에 적용한 환경 인식 자동 재보정.

원리:
- 풍속·기온·드론 밀도 등 환경 변화가 누적되면 APF 인력/척력 상수가
  최적점에서 이탈한다.
- 매 보정 윈도우(기본 10초)마다 환경 지표를 측정해 도메인 시프트를
  감지하고, 적은 샘플(소량 보정)로 파라미터를 재정렬한다.
- 단순 PID 적응을 넘어 **환경 컨디션 클러스터**를 학습하고 가장 가까운
  클러스터의 사전 보정값으로 워밍 스타트한다.

사용법:
    cal = MeridianCalibrator(window_s=10.0)
    cal.observe(wind_speed=12.0, temp_c=22.0, density=0.6, t=5.0)
    cal.observe(wind_speed=15.0, temp_c=21.5, density=0.65, t=15.0)
    new_params = cal.recalibrate(current_params={"k_rep": 2.5, "k_att": 1.0})
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

DEFAULT_WINDOW_S: float = 10.0
DEFAULT_SHIFT_THRESHOLD: float = 0.25
MIN_SAMPLES_FOR_CLUSTER: int = 3
MAX_CLUSTERS: int = 8
HIGH_WIND_THRESHOLD_MPS: float = 10.0


@dataclass
class EnvironmentSample:
    """단일 환경 관측."""
    t: float
    wind_speed_mps: float
    temp_c: float
    density: float


@dataclass
class CalibrationCluster:
    """환경 컨디션 클러스터 + 최적 파라미터 기억."""
    centroid: np.ndarray
    best_params: dict[str, float]
    visits: int = 0
    last_seen_t: float = 0.0


@dataclass
class RecalibrationResult:
    """재보정 결과."""
    triggered: bool
    reason: str
    new_params: dict[str, float]
    distance_to_cluster: float = 0.0
    cluster_id: Optional[int] = None


class MeridianCalibrator:
    """환경 인식 APF/CPA 자동 재보정기.

    10초 윈도우마다 환경 지표를 평균내어 사전 학습된 클러스터와 매칭한다.
    클러스터가 없으면 신규 생성하고, 풍속 강풍 모드(>10 m/s)는 즉시
    APF_PARAMS_WINDY 사전값으로 점프한다.
    """

    DEFAULT_PARAMS_CALM = {
        "k_rep": 2.5,
        "k_att": 1.0,
        "cpa_lookahead_s": 90.0,
    }
    DEFAULT_PARAMS_WINDY = {
        "k_rep": 4.0,
        "k_att": 0.7,
        "cpa_lookahead_s": 60.0,
    }

    def __init__(
        self,
        window_s: float = DEFAULT_WINDOW_S,
        shift_threshold: float = DEFAULT_SHIFT_THRESHOLD,
        seed: int = 42,
    ) -> None:
        self.window_s = window_s
        self.shift_threshold = shift_threshold
        self.rng = np.random.default_rng(seed)
        self._samples: list[EnvironmentSample] = []
        self._clusters: list[CalibrationCluster] = []
        self._last_calibration_t: Optional[float] = None
        self._first_observed_t: Optional[float] = None
        self._last_centroid: Optional[np.ndarray] = None

    def observe(
        self, wind_speed: float, temp_c: float, density: float, t: float
    ) -> None:
        """단일 환경 샘플 기록."""
        if self._first_observed_t is None:
            self._first_observed_t = t
        self._samples.append(EnvironmentSample(
            t=t, wind_speed_mps=wind_speed, temp_c=temp_c, density=density,
        ))
        # 윈도우 2배 이상 오래된 샘플 정리
        cutoff = t - self.window_s * 3
        self._samples = [s for s in self._samples if s.t >= cutoff]

    def _window_centroid(self, t: float) -> Optional[np.ndarray]:
        recent = [s for s in self._samples if s.t >= t - self.window_s]
        if len(recent) < MIN_SAMPLES_FOR_CLUSTER:
            return None
        arr = np.array([
            [s.wind_speed_mps, s.temp_c, s.density] for s in recent
        ])
        return arr.mean(axis=0)

    def _normalized_distance(
        self, a: np.ndarray, b: np.ndarray
    ) -> float:
        """풍속·기온·밀도 스케일 정규화 거리."""
        scale = np.array([15.0, 20.0, 1.0])
        return float(np.linalg.norm((a - b) / scale))

    def _find_nearest_cluster(
        self, centroid: np.ndarray
    ) -> tuple[Optional[int], float]:
        if not self._clusters:
            return None, float("inf")
        distances = [
            self._normalized_distance(c.centroid, centroid)
            for c in self._clusters
        ]
        idx = int(np.argmin(distances))
        return idx, distances[idx]

    def _spawn_cluster(self, centroid: np.ndarray, t: float) -> int:
        # 풍속 기반 사전 파라미터로 워밍 스타트
        wind = centroid[0]
        prior = (self.DEFAULT_PARAMS_WINDY if wind > HIGH_WIND_THRESHOLD_MPS
                 else self.DEFAULT_PARAMS_CALM)
        new = CalibrationCluster(
            centroid=centroid.copy(),
            best_params=dict(prior),
            visits=1,
            last_seen_t=t,
        )
        if len(self._clusters) >= MAX_CLUSTERS:
            # 가장 오래 안 본 클러스터 교체 (LRU)
            lru_idx = int(np.argmin([c.last_seen_t for c in self._clusters]))
            self._clusters[lru_idx] = new
            return lru_idx
        self._clusters.append(new)
        return len(self._clusters) - 1

    def update_cluster_with_observed_quality(
        self, cluster_id: int, params: dict[str, float], quality: float
    ) -> None:
        """관측된 품질(예: 충돌 해결률)이 더 좋으면 클러스터 최적값 갱신.

        품질 척도는 호출자가 정의 (0~1, 클수록 좋음).
        """
        if not 0 <= cluster_id < len(self._clusters):
            return
        cluster = self._clusters[cluster_id]
        baseline = cluster.best_params.get("_quality", 0.0)
        if quality > baseline:
            cluster.best_params = {**params, "_quality": quality}
            cluster.visits += 1

    def recalibrate(
        self,
        current_params: dict[str, float],
        t: Optional[float] = None,
    ) -> RecalibrationResult:
        """현재 시각 기준 재보정 시도. 윈도우 미충족 시 패스스루."""
        if t is None:
            t = self._samples[-1].t if self._samples else 0.0

        reference_t = (self._last_calibration_t
                       if self._last_calibration_t is not None
                       else self._first_observed_t)
        if reference_t is not None and t - reference_t < self.window_s:
            return RecalibrationResult(
                triggered=False,
                reason="window_not_elapsed",
                new_params=current_params,
            )

        centroid = self._window_centroid(t)
        if centroid is None:
            return RecalibrationResult(
                triggered=False,
                reason="insufficient_samples",
                new_params=current_params,
            )

        # 도메인 시프트 감지
        if self._last_centroid is not None:
            shift = self._normalized_distance(self._last_centroid, centroid)
            if shift < self.shift_threshold:
                self._last_calibration_t = t
                return RecalibrationResult(
                    triggered=False,
                    reason="no_shift",
                    new_params=current_params,
                )

        idx, dist = self._find_nearest_cluster(centroid)
        if idx is None or dist > self.shift_threshold * 2:
            idx = self._spawn_cluster(centroid, t)
            dist = 0.0
            reason = "new_cluster"
        else:
            reason = "cluster_hit"
            self._clusters[idx].last_seen_t = t
            self._clusters[idx].visits += 1

        cluster_params = {
            k: v for k, v in self._clusters[idx].best_params.items()
            if not k.startswith("_")
        }
        merged = {**current_params, **cluster_params}

        self._last_calibration_t = t
        self._last_centroid = centroid

        return RecalibrationResult(
            triggered=True,
            reason=reason,
            new_params=merged,
            distance_to_cluster=dist,
            cluster_id=idx,
        )

    def summary(self) -> dict:
        return {
            "window_s": self.window_s,
            "samples": len(self._samples),
            "clusters": len(self._clusters),
            "shift_threshold": self.shift_threshold,
        }

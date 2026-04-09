"""
드론 군집 AI 행동 패턴 분석기
==============================
드론 궤적 데이터에서 비정상 행동 패턴 자동 탐지.

기능:
  - K-means 기반 비행 패턴 분류 (NORMAL, ABNORMAL, DANGEROUS)
  - 간이 이상치 탐지 (평균/표준편차 기반)
  - 궤적 특징 벡터 추출 (속도변동, 방향전환, 고도변동 등)
  - 행동 리포트 생성
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


class BehaviorClass(str, Enum):
    NORMAL = "NORMAL"
    ABNORMAL = "ABNORMAL"
    DANGEROUS = "DANGEROUS"


@dataclass
class TrajectoryFeatures:
    """궤적 특징 벡터"""
    drone_id: str
    avg_speed: float = 0.0
    speed_std: float = 0.0
    max_speed: float = 0.0
    avg_altitude: float = 0.0
    altitude_std: float = 0.0
    direction_changes: int = 0
    total_distance: float = 0.0
    flight_duration: float = 0.0
    nfz_proximity_count: int = 0
    behavior_class: BehaviorClass = BehaviorClass.NORMAL
    anomaly_score: float = 0.0


class BehaviorAnalyzer:
    """
    드론 행동 패턴 분석기.

    궤적 데이터(위치+속도 시계열)를 입력받아
    특징 벡터를 추출하고 비정상 행동을 탐지.
    """

    def __init__(
        self,
        speed_threshold: float = 25.0,
        altitude_std_threshold: float = 20.0,
        direction_change_threshold: int = 50,
        anomaly_z_threshold: float = 2.5,
    ) -> None:
        self.speed_threshold = speed_threshold
        self.altitude_std_threshold = altitude_std_threshold
        self.direction_change_threshold = direction_change_threshold
        self.anomaly_z_threshold = anomaly_z_threshold

        self._features: list[TrajectoryFeatures] = []
        self._centroids: list[np.ndarray] = []

    def extract_features(
        self,
        drone_id: str,
        positions: list[np.ndarray],
        velocities: list[np.ndarray] | None = None,
        dt: float = 0.1,
    ) -> TrajectoryFeatures:
        """궤적에서 특징 벡터 추출"""
        if len(positions) < 2:
            return TrajectoryFeatures(drone_id=drone_id)

        pos = np.array(positions)

        # 속도 계산
        if velocities and len(velocities) == len(positions):
            speeds = np.array([float(np.linalg.norm(v[:2])) for v in velocities])
        else:
            diffs = np.diff(pos, axis=0)
            speeds = np.array([float(np.linalg.norm(d[:2])) / dt for d in diffs])

        # 고도
        altitudes = pos[:, 2] if pos.shape[1] > 2 else np.zeros(len(pos))

        # 방향 전환 카운트
        dir_changes = 0
        if len(pos) >= 3:
            for i in range(1, len(pos) - 1):
                v1 = pos[i] - pos[i - 1]
                v2 = pos[i + 1] - pos[i]
                n1 = float(np.linalg.norm(v1[:2]))
                n2 = float(np.linalg.norm(v2[:2]))
                if n1 > 0.1 and n2 > 0.1:
                    cos_angle = float(np.dot(v1[:2], v2[:2]) / (n1 * n2))
                    cos_angle = np.clip(cos_angle, -1, 1)
                    angle = np.degrees(np.arccos(cos_angle))
                    if angle > 30:
                        dir_changes += 1

        # 총 비행거리
        total_dist = float(np.sum(np.linalg.norm(np.diff(pos[:, :2], axis=0), axis=1)))

        feat = TrajectoryFeatures(
            drone_id=drone_id,
            avg_speed=float(np.mean(speeds)) if len(speeds) > 0 else 0.0,
            speed_std=float(np.std(speeds)) if len(speeds) > 0 else 0.0,
            max_speed=float(np.max(speeds)) if len(speeds) > 0 else 0.0,
            avg_altitude=float(np.mean(altitudes)),
            altitude_std=float(np.std(altitudes)),
            direction_changes=dir_changes,
            total_distance=total_dist,
            flight_duration=len(positions) * dt,
        )

        self._features.append(feat)
        return feat

    def classify(self, features: TrajectoryFeatures | None = None) -> BehaviorClass:
        """규칙 기반 행동 분류"""
        feat = features or (self._features[-1] if self._features else None)
        if feat is None:
            return BehaviorClass.NORMAL

        # 위험 기준
        if (feat.max_speed > self.speed_threshold * 1.5 or
                feat.altitude_std > self.altitude_std_threshold * 2):
            feat.behavior_class = BehaviorClass.DANGEROUS
            return BehaviorClass.DANGEROUS

        # 비정상 기준
        if (feat.speed_std > feat.avg_speed * 0.8 or
                feat.altitude_std > self.altitude_std_threshold or
                feat.direction_changes > self.direction_change_threshold):
            feat.behavior_class = BehaviorClass.ABNORMAL
            return BehaviorClass.ABNORMAL

        feat.behavior_class = BehaviorClass.NORMAL
        return BehaviorClass.NORMAL

    def detect_anomalies(self) -> list[TrajectoryFeatures]:
        """전체 드론 대비 이상치 탐지 (z-score 기반)"""
        if len(self._features) < 3:
            return []

        speeds = np.array([f.avg_speed for f in self._features])
        alt_stds = np.array([f.altitude_std for f in self._features])
        dir_changes = np.array([f.direction_changes for f in self._features])

        anomalies = []
        for i, feat in enumerate(self._features):
            z_speed = abs(speeds[i] - np.mean(speeds)) / max(np.std(speeds), 1e-6)
            z_alt = abs(alt_stds[i] - np.mean(alt_stds)) / max(np.std(alt_stds), 1e-6)
            z_dir = abs(dir_changes[i] - np.mean(dir_changes)) / max(np.std(dir_changes), 1e-6)

            anomaly_score = max(z_speed, z_alt, z_dir)
            feat.anomaly_score = anomaly_score

            if anomaly_score > self.anomaly_z_threshold:
                anomalies.append(feat)

        return anomalies

    def cluster_kmeans(self, k: int = 3) -> dict[int, list[str]]:
        """간이 K-means 클러스터링 (3클래스)"""
        if len(self._features) < k:
            return {i: [] for i in range(k)}

        # 특징 행렬
        X = np.array([
            [f.avg_speed, f.speed_std, f.altitude_std, f.direction_changes]
            for f in self._features
        ])

        # 정규화
        means = X.mean(axis=0)
        stds = X.std(axis=0)
        stds[stds < 1e-6] = 1.0
        X_norm = (X - means) / stds

        # K-means (최대 20 반복)
        rng = np.random.default_rng(42)
        centroids = X_norm[rng.choice(len(X_norm), k, replace=False)]

        for _ in range(20):
            dists = np.array([
                np.linalg.norm(X_norm - c, axis=1) for c in centroids
            ])
            labels = np.argmin(dists, axis=0)
            new_centroids = np.array([
                X_norm[labels == i].mean(axis=0) if np.any(labels == i)
                else centroids[i]
                for i in range(k)
            ])
            if np.allclose(centroids, new_centroids, atol=1e-6):
                break
            centroids = new_centroids

        self._centroids = [c for c in centroids]

        clusters: dict[int, list[str]] = {i: [] for i in range(k)}
        for i, feat in enumerate(self._features):
            clusters[labels[i]].append(feat.drone_id)

        return clusters

    def report(self) -> dict[str, Any]:
        """행동 분석 리포트"""
        if not self._features:
            return {"total_drones": 0}

        classes = {}
        for feat in self._features:
            self.classify(feat)
            cls = feat.behavior_class.value
            classes[cls] = classes.get(cls, 0) + 1

        anomalies = self.detect_anomalies()

        return {
            "total_drones": len(self._features),
            "classification": classes,
            "anomaly_count": len(anomalies),
            "anomaly_drone_ids": [a.drone_id for a in anomalies],
            "avg_speed_overall": float(np.mean([f.avg_speed for f in self._features])),
            "avg_altitude_overall": float(np.mean([f.avg_altitude for f in self._features])),
        }

    def clear(self) -> None:
        self._features.clear()
        self._centroids.clear()

    @property
    def features(self) -> list[TrajectoryFeatures]:
        return list(self._features)

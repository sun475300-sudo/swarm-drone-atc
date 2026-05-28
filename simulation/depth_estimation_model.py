"""
Phase 435: Depth Estimation Model for 3D Scene Understanding
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class DepthMap:
    """``DepthMap`` 관련 기능을 제공한다."""
    depth: np.ndarray
    confidence: np.ndarray
    unit: str = "meters"


class DepthEstimationModel:
    """``DepthEstimationModel`` 관련 기능을 제공한다."""
    def __init__(self, model_type: str = "monodepth"):
        """인스턴스를 초기화한다."""
        self.model_type = model_type

    def estimate_depth(self, image: np.ndarray) -> DepthMap:
        """`depth` 결과를 계산하거나 판정한다."""
        h, w = image.shape[:2]

        depth = np.random.uniform(1.0, 50.0, (h, w))
        confidence = np.random.uniform(0.5, 1.0, (h, w))

        depth[depth < 0.1] = 0.1

        return DepthMap(depth, confidence, "meters")

    def estimate_depth_stereo(
        self, left_image: np.ndarray, right_image: np.ndarray
    ) -> DepthMap:
        """`depth stereo` 결과를 계산하거나 판정한다."""
        return self.estimate_depth(left_image)

    def point_cloud_from_depth(
        self, depth: DepthMap, intrinsics: np.ndarray
    ) -> np.ndarray:
        """``point_cloud_from_depth`` 동작을 수행한다."""
        h, w = depth.depth.shape

        y_coords, x_coords = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")

        fx, fy = intrinsics[0, 0], intrinsics[1, 1]
        cx, cy = intrinsics[0, 2], intrinsics[1, 2]

        x_3d = (x_coords - cx) * depth.depth / fx
        y_3d = (y_coords - cy) * depth.depth / fy
        z_3d = depth.depth

        points = np.stack([x_3d, y_3d, z_3d], axis=-1)

        return points.reshape(-1, 3)

"""
Computer Vision Object Tracker
Phase 354 - Kalman Filter, IoU Tracking, SORT, DeepSORT
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from scipy.optimize import linear_sum_assignment


@dataclass
class BoundingBox:
    x: float
    y: float
    w: float
    h: float
    confidence: float = 1.0
    feature: Optional[np.ndarray] = None

    def to_xyxy(self) -> Tuple[float, float, float, float]:
        return self.x, self.y, self.x + self.w, self.y + self.h

    def to_xywh(self) -> Tuple[float, float, float, float]:
        return self.x, self.y, self.w, self.h


@dataclass
class Track:
    track_id: int
    bbox: BoundingBox
    age: int = 0
    hits: int = 0
    time_since_update: int = 0
    feature: Optional[np.ndarray] = None
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(2))


class KalmanFilter:
    def __init__(self):
        self.dimension = 4
        self.state_dim = 8

        self.F = np.eye(self.state_dim)
        self.F[:4, 4:] = np.eye(4)

        self.H = np.zeros((4, self.state_dim))
        self.H[:4, :4] = np.eye(4)

        self.Q = np.eye(self.state_dim) * 0.01
        self.R = np.eye(self.dimension) * 0.1

        self.x = np.zeros(self.state_dim)
        self.P = np.eye(self.state_dim)

    def init(self, bbox: BoundingBox):
        self.x[:4] = np.array([bbox.x, bbox.y, bbox.w, bbox.h])
        self.x[4:] = np.array([0, 0, 0, 0])

    def predict(self) -> BoundingBox:
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q

        return BoundingBox(x=self.x[0], y=self.x[1], w=self.x[2], h=self.x[3])

    def update(self, bbox: BoundingBox):
        z = np.array([bbox.x, bbox.y, bbox.w, bbox.h])

        y = z - self.H @ self.x
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)

        self.x = self.x + K @ y
        self.P = (np.eye(self.state_dim) - K @ self.H) @ self.P

        return BoundingBox(x=self.x[0], y=self.x[1], w=self.x[2], h=self.x[3])


def iou(box1: BoundingBox, box2: BoundingBox) -> float:
    x1_1, y1_1, x2_1, y2_1 = box1.to_xyxy()
    x1_2, y1_2, x2_2, y2_2 = box2.to_xyxy()

    xi1 = max(x1_1, x1_2)
    yi1 = max(y1_1, y1_2)
    xi2 = min(x2_1, x2_2)
    yi2 = min(y2_1, y2_2)

    inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)

    box1_area = box1.w * box1.h
    box2_area = box2.w * box2.h

    union_area = box1_area + box2_area - inter_area

    if union_area == 0:
        return 0.0

    return inter_area / union_area


def giou(box1: BoundingBox, box2: BoundingBox) -> float:
    x1_1, y1_1, x2_1, y2_1 = box1.to_xyxy()
    x1_2, y1_2, x2_2, y2_2 = box2.to_xyxy()

    xi1 = max(x1_1, x1_2)
    yi1 = max(y1_1, y1_2)
    xi2 = min(x2_1, x2_2)
    yi2 = min(y2_1, y2_2)

    inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)

    box1_area = box1.w * box1.h
    box2_area = box2.w * box2.h
    union_area = box1_area + box2_area - inter_area

    iou_val = inter_area / union_area if union_area > 0 else 0

    cx1 = min(x1_1, x1_2)
    cy1 = min(y1_1, y1_2)
    cx2 = max(x2_1, x2_2)
    cy2 = max(y2_1, y2_2)
    enclose_area = (cx2 - cx1) * (cy2 - cy1)

    giou_val = (
        iou_val - (enclose_area - union_area) / enclose_area
        if enclose_area > 0
        else iou_val
    )

    return giou_val


class SORTTracker:
    def __init__(
        self, max_age: int = 30, min_hits: int = 3, iou_threshold: float = 0.3
    ):
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.tracks: List[Track] = []
        self.track_id_count = 0

    def update(self, detections: List[BoundingBox]) -> List[Track]:
        if len(self.tracks) == 0:
            for det in detections:
                self.track_id_count += 1
                track = Track(track_id=self.track_id_count, bbox=det, age=0, hits=1)
                self.tracks.append(track)
            return self.tracks

        predicted_boxes = []
        for track in self.tracks:
            kf = KalmanFilter()
            kf.init(track.bbox)
            pred_bbox = kf.predict()
            predicted_boxes.append(pred_bbox)
            track.bbox = pred_bbox

        iou_matrix = np.zeros((len(predicted_boxes), len(detections)))
        for i, pred in enumerate(predicted_boxes):
            for j, det in enumerate(detections):
                iou_matrix[i, j] = iou(pred, det)

        matched_indices = []
        if iou_matrix.size > 0:
            row_ind, col_ind = linear_sum_assignment(-iou_matrix)
            for r, c in zip(row_ind, col_ind):
                if iou_matrix[r, c] >= self.iou_threshold:
                    matched_indices.append((r, c))

        unmatched_tracks = list(range(len(self.tracks)))
        unmatched_detections = list(range(len(detections)))

        for r, c in matched_indices:
            unmatched_tracks.remove(r)
            unmatched_detections.remove(c)

            self.tracks[r].bbox = detections[c]
            self.tracks[r].hits += 1
            self.tracks[r].time_since_update = 0

        for idx in unmatched_tracks:
            self.tracks[idx].time_since_update += 1

        new_tracks = []
        for idx in unmatched_detections:
            self.track_id_count += 1
            new_track = Track(
                track_id=self.track_id_count, bbox=detections[idx], age=0, hits=1
            )
            new_tracks.append(new_track)

        self.tracks = [t for t in self.tracks if t.time_since_update < self.max_age]
        self.tracks.extend(new_tracks)

        return [t for t in self.tracks if t.hits >= self.min_hits]


class DeepSORTTracker:
    def __init__(
        self,
        max_age: int = 30,
        min_hits: int = 3,
        iou_threshold: float = 0.3,
        appearance_threshold: float = 0.2,
    ):
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.appearance_threshold = appearance_threshold
        self.tracks: List[Track] = []
        self.track_id_count = 0

    def cosine_distance(self, feat1: np.ndarray, feat2: np.ndarray) -> float:
        return 1 - np.dot(feat1, feat2) / (
            np.linalg.norm(feat1) * np.linalg.norm(feat2) + 1e-8
        )

    def appearance_matching(
        self, tracks: List[Track], detections: List[BoundingBox]
    ) -> Tuple[List[Tuple], List, List]:
        cost_matrix = np.zeros((len(tracks), len(detections)))

        for i, track in enumerate(tracks):
            for j, det in enumerate(detections):
                if track.feature is not None and det.feature is not None:
                    cost_matrix[i, j] = self.cosine_distance(track.feature, det.feature)
                else:
                    cost_matrix[i, j] = 0.5

        matched = []
        if cost_matrix.size > 0:
            row_ind, col_ind = linear_sum_assignment(cost_matrix)
            for r, c in zip(row_ind, col_ind):
                if cost_matrix[r, c] < self.appearance_threshold:
                    matched.append((r, c))

        unmatched_tracks = list(range(len(tracks)))
        unmatched_detections = list(range(len(detections)))

        for r, c in matched:
            unmatched_tracks.remove(r)
            unmatched_detections.remove(c)

        return matched, unmatched_tracks, unmatched_detections

    def update(self, detections: List[BoundingBox]) -> List[Track]:
        predicted_boxes = []
        for track in self.tracks:
            kf = KalmanFilter()
            kf.init(track.bbox)
            pred_bbox = kf.predict()
            predicted_boxes.append(pred_bbox)
            track.bbox = pred_bbox

        matched, unmatched_tracks_idx, unmatched_detections_idx = (
            self.appearance_matching(self.tracks, detections)
        )

        for r, c in matched:
            self.tracks[r].bbox = detections[c]
            if detections[c].feature is not None:
                if self.tracks[r].feature is None:
                    self.tracks[r].feature = detections[c].feature
                else:
                    self.tracks[r].feature = (
                        0.9 * self.tracks[r].feature + 0.1 * detections[c].feature
                    )
            self.tracks[r].hits += 1
            self.tracks[r].time_since_update = 0

        for idx in sorted(unmatched_tracks_idx, reverse=True):
            self.tracks[idx].time_since_update += 1

        new_tracks = []
        for idx in unmatched_detections_idx:
            self.track_id_count += 1
            new_track = Track(
                track_id=self.track_id_count,
                bbox=detections[idx],
                age=0,
                hits=1,
                feature=detections[idx].feature,
            )
            new_tracks.append(new_track)

        self.tracks = [t for t in self.tracks if t.time_since_update < self.max_age]
        self.tracks.extend(new_tracks)

        return [t for t in self.tracks if t.hits >= self.min_hits]


class DroneObjectTracker:
    def __init__(self, tracker_type: str = "DeepSORT"):
        if tracker_type == "SORT":
            self.tracker = SORTTracker()
        else:
            self.tracker = DeepSORTTracker()

        self.detection_history: List[List[BoundingBox]] = []

    def process_frame(self, detections: List[BoundingBox]) -> List[Track]:
        tracks = self.tracker.update(detections)
        self.detection_history.append(detections)
        return tracks

    def get_track_info(self) -> Dict:
        return {
            "num_active_tracks": len(self.tracker.tracks),
            "total_track_ids": self.tracker.track_id_count,
            "frame_history": len(self.detection_history),
        }


def simulate_detection(frame_id: int, num_objects: int = 3) -> List[BoundingBox]:
    detections = []
    for i in range(num_objects):
        x = 100 + i * 50 + np.random.randn() * 5 + frame_id * 2
        y = 100 + i * 30 + np.random.randn() * 5
        w = 40 + np.random.randn() * 5
        h = 40 + np.random.randn() * 5
        conf = 0.8 + np.random.rand() * 0.2
        feature = np.random.randn(128)

        detections.append(BoundingBox(x, y, w, h, conf, feature))
    return detections


if __name__ == "__main__":
    print("=== Computer Vision Object Tracker ===")

    tracker = DroneObjectTracker(tracker_type="DeepSORT")

    print("\n--- Tracking Simulation ---")
    for frame in range(10):
        detections = simulate_detection(frame)
        tracks = tracker.process_frame(detections)

        print(f"Frame {frame}: {len(detections)} detections, {len(tracks)} tracks")
        for t in tracks:
            print(
                f"  Track {t.track_id}: bbox=({t.bbox.x:.1f}, {t.bbox.y:.1f}, {t.bbox.w:.1f}, {t.bbox.h:.1f})"
            )

    print(f"\n{tracker.get_track_info()}")

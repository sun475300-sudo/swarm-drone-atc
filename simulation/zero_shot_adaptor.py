"""
Phase 417: Zero-Shot Adaptor for Unseen Task Handling
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import time


class TaskDomain(Enum):
    DETECTION = "detection"
    TRACKING = "tracking"
    NAVIGATION = "navigation"
    OBSTACLE_AVOIDANCE = "obstacle_avoidance"


@dataclass
class TaskDescriptor:
    domain: TaskDomain
    description: str
    required_capabilities: List[str]
    constraints: Dict[str, Any]


@dataclass
class AdaptationResult:
    task_id: str
    success: bool
    confidence: float
    adaptation_time: float
    output: Dict[str, Any]


class ZeroShotAdaptor:
    def __init__(
        self,
        base_model_path: Optional[str] = None,
        use_llm_descriptor: bool = True,
        confidence_threshold: float = 0.7,
    ):
        self.base_model_path = base_model_path
        self.use_llm_descriptor = use_llm_descriptor
        self.confidence_threshold = confidence_threshold

        self.capability_embeddings: Dict[str, np.ndarray] = {}
        self.adaptation_strategies: Dict[TaskDomain, callable] = {}

        self.task_history: List[AdaptationResult] = []

        self._initialize_capabilities()
        self._register_strategies()

    def _initialize_capabilities(self):
        capability_list = [
            "collision_detection",
            "trajectory_prediction",
            "path_planning",
            "object_tracking",
            "obstacle_avoidance",
            "weather_adaptation",
            "battery_management",
            "communication_relay",
        ]

        for cap in capability_list:
            self.capability_embeddings[cap] = np.random.randn(128)

    def _register_strategies(self):
        self.adaptation_strategies = {
            TaskDomain.DETECTION: self._adapt_detection,
            TaskDomain.TRACKING: self._adapt_tracking,
            TaskDomain.NAVIGATION: self._adapt_navigation,
            TaskDomain.OBSTACLE_AVOIDANCE: self._adapt_obstacle_avoidance,
        }

    def describe_task(self, task: TaskDescriptor) -> Dict[str, Any]:
        description_embedding = self._encode_description(task.description)

        required_caps = []
        for cap_name, cap_emb in self.capability_embeddings.items():
            similarity = np.dot(description_embedding, cap_emb) / (
                np.linalg.norm(description_embedding) * np.linalg.norm(cap_emb) + 1e-6
            )
            if similarity > 0.3:
                required_caps.append(
                    {
                        "capability": cap_name,
                        "relevance": float(similarity),
                    }
                )

        return {
            "domain": task.domain.value,
            "description_embedding": description_embedding,
            "relevant_capabilities": required_caps,
            "complexity": self._estimate_complexity(task),
        }

    def _encode_description(self, description: str) -> np.ndarray:
        words = description.lower().split()
        embedding = np.zeros(128)

        for word in words:
            if word in self.capability_embeddings:
                embedding += self.capability_embeddings[word]
            else:
                embedding += np.random.randn(128) * 0.1

        return embedding / (len(words) + 1e-6)

    def _estimate_complexity(self, task: TaskDescriptor) -> str:
        num_caps = len(task.required_capabilities)
        num_constraints = len(task.constraints)

        complexity_score = num_caps * 0.4 + num_constraints * 0.3

        if complexity_score > 2.5:
            return "high"
        elif complexity_score > 1.5:
            return "medium"
        else:
            return "low"

    def adapt(self, task: TaskDescriptor) -> AdaptationResult:
        start_time = time.time()

        task_info = self.describe_task(task)

        if task.domain not in self.adaptation_strategies:
            return AdaptationResult(
                task_id=f"task_{int(time.time())}",
                success=False,
                confidence=0.0,
                adaptation_time=time.time() - start_time,
                output={"error": "Unknown domain"},
            )

        strategy = self.adaptation_strategies[task.domain]
        output = strategy(task, task_info)

        confidence = self._calculate_confidence(task_info, output)

        success = confidence >= self.confidence_threshold

        result = AdaptationResult(
            task_id=f"task_{int(time.time())}",
            success=success,
            confidence=confidence,
            adaptation_time=time.time() - start_time,
            output=output,
        )

        self.task_history.append(result)

        return result

    def _adapt_detection(
        self,
        task: TaskDescriptor,
        task_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "model_type": "yolov8",
            "input_size": [640, 640],
            "confidence_threshold": 0.5,
            "augmentation": ["flip", "rotation", "scale"],
        }

    def _adapt_tracking(
        self,
        task: TaskDescriptor,
        task_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "tracker_type": "bytetrack",
            "max_time_lost": 30,
            "track_thresh": 0.5,
            "asso_iou_threshold": 0.3,
        }

    def _adapt_navigation(
        self,
        task: TaskDescriptor,
        task_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "planner_type": "astar",
            "heuristic": "euclidean",
            "diagonal_movement": True,
            "smooth_path": True,
        }

    def _adapt_obstacle_avoidance(
        self,
        task: TaskDescriptor,
        task_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "method": "apf",
            "repulsion_gain": 1.5,
            "attraction_gain": 1.0,
            "obstacle_margin": 5.0,
        }

    def _calculate_confidence(
        self,
        task_info: Dict[str, Any],
        output: Dict[str, Any],
    ) -> float:
        base_confidence = 0.8

        if "error" in output:
            return 0.0

        complexity = task_info.get("complexity", "low")
        if complexity == "high":
            base_confidence *= 0.8
        elif complexity == "medium":
            base_confidence *= 0.9

        num_caps = len(task_info.get("relevant_capabilities", []))
        cap_bonus = min(num_caps * 0.05, 0.2)

        return min(base_confidence + cap_bonus, 1.0)

    def get_adaptation_stats(self) -> Dict[str, Any]:
        if not self.task_history:
            return {"total_tasks": 0}

        successful = sum(1 for r in self.task_history if r.success)

        return {
            "total_tasks": len(self.task_history),
            "successful_adaptations": successful,
            "success_rate": successful / len(self.task_history),
            "avg_confidence": np.mean([r.confidence for r in self.task_history]),
            "avg_adaptation_time": np.mean(
                [r.adaptation_time for r in self.task_history]
            ),
        }

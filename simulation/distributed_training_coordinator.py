"""
Phase 425: Distributed Training Coordinator for Swarm Learning
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np


class WorkerStatus(Enum):
    """``WorkerStatus`` 관련 기능을 제공한다."""
    IDLE = "idle"
    TRAINING = "training"
    SYNCING = "syncing"
    FAILED = "failed"


@dataclass
class TrainingWorker:
    """``TrainingWorker`` 관련 기능을 제공한다."""
    worker_id: str
    status: WorkerStatus
    current_epoch: int
    loss: float
    accuracy: float
    last_update: float


@dataclass
class SyncRequest:
    """``SyncRequest`` 데이터를 표현한다."""
    request_id: str
    worker_id: str
    model_gradients: dict[str, np.ndarray]
    timestamp: float


class DistributedTrainingCoordinator:
    """``DistributedTrainingCoordinator`` 관련 기능을 제공한다."""
    def __init__(self, coordinator_id: str, sync_interval: float = 10.0):
        """인스턴스를 초기화한다."""
        self.coordinator_id = coordinator_id
        self.sync_interval = sync_interval

        self.workers: dict[str, TrainingWorker] = {}
        self.sync_queue: list[SyncRequest] = []

        self.global_model: dict[str, np.ndarray] = {}
        self.training_config = {}

        self.metrics = {
            "total_syncs": 0,
            "failed_workers": 0,
            "avg_epoch_time": 0.0,
        }

    def register_worker(self, worker_id: str):
        """`worker` 항목을 추가한다."""
        worker = TrainingWorker(
            worker_id=worker_id,
            status=WorkerStatus.IDLE,
            current_epoch=0,
            loss=0.0,
            accuracy=0.0,
            last_update=time.time(),
        )
        self.workers[worker_id] = worker

    def start_training(self, worker_id: str):
        """`training` 실행 상태를 제어한다."""
        if worker_id in self.workers:
            self.workers[worker_id].status = WorkerStatus.TRAINING

    def submit_gradients(self, worker_id: str, gradients: dict[str, np.ndarray]):
        """``submit_gradients`` 동작을 수행한다."""
        request = SyncRequest(
            request_id=f"sync_{int(time.time())}_{worker_id}",
            worker_id=worker_id,
            model_gradients=gradients,
            timestamp=time.time(),
        )
        self.sync_queue.append(request)

        if worker_id in self.workers:
            self.workers[worker_id].status = WorkerStatus.SYNCING

    def synchronize_models(self) -> bool:
        """``synchronize_models`` 동작을 수행한다."""
        if not self.sync_queue:
            return False

        num_workers = len({r.worker_id for r in self.sync_queue})

        if num_workers < 2:
            return False

        aggregated_gradients = {}

        for key in self.sync_queue[0].model_gradients:
            grads = [
                r.model_gradients[key]
                for r in self.sync_queue
                if key in r.model_gradients
            ]
            aggregated_gradients[key] = np.mean(grads, axis=0)

        self.global_model = aggregated_gradients

        for request in self.sync_queue:
            if request.worker_id in self.workers:
                self.workers[request.worker_id].status = WorkerStatus.IDLE
                self.workers[request.worker_id].current_epoch += 1

        self.sync_queue.clear()
        self.metrics["total_syncs"] += 1

        return True

    def get_worker_status(self, worker_id: str) -> TrainingWorker | None:
        """`worker status` 정보를 조회한다."""
        return self.workers.get(worker_id)

    def get_coordinator_status(self) -> dict[str, Any]:
        """`coordinator status` 정보를 조회한다."""
        status_counts = {}
        for worker in self.workers.values():
            status_counts[worker.status.value] = (
                status_counts.get(worker.status.value, 0) + 1
            )

        return {
            "coordinator_id": self.coordinator_id,
            "total_workers": len(self.workers),
            "worker_status": status_counts,
            "pending_syncs": len(self.sync_queue),
            "total_syncs": self.metrics["total_syncs"],
        }

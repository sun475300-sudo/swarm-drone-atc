"""
임무 체인
=========
다단계 임무 의존성 + DAG 실행 + 진행 추적.

사용법:
    mc = MissionChain()
    mc.add_task("pickup", drone="d1")
    mc.add_task("deliver", drone="d1", depends_on=["pickup"])
    mc.start("pickup")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChainTask:
    """체인 태스크"""
    task_id: str
    drone_id: str = ""
    depends_on: list[str] = field(default_factory=list)
    status: str = "PENDING"  # PENDING, READY, RUNNING, COMPLETED, FAILED
    result: dict[str, Any] = field(default_factory=dict)


class MissionChain:
    """다단계 임무 체인."""

    def __init__(self, chain_id: str = "chain_1") -> None:
        self.chain_id = chain_id
        self._tasks: dict[str, ChainTask] = {}
        self._execution_order: list[str] = []

    def add_task(
        self, task_id: str, drone: str = "",
        depends_on: list[str] | None = None,
    ) -> ChainTask:
        task = ChainTask(
            task_id=task_id, drone_id=drone,
            depends_on=depends_on or [],
        )
        self._tasks[task_id] = task
        return task

    def start(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False
        # 의존성 확인
        for dep in task.depends_on:
            dep_task = self._tasks.get(dep)
            if not dep_task or dep_task.status != "COMPLETED":
                return False
        task.status = "RUNNING"
        self._execution_order.append(task_id)
        return True

    def complete(self, task_id: str, result: dict[str, Any] | None = None) -> bool:
        task = self._tasks.get(task_id)
        if not task or task.status != "RUNNING":
            return False
        task.status = "COMPLETED"
        task.result = result or {}
        # 자동으로 준비된 태스크 시작
        self._update_ready()
        return True

    def fail(self, task_id: str, reason: str = "") -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False
        task.status = "FAILED"
        task.result = {"error": reason}
        return True

    def _update_ready(self) -> None:
        for task in self._tasks.values():
            if task.status != "PENDING":
                continue
            all_done = all(
                self._tasks.get(d, ChainTask("")).status == "COMPLETED"
                for d in task.depends_on
            )
            if all_done:
                task.status = "READY"

    def ready_tasks(self) -> list[str]:
        self._update_ready()
        return [tid for tid, t in self._tasks.items() if t.status == "READY"]

    def is_complete(self) -> bool:
        return all(t.status == "COMPLETED" for t in self._tasks.values())

    def is_failed(self) -> bool:
        return any(t.status == "FAILED" for t in self._tasks.values())

    def progress_pct(self) -> float:
        if not self._tasks:
            return 100.0
        done = sum(1 for t in self._tasks.values() if t.status == "COMPLETED")
        return (done / len(self._tasks)) * 100

    def topological_order(self) -> list[str]:
        """위상 정렬"""
        visited: set[str] = set()
        order: list[str] = []

        def dfs(tid: str) -> None:
            if tid in visited:
                return
            visited.add(tid)
            task = self._tasks.get(tid)
            if task:
                for dep in task.depends_on:
                    dfs(dep)
            order.append(tid)

        for tid in self._tasks:
            dfs(tid)
        return order

    def critical_path(self) -> list[str]:
        """가장 긴 의존 체인"""
        memo: dict[str, list[str]] = {}

        def longest(tid: str) -> list[str]:
            if tid in memo:
                return memo[tid]
            task = self._tasks.get(tid)
            if not task or not task.depends_on:
                memo[tid] = [tid]
                return [tid]
            best = max(
                (longest(d) for d in task.depends_on),
                key=len, default=[],
            )
            memo[tid] = best + [tid]
            return memo[tid]

        if not self._tasks:
            return []
        return max((longest(tid) for tid in self._tasks), key=len, default=[])

    def summary(self) -> dict[str, Any]:
        status_counts: dict[str, int] = {}
        for t in self._tasks.values():
            status_counts[t.status] = status_counts.get(t.status, 0) + 1
        return {
            "chain_id": self.chain_id,
            "total_tasks": len(self._tasks),
            "progress_pct": round(self.progress_pct(), 1),
            "by_status": status_counts,
            "is_complete": self.is_complete(),
        }

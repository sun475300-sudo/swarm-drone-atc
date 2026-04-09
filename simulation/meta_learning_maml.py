# Phase 540: Meta-Learning MAML Controller — Few-Shot Adaptive Control
"""
MAML 기반 메타학습 제어기: 소수 샘플로 새 환경에 빠르게 적응.
Inner loop(태스크 적응) + Outer loop(메타 업데이트) 구조.
Phase 416 meta_learning_controller.py와 별도 — MAML 특화 구현.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class MAMLTask:
    task_id: str
    target_fn: object  # callable
    support_x: np.ndarray
    support_y: np.ndarray
    query_x: np.ndarray
    query_y: np.ndarray


@dataclass
class MAMLAdaptResult:
    task_id: str
    loss_before: float
    loss_after: float
    improvement: float


class MAMLController:
    """간이 2-layer 제어기."""

    def __init__(self, input_dim=4, hidden=16, output_dim=2, seed=42):
        rng = np.random.default_rng(seed)
        self.w1 = rng.normal(0, 0.3, (input_dim, hidden))
        self.b1 = np.zeros(hidden)
        self.w2 = rng.normal(0, 0.3, (hidden, output_dim))
        self.b2 = np.zeros(output_dim)

    def forward(self, x: np.ndarray) -> np.ndarray:
        h = np.maximum(0, x @ self.w1 + self.b1)
        return h @ self.w2 + self.b2

    def compute_loss(self, x: np.ndarray, y: np.ndarray) -> float:
        pred = self.forward(x)
        return float(np.mean((pred - y) ** 2))

    def get_params(self):
        return (self.w1.copy(), self.b1.copy(), self.w2.copy(), self.b2.copy())

    def set_params(self, params):
        self.w1, self.b1, self.w2, self.b2 = params

    def gradient_step(self, x: np.ndarray, y: np.ndarray, lr=0.01):
        h = np.maximum(0, x @ self.w1 + self.b1)
        pred = h @ self.w2 + self.b2
        error = pred - y
        dw2 = h.T @ error / len(x)
        db2 = error.mean(axis=0)
        self.w2 -= lr * dw2
        self.b2 -= lr * db2
        d_h = error @ self.w2.T
        d_h[h <= 0] = 0
        dw1 = x.T @ d_h / len(x)
        db1 = d_h.mean(axis=0)
        self.w1 -= lr * dw1
        self.b1 -= lr * db1


class MAMLTaskGenerator:
    def __init__(self, seed=42):
        self.rng = np.random.default_rng(seed)
        self.task_count = 0

    def generate(self, n_support=10, n_query=10) -> MAMLTask:
        self.task_count += 1
        A = self.rng.normal(0, 1, (4, 2))
        b = self.rng.normal(0, 0.5, 2)
        target_fn = lambda x, A=A, b=b: x @ A + b
        sx = self.rng.normal(0, 1, (n_support, 4))
        sy = target_fn(sx) + self.rng.normal(0, 0.1, (n_support, 2))
        qx = self.rng.normal(0, 1, (n_query, 4))
        qy = target_fn(qx) + self.rng.normal(0, 0.1, (n_query, 2))
        return MAMLTask(f"maml_task_{self.task_count}", target_fn, sx, sy, qx, qy)


class MetaLearningMAML:
    """MAML 메타학습 시스템."""

    def __init__(self, inner_lr=0.01, outer_lr=0.001, inner_steps=5, seed=42):
        self.inner_lr = inner_lr
        self.outer_lr = outer_lr
        self.inner_steps = inner_steps
        self.controller = MAMLController(seed=seed)
        self.task_gen = MAMLTaskGenerator(seed)
        self.rng = np.random.default_rng(seed)
        self.adaptation_results: list[MAMLAdaptResult] = []
        self.meta_losses: list[float] = []

    def adapt(self, task: MAMLTask) -> MAMLAdaptResult:
        original_params = self.controller.get_params()
        loss_before = self.controller.compute_loss(task.support_x, task.support_y)
        for _ in range(self.inner_steps):
            self.controller.gradient_step(task.support_x, task.support_y, self.inner_lr)
        loss_after = self.controller.compute_loss(task.query_x, task.query_y)
        result = MAMLAdaptResult(task.task_id, loss_before, loss_after, max(0, loss_before - loss_after))
        self.adaptation_results.append(result)
        self.controller.set_params(original_params)
        return result

    def meta_update(self, tasks: list[MAMLTask]):
        original_params = self.controller.get_params()
        meta_grads_w1 = np.zeros_like(self.controller.w1)
        meta_grads_w2 = np.zeros_like(self.controller.w2)
        for task in tasks:
            self.controller.set_params(tuple(p.copy() for p in original_params))
            for _ in range(self.inner_steps):
                self.controller.gradient_step(task.support_x, task.support_y, self.inner_lr)
            h = np.maximum(0, task.query_x @ self.controller.w1 + self.controller.b1)
            pred = h @ self.controller.w2 + self.controller.b2
            error = pred - task.query_y
            meta_grads_w2 += h.T @ error / len(task.query_x)
            d_h = error @ self.controller.w2.T
            d_h[h <= 0] = 0
            meta_grads_w1 += task.query_x.T @ d_h / len(task.query_x)
        n = len(tasks)
        w1, b1, w2, b2 = original_params
        w1 -= self.outer_lr * meta_grads_w1 / n
        w2 -= self.outer_lr * meta_grads_w2 / n
        self.controller.set_params((w1, b1, w2, b2))
        meta_loss = float(np.mean([r.loss_after for r in self.adaptation_results[-n:]]))
        self.meta_losses.append(meta_loss)

    def train(self, n_epochs=10, tasks_per_epoch=5):
        for epoch in range(n_epochs):
            tasks = [self.task_gen.generate() for _ in range(tasks_per_epoch)]
            for t in tasks:
                self.adapt(t)
            self.meta_update(tasks)

    def evaluate(self, n_tasks=5) -> dict:
        results = []
        for _ in range(n_tasks):
            task = self.task_gen.generate()
            r = self.adapt(task)
            results.append(r)
        avg_before = float(np.mean([r.loss_before for r in results]))
        avg_after = float(np.mean([r.loss_after for r in results]))
        return {
            "avg_loss_before": round(avg_before, 4),
            "avg_loss_after": round(avg_after, 4),
            "avg_improvement": round(avg_before - avg_after, 4),
        }

    def summary(self):
        eval_result = self.evaluate()
        return {
            "total_tasks": len(self.adaptation_results),
            "meta_epochs": len(self.meta_losses),
            "final_meta_loss": round(self.meta_losses[-1], 4) if self.meta_losses else 0,
            **eval_result,
        }


if __name__ == "__main__":
    mlc = MetaLearningMAML(inner_lr=0.01, outer_lr=0.001, inner_steps=5, seed=42)
    mlc.train(10, 5)
    s = mlc.summary()
    for k, v in s.items():
        print(f"  {k}: {v}")

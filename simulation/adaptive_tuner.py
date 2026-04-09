"""
적응형 파라미터 튜너
===================
실시간 성능 피드백 → APF/CPA 파라미터 자동 조정.

사용법:
    tuner = AdaptiveTuner()
    tuner.add_param("k_rep", current=2.5, min_val=1.0, max_val=10.0)
    tuner.record_metric("collision_rate", 0.03)
    tuner.tune()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class TunableParam:
    """조정 가능 파라미터"""
    name: str
    current: float
    min_val: float
    max_val: float
    step: float = 0.1
    history: list[float] = field(default_factory=list)


@dataclass
class TuneResult:
    """튜닝 결과"""
    param: str
    old_value: float
    new_value: float
    reason: str


class AdaptiveTuner:
    """적응형 파라미터 튜너."""

    METRIC_TARGETS = {
        "collision_rate": ("minimize", 0.01),
        "resolution_time_ms": ("minimize", 50.0),
        "energy_efficiency": ("maximize", 0.8),
        "throughput": ("maximize", 100.0),
    }

    def __init__(self, sensitivity: float = 0.5) -> None:
        self._params: dict[str, TunableParam] = {}
        self._metrics: dict[str, list[float]] = {}
        self._history: list[TuneResult] = []
        self.sensitivity = sensitivity

    def add_param(
        self, name: str, current: float,
        min_val: float = 0.0, max_val: float = 100.0, step: float = 0.1,
    ) -> None:
        self._params[name] = TunableParam(
            name=name, current=current,
            min_val=min_val, max_val=max_val, step=step,
        )

    def record_metric(self, name: str, value: float) -> None:
        if name not in self._metrics:
            self._metrics[name] = []
        self._metrics[name].append(value)
        if len(self._metrics[name]) > 200:
            self._metrics[name] = self._metrics[name][-200:]

    def get_param(self, name: str) -> float:
        p = self._params.get(name)
        return p.current if p else 0.0

    def _metric_trend(self, name: str) -> float:
        """메트릭 트렌드 (-1 하락, 0 안정, +1 상승)"""
        vals = self._metrics.get(name, [])
        if len(vals) < 5:
            return 0.0
        recent = np.mean(vals[-5:])
        older = np.mean(vals[-10:-5]) if len(vals) >= 10 else np.mean(vals[:5])
        if older == 0:
            return 0.0
        return (recent - older) / abs(older)

    def tune(self) -> list[TuneResult]:
        """전체 파라미터 튜닝"""
        results = []
        for metric_name, (direction, target) in self.METRIC_TARGETS.items():
            vals = self._metrics.get(metric_name, [])
            if len(vals) < 3:
                continue

            current_val = np.mean(vals[-5:])
            trend = self._metric_trend(metric_name)

            # 목표 대비 차이
            if direction == "minimize":
                gap = (current_val - target) / max(target, 0.001)
            else:
                gap = (target - current_val) / max(target, 0.001)

            if gap <= 0:
                continue  # 이미 목표 달성

            # 관련 파라미터 조정
            for pname, param in self._params.items():
                adjustment = param.step * self.sensitivity * min(gap, 1.0)
                if direction == "minimize":
                    new_val = param.current + adjustment
                else:
                    new_val = param.current - adjustment

                new_val = max(param.min_val, min(param.max_val, new_val))
                if abs(new_val - param.current) < 1e-6:
                    continue

                old_val = param.current
                param.current = new_val
                param.history.append(new_val)

                result = TuneResult(
                    param=pname, old_value=old_val,
                    new_value=round(new_val, 4),
                    reason=f"{metric_name} gap={gap:.2f}",
                )
                results.append(result)
                self._history.append(result)
                break  # 메트릭당 1개 파라미터

        return results

    def reset_param(self, name: str, value: float) -> None:
        p = self._params.get(name)
        if p:
            p.current = value

    def tuning_history(self, n: int = 20) -> list[TuneResult]:
        return self._history[-n:]

    def summary(self) -> dict[str, Any]:
        return {
            "params": len(self._params),
            "metrics_tracked": len(self._metrics),
            "total_adjustments": len(self._history),
            "current_values": {n: round(p.current, 4) for n, p in self._params.items()},
        }

from .cbs import (
    GridNode,
    Conflict,
    Constraint,
    CTNode,
    cbs_plan,
    position_to_grid,
    low_level_astar,
    detect_conflict as _detect_conflict_cpu,
    GRID_RESOLUTION,
)

# GPU 가속 충돌 탐지
_USE_GPU = False
try:
    from .cbs_gpu import gpu_detect_conflict
    _USE_GPU = True
except ImportError:
    pass


def detect_conflict(paths):
    """충돌 탐지 — GPU 사용 가능 시 자동 가속."""
    if _USE_GPU:
        return gpu_detect_conflict(paths)
    return _detect_conflict_cpu(paths)


__all__ = [
    "GridNode", "Conflict", "Constraint", "CTNode",
    "cbs_plan", "position_to_grid", "low_level_astar",
    "detect_conflict", "GRID_RESOLUTION",
]

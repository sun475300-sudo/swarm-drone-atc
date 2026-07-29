"""Module: simulation/apf_engine/__init__.py."""

from .apf import (
    APF_PARAMS,
    APF_PARAMS_HIGH_DENSITY,
    APF_PARAMS_WINDY,
    APFState,
    attractive_force,
    compute_total_force,
    force_to_velocity,
    repulsive_force_drone,
    repulsive_force_obstacle,
)
from .apf import (
    batch_compute_forces as _batch_compute_forces_cpu,
)

# GPU 가속 엔진 자동 감지
_USE_GPU = False
_USE_MULTI_GPU = False
try:
    from .apf_gpu import (
        _TORCH_AVAILABLE as _APF_TORCH_OK,
    )
    from .apf_gpu import (
        _get_device_info,
        gpu_batch_compute_forces,
    )
    from .multi_gpu import get_gpu_count, multi_gpu_batch_compute

    _USE_GPU = bool(_APF_TORCH_OK)
    _USE_MULTI_GPU = _USE_GPU and get_gpu_count() > 1
except (ImportError, OSError):
    # OSError covers Windows DLL load failures during torch import inside apf_gpu.
    pass


def batch_compute_forces(*args, **kwargs):
    """APF 배치 계산 — 멀티 GPU > 단일 GPU > CPU 우선순위로 자동 선택."""
    if _USE_MULTI_GPU:
        return multi_gpu_batch_compute(*args, **kwargs)
    if _USE_GPU:
        return gpu_batch_compute_forces(*args, **kwargs)
    return _batch_compute_forces_cpu(*args, **kwargs)


def get_apf_backend_info() -> dict:
    """현재 APF 백엔드 정보 반환."""
    if _USE_GPU:
        info = _get_device_info()
        info["multi_gpu"] = _USE_MULTI_GPU
        return info
    return {"backend": "numpy-cpu", "device": "cpu", "gpu": None, "multi_gpu": False}


__all__ = [
    "APFState",
    "APF_PARAMS",
    "APF_PARAMS_WINDY",
    "APF_PARAMS_HIGH_DENSITY",
    "compute_total_force",
    "batch_compute_forces",
    "force_to_velocity",
    "attractive_force",
    "repulsive_force_drone",
    "repulsive_force_obstacle",
    "get_apf_backend_info",
]

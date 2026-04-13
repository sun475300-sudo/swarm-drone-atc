from .apf import (
    APFState,
    APF_PARAMS,
    APF_PARAMS_WINDY,
    APF_PARAMS_HIGH_DENSITY,
    compute_total_force,
    batch_compute_forces as _batch_compute_forces_cpu,
    force_to_velocity,
    attractive_force,
    repulsive_force_drone,
    repulsive_force_obstacle,
)

# GPU 가속 엔진 자동 감지
_USE_GPU = False
try:
    from .apf_gpu import gpu_batch_compute_forces, _get_device_info

    _USE_GPU = True
except ImportError:
    pass


def batch_compute_forces(*args, **kwargs):
    """APF 배치 계산 — GPU 사용 가능 시 자동 가속."""
    if _USE_GPU:
        return gpu_batch_compute_forces(*args, **kwargs)
    return _batch_compute_forces_cpu(*args, **kwargs)


def get_apf_backend_info() -> dict:
    """현재 APF 백엔드 정보 반환."""
    if _USE_GPU:
        return _get_device_info()
    return {"backend": "numpy-cpu", "device": "cpu", "gpu": None}


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

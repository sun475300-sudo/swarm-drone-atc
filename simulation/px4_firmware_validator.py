"""PX4 v1.15+ 펌웨어 버전 및 파라미터 검증 모듈."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)


# 필수 파라미터 및 허용 범위 (min, max). None이면 존재 여부만 확인.
_REQUIRED_PARAMS: dict[str, tuple[float | None, float | None]] = {
    "NAV_ACC_RAD":     (0.5,  200.0),
    "MPC_XY_CRUISE":   (0.5,  20.0),
    "RTL_RETURN_ALT":  (2.0,  300.0),
    "COM_LOW_BAT_ACT": (0,    3),
    "BAT_N_CELLS":     (1,    14),
    "MPC_Z_VEL_MAX_UP":(0.5,  8.0),
    "MPC_Z_VEL_MAX_DN":(0.5,  4.0),
    "COM_RC_LOSS_T":   (0.0,  35.0),
    "GF_ACTION":       (0,    4),
    "EKF2_AID_MASK":   (0,    511),
}

_MIN_MAJOR = 1
_MIN_MINOR = 15


class PX4FirmwareValidator:
    """PX4 펌웨어 버전과 파라미터를 검증한다."""

    def validate_version(self, version_str: str) -> None:
        """버전 문자열이 v1.15+ 인지 검증. 아니면 ValueError."""
        cleaned = version_str.lstrip("vV").split("-")[0]
        parts = cleaned.split(".")
        if len(parts) < 2:
            raise ValueError(f"파싱 불가 버전 문자열: {version_str!r}")
        try:
            major, minor = int(parts[0]), int(parts[1])
        except ValueError:
            raise ValueError(f"버전 숫자 파싱 실패: {version_str!r}")

        if (major, minor) < (_MIN_MAJOR, _MIN_MINOR):
            raise ValueError(
                f"PX4 버전 {version_str}은 최소 요구 v{_MIN_MAJOR}.{_MIN_MINOR}+ 미달"
            )

    def validate_params(self, params: dict) -> ValidationResult:
        """필수 10개 파라미터 존재 및 범위 검증."""
        errors: list[str] = []

        for name, (lo, hi) in _REQUIRED_PARAMS.items():
            if name not in params:
                errors.append(f"누락 파라미터: {name}")
                continue

            val = params[name]
            try:
                fval = float(val)
            except (TypeError, ValueError):
                errors.append(f"{name}: 숫자 변환 불가 값 {val!r}")
                continue

            if lo is not None and fval < lo:
                errors.append(f"{name}={fval} < 최솟값 {lo}")
            if hi is not None and fval > hi:
                errors.append(f"{name}={fval} > 최댓값 {hi}")

        return ValidationResult(ok=len(errors) == 0, errors=errors)

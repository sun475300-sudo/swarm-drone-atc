"""
시나리오 스키마 검증기 (GENESIS Phase 322)
==========================================
``.sdacs-scenario`` 마켓플레이스 포맷 검증기.

config/scenario_params/*.yaml 의 실행형 시나리오가 scenario_runner 계약
(``docs/schemas/sdacs-scenario.schema.json``)을 만족하는지 결정적으로 검증한다.
플러그인 SDK(Phase 321)·시나리오 마켓플레이스가 외부 시나리오를 공유하기 전에
이 검증기로 사전 점검한다.

새 의존성(jsonschema 등) 없이 손수 검증한다 — 결정적·오프라인 동작 보장.

CLI:
    python simulation/scenario_schema.py config/scenario_params/high_density.yaml
    python simulation/scenario_schema.py --all
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# 분포 합 허용 오차
_DISTRIBUTION_SUM_TOL = 0.01

# 알려진 최상위 키 (이 외의 키는 경고로 표면화)
_KNOWN_KEYS = frozenset({
    "scenario", "description",
    "schema_version",  # ODYSSEY Phase 485 포맷 버전 스탬프
    "simulation_duration_min", "simulation_duration_s",
    "drone_count", "base_drone_count", "total_drone_count",
    "arrival_rate_per_min", "area_km2",
    "drone_profile_distribution", "route_generation", "success_criteria",
    "weather", "intrusion", "comms_loss", "lost_link_protocol",
    "failure_injection", "separation_standards",
    # 특수 시나리오 전용 키 (런너가 직접 읽지 않으나 유효한 마켓플레이스 필드)
    "landing", "landing_pads", "takeoff", "takeoff_pads",
    "cities", "formation",
    "closing_speed_ms", "conflict_geometries", "separation_at_start_m",
})

# 양수여야 하는 정수 드론 수 키
_POSITIVE_INT_KEYS = ("drone_count", "base_drone_count", "total_drone_count")
# 양수여야 하는 실수 키
_POSITIVE_FLOAT_KEYS = ("arrival_rate_per_min", "area_km2")
# 매핑이어야 하는 키
_MAPPING_KEYS = (
    "route_generation", "success_criteria", "weather", "intrusion",
    "comms_loss", "lost_link_protocol", "failure_injection",
    "separation_standards",
)


@dataclass(frozen=True)
class ValidationResult:
    """검증 결과. errors 가 비어 있으면 유효한 시나리오다."""

    is_valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    def summary(self) -> str:
        """사람이 읽는 한 줄 요약을 반환한다."""
        if self.is_valid:
            base = "VALID"
        else:
            base = f"INVALID ({len(self.errors)} error)"
        if self.warnings:
            base += f" / {len(self.warnings)} warning"
        return base


def _is_number(value: Any) -> bool:
    """bool 을 제외한 int/float 인지 판정한다."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_positive_int(value: Any) -> bool:
    """bool 을 제외한 양의 정수인지 판정한다."""
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def validate_scenario(raw: Any) -> ValidationResult:
    """
    파싱된 시나리오 dict 를 검증한다.

    Args:
        raw: YAML 에서 로드한 시나리오 객체.

    Returns:
        ValidationResult — errors 가 비면 유효.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(raw, dict):
        return ValidationResult(
            is_valid=False,
            errors=(f"최상위 객체가 매핑이 아님 (got {type(raw).__name__})",),
            warnings=(),
        )

    # 필수 문자열 필드
    for key in ("scenario", "description"):
        value = raw.get(key)
        if value is None:
            errors.append(f"필수 필드 누락: '{key}'")
        elif not isinstance(value, str) or not value.strip():
            errors.append(f"'{key}' 는 비어 있지 않은 문자열이어야 함")

    # 시뮬레이션 시간 (택일)
    _validate_duration(raw, errors)

    # 드론 수 (있으면 양의 정수)
    for key in _POSITIVE_INT_KEYS:
        if key in raw and not _is_positive_int(raw[key]):
            errors.append(f"'{key}' 는 양의 정수여야 함 (got {raw[key]!r})")

    # 양수 실수 필드
    for key in _POSITIVE_FLOAT_KEYS:
        if key in raw and not (_is_number(raw[key]) and raw[key] > 0):
            errors.append(f"'{key}' 는 양수여야 함 (got {raw[key]!r})")

    # 매핑 필드
    for key in _MAPPING_KEYS:
        if key in raw and not isinstance(raw[key], dict):
            errors.append(f"'{key}' 는 매핑이어야 함 (got {type(raw[key]).__name__})")

    # 드론 프로파일 분포
    _validate_distribution(raw, errors)

    # 알 수 없는 최상위 키 (경고)
    for key in raw:
        if key not in _KNOWN_KEYS:
            warnings.append(f"알 수 없는 최상위 키: '{key}'")

    return ValidationResult(
        is_valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def _validate_duration(raw: dict, errors: list[str]) -> None:
    """시뮬레이션 시간 필드를 검증한다 (둘 중 최소 하나 + 양수)."""
    has_min = "simulation_duration_min" in raw
    has_s = "simulation_duration_s" in raw
    if not has_min and not has_s:
        errors.append(
            "시뮬레이션 시간 누락: 'simulation_duration_min' 또는 "
            "'simulation_duration_s' 중 하나 필요"
        )
    for key in ("simulation_duration_min", "simulation_duration_s"):
        if key in raw and not (_is_number(raw[key]) and raw[key] > 0):
            errors.append(f"'{key}' 는 양수여야 함 (got {raw[key]!r})")


def _validate_distribution(raw: dict, errors: list[str]) -> None:
    """drone_profile_distribution 의 합이 1.0(±tol)인지 검증한다."""
    dist = raw.get("drone_profile_distribution")
    if dist is None:
        return
    if not isinstance(dist, dict) or not dist:
        errors.append("'drone_profile_distribution' 는 비어 있지 않은 매핑이어야 함")
        return
    total = 0.0
    for profile, ratio in dist.items():
        if not _is_number(ratio) or ratio < 0:
            errors.append(
                f"분포 비율 '{profile}' 는 0 이상의 수여야 함 (got {ratio!r})"
            )
            return
        total += ratio
    if abs(total - 1.0) > _DISTRIBUTION_SUM_TOL:
        errors.append(
            f"'drone_profile_distribution' 합이 1.0 이 아님 (합={total:.3f})"
        )


def validate_scenario_file(path: str | Path) -> ValidationResult:
    """
    YAML 시나리오 파일을 로드하고 검증한다.

    Args:
        path: 시나리오 YAML 경로.

    Returns:
        ValidationResult.
    """
    import yaml

    file_path = Path(path)
    if not file_path.exists():
        return ValidationResult(
            is_valid=False,
            errors=(f"파일 없음: {file_path}",),
            warnings=(),
        )
    try:
        with open(file_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        return ValidationResult(
            is_valid=False,
            errors=(f"YAML 파싱 실패: {exc}",),
            warnings=(),
        )
    return validate_scenario(raw)


# ── CLI ──────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    """``main`` 동작을 수행한다. 유효하지 않은 시나리오가 있으면 1 을 반환한다."""
    import argparse

    parser = argparse.ArgumentParser(
        description="SDACS .sdacs-scenario 포맷 검증기 (GENESIS Phase 322)"
    )
    parser.add_argument("paths", nargs="*", help="검증할 시나리오 YAML 경로")
    parser.add_argument(
        "--all", action="store_true",
        help="config/scenario_params/*.yaml 전체 검증",
    )
    args = parser.parse_args(argv)

    paths: list[Path] = [Path(p) for p in args.paths]
    if args.all:
        root = Path(__file__).resolve().parent.parent
        paths += sorted((root / "config" / "scenario_params").glob("*.yaml"))

    if not paths:
        parser.error("검증할 경로를 지정하거나 --all 을 사용하세요")

    any_invalid = False
    for path in paths:
        result = validate_scenario_file(path)
        print(f"{path.name:<40} {result.summary()}")
        for err in result.errors:
            print(f"    ERROR: {err}")
            any_invalid = True
        for warn in result.warnings:
            print(f"    WARN:  {warn}")

    return 1 if any_invalid else 0


if __name__ == "__main__":
    sys.exit(main())

"""ODYSSEY Phase 466 — 텔레메트리 표준 스키마 검증기 (오픈 데이터 표준).

`docs/schemas/telemetry.schema.json` (draft-07) 에 정의된 2Hz WebSocket 스냅샷
계약을 외부 소비자(웹 시뮬 LIVE 모드, Grafana, 연합 인스턴스)가 신뢰할 수 있도록,
임의의 페이로드가 그 계약을 충족하는지 검증한다.

`jsonschema` 패키지가 설치돼 있으면 그것으로 (정본) 검증하고, 없으면 스키마의
제약을 직접 구현한 *순수 파이썬 폴백* 으로 동일한 핵심 제약을 검사한다 — 이는
기존 `tests/test_telemetry_schema.py` 의 "jsonschema(또는 수동 검증)" 방침과
일치하며, 프로젝트가 `jsonschema` 를 필수 의존성으로 끌어들이지 않게 한다.

`simulation/scenario_schema.py` (GENESIS Phase 322) 의 `ValidationResult` 규약을
그대로 따른다 — errors 가 비면 유효.

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python simulation/telemetry_validator.py snapshot.json   # 파일 검증
    python simulation/telemetry_validator.py --example       # 표준 예제 검증
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "docs" / "schemas" / "telemetry.schema.json"

# 스키마와 동기화된 표준 예제 스냅샷 (외부 소비자 참조용 · 테스트 픽스처).
CANONICAL_EXAMPLE: dict[str, Any] = {
    "t": 12.5,
    "drones": [
        {
            "id": "D-001",
            "pos": [10.0, 0.5, -3.2],
            "vel": [1.1, 0.0, 0.0],
            "phase": "CRUISE",
            "battery": 87.4,
        }
    ],
    "stats": {
        "collisions": 0,
        "near_misses": 1,
        "conflicts": 3,
        "advisories": 2,
        "cbs_attempts": 5,
        "cbs_successes": 5,
    },
    "backend": "cpu",
}

# 스키마 required 미러 — 폴백 검증의 단일 출처.
_REQUIRED_DRONE_KEYS = ("id", "pos", "vel", "phase", "battery")
_REQUIRED_STAT_KEYS = ("collisions", "near_misses", "conflicts", "advisories")


@dataclass(frozen=True)
class ValidationResult:
    """검증 결과. errors 가 비어 있으면 유효한 텔레메트리 스냅샷이다."""

    is_valid: bool
    errors: tuple[str, ...]

    def summary(self) -> str:
        """사람이 읽는 한 줄 요약을 반환한다."""
        return "VALID" if self.is_valid else f"INVALID ({len(self.errors)} error)"


def load_schema() -> dict[str, Any]:
    """텔레메트리 draft-07 스키마를 로드한다."""
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def _is_number(value: Any) -> bool:
    """bool 을 제외한 int/float 인지 판정한다."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_nonneg_int(value: Any) -> bool:
    """bool 을 제외한 0 이상 정수인지 판정한다."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _vec3_error(label: str, value: Any) -> str | None:
    """길이 3 의 수치 벡터가 아니면 오류 메시지를, 맞으면 None 을 반환한다."""
    if not isinstance(value, list) or len(value) != 3:
        return f"{label} 는 길이 3 배열이어야 함 (got {value!r})"
    if not all(_is_number(c) for c in value):
        return f"{label} 의 모든 성분은 수치여야 함 (got {value!r})"
    return None


def _validate_drone(index: int, drone: Any, errors: list[str]) -> None:
    """단일 드론 항목을 스키마 제약에 맞춰 검사한다."""
    prefix = f"drones[{index}]"
    if not isinstance(drone, dict):
        errors.append(f"{prefix} 는 객체여야 함 (got {type(drone).__name__})")
        return
    for key in _REQUIRED_DRONE_KEYS:
        if key not in drone:
            errors.append(f"{prefix} 필수 키 누락: '{key}'")

    if "id" in drone and (not isinstance(drone["id"], str) or not drone["id"]):
        errors.append(f"{prefix}.id 는 비어 있지 않은 문자열이어야 함")
    for vec_key in ("pos", "vel"):
        if vec_key in drone:
            err = _vec3_error(f"{prefix}.{vec_key}", drone[vec_key])
            if err:
                errors.append(err)
    if "phase" in drone and not isinstance(drone["phase"], str):
        errors.append(f"{prefix}.phase 는 문자열이어야 함")
    if "battery" in drone:
        bat = drone["battery"]
        if not _is_number(bat) or not (0 <= bat <= 100):
            errors.append(f"{prefix}.battery 는 0~100 수치여야 함 (got {bat!r})")


def _validate_stats(stats: Any, errors: list[str]) -> None:
    """stats 객체를 스키마 제약에 맞춰 검사한다."""
    if not isinstance(stats, dict):
        errors.append(f"'stats' 는 객체여야 함 (got {type(stats).__name__})")
        return
    for key in _REQUIRED_STAT_KEYS:
        if key not in stats:
            errors.append(f"stats 필수 키 누락: '{key}'")
    # 정의된 모든 카운터는 0 이상 정수.
    for key, value in stats.items():
        if not _is_nonneg_int(value):
            errors.append(f"stats.{key} 는 0 이상 정수여야 함 (got {value!r})")


def _validate_fallback(payload: Any) -> list[str]:
    """jsonschema 미설치 시 스키마 핵심 제약을 직접 검사한다."""
    errors: list[str] = []
    if not isinstance(payload, dict):
        return [f"최상위 객체가 매핑이 아님 (got {type(payload).__name__})"]

    for key in ("t", "drones", "stats", "backend"):
        if key not in payload:
            errors.append(f"필수 필드 누락: '{key}'")

    if "t" in payload and not (_is_number(payload["t"]) and payload["t"] >= 0):
        errors.append(f"'t' 는 0 이상 수치여야 함 (got {payload['t']!r})")

    if "drones" in payload:
        if not isinstance(payload["drones"], list):
            errors.append(f"'drones' 는 배열이어야 함 (got {type(payload['drones']).__name__})")
        else:
            for i, drone in enumerate(payload["drones"]):
                _validate_drone(i, drone, errors)

    if "stats" in payload:
        _validate_stats(payload["stats"], errors)

    if "backend" in payload and not isinstance(payload["backend"], str):
        errors.append(f"'backend' 는 문자열이어야 함 (got {type(payload['backend']).__name__})")

    return errors


def validate_telemetry(payload: Any) -> ValidationResult:
    """
    파싱된 텔레메트리 스냅샷을 표준 스키마에 맞춰 검증한다.

    `jsonschema` 가 설치돼 있으면 그것으로 검증하고, 없으면 순수 파이썬 폴백으로
    동일한 핵심 제약을 검사한다.

    Args:
        payload: JSON 에서 로드한 스냅샷 객체.

    Returns:
        ValidationResult — errors 가 비면 유효.
    """
    try:
        import jsonschema
    except ImportError:
        errors = _validate_fallback(payload)
    else:
        validator = jsonschema.Draft7Validator(load_schema())
        errors = [
            f"{'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}"
            for e in sorted(validator.iter_errors(payload), key=lambda e: list(e.path))
        ]
    return ValidationResult(is_valid=not errors, errors=tuple(errors))


def validate_telemetry_file(path: str | Path) -> ValidationResult:
    """
    JSON 텔레메트리 파일을 로드하고 검증한다.

    Args:
        path: 스냅샷 JSON 경로.

    Returns:
        ValidationResult.
    """
    file_path = Path(path)
    if not file_path.exists():
        return ValidationResult(is_valid=False, errors=(f"파일 없음: {file_path}",))
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return ValidationResult(is_valid=False, errors=(f"JSON 파싱 실패: {exc}",))
    return validate_telemetry(payload)


# ── CLI ──────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    """``main`` 동작을 수행한다. 유효하지 않은 스냅샷이 있으면 1 을 반환한다."""
    import argparse

    parser = argparse.ArgumentParser(
        description="SDACS 텔레메트리 스냅샷 검증기 (ODYSSEY Phase 466)"
    )
    parser.add_argument("paths", nargs="*", help="검증할 텔레메트리 JSON 경로")
    parser.add_argument(
        "--example", action="store_true",
        help="표준 예제 스냅샷(CANONICAL_EXAMPLE) 을 검증",
    )
    args = parser.parse_args(argv)

    if args.example:
        result = validate_telemetry(CANONICAL_EXAMPLE)
        print(f"{'<canonical example>':<40} {result.summary()}")
        for err in result.errors:
            print(f"    ERROR: {err}")
        return 1 if not result.is_valid else 0

    if not args.paths:
        parser.error("검증할 경로를 지정하거나 --example 을 사용하세요")

    any_invalid = False
    for path in args.paths:
        result = validate_telemetry_file(path)
        print(f"{Path(path).name:<40} {result.summary()}")
        for err in result.errors:
            print(f"    ERROR: {err}")
            any_invalid = True

    return 1 if any_invalid else 0


if __name__ == "__main__":
    import sys

    sys.exit(main())

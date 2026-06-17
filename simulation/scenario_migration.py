"""
시나리오 포맷 버전 마이그레이션 도구 (ODYSSEY Phase 485)
========================================================
``config/scenario_params/*.yaml`` 시나리오 포맷의 역사적 변종(variant)을
단일 canonical 표현으로 정규화하는 결정적 버전 변환기.

배경 — 실측 분기
----------------
러너 ``scenario_runner._translate_scenario`` 는 동등한 여러 인코딩을 관용한다:

* 시뮬 시간 — ``simulation_duration_min`` (분) vs ``simulation_duration_s`` (초)
* 드론 수   — ``drone_count`` / ``base_drone_count`` / ``base_traffic.drone_count``

여기에 스키마(``scenario_schema``)는 ``total_drone_count`` 도 유효로 인정하나
러너는 이를 *읽지 않는다*. 즉 ``total_drone_count`` 만 가진 시나리오는
스키마는 통과하지만 러너가 드론 수를 얻지 못하는 잠재 불일치가 있다
(예: ``multi_city.yaml``). 본 도구의 정규화는 이를 ``drone_count`` 로
모아 러너 호환성을 *복원*한다.

canonical v2.0 규약
-------------------
* ``schema_version: "2.0"`` 명시 스탬프
* 시간은 초 단위 ``simulation_duration_s`` (SI, 무모호) 로 통일 — ``_min`` 제거
* 드론 수는 단일 키 ``drone_count`` 로 통일 — 다른 count 키 제거

마이그레이션은 **멱등(idempotent)** 이다: 이미 canonical 인 시나리오를 변환하면
변경 없이 동일 내용을 돌려준다(``migrated == False``). 출력은 항상
``scenario_schema.validate_scenario`` 계약(GENESIS 322)을 만족한다.

대상 범위는 ``config/scenario_params/*.yaml`` 의 **러너 포맷** 시나리오다.
``config/scenario_params/uam/`` 하위는 ``drones``/``airspace``/``corridors``/
``vertiports``/``safety_net`` 등 별도 풍부 포맷이라 본 변환기 대상이 아니다.

새 의존성 없이 동작한다 — 결정적·오프라인.

CLI::

    python simulation/scenario_migration.py --detect config/scenario_params/high_density.yaml
    python simulation/scenario_migration.py --all                 # 전체 dry-run 리포트
    python simulation/scenario_migration.py --migrate IN.yaml -o OUT.yaml
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# canonical 현재 버전 / 미스탬프 레거시 버전
CURRENT_VERSION = "2.0"
LEGACY_VERSION = "1.0"

_SECONDS_PER_MINUTE = 60

# 드론 수 출처 키 결정적 우선순위 (러너 우선순위 + total_drone_count 보정)
_COUNT_SOURCE_KEYS = (
    "drone_count",
    "base_drone_count",
    "total_drone_count",
)


@dataclass(frozen=True)
class MigrationResult:
    """마이그레이션 결과. ``scenario`` 는 canonical 시나리오 dict 다."""

    scenario: dict[str, Any]
    from_version: str
    to_version: str
    changes: tuple[str, ...]

    @property
    def migrated(self) -> bool:
        """입력과 출력이 달라졌으면(구조 정리 또는 버전 상승) True."""
        return bool(self.changes)

    def summary(self) -> str:
        """사람이 읽는 한 줄 요약을 반환한다."""
        if not self.changes:
            return f"{self.from_version} (canonical — 변경 없음)"
        return f"{self.from_version} → {self.to_version} ({len(self.changes)} 변경)"


def detect_version(raw: dict[str, Any]) -> str:
    """
    시나리오 dict 의 포맷 버전을 판정한다.

    명시 ``schema_version`` 스탬프가 있으면 그것을, 없으면 레거시(1.0)로 본다
    (현 리포 시나리오는 전부 미스탬프 = 레거시).

    Raises:
        ValueError: ``raw`` 가 dict 가 아니거나 schema_version 이 문자열이 아닐 때.
    """
    if not isinstance(raw, dict):
        raise ValueError(f"시나리오는 매핑이어야 합니다: {type(raw).__name__}")
    stamped = raw.get("schema_version")
    if stamped is None:
        return LEGACY_VERSION
    if not isinstance(stamped, str):
        raise ValueError(
            f"schema_version 은 문자열이어야 합니다: {type(stamped).__name__}"
        )
    return stamped


def _as_count(value: Any, key: str) -> int:
    """드론 수가 정수인지 검증한다 — float 무음 절삭 방지(스키마는 양의 정수 요구)."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"'{key}' 는 정수여야 합니다: {value!r}")
    return value


def _resolve_count(raw: dict[str, Any]) -> tuple[int | None, str | None]:
    """드론 수와 그 출처 키를 결정적 우선순위로 해소한다."""
    for key in _COUNT_SOURCE_KEYS:
        value = raw.get(key)
        if value is not None:
            return _as_count(value, key), key
    nested = raw.get("base_traffic")
    if isinstance(nested, dict) and nested.get("drone_count") is not None:
        return _as_count(nested["drone_count"], "base_traffic.drone_count"), "base_traffic.drone_count"
    return None, None


def migrate_scenario(raw: dict[str, Any]) -> MigrationResult:
    """
    파싱된 시나리오 dict 를 canonical v2.0 으로 변환한다 (멱등).

    원본은 변형하지 않고 새 dict 를 반환한다. 변경이 없으면 동일 내용을
    돌려준다(from_version == to_version).
    """
    from_version = detect_version(raw)
    out: dict[str, Any] = dict(raw)
    changes: list[str] = []

    # ── 드론 수 정규화 → drone_count 단일 키 ─────────────────────────────
    # 모든 잉여 키 제거를 changes 에 기록한다 — 출력이 달라지면 반드시 표면화
    # (어드바이저 HIGH: 무음 삭제가 migrated/changes 에 미반영되는 계약 위반 차단).
    count, source = _resolve_count(raw)
    if count is not None and source != "drone_count":
        out["drone_count"] = count
        changes.append(f"{source}({count}) → drone_count")
    # 잉여 count 키 제거 (출처 키는 위에서 이미 이전 기록됨)
    for key in ("base_drone_count", "total_drone_count"):
        if key in out:
            removed = out.pop(key)
            if key != source:
                changes.append(f"{key}({removed}) 제거 (drone_count 우선)")
    nested = out.get("base_traffic")
    if isinstance(nested, dict):
        leftover = {k: v for k, v in nested.items() if k != "drone_count"}
        had_count = "drone_count" in nested
        if leftover:
            out["base_traffic"] = leftover
        else:
            out.pop("base_traffic")
        if had_count and source != "base_traffic.drone_count":
            changes.append("base_traffic.drone_count 제거 (drone_count 우선)")

    # ── 시뮬 시간 정규화 → simulation_duration_s ────────────────────────
    converted = False
    if out.get("simulation_duration_s") is None:
        dur_m = raw.get("simulation_duration_min")
        if dur_m is not None:
            dur_s = float(dur_m) * _SECONDS_PER_MINUTE
            out["simulation_duration_s"] = dur_s
            changes.append(
                f"simulation_duration_min({dur_m}) → simulation_duration_s({dur_s})"
            )
            converted = True
    if "simulation_duration_min" in out:
        removed_m = out.pop("simulation_duration_min")
        if not converted:  # 초가 이미 권위였는데 분이 잉여로 남은 경우
            changes.append(
                f"simulation_duration_min({removed_m}) 제거 (simulation_duration_s 권위)"
            )

    # ── 버전 스탬프 ─────────────────────────────────────────────────────
    if from_version != CURRENT_VERSION:
        out["schema_version"] = CURRENT_VERSION
        changes.append(f"schema_version 스탬프 {CURRENT_VERSION}")

    to_version = detect_version(out)
    return MigrationResult(
        scenario=out,
        from_version=from_version,
        to_version=to_version,
        changes=tuple(changes),
    )


def migrate_file(path: str | Path, out_path: str | Path | None = None) -> MigrationResult:
    """
    YAML 시나리오 파일을 로드해 canonical v2.0 으로 변환한다.

    ``out_path`` 가 주어지면 변환 결과를 그 경로에 YAML 로 기록한다(dry-run
    이면 생략). 반환은 항상 ``MigrationResult``.

    Raises:
        FileNotFoundError: 입력 파일이 없을 때.
        ValueError: YAML 파싱 실패 또는 매핑이 아닐 때.
    """
    import yaml

    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"파일 없음: {file_path}")
    try:
        with open(file_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML 파싱 실패: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"시나리오는 매핑이어야 합니다: {file_path}")

    result = migrate_scenario(raw)

    if out_path is not None:
        with open(out_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                result.scenario, f,
                allow_unicode=True, sort_keys=False, default_flow_style=False,
            )
    return result


# ── CLI ──────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    """CLI 진입점. 성공 시 0, 오류 시 1 을 반환한다."""
    import argparse

    parser = argparse.ArgumentParser(
        description="SDACS 시나리오 포맷 버전 마이그레이션 도구 (ODYSSEY Phase 485)"
    )
    parser.add_argument("paths", nargs="*", help="대상 시나리오 YAML 경로")
    parser.add_argument(
        "--all", action="store_true",
        help="config/scenario_params/*.yaml 전체 dry-run 리포트",
    )
    parser.add_argument(
        "--detect", action="store_true",
        help="버전 판정만 수행(변환 없음)",
    )
    parser.add_argument(
        "--migrate", action="store_true",
        help="변환 결과를 -o 경로에 기록",
    )
    parser.add_argument(
        "-o", "--output", help="--migrate 출력 경로",
    )
    args = parser.parse_args(argv)

    paths: list[Path] = [Path(p) for p in args.paths]
    if args.all:
        # 상위 scenario_params 의 러너 포맷만 대상 — uam/ 하위는 다른 스키마(별도 포맷)
        paths += sorted((_ROOT / "config" / "scenario_params").glob("*.yaml"))
    if not paths:
        parser.error("경로를 지정하거나 --all 을 사용하세요")
    if args.output and len(paths) != 1:
        parser.error("-o/--output 은 단일 경로에만 사용할 수 있습니다")

    try:
        for path in paths:
            if args.detect:
                import yaml
                with open(path, encoding="utf-8") as f:
                    raw = yaml.safe_load(f)
                print(f"{path.name:<40} v{detect_version(raw)}")
                continue
            out = args.output if args.migrate else None
            result = migrate_file(path, out_path=out)
            print(f"{path.name:<40} {result.summary()}")
            for change in result.changes:
                print(f"    - {change}")
    except (FileNotFoundError, ValueError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

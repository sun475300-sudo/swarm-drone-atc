"""ODYSSEY Phase 469 — 정책 영향 시뮬레이션 (규제 파라미터 변경 효과 자동 비교).

규제 파라미터 — 이격 거리(lateral/vertical)와 고도 상한 — 를 바꿨을 때 공역
운용에 미치는 *1차(first-order) 효과* 를 결정적 해석 모델로 정량화하고 두
정책(baseline vs proposed)을 자동 비교한다. 정책 입안자가 "수평 이격을 50m →
70m 로 강화하면 동시 운용 가능 대수가 몇 % 줄어드는가?" 같은 질문에 즉시
답하기 위한 도구다.

모델 (해석적 용량 모델)
----------------------
공역을 *수직 분리 고도층* 의 적층으로 본다:

- 고도층 수 ``layers = floor((max_alt - min_alt) / vertical_min_m) + 1``
  (min_alt 부터 vertical_min_m 간격으로 놓이는 층, 양 끝 포함).
- 한 고도층 내에서는 드론이 수평 이격 ``lateral_min_m`` 을 만족하도록 육각
  최밀 충전(hexagonal close packing)된다고 가정한다. 점당 점유 면적은
  ``(sqrt(3)/2) * lateral_min_m**2`` (간격 s 의 육각 격자 셀 면적).
- ``per_layer = floor(area_m2 / cell_area)``,
  ``capacity = layers * per_layer``.

한계 (정직 공시 — CLAUDE.md)
---------------------------
이것은 전체 SimPy 시뮬레이션이 아니라 *정적 기하 용량 상한* 이다. 바람·기동·
경로 교차·컨트롤러 개입 동역학을 포함하지 않으므로 절대 대수는 낙관적 상한이다.
본 도구의 가치는 *절대값* 이 아니라 동일 모델 하의 두 정책 간 *상대 변화* 에
있다 — 그 비교는 동역학 가정이 양쪽에 동일하게 적용되어 1차 근사로 견고하다.

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python simulation/policy_impact.py                  # 기본 설정 용량
    python simulation/policy_impact.py --lateral 70     # 수평 이격 70m 효과
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# 육각 최밀 충전: 간격 s 의 격자에서 점당 점유 면적 계수 (sqrt(3)/2)
_HEX_PACKING_COEFF = math.sqrt(3.0) / 2.0

_DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config" / "default_simulation.yaml"


@dataclass(frozen=True)
class PolicyConfig:
    """공역 규제 정책 파라미터 (불변).

    Attributes:
        lateral_min_m: 수평 최소 이격 거리 (m).
        vertical_min_m: 수직 최소 이격 거리 (m).
        min_altitude_m: 운용 고도 하한 (AGL, m).
        max_altitude_m: 운용 고도 상한 (AGL, m).
        area_m2: 운용 공역 수평 면적 (m²).
    """

    lateral_min_m: float
    vertical_min_m: float
    min_altitude_m: float
    max_altitude_m: float
    area_m2: float

    def __post_init__(self) -> None:
        for name in ("lateral_min_m", "vertical_min_m", "area_m2"):
            value = getattr(self, name)
            if value <= 0.0:
                raise ValueError(f"{name} 는 양수여야 합니다: {value}")
        if self.min_altitude_m < 0.0:
            raise ValueError(f"min_altitude_m 는 0 이상이어야 합니다 (AGL): {self.min_altitude_m}")
        if self.max_altitude_m <= self.min_altitude_m:
            raise ValueError(
                f"max_altitude_m({self.max_altitude_m}) 는 "
                f"min_altitude_m({self.min_altitude_m}) 보다 커야 합니다"
            )
        # 운용 면적이 단일 드론의 수평 셀보다 작으면 용량 0 인 퇴화 정책 → 사전 차단
        cell_area = _HEX_PACKING_COEFF * self.lateral_min_m**2
        if self.area_m2 < cell_area:
            raise ValueError(
                f"area_m2({self.area_m2}) 가 수평 이격 셀 면적({cell_area:.1f}m²)보다 작아 "
                f"드론 1대도 수용할 수 없습니다 — 이격을 줄이거나 면적을 키우세요"
            )

    @property
    def altitude_band_m(self) -> float:
        """운용 가능 고도 폭 (m)."""
        return self.max_altitude_m - self.min_altitude_m

    @classmethod
    def from_config(cls, path: Path | str | None = None) -> PolicyConfig:
        """``config/default_simulation.yaml`` 에서 정책 파라미터를 적재한다.

        고도 상한은 airspace.bounds_km.z[1] 에서, 고도 하한은 *운용 실제 바닥*
        인 drones.min_altitude_m 와 z[0] 중 더 제약적인(높은) 값을 쓴다 — z[0]=0 만
        쓰면 드론이 실제로 날지 않는 지표 근처 고도층까지 세어 용량을 과대계상하기
        때문이다. 면적은 airspace.area_km2, 이격은 separation_standards 에서 읽는다.
        """
        import yaml

        cfg_path = Path(path) if path is not None else _DEFAULT_CONFIG
        data: dict[str, Any] = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}

        airspace = data.get("airspace", {})
        sep = data.get("separation_standards", {})
        drones = data.get("drones", {})

        z_bounds = airspace.get("bounds_km", {}).get("z", [0.0, 0.12])
        z_floor_m = float(z_bounds[0]) * 1000.0
        max_alt_m = float(z_bounds[1]) * 1000.0
        # 운용 바닥: 공역 경계 하한과 드론 운용 하한 중 더 높은(제약적인) 쪽
        drone_floor_m = float(drones.get("min_altitude_m", z_floor_m))
        min_alt_m = max(z_floor_m, drone_floor_m)
        area_m2 = float(airspace.get("area_km2", 100.0)) * 1_000_000.0

        return cls(
            lateral_min_m=float(sep.get("lateral_min_m", 50.0)),
            vertical_min_m=float(sep.get("vertical_min_m", 15.0)),
            min_altitude_m=min_alt_m,
            max_altitude_m=max_alt_m,
            area_m2=area_m2,
        )


def altitude_layers(policy: PolicyConfig) -> int:
    """수직 이격을 만족하는 고도층 수.

    ``floor(band / vertical_min_m) + 1`` — min_alt 부터 vertical_min_m 간격으로
    놓이는 층 수(양 끝 포함). band < vertical_min_m 이어도 최소 1개 층.
    """
    return int(policy.altitude_band_m // policy.vertical_min_m) + 1


def lateral_cell_area_m2(policy: PolicyConfig) -> float:
    """육각 최밀 충전 시 드론 1대가 점유하는 수평 면적 (m²)."""
    return _HEX_PACKING_COEFF * policy.lateral_min_m**2


def per_layer_capacity(policy: PolicyConfig) -> int:
    """단일 고도층의 안전 동시 수용 대수."""
    return int(policy.area_m2 // lateral_cell_area_m2(policy))


def airspace_capacity(policy: PolicyConfig) -> int:
    """정책 하에서 안전하게 동시 운용 가능한 드론 대수 (기하 상한)."""
    return altitude_layers(policy) * per_layer_capacity(policy)


def utilization(policy: PolicyConfig, drone_count: int) -> float:
    """요청 대수 대비 용량 활용률 ``drone_count / capacity``.

    1.0 초과는 과포화(용량 초과 운용 요청)를 의미한다.
    """
    if drone_count < 0:
        raise ValueError(f"drone_count 는 음수일 수 없습니다: {drone_count}")
    capacity = airspace_capacity(policy)
    if capacity == 0:
        raise ValueError("용량이 0 인 정책에서는 활용률을 정의할 수 없습니다")
    return drone_count / capacity


@dataclass(frozen=True)
class PolicyComparison:
    """두 정책 간 영향 비교 결과 (불변)."""

    baseline_capacity: int
    proposed_capacity: int
    drone_count: int
    baseline_utilization: float
    proposed_utilization: float

    @property
    def capacity_delta(self) -> int:
        """용량 변화량 (proposed - baseline). 음수면 용량 감소."""
        return self.proposed_capacity - self.baseline_capacity

    @property
    def capacity_pct_change(self) -> float:
        """용량 변화율 (%). baseline 대비. baseline 0 이면 0 반환."""
        if self.baseline_capacity == 0:
            return 0.0
        return 100.0 * self.capacity_delta / self.baseline_capacity

    @property
    def is_oversaturated(self) -> bool:
        """제안 정책에서 요청 대수가 용량을 초과하는지."""
        return self.proposed_utilization > 1.0

    def summary(self) -> str:
        """사람이 읽는 한 줄 요약."""
        if self.capacity_delta == 0:
            direction = "변동없음"
        elif self.capacity_delta < 0:
            direction = "감소"
        else:
            direction = "증가"
        sat = " ⚠ 과포화" if self.is_oversaturated else ""
        return (
            f"용량 {self.baseline_capacity} → {self.proposed_capacity} "
            f"({self.capacity_pct_change:+.1f}% {direction}), "
            f"활용률 {self.baseline_utilization:.2f} → {self.proposed_utilization:.2f}{sat}"
        )


def compare_policies(
    baseline: PolicyConfig, proposed: PolicyConfig, drone_count: int
) -> PolicyComparison:
    """baseline 대비 proposed 정책의 공역 용량·활용률 영향을 비교한다."""
    return PolicyComparison(
        baseline_capacity=airspace_capacity(baseline),
        proposed_capacity=airspace_capacity(proposed),
        drone_count=drone_count,
        baseline_utilization=utilization(baseline, drone_count),
        proposed_utilization=utilization(proposed, drone_count),
    )


def _cli(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="공역 규제 정책 영향 비교 (Phase 469)")
    parser.add_argument("--lateral", type=float, help="제안 수평 이격 거리 (m)")
    parser.add_argument("--vertical", type=float, help="제안 수직 이격 거리 (m)")
    parser.add_argument("--max-alt", type=float, help="제안 고도 상한 (m)")
    parser.add_argument("--drones", type=int, default=100, help="요청 동시 운용 대수")
    args = parser.parse_args(argv)

    baseline = PolicyConfig.from_config()
    print(f"[baseline] {baseline}")
    print(f"  고도층 {altitude_layers(baseline)} · 층당 {per_layer_capacity(baseline)} "
          f"· 용량 {airspace_capacity(baseline)}")

    if any(v is not None for v in (args.lateral, args.vertical, args.max_alt)):
        from dataclasses import replace

        proposed = replace(
            baseline,
            lateral_min_m=args.lateral if args.lateral is not None else baseline.lateral_min_m,
            vertical_min_m=args.vertical if args.vertical is not None else baseline.vertical_min_m,
            max_altitude_m=args.max_alt if args.max_alt is not None else baseline.max_altitude_m,
        )
        comparison = compare_policies(baseline, proposed, args.drones)
        print(f"[proposed] {proposed}")
        print(f"  {comparison.summary()}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys

    raise SystemExit(_cli(sys.argv[1:]))

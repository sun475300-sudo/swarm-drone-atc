"""
적대적 시나리오 퍼징 (ODYSSEY Phase 447)
=========================================
시드 기반 결정적 시나리오 변이 생성기.

기존 ``config/scenario_params/*.yaml`` 베이스 시나리오를 입력으로 받아, 동일
시드에 대해 항상 동일한 변이 집합을 생성한다(재현성). 생성된 변이는
``scenario_schema.validate_scenario`` 계약을 만족하므로 ``scenario_runner`` ·
시나리오 마켓플레이스에서 그대로 실행할 수 있다.

목적: 4,443건 검증 자산을 "고정 시나리오 통과"에서 "근방 시나리오 공간 전역
통과"로 격상. ``adversarial=True`` 모드는 부하 필드(드론 수·도착률)를 위로,
안전 마진 필드(공역 면적·최소 분리거리)를 아래로 편향시켜 안전망에 스트레스를
가한다.

설계 원칙:
- 외부 의존성은 numpy(프로젝트 RNG 규약)뿐 — 오프라인·결정적.
- 입력 dict 를 변형하지 않고 항상 새 객체를 반환한다(불변성).
- 합격/불합격 임계값인 ``success_criteria`` 는 변이하지 않는다 — 검증 의미 보존.

CLI:
    python simulation/scenario_fuzzer.py config/scenario_params/high_density.yaml -n 5
    python simulation/scenario_fuzzer.py config/scenario_params/high_density.yaml -n 5 --adversarial
"""
from __future__ import annotations

import copy
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

# 적대적 모드에서 위로 편향(부하 증가)되는 수치 필드
_LOAD_UP_INT_KEYS = ("drone_count", "base_drone_count", "total_drone_count")
_LOAD_UP_FLOAT_KEYS = ("arrival_rate_per_min",)
# 적대적 모드에서 아래로 편향(안전 마진 축소)되는 수치 필드
_MARGIN_DOWN_FLOAT_KEYS = ("area_km2",)
# route_generation 내부의 안전 마진(거리) 필드
_ROUTE_DISTANCE_KEYS = ("min_distance_km", "max_distance_km")


@dataclass(frozen=True)
class FuzzConfig:
    """퍼징 파라미터 분포.

    Attributes:
        jitter: 대칭 곱셈 지터 진폭. 필드값 × U(1-jitter, 1+jitter).
        adversarial: True 면 부하/마진 필드를 단방향으로 편향.
        adversarial_bias: 적대적 편향 추가 진폭.
        perturb_distribution: drone_profile_distribution 비율도 지터 후 재정규화.
    """

    jitter: float = 0.25
    adversarial: bool = False
    adversarial_bias: float = 0.35
    perturb_distribution: bool = True


class ScenarioFuzzer:
    """시드 기반 결정적 시나리오 변이 생성기."""

    def __init__(self, cfg: FuzzConfig | None = None, seed: int = 42) -> None:
        """주어진 설정·시드로 RNG 를 초기화한다."""
        self.cfg = cfg or FuzzConfig()
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    # ── 내부 헬퍼 ────────────────────────────────────────────────────────

    def _factor(self, *, margin: bool) -> float:
        """곱셈 변이 계수를 샘플한다.

        Args:
            margin: True 면 안전 마진 필드(작을수록 어려움), False 면 부하 필드.
        """
        j = self.cfg.jitter
        if not self.cfg.adversarial:
            return float(self.rng.uniform(1.0 - j, 1.0 + j))
        bias = self.cfg.adversarial_bias
        if margin:
            # 마진 축소: (1-j-bias, 1) 하한 양수 보장
            low = max(0.05, 1.0 - j - bias)
            return float(self.rng.uniform(low, 1.0))
        # 부하 증가: (1, 1+j+bias)
        return float(self.rng.uniform(1.0, 1.0 + j + bias))

    def _mutate_route(self, route: dict) -> dict:
        """route_generation 의 거리 필드를 변이하고 min<max 를 보장한다."""
        out = copy.deepcopy(route)
        present = [k for k in _ROUTE_DISTANCE_KEYS
                   if isinstance(out.get(k), (int, float))]
        for key in present:
            out[key] = max(0.1, round(out[key] * self._factor(margin=True), 3))
        if {"min_distance_km", "max_distance_km"} <= set(present):
            lo, hi = out["min_distance_km"], out["max_distance_km"]
            if lo >= hi:
                # 순서 역전 시 결정적 복원
                out["min_distance_km"], out["max_distance_km"] = (
                    min(lo, hi), max(lo, hi) + 0.1
                )
        return out

    def _mutate_distribution(self, dist: dict) -> dict:
        """프로파일 분포 비율을 지터 후 합 1.0 으로 재정규화한다."""
        ratios = {k: max(0.0, v * float(self.rng.uniform(1.0 - self.cfg.jitter,
                                                          1.0 + self.cfg.jitter)))
                  for k, v in dist.items() if isinstance(v, (int, float))}
        total = sum(ratios.values())
        if total <= 0:
            return copy.deepcopy(dist)
        return {k: round(v / total, 4) for k, v in ratios.items()}

    # ── 공개 API ─────────────────────────────────────────────────────────

    def mutate(self, base: dict, index: int = 0) -> dict:
        """베이스 시나리오의 변이 1건을 반환한다(입력 불변).

        Args:
            base: 파싱된 시나리오 dict.
            index: 변이 식별자(이름/설명 접미사용).

        Returns:
            새 시나리오 dict.
        """
        out = copy.deepcopy(base)

        for key in _LOAD_UP_INT_KEYS:
            if isinstance(out.get(key), int) and not isinstance(out[key], bool):
                out[key] = max(1, int(round(out[key] * self._factor(margin=False))))
        for key in _LOAD_UP_FLOAT_KEYS:
            if isinstance(out.get(key), (int, float)) and not isinstance(out[key], bool):
                out[key] = max(0.01, round(out[key] * self._factor(margin=False), 3))
        for key in _MARGIN_DOWN_FLOAT_KEYS:
            if isinstance(out.get(key), (int, float)) and not isinstance(out[key], bool):
                out[key] = max(0.1, round(out[key] * self._factor(margin=True), 3))

        if isinstance(out.get("route_generation"), dict):
            out["route_generation"] = self._mutate_route(out["route_generation"])

        if self.cfg.perturb_distribution and isinstance(
            out.get("drone_profile_distribution"), dict
        ):
            out["drone_profile_distribution"] = self._mutate_distribution(
                out["drone_profile_distribution"]
            )

        tag = "adv" if self.cfg.adversarial else "fuzz"
        base_name = str(base.get("scenario", "scenario"))
        out["scenario"] = f"{base_name}_{tag}{index:03d}_s{self.seed}"
        base_desc = str(base.get("description", "")).strip()
        out["description"] = (
            f"[{tag} seed={self.seed} #{index}] {base_desc}".strip()
        )
        return out

    def generate(self, base: dict, n: int) -> list[dict]:
        """베이스로부터 n 건의 결정적 변이를 생성한다."""
        if n < 0:
            raise ValueError(f"n 은 음수일 수 없음 (got {n})")
        return [self.mutate(base, index=i) for i in range(n)]


# ── CLI ──────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    """CLI: 시나리오 파일을 퍼징하고 검증 결과를 출력한다."""
    import argparse

    import yaml
    from scenario_schema import validate_scenario  # type: ignore

    parser = argparse.ArgumentParser(
        description="SDACS 적대적 시나리오 퍼저 (ODYSSEY Phase 447)"
    )
    parser.add_argument("path", help="베이스 시나리오 YAML 경로")
    parser.add_argument("-n", type=int, default=5, help="생성할 변이 수")
    parser.add_argument("--seed", type=int, default=42, help="RNG 시드")
    parser.add_argument("--adversarial", action="store_true", help="스트레스 편향 모드")
    args = parser.parse_args(argv)

    with open(args.path, encoding="utf-8") as f:
        base = yaml.safe_load(f)

    fuzzer = ScenarioFuzzer(
        FuzzConfig(adversarial=args.adversarial), seed=args.seed
    )
    variants = fuzzer.generate(base, args.n)

    any_invalid = False
    for v in variants:
        result = validate_scenario(v)
        flag = "VALID" if result.is_valid else f"INVALID ({len(result.errors)})"
        print(f"{v['scenario']:<48} {flag}")
        for err in result.errors:
            print(f"    ERROR: {err}")
            any_invalid = True
    return 1 if any_invalid else 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main())

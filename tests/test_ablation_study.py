"""Phase 286 — Safety-Net Ablation Study 테스트.

- resolution_rate / aggregate 헬퍼의 결정적 동작
- SwarmSimulator·AirspaceController 의 ablation 토글 plumbing
- run_single 통합 스모크 (짧은 시뮬레이션)
"""
from __future__ import annotations

import pytest

from scripts.ablation_study import (
    ABLATIONS,
    AblationRun,
    aggregate,
    resolution_rate,
    run_single,
)


class TestResolutionRate:
    def test_no_conflicts_returns_full(self):
        # Arrange / Act / Assert
        assert resolution_rate(conflicts=0, collisions=0) == 100.0

    def test_all_resolved(self):
        # 갈등 10건 전부 해소(충돌 0) → 100%
        assert resolution_rate(conflicts=10, collisions=0) == 100.0

    def test_half_collide(self):
        # 갈등 5 + 충돌 5 → 1 - 5/10 = 50%
        assert resolution_rate(conflicts=5, collisions=5) == 50.0

    def test_negative_denominator_guarded(self):
        assert resolution_rate(conflicts=-3, collisions=0) == 100.0


class TestAggregate:
    def test_groups_by_ablation_and_means(self):
        runs = [
            AblationRun("baseline", 0, 0, 2, 10, 100.0),
            AblationRun("baseline", 1, 2, 4, 10, 80.0),
            AblationRun("no_apf", 0, 6, 8, 10, 40.0),
        ]
        summaries = {s.ablation: s for s in aggregate(runs)}

        assert summaries["baseline"].n_runs == 2
        assert summaries["baseline"].collision_count_mean == 1.0
        assert summaries["baseline"].resolution_rate_mean == 90.0
        assert summaries["no_apf"].n_runs == 1
        assert summaries["no_apf"].collision_count_mean == 6.0

    def test_skips_absent_ablations(self):
        runs = [AblationRun("baseline", 0, 0, 0, 0, 100.0)]
        names = {s.ablation for s in aggregate(runs)}
        assert names == {"baseline"}


class TestAblationToggles:
    def test_disable_apf_flag_honored(self, sim_config):
        from simulation.simulator import SwarmSimulator

        sim = SwarmSimulator(
            config_path=sim_config,
            scenario_cfg={"ablation": {"disable_apf": True}},
            seed=0,
        )
        assert sim._ablate_apf is True

    def test_default_keeps_all_layers_active(self, sim_config):
        from simulation.simulator import SwarmSimulator

        sim = SwarmSimulator(config_path=sim_config, seed=0)
        assert sim._ablate_apf is False
        assert sim.controller._disable_cbs is False

    def test_disable_cbs_flag_honored(self, sim_config):
        from simulation.simulator import SwarmSimulator

        sim = SwarmSimulator(
            config_path=sim_config,
            scenario_cfg={"ablation": {"disable_cbs": True}},
            seed=0,
        )
        assert sim.controller._disable_cbs is True

    def test_disable_apf_yields_no_forces_after_run(self, sim_config):
        from simulation.simulator import SwarmSimulator

        sim = SwarmSimulator(
            config_path=sim_config,
            scenario_cfg={"ablation": {"disable_apf": True}},
            seed=0,
        )
        sim.run(duration_s=20.0)
        # APF 계층 비활성 시 회피 힘 캐시는 항상 비어 있어야 한다.
        assert sim.apf_forces == {}


@pytest.mark.e2e
class TestRunSingleIntegration:
    def test_baseline_completes(self):
        run = run_single("baseline", ABLATIONS["baseline"], seed=0, n_drones=4, duration_s=20.0)
        assert run.ablation == "baseline"
        assert run.collision_count >= 0
        assert 0.0 <= run.conflict_resolution_rate_pct <= 100.0

    def test_no_cbs_completes_without_cbs_attempts(self):
        run = run_single("no_cbs", ABLATIONS["no_cbs"], seed=0, n_drones=4, duration_s=20.0)
        assert run.ablation == "no_cbs"
        assert run.collision_count >= 0

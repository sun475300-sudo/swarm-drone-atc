"""Tests for src/swarm_sync.py — P696 Swarm Frame Synchronization."""

from __future__ import annotations

import math

import pytest

from src.swarm_sync import (
    DroneClockState,
    SwarmClock,
    SwarmSyncManager,
    _JITTER_TARGET_MS,
)


# ---------------------------------------------------------------------------
# DroneClockState
# ---------------------------------------------------------------------------


class TestDroneClockState:
    def test_is_frozen(self):
        state = DroneClockState(
            drone_id=1, offset_s=0.001, stratum=1, last_sync_time=0.0, synced=True
        )
        with pytest.raises((AttributeError, TypeError)):
            state.offset_s = 999.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SwarmClock
# ---------------------------------------------------------------------------


class TestSwarmClock:
    def test_initial_state_unsync(self):
        clock = SwarmClock(drone_id=1)
        assert not clock.is_synced
        assert clock.stratum == 255
        assert clock.offset_s == 0.0

    def test_initial_offset_reflected(self):
        clock = SwarmClock(drone_id=1, initial_offset_s=0.005)
        assert clock.offset_s == pytest.approx(0.005)

    def test_record_sync_marks_synced(self):
        clock = SwarmClock(drone_id=1)
        clock.record_sync(ref_time=1.0, measured_offset_s=0.002)
        assert clock.is_synced
        assert clock.stratum == 1

    def test_offset_converges_to_median(self):
        clock = SwarmClock(drone_id=1, window_size=5)
        samples = [0.001, 0.002, 0.003, 0.004, 0.005]
        for s in samples:
            clock.record_sync(ref_time=1.0, measured_offset_s=s)
        assert clock.offset_s == pytest.approx(0.003, abs=1e-9)

    def test_jitter_inf_with_single_sample(self):
        clock = SwarmClock(drone_id=1)
        clock.record_sync(ref_time=1.0, measured_offset_s=0.001)
        assert clock.jitter_ms == float("inf")

    def test_jitter_zero_for_identical_samples(self):
        clock = SwarmClock(drone_id=1)
        for _ in range(4):
            clock.record_sync(ref_time=1.0, measured_offset_s=0.001)
        assert clock.jitter_ms == pytest.approx(0.0, abs=1e-12)

    def test_jitter_matches_stddev(self):
        clock = SwarmClock(drone_id=1)
        samples = [0.001, 0.003]  # mean=0.002, sample stddev = sqrt(2e-6)
        for s in samples:
            clock.record_sync(ref_time=1.0, measured_offset_s=s)
        expected_ms = math.sqrt(2e-6) * 1000.0
        assert clock.jitter_ms == pytest.approx(expected_ms, rel=1e-6)

    def test_window_size_limits_samples(self):
        clock = SwarmClock(drone_id=1, window_size=3)
        for i in range(10):
            clock.record_sync(ref_time=float(i), measured_offset_s=float(i) * 0.001)
        # Only last 3 samples should be retained
        assert len(clock._samples) == 3

    def test_meets_jitter_target_false_with_large_noise(self):
        clock = SwarmClock(drone_id=1)
        for offset in [0.0, 0.1]:  # 100ms difference
            clock.record_sync(ref_time=1.0, measured_offset_s=offset)
        assert not clock.meets_jitter_target

    def test_meets_jitter_target_true_with_small_noise(self):
        clock = SwarmClock(drone_id=1)
        for offset in [0.001, 0.0011]:  # ~0.05ms stddev
            clock.record_sync(ref_time=1.0, measured_offset_s=offset)
        assert clock.meets_jitter_target

    def test_snapshot_returns_frozen_state(self):
        clock = SwarmClock(drone_id=7)
        clock.record_sync(ref_time=5.0, measured_offset_s=0.003)
        snap = clock.snapshot()
        assert isinstance(snap, DroneClockState)
        assert snap.drone_id == 7
        assert snap.synced is True
        assert snap.offset_s == pytest.approx(0.003)

    def test_reset_clears_sync_state(self):
        clock = SwarmClock(drone_id=1)
        clock.record_sync(ref_time=1.0, measured_offset_s=0.002)
        clock.reset()
        assert not clock.is_synced
        assert clock.stratum == 255
        assert clock.jitter_ms == float("inf")

    def test_jitter_target_constant_is_ten_ms(self):
        assert _JITTER_TARGET_MS == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# SwarmSyncManager
# ---------------------------------------------------------------------------


class TestSwarmSyncManager:
    def _mgr(self, n_drones=3, noise_std_s=0.0001, seed=0):
        mgr = SwarmSyncManager(noise_std_s=noise_std_s, window_size=8, seed=seed)
        for i in range(1, n_drones + 1):
            mgr.add_drone(drone_id=i, initial_offset_s=float(i) * 0.001)
        return mgr

    def test_add_drone_creates_clock(self):
        mgr = SwarmSyncManager()
        mgr.add_drone(drone_id=5)
        assert mgr.get_clock(5) is not None

    def test_get_clock_returns_none_for_unknown(self):
        mgr = SwarmSyncManager()
        assert mgr.get_clock(99) is None

    def test_run_sync_round_returns_snapshots_for_all_drones(self):
        mgr = self._mgr(n_drones=4)
        snapshots = mgr.run_sync_round(ref_time=0.0)
        assert len(snapshots) == 4

    def test_run_sync_round_snapshots_sorted_by_drone_id(self):
        mgr = self._mgr(n_drones=3)
        snapshots = mgr.run_sync_round(ref_time=0.0)
        assert [s.drone_id for s in snapshots] == [1, 2, 3]

    def test_run_sync_round_marks_drones_synced(self):
        mgr = self._mgr(n_drones=2)
        mgr.run_sync_round(ref_time=0.0)
        assert all(mgr.get_clock(i).is_synced for i in [1, 2])

    def test_offset_converges_after_many_rounds(self):
        mgr = SwarmSyncManager(noise_std_s=0.0, window_size=8, seed=0)
        true_offset = 0.005
        mgr.add_drone(drone_id=1, initial_offset_s=true_offset)
        for t in range(10):
            mgr.run_sync_round(ref_time=float(t))
        clock = mgr.get_clock(1)
        assert clock.offset_s == pytest.approx(true_offset, abs=1e-9)

    def test_fleet_jitter_returns_per_drone_dict(self):
        mgr = self._mgr(n_drones=3)
        for t in range(5):
            mgr.run_sync_round(ref_time=float(t))
        jitters = mgr.fleet_jitter_ms()
        assert set(jitters.keys()) == {1, 2, 3}
        assert all(isinstance(v, float) for v in jitters.values())

    def test_all_meet_jitter_target_with_zero_noise(self):
        mgr = SwarmSyncManager(noise_std_s=0.0, window_size=4, seed=0)
        for i in range(1, 4):
            mgr.add_drone(drone_id=i, initial_offset_s=0.001)
        for t in range(5):
            mgr.run_sync_round(ref_time=float(t))
        assert mgr.all_meet_jitter_target()

    def test_sync_summary_structure(self):
        mgr = self._mgr(n_drones=3)
        for t in range(5):
            mgr.run_sync_round(ref_time=float(t))
        summary = mgr.sync_summary()
        assert "synced_count" in summary
        assert "total_count" in summary
        assert "max_jitter_ms" in summary
        assert "all_meet_target" in summary
        assert summary["synced_count"] == 3
        assert summary["total_count"] == 3

    def test_sync_summary_no_synced_drones(self):
        mgr = self._mgr(n_drones=2)
        summary = mgr.sync_summary()
        assert summary["synced_count"] == 0
        assert summary["max_jitter_ms"] == float("inf")

    def test_reset_all_clears_sync(self):
        mgr = self._mgr(n_drones=2)
        mgr.run_sync_round(ref_time=0.0)
        mgr.reset()
        for i in [1, 2]:
            assert not mgr.get_clock(i).is_synced

    def test_reset_single_drone(self):
        mgr = self._mgr(n_drones=2)
        for t in range(3):
            mgr.run_sync_round(ref_time=float(t))
        mgr.reset(drone_id=1)
        assert not mgr.get_clock(1).is_synced
        assert mgr.get_clock(2).is_synced

    def test_reproducible_with_same_seed(self):
        mgr_a = self._mgr(n_drones=2, noise_std_s=0.001, seed=99)
        mgr_b = self._mgr(n_drones=2, noise_std_s=0.001, seed=99)
        snaps_a = [mgr_a.run_sync_round(float(t)) for t in range(5)]
        snaps_b = [mgr_b.run_sync_round(float(t)) for t in range(5)]
        for sa, sb in zip(snaps_a, snaps_b):
            for a, b in zip(sa, sb):
                assert a.offset_s == pytest.approx(b.offset_s, abs=1e-15)

    def test_empty_manager_returns_empty_list(self):
        mgr = SwarmSyncManager()
        assert mgr.run_sync_round(ref_time=0.0) == []
        assert mgr.fleet_jitter_ms() == {}
        assert mgr.all_meet_jitter_target() is True

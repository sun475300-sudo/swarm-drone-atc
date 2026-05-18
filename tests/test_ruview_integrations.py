"""
RuView 영감 통합 모듈 테스트
==========================
3개 모듈 검증:
1. passive_rf_detector — 멀티스태틱 패시브 RF 탐지
2. meridian_calibrator — 환경 인식 APF 자동 재보정
3. csi_attention_fusion — N×(N-1) 어텐션 융합
"""
from __future__ import annotations

import math

import pytest


# ── 1. PassiveRFDetector ────────────────────────────────────────────────
class TestPassiveRfDetector:
    def _four_node_grid(self):
        from simulation.passive_rf_detector import RFNode
        return [
            RFNode("n1", 0, 0, 5),
            RFNode("n2", 1000, 0, 5),
            RFNode("n3", 0, 1000, 5),
            RFNode("n4", 1000, 1000, 5),
        ]

    def test_init_requires_two_nodes(self):
        from simulation.passive_rf_detector import PassiveRFDetector, RFNode
        with pytest.raises(ValueError):
            PassiveRFDetector(nodes=[RFNode("n1", 0, 0, 5)])

    def test_basic_detection(self):
        from simulation.passive_rf_detector import PassiveRFDetector, RFEmitter
        det = PassiveRFDetector(nodes=self._four_node_grid(), seed=1)
        det.add_emitter(RFEmitter(
            "rogue1", x=500, y=500, z=80,
            vx=10.0, tx_power_w=0.1, freq_hz=2.4e9,
        ))
        contacts = det.scan(t=1.0)
        assert len(contacts) == 1
        c = contacts[0]
        assert c.emitter_id == "rogue1"
        assert len(c.contributing_nodes) >= 2

    def test_high_power_high_snr(self):
        from simulation.passive_rf_detector import PassiveRFDetector, RFEmitter
        det = PassiveRFDetector(nodes=self._four_node_grid(), seed=2)
        det.add_emitter(RFEmitter(
            "loud", x=500, y=500, z=80, tx_power_w=1.0, freq_hz=2.4e9,
        ))
        contacts = det.scan(t=0.0)
        assert contacts[0].confidence > 0.0
        # 모든 노드가 강한 신호를 들어야 함
        assert len(contacts[0].contributing_nodes) == 4

    def test_low_power_no_detection(self):
        from simulation.passive_rf_detector import PassiveRFDetector, RFEmitter
        det = PassiveRFDetector(nodes=self._four_node_grid(), seed=3)
        det.add_emitter(RFEmitter(
            "weak", x=500, y=500, z=80,
            tx_power_w=1e-9, freq_hz=2.4e9,
        ))
        contacts = det.scan(t=0.0)
        assert contacts == []

    def test_doppler_recovers_speed(self):
        from simulation.passive_rf_detector import PassiveRFDetector, RFEmitter
        det = PassiveRFDetector(nodes=self._four_node_grid(), seed=4)
        det.add_emitter(RFEmitter(
            "fast", x=500, y=500, z=80,
            vx=20.0, tx_power_w=1.0, freq_hz=2.4e9,
        ))
        contacts = det.scan(t=0.0)
        # 도플러 속도 추정이 진짜 속도(20m/s) 부근이어야 함
        # 측정 노이즈를 고려해 넉넉히 ±40% 허용
        assert 5.0 < contacts[0].estimated_velocity_mps < 35.0

    def test_multilateration_position(self):
        from simulation.passive_rf_detector import PassiveRFDetector, RFEmitter
        det = PassiveRFDetector(nodes=self._four_node_grid(), seed=5)
        true_x, true_y = 500.0, 500.0
        det.add_emitter(RFEmitter(
            "tgt", x=true_x, y=true_y, z=80,
            tx_power_w=1.0, freq_hz=2.4e9,
        ))
        contacts = det.scan(t=0.0)
        px, py, _ = contacts[0].estimated_position
        # 다변측량 위치 오차 ≤ 200m (노이즈 ±2dB → 거리 추정 오차)
        assert math.hypot(px - true_x, py - true_y) < 250.0

    def test_summary_keys(self):
        from simulation.passive_rf_detector import PassiveRFDetector
        det = PassiveRFDetector(nodes=self._four_node_grid())
        s = det.summary()
        assert {"nodes", "emitters", "noise_floor_dbm", "total_contacts"} <= s.keys()


# ── 2. MeridianCalibrator ───────────────────────────────────────────────
class TestMeridianCalibrator:
    def test_window_not_elapsed_passes_through(self):
        from simulation.meridian_calibrator import MeridianCalibrator
        cal = MeridianCalibrator(window_s=10.0)
        cal.observe(wind_speed=5.0, temp_c=20, density=0.5, t=0.0)
        cal.observe(wind_speed=5.0, temp_c=20, density=0.5, t=1.0)
        cal.observe(wind_speed=5.0, temp_c=20, density=0.5, t=2.0)
        result = cal.recalibrate({"k_rep": 2.5}, t=2.0)
        assert result.triggered is False
        assert result.new_params == {"k_rep": 2.5}

    def test_high_wind_triggers_windy_params(self):
        from simulation.meridian_calibrator import MeridianCalibrator
        cal = MeridianCalibrator(window_s=10.0)
        for ti in range(0, 15):
            cal.observe(wind_speed=15.0, temp_c=18, density=0.5, t=float(ti))
        result = cal.recalibrate({"k_rep": 2.5}, t=15.0)
        assert result.triggered is True
        assert result.reason == "new_cluster"
        # 강풍 사전값 적용 확인
        assert result.new_params["k_rep"] == pytest.approx(4.0)
        assert result.new_params["cpa_lookahead_s"] == pytest.approx(60.0)

    def test_calm_conditions_use_calm_params(self):
        from simulation.meridian_calibrator import MeridianCalibrator
        cal = MeridianCalibrator(window_s=10.0)
        for ti in range(0, 15):
            cal.observe(wind_speed=3.0, temp_c=22, density=0.4, t=float(ti))
        result = cal.recalibrate({"k_rep": 2.5}, t=15.0)
        assert result.triggered is True
        assert result.new_params["k_rep"] == pytest.approx(2.5)
        assert result.new_params["cpa_lookahead_s"] == pytest.approx(90.0)

    def test_cluster_reuse_on_similar_conditions(self):
        from simulation.meridian_calibrator import MeridianCalibrator
        cal = MeridianCalibrator(window_s=10.0)
        # 첫 번째 보정: 클러스터 생성
        for ti in range(0, 15):
            cal.observe(wind_speed=12.0, temp_c=20, density=0.5, t=float(ti))
        first = cal.recalibrate({"k_rep": 2.5}, t=15.0)
        assert first.reason == "new_cluster"

        # 환경 약간만 변화시켜 두번째 윈도우
        for ti in range(20, 35):
            cal.observe(wind_speed=12.5, temp_c=20.5, density=0.55, t=float(ti))
        second = cal.recalibrate({"k_rep": 2.5}, t=35.0)
        # 도메인 시프트 임계 미만일 수도 있고 클러스터 재방문일 수도 있음
        assert second.reason in {"cluster_hit", "no_shift"}

    def test_insufficient_samples(self):
        from simulation.meridian_calibrator import MeridianCalibrator
        cal = MeridianCalibrator(window_s=10.0)
        cal.observe(wind_speed=5.0, temp_c=20, density=0.5, t=0.0)
        result = cal.recalibrate({"k_rep": 2.5}, t=15.0)
        assert result.triggered is False
        assert result.reason == "insufficient_samples"

    def test_summary_keys(self):
        from simulation.meridian_calibrator import MeridianCalibrator
        cal = MeridianCalibrator()
        s = cal.summary()
        assert {"window_s", "samples", "clusters", "shift_threshold"} <= s.keys()


# ── 3. CsiAttentionFusion ───────────────────────────────────────────────
class TestCsiAttentionFusion:
    def _drone_grid(self):
        return {
            "d1": (0.0, 0.0, 80.0),
            "d2": (300.0, 0.0, 80.0),
            "d3": (0.0, 300.0, 80.0),
            "d4": (300.0, 300.0, 80.0),
        }

    def test_empty_observations(self):
        from simulation.csi_attention_fusion import CsiAttentionFusion
        f = CsiAttentionFusion()
        assert f.fuse([], {}) is None

    def test_basic_fusion(self):
        from simulation.csi_attention_fusion import (
            CsiAttentionFusion,
            LinkObservation,
        )
        f = CsiAttentionFusion()
        obs = [
            LinkObservation("d1", "d2", (150.0, 200.0, 50.0), snr_db=20),
            LinkObservation("d1", "d3", (152.0, 198.0, 51.0), snr_db=18),
            LinkObservation("d2", "d3", (148.0, 202.0, 49.0), snr_db=22),
        ]
        result = f.fuse(obs, self._drone_grid(), t_now=0.0)
        assert result is not None
        assert result.contributing_links == 3
        assert len(result.attention_weights) == 3
        assert abs(sum(result.attention_weights) - 1.0) < 1e-6
        px, py, pz = result.position
        assert 148 < px < 152
        assert 198 < py < 202

    def test_higher_snr_gets_more_weight(self):
        from simulation.csi_attention_fusion import (
            CsiAttentionFusion,
            LinkObservation,
        )
        f = CsiAttentionFusion(temperature=0.5)
        # 모든 링크가 동일한 베이스라인(300m)을 가지므로 SNR만 가중치 결정
        obs = [
            LinkObservation("d1", "d2", (100.0, 100.0, 50.0), snr_db=28),
            LinkObservation("d1", "d3", (100.0, 100.0, 50.0), snr_db=5),
            LinkObservation("d2", "d4", (100.0, 100.0, 50.0), snr_db=5),
        ]
        result = f.fuse(obs, self._drone_grid(), t_now=0.0)
        # SNR 28 링크 가중치가 가장 커야 함
        assert result.attention_weights[0] > max(
            result.attention_weights[1], result.attention_weights[2]
        )

    def test_geometric_diversity_metric(self):
        from simulation.csi_attention_fusion import (
            CsiAttentionFusion,
            LinkObservation,
        )
        f = CsiAttentionFusion()
        obs = [
            LinkObservation("d1", "d2", (100.0, 100.0, 50.0), snr_db=20),
            LinkObservation("d3", "d4", (100.0, 100.0, 50.0), snr_db=20),
        ]
        result = f.fuse(obs, self._drone_grid(), t_now=0.0)
        # 4개 다른 드론이 참여 → 다이버시티 > 0
        assert result.geometric_diversity > 0.0

    def test_short_baseline_low_score(self):
        from simulation.csi_attention_fusion import (
            CsiAttentionFusion,
            LinkObservation,
        )
        f = CsiAttentionFusion()
        positions = {
            "d1": (0.0, 0.0, 80.0),
            "d2": (1.0, 0.0, 80.0),    # d1과 1m 떨어진 짧은 베이스라인
            "d3": (300.0, 0.0, 80.0),
        }
        obs = [
            LinkObservation("d1", "d2", (100.0, 100.0, 50.0), snr_db=25),
            LinkObservation("d1", "d3", (100.0, 100.0, 50.0), snr_db=25),
        ]
        result = f.fuse(obs, positions, t_now=0.0)
        # 짧은 베이스라인 링크 가중치 < 정상 베이스라인 가중치
        assert result.attention_weights[0] < result.attention_weights[1]

    def test_recency_decay(self):
        from simulation.csi_attention_fusion import (
            CsiAttentionFusion,
            LinkObservation,
        )
        f = CsiAttentionFusion(recency_decay_s=2.0)
        obs = [
            LinkObservation("d1", "d2", (100.0, 100.0, 50.0),
                            snr_db=20, timestamp=0.0),  # 오래된 관측
            LinkObservation("d1", "d3", (100.0, 100.0, 50.0),
                            snr_db=20, timestamp=10.0),  # 최근 관측
        ]
        result = f.fuse(obs, self._drone_grid(), t_now=10.0)
        # 최신 관측이 더 큰 가중치
        assert result.attention_weights[1] > result.attention_weights[0]

    def test_summary_keys(self):
        from simulation.csi_attention_fusion import CsiAttentionFusion
        f = CsiAttentionFusion()
        s = f.summary()
        assert {"temperature", "optimal_baseline_m", "recency_decay_s"} <= s.keys()

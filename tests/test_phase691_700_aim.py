"""Phase 691-700: Aeronautical Information Management 모듈 테스트."""

import time

import numpy as np
import pytest


# ── NOTAM Manager ────────────────────────────────────────────────────
class TestNotamManager:
    def test_create_and_query_active(self):
        from simulation.notam_manager import NotamManager, NotamCategory
        mgr = NotamManager()
        nid = mgr.create_notam(
            NotamCategory.HAZARD, (37.5, 127.0), 1000.0, 0.0, 120.0, 2.0, "test"
        )
        assert nid.startswith("NOTAM-")
        active = mgr.query_active(area_center=(37.5, 127.0), radius_m=500.0, altitude=50.0)
        assert len(active) == 1

    def test_cancel_notam(self):
        from simulation.notam_manager import NotamManager, NotamCategory
        mgr = NotamManager()
        nid = mgr.create_notam(NotamCategory.OBSTACLE, (0, 0), 100.0, 0.0, 100.0, 1.0, "x")
        assert mgr.cancel_notam(nid)
        assert mgr.get(nid).status.value == "cancelled"

    def test_expire_old(self):
        from simulation.notam_manager import NotamManager, NotamCategory
        mgr = NotamManager()
        nid = mgr.create_notam(NotamCategory.SERVICE, (0, 0), 100.0, 0.0, 100.0, 1.0, "x")
        mgr.get(nid).valid_until = time.time() - 10.0
        expired = mgr.expire_old()
        assert expired == 1

    def test_extend_notam(self):
        from simulation.notam_manager import NotamManager, NotamCategory
        mgr = NotamManager()
        nid = mgr.create_notam(NotamCategory.AIRSPACE, (0, 0), 100.0, 0.0, 100.0, 1.0, "x")
        original = mgr.get(nid).valid_until
        assert mgr.extend_notam(nid, 2.0)
        assert mgr.get(nid).valid_until > original

    def test_invalid_params_raise(self):
        from simulation.notam_manager import NotamManager, NotamCategory
        mgr = NotamManager()
        with pytest.raises(ValueError):
            mgr.create_notam(NotamCategory.HAZARD, (0, 0), -1.0, 0.0, 100.0, 1.0, "x")

    def test_stats(self):
        from simulation.notam_manager import NotamManager, NotamCategory
        mgr = NotamManager()
        mgr.create_notam(NotamCategory.HAZARD, (0, 0), 100.0, 0.0, 100.0, 1.0, "x")
        stats = mgr.get_stats()
        assert stats["total"] == 1


# ── TFR Handler ──────────────────────────────────────────────────────
class TestTfrHandler:
    def test_declare_and_active(self):
        from simulation.tfr_handler import TfrHandler, TfrReason
        h = TfrHandler()
        tid = h.declare_tfr(TfrReason.VIP, (37.5, 127.0), 2000.0, 0.0, 500.0, 1.0)
        assert h.is_active(tid)

    def test_violation_detected(self):
        from simulation.tfr_handler import TfrHandler, TfrReason
        h = TfrHandler()
        tid = h.declare_tfr(TfrReason.DISASTER, (0.0, 0.0), 1000.0, 0.0, 500.0, 1.0)
        violations = h.check_violation("INTRUDER", (100.0, 100.0, 100.0))
        assert tid in violations

    def test_authorized_callsign_no_violation(self):
        from simulation.tfr_handler import TfrHandler, TfrReason
        h = TfrHandler()
        tid = h.declare_tfr(
            TfrReason.SECURITY, (0.0, 0.0), 1000.0, 0.0, 500.0, 1.0, authorized=["POLICE1"]
        )
        assert h.check_violation("POLICE1", (100.0, 100.0, 100.0)) == []

    def test_authorize_after_declare(self):
        from simulation.tfr_handler import TfrHandler, TfrReason
        h = TfrHandler()
        tid = h.declare_tfr(TfrReason.SPORTS, (0.0, 0.0), 500.0, 0.0, 300.0, 1.0)
        assert h.authorize(tid, "BLIMP1")
        assert h.check_violation("BLIMP1", (50.0, 50.0, 100.0)) == []

    def test_revoke(self):
        from simulation.tfr_handler import TfrHandler, TfrReason
        h = TfrHandler()
        tid = h.declare_tfr(TfrReason.HAZMAT, (0.0, 0.0), 500.0, 0.0, 300.0, 1.0)
        assert h.revoke(tid)
        assert not h.is_active(tid)

    def test_invalid_geometry_raises(self):
        from simulation.tfr_handler import TfrHandler, TfrReason
        h = TfrHandler()
        with pytest.raises(ValueError):
            h.declare_tfr(TfrReason.WILDFIRE, (0, 0), 0.0, 0.0, 100.0, 1.0)


# ── Vertiport Ops ────────────────────────────────────────────────────
class TestVertiportOps:
    def test_add_pad_and_reserve(self):
        from simulation.vertiport_ops import VertiportOps
        v = VertiportOps("VP-TEST")
        v.add_pad("P1", (0.0, 0.0))
        slot = v.reserve_slot("AIR1", desired_time=1000.0, duration_s=600.0)
        assert slot is not None

    def test_conflict_sends_to_queue(self):
        from simulation.vertiport_ops import VertiportOps
        v = VertiportOps()
        v.add_pad("P1", (0.0, 0.0))
        v.reserve_slot("AIR1", 1000.0, duration_s=600.0)
        slot2 = v.reserve_slot("AIR2", 1100.0, duration_s=600.0)
        assert slot2 is None
        assert "AIR2" in v.wait_queue

    def test_weight_filter(self):
        from simulation.vertiport_ops import VertiportOps
        v = VertiportOps()
        v.add_pad("P1", (0.0, 0.0), max_weight=1000.0)
        slot = v.reserve_slot("HEAVY", 1000.0, weight_kg=2000.0)
        assert slot is None

    def test_cancel_reservation(self):
        from simulation.vertiport_ops import VertiportOps
        v = VertiportOps()
        v.add_pad("P1", (0.0, 0.0))
        slot = v.reserve_slot("AIR1", 1000.0)
        assert v.cancel_reservation(slot)

    def test_land_and_depart(self):
        from simulation.vertiport_ops import VertiportOps, PadStatus
        v = VertiportOps()
        v.add_pad("P1", (0.0, 0.0))
        slot = v.reserve_slot("AIR1", 1000.0)
        assert v.land(slot)
        assert v.pads["P1"].status == PadStatus.OCCUPIED
        assert v.depart("P1")
        assert v.pads["P1"].status == PadStatus.AVAILABLE

    def test_maintenance(self):
        from simulation.vertiport_ops import VertiportOps, PadStatus
        v = VertiportOps()
        v.add_pad("P1", (0.0, 0.0))
        v.set_maintenance("P1", True)
        assert v.pads["P1"].status == PadStatus.MAINTENANCE

    def test_stats(self):
        from simulation.vertiport_ops import VertiportOps
        v = VertiportOps()
        v.add_pad("P1", (0.0, 0.0))
        v.add_pad("P2", (10.0, 10.0))
        stats = v.get_stats()
        assert stats["pads_total"] == 2


# ── METAR Parser ────────────────────────────────────────────────────
class TestMetarParser:
    def test_parse_basic_metar(self):
        from simulation.metar_parser import MetarParser
        p = MetarParser()
        text = "RKSI 091200Z 27015KT 9999 FEW030 18/10 Q1013"
        obs = p.parse_metar(text)
        assert obs.station == "RKSI"
        assert obs.wind_dir_deg == 270
        assert obs.wind_speed_kt == 15
        assert obs.temperature_c == 18
        assert obs.dewpoint_c == 10
        assert obs.altimeter_hpa == 1013

    def test_parse_metar_with_gust_and_conditions(self):
        from simulation.metar_parser import MetarParser
        p = MetarParser()
        text = "KJFK 091200Z 18020G35KT 5000 RA BR BKN010 15/14 Q1005"
        obs = p.parse_metar(text)
        assert obs.gust_kt == 35
        assert "rain" in obs.conditions
        assert obs.clouds[0][0] == "BKN"

    def test_parse_taf(self):
        from simulation.metar_parser import MetarParser
        p = MetarParser()
        text = "TAF RKSI 091200Z 0912/1018 27010KT 5SM"
        taf = p.parse_taf(text)
        assert taf.station == "RKSI"
        assert taf.wind_speed_kt == 10
        assert taf.valid_from == "0912"
        assert taf.valid_to == "1018"

    def test_vfr_assessment(self):
        from simulation.metar_parser import MetarParser
        p = MetarParser()
        vfr_obs = p.parse_metar("RKSI 091200Z 27010KT 9999 FEW040 18/10 Q1013")
        assert p.is_vfr(vfr_obs) is True
        ifr_obs = p.parse_metar("KJFK 091200Z 18020KT 1SM OVC003 15/14 Q1005")
        assert p.is_vfr(ifr_obs) is False

    def test_empty_raises(self):
        from simulation.metar_parser import MetarParser
        p = MetarParser()
        with pytest.raises(ValueError):
            p.parse_metar("")
        with pytest.raises(ValueError):
            p.parse_taf("")


# ── Cross-border Coordinator ─────────────────────────────────────────
class TestCrossBorderCoordinator:
    def _fixture(self):
        from simulation.cross_border_coord import CrossBorderCoordinator, AirspaceAuthority
        c = CrossBorderCoordinator()
        c.register_authority(AirspaceAuthority("KR", "Korea", required_docs=["manifest", "insurance"]))
        c.register_authority(AirspaceAuthority("JP", "Japan", required_docs=["manifest"]))
        return c

    def test_propose_and_accept(self):
        c = self._fixture()
        cid = c.propose_crossing("AIR1", "KR", "JP", (35.0, 130.0), 1000.0, 3000.0)
        assert cid is not None
        assert c.submit_document(cid, "manifest")
        assert c.all_documents_ready(cid)
        assert c.accept_handoff(cid)

    def test_cannot_accept_without_docs(self):
        c = self._fixture()
        cid = c.propose_crossing("AIR1", "JP", "KR", (35.0, 130.0), 1000.0, 3000.0)
        assert c.accept_handoff(cid) is False

    def test_invalid_authority(self):
        c = self._fixture()
        assert c.propose_crossing("AIR1", "KR", "US", (0, 0), 0, 0) is None

    def test_reject_and_complete(self):
        c = self._fixture()
        cid = c.propose_crossing("AIR1", "KR", "JP", (35.0, 130.0), 1000.0, 3000.0)
        assert c.reject_handoff(cid, "bad plan")
        cid2 = c.propose_crossing("AIR2", "JP", "KR", (35.0, 130.0), 1100.0, 3000.0)
        c.submit_document(cid2, "manifest")
        c.submit_document(cid2, "insurance")
        c.accept_handoff(cid2)
        assert c.complete_handoff(cid2)

    def test_stats(self):
        c = self._fixture()
        cid = c.propose_crossing("AIR1", "KR", "JP", (35.0, 130.0), 1000.0, 3000.0)
        s = c.get_stats()
        assert s["authorities"] == 2
        assert s["crossings"] == 1


# ── Insurance Risk ──────────────────────────────────────────────────
class TestInsuranceRisk:
    def _factors(self, **over):
        from simulation.insurance_risk import RiskFactors
        base = {
            "population_density": 1000.0,
            "flight_hours": 5.0,
            "weather_severity": 0.2,
            "drone_mtow_kg": 3.0,
            "operator_experience_hours": 200.0,
            "payload_hazard_level": 1,
            "proximity_airports_km": 20.0,
        }
        base.update(over)
        return RiskFactors(**base)

    def test_compute_risk_bounds(self):
        from simulation.insurance_risk import InsuranceRiskCalculator
        calc = InsuranceRiskCalculator()
        score = calc.compute_risk_score(self._factors())
        assert 0.0 <= score <= 2.0

    def test_recommend_tier(self):
        from simulation.insurance_risk import InsuranceRiskCalculator, CoverageTier
        calc = InsuranceRiskCalculator()
        low = calc.recommend_tier(0.2)
        high = calc.recommend_tier(1.5)
        assert low == CoverageTier.BASIC
        assert high == CoverageTier.PREMIUM

    def test_quote_fields(self):
        from simulation.insurance_risk import InsuranceRiskCalculator
        calc = InsuranceRiskCalculator()
        q = calc.quote(self._factors())
        for key in ("risk_score", "recommended_tier", "premium_krw", "coverage_limit_krw"):
            assert key in q

    def test_invalid_factors_raise(self):
        from simulation.insurance_risk import InsuranceRiskCalculator
        calc = InsuranceRiskCalculator()
        with pytest.raises(ValueError):
            calc.compute_risk_score(self._factors(flight_hours=-1.0))

    def test_stats(self):
        from simulation.insurance_risk import InsuranceRiskCalculator
        calc = InsuranceRiskCalculator()
        calc.quote(self._factors())
        calc.quote(self._factors(drone_mtow_kg=15.0))
        stats = calc.stats()
        assert stats["quotes"] == 2


# ── Aero Charts ─────────────────────────────────────────────────────
class TestAeroCharts:
    def _chart(self):
        from simulation.aero_charts import AeroCharts, ChartFeature, ChartFeatureType
        c = AeroCharts()
        c.bulk_add([
            ChartFeature("F1", ChartFeatureType.AIRPORT, (0.0, 0.0), 10.0, "Home"),
            ChartFeature("F2", ChartFeatureType.OBSTACLE, (50.0, 50.0), 120.0, "Tower"),
            ChartFeature("F3", ChartFeatureType.RADIO_TOWER, (200.0, 0.0), 100.0, "Antenna"),
        ])
        return c

    def test_nearby_filter(self):
        from simulation.aero_charts import ChartFeatureType
        c = self._chart()
        near = c.nearby((0.0, 0.0), 100.0)
        assert len(near) == 2
        obstacles = c.nearby((0.0, 0.0), 100.0, feature_type=ChartFeatureType.OBSTACLE)
        assert len(obstacles) == 1

    def test_nearest(self):
        c = self._chart()
        nearest = c.nearest((10.0, 10.0))
        assert nearest.feature_id == "F1"

    def test_path_obstacles(self):
        c = self._chart()
        hazards = c.path_obstacles(
            waypoints=[(0.0, 0.0), (100.0, 100.0)], corridor_width_m=50.0
        )
        assert any(h.feature_id == "F2" for h in hazards)

    def test_remove(self):
        c = self._chart()
        assert c.remove("F1")
        assert c.get("F1") is None

    def test_stats(self):
        c = self._chart()
        s = c.stats()
        assert s["total"] == 3
        assert "airport" in s["by_type"]


# ── Flight Following ────────────────────────────────────────────────
class TestFlightFollowing:
    def test_register_and_report(self):
        from simulation.flight_following import FlightFollowingService
        svc = FlightFollowingService()
        svc.register_flight("AIR1", "FP-1", [(0, 0, 50), (1000, 0, 50)])
        r = svc.report_position("AIR1", (500.0, 0.0, 50.0), (20, 0, 0), 90.0)
        assert r["ok"]
        assert r["deviation_m"] < 10.0

    def test_deviation_triggers_alert(self):
        from simulation.flight_following import FlightFollowingService
        svc = FlightFollowingService(deviation_tolerance_m=100.0)
        svc.register_flight("AIR1", "FP-1", [(0, 0, 50), (1000, 0, 50)])
        svc.report_position("AIR1", (500.0, 500.0, 50.0), (0, 20, 0), 80.0)
        assert svc.tracks["AIR1"].deviation_alerts == 1

    def test_lost_comms_sweep(self):
        from simulation.flight_following import FlightFollowingService, TrackState
        svc = FlightFollowingService(comms_timeout_s=1.0)
        svc.register_flight("AIR1", "FP-1", [(0, 0, 50), (1000, 0, 50)])
        svc.report_position("AIR1", (0, 0, 50), (10, 0, 0), 100)
        lost = svc.sweep_lost_comms(current_time=time.time() + 10.0)
        assert "AIR1" in lost
        assert svc.tracks["AIR1"].state == TrackState.LOST_COMMS

    def test_state_transitions(self):
        from simulation.flight_following import FlightFollowingService, TrackState
        svc = FlightFollowingService()
        svc.register_flight("AIR1", "FP-1", [(0, 0, 50), (1000, 0, 50)])
        assert svc.declare_hold("AIR1")
        assert svc.tracks["AIR1"].state == TrackState.HOLDING
        assert svc.declare_diversion("AIR1")
        assert svc.tracks["AIR1"].state == TrackState.DIVERTED
        assert svc.declare_completed("AIR1")
        assert svc.tracks["AIR1"].state == TrackState.COMPLETED

    def test_unregistered_rejected(self):
        from simulation.flight_following import FlightFollowingService
        svc = FlightFollowingService()
        r = svc.report_position("GHOST", (0, 0, 0), (0, 0, 0), 100.0)
        assert r["ok"] is False

    def test_stats(self):
        from simulation.flight_following import FlightFollowingService
        svc = FlightFollowingService()
        svc.register_flight("AIR1", "FP-1", [(0, 0, 50), (1000, 0, 50)])
        svc.report_position("AIR1", (100, 0, 50), (10, 0, 0), 90.0)
        stats = svc.stats()
        assert stats["tracks"] == 1
        assert stats["total_track_points"] == 1


# ── AIM Briefing Service ────────────────────────────────────────────
class TestAimBriefing:
    def _build(self):
        from simulation.aim_briefing import AimBriefingService
        from simulation.notam_manager import NotamManager, NotamCategory
        from simulation.tfr_handler import TfrHandler
        from simulation.aero_charts import AeroCharts, ChartFeature, ChartFeatureType
        from simulation.metar_parser import MetarParser

        notam = NotamManager()
        notam.create_notam(NotamCategory.OBSTACLE, (500.0, 0.0), 50.0, 0.0, 120.0, 2.0, "tower")
        tfr = TfrHandler()
        charts = AeroCharts()
        charts.add_feature(ChartFeature("O1", ChartFeatureType.OBSTACLE, (500.0, 0.0), 80.0, "Tower"))
        parser = MetarParser()
        svc = AimBriefingService(notam, tfr, charts, parser)
        return svc

    def test_generate_conflict(self):
        from simulation.aim_briefing import BriefingRequest
        svc = self._build()
        req = BriefingRequest(
            callsign="AIR1",
            departure=(0.0, 0.0),
            destination=(1000.0, 0.0),
            route_waypoints=[(500.0, 0.0)],
            planned_altitude_m=50.0,
            departure_time=time.time(),
        )
        result = svc.generate(req)
        assert result.go_nogo == "NO-GO"
        assert len(result.notam_conflicts) >= 1

    def test_generate_clear(self):
        from simulation.aim_briefing import AimBriefingService, BriefingRequest
        from simulation.notam_manager import NotamManager
        from simulation.tfr_handler import TfrHandler
        from simulation.aero_charts import AeroCharts
        from simulation.metar_parser import MetarParser
        svc = AimBriefingService(NotamManager(), TfrHandler(), AeroCharts(), MetarParser())
        req = BriefingRequest(
            "AIR2", (0.0, 0.0), (1000.0, 0.0), [(500.0, 0.0)], 50.0, time.time()
        )
        result = svc.generate(req, metar_text="RKSI 091200Z 27010KT 9999 FEW040 18/10 Q1013")
        assert result.go_nogo == "GO"

    def test_weather_bad_forces_nogo(self):
        from simulation.aim_briefing import AimBriefingService, BriefingRequest
        from simulation.notam_manager import NotamManager
        from simulation.tfr_handler import TfrHandler
        from simulation.aero_charts import AeroCharts
        from simulation.metar_parser import MetarParser
        svc = AimBriefingService(NotamManager(), TfrHandler(), AeroCharts(), MetarParser())
        req = BriefingRequest(
            "AIR3", (0.0, 0.0), (1000.0, 0.0), [], 50.0, time.time()
        )
        result = svc.generate(req, metar_text="KJFK 091200Z 18020KT 1SM OVC003 15/14 Q1005")
        assert result.go_nogo == "NO-GO"
        assert result.weather_ok is False

    def test_stats(self):
        from simulation.aim_briefing import AimBriefingService, BriefingRequest
        from simulation.notam_manager import NotamManager
        svc = AimBriefingService(NotamManager())
        req = BriefingRequest("AIR1", (0, 0), (1, 1), [], 50.0, time.time())
        svc.generate(req)
        svc.generate(req)
        stats = svc.stats()
        assert stats["briefings"] == 2


# ── Post Flight Reporter ────────────────────────────────────────────
class TestPostFlightReporter:
    def _track(self, duration=600.0, n=10):
        t0 = time.time()
        pts = []
        for i in range(n):
            t = t0 + i * (duration / (n - 1))
            pos = (i * 100.0, 0.0, 50.0)
            fuel = 100.0 - i * 5.0
            pts.append((t, pos, fuel))
        return pts

    def test_build_success_report(self):
        from simulation.post_flight_report import PostFlightReporter, ReportOutcome
        r = PostFlightReporter()
        report = r.build_report("AIR1", "FP-1", self._track(), events=[])
        assert report.outcome == ReportOutcome.SUCCESS
        assert report.metrics.distance_m > 0

    def test_collision_triggers_incident(self):
        from simulation.post_flight_report import PostFlightReporter, ReportOutcome
        r = PostFlightReporter()
        report = r.build_report("AIR1", "FP-1", self._track(), collisions=1)
        assert report.outcome == ReportOutcome.INCIDENT

    def test_abort_event_triggers_aborted(self):
        from simulation.post_flight_report import PostFlightReporter, ReportOutcome
        r = PostFlightReporter()
        report = r.build_report("AIR1", "FP-1", self._track(), events=["ABORT: low battery"])
        assert report.outcome == ReportOutcome.ABORTED

    def test_degraded_on_deviation(self):
        from simulation.post_flight_report import PostFlightReporter, ReportOutcome
        r = PostFlightReporter()
        report = r.build_report("AIR1", "FP-1", self._track(), deviation_alerts=10)
        assert report.outcome == ReportOutcome.DEGRADED

    def test_export_summary(self):
        from simulation.post_flight_report import PostFlightReporter
        r = PostFlightReporter()
        report = r.build_report("AIR1", "FP-1", self._track())
        summary = r.export_summary(report.report_id)
        assert summary["callsign"] == "AIR1"
        assert "distance_m" in summary

    def test_insufficient_points_raises(self):
        from simulation.post_flight_report import PostFlightReporter
        r = PostFlightReporter()
        with pytest.raises(ValueError):
            r.build_report("AIR1", "FP-1", [(0.0, (0, 0, 0), 100.0)])

    def test_outcome_distribution(self):
        from simulation.post_flight_report import PostFlightReporter
        r = PostFlightReporter()
        r.build_report("AIR1", "FP-1", self._track())
        r.build_report("AIR2", "FP-2", self._track(), collisions=1)
        dist = r.outcome_distribution()
        assert dist.get("success", 0) == 1
        assert dist.get("incident", 0) == 1


# ── Memory-Leak Defence Tests ────────────────────────────────────────
class TestMemoryLeakDefence:
    """각 모듈의 overflow trimming / cap 동작을 검증."""

    # ── MetarParser: VIS_M_RE TAF 오탐 수정 ──────────────────────────
    def test_metar_vis_not_match_taf_period(self):
        """TAF 유효기간 토큰(0912/1018)이 가시거리로 오탐되면 안 된다."""
        from simulation.metar_parser import MetarParser
        import re
        m = MetarParser.VIS_M_RE.search("0912/1018")
        assert m is None, "TAF 유효기간이 VIS_M_RE에 매칭되면 안 된다"

    def test_metar_vis_still_matches_real_visibility(self):
        """실제 가시거리 4자리 숫자는 여전히 매칭돼야 한다."""
        from simulation.metar_parser import MetarParser
        p = MetarParser()
        obs = p.parse_metar("RKSI 091200Z 27010KT 9999 FEW040 18/10 Q1013")
        assert obs.visibility_m == 9999

    def test_metar_vis_matches_standalone_4digits(self):
        """공백으로 분리된 4자리 숫자는 정상 매칭된다."""
        from simulation.metar_parser import MetarParser
        import re
        m = MetarParser.VIS_M_RE.search("27010KT 6000 FEW040")
        assert m is not None
        assert m.group(1) == "6000"

    # ── FlightFollowingService: track points ring-buffer ─────────────
    def test_flight_following_track_points_capped(self):
        """report_position() 초과 호출 후 points 길이가 cap을 넘지 않는다."""
        from simulation.flight_following import FlightFollowingService
        cap = 10
        svc = FlightFollowingService(max_points_per_track=cap)
        svc.register_flight("FF1", "FP-1", [(0, 0, 50), (1000, 0, 50)])
        for i in range(cap * 3):
            svc.report_position("FF1", (float(i), 0.0, 50.0), (10, 0, 0), 90.0)
        assert len(svc.tracks["FF1"].points) <= cap

    def test_flight_following_invalid_cap_raises(self):
        from simulation.flight_following import FlightFollowingService
        with pytest.raises(ValueError):
            FlightFollowingService(max_points_per_track=0)

    def test_flight_following_recent_points_retained(self):
        """ring-buffer는 가장 최근 포인트를 유지해야 한다."""
        from simulation.flight_following import FlightFollowingService
        cap = 5
        svc = FlightFollowingService(max_points_per_track=cap)
        svc.register_flight("FF1", "FP-1", [(0, 0, 50), (1000, 0, 50)])
        for i in range(cap + 2):
            svc.report_position("FF1", (float(i * 100), 0.0, 50.0), (10, 0, 0), 90.0)
        # 마지막 포인트의 x 좌표가 cap 범위 안에 있어야 함
        last_x = svc.tracks["FF1"].points[-1].position[0]
        assert last_x == float((cap + 1) * 100)

    # ── VertiportOps: wait_queue cap ─────────────────────────────────
    def test_vertiport_wait_queue_capped(self):
        """패드가 없을 때 큐 요청이 max_queue_size를 초과하면 추가 거부된다."""
        from simulation.vertiport_ops import VertiportOps
        cap = 5
        ops = VertiportOps(max_queue_size=cap)
        for i in range(cap + 10):
            ops.reserve_slot(f"CS{i}", desired_time=1000.0)
        assert len(ops.wait_queue) == cap

    def test_vertiport_invalid_queue_size_raises(self):
        from simulation.vertiport_ops import VertiportOps
        with pytest.raises(ValueError):
            VertiportOps(max_queue_size=0)

    def test_vertiport_queue_accepts_when_below_cap(self):
        """cap 미만일 때는 정상적으로 큐에 추가된다."""
        from simulation.vertiport_ops import VertiportOps
        ops = VertiportOps(max_queue_size=3)
        ops.reserve_slot("CS1", desired_time=1000.0)
        ops.reserve_slot("CS2", desired_time=1000.0)
        assert len(ops.wait_queue) == 2

    # ── PostFlightReporter: reports dict FIFO cap ────────────────────
    def test_post_flight_reports_capped(self):
        """build_report() 초과 시 오래된 보고서가 제거된다."""
        from simulation.post_flight_report import PostFlightReporter
        cap = 5
        r = PostFlightReporter(max_reports=cap)
        t0 = time.time()
        pts = [(t0, (0, 0, 50), 100.0), (t0 + 10, (100, 0, 50), 90.0)]
        all_ids = []
        for i in range(cap + 3):
            report = r.build_report(f"AIR{i}", "FP", pts)
            all_ids.append(report.report_id)
        assert len(r.reports) == cap
        # 가장 최근 cap개가 남아있어야 함
        for rid in all_ids[-cap:]:
            assert rid in r.reports

    def test_post_flight_invalid_max_raises(self):
        from simulation.post_flight_report import PostFlightReporter
        with pytest.raises(ValueError):
            PostFlightReporter(max_reports=0)

    def test_post_flight_oldest_evicted(self):
        """FIFO: max 초과 시 가장 먼저 추가된 보고서가 제거된다."""
        from simulation.post_flight_report import PostFlightReporter
        cap = 3
        r = PostFlightReporter(max_reports=cap)
        t0 = time.time()
        pts = [(t0, (0, 0, 50), 100.0), (t0 + 10, (100, 0, 50), 90.0)]
        first = r.build_report("A1", "FP", pts)
        for i in range(cap):
            r.build_report(f"A{i+2}", "FP", pts)
        # 첫 번째 보고서는 사라져 있어야 함
        assert first.report_id not in r.reports


# ── Round-2 Precision Tests ──────────────────────────────────────────
class TestPrecisionRound2:
    """코드 리뷰 2라운드에서 발견된 HIGH/MEDIUM 이슈 검증."""

    # ── metar_parser: 분수 SM 가시거리 ──────────────────────────────
    def test_fractional_sm_visibility(self):
        """1/2SM 은 0.5 SM 으로 파싱되어야 한다."""
        from simulation.metar_parser import MetarParser
        p = MetarParser()
        obs = p.parse_metar("KJFK 091200Z 18020KT 1/2SM OVC003 15/14 Q1005")
        assert obs.visibility_sm == pytest.approx(0.5)

    def test_three_quarter_sm_visibility(self):
        """3/4SM 은 0.75 SM 으로 파싱되어야 한다."""
        from simulation.metar_parser import MetarParser
        p = MetarParser()
        obs = p.parse_metar("RKSI 091200Z 27010KT 3/4SM FEW020 15/10 Q1013")
        assert obs.visibility_sm == pytest.approx(0.75)

    def test_fractional_sm_triggers_ifr_in_is_vfr(self):
        """1/2SM 가시거리(IFR)는 is_vfr()에서 False를 반환해야 한다."""
        from simulation.metar_parser import MetarParser
        p = MetarParser()
        obs = p.parse_metar("KJFK 091200Z 18020KT 1/2SM OVC003 15/14 Q1005")
        assert p.is_vfr(obs) is False

    # ── metar_parser: 조건 코드 오탐 방지 ───────────────────────────
    def test_no_false_positive_conditions_on_station_id(self):
        """스테이션 ID에 조건 코드 문자열이 포함되어도 오탐되면 안 된다."""
        from simulation.metar_parser import MetarParser
        p = MetarParser()
        # RKSHI 에 SH(shower), RKSBR 에 BR(mist) 포함 → 오탐 없어야 함
        obs = p.parse_metar("RKSHI 091200Z 27010KT 9999 FEW040 18/10 Q1013")
        assert obs.conditions == []

    def test_condition_correctly_detected_in_token(self):
        """실제 조건 코드 토큰(RA)은 조건 목록에 포함되어야 한다."""
        from simulation.metar_parser import MetarParser
        p = MetarParser()
        obs = p.parse_metar("RKSI 091200Z 27010KT 5000 RA FEW020 15/14 Q1005")
        assert "rain" in obs.conditions

    def test_is_vfr_uses_metric_visibility_fallback(self):
        """visibility_sm 없이 visibility_m 만 있는 경우도 IFR 판정이 가능해야 한다."""
        from simulation.metar_parser import MetarParser
        p = MetarParser()
        # 0600m = ~0.37 SM → IFR
        obs = p.parse_metar("RKSI 091200Z 27010KT 0600 FEW020 15/14 Q1013")
        # visibility_m 은 파싱되지만 SM 토큰이 없으므로 visibility_sm=None
        assert obs.visibility_m == 600
        assert p.is_vfr(obs) is False

    # ── aim_briefing: chart hazard NO-GO ─────────────────────────────
    def test_chart_hazard_triggers_nogo(self):
        """차트 장애물이 있는 경로는 NO-GO 가 되어야 한다."""
        from simulation.aim_briefing import AimBriefingService, BriefingRequest
        from simulation.notam_manager import NotamManager
        from simulation.tfr_handler import TfrHandler
        from simulation.aero_charts import AeroCharts, ChartFeature, ChartFeatureType
        from simulation.metar_parser import MetarParser
        charts = AeroCharts()
        charts.add_feature(ChartFeature("OBS1", ChartFeatureType.OBSTACLE, (500.0, 0.0), 120.0, "Tower"))
        svc = AimBriefingService(
            notam_manager=NotamManager(),
            tfr_handler=TfrHandler(),
            aero_charts=charts,
            metar_parser=MetarParser(),
        )
        req = BriefingRequest(
            callsign="AIR1",
            departure=(0.0, 0.0),
            destination=(1000.0, 0.0),
            route_waypoints=[(500.0, 0.0)],
            planned_altitude_m=50.0,
            departure_time=time.time(),
        )
        result = svc.generate(req)
        assert result.go_nogo == "NO-GO"
        assert len(result.chart_hazards) >= 1

    def test_clear_route_still_go(self):
        """장애물/NOTAM/TFR 없는 맑은 경로는 GO 여야 한다."""
        from simulation.aim_briefing import AimBriefingService, BriefingRequest
        from simulation.notam_manager import NotamManager
        from simulation.tfr_handler import TfrHandler
        from simulation.aero_charts import AeroCharts
        from simulation.metar_parser import MetarParser
        svc = AimBriefingService(NotamManager(), TfrHandler(), AeroCharts(), MetarParser())
        req = BriefingRequest(
            callsign="AIR2",
            departure=(0.0, 0.0),
            destination=(1000.0, 0.0),
            route_waypoints=[],
            planned_altitude_m=50.0,
            departure_time=time.time(),
        )
        result = svc.generate(req, metar_text="RKSI 091200Z 27010KT 9999 FEW040 18/10 Q1013")
        assert result.go_nogo == "GO"

    # ── notam_manager: purge_terminal ────────────────────────────────
    def test_notam_purge_terminal_removes_expired(self):
        """purge_terminal()은 EXPIRED/CANCELLED NOTAM을 제거한다."""
        from simulation.notam_manager import NotamManager, NotamCategory
        mgr = NotamManager()
        nid = mgr.create_notam(NotamCategory.HAZARD, (0, 0), 100.0, 0.0, 100.0, 1.0, "x")
        mgr.get(nid).valid_until = time.time() - 10.0
        mgr.expire_old()
        assert nid in mgr.notams  # purge 전에는 남아있음
        mgr.purge_terminal()
        assert nid not in mgr.notams  # purge 후에는 제거됨

    def test_notam_expire_records_history(self):
        """expire_old() 가 히스토리 이벤트를 기록해야 한다."""
        from simulation.notam_manager import NotamManager, NotamCategory
        mgr = NotamManager()
        nid = mgr.create_notam(NotamCategory.HAZARD, (0, 0), 100.0, 0.0, 100.0, 1.0, "x")
        mgr.get(nid).valid_until = time.time() - 10.0
        before = len(mgr.history)
        mgr.expire_old()
        assert len(mgr.history) > before

    # ── tfr_handler: purge_expired ───────────────────────────────────
    def test_tfr_purge_expired(self):
        """purge_expired()는 end_time이 지난 TFR을 제거한다."""
        from simulation.tfr_handler import TfrHandler, TfrReason
        h = TfrHandler()
        tid = h.declare_tfr(TfrReason.VIP, (0, 0), 500.0, 0.0, 200.0, 0.001)
        # end_time 을 과거로 설정
        h.tfrs[tid].end_time = time.time() - 10.0
        count = h.purge_expired()
        assert count == 1
        assert tid not in h.tfrs

    # ── cross_border_coord: rejection_reason 저장 + purge_terminal ──
    def test_reject_handoff_stores_reason(self):
        """reject_handoff()가 reason을 BorderCrossing에 저장해야 한다."""
        from simulation.cross_border_coord import CrossBorderCoordinator, AirspaceAuthority
        c = CrossBorderCoordinator()
        c.register_authority(AirspaceAuthority("KR", "Korea"))
        c.register_authority(AirspaceAuthority("JP", "Japan"))
        cid = c.propose_crossing("AIR1", "KR", "JP", (0, 0), 1000.0, 100.0)
        c.reject_handoff(cid, reason="airspace closed")
        assert c.crossings[cid].rejection_reason == "airspace closed"

    def test_cross_border_purge_terminal(self):
        """purge_terminal()은 COMPLETED/REJECTED 크로싱을 제거한다."""
        from simulation.cross_border_coord import CrossBorderCoordinator, AirspaceAuthority
        c = CrossBorderCoordinator()
        c.register_authority(AirspaceAuthority("KR", "Korea", required_docs=[]))
        c.register_authority(AirspaceAuthority("JP", "Japan", required_docs=[]))
        cid = c.propose_crossing("AIR1", "KR", "JP", (0, 0), 1000.0, 100.0)
        c.accept_handoff(cid)
        c.complete_handoff(cid)
        count = c.purge_terminal()
        assert count == 1
        assert cid not in c.crossings

    # ── vertiport_ops: purge_completed ───────────────────────────────
    def test_vertiport_purge_completed(self):
        """purge_completed()는 만료된 예약을 제거한다."""
        from simulation.vertiport_ops import VertiportOps
        ops = VertiportOps()
        ops.add_pad("P1", (0.0, 0.0))
        slot_id = ops.reserve_slot("CS1", desired_time=0.0, duration_s=600.0)
        assert slot_id is not None
        # 현재 시간 기준 이미 만료된 예약 (start=0, duration=600 → end=600 < now)
        count = ops.purge_completed(current_time=time.time())
        assert count >= 1
        assert slot_id not in ops.reservations

    # ── insurance_risk: DRY 검증 ─────────────────────────────────────
    def test_insurance_quote_history_recorded_once(self):
        """quote() 호출 시 히스토리가 정확히 1번만 기록되어야 한다."""
        from simulation.insurance_risk import InsuranceRiskCalculator, RiskFactors
        calc = InsuranceRiskCalculator()
        f = RiskFactors(
            population_density=5000, flight_hours=100, weather_severity=0.3,
            drone_mtow_kg=5.0, operator_experience_hours=200, payload_hazard_level=1,
            proximity_airports_km=15.0,
        )
        calc.quote(f)
        assert calc.stats()["quotes"] == 1

    # ── post_flight_report: zero-dt 속도 ─────────────────────────────
    def test_zero_dt_segments_excluded_from_speed(self):
        """동일 타임스탬프 포인트가 있어도 avg/max_speed 가 과대계산되면 안 된다."""
        from simulation.post_flight_report import PostFlightReporter
        r = PostFlightReporter()
        t0 = time.time()
        # 3번째와 4번째 포인트가 동일 ts (dt=0)
        pts = [
            (t0,      (0.0,   0.0, 50.0), 100.0),
            (t0 + 10, (100.0, 0.0, 50.0),  95.0),
            (t0 + 10, (200.0, 0.0, 50.0),  90.0),  # dt=0 세그먼트
            (t0 + 20, (300.0, 0.0, 50.0),  85.0),
        ]
        report = r.build_report("AIR1", "FP", pts)
        # dt=0 세그먼트(0→100m) 가 speed=100/1 로 잘못 계산되면 max_speed >= 100
        # 올바르게 제외되면 max_speed = 100/10 = 10 m/s
        assert report.metrics.max_speed_mps == pytest.approx(10.0, rel=0.01)

    # ── flight_following: deque ring-buffer ──────────────────────────
    def test_flight_following_deque_cap(self):
        """deque(maxlen=) 으로 교체 후에도 points cap 이 유지된다."""
        from simulation.flight_following import FlightFollowingService
        cap = 5
        svc = FlightFollowingService(max_points_per_track=cap)
        svc.register_flight("FF1", "FP-1", [(0, 0, 50), (1000, 0, 50)])
        for i in range(cap * 4):
            svc.report_position("FF1", (float(i), 0.0, 50.0), (10, 0, 0), 90.0)
        assert len(svc.tracks["FF1"].points) == cap

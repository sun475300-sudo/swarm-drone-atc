"""Phase 681-690: UTM Standards Compliance 모듈 테스트."""

import time

import numpy as np
import pytest


# ── K-UTM Protocol ──────────────────────────────────────────────────────
class TestKUTMProtocol:
    def test_register_drone(self):
        from simulation.kutm_protocol import KUTMProtocol
        kutm = KUTMProtocol()
        reg_id = kutm.register_drone({"drone_id": "d1", "manufacturer": "DJI", "model": "M30"})
        assert reg_id.startswith("REG-")

    def test_submit_flight_plan_approved(self):
        from simulation.kutm_protocol import KUTMProtocol, FlightPlan
        kutm = KUTMProtocol()
        plan = FlightPlan(
            plan_id="FP-001", operator_id="OP1", drone_id="d1",
            departure_time=time.time(), arrival_time=time.time() + 3600,
            waypoints=[(37.5, 127.0, 50.0)], altitude_min=30, altitude_max=100,
        )
        result = kutm.submit_flight_plan(plan)
        assert result["approved"] is True

    def test_submit_flight_plan_rejected_altitude(self):
        from simulation.kutm_protocol import KUTMProtocol, FlightPlan
        kutm = KUTMProtocol()
        plan = FlightPlan(
            plan_id="FP-002", operator_id="OP1", drone_id="d1",
            departure_time=time.time(), arrival_time=time.time() + 3600,
            waypoints=[(37.5, 127.0, 150.0)], altitude_min=30, altitude_max=200,
        )
        result = kutm.submit_flight_plan(plan)
        assert result["approved"] is False

    def test_cancel_flight_plan(self):
        from simulation.kutm_protocol import KUTMProtocol, FlightPlan
        kutm = KUTMProtocol()
        plan = FlightPlan(
            plan_id="FP-003", operator_id="OP1", drone_id="d1",
            departure_time=time.time(), arrival_time=time.time() + 3600,
            waypoints=[], altitude_min=0, altitude_max=100,
        )
        kutm.submit_flight_plan(plan)
        assert kutm.cancel_flight_plan("FP-003")
        assert kutm.get_flight_plan_status("FP-003") == "cancelled"

    def test_report_telemetry(self):
        from simulation.kutm_protocol import KUTMProtocol
        kutm = KUTMProtocol()
        assert kutm.report_telemetry("d1", (37.5, 127.0, 50.0), (1, 0, 0), 85.0)
        assert len(kutm.telemetry_log) == 1

    def test_get_notams(self):
        from simulation.kutm_protocol import KUTMProtocol, NOTAM
        kutm = KUTMProtocol()
        kutm.add_notam(NOTAM(
            notam_id="N001", area_center=(37.5, 127.0), radius_m=1000,
            altitude_min=0, altitude_max=120, description="Test NOTAM",
            valid_from=time.time() - 100, valid_until=time.time() + 3600,
        ))
        notams = kutm.get_notams((37.5, 127.0))
        assert len(notams) == 1

    def test_validate_operator(self):
        from simulation.kutm_protocol import KUTMProtocol
        kutm = KUTMProtocol()
        result = kutm.validate_operator_credentials("OP1")
        assert isinstance(result, bool)

    def test_get_stats(self):
        from simulation.kutm_protocol import KUTMProtocol
        kutm = KUTMProtocol()
        stats = kutm.get_stats()
        assert "total_plans" in stats


# ── ADS-B Receiver ──────────────────────────────────────────────────────
class TestADSBReceiver:
    def test_start_stop_listening(self):
        from simulation.adsb_receiver import ADSBReceiver
        rx = ADSBReceiver()
        assert rx.start_listening()
        assert rx.listening
        rx.stop_listening()
        assert not rx.listening

    def test_inject_traffic(self):
        from simulation.adsb_receiver import ADSBReceiver
        rx = ADSBReceiver()
        msgs = rx.generate_simulated_traffic(count=3)
        injected = rx.inject_traffic(msgs)
        assert injected == 3
        assert len(rx.get_aircraft_list()) == 3

    def test_get_aircraft_by_icao(self):
        from simulation.adsb_receiver import ADSBReceiver, ADSBMessage
        rx = ADSBReceiver()
        msg = ADSBMessage(
            icao_address="ABC123", callsign="KAL001",
            latitude=37.5, longitude=127.0, altitude_ft=10000,
            ground_speed_kt=250, track_deg=90, vertical_rate_fpm=0,
        )
        rx.inject_traffic([msg])
        found = rx.get_aircraft_by_icao("ABC123")
        assert found is not None
        assert found.callsign == "KAL001"

    def test_detect_conflicts(self):
        from simulation.adsb_receiver import ADSBReceiver, ADSBMessage
        rx = ADSBReceiver()
        msg = ADSBMessage(
            icao_address="AC001", callsign="KAL100",
            latitude=37.5, longitude=127.0, altitude_ft=500,
            ground_speed_kt=200, track_deg=0, vertical_rate_fpm=0,
        )
        rx.inject_traffic([msg])
        conflicts = rx.detect_conflicts([(37.5, 127.0, 500)])
        assert len(conflicts) > 0
        assert conflicts[0]["severity"] == "HIGH"

    def test_no_conflict_when_separated(self):
        from simulation.adsb_receiver import ADSBReceiver, ADSBMessage
        rx = ADSBReceiver()
        msg = ADSBMessage(
            icao_address="AC002", callsign="AAR200",
            latitude=38.0, longitude=128.0, altitude_ft=30000,
            ground_speed_kt=450, track_deg=180, vertical_rate_fpm=-500,
        )
        rx.inject_traffic([msg])
        conflicts = rx.detect_conflicts([(37.5, 127.0, 100)])
        assert len(conflicts) == 0

    def test_traffic_density(self):
        from simulation.adsb_receiver import ADSBReceiver
        rx = ADSBReceiver()
        msgs = rx.generate_simulated_traffic(count=10, center=(37.5, 127.0))
        rx.inject_traffic(msgs)
        density = rx.get_traffic_density((37.0, 126.5, 38.0, 127.5))
        assert density > 0

    def test_receiver_stats(self):
        from simulation.adsb_receiver import ADSBReceiver
        rx = ADSBReceiver()
        rx.start_listening()
        stats = rx.get_receiver_stats()
        assert stats["listening"] is True


# ── Remote ID ───────────────────────────────────────────────────────────
class TestRemoteIDTransmitter:
    def test_broadcast(self):
        from simulation.remote_id import RemoteIDTransmitter, RemoteIDMessage
        tx = RemoteIDTransmitter()
        msg = RemoteIDMessage(uas_id="UAS-001", latitude=37.5, longitude=127.0)
        assert tx.broadcast(msg)
        assert tx.broadcast_count == 1

    def test_broadcast_no_id(self):
        from simulation.remote_id import RemoteIDTransmitter, RemoteIDMessage
        tx = RemoteIDTransmitter()
        msg = RemoteIDMessage()  # empty uas_id
        assert not tx.broadcast(msg)

    def test_network_publish(self):
        from simulation.remote_id import RemoteIDTransmitter, RemoteIDMessage
        tx = RemoteIDTransmitter()
        msg = RemoteIDMessage(uas_id="UAS-002")
        assert tx.network_publish(msg)
        assert tx.network_publish_count == 1

    def test_set_broadcast_interval(self):
        from simulation.remote_id import RemoteIDTransmitter
        tx = RemoteIDTransmitter()
        tx.set_broadcast_interval(0.5)
        assert tx.broadcast_interval_s == 0.5
        tx.set_broadcast_interval(0.01)
        assert tx.broadcast_interval_s == 0.1  # clamped

    def test_compliance_status(self):
        from simulation.remote_id import RemoteIDTransmitter, RemoteIDMessage
        tx = RemoteIDTransmitter()
        tx.broadcast(RemoteIDMessage(uas_id="UAS-003"))
        status = tx.get_compliance_status()
        assert status["is_broadcasting"] is True


class TestRemoteIDReceiver:
    def test_scan_empty(self):
        from simulation.remote_id import RemoteIDReceiver
        rx = RemoteIDReceiver()
        assert rx.scan() == []

    def test_receive_and_scan(self):
        from simulation.remote_id import RemoteIDReceiver, RemoteIDMessage
        rx = RemoteIDReceiver()
        rx.receive(RemoteIDMessage(uas_id="UAS-001", latitude=37.5, longitude=127.0))
        results = rx.scan()
        assert len(results) == 1

    def test_get_nearby_uas(self):
        from simulation.remote_id import RemoteIDReceiver, RemoteIDMessage
        rx = RemoteIDReceiver()
        rx.receive(RemoteIDMessage(uas_id="UAS-N", latitude=37.5, longitude=127.0))
        rx.receive(RemoteIDMessage(uas_id="UAS-F", latitude=38.5, longitude=128.0))
        nearby = rx.get_nearby_uas(37.5, 127.0, radius_m=5000)
        assert len(nearby) == 1

    def test_verify_valid_message(self):
        from simulation.remote_id import RemoteIDReceiver, RemoteIDMessage, OperationalStatus
        rx = RemoteIDReceiver()
        msg = RemoteIDMessage(
            uas_id="UAS-V", latitude=37.5, longitude=127.0,
            operational_status=OperationalStatus.AIRBORNE,
        )
        result = rx.verify_message(msg)
        assert result["valid"] is True

    def test_verify_invalid_message(self):
        from simulation.remote_id import RemoteIDReceiver, RemoteIDMessage
        rx = RemoteIDReceiver()
        msg = RemoteIDMessage()  # missing fields
        result = rx.verify_message(msg)
        assert result["valid"] is False


# ── FAA LAANC ───────────────────────────────────────────────────────────
class TestFAALAANC:
    def test_request_authorization_approved(self):
        from simulation.faa_laanc import FAA_LAANC, LAANCRequest
        laanc = FAA_LAANC()
        req = LAANCRequest(
            operator_id="OP1", drone_registration="REG-001",
            operation_area=(36.0, 126.0, 36.5, 126.5),
            max_altitude_ft=200, start_time=time.time(),
            end_time=time.time() + 3600,
        )
        auth = laanc.request_authorization(req)
        assert auth.status.value == "approved"

    def test_request_authorization_rejected_altitude(self):
        from simulation.faa_laanc import FAA_LAANC, LAANCRequest
        laanc = FAA_LAANC()
        req = LAANCRequest(
            operator_id="OP1", drone_registration="REG-001",
            operation_area=(36.0, 126.0, 36.5, 126.5),
            max_altitude_ft=500, start_time=time.time(),
            end_time=time.time() + 3600,
        )
        auth = laanc.request_authorization(req)
        assert auth.status.value == "rejected"

    def test_cancel_authorization(self):
        from simulation.faa_laanc import FAA_LAANC, LAANCRequest
        laanc = FAA_LAANC()
        req = LAANCRequest(
            operator_id="OP1", drone_registration="REG-001",
            operation_area=(36.0, 126.0, 36.5, 126.5),
            max_altitude_ft=200, start_time=time.time(),
            end_time=time.time() + 3600,
        )
        auth = laanc.request_authorization(req)
        assert laanc.cancel_authorization(auth.request_id)
        assert laanc.check_authorization_status(auth.request_id) == "cancelled"

    def test_check_airspace_class(self):
        from simulation.faa_laanc import FAA_LAANC
        laanc = FAA_LAANC()
        # Far from airports -> G
        assert laanc.check_airspace_class(36.0, 126.0) == "G"

    def test_is_near_airport(self):
        from simulation.faa_laanc import FAA_LAANC
        laanc = FAA_LAANC()
        # Near Incheon
        assert laanc.is_near_airport(37.5665, 126.9780)
        # Far away
        assert not laanc.is_near_airport(36.0, 126.0)

    def test_validate_part107(self):
        from simulation.faa_laanc import FAA_LAANC
        laanc = FAA_LAANC()
        result = laanc.validate_part107_compliance({"altitude_ft": 300, "speed_kt": 80})
        assert result["compliant"] is True

    def test_validate_part107_violations(self):
        from simulation.faa_laanc import FAA_LAANC
        laanc = FAA_LAANC()
        result = laanc.validate_part107_compliance({"altitude_ft": 500, "speed_kt": 120})
        assert not result["compliant"]
        assert len(result["violations"]) >= 2

    def test_get_facility_map(self):
        from simulation.faa_laanc import FAA_LAANC
        laanc = FAA_LAANC()
        fmap = laanc.get_facility_map((36.0, 126.0, 36.5, 126.5))
        assert "airspace_class" in fmap


# ── ICAO Doc 10019 ──────────────────────────────────────────────────────
class TestICAODoc10019:
    def test_validate_operator_valid(self):
        from simulation.icao_doc10019 import ICAODoc10019, RPASOperator
        icao = ICAODoc10019()
        op = RPASOperator(
            operator_id="OP1", name="Test Operator",
            certificate_number="CERT-001", certificate_type="remote_pilot",
            valid_until=time.time() + 86400,
        )
        result = icao.validate_operator(op)
        assert result.compliant

    def test_validate_operator_missing_cert(self):
        from simulation.icao_doc10019 import ICAODoc10019, RPASOperator
        icao = ICAODoc10019()
        op = RPASOperator(
            operator_id="OP2", name="", certificate_number="",
            certificate_type="remote_pilot", valid_until=time.time() + 86400,
        )
        result = icao.validate_operator(op)
        assert not result.compliant

    def test_validate_aircraft(self):
        from simulation.icao_doc10019 import ICAODoc10019, RPASAircraft
        icao = ICAODoc10019()
        ac = RPASAircraft(
            registration="KR-001", type_certificate="TC-001",
            serial_number="SN-001", mtow_kg=2.5,
            max_altitude_m=100, max_speed_ms=15, endurance_min=30,
        )
        result = icao.validate_aircraft(ac)
        assert result.compliant

    def test_classify_operation_open(self):
        from simulation.icao_doc10019 import ICAODoc10019
        icao = ICAODoc10019()
        cat = icao.classify_operation(altitude_m=50, vlos=True, over_people=False, mtow_kg=2.0)
        assert cat == "Open"

    def test_classify_operation_specific(self):
        from simulation.icao_doc10019 import ICAODoc10019
        icao = ICAODoc10019()
        cat = icao.classify_operation(altitude_m=150, vlos=True, over_people=False, mtow_kg=2.0)
        assert cat == "Specific"

    def test_classify_operation_certified(self):
        from simulation.icao_doc10019 import ICAODoc10019
        icao = ICAODoc10019()
        cat = icao.classify_operation(altitude_m=50, vlos=True, over_people=False, mtow_kg=200)
        assert cat == "Certified"

    def test_c2_link_open(self):
        from simulation.icao_doc10019 import ICAODoc10019
        icao = ICAODoc10019()
        result = icao.check_c2_link_requirements("direct_rf", "Open")
        assert result["compliant"] is True

    def test_c2_link_certified_satellite(self):
        from simulation.icao_doc10019 import ICAODoc10019
        icao = ICAODoc10019()
        result = icao.check_c2_link_requirements("satellite", "Certified")
        assert result["compliant"] is True

    def test_c2_link_certified_cellular_rejected(self):
        from simulation.icao_doc10019 import ICAODoc10019
        icao = ICAODoc10019()
        result = icao.check_c2_link_requirements("cellular", "Certified")
        assert result["compliant"] is False

    def test_required_certifications(self):
        from simulation.icao_doc10019 import ICAODoc10019
        icao = ICAODoc10019()
        certs = icao.get_required_certifications("Certified")
        assert len(certs) >= 4

    def test_detect_and_avoid(self):
        from simulation.icao_doc10019 import ICAODoc10019, RPASAircraft
        icao = ICAODoc10019()
        ac = RPASAircraft(
            registration="KR-002", type_certificate="TC-002",
            serial_number="SN-002", mtow_kg=30,
            max_altitude_m=200, max_speed_ms=20, endurance_min=45,
        )
        result = icao.check_detect_and_avoid(ac, [{"distance_m": 3000}])
        assert result["daa_required"] is True
        assert result["nearby_traffic_count"] == 1

    def test_compliance_report(self):
        from simulation.icao_doc10019 import ICAODoc10019, RPASOperator, RPASAircraft
        icao = ICAODoc10019()
        op = RPASOperator("OP1", "Test", "CERT-1", "remote_pilot", time.time() + 86400)
        ac = RPASAircraft("KR-001", "TC-001", "SN-001", 2.5, 100, 15, 30)
        report = icao.generate_compliance_report(op, ac, {"altitude_m": 50, "vlos": True})
        assert report["overall_compliant"] is True
        assert report["operation_category"] == "Open"

    def test_annex_requirements(self):
        from simulation.icao_doc10019 import ICAODoc10019
        icao = ICAODoc10019()
        reqs = icao.get_annex_requirements(2)
        assert len(reqs) >= 1
        assert "Rules of the Air" in reqs[0]

    def test_annex_unknown(self):
        from simulation.icao_doc10019 import ICAODoc10019
        icao = ICAODoc10019()
        reqs = icao.get_annex_requirements(99)
        assert len(reqs) == 1

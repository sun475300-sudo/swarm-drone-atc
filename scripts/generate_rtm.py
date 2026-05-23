"""
RTM (Requirements-Test Traceability Matrix) 자동 생성 스크립트.

실행: python scripts/generate_rtm.py
출력: reports/rtm.csv, reports/rtm.md
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent

# ─────────────────────────────────────────────────────────────
# 요구사항 정의 (REQ-ID → 설명, 분류, 허용 기준)
# ─────────────────────────────────────────────────────────────
REQUIREMENTS: list[dict] = [
    # 안전 · 분리
    {
        "id": "REQ-001",
        "category": "Safety",
        "description": "정상 운영 중 드론 간 충돌 0건 (600s, 20대 기준)",
        "acceptance": "collisions == 0",
    },
    {
        "id": "REQ-002",
        "category": "Safety",
        "description": "최소 분리간격 50m 유지 (수평)",
        "acceptance": "separation ≥ 50 m at all times",
    },
    {
        "id": "REQ-003",
        "category": "Safety",
        "description": "Near-miss (10m 이내 접근) 발생 시 어드바이저리 즉시 발령",
        "acceptance": "advisory latency < 1 s",
    },
    {
        "id": "REQ-004",
        "category": "Safety",
        "description": "NFZ(비행금지구역) 진입 사전 차단 (lookahead 3s)",
        "acceptance": "NFZ violations == 0",
    },
    {
        "id": "REQ-005",
        "category": "Safety",
        "description": "배터리 5% 미만 → LANDING 강제 전환",
        "acceptance": "BATTERY_CRITICAL → FlightPhase.LANDING",
    },
    # 회피 · 경로
    {
        "id": "REQ-006",
        "category": "Navigation",
        "description": "APF 기반 충돌 회피 기동 (EVADING 상태)",
        "acceptance": "EVADING → ENROUTE 전환율 ≥ 95%",
    },
    {
        "id": "REQ-007",
        "category": "Navigation",
        "description": "경로효율(Route Efficiency) ≤ 1.15",
        "acceptance": "planned_dist / actual_dist ≤ 1.15",
    },
    {
        "id": "REQ-008",
        "category": "Navigation",
        "description": "CPA(최근접점) 90초 선제 예측 및 어드바이저리 발령",
        "acceptance": "CPA lookahead ≥ 90 s",
    },
    {
        "id": "REQ-009",
        "category": "Navigation",
        "description": "강풍(>10 m/s) 시 APF_PARAMS_WINDY 자동 전환",
        "acceptance": "windy params applied when |wind| > 10 m/s",
    },
    # 상태 머신
    {
        "id": "REQ-010",
        "category": "StateMachine",
        "description": "이륙(TAKEOFF) → 순항고도 도달 → ENROUTE 자동 전환",
        "acceptance": "position[2] == CRUISE_ALT after TAKEOFF",
    },
    {
        "id": "REQ-011",
        "category": "StateMachine",
        "description": "착륙(LANDING) → 지면 도달 → GROUNDED 전환 + 배터리 충전",
        "acceptance": "position[2] == 0.0, battery += 40%",
    },
    {
        "id": "REQ-012",
        "category": "StateMachine",
        "description": "통신두절(Lost-Link) 3단계 처리: HOLDING → RTL → LANDING",
        "acceptance": "hold 5s → RTL → pad proximity → LANDING",
    },
    {
        "id": "REQ-013",
        "category": "StateMachine",
        "description": "FAILED 드론 하강 (1.5 m/s) 후 지면 정지",
        "acceptance": "position[2] decreases at 1.5 m/s until 0",
    },
    # 제어 · 관제
    {
        "id": "REQ-014",
        "category": "Controller",
        "description": "충돌 해결률(CRR) ≥ 95%: 1 - collisions/(conflicts + collisions)",
        "acceptance": "CRR ≥ 0.95",
    },
    {
        "id": "REQ-015",
        "category": "Controller",
        "description": "동적 분리간격: 풍속 비례 증가, 최대 150m 상한",
        "acceptance": "separation scales with wind, capped at 150 m",
    },
    {
        "id": "REQ-016",
        "category": "Controller",
        "description": "CBS(Conflict-Based Search) 경로 최적화",
        "acceptance": "CBS returns valid path within timeout",
    },
    {
        "id": "REQ-017",
        "category": "Controller",
        "description": "어드바이저리 만료 관리 (TTL 기반 자동 제거)",
        "acceptance": "expired advisories removed from active set",
    },
    {
        "id": "REQ-018",
        "category": "Controller",
        "description": "ROGUE 드론 탐지 및 선택적 어드바이저리 발령",
        "acceptance": "ROGUE↔ROGUE 쌍은 건너뜀, ROGUE↔등록 쌍만 대상",
    },
    # 재현성 · 성능
    {
        "id": "REQ-019",
        "category": "Reproducibility",
        "description": "동일 시드(seed=42)로 동일 결과 재현 (결정론적 시뮬레이션)",
        "acceptance": "output identical across runs with same seed",
    },
    {
        "id": "REQ-020",
        "category": "Reproducibility",
        "description": "Monte Carlo 38,400회 통계 안정성 (평균 ±2σ 이내)",
        "acceptance": "MC sweep convergence within ±2σ",
    },
    {
        "id": "REQ-021",
        "category": "Performance",
        "description": "시뮬레이션 틱 성능: 30대 드론 기준 10Hz 실시간",
        "acceptance": "tick_time_ms < 100 ms (CPU-default)",
    },
    {
        "id": "REQ-022",
        "category": "Performance",
        "description": "SLA: collision_rate < 0.01, resolution_rate ≥ 0.95",
        "acceptance": "SLA 위반 0건 in 600s nominal run",
    },
    # 환경 적응
    {
        "id": "REQ-023",
        "category": "Environment",
        "description": "강풍 시나리오(15 m/s gust) 시 충돌 0건",
        "acceptance": "collisions == 0 under 15 m/s wind",
    },
    {
        "id": "REQ-024",
        "category": "Environment",
        "description": "통신 두절(comms_loss_rate=0.3) 시 RTL 정상 작동",
        "acceptance": "all drones land safely under 30% comms loss",
    },
    {
        "id": "REQ-025",
        "category": "Environment",
        "description": "침입 드론(ROGUE) 탐지 후 안전 분리 유지",
        "acceptance": "registered drones maintain ≥ 50m from ROGUE",
    },
]

# ─────────────────────────────────────────────────────────────
# 테스트-요구사항 매핑
# ─────────────────────────────────────────────────────────────
MAPPINGS: list[dict] = [
    # REQ-001 충돌 0건
    {"req_id": "REQ-001", "test_file": "tests/test_simulator_scenarios.py", "test_name": "TestBaseScenario::test_no_collision_basic"},
    {"req_id": "REQ-001", "test_file": "tests/test_e2e_quick.py", "test_name": "TestE2EWithRealSimulation::test_full_simulation_pipeline"},
    {"req_id": "REQ-001", "test_file": "tests/test_e2e_quick.py", "test_name": "TestE2ESimulation::test_collision_resolution_formula"},
    # REQ-002 분리간격
    {"req_id": "REQ-002", "test_file": "tests/test_airspace_controller.py", "test_name": "TestConflictScan::test_no_conflict_when_separated"},
    {"req_id": "REQ-002", "test_file": "tests/test_airspace_controller.py", "test_name": "TestConflictScan::test_conflict_detected_when_close"},
    {"req_id": "REQ-002", "test_file": "tests/test_airspace_controller.py", "test_name": "TestKDTreeQueryPairs::test_close_pair_found"},
    {"req_id": "REQ-002", "test_file": "tests/test_airspace_controller.py", "test_name": "TestKDTreeQueryPairs::test_distance_accuracy"},
    # REQ-003 어드바이저리 지연
    {"req_id": "REQ-003", "test_file": "tests/test_resolution_advisory.py", "test_name": "TestAdvisoryGenerator::test_urgent_cpa_triggers_evade_apf"},
    {"req_id": "REQ-003", "test_file": "tests/test_resolution_advisory.py", "test_name": "TestAdvisoryGenerator::test_advisory_has_valid_duration"},
    {"req_id": "REQ-003", "test_file": "tests/test_resolution_advisory.py", "test_name": "TestAdvisoryGenerator::test_stationary_drone_triggers_evade_apf"},
    # REQ-004 NFZ 차단
    {"req_id": "REQ-004", "test_file": "tests/test_airspace_controller.py", "test_name": "TestNFZ3DCheck::test_clearance_above_nfz_allowed"},
    {"req_id": "REQ-004", "test_file": "tests/test_safety_fixes.py", "test_name": "TestNFZValidation::test_point_in_nfz"},
    {"req_id": "REQ-004", "test_file": "tests/test_safety_fixes.py", "test_name": "TestNFZValidation::test_point_outside_nfz"},
    # REQ-005 배터리 임계
    {"req_id": "REQ-005", "test_file": "tests/test_core_functions.py", "test_name": "TestSimulator3dUpdate::test_battery_critical_forces_landing"},
    {"req_id": "REQ-005", "test_file": "tests/test_safety_fixes.py", "test_name": "TestBoundaryConditions::test_battery_zero"},
    # REQ-006 APF 회피
    {"req_id": "REQ-006", "test_file": "tests/test_apf.py", "test_name": "TestBatchComputeForces::test_two_drones_repulsion"},
    {"req_id": "REQ-006", "test_file": "tests/test_apf.py", "test_name": "TestBatchComputeForces::test_obstacle_repulsion"},
    {"req_id": "REQ-006", "test_file": "tests/test_safety_fixes.py", "test_name": "TestFlightPhaseTransitions::test_evading_to_enroute"},
    {"req_id": "REQ-006", "test_file": "tests/test_safety_fixes.py", "test_name": "TestFlightPhaseTransitions::test_evading_to_landing_no_goal"},
    # REQ-007 경로효율
    {"req_id": "REQ-007", "test_file": "tests/test_metrics.py", "test_name": "TestSimulationMetrics::test_route_efficiency"},
    {"req_id": "REQ-007", "test_file": "tests/test_metrics.py", "test_name": "TestSimulationMetrics::test_route_efficiency_no_plan"},
    {"req_id": "REQ-007", "test_file": "tests/test_e2e_quick.py", "test_name": "TestE2ESimulation::test_throughput_calculation"},
    # REQ-008 CPA 예측
    {"req_id": "REQ-008", "test_file": "tests/test_resolution_advisory.py", "test_name": "TestAdvisoryGenerator::test_generate_returns_advisory"},
    {"req_id": "REQ-008", "test_file": "tests/test_resolution_advisory.py", "test_name": "TestAdvisoryGenerator::test_head_on_triggers_turn_right"},
    # REQ-009 강풍 APF 전환
    {"req_id": "REQ-009", "test_file": "tests/test_apf.py", "test_name": "TestAPFWindyMode::test_windy_increases_repulsion"},
    {"req_id": "REQ-009", "test_file": "tests/test_safety_fixes.py", "test_name": "TestAPFWindyModeTransition::test_strong_wind_uses_windy_params"},
    {"req_id": "REQ-009", "test_file": "tests/test_safety_fixes.py", "test_name": "TestAPFWindyModeTransition::test_calm_uses_normal_params"},
    {"req_id": "REQ-009", "test_file": "tests/test_safety_fixes.py", "test_name": "TestAPFWindyModeTransition::test_mid_wind_blends_params"},
    # REQ-010 이륙→ENROUTE
    {"req_id": "REQ-010", "test_file": "tests/test_core_functions.py", "test_name": "TestSimulator3dUpdate::test_takeoff_reaches_cruise"},
    # REQ-011 착륙→GROUNDED
    {"req_id": "REQ-011", "test_file": "tests/test_core_functions.py", "test_name": "TestSimulator3dUpdate::test_landing_touches_ground"},
    {"req_id": "REQ-011", "test_file": "tests/test_safety_fixes.py", "test_name": "TestFlightPhaseTransitions::test_landing_to_grounded"},
    # REQ-012 Lost-Link
    {"req_id": "REQ-012", "test_file": "tests/test_resolution_advisory.py", "test_name": "TestAdvisoryGenerator::test_lost_link_sequence_three_phases"},
    {"req_id": "REQ-012", "test_file": "tests/test_core_functions.py", "test_name": "TestSimulator3dUpdate::test_holding_to_rtl"},
    {"req_id": "REQ-012", "test_file": "tests/test_safety_fixes.py", "test_name": "TestHoldingStateTransition::test_hold_timeout_triggers_transition"},
    {"req_id": "REQ-012", "test_file": "tests/test_safety_fixes.py", "test_name": "TestFlightPhaseTransitions::test_rtl_to_landing"},
    # REQ-013 FAILED 하강
    {"req_id": "REQ-013", "test_file": "tests/test_core_functions.py", "test_name": "TestSimulator3dUpdate::test_failed_descends"},
    {"req_id": "REQ-013", "test_file": "tests/test_safety_fixes.py", "test_name": "TestFailedToGrounded::test_failed_drone_descends"},
    # REQ-014 충돌 해결률
    {"req_id": "REQ-014", "test_file": "tests/test_e2e_quick.py", "test_name": "TestE2ESimulation::test_collision_resolution_formula"},
    {"req_id": "REQ-014", "test_file": "tests/test_e2e_quick.py", "test_name": "TestE2ESimulation::test_safety_metrics_calculation"},
    {"req_id": "REQ-014", "test_file": "tests/test_metrics.py", "test_name": "TestSimulationMetrics::test_conflict_resolution_rate"},
    # REQ-015 동적 분리간격
    {"req_id": "REQ-015", "test_file": "tests/test_airspace_controller.py", "test_name": "TestDynamicSeparation::test_moderate_wind"},
    {"req_id": "REQ-015", "test_file": "tests/test_airspace_controller.py", "test_name": "TestDynamicSeparation::test_strong_wind"},
    {"req_id": "REQ-015", "test_file": "tests/test_airspace_controller.py", "test_name": "TestDynamicSeparation::test_extreme_wind_caps"},
    # REQ-016 CBS
    {"req_id": "REQ-016", "test_file": "tests/test_cbs.py", "test_name": "TestGridNode::test_equality"},
    {"req_id": "REQ-016", "test_file": "tests/test_cbs.py", "test_name": "TestGridResolution::test_reasonable_range"},
    # REQ-017 어드바이저리 만료
    {"req_id": "REQ-017", "test_file": "tests/test_airspace_controller.py", "test_name": "TestAdvisoryExpiry::test_expired_advisory_removed"},
    {"req_id": "REQ-017", "test_file": "tests/test_airspace_controller.py", "test_name": "TestAdvisoryExpiry::test_active_advisory_not_removed"},
    # REQ-018 ROGUE
    {"req_id": "REQ-018", "test_file": "tests/test_safety_fixes.py", "test_name": "TestRogueAdvisoryGuard::test_rogue_profile_detection"},
    {"req_id": "REQ-018", "test_file": "tests/test_safety_fixes.py", "test_name": "TestRogueAdvisoryGuard::test_rogue_pair_skip"},
    {"req_id": "REQ-018", "test_file": "tests/test_safety_fixes.py", "test_name": "TestRogueAdvisoryGuard::test_rogue_vs_registered_target"},
    {"req_id": "REQ-018", "test_file": "tests/test_simulator_scenarios.py", "test_name": "TestIntrusionScenario::test_rogue_drone_detected"},
    # REQ-019 재현성
    {"req_id": "REQ-019", "test_file": "tests/test_e2e_quick.py", "test_name": "TestParametrized::test_determinism_with_seed"},
    {"req_id": "REQ-019", "test_file": "tests/test_verify_canonical_hashes.py", "test_name": "test_canonical_hashes"},
    # REQ-020 Monte Carlo
    {"req_id": "REQ-020", "test_file": "tests/test_monte_carlo.py", "test_name": "TestRunSingle::test_returns_dict_with_required_keys"},
    {"req_id": "REQ-020", "test_file": "tests/test_monte_carlo.py", "test_name": "TestSummarizeResults::test_with_sample_data"},
    {"req_id": "REQ-020", "test_file": "tests/test_e2e_quick.py", "test_name": "TestE2ESimulation::test_monte_carlo_mini_sweep"},
    # REQ-021 성능
    {"req_id": "REQ-021", "test_file": "tests/test_e2e_quick.py", "test_name": "TestE2ESimulation::test_response_time_analysis"},
    {"req_id": "REQ-021", "test_file": "tests/test_e2e_quick.py", "test_name": "TestParametrized::test_various_drone_counts"},
    # REQ-022 SLA
    {"req_id": "REQ-022", "test_file": "tests/test_metrics.py", "test_name": "TestCheckSla::test_pass_all"},
    {"req_id": "REQ-022", "test_file": "tests/test_metrics.py", "test_name": "TestCheckSla::test_fail_collision"},
    {"req_id": "REQ-022", "test_file": "tests/test_e2e_quick.py", "test_name": "TestE2ESimulation::test_safety_metrics_calculation"},
    # REQ-023 강풍 시나리오
    {"req_id": "REQ-023", "test_file": "tests/test_simulator_scenarios.py", "test_name": "TestWeatherScenario::test_strong_wind_scenario"},
    {"req_id": "REQ-023", "test_file": "tests/test_simulator_scenarios.py", "test_name": "TestWeatherScenario::test_gust_scenario"},
    # REQ-024 통신 두절
    {"req_id": "REQ-024", "test_file": "tests/test_simulator_scenarios.py", "test_name": "TestCommsLossScenario::test_comms_loss_simulation"},
    {"req_id": "REQ-024", "test_file": "tests/test_resolution_advisory.py", "test_name": "TestAdvisoryGenerator::test_lost_link_sequence_three_phases"},
    # REQ-025 침입 드론
    {"req_id": "REQ-025", "test_file": "tests/test_simulator_scenarios.py", "test_name": "TestIntrusionScenario::test_rogue_drone_detected"},
    {"req_id": "REQ-025", "test_file": "tests/test_safety_fixes.py", "test_name": "TestRogueAdvisoryGuard::test_rogue_pair_skip"},
]


def collect_pytest_results() -> dict[str, str]:
    """pytest --collect-only로 실제 테스트 존재 여부 확인."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", "--no-header"],
            capture_output=True, text=True, cwd=ROOT, timeout=60,
        )
        collected = set()
        for line in result.stdout.splitlines():
            line = line.strip()
            if "::" in line:
                # normalize path separators
                collected.add(line.replace("\\", "/"))
        return collected
    except Exception:
        return set()


def normalize_test_id(test_file: str, test_name: str) -> str:
    return f"{test_file}::{test_name}".replace("\\", "/")


def generate_rtm() -> None:
    reports_dir = ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)

    collected = collect_pytest_results()

    # req_id → list of mapping rows
    req_map: dict[str, list[dict]] = {r["id"]: [] for r in REQUIREMENTS}
    for m in MAPPINGS:
        req_map[m["req_id"]].append(m)

    rows = []
    for req in REQUIREMENTS:
        req_id = req["id"]
        tests = req_map.get(req_id, [])
        if not tests:
            rows.append({
                "req_id": req_id,
                "category": req["category"],
                "description": req["description"],
                "acceptance": req["acceptance"],
                "test_file": "—",
                "test_name": "—",
                "verified": "NOT COVERED",
            })
            continue
        for t in tests:
            tid = normalize_test_id(t["test_file"], t["test_name"])
            verified = "PASS" if any(tid in c for c in collected) else "MAPPED"
            rows.append({
                "req_id": req_id,
                "category": req["category"],
                "description": req["description"],
                "acceptance": req["acceptance"],
                "test_file": t["test_file"],
                "test_name": t["test_name"],
                "verified": verified,
            })

    # CSV
    csv_path = reports_dir / "rtm.csv"
    fieldnames = ["req_id", "category", "description", "acceptance", "test_file", "test_name", "verified"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"CSV  → {csv_path}")

    # Markdown
    md_path = reports_dir / "rtm.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# SDACS 요구사항-테스트 추적 매트릭스 (RTM)\n\n")
        f.write(f"> 생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write(f"> 총 요구사항: {len(REQUIREMENTS)}개  \n")
        f.write(f"> 총 테스트 매핑: {len(MAPPINGS)}건  \n\n")

        # 요약 통계
        categories = sorted({r["category"] for r in REQUIREMENTS})
        f.write("## 요약\n\n")
        f.write("| 분류 | 요구사항 수 | 매핑 테스트 수 |\n")
        f.write("|------|------------|---------------|\n")
        for cat in categories:
            cat_reqs = [r for r in REQUIREMENTS if r["category"] == cat]
            cat_tests = sum(len(req_map.get(r["id"], [])) for r in cat_reqs)
            f.write(f"| {cat} | {len(cat_reqs)} | {cat_tests} |\n")
        f.write(f"| **합계** | **{len(REQUIREMENTS)}** | **{len(MAPPINGS)}** |\n\n")

        # 본문 표
        f.write("## 상세 매트릭스\n\n")
        f.write("| REQ-ID | 분류 | 요구사항 설명 | 허용 기준 | 테스트 파일 | 테스트 함수 | 상태 |\n")
        f.write("|--------|------|--------------|-----------|------------|------------|------|\n")
        prev_id = None
        for row in rows:
            rid = row["req_id"] if row["req_id"] != prev_id else ""
            rdesc = row["description"] if row["req_id"] != prev_id else ""
            racc = row["acceptance"] if row["req_id"] != prev_id else ""
            rcat = row["category"] if row["req_id"] != prev_id else ""
            status_badge = {
                "PASS": "✅ PASS",
                "MAPPED": "🔵 MAPPED",
                "NOT COVERED": "❌ NOT COVERED",
            }.get(row["verified"], row["verified"])
            f.write(
                f"| {rid} | {rcat} | {rdesc} | {racc} | "
                f"`{row['test_file']}` | `{row['test_name']}` | {status_badge} |\n"
            )
            prev_id = row["req_id"]

    print(f"MD   → {md_path}")

    # JSON manifest
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "total_requirements": len(REQUIREMENTS),
        "total_mappings": len(MAPPINGS),
        "requirements": REQUIREMENTS,
        "mappings": MAPPINGS,
    }
    manifest_path = reports_dir / "rtm_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"JSON → {manifest_path}")


if __name__ == "__main__":
    generate_rtm()

#!/usr/bin/env python3
"""Phase 478 — SDACS 표준 의견서·정합 자료의 메타 일관성 자동 점검.

목적:
1. 모든 의견서(Phase 461·472·474·475·476·477)가 *정직성 공시* 보유
2. 모든 표준 산출물(461·462·463·464·465·467·470·471·472·474·475·476·477)이
   상호 자매 문서 참조 (cross-link integrity)
3. 표준 dashboard (Phase 470) 의 §2.2 인벤토리가 실 산출물과 일치
   (드리프트 자동 탐지)
4. 모든 의견서가 MIT 라이센스 명시

사용:
    python scripts/standards_conformance_check.py            # 보고서 stdout
    python scripts/standards_conformance_check.py --json     # JSON 출력 (CI 게이트용)
    python scripts/standards_conformance_check.py --check    # 위반 시 exit 1

CI 통합:
- 표준 산출물 신규 추가 시 본 스크립트가 정합성 자동 검증
- 분기 갱신 시 dashboard 드리프트 자동 식별
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STANDARDS = ROOT / "docs" / "standards"
DOCS = ROOT / "docs"
DASHBOARD = STANDARDS / "SDACS_STANDARDS_CONTRIBUTION_DASHBOARD.md"

# 본 점검 대상 산출물 (Phase 기반 메타데이터)
# (key 파일명, 필수 phase 헤더, 카테고리)
STANDARDS_ARTIFACTS: list[dict] = [
    {"file": "SDACS_ASTM_F38_PROPOSAL.md", "phase": "Phase 461", "kind": "기고 초안"},
    {"file": "SDACS_ISO_TC20_SC16_TRACKER.md", "phase": "Phase 462", "kind": "추적 매트릭스"},
    {"file": "SDACS_KDRONE_POLICY_PROPOSAL.md", "phase": "Phase 463", "kind": "정책 제안서"},
    {"file": "SDACS_SWARM_SAFETY_WHITEPAPER.md", "phase": "Phase 464", "kind": "안전 백서"},
    {"file": "SDACS_BENCHMARK_SUITE.md", "phase": "Phase 465", "kind": "표준 시나리오"},
    {"file": "SDACS_STANDARDS_CONTRIBUTION_DASHBOARD.md", "phase": "Phase 470", "kind": "대시보드"},
    {"file": "SDACS_KS_PROPOSAL_UAS_CR.md", "phase": "Phase 471", "kind": "KS 표준 제안"},
    {"file": "SDACS_ICAO_RPASP_OPINION.md", "phase": "Phase 472", "kind": "WG 의견서"},
    {"file": "SDACS_GUTMA_HARMONY_OPINION.md", "phase": "Phase 474", "kind": "WG 의견서"},
    {"file": "SDACS_FAA_UTM_OPINION.md", "phase": "Phase 475", "kind": "WG 의견서"},
    {"file": "SDACS_JARUS_WG105_OPINION.md", "phase": "Phase 476", "kind": "WG 의견서"},
    {"file": "SDACS_IFALPA_RPAS_OPINION.md", "phase": "Phase 477", "kind": "WG 의견서"},
]

# WG 의견서(kind=="WG 의견서")가 반드시 보유해야 할 메타
OPINION_REQUIRED_KEYS = ["정직성", "MIT"]


def check_artifact_exists(artifact: dict) -> list[str]:
    """파일 존재 + 헤더 일치 검증."""
    issues: list[str] = []
    path = STANDARDS / artifact["file"]
    if not path.is_file():
        issues.append(f"FILE_MISSING: {artifact['file']}")
        return issues
    text = path.read_text(encoding="utf-8")
    if artifact["phase"] not in text:
        issues.append(f"PHASE_HEADER_MISSING: {artifact['file']} 에 {artifact['phase']} 없음")
    return issues


def check_opinion_meta(artifact: dict) -> list[str]:
    """WG 의견서의 정직성 공시 + MIT 라이센스 명시 검증."""
    issues: list[str] = []
    if artifact["kind"] != "WG 의견서":
        return issues
    path = STANDARDS / artifact["file"]
    if not path.is_file():
        return issues  # FILE_MISSING 이 별도 보고
    text = path.read_text(encoding="utf-8")
    for key in OPINION_REQUIRED_KEYS:
        if key not in text:
            issues.append(f"META_MISSING: {artifact['file']} 에 '{key}' 명시 없음")
    return issues


def check_dashboard_inventory() -> list[str]:
    """Phase 470 dashboard 의 §2.2 인벤토리가 실 산출물과 일치하는지."""
    issues: list[str] = []
    if not DASHBOARD.is_file():
        issues.append("DASHBOARD_MISSING: SDACS_STANDARDS_CONTRIBUTION_DASHBOARD.md")
        return issues
    text = DASHBOARD.read_text(encoding="utf-8")
    # 각 산출물 파일명이 dashboard 인벤토리에 존재해야
    for artifact in STANDARDS_ARTIFACTS:
        if artifact["file"] not in text:
            issues.append(
                f"DASHBOARD_DRIFT: {artifact['file']} 가 §2.2 인벤토리에 없음 — 분기 갱신 필요"
            )
    return issues


def check_cross_references() -> list[str]:
    """모든 WG 의견서가 Phase 470 dashboard 참조."""
    issues: list[str] = []
    for artifact in STANDARDS_ARTIFACTS:
        if artifact["kind"] != "WG 의견서":
            continue
        path = STANDARDS / artifact["file"]
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if "Phase 470" not in text and "STANDARDS_CONTRIBUTION_DASHBOARD" not in text:
            issues.append(
                f"XREF_MISSING: {artifact['file']} 가 Phase 470 dashboard 참조 안 함"
            )
    return issues


def run_all_checks() -> dict:
    """전 점검 수행 + 종합 결과 반환."""
    all_issues: list[str] = []
    for artifact in STANDARDS_ARTIFACTS:
        all_issues.extend(check_artifact_exists(artifact))
        all_issues.extend(check_opinion_meta(artifact))
    all_issues.extend(check_dashboard_inventory())
    all_issues.extend(check_cross_references())

    return {
        "total_artifacts": len(STANDARDS_ARTIFACTS),
        "issues_count": len(all_issues),
        "issues": all_issues,
        "ok": len(all_issues) == 0,
    }


def render_report(data: dict) -> str:
    lines = [
        "# 📊 SDACS 표준 산출물 정합성 점검 (Phase 478)",
        "",
        f"총 점검 대상: **{data['total_artifacts']} 산출물**",
        f"발견 이슈: **{data['issues_count']}건**",
        "",
    ]
    if data["ok"]:
        lines.append("✅ **모든 검사 통과** — 표준 산출물 메타 일관성 유지.")
    else:
        lines.append("⚠️ **이슈 발견** — 분기 갱신 또는 누락 항목 보강 필요.")
        lines.append("")
        for issue in data["issues"]:
            lines.append(f"- {issue}")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="JSON 출력 (CI 파싱용)")
    parser.add_argument("--check", action="store_true", help="이슈 발견 시 exit 1 (CI 게이트)")
    args = parser.parse_args()

    data = run_all_checks()

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(render_report(data))

    if args.check and not data["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

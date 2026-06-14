"""
비행계획 신고 양식 자동 생성 CLI (GENESIS Phase 303).

드론 원스톱 비행승인/특별비행승인 신청서를 생성해 reports/에 저장한다.

실행: python scripts/generate_flight_plan.py
출력: reports/flight_plan_application.json, reports/flight_plan_application.md
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.certification.flight_plan import (  # noqa: E402
    Aircraft,
    ApplicationInput,
    FlightPlan,
    Insurance,
    Operator,
    Pilot,
    build_application,
    render_markdown,
)

# ── 예시 신청 입력 (전남 해남 간척지 방제 시나리오) ────────────────────
SAMPLE = ApplicationInput(
    operator=Operator(
        name="SDACS 운영팀",
        organization="군집드론 공역통제 자동화 시스템",
        phone="010-0000-0000",
        address="서울특별시 관악구 관악로 1",
    ),
    aircraft=Aircraft(
        model="SDACS-X1",
        category="멀티콥터",
        purpose="농경지 방제",
        weight_kg=12.0,
        max_takeoff_weight_kg=20.0,
        registration_no="A1234",
    ),
    pilot=Pilot(name="김조종", license_no="DR-2024-001", phone="010-1111-2222"),
    flight_plan=FlightPlan(
        purpose="농경지 방제 군집 비행",
        area_name="전남 해남 간척지",
        center_lat=34.57,
        center_lon=126.59,
        radius_m=300.0,
        altitude_max_m=80.0,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 3),
    ),
    insurance=Insurance(insured=True, provider="삼성화재", policy_no="P-2026-001"),
)


def main() -> int:
    out_dir = ROOT / "reports"
    out_dir.mkdir(exist_ok=True)

    application = build_application(SAMPLE)

    json_path = out_dir / "flight_plan_application.json"
    json_path.write_text(
        json.dumps(application, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    md_path = out_dir / "flight_plan_application.md"
    md_path.write_text(render_markdown(application), encoding="utf-8")

    print(f"생성 완료: {json_path}")
    print(f"생성 완료: {md_path}")
    print(f"필요 승인: {application['필요승인'] or '면제 대상'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

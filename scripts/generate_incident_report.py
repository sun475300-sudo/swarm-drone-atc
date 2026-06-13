"""사고 보고서 자동 생성 CLI (GENESIS Phase 307).

짧은 시뮬레이션을 고장·통신두절 주입과 함께 실행한 뒤, 발생한 사건을 항철위
(ARAIB) 분류 체계로 정리한 사고 보고서를 ``reports/incident_report.md`` 및
``reports/incident_report.json``으로 출력한다.

실행: python scripts/generate_incident_report.py [--duration 120] [--seed 42]
                                                  [--drones 40] [--out reports]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from simulation.incident_report import build_incident_report  # noqa: E402
from simulation.simulator import SwarmSimulator  # noqa: E402


def main() -> int:
    """CLI 진입점 — 시뮬 실행 후 사고 보고서를 파일로 출력한다."""
    parser = argparse.ArgumentParser(description="SDACS 사고 보고서 자동 생성")
    parser.add_argument("--duration", type=float, default=120.0, help="시뮬레이션 시간(s)")
    parser.add_argument("--seed", type=int, default=42, help="난수 시드")
    parser.add_argument("--drones", type=int, default=40, help="드론 수")
    parser.add_argument("--scenario", type=str, default="default", help="시나리오 이름(보고서 표기용)")
    parser.add_argument("--out", type=str, default="reports", help="출력 디렉터리")
    args = parser.parse_args()

    # 고장·통신두절을 주입해 보고 대상 사건이 발생하도록 한다.
    override = {
        "drones": {"default_count": args.drones},
        "failure_injection": {
            "drone_failure_rate": 2.0,
            "comms_loss_rate": 1.0,
        },
    }
    print(
        f"🛸 시뮬레이션 실행: seed={args.seed}, drones={args.drones}, "
        f"duration={args.duration:.0f}s"
    )
    sim = SwarmSimulator(seed=args.seed, scenario_cfg=override)
    sim.run(duration_s=args.duration)

    report = build_incident_report(
        sim.analytics.events,
        scenario=args.scenario,
        seed=args.seed,
        duration_s=args.duration,
    )

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "incident_report.md"
    json_path = out_dir / "incident_report.json"
    md_path.write_text(report.to_markdown(), encoding="utf-8")
    json_path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    counts = report.category_counts
    print(f"📋 보고 대상 사건 {len(report.records)}건:")
    for cat, cnt in counts.items():
        print(f"   - {cat.value}: {cnt}건")
    print(f"✅ 생성 완료: {md_path}, {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

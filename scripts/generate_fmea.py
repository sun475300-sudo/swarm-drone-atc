#!/usr/bin/env python3
"""P700 — HITL Integration Report & FMEA (Failure Mode and Effects Analysis).

Generates a structured Markdown FMEA report for the SDACS drone swarm system.
The FMEA covers hardware, software, communication, and regulatory failure modes.

Usage:
    python scripts/generate_fmea.py [--output reports/fmea_YYYY-MM-DD.md]
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT / "reports"

# ---------------------------------------------------------------------------
# FMEA data — (ID, Component, Failure Mode, Effect, Severity, Occurrence,
#             Detection, RPN, Mitigation)
# Severity 1-10 (10=worst), Occurrence 1-10 (10=most frequent),
# Detection 1-10 (10=hardest to detect), RPN = S × O × D
# ---------------------------------------------------------------------------

FMEA_ITEMS = [
    # Hardware failures
    ("HW-01", "Pixhawk 6X", "전원 공급 실패", "드론 즉시 추락", 10, 2, 3, 60,
     "이중 전원 보드, LiPo 전압 모니터링 + 저전압 RTL"),
    ("HW-02", "ESC/모터", "단일 모터 고장", "비행 안정성 저하, 긴급 착륙", 8, 3, 4, 96,
     "쿼드/헥사 모터 리던던시, 모터 전류 이상 감지 후 Failsafe"),
    ("HW-03", "RTK-GPS", "위성 신호 손실", "위치 추정 오류 → 충돌 위험", 9, 4, 2, 72,
     "IMU 데드레코닝 보정, 광류 센서 보조, 3D 지오펜스 강제 Failsafe"),
    ("HW-04", "컴패니언 컴퓨터(Jetson)", "과열 → 재부팅", "SDACS AI 제어 루프 중단", 7, 3, 5, 105,
     "온도 모니터링, 80°C 이상 시 경량 모드 전환, Pixhawk 독립 Failsafe"),
    ("HW-05", "배터리", "급격한 셀 전압 강하", "비행 중 갑작스러운 전원 차단", 10, 2, 3, 60,
     "셀-레벨 모니터링, 20% RTL 트리거, 10% 강제 착륙"),
    # Software failures
    ("SW-01", "AirspaceController", "CBS 경로 계산 타임아웃(>1s)", "충돌 해결 불가 → NMR 상승", 8, 3, 3, 72,
     "CBS 시간 제한 500ms, 초과 시 APF 폴백, 테스트: test_cbs_timeout"),
    ("SW-02", "BatteryPredictor", "np.bool_ 타입 오류 → 잘못된 RTL 판단", "RTL 미발동 → 배터리 방전", 7, 2, 6, 84,
     "bool() 명시적 캐스팅 적용 (v2026-05-30 수정), 회귀 테스트 추가"),
    ("SW-03", "WindModel", "강풍 조건 APF 파라미터 미전환", "충돌 회피 반응 지연", 7, 3, 4, 84,
     "풍속 >10 m/s 자동 APF_PARAMS_WINDY 전환, 테스트 검증"),
    ("SW-04", "SwarmSimulator", "SimPy 이벤트 루프 무한 대기", "시뮬레이션 정지", 5, 2, 7, 70,
     "타임아웃 감시자 스레드, env.run(until=timeout) 강제"),
    ("SW-05", "Remote ID 브로드캐스터", "1Hz 미만 전송 → FAA 위반", "규제 불순응, 운항 허가 취소", 9, 3, 2, 54,
     "전송 레이트 모니터링 + 경보, RID-CR 메트릭 CI 검증"),
    # Communication failures
    ("CM-01", "MAVLink 링크", "패킷 손실률 >5%", "명령 지연, 위치 업데이트 오류", 7, 4, 3, 84,
     "MAVLink 재전송 메커니즘, 링크 품질 모니터링, Failsafe LAND"),
    ("CM-02", "Ground WebSocket", "연결 끊김", "지상 제어 불가", 8, 3, 2, 48,
     "자동 재연결 (OnboardBridge), 독립 Pixhawk Failsafe"),
    ("CM-03", "LAANC 인가 시스템", "응답 지연 >30s", "비승인 공역 진입 위험", 8, 2, 4, 64,
     "LAANC 캐싱 (5분), 타임아웃 후 지상 대기 + 운영자 알림"),
    ("CM-04", "GPS 스푸핑", "위치 위조 신호 수신", "잘못된 비행 경로, 충돌", 10, 1, 7, 70,
     "다중 GNSS 수신기 교차 검증, 이상 위치 점프 감지"),
    # Regulatory failures
    ("REG-01", "지오펜스 위반", "경계 이탈 → 금지 공역 진입", "법적 제재, 충돌 위험", 10, 2, 2, 40,
     "하드웨어 지오펜스(Pixhawk) + 소프트웨어 이중 검사"),
    ("REG-02", "UTM 연동 실패", "비행 계획 미등록", "공역 충돌 위험, 법적 제재", 8, 2, 4, 64,
     "UTM 제출 실패 시 자동 대기, 수동 승인 없이 이륙 차단"),
    ("REG-03", "NOTAM 미확인 비행", "임시 제한 공역 진입", "법적 제재, 안전 사고", 9, 2, 3, 54,
     "비행 전 NOTAM 자동 조회, 활성 NOTAM 충돌 시 경로 재계획"),
]


def _rpn_risk_level(rpn: int) -> str:
    if rpn >= 200:
        return "🔴 CRITICAL"
    if rpn >= 100:
        return "🟠 HIGH"
    if rpn >= 50:
        return "🟡 MEDIUM"
    return "🟢 LOW"


def build_fmea_report() -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines: list[str] = [
        f"# SDACS HITL Integration Report & FMEA — {today}",
        "",
        "> Phase P700 — 자동 생성 by `scripts/generate_fmea.py`",
        "",
        "## 1. 개요",
        "",
        "본 보고서는 SDACS (군집드론 공역통제 자동화 시스템)의 HITL(Hardware-In-The-Loop)",
        "통합 단계에서 식별된 실패 모드를 FMEA 방법론으로 분석한 결과입니다.",
        "",
        "**분석 범위:** 하드웨어, 소프트웨어, 통신, 규제 준수",
        "**RPN 계산:** 심각도(S) × 발생빈도(O) × 검출불능도(D)",
        "",
        "---",
        "",
        "## 2. FMEA 표",
        "",
        "| ID | 구성요소 | 실패 모드 | 영향 | S | O | D | RPN | 위험도 | 경감 조치 |",
        "|-----|---------|---------|------|---|---|---|-----|------|---------|",
    ]

    for item in FMEA_ITEMS:
        fid, comp, mode, effect, s, o, d, rpn, mitigation = item
        risk = _rpn_risk_level(rpn)
        lines.append(
            f"| {fid} | {comp} | {mode} | {effect} | {s} | {o} | {d} | **{rpn}** | {risk} | {mitigation} |"
        )

    # Summary statistics
    rpns = [item[7] for item in FMEA_ITEMS]
    critical = sum(1 for r in rpns if r >= 200)
    high = sum(1 for r in rpns if 100 <= r < 200)
    medium = sum(1 for r in rpns if 50 <= r < 100)
    low = sum(1 for r in rpns if r < 50)

    lines += [
        "",
        "---",
        "",
        "## 3. 위험도 요약",
        "",
        f"| 수준 | 건수 | 기준(RPN) |",
        f"|------|------|---------|",
        f"| 🔴 CRITICAL | {critical} | ≥200 |",
        f"| 🟠 HIGH | {high} | 100-199 |",
        f"| 🟡 MEDIUM | {medium} | 50-99 |",
        f"| 🟢 LOW | {low} | <50 |",
        f"| **합계** | **{len(FMEA_ITEMS)}** | |",
        "",
        "---",
        "",
        "## 4. 즉각 대응 항목 (RPN ≥ 100)",
        "",
    ]

    high_risk = [item for item in FMEA_ITEMS if item[7] >= 100]
    for item in sorted(high_risk, key=lambda x: x[7], reverse=True):
        fid, comp, mode, effect, s, o, d, rpn, mitigation = item
        lines += [
            f"### {fid} — {comp}: {mode} (RPN={rpn})",
            "",
            f"- **영향:** {effect}",
            f"- **경감:** {mitigation}",
            "",
        ]

    lines += [
        "---",
        "",
        "## 5. HITL 통합 검증 체크리스트",
        "",
        "- [ ] Pixhawk ↔ Jetson MAVLink 링크 지연 <10ms 확인",
        "- [ ] 배터리 RTL 트리거 실기 테스트 (20% 기준)",
        "- [ ] GPS 손실 시뮬레이션 → IMU 데드레코닝 전환 확인",
        "- [ ] 지오펜스 하드웨어 차단 동작 확인",
        "- [ ] Remote ID 브로드캐스트 주파수 검증 (≥1Hz)",
        "- [ ] WebSocket 재연결 자동화 (ground link 차단 후 복구)",
        "- [ ] NOTAM 조회 → 경로 재계획 end-to-end 테스트",
        "",
        "---",
        "",
        f"*생성 시각: {datetime.now(timezone.utc).isoformat()}*",
    ]

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """``main`` 동작을 수행한다."""
    p = argparse.ArgumentParser(description="Generate HITL FMEA report")
    p.add_argument("--output", metavar="PATH", help="Output Markdown path")
    args = p.parse_args(argv)

    report = build_fmea_report()

    if args.output:
        out = Path(args.output)
    else:
        REPORTS_DIR.mkdir(exist_ok=True)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out = REPORTS_DIR / f"fmea_{today}.md"

    out.write_text(report, encoding="utf-8")
    print(f"FMEA report written to: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

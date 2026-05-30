"""FMEA 8항목 + HITL 통합 보고서 생성기 (Markdown/JSON 출력)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class FMEAItem:
    """FMEA (Failure Mode and Effects Analysis) 단일 항목."""

    component: str      # 구성 요소
    failure_mode: str   # 고장 모드
    effect: str         # 영향
    severity: int       # 심각도 (1~10)
    occurrence: int     # 발생 가능성 (1~10)
    detection: int      # 검출 용이성 (1~10, 낮을수록 검출 어려움)
    rpn: int            # 위험 우선 순위 수치 (Severity × Occurrence × Detection)
    mitigation: str     # 완화 대책

    def __post_init__(self) -> None:
        for attr in ("severity", "occurrence", "detection"):
            val = getattr(self, attr)
            if not (1 <= val <= 10):
                raise ValueError(f"{attr}는 1~10 범위여야 합니다, 입력: {val}")


@dataclass
class HITLReport:
    """HITL(Hardware-in-the-Loop) 통합 테스트 보고서."""

    drone_count: int
    test_duration_s: float
    pass_rate: float                        # 0.0 ~ 1.0
    fmea_items: list[FMEAItem] = field(default_factory=list)
    timestamp: str = ""                     # ISO 8601 UTC

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


# -----------------------------------------------------------------
# 표준 8개 FMEA 항목 정의
# -----------------------------------------------------------------
_STANDARD_FMEA: list[dict] = [
    {
        "component": "GPS 수신기",
        "failure_mode": "GPS 신호 손실",
        "effect": "위치 정확도 저하, 자동 착륙 불가",
        "severity": 8,
        "occurrence": 3,
        "detection": 2,
        "mitigation": "RTK GPS 이중화, IMU/Optical Flow 백업 융합 적용",
    },
    {
        "component": "모터/ESC",
        "failure_mode": "단일 모터 과열/고장",
        "effect": "추력 불균형, 기체 불안정",
        "severity": 9,
        "occurrence": 2,
        "detection": 3,
        "mitigation": "실시간 모터 전류 모니터링, N+1 모터 구성 고려",
    },
    {
        "component": "통신 링크",
        "failure_mode": "RF 통신 두절",
        "effect": "원격 제어 불가, 군집 좌표 손실",
        "severity": 8,
        "occurrence": 4,
        "detection": 1,
        "mitigation": "메시 네트워크 자동 전환, 자율 RTL 페일세이프 활성화",
    },
    {
        "component": "배터리",
        "failure_mode": "배터리 셀 불량/과방전",
        "effect": "급격한 전압 강하, 비상 착륙",
        "severity": 9,
        "occurrence": 3,
        "detection": 2,
        "mitigation": "셀 밸런싱 BMS, 배터리 < 20% RTL 자동 트리거",
    },
    {
        "component": "지오펜스 모듈",
        "failure_mode": "지오펜스 경계 위반",
        "effect": "비인가 공역 침범, 규제 위반",
        "severity": 7,
        "occurrence": 2,
        "detection": 1,
        "mitigation": "하드웨어 지오펜스 이중화, COM_FLTMODE 강제 RTL 설정",
    },
    {
        "component": "센서 IMU",
        "failure_mode": "IMU 드리프트/바이어스",
        "effect": "자세 추정 오류, 경로 이탈",
        "severity": 7,
        "occurrence": 3,
        "detection": 4,
        "mitigation": "EKF2 다중 IMU 융합, 이륙 전 자동 캘리브레이션",
    },
    {
        "component": "RTL 시스템",
        "failure_mode": "RTL 명령 실패/무응답",
        "effect": "페일세이프 미동작, 드론 표류",
        "severity": 9,
        "occurrence": 2,
        "detection": 2,
        "mitigation": "RTL 이중 명령 채널, 지상국 watchdog 타이머",
    },
    {
        "component": "편대 제어",
        "failure_mode": "편대 대형 붕괴",
        "effect": "드론 간 충돌 위험 증가",
        "severity": 8,
        "occurrence": 3,
        "detection": 3,
        "mitigation": "APF 기반 충돌 회피, 최소 이격 거리 1.5m 강제",
    },
]


class HITLReportGenerator:
    """HITL 통합 테스트 보고서를 생성하고 Markdown/JSON으로 내보낸다."""

    def generate_fmea(self) -> list[FMEAItem]:
        """표준 8개 FMEA 항목을 반환한다."""
        items = []
        for d in _STANDARD_FMEA:
            rpn = d["severity"] * d["occurrence"] * d["detection"]
            items.append(FMEAItem(
                component=d["component"],
                failure_mode=d["failure_mode"],
                effect=d["effect"],
                severity=d["severity"],
                occurrence=d["occurrence"],
                detection=d["detection"],
                rpn=rpn,
                mitigation=d["mitigation"],
            ))
        return items

    def generate_report(
        self, drone_count: int, test_duration_s: float, pass_rate: float
    ) -> HITLReport:
        """HITL 보고서를 생성한다. pass_rate: 0.0~1.0."""
        if not (0.0 <= pass_rate <= 1.0):
            raise ValueError(f"pass_rate는 0~1 범위여야 합니다, 입력: {pass_rate}")
        return HITLReport(
            drone_count=drone_count,
            test_duration_s=test_duration_s,
            pass_rate=pass_rate,
            fmea_items=self.generate_fmea(),
        )

    def to_markdown(self, report: HITLReport) -> str:
        """HITLReport를 Markdown 문자열로 변환한다."""
        lines: list[str] = [
            "# HITL 통합 테스트 보고서",
            "",
            f"- **생성 일시**: {report.timestamp}",
            f"- **드론 수**: {report.drone_count}대",
            f"- **테스트 시간**: {report.test_duration_s}초",
            f"- **통과율**: {report.pass_rate * 100:.1f}%",
            "",
            "## FMEA 분석 (8항목)",
            "",
            "| 구성 요소 | 고장 모드 | 영향 | 심각도(S) | 발생도(O) | 검출도(D) | RPN | 완화 대책 |",
            "|-----------|----------|------|:---------:|:---------:|:---------:|:---:|-----------|",
        ]
        for item in report.fmea_items:
            lines.append(
                f"| {item.component} | {item.failure_mode} | {item.effect} "
                f"| {item.severity} | {item.occurrence} | {item.detection} "
                f"| {item.rpn} | {item.mitigation} |"
            )

        # RPN 기준 상위 위험 항목 요약
        sorted_items = sorted(report.fmea_items, key=lambda x: x.rpn, reverse=True)
        lines += [
            "",
            "## 고위험 항목 (RPN 상위 3)",
            "",
        ]
        for i, item in enumerate(sorted_items[:3], 1):
            lines.append(f"{i}. **{item.component}** — {item.failure_mode} (RPN: {item.rpn})")

        return "\n".join(lines)

    def to_json(self, report: HITLReport) -> str:
        """HITLReport를 JSON 문자열로 변환한다 (들여쓰기 2칸)."""
        data = {
            "timestamp": report.timestamp,
            "drone_count": report.drone_count,
            "test_duration_s": report.test_duration_s,
            "pass_rate": report.pass_rate,
            "fmea_items": [asdict(item) for item in report.fmea_items],
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

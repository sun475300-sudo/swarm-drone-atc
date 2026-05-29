"""P700: FMEA 8항목 + HITL 통합 보고서 생성기 (Markdown/JSON).

FMEA (Failure Mode and Effects Analysis) 8개 항목:
1. 모터 고장
2. GPS 신호 손실
3. 통신 두절
4. 배터리 극단적 방전
5. Geofence 침범
6. 소프트웨어 크래시 (Watchdog 감지)
7. 센서 오프셋 (IMU 드리프트)
8. 충돌 감지 시스템 오작동
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Severity(Enum):
    CATASTROPHIC = 1    # 드론 손실 / 인명 위협
    CRITICAL = 2        # 미션 중단
    MAJOR = 3           # 성능 저하
    MINOR = 4           # 운용 불편
    NEGLIGIBLE = 5      # 무시 가능


class Probability(Enum):
    FREQUENT = 1        # 자주 발생
    PROBABLE = 2        # 가능성 높음
    OCCASIONAL = 3      # 가끔 발생
    REMOTE = 4          # 드물게 발생
    IMPROBABLE = 5      # 거의 없음


class Detectability(Enum):
    ALMOST_IMPOSSIBLE = 1
    DIFFICULT = 2
    MODERATE = 3
    EASY = 4
    ALMOST_CERTAIN = 5


@dataclass
class FMEAItem:
    id: str
    failure_mode: str
    effect: str
    severity: Severity
    probability: Probability
    detectability: Detectability
    current_control: str
    recommended_action: str
    mitigation_implemented: bool = False

    @property
    def rpn(self) -> int:
        """Risk Priority Number (SxPxD — 낮을수록 위험)."""
        return self.severity.value * self.probability.value * self.detectability.value

    @property
    def risk_level(self) -> str:
        rpn = self.rpn
        if rpn <= 10:
            return "HIGH_RISK"
        if rpn <= 30:
            return "MEDIUM_RISK"
        return "LOW_RISK"


# 표준 FMEA 8개 항목
DEFAULT_FMEA_ITEMS: list[FMEAItem] = [
    FMEAItem("F01", "모터 고장", "드론 추락·충돌 위험",
             Severity.CATASTROPHIC, Probability.REMOTE, Detectability.EASY,
             "모터 전류 모니터링", "트리모터 비상착륙 모드 구현"),
    FMEAItem("F02", "GPS 신호 손실", "위치 추정 정확도 저하·RTL 불가",
             Severity.CRITICAL, Probability.OCCASIONAL, Detectability.ALMOST_CERTAIN,
             "EKF2 복합 센서 융합", "광학류 + 기압계 폴백 활성화"),
    FMEAItem("F03", "통신 두절", "원격 제어 불능·미션 중단",
             Severity.CRITICAL, Probability.OCCASIONAL, Detectability.EASY,
             "RC 손실 Failsafe RTL", "메시 네트워크 이중화"),
    FMEAItem("F04", "배터리 극단 방전", "드론 전원 차단·추락",
             Severity.CATASTROPHIC, Probability.REMOTE, Detectability.ALMOST_CERTAIN,
             "전압 20% 기준 RTL", "배터리 상태 예측 강화"),
    FMEAItem("F05", "Geofence 침범", "비허가 공역 진입·법규 위반",
             Severity.MAJOR, Probability.REMOTE, Detectability.ALMOST_CERTAIN,
             "Geofence 소프트·하드 경계 이중화", "Geofence 사전 경고 알림 추가"),
    FMEAItem("F06", "소프트웨어 크래시 (Watchdog)", "자율 제어 상실",
             Severity.CRITICAL, Probability.REMOTE, Detectability.MODERATE,
             "Watchdog 타이머 1Hz 킥", "안전 착륙 데몬 분리 프로세스화"),
    FMEAItem("F07", "IMU 드리프트", "자세 추정 오류·불안정 비행",
             Severity.MAJOR, Probability.OCCASIONAL, Detectability.DIFFICULT,
             "온도 보정 캘리브레이션", "이중 IMU 교차 검증"),
    FMEAItem("F08", "충돌 감지 오작동", "회피 기동 실패·근접 충돌",
             Severity.CRITICAL, Probability.REMOTE, Detectability.MODERATE,
             "CPA 90초 선제 감지", "백업 라이다 기반 감지 추가"),
]


@dataclass
class HITLTestResult:
    test_id: str
    description: str
    passed: bool
    duration_sec: float
    notes: str = ""


@dataclass
class HITLReport:
    title: str = "SDACS HITL 통합 보고서"
    generated_at: float = field(default_factory=time.time)
    fmea_items: list[FMEAItem] = field(default_factory=lambda: list(DEFAULT_FMEA_ITEMS))
    hitl_results: list[HITLTestResult] = field(default_factory=list)
    environment: dict[str, Any] = field(default_factory=dict)

    def add_test_result(self, result: HITLTestResult) -> None:
        self.hitl_results.append(result)

    @property
    def pass_rate(self) -> float:
        if not self.hitl_results:
            return 0.0
        return sum(1 for r in self.hitl_results if r.passed) / len(self.hitl_results)

    @property
    def high_risk_items(self) -> list[FMEAItem]:
        return [item for item in self.fmea_items if item.risk_level == "HIGH_RISK"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "generated_at": self.generated_at,
            "fmea_summary": {
                "total_items": len(self.fmea_items),
                "high_risk": len(self.high_risk_items),
                "avg_rpn": sum(i.rpn for i in self.fmea_items) / len(self.fmea_items),
            },
            "hitl_summary": {
                "total_tests": len(self.hitl_results),
                "pass_rate": round(self.pass_rate, 4),
            },
            "fmea_items": [
                {
                    "id": item.id,
                    "failure_mode": item.failure_mode,
                    "severity": item.severity.name,
                    "probability": item.probability.name,
                    "detectability": item.detectability.name,
                    "rpn": item.rpn,
                    "risk_level": item.risk_level,
                    "mitigation_implemented": item.mitigation_implemented,
                }
                for item in self.fmea_items
            ],
            "hitl_results": [
                {"test_id": r.test_id, "passed": r.passed, "duration_sec": r.duration_sec}
                for r in self.hitl_results
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def to_markdown(self) -> str:
        lines = [
            f"# {self.title}",
            "",
            "## FMEA 분석 결과",
            "",
            "| ID | 고장 모드 | 심각도 | 발생 확률 | 감지도 | RPN | 위험 수준 |",
            "|----|---------|--------|---------|--------|-----|---------|",
        ]
        for item in self.fmea_items:
            lines.append(
                f"| {item.id} | {item.failure_mode} | {item.severity.name} | "
                f"{item.probability.name} | {item.detectability.name} | "
                f"{item.rpn} | {item.risk_level} |"
            )
        lines.extend([
            "",
            "## HITL 통합 테스트 결과",
            "",
            f"- 총 테스트: {len(self.hitl_results)}",
            f"- 통과율: {self.pass_rate:.1%}",
            "",
            "| 테스트 ID | 설명 | 결과 | 소요 시간 |",
            "|---------|-----|------|---------|",
        ])
        for r in self.hitl_results:
            status = "✅ PASS" if r.passed else "❌ FAIL"
            lines.append(f"| {r.test_id} | {r.description} | {status} | {r.duration_sec:.2f}s |")
        return "\n".join(lines)


class HITLReportGenerator:
    """HITL 보고서 생성 유틸리티."""

    def __init__(self) -> None:
        self._report = HITLReport()

    def set_environment(self, **kwargs: Any) -> None:
        self._report.environment.update(kwargs)

    def add_test(self, test_id: str, description: str, passed: bool,
                 duration_sec: float, notes: str = "") -> None:
        self._report.add_test_result(
            HITLTestResult(test_id, description, passed, duration_sec, notes)
        )

    def mark_fmea_mitigated(self, fmea_id: str) -> None:
        for item in self._report.fmea_items:
            if item.id == fmea_id:
                item.mitigation_implemented = True
                return

    def build(self) -> HITLReport:
        return self._report

    def save_json(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self._report.to_json())

    def save_markdown(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self._report.to_markdown())

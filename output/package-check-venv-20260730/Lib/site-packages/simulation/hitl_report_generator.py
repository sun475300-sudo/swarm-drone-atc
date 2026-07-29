"""Phase 700: HITL 통합 보고서 + FMEA (Failure Mode and Effects Analysis)."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(Enum):
    """FMEA 심각도."""
    CATASTROPHIC = 1
    CRITICAL = 2
    MARGINAL = 3
    NEGLIGIBLE = 4


class Probability(Enum):
    """FMEA 발생 확률."""
    FREQUENT = 1
    PROBABLE = 2
    OCCASIONAL = 3
    REMOTE = 4
    IMPROBABLE = 5


class Detectability(Enum):
    """FMEA 탐지 용이성."""
    UNDETECTABLE = 10
    VERY_LOW = 8
    LOW = 6
    MODERATE = 4
    HIGH = 2
    VERY_HIGH = 1


@dataclass
class FMEAEntry:
    """FMEA 항목."""
    component: str
    failure_mode: str
    failure_effect: str
    severity: Severity
    probability: Probability
    detectability: Detectability
    current_controls: str
    recommended_action: str
    responsible: str = "SDACS 팀"

    @property
    def rpn(self) -> int:
        return self.severity.value * self.probability.value * self.detectability.value

    @property
    def risk_level(self) -> str:
        if self.rpn <= 20:
            return "LOW"
        if self.rpn <= 60:
            return "MEDIUM"
        if self.rpn <= 120:
            return "HIGH"
        return "CRITICAL"


@dataclass
class HITLTestSummary:
    """HITL 시험 결과 요약."""
    test_name: str
    passed: bool
    duration_s: float
    metrics: dict[str, float] = field(default_factory=dict)
    notes: str = ""


@dataclass
class HITLReport:
    """HITL 통합 보고서."""
    title: str = "SDACS HITL 통합 안전 보고서"
    version: str = "1.0"
    generated_at: float = field(default_factory=time.time)
    fmea_entries: list[FMEAEntry] = field(default_factory=list)
    test_results: list[HITLTestSummary] = field(default_factory=list)
    overall_passed: bool = False
    safety_score: float = 0.0


STANDARD_FMEA: list[dict[str, Any]] = [
    {
        "component": "GPS 수신기",
        "failure_mode": "신호 손실",
        "failure_effect": "위치 추정 불가 → 포메이션 붕괴",
        "severity": Severity.CRITICAL,
        "probability": Probability.OCCASIONAL,
        "detectability": Detectability.HIGH,
        "current_controls": "RTK 이중화, 고도계 백업",
        "recommended_action": "광학 흐름 센서 추가, EKF 피처 게이팅",
    },
    {
        "component": "통신 링크",
        "failure_mode": "RF 간섭 / 링크 단절",
        "failure_effect": "명령 불가 → Failsafe RTL 발동",
        "severity": Severity.CRITICAL,
        "probability": Probability.PROBABLE,
        "detectability": Detectability.HIGH,
        "current_controls": "Failsafe RTL (5초 임계값)",
        "recommended_action": "주파수 다이버시티 (2.4+5.8 GHz), 자율 복귀 시험",
    },
    {
        "component": "배터리",
        "failure_mode": "급격한 전압 강하",
        "failure_effect": "즉시 착륙 불가 → 추락",
        "severity": Severity.CATASTROPHIC,
        "probability": Probability.REMOTE,
        "detectability": Detectability.MODERATE,
        "current_controls": "배터리 잔량 모니터링, 15% 강제 착륙",
        "recommended_action": "셀 밸런싱 모니터링, 비행 전 배터리 상태 검사 의무화",
    },
    {
        "component": "APF 충돌 회피",
        "failure_mode": "포텐셜 장 계산 오류",
        "failure_effect": "드론 간 근접 → 충돌 위험",
        "severity": Severity.CRITICAL,
        "probability": Probability.REMOTE,
        "detectability": Detectability.MODERATE,
        "current_controls": "CPA 90초 예측, CBS 대안 경로",
        "recommended_action": "하드웨어 근접 센서 (ToF) 추가, 충돌 임계 2중 검사",
    },
    {
        "component": "Jetson 컴패니언",
        "failure_mode": "프로세서 과부하 / 메모리 부족",
        "failure_effect": "제어 루프 지연 → 불안정 비행",
        "severity": Severity.MARGINAL,
        "probability": Probability.OCCASIONAL,
        "detectability": Detectability.HIGH,
        "current_controls": "CPU/GPU 사용률 모니터링, 태스크 우선순위 설정",
        "recommended_action": "실시간 커널 패치, 메모리 예약 설정",
    },
    {
        "component": "Remote ID 방송",
        "failure_mode": "BLE 모듈 고장",
        "failure_effect": "FAA 규정 위반 → 비행 허가 취소",
        "severity": Severity.CRITICAL,
        "probability": Probability.IMPROBABLE,
        "detectability": Detectability.HIGH,
        "current_controls": "네트워크 Remote ID 백업",
        "recommended_action": "자가 진단 루틴, 이중화 BLE 모듈",
    },
    {
        "component": "RTK 기준국",
        "failure_mode": "NTRIP 서버 연결 실패",
        "failure_effect": "RTK FIX → FLOAT 강등, 정밀도 저하",
        "severity": Severity.MARGINAL,
        "probability": Probability.OCCASIONAL,
        "detectability": Detectability.HIGH,
        "current_controls": "로컬 기준국 운용, FLOAT 모드 허용",
        "recommended_action": "기준국 이중화, FLOAT 모드 성능 검증",
    },
    {
        "component": "PTP 시간 동기화",
        "failure_mode": "마스터 노드 장애",
        "failure_effect": "클록 드리프트 → 센서 퓨전 오차 증가",
        "severity": Severity.MARGINAL,
        "probability": Probability.REMOTE,
        "detectability": Detectability.MODERATE,
        "current_controls": "BMCA 자동 마스터 재선출",
        "recommended_action": "GPS PPS 신호 기반 클록 교정",
    },
]


class HITLReportGenerator:
    """HITL 통합 보고서 + FMEA 생성기."""

    def __init__(self) -> None:
        self._report = HITLReport()
        self._load_standard_fmea()

    def _load_standard_fmea(self) -> None:
        for entry in STANDARD_FMEA:
            self._report.fmea_entries.append(FMEAEntry(**entry))

    def add_test_result(
        self,
        test_name: str,
        passed: bool,
        duration_s: float,
        metrics: dict[str, float] | None = None,
        notes: str = "",
    ) -> None:
        self._report.test_results.append(HITLTestSummary(
            test_name=test_name,
            passed=passed,
            duration_s=duration_s,
            metrics=metrics or {},
            notes=notes,
        ))

    def compute_safety_score(self) -> float:
        """안전 점수 (0-100): RPN 기반 역산."""
        entries = self._report.fmea_entries
        if not entries:
            return 100.0
        max_rpn = max(e.rpn for e in entries)
        avg_rpn = sum(e.rpn for e in entries) / len(entries)
        score = max(0.0, 100.0 - avg_rpn / 2.0 - max_rpn / 10.0)
        self._report.safety_score = round(score, 1)
        return self._report.safety_score

    def finalize(self) -> HITLReport:
        """보고서 최종화."""
        passed_tests = sum(1 for t in self._report.test_results if t.passed)
        total_tests = len(self._report.test_results)
        self._report.overall_passed = (
            total_tests > 0 and passed_tests == total_tests
        )
        self.compute_safety_score()
        return self._report

    def to_markdown(self) -> str:
        """Markdown 보고서 문자열 반환."""
        report = self.finalize()
        lines = [
            f"# {report.title}",
            f"버전: {report.version}",
            "",
            "## FMEA 분석",
            "",
            "| 컴포넌트 | 고장 모드 | 영향 | 심각도 | RPN | 위험 수준 | 권고 조치 |",
            "|---------|---------|------|------|-----|---------|---------|",
        ]
        for e in report.fmea_entries:
            effect = e.failure_effect[:30] + ("..." if len(e.failure_effect) > 30 else "")
            action = e.recommended_action[:40] + ("..." if len(e.recommended_action) > 40 else "")
            lines.append(
                f"| {e.component} | {e.failure_mode} | {effect} "
                f"| {e.severity.name} | {e.rpn} | {e.risk_level} | {action} |"
            )
        lines += [
            "",
            "## HITL 시험 결과",
            "",
            "| 시험명 | 합격 | 소요 시간 |",
            "|-------|------|---------|",
        ]
        for t in report.test_results:
            status = "✅ 합격" if t.passed else "❌ 실패"
            lines.append(f"| {t.test_name} | {status} | {t.duration_s:.2f}s |")
        lines += [
            "",
            f"## 종합 안전 점수: {report.safety_score}/100",
            f"## 전체 결과: {'✅ 합격' if report.overall_passed else '⚠️ 추가 검토 필요'}",
        ]
        return "\n".join(lines)

    def to_json(self) -> str:
        """JSON 보고서 문자열 반환."""
        report = self.finalize()
        data = {
            "title": report.title,
            "version": report.version,
            "generated_at": report.generated_at,
            "overall_passed": report.overall_passed,
            "safety_score": report.safety_score,
            "fmea": [
                {
                    "component": e.component,
                    "failure_mode": e.failure_mode,
                    "severity": e.severity.name,
                    "probability": e.probability.name,
                    "detectability": e.detectability.name,
                    "rpn": e.rpn,
                    "risk_level": e.risk_level,
                    "recommended_action": e.recommended_action,
                }
                for e in report.fmea_entries
            ],
            "tests": [
                {
                    "name": t.test_name,
                    "passed": t.passed,
                    "duration_s": t.duration_s,
                    "metrics": t.metrics,
                }
                for t in report.test_results
            ],
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

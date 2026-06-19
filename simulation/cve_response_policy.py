"""ODYSSEY Phase 488 — 보안 장기 지원: CVE 대응 SLA + 핀 갱신 절차.

Continuum 트랙(Phase 481-500)에서 Phase 481(`dependency_gate`, 의존성 자동
머지 정책)의 자매편. 481 이 *기능 갱신* PR 을 자동 머지/리뷰/차단으로 가르는
정책이라면, 본 모듈은 *보안 취약점(CVE)* 한 건이 들어왔을 때 "얼마나 급히
대응해야 하고, 핀(`requirements.lock.txt`)을 갱신해야 하는가" 를 결정적
정책으로 명문화한다 — 같은 입력은 항상 같은 대응 결정을 낸다.

설계 원칙
--------
- **정책은 코드, 코드는 정책**: 대응 규칙을 문서(``docs/standards/
  CVE_RESPONSE_SLA_POLICY.md``)와 본 평가기에 *한 번씩만* 적기 위해, 본
  모듈이 유일한 실행 가능 명세다. 문서는 규칙을 서술할 뿐 중복 로직을 두지
  않는다(테스트가 ``POLICY_MATRIX`` ↔ ``assess`` 일치를 강제).
- **자문이지 집행 아님**: 본 모듈은 *대응을 권고*할 뿐 핀을 실제로 갱신하거나
  배포하지 않는다(부수효과 0). 사람/CI 가 결정을 집행한다.
- **SECURITY.md 기준선 준수**: SLA 는 ``SECURITY.md`` 의 명시 약속(접수 확인
  7일·해결 시한 14일)을 HIGH 등급 기준으로 삼고, 심각도에 따라 단조 가감한다.
  HIGH 의 (접수 3일·해결 14일) 중 해결 14일이 SECURITY.md 의 상한과 일치.
- **노출 기반 차등**: 같은 CVSS 라도 런타임 의존성(실제 임포트)·개발 도구·
  은퇴(archived) 코드 노출에 따라 대응이 다르다. archived 노출은 SECURITY.md
  "Out of Scope" 에 따라 SLA 대상 외.

CVSS v3.1 정성 등급(표준 절단점):
    0.0=NONE · 0.1-3.9=LOW · 4.0-6.9=MEDIUM · 7.0-8.9=HIGH · 9.0-10.0=CRITICAL

무작위성 0 · 결정적 · 기존 모듈 무수정 순수 추가.

CLI:
    python -m simulation.cve_response_policy --policy    # 정책 매트릭스
    python -m simulation.cve_response_policy --demo      # 예시 평가
    python -m simulation.cve_response_policy --manifest  # 정책 매니페스트(JSON)
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any

# --- CVSS 심각도 등급 -------------------------------------------------------
SEVERITY_CRITICAL = "CRITICAL"
SEVERITY_HIGH = "HIGH"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_LOW = "LOW"
SEVERITY_NONE = "NONE"

# 심각도 단조 순서(낮음→높음). 인덱스로 한 단계 강등/승급을 계산한다.
_SEVERITY_ORDER = (
    SEVERITY_NONE,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    SEVERITY_HIGH,
    SEVERITY_CRITICAL,
)

# --- 노출 분류(취약 의존성이 SDACS 에 닿는 경로) ----------------------------
EXPOSURE_RUNTIME = "runtime"   # 런타임에 실제 임포트(requirements.lock.txt 핀)
EXPOSURE_DEV = "dev"           # 개발/테스트/빌드 도구 전용
EXPOSURE_ARCHIVED = "archived"  # archived/ 또는 은퇴 phase 에서만 사용

_EXPOSURES = (EXPOSURE_RUNTIME, EXPOSURE_DEV, EXPOSURE_ARCHIVED)

# --- 대응 결정 --------------------------------------------------------------
DECISION_PATCH_NOW = "PATCH_NOW"          # 즉시 대응(SLA 짧음)
DECISION_SCHEDULED = "SCHEDULED"          # 정해진 시한 내 계획 대응
DECISION_MONITOR = "MONITOR"              # 긴급도 없음 — 추적만
DECISION_OUT_OF_SCOPE = "OUT_OF_SCOPE"    # SECURITY.md 범위 밖

# 심각도 → SLA(접수 확인 일수, 해결 시한 일수). HIGH 가 SECURITY.md 기준선.
_SEVERITY_SLA: dict[str, tuple[int, int]] = {
    SEVERITY_CRITICAL: (1, 7),
    SEVERITY_HIGH: (3, 14),
    SEVERITY_MEDIUM: (7, 30),
    SEVERITY_LOW: (14, 90),
    SEVERITY_NONE: (0, 0),  # SLA 없음(정보성)
}


def severity_from_cvss(score: float) -> str:
    """CVSS v3.1 기반 점수를 정성 등급으로 결정적 변환한다.

    표준 절단점(NVD): 0.0 NONE · 0.1-3.9 LOW · 4.0-6.9 MEDIUM ·
    7.0-8.9 HIGH · 9.0-10.0 CRITICAL.

    Raises:
        ValueError: 점수가 [0.0, 10.0] 범위 밖.
    """
    if not 0.0 <= score <= 10.0:
        raise ValueError(f"CVSS 점수는 0.0~10.0 이어야 함: {score}")
    if score == 0.0:
        return SEVERITY_NONE
    if score < 4.0:
        return SEVERITY_LOW
    if score < 7.0:
        return SEVERITY_MEDIUM
    if score < 9.0:
        return SEVERITY_HIGH
    return SEVERITY_CRITICAL


def _demote(severity: str, steps: int) -> str:
    """심각도를 steps 단계 강등한다(NONE 미만으로 내려가지 않음)."""
    idx = _SEVERITY_ORDER.index(severity)
    return _SEVERITY_ORDER[max(0, idx - steps)]


def effective_severity(severity: str, exposure: str) -> str:
    """노출을 반영한 *유효* 심각도.

    개발 전용(dev) 노출은 프로덕션 경로가 아니므로 한 단계 강등해 대응한다
    (공급망 위험은 남으므로 무시하지 않고 완화만). runtime 은 그대로,
    archived 는 별도 처리(이 함수는 SLA 계산용 유효 등급만 반환).
    """
    if exposure == EXPOSURE_DEV:
        return _demote(severity, 1)
    return severity


@dataclass(frozen=True)
class CveReport:
    """평가 대상 CVE 한 건(불변).

    Attributes:
        cve_id: CVE 식별자(예: ``CVE-2025-12345``).
        package: 영향 받는 패키지/액션 이름.
        cvss_score: CVSS v3.1 기반 점수 [0.0, 10.0].
        exposure: ``runtime``·``dev``·``archived`` 중 하나.
        fix_available: 상류에 수정 버전이 존재하는지.
        fixed_version: 수정 버전(있으면). 핀 갱신 절차 근거.
    """

    cve_id: str
    package: str
    cvss_score: float
    exposure: str
    fix_available: bool = True
    fixed_version: str | None = None

    def __post_init__(self) -> None:
        if not self.cve_id.strip():
            raise ValueError("cve_id 는 비어 있을 수 없음")
        if not self.package.strip():
            raise ValueError("package 는 비어 있을 수 없음")
        if not 0.0 <= self.cvss_score <= 10.0:
            raise ValueError(
                f"cvss_score 는 0.0~10.0 이어야 함: {self.cvss_score}")
        if self.exposure not in _EXPOSURES:
            raise ValueError(
                f"알 수 없는 노출 {self.exposure!r} "
                f"(허용: {', '.join(_EXPOSURES)})")
        if self.fix_available and not (self.fixed_version or "").strip():
            raise ValueError("fix_available=True 면 fixed_version 이 필요함")
        if not self.fix_available and (self.fixed_version or "").strip():
            raise ValueError("fix_available=False 면 fixed_version 은 None")

    @property
    def severity(self) -> str:
        return severity_from_cvss(self.cvss_score)


@dataclass(frozen=True)
class CveResponse:
    """평가 결과(불변).

    Attributes:
        decision: 대응 결정(PATCH_NOW·SCHEDULED·MONITOR·OUT_OF_SCOPE).
        severity: CVSS 기반 원 심각도.
        ack_days: 접수 확인 SLA(일). SLA 없으면 None.
        remediate_days: 해결 시한 SLA(일). SLA 없으면 None.
        pin_refresh_required: requirements.lock.txt 핀 갱신이 필요한지.
        reasons: 결정 근거.
    """

    decision: str
    severity: str
    ack_days: int | None
    remediate_days: int | None
    pin_refresh_required: bool
    reasons: tuple[str, ...]

    def summary(self) -> str:
        """사람이 읽는 한 줄 요약."""
        if self.remediate_days is None:
            sla = "SLA 없음"
        else:
            sla = f"접수 {self.ack_days}일·해결 {self.remediate_days}일"
        pin = " · 핀 갱신 필요" if self.pin_refresh_required else ""
        return (f"{self.decision} ({self.severity}, {sla}{pin}): "
                f"{'; '.join(self.reasons)}")


def assess(report: CveReport) -> CveResponse:
    """단일 CVE 에 대한 대응 결정·SLA·핀 갱신 필요를 결정적으로 산출한다.

    결정 순서(먼저 매칭되는 규칙이 결과):
        1. archived 노출 → OUT_OF_SCOPE(SECURITY.md "Out of Scope"). SLA 없음.
        2. severity NONE → MONITOR(정보성). SLA 없음.
        3. dev 강등으로 유효 심각도 NONE(예: LOW·dev) → MONITOR. SLA 없음.
        4. 유효 심각도 CRITICAL/HIGH → PATCH_NOW.
        5. 그 외(MEDIUM/LOW) → SCHEDULED.

    SLA 는 *유효* 심각도(dev 한 단계 강등 반영) 기준. 핀 갱신은 수정 버전이
    존재하고(fix_available) 노출이 핀 대상(runtime·dev)일 때만 필요 —
    상류 수정이 없으면 핀을 올릴 수 없으므로 사람이 완화책을 적용한다.
    """
    severity = report.severity

    if report.exposure == EXPOSURE_ARCHIVED:
        return CveResponse(
            DECISION_OUT_OF_SCOPE, severity, None, None, False,
            ("archived/은퇴 phase 노출 — SECURITY.md 범위 밖, 추적만",),
        )

    if severity == SEVERITY_NONE:
        return CveResponse(
            DECISION_MONITOR, severity, None, None, False,
            ("CVSS 0.0(NONE) — 정보성, 긴급 대응 불필요",),
        )

    eff = effective_severity(severity, report.exposure)
    # dev 강등으로 유효 등급이 NONE 이 되면(예: LOW·dev) 긴급도 소멸 — MONITOR.
    # NONE 경로와 동일하게 SLA 없음·핀 갱신 없음으로 일관 처리.
    if eff == SEVERITY_NONE:
        return CveResponse(
            DECISION_MONITOR, severity, None, None, False,
            (f"dev 노출 — 유효 심각도 {severity}→{eff} 강등, 추적만",),
        )

    ack_days, remediate_days = _SEVERITY_SLA[eff]
    # 여기서 eff 는 LOW 이상(위에서 NONE 조기 반환). 노출은 runtime·dev(둘 다 핀 대상).
    pin_refresh = report.fix_available

    reasons: list[str] = []
    if eff != severity:
        reasons.append(f"dev 노출 — 유효 심각도 {severity}→{eff} 강등")
    if report.fix_available:
        reasons.append(f"수정 버전 {report.fixed_version} 으로 핀 갱신")
    else:
        reasons.append("상류 수정 없음 — 완화책 적용 후 패치 추적(핀 갱신 보류)")

    if eff in (SEVERITY_CRITICAL, SEVERITY_HIGH):
        decision = DECISION_PATCH_NOW
    else:
        decision = DECISION_SCHEDULED

    return CveResponse(
        decision, severity, ack_days, remediate_days, pin_refresh,
        tuple(reasons),
    )


# 정책 매트릭스. (severity, exposure) → decision.
# assess() 의 권위 있는 규칙을 사람이 한눈에 볼 수 있게 표로 투영한 것일 뿐,
# 결정은 항상 assess() 가 내린다(중복 로직 아님 — 테스트가 일치 강제).
# archived 는 항상 OUT_OF_SCOPE 이므로 매트릭스는 runtime·dev 만 다룬다.
def _matrix_decision(severity: str, exposure: str) -> str:
    """매트릭스 생성용 결정(fix_available 무관 — 결정은 심각도에만 의존)."""
    if severity == SEVERITY_NONE:
        return DECISION_MONITOR
    eff = effective_severity(severity, exposure)
    if eff == SEVERITY_NONE:  # LOW·dev 강등 바닥 — assess() 와 동일하게 MONITOR.
        return DECISION_MONITOR
    if eff in (SEVERITY_CRITICAL, SEVERITY_HIGH):
        return DECISION_PATCH_NOW
    return DECISION_SCHEDULED


POLICY_MATRIX: dict[tuple[str, str], str] = {
    (severity, exposure): _matrix_decision(severity, exposure)
    for severity in (
        SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM,
        SEVERITY_LOW, SEVERITY_NONE,
    )
    for exposure in (EXPOSURE_RUNTIME, EXPOSURE_DEV)
}


def policy_manifest() -> dict[str, Any]:
    """정책을 JSON 직렬화 가능한 매니페스트로 굳힌다."""
    return {
        "schema": "sdacs-cve-response-policy",
        "version": "1.0",
        "decisions": [
            DECISION_PATCH_NOW, DECISION_SCHEDULED,
            DECISION_MONITOR, DECISION_OUT_OF_SCOPE,
        ],
        "severities": list(reversed(_SEVERITY_ORDER)),
        "exposures": list(_EXPOSURES),
        "sla_by_severity": {
            sev: {"ack_days": ack, "remediate_days": rem}
            for sev, (ack, rem) in _SEVERITY_SLA.items()
        },
        "baseline": (
            f"SECURITY.md: 외부 ack 7d·remediation 14d. "
            f"HIGH 내부 SLA: ack {_SEVERITY_SLA[SEVERITY_HIGH][0]}d / "
            f"remediation {_SEVERITY_SLA[SEVERITY_HIGH][1]}d "
            f"(해결 14d 가 SECURITY.md 상한과 일치)"
        ),
        "advisory_only": True,
        "matrix": [
            {"severity": sev, "exposure": exp, "decision": decision}
            for (sev, exp), decision in POLICY_MATRIX.items()
        ],
    }


# 정책 동작을 보이는 결정적 예시.
_DEMO_REPORTS: tuple[CveReport, ...] = (
    CveReport("CVE-2025-0001", "numpy", 9.8, EXPOSURE_RUNTIME,
              fixed_version="1.26.4"),
    CveReport("CVE-2025-0002", "pyyaml", 7.5, EXPOSURE_RUNTIME,
              fixed_version="6.0.3"),
    CveReport("CVE-2025-0003", "playwright", 8.1, EXPOSURE_DEV,
              fixed_version="1.60.0"),
    CveReport("CVE-2025-0004", "matplotlib", 5.3, EXPOSURE_RUNTIME,
              fixed_version="3.10.9"),
    CveReport("CVE-2025-0005", "requests", 6.1, EXPOSURE_RUNTIME,
              fix_available=False),
    CveReport("CVE-2025-0006", "old-lib", 9.1, EXPOSURE_ARCHIVED,
              fixed_version="2.0.0"),
)


def _cmd_policy() -> None:
    print("CVE 대응 정책 매트릭스 (수정 버전 존재 전제, archived → OUT_OF_SCOPE)")
    print(f"{'SEVERITY':<10}{'EXPOSURE':<10}{'DECISION':<12}SLA(접수/해결 일)")
    for (severity, exposure), decision in POLICY_MATRIX.items():
        eff = effective_severity(severity, exposure)
        ack, rem = _SEVERITY_SLA[eff]
        sla = "-" if rem == 0 else f"{ack}/{rem}"
        print(f"{severity:<10}{exposure:<10}{decision:<12}{sla}")
    print("\n게이트: archived 노출·NONE → SLA 없음. SLA 는 dev 강등 반영 유효 등급 기준.")


def _cmd_demo() -> None:
    print("예시 평가:")
    for report in _DEMO_REPORTS:
        response = assess(report)
        print(f"  {report.cve_id} {report.package:<12} "
              f"CVSS {report.cvss_score:<4} {response.summary()}")


_KNOWN_FLAGS = ("--policy", "--demo", "--manifest")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    unknown = [a for a in args if a not in _KNOWN_FLAGS]
    if unknown:
        print(f"알 수 없는 인자: {' '.join(unknown)}", file=sys.stderr)
        print(f"사용법: {' | '.join(_KNOWN_FLAGS)}", file=sys.stderr)
        return 2
    if "--manifest" in args:
        print(json.dumps(policy_manifest(), ensure_ascii=False, indent=2))
        return 0
    if "--demo" in args:
        _cmd_demo()
        return 0
    _cmd_policy()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

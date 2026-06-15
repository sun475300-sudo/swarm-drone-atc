"""Phase 311 (GENESIS): KISA CSAP 클라우드 보안인증 자가진단 자동화.

과학기술정보통신부·KISA 「클라우드컴퓨팅서비스 보안인증제(CSAP)」 정보보호 기준의
통제분야(보호대책 영역)에 정렬한 **자가진단 도구**다. 운영자가 통제항목별 이행
상태를 입력하면, 외부 호출 없이 영역별 이행률과 종합 준비도를 결정적으로 산출한다.

본 모듈은 공식 인증 심사를 대체하지 않으며, 인증 신청 전 갭을 파악하기 위한
대표 통제항목 카탈로그(``DEFAULT_CATALOG``)를 제공한다. 카탈로그는 CSAP 정보보호
기준의 14개 통제분야 구조를 따르되, 운영자가 자체 항목으로 교체·확장할 수 있다.

이행 상태 4종(결정적 점수):
  - IMPLEMENTED      이행      → 분모·분자 모두 포함
  - PARTIAL          부분이행  → 분모 포함, 분자 0.5
  - NOT_IMPLEMENTED  미이행    → 분모 포함, 분자 0
  - NOT_APPLICABLE   해당없음  → 분모·분자 모두 제외
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

STANDARD = "과학기술정보통신부·KISA 클라우드 보안인증제(CSAP) 정보보호 기준"

# 종합 이행률 기준 준비도 판정 임계값(자가진단 권고 기준)
READY_THRESHOLD = 0.95  # 신청 권장
PARTIAL_THRESHOLD = 0.80  # 보완 후 신청


class Status(str, Enum):
    """통제항목 이행 상태."""

    IMPLEMENTED = "이행"
    PARTIAL = "부분이행"
    NOT_IMPLEMENTED = "미이행"
    NOT_APPLICABLE = "해당없음"


# CSAP 정보보호 기준 14개 통제분야 × 대표 통제항목 카탈로그.
# {분야코드: (분야명, (통제항목, ...))}
DEFAULT_CATALOG: dict[str, tuple[str, tuple[str, ...]]] = {
    "1": (
        "정보보호 정책 및 조직",
        (
            "정보보호 정책 수립·승인·공표",
            "정보보호 조직 및 역할·책임 정의",
            "정책 정기 검토·개정 절차",
        ),
    ),
    "2": (
        "인적 보안",
        (
            "임직원 보안서약 및 직무분리",
            "정기 정보보호 교육·훈련",
            "퇴직·직무변경 시 권한 회수",
        ),
    ),
    "3": (
        "자산 관리",
        (
            "정보자산 식별·분류·목록 관리",
            "자산 중요도 등급 부여",
            "매체 반출입·폐기 통제",
        ),
    ),
    "4": (
        "서비스 공급망 관리",
        (
            "외부 위탁·공급자 보안 요구사항 계약 반영",
            "공급망 보안 점검·평가",
        ),
    ),
    "5": (
        "침해사고 관리",
        (
            "침해사고 대응 절차·체계 수립",
            "사고 탐지·보고·기록 관리",
            "모의훈련 정기 수행",
        ),
    ),
    "6": (
        "위험 관리",
        (
            "위험평가 방법론 수립·정기 수행",
            "위험처리 계획 및 잔여위험 승인",
        ),
    ),
    "7": (
        "정보보호 대책 채택·관리",
        (
            "보호대책 이행계획 수립·관리",
            "이행 점검 및 미흡사항 조치",
        ),
    ),
    "8": (
        "접근 통제",
        (
            "사용자 식별·인증·권한 관리",
            "관리자 접근 다중인증 적용",
            "최소권한·접근기록 검토",
        ),
    ),
    "9": (
        "암호화 적용",
        (
            "전송·저장 데이터 암호화",
            "암호키 생성·보관·폐기 관리",
        ),
    ),
    "10": (
        "도입·개발 보안",
        (
            "보안 요구사항 설계 반영",
            "개발·운영 환경 분리",
            "소스코드 보안 점검",
        ),
    ),
    "11": (
        "운영 보안",
        (
            "변경·패치 관리 절차",
            "로그 수집·보관·검토",
            "백업 및 복구 시험",
        ),
    ),
    "12": (
        "서비스 보안관리",
        (
            "이용자 데이터 분리·격리",
            "서비스 가용성·성능 모니터링",
        ),
    ),
    "13": (
        "물리적 보안",
        (
            "전산실 출입통제·CCTV",
            "전원·항온항습 등 설비 보호",
        ),
    ),
    "14": (
        "재해 복구",
        (
            "BCP/DRP 수립 및 RTO·RPO 정의",
            "재해복구 시험 정기 수행",
        ),
    ),
}


@dataclass(frozen=True)
class ControlResult:
    """단일 통제항목 자가진단 결과."""

    domain_code: str
    domain_name: str
    control: str
    status: Status


@dataclass(frozen=True)
class DomainScore:
    """통제분야별 이행률 집계."""

    code: str
    name: str
    applicable: int  # 해당없음 제외 항목 수
    earned: float  # 이행 1.0 + 부분이행 0.5 합
    rate: float  # earned / applicable (분모 0이면 1.0)


@dataclass(frozen=True)
class Assessment:
    """CSAP 자가진단 종합 판정."""

    domains: tuple[DomainScore, ...]
    overall_rate: float
    verdict: str  # "신청 권장" | "보완 후 신청" | "준비 부족"
    weak_domains: tuple[str, ...]  # 종합 이하 분야 코드


def _status_weight(status: Status) -> tuple[int, float]:
    """이행 상태를 (분모 기여, 분자 기여)로 환산한다."""
    if status is Status.NOT_APPLICABLE:
        return 0, 0.0
    if status is Status.IMPLEMENTED:
        return 1, 1.0
    if status is Status.PARTIAL:
        return 1, 0.5
    return 1, 0.0  # NOT_IMPLEMENTED


def _validate(
    responses: dict[str, dict[str, Status]],
    catalog: dict[str, tuple[str, tuple[str, ...]]],
) -> list[str]:
    """응답이 카탈로그 구조와 일치하는지 검증한다(시스템 경계 검증)."""
    errors: list[str] = []
    for code, controls in responses.items():
        if code not in catalog:
            errors.append(f"미정의 통제분야 코드: {code}")
            continue
        valid = set(catalog[code][1])
        for control in controls:
            if control not in valid:
                errors.append(f"[{code}] 미정의 통제항목: {control}")
    return errors


def assess_csap(
    responses: dict[str, dict[str, Status]],
    catalog: dict[str, tuple[str, tuple[str, ...]]] | None = None,
) -> Assessment:
    """통제분야별 응답으로부터 CSAP 자가진단 결과를 결정적으로 산출한다.

    ``responses`` 는 ``{분야코드: {통제항목: Status}}`` 형태다. 카탈로그에 있으나
    응답이 없는 항목은 ``NOT_IMPLEMENTED`` 로 간주한다(보수적 평가).
    """
    catalog = catalog or DEFAULT_CATALOG
    errors = _validate(responses, catalog)
    if errors:
        raise ValueError("CSAP 자가진단 입력 검증 실패: " + "; ".join(errors))

    domains: list[DomainScore] = []
    total_applicable = 0
    total_earned = 0.0
    for code, (name, controls) in catalog.items():
        given = responses.get(code, {})
        applicable = 0
        earned = 0.0
        for control in controls:
            status = given.get(control, Status.NOT_IMPLEMENTED)
            denom, numer = _status_weight(status)
            applicable += denom
            earned += numer
        rate = 1.0 if applicable == 0 else earned / applicable
        domains.append(DomainScore(code, name, applicable, earned, round(rate, 4)))
        total_applicable += applicable
        total_earned += earned

    overall = 1.0 if total_applicable == 0 else total_earned / total_applicable
    overall = round(overall, 4)
    if overall >= READY_THRESHOLD:
        verdict = "신청 권장"
    elif overall >= PARTIAL_THRESHOLD:
        verdict = "보완 후 신청"
    else:
        verdict = "준비 부족"

    weak = tuple(d.code for d in domains if d.rate < overall)
    return Assessment(tuple(domains), overall, verdict, weak)


def build_responses(
    results: list[ControlResult],
) -> dict[str, dict[str, Status]]:
    """``ControlResult`` 목록을 ``assess_csap`` 입력 형태로 변환한다."""
    out: dict[str, dict[str, Status]] = {}
    for r in results:
        out.setdefault(r.domain_code, {})[r.control] = r.status
    return out


def build_report(
    responses: dict[str, dict[str, Status]],
    catalog: dict[str, tuple[str, tuple[str, ...]]] | None = None,
) -> dict[str, Any]:
    """CSAP 자가진단 보고서 데이터를 결정적으로 구성한다."""
    catalog = catalog or DEFAULT_CATALOG
    assessment = assess_csap(responses, catalog)
    total_items = sum(len(controls) for _, controls in catalog.values())
    return {
        "standard": STANDARD,
        "total_controls": total_items,
        "domains": [
            {
                "code": d.code,
                "name": d.name,
                "applicable": d.applicable,
                "earned": round(d.earned, 2),
                "rate": d.rate,
            }
            for d in assessment.domains
        ],
        "assessment": {
            "overall_rate": assessment.overall_rate,
            "verdict": assessment.verdict,
            "weak_domains": list(assessment.weak_domains),
        },
    }


def export_json(report: dict[str, Any]) -> str:
    """자가진단 보고서를 UTF-8 JSON 문자열로 직렬화한다."""
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)


def export_text(report: dict[str, Any]) -> str:
    """자가진단 보고서를 사람이 읽는 한국어 양식 텍스트로 변환한다."""
    asm = report["assessment"]
    lines = [
        "═══ CSAP 클라우드 보안인증 자가진단 보고서 ═══",
        "",
        f"근거: {report['standard']}",
        f"통제항목 수: {report['total_controls']} 개",
        "",
        "[통제분야별 이행률]",
    ]
    for d in report["domains"]:
        pct = round(d["rate"] * 100, 1)
        lines.append(f"  [{d['code']:>2}] {d['name']}: {pct}% ({d['applicable']} 항목)")
    lines += [
        "",
        "[종합 판정]",
        f"  종합 이행률: {round(asm['overall_rate'] * 100, 1)}%",
        f"  준비도: {asm['verdict']}",
    ]
    if asm["weak_domains"]:
        lines.append(f"  보완 우선 분야: {', '.join(asm['weak_domains'])}")
    return "\n".join(lines)

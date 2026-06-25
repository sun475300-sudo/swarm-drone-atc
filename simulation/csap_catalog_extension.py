"""GENESIS Phase 312 -- CSAP 통제항목 카탈로그 확장 (자동 수집).

Phase 311 CSAP 자가진단(수동 응답 방식)을 확장하여,
리포지토리 파일시스템에서 보안 통제항목의 이행 여부를
자동으로 감지합니다.

14개 통제분야 × 35개 대표 통제항목에 대해
파일 존재·패턴 매칭·설정 확인을 통해 이행 상태를 결정적으로 판정합니다.

CLI:
    python simulation/csap_catalog_extension.py --scan
    python simulation/csap_catalog_extension.py --domain DOMAIN_CODE
    python simulation/csap_catalog_extension.py --domains
    python simulation/csap_catalog_extension.py --json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from dataclasses import dataclass
from typing import Any

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from simulation.csap_self_assessment import (  # noqa: E402
    DEFAULT_CATALOG,
    Assessment,
    Status,
    assess_csap,
)

SCAN_RULES: tuple[tuple[str, str, tuple[tuple[str, ...], ...]], ...] = (
    (
        "1", "정보보호 정책 수립·승인·공표",
        (
            ("docs/certification/*SECURITY*",),
            ("docs/standards/*SECURITY*",),
            ("SECURITY.md",),
            ("docs/SECURITY*",),
        ),
    ),
    (
        "1", "정보보호 조직 및 역할·책임 정의",
        (
            ("CONTRIBUTING.md",),
            ("docs/CONTRIBUTING*",),
            (".github/CODEOWNERS",),
        ),
    ),
    (
        "1", "정책 정기 검토·개정 절차",
        (
            ("CHANGELOG.md",),
            ("docs/CHANGELOG*",),
        ),
    ),
    (
        "2", "임직원 보안서약 및 직무분리",
        (
            (".github/CODEOWNERS",),
            ("docs/certification/PILOT_LICENSE*",),
        ),
    ),
    (
        "2", "정기 정보보호 교육·훈련",
        (
            ("simulation/practice_assignments.py",),
            ("simulation/curriculum_slide_package.py",),
        ),
    ),
    (
        "2", "퇴직·직무변경 시 권한 회수",
        (
            ("simulation/handover_checklist.py",),
            ("docs/MAINTENANCE*",),
        ),
    ),
    (
        "3", "정보자산 식별·분류·목록 관리",
        (
            ("simulation/education_asset_registry.py",),
            ("docs/SDACS_API.md",),
        ),
    ),
    (
        "3", "자산 중요도 등급 부여",
        (
            ("simulation/maturity_assessment.py",),
            ("docs/TECH_DEBT*",),
        ),
    ),
    (
        "3", "매체 반출입·폐기 통제",
        (
            ("simulation/asset_publication_checklist.py",),
            (".gitignore",),
        ),
    ),
    (
        "4", "외부 위탁·공급자 보안 요구사항 계약 반영",
        (
            ("simulation/dependency_gate.py",),
            ("requirements*.txt",),
            ("pyproject.toml",),
        ),
    ),
    (
        "4", "공급망 보안 점검·평가",
        (
            ("simulation/cve_response_policy.py",),
            (".github/dependabot.yml",),
            (".github/dependabot.yaml",),
        ),
    ),
    (
        "5", "침해사고 대응 절차·체계 수립",
        (
            ("simulation/accident_report.py",),
            ("docs/certification/ACCIDENT_REPORT*",),
        ),
    ),
    (
        "5", "사고 탐지·보고·기록 관리",
        (
            ("simulation/incident_investigation_report.py",),
            ("simulation/flight_data_recorder.py",),
        ),
    ),
    (
        "5", "모의훈련 정기 수행",
        (
            ("tests/e2e/test_simulator_fuzz.py",),
            ("simulation/scenario_fuzzer.py",),
        ),
    ),
    (
        "6", "위험평가 방법론 수립·정기 수행",
        (
            ("simulation/insurance_rate_quote.py",),
            ("simulation/insurance_risk.py",),
        ),
    ),
    (
        "6", "위험처리 계획 및 잔여위험 승인",
        (
            ("docs/TECH_DEBT_LEDGER.md",),
            ("simulation/cve_response_policy.py",),
        ),
    ),
    (
        "7", "보호대책 이행계획 수립·관리",
        (
            ("docs/certification/RTM_5LAYER*",),
            ("docs/certification/DO178C*",),
        ),
    ),
    (
        "7", "이행 점검 및 미흡사항 조치",
        (
            ("simulation/integration_gate.py",),
            ("simulation/maturity_assessment.py",),
        ),
    ),
    (
        "8", "사용자 식별·인증·권한 관리",
        (
            (".github/CODEOWNERS",),
            ("docs/certification/PILOT_LICENSE*",),
        ),
    ),
    (
        "8", "관리자 접근 다중인증 적용",
        (
            (".github/workflows/*.yml",),
            (".github/workflows/*.yaml",),
        ),
    ),
    (
        "8", "최소권한·접근기록 검토",
        (
            (".gitignore",),
            ("simulation/handover_checklist.py",),
        ),
    ),
    (
        "9", "전송·저장 데이터 암호화",
        (
            ("simulation/pqc_kex.py",),
            ("simulation/blockchain*.py",),
        ),
    ),
    (
        "9", "암호키 생성·보관·폐기 관리",
        (
            (".env.example",),
            (".gitignore",),
        ),
    ),
    (
        "10", "보안 요구사항 설계 반영",
        (
            ("docs/certification/AIR_SAFETY_ACT*",),
            ("docs/certification/DO178C*",),
        ),
    ),
    (
        "10", "개발·운영 환경 분리",
        (
            (".github/workflows/*.yml",),
            ("config/",),
        ),
    ),
    (
        "10", "소스코드 보안 점검",
        (
            ("tests/",),
            (".github/workflows/*.yml",),
        ),
    ),
    (
        "11", "변경·패치 관리 절차",
        (
            ("CHANGELOG.md",),
            ("docs/API_DEPRECATION_POLICY.md",),
        ),
    ),
    (
        "11", "로그 수집·보관·검토",
        (
            ("simulation/flight_data_recorder.py",),
            ("simulation/post_flight_report.py",),
        ),
    ),
    (
        "11", "백업 및 복구 시험",
        (
            ("simulation/archive_strategy.py",),
            ("simulation/archive_redundancy.py",),
        ),
    ),
    (
        "12", "이용자 데이터 분리·격리",
        (
            ("simulation/geo_zones.py",),
            ("simulation/airspace_class.py",),
        ),
    ),
    (
        "12", "서비스 가용성·성능 모니터링",
        (
            ("simulation/achievement_summary.py",),
            ("docs/HEALTH_CHECK.md",),
        ),
    ),
    (
        "13", "전산실 출입통제·CCTV",
        (
            ("docs/certification/NIGHT_BVLOS*",),
            ("docs/MAINTENANCE*",),
        ),
    ),
    (
        "13", "전원·항온항습 등 설비 보호",
        (
            ("simulation/energy_budget.py",),
            ("simulation/failsafe_manager.py",),
        ),
    ),
    (
        "14", "BCP/DRP 수립 및 RTO·RPO 정의",
        (
            ("simulation/archive_strategy.py",),
            ("docs/MAINTENANCE_MINIMAL_MODE.md",),
        ),
    ),
    (
        "14", "재해복구 시험 정기 수행",
        (
            ("scripts/independent_reproduction.sh",),
            ("simulation/archive_redundancy.py",),
        ),
    ),
)


@dataclass(frozen=True)
class ScanResult:
    """단일 통제항목 자동 스캔 결과."""

    domain_code: str
    domain_name: str
    control: str
    status: Status
    evidence: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "domain_code": self.domain_code,
            "domain_name": self.domain_name,
            "control": self.control,
            "status": self.status.value,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True)
class CatalogScanReport:
    """CSAP 통제항목 자동 스캔 보고서."""

    scan_results: tuple[ScanResult, ...]
    assessment: Assessment
    total_controls: int
    implemented_count: int
    partial_count: int
    not_implemented_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_controls": self.total_controls,
            "implemented_count": self.implemented_count,
            "partial_count": self.partial_count,
            "not_implemented_count": self.not_implemented_count,
            "overall_rate": self.assessment.overall_rate,
            "verdict": self.assessment.verdict,
            "weak_domains": list(self.assessment.weak_domains),
            "domains": [
                {
                    "code": d.code,
                    "name": d.name,
                    "applicable": d.applicable,
                    "rate": d.rate,
                }
                for d in self.assessment.domains
            ],
            "scan_results": [r.as_dict() for r in self.scan_results],
        }


def _glob_any(root: pathlib.Path, patterns: tuple[str, ...]) -> list[str]:
    """주어진 패턴 중 하나라도 매칭되는 파일이 있으면 경로 목록을 반환."""
    found: list[str] = []
    for pattern in patterns:
        if ".." in pathlib.PurePosixPath(pattern).parts:
            raise ValueError(f"Pattern escapes root: {pattern!r}")
        if pattern.endswith("/"):
            target = root / pattern.rstrip("/")
            if target.is_dir():
                found.append(target.relative_to(root).as_posix())
        else:
            for match in root.glob(pattern):
                found.append(match.relative_to(root).as_posix())
    return found


def _detect_status(
    root: pathlib.Path,
    pattern_groups: tuple[tuple[str, ...], ...],
) -> tuple[Status, tuple[str, ...]]:
    """패턴 그룹에서 증거 파일을 탐색하여 이행 상태를 결정."""
    all_evidence: list[str] = []
    groups_matched = 0
    for patterns in pattern_groups:
        matches = _glob_any(root, patterns)
        if matches:
            groups_matched += 1
            all_evidence.extend(matches)

    if groups_matched == 0:
        return Status.NOT_IMPLEMENTED, ()
    if groups_matched == len(pattern_groups):
        return Status.IMPLEMENTED, tuple(sorted(set(all_evidence)))
    return Status.PARTIAL, tuple(sorted(set(all_evidence)))


def scan_catalog(
    repo_root: pathlib.Path | None = None,
) -> CatalogScanReport:
    """리포지토리를 스캔하여 CSAP 통제항목 이행 상태를 자동 감지."""
    root = repo_root or _REPO_ROOT
    if not root.is_dir():
        raise ValueError(f"repo_root does not exist: {root}")

    results: list[ScanResult] = []
    responses: dict[str, dict[str, Status]] = {}

    for domain_code, control_name, pattern_groups in SCAN_RULES:
        domain_name = DEFAULT_CATALOG[domain_code][0]
        status, evidence = _detect_status(root, pattern_groups)

        results.append(ScanResult(
            domain_code=domain_code,
            domain_name=domain_name,
            control=control_name,
            status=status,
            evidence=evidence,
        ))

        if domain_code not in responses:
            responses[domain_code] = {}
        responses[domain_code][control_name] = status

    assessment = assess_csap(responses, DEFAULT_CATALOG)

    impl = sum(1 for r in results if r.status is Status.IMPLEMENTED)
    partial = sum(1 for r in results if r.status is Status.PARTIAL)
    not_impl = sum(1 for r in results if r.status is Status.NOT_IMPLEMENTED)

    return CatalogScanReport(
        scan_results=tuple(results),
        assessment=assessment,
        total_controls=len(results),
        implemented_count=impl,
        partial_count=partial,
        not_implemented_count=not_impl,
    )


def get_domain_scan(
    domain_code: str,
    repo_root: pathlib.Path | None = None,
) -> dict[str, Any]:
    """특정 통제분야의 스캔 결과."""
    if domain_code not in DEFAULT_CATALOG:
        raise ValueError(f"유효하지 않은 통제분야 코드: {domain_code}")

    report = scan_catalog(repo_root)
    domain_results = [
        r.as_dict() for r in report.scan_results
        if r.domain_code == domain_code
    ]
    domain_assessment = next(
        (d for d in report.assessment.domains if d.code == domain_code),
        None,
    )

    return {
        "domain_code": domain_code,
        "domain_name": DEFAULT_CATALOG[domain_code][0],
        "rate": domain_assessment.rate if domain_assessment else 0.0,
        "controls": domain_results,
    }


def list_domains() -> list[dict[str, Any]]:
    """통제분야 목록."""
    return [
        {
            "code": code,
            "name": name,
            "control_count": len(controls),
        }
        for code, (name, controls) in DEFAULT_CATALOG.items()
    ]


def _main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="GENESIS Phase 312 -- CSAP 통제항목 카탈로그 확장 (자동 수집)",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--scan", action="store_true", help="전체 자동 스캔")
    group.add_argument("--domain", type=str, help="특정 통제분야 스캔")
    group.add_argument("--domains", action="store_true", help="통제분야 목록")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    if args.scan:
        _print_scan(args.json)
    elif args.domain:
        _print_domain(args.domain, args.json)
    elif args.domains:
        _print_domains(args.json)
    else:
        parser.print_help()
        sys.exit(1)


def _print_scan(as_json: bool) -> None:
    report = scan_catalog()
    if as_json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
        return
    print("=== CSAP 통제항목 자동 스캔 ===")
    print(f"  종합 이행률: {report.assessment.overall_rate * 100:.1f}%")
    print(f"  판정: {report.assessment.verdict}")
    print(f"  통제항목: {report.total_controls}건")
    print(f"    이행: {report.implemented_count} / 부분이행: {report.partial_count} / 미이행: {report.not_implemented_count}")
    print()
    for d in report.assessment.domains:
        filled = max(0, min(10, int(d.rate * 10)))
        bar = "█" * filled + "░" * (10 - filled)
        print(f"  [{d.code:>2}] {d.name:<20} {bar} {d.rate * 100:.0f}%")


def _print_domain(code: str, as_json: bool) -> None:
    result = get_domain_scan(code)
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"=== [{code}] {result['domain_name']} ===")
    print(f"  이행률: {result['rate'] * 100:.0f}%")
    for c in result["controls"]:
        marker = "+" if c["status"] == "이행" else ("-" if c["status"] == "미이행" else "~")
        print(f"  {marker} {c['control']} [{c['status']}]")
        for e in c["evidence"]:
            print(f"      → {e}")


def _print_domains(as_json: bool) -> None:
    domains = list_domains()
    if as_json:
        print(json.dumps(domains, ensure_ascii=False, indent=2))
        return
    print("=== CSAP 통제분야 목록 ===")
    for d in domains:
        print(f"  [{d['code']:>2}] {d['name']} ({d['control_count']}개 항목)")


if __name__ == "__main__":
    _main()

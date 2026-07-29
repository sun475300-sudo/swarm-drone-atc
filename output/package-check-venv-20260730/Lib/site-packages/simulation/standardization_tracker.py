"""ODYSSEY Phase 470 — 표준화 기고 추적 대시보드.

Standards & Policy 트랙(Phase 461-480)이 산출하는 *표준화 기고* — ASTM·ISO·
GUTMA·EASA·국토부(K-드론)·KS 등 — 의 진행 상태를 단일 출처(SSoT)로 추적하고
대시보드/매니페스트로 굳힌다. Phase 465(표준 벤치마크 스위트)·466(텔레메트리
오픈 데이터 스키마)·467(사고 조사 데이터 표준)이 이미 공개 산출물을 만들었고,
461-464·471-480 이 다수의 기고를 *예정* 한다. 본 모듈은 그 기고들이 흩어져
관리되며 "어디까지 진행됐는지" 가 보이지 않던 공백을 메운다.

설계 원칙
--------
- **중복 없는 추적 계층**: 기고의 *내용* 은 산출물 파일(``docs/standards/*``·
  ``docs/schemas/*``)이 유일 출처다. 본 모듈은 내용을 복제하지 않고 진행 상태
  메타데이터(표준 기구·발신 Phase·상태·산출물 경로)만 보유하며 파일을 가리킨다.
- **검증 가능한 정직성**: ``PUBLISHED`` 이상으로 표시된 기고는 산출물 경로가
  실재 파일을 가리켜야 한다(``validate_registry`` 가 결정적으로 강제). 경로를
  명시한 모든 기고는 파일이 존재해야 한다 — 옮겨지거나 사라진 산출물을 위양성
  없이 잡아낸다.
- **단조 상태 모델**: PLANNED→DRAFTING→SUBMITTED→PUBLISHED→ADOPTED 의 순서형
  상태로 진행률을 정량화한다(가중 평균).

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python -m simulation.standardization_tracker --list       # 기고 요약 표
    python -m simulation.standardization_tracker --validate   # 레지스트리 정합성
    python -m simulation.standardization_tracker --manifest   # 매니페스트(JSON)
    python -m simulation.standardization_tracker --markdown   # 대시보드(Markdown)
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# 리포 루트 — 산출물 경로는 이 기준의 상대 경로로 보관한다.
_REPO_ROOT = Path(__file__).resolve().parent.parent

# 단조 진행 상태(순서형). 인덱스가 진행 가중치다.
STATUS_ORDER: tuple[str, ...] = (
    "PLANNED",    # 0 — 로드맵에 정의됐으나 착수 전
    "DRAFTING",   # 1 — 초안 작성 중
    "SUBMITTED",  # 2 — 기구/위원회에 제출됨
    "PUBLISHED",  # 3 — 공개 산출물 확정(리포 내 파일 존재)
    "ADOPTED",    # 4 — 표준/정책으로 채택됨
)
_STATUS_INDEX = {status: i for i, status in enumerate(STATUS_ORDER)}

# 이 상태 이상은 리포 내 산출물 파일을 반드시 동반해야 한다.
_REQUIRES_ARTIFACT_FROM = _STATUS_INDEX["PUBLISHED"]


@dataclass(frozen=True)
class Contribution:
    """표준화 기고 한 건의 진행 상태(불변).

    기고의 *내용* 은 ``artifact`` 가 가리키는 파일이 유일 출처이며, 본 객체는
    추적 메타데이터만 보유한다.

    Attributes:
        contribution_id: 안정 식별자 (STD-01..).
        body: 대상 표준 기구·정책 채널 (예: ``ASTM F38``, ``GUTMA``).
        title: 기고 제목.
        phase: 발신 로드맵 Phase 식별자 (예: ``ODYSSEY-465``).
        status: STATUS_ORDER 중 하나.
        artifact: 리포 루트 기준 산출물 상대 경로(없으면 None).
    """

    contribution_id: str
    body: str
    title: str
    phase: str
    status: str
    artifact: str | None = None

    def status_rank(self) -> int:
        """상태의 진행 순위(0=PLANNED .. 4=ADOPTED). 미지의 상태는 -1."""
        return _STATUS_INDEX.get(self.status, -1)

    def artifact_path(self) -> Path | None:
        """산출물의 절대 경로(없으면 None)."""
        return _REPO_ROOT / self.artifact if self.artifact else None

    def artifact_exists(self) -> bool:
        """산출물 파일이 실재하는지 여부(경로 미지정이면 False)."""
        path = self.artifact_path()
        return path is not None and path.is_file()


# 표준화 기고 레지스트리 — 로드맵에 문서화된 기고만, 결정적 순서.
# 산출물은 리포에 실재하는 파일만 명시한다(PUBLISHED 의 정직성 보장).
REGISTRY: tuple[Contribution, ...] = (
    Contribution(
        "STD-01", "SDACS 공개 표준", "공역 통합 표준 벤치마크 스위트 SDACS-SBS-10",
        "ODYSSEY-465", "PUBLISHED", "docs/standards/SDACS_BENCHMARK_SUITE.md",
    ),
    Contribution(
        "STD-02", "SDACS 공개 표준", "텔레메트리 오픈 데이터 스키마 (JSON Schema)",
        "ODYSSEY-466", "PUBLISHED", "docs/schemas/telemetry.schema.json",
    ),
    Contribution(
        "STD-03", "SDACS 공개 표준", "사고 조사 데이터 표준 양식",
        "ODYSSEY-467", "PUBLISHED", "docs/standards/INCIDENT_INVESTIGATION_REPORT.md",
    ),
    Contribution(
        "STD-04", "ASTM F38", "군집 관제 시험 방법 기고 초안",
        "ODYSSEY-461", "PLANNED", None,
    ),
    Contribution(
        "STD-05", "ISO/TC 20/SC 16", "UAS 표준 동향 추적 매트릭스",
        "ODYSSEY-462", "PLANNED", None,
    ),
    Contribution(
        "STD-06", "국토부 (K-드론)", "K-드론 시스템 고도화 정책 제안서",
        "ODYSSEY-463", "PLANNED", None,
    ),
    Contribution(
        "STD-07", "국가 안전 기준", "군집 비행 안전 기준 백서 (5계층 안전망 사례)",
        "ODYSSEY-464", "PLANNED", None,
    ),
    Contribution(
        "STD-08", "GUTMA", "U-space/UTM 상호운용 기고",
        "ODYSSEY-410", "PLANNED", None,
    ),
    Contribution(
        "STD-09", "EASA", "U-space 서비스 매핑",
        "ODYSSEY-401", "PLANNED", None,
    ),
    Contribution(
        "STD-10", "ASTM F3411", "Remote ID 방송 적합성 실증",
        "TRANSCENDENCE-270", "PLANNED", None,
    ),
)


@dataclass(frozen=True)
class ValidationResult:
    """레지스트리 검증 결과. errors 가 비면 정합하다.

    Phase 465/466/485 의 ``scenario_schema.ValidationResult`` 와 동일한 계약
    (is_valid·errors·warnings 튜플)을 따른다.
    """

    is_valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    def summary(self) -> str:
        """사람이 읽는 한 줄 요약을 반환한다."""
        if self.is_valid:
            base = "VALID"
        else:
            n = len(self.errors)
            base = f"INVALID ({n} {'error' if n == 1 else 'errors'})"
        if self.warnings:
            n = len(self.warnings)
            base += f" / {n} {'warning' if n == 1 else 'warnings'}"
        return base


def all_contributions() -> tuple[Contribution, ...]:
    """결정적 순서의 전체 레지스트리를 반환한다."""
    return REGISTRY


def get_contribution(contribution_id: str) -> Contribution:
    """식별자로 기고를 조회한다.

    Raises:
        KeyError: 알 수 없는 식별자.
    """
    for entry in REGISTRY:
        if entry.contribution_id == contribution_id:
            return entry
    raise KeyError(f"알 수 없는 기고 식별자: {contribution_id!r}")


def validate_registry(registry: tuple[Contribution, ...] = REGISTRY) -> ValidationResult:
    """레지스트리의 내부 정합성을 결정적으로 검증한다.

    검사 규칙:
        - 식별자 유일 (위반 → error).
        - 상태가 STATUS_ORDER 에 속함 (위반 → error).
        - body·title·phase 비어 있지 않음 (위반 → error).
        - PUBLISHED 이상은 산출물 경로 명시 + 파일 실재 (위반 → error).
        - 경로를 명시한 모든 기고는 파일이 실재 (위반 → error).
        - phase 가 ``TRACK-번호`` 형식 (위반 → warning).
    """
    errors: list[str] = []
    warnings: list[str] = []

    seen: set[str] = set()
    for entry in registry:
        cid = entry.contribution_id
        if cid in seen:
            errors.append(f"{cid}: 중복 식별자")
        seen.add(cid)

        if not cid.strip():
            errors.append("(이름 없음): 'contribution_id' 가 비어 있음")

        if entry.status not in _STATUS_INDEX:
            errors.append(
                f"{cid}: 알 수 없는 상태 {entry.status!r} "
                f"(허용: {', '.join(STATUS_ORDER)})"
            )
        for field_name in ("body", "title", "phase"):
            if not getattr(entry, field_name).strip():
                errors.append(f"{cid}: '{field_name}' 가 비어 있음")

        rank = entry.status_rank()
        if rank >= _REQUIRES_ARTIFACT_FROM:
            if not entry.artifact:
                errors.append(
                    f"{cid}: 상태 {entry.status} 는 산출물 경로가 필요함"
                )
            elif not entry.artifact_exists():
                errors.append(
                    f"{cid}: 산출물 없음 → {entry.artifact}"
                )
        elif entry.artifact and not entry.artifact_exists():
            # PUBLISHED 미만이라도 경로를 명시했으면 실재해야 한다.
            errors.append(f"{cid}: 산출물 없음 → {entry.artifact}")

        if "-" not in entry.phase or not entry.phase.split("-")[-1].isdigit():
            warnings.append(f"{cid}: phase 형식 비표준 → {entry.phase!r}")

    return ValidationResult(
        is_valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def status_rollup(registry: tuple[Contribution, ...] = REGISTRY) -> dict[str, int]:
    """상태별 기고 수를 STATUS_ORDER 순으로 집계한다(0 포함)."""
    counts = dict.fromkeys(STATUS_ORDER, 0)
    for entry in registry:
        if entry.status in counts:
            counts[entry.status] += 1
    return counts


def body_rollup(registry: tuple[Contribution, ...] = REGISTRY) -> dict[str, int]:
    """표준 기구별 기고 수를 첫 등장 순서로 집계한다."""
    counts: dict[str, int] = {}
    for entry in registry:
        counts[entry.body] = counts.get(entry.body, 0) + 1
    return counts


def progress(registry: tuple[Contribution, ...] = REGISTRY) -> float:
    """전체 진행률 [0,1] — 상태 순위의 가중 평균(ADOPTED 만점).

    빈 레지스트리는 0.0. 미지 상태(순위 -1)는 0 으로 클램프해 음수 진행률을
    방지한다.
    """
    if not registry:
        return 0.0
    max_rank = len(STATUS_ORDER) - 1
    total = sum(max(entry.status_rank(), 0) for entry in registry)
    return total / (len(registry) * max_rank)


def manifest(registry: tuple[Contribution, ...] = REGISTRY) -> dict[str, Any]:
    """JSON 직렬화 가능한 추적 매니페스트를 생성한다."""
    result = validate_registry(registry)
    return {
        "schema": "sdacs-standardization-tracker",
        "version": "1.0",
        "count": len(registry),
        "progress": round(progress(registry), 4),
        "is_valid": result.is_valid,
        "status_rollup": status_rollup(registry),
        "body_rollup": body_rollup(registry),
        "contributions": [
            {
                "contribution_id": entry.contribution_id,
                "body": entry.body,
                "title": entry.title,
                "phase": entry.phase,
                "status": entry.status,
                "status_rank": entry.status_rank(),
                "artifact": entry.artifact,
                "artifact_exists": entry.artifact_exists(),
            }
            for entry in registry
        ],
    }


def _escape_md(value: str) -> str:
    """Markdown 표 셀에서 파이프를 이스케이프해 표 깨짐을 막는다."""
    return value.replace("|", "\\|")


def markdown_table(registry: tuple[Contribution, ...] = REGISTRY) -> str:
    """대시보드용 Markdown 표를 생성한다(결정적)."""
    lines = [
        "| ID | 기구 | 기고 | Phase | 상태 | 산출물 |",
        "|---|---|---|---|:-:|---|",
    ]
    for entry in registry:
        artifact = _escape_md(entry.artifact) if entry.artifact else "—"
        lines.append(
            f"| {_escape_md(entry.contribution_id)} | {_escape_md(entry.body)} "
            f"| {_escape_md(entry.title)} | {_escape_md(entry.phase)} "
            f"| {entry.status} | {artifact} |"
        )
    pct = round(progress(registry) * 100, 1)
    lines.append("")
    lines.append(f"**진행률**: {pct}% ({len(registry)}건)")
    return "\n".join(lines)


def _cmd_list() -> None:
    print(f"표준화 기고 추적 — {len(REGISTRY)}건")
    print(f"{'ID':<8}{'BODY':<18}{'STATUS':<11}PHASE")
    for entry in REGISTRY:
        print(f"{entry.contribution_id:<8}{entry.body:<18}{entry.status:<11}{entry.phase}")
    print(f"\n진행률: {progress() * 100:.1f}%")


def _cmd_validate() -> int:
    result = validate_registry()
    for err in result.errors:
        print(f"ERROR  {err}", file=sys.stderr)
    for warn in result.warnings:
        print(f"WARN   {warn}")
    print(result.summary())
    return 0 if result.is_valid else 1


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if "--validate" in args:
        return _cmd_validate()
    if "--manifest" in args:
        print(json.dumps(manifest(), ensure_ascii=False, indent=2))
        return 0
    if "--markdown" in args:
        print(markdown_table())
        return 0
    _cmd_list()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

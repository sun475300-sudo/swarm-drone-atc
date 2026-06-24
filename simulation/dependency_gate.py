"""ODYSSEY Phase 481 — 의존성 자동 갱신 회귀 게이트 정책.

Continuum 트랙(Phase 481-500)의 첫 칸. 리포에는 Dependabot 이 만든 의존성
갱신 PR 이 다수 적체되어 있다(pip·npm·github-actions). "어떤 갱신을 회귀
테스트만 통과하면 자동 머지해도 되고, 어떤 갱신은 사람 리뷰가 필요한가" 를
사람이 매번 직관으로 판단하면 일관성이 없다. 본 모듈은 그 판단을 *결정적
정책*으로 명문화한다 — 같은 입력은 항상 같은 결정을 낸다.

설계 원칙
--------
- **정책은 코드, 코드는 정책**: 머지 결정 규칙을 문서(``docs/standards/
  DEPENDENCY_AUTOMERGE_POLICY.md``)와 본 평가기에 *한 번씩만* 적기 위해, 본
  모듈이 유일한 실행 가능 명세다. 문서는 본 모듈의 규칙을 서술할 뿐 중복
  로직을 두지 않는다.
- **자문이지 머지가 아님**: 본 모듈은 *결정을 권고*할 뿐 실제로 PR 을 머지
  하지 않는다(부수효과 0). CI/사람이 결정을 집행한다.
- **회귀 게이트 우선**: 어떤 버전 점프든 회귀 테스트 실패·머지 충돌이면
  무조건 BLOCK. 자동 머지는 게이트 통과가 필요조건이다.
- **SemVer 보수성**: MAJOR 점프와 다운그레이드는 자동 머지 불가. 런타임
  의존성의 MINOR 도 사람 리뷰. 자동 머지는 *깨질 가능성이 낮은* 변경에만.

무작위성 0 · 결정적 · 기존 모듈 무수정 순수 추가.

CLI:
    python -m simulation.dependency_gate --policy     # 정책 매트릭스 출력
    python -m simulation.dependency_gate --demo       # 예시 평가
    python -m simulation.dependency_gate --manifest   # 정책 매니페스트(JSON)
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from typing import Any

# 완전한 3성분 버전(꼬리 prerelease/build 허용) · 1~2성분 짧은 버전(꼬리 불가).
# prerelease/build 꼬리는 SemVer 상 *완전한* X.Y.Z 에만 붙으므로, "1-2-3" 같은
# 불완전 버전의 하이픈은 거부되어 BUMP_UNKNOWN → 사람 리뷰로 에스컬레이션된다.
_FULL_SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$")
_SHORT_VERSION = re.compile(r"^(\d+)(?:\.(\d+))?$")

# --- 버전 점프 분류 ---------------------------------------------------------
BUMP_MAJOR = "MAJOR"
BUMP_MINOR = "MINOR"
BUMP_PATCH = "PATCH"
BUMP_NONE = "NONE"            # 동일 버전(버전 변화 없음)
BUMP_DOWNGRADE = "DOWNGRADE"  # 역행
BUMP_UNKNOWN = "UNKNOWN"      # 파싱 불가

# --- 의존성 분류 ------------------------------------------------------------
CLASS_RUNTIME = "runtime"  # 런타임 동작에 직접 영향(numpy·simpy·dash 등)
CLASS_DEV = "dev"          # 개발/테스트 전용(pytest·playwright·electron-builder)
CLASS_CI = "ci"            # GitHub Actions 워크플로 액션

_DEP_CLASSES = (CLASS_RUNTIME, CLASS_DEV, CLASS_CI)

# --- 결정 ------------------------------------------------------------------
DECISION_AUTO_MERGE = "AUTO_MERGE"          # 게이트 통과 시 자동 머지 가능
DECISION_REVIEW_REQUIRED = "REVIEW_REQUIRED"  # 사람 리뷰 필요
DECISION_BLOCK = "BLOCK"                     # 머지 금지


@dataclass(frozen=True)
class SemVer:
    """SemVer 삼중항. 누락 성분은 0 으로 본다(``"4"`` → 4.0.0)."""

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, version: str) -> "SemVer | None":
        """버전 문자열을 파싱한다. 실패하면 None.

        허용:
            - 1~3개 숫자 성분(``"4"``·``"4.2"``·``"1.2.3"``), 누락분은 0.
            - 선행 ``v``/``V``.
            - prerelease/build 꼬리(``-``·``+`` 이후)는 *완전한 3성분 버전에만*
              허용하고 버린다(``"1.2.3-rc1"`` → 1.2.3).
        거부(→ None → BUMP_UNKNOWN → 사람 리뷰):
            - 비숫자 성분(``"1.x.0"``·``"latest"``).
            - 선행 0(``"01.0.0"``) — SemVer §2 위반.
            - 불완전 버전의 하이픈/꼬리(``"1-2-3"``·``"1.2-rc1"``).
        """
        text = version.strip()
        if text[:1] in ("v", "V"):
            text = text[1:]
        full = _FULL_SEMVER.match(text)
        if full:
            parts = full.group(1, 2, 3)
        else:
            short = _SHORT_VERSION.match(text)
            if short is None:
                return None
            parts = (short.group(1), short.group(2) or "0", "0")
        for part in parts:
            if len(part) > 1 and part[0] == "0":
                return None  # 선행 0 거부
        return cls(int(parts[0]), int(parts[1]), int(parts[2]))

    def as_tuple(self) -> tuple[int, int, int]:
        return (self.major, self.minor, self.patch)


def classify_bump(from_version: str, to_version: str) -> str:
    """두 버전 사이의 점프 종류를 결정적으로 분류한다."""
    a = SemVer.parse(from_version)
    b = SemVer.parse(to_version)
    if a is None or b is None:
        return BUMP_UNKNOWN
    if b.as_tuple() < a.as_tuple():
        return BUMP_DOWNGRADE
    if b.major != a.major:
        return BUMP_MAJOR
    if b.minor != a.minor:
        return BUMP_MINOR
    if b.patch != a.patch:
        return BUMP_PATCH
    return BUMP_NONE


@dataclass(frozen=True)
class RegressionGate:
    """갱신 PR 의 회귀 게이트 상태(불변).

    Attributes:
        tests_passed: 회귀 테스트 스위트 전체 통과 여부.
        coverage_ok: 커버리지 임계(80%) 충족 여부.
        has_conflicts: 대상 브랜치와 머지 충돌 존재 여부.
    """

    tests_passed: bool
    coverage_ok: bool
    has_conflicts: bool = False

    def is_green(self) -> bool:
        """자동 머지의 필요조건(충돌 없음 + 테스트·커버리지 통과)."""
        return self.tests_passed and self.coverage_ok and not self.has_conflicts


@dataclass(frozen=True)
class DependencyUpdate:
    """평가 대상 의존성 갱신 한 건(불변).

    Attributes:
        name: 패키지/액션 이름.
        ecosystem: ``pip``·``npm``·``github-actions``.
        from_version: 현재 버전.
        to_version: 제안 버전.
        dep_class: ``runtime``·``dev``·``ci`` 중 하나.
        gate: 회귀 게이트 상태.
    """

    name: str
    ecosystem: str
    from_version: str
    to_version: str
    dep_class: str
    gate: RegressionGate


@dataclass(frozen=True)
class GateDecision:
    """평가 결과(불변). decision 과 그 근거(reasons)."""

    decision: str
    bump: str
    reasons: tuple[str, ...]

    def summary(self) -> str:
        """사람이 읽는 한 줄 요약."""
        return f"{self.decision} ({self.bump}): {'; '.join(self.reasons)}"


def _auto_mergeable_bump(bump: str, dep_class: str) -> bool:
    """게이트 통과를 전제로, 이 점프·분류가 자동 머지 후보인지 판정.

    정책 매트릭스(게이트 GREEN 가정):
        - PATCH: 모든 분류 자동 머지.
        - MINOR: dev·ci 자동 머지, runtime 은 리뷰.
        - MAJOR·DOWNGRADE·NONE·UNKNOWN: 자동 머지 불가.
    """
    if bump == BUMP_PATCH:
        return True
    if bump == BUMP_MINOR:
        return dep_class in (CLASS_DEV, CLASS_CI)
    return False


def evaluate(update: DependencyUpdate) -> GateDecision:
    """단일 의존성 갱신에 대한 머지 결정을 결정적으로 산출한다.

    결정 순서(먼저 매칭되는 규칙이 결과):
        1. 알 수 없는 의존성 분류 → BLOCK(정책 적용 불가).
        2. 머지 충돌 → BLOCK.
        3. 회귀 테스트 실패 → BLOCK.  (게이트 우선: 다운그레이드라도 테스트가
           실패하면 본 규칙이 먼저 매칭되어 reason 은 테스트 실패를 가리킨다.
           bump 필드는 여전히 DOWNGRADE 로 보고된다.)
        4. 다운그레이드 → BLOCK(의도치 않은 역행 차단).
        5. 버전 파싱 불가(UNKNOWN) → REVIEW_REQUIRED(평가 불가, 사람이 판단).
        6. 버전 변화 없음(NONE) → REVIEW_REQUIRED(메타/해시 변경 의심).
        7. 커버리지 미달 → REVIEW_REQUIRED(자동 머지 자격 박탈).
        8. 자동 머지 후보 점프 → AUTO_MERGE, 아니면 REVIEW_REQUIRED.
    """
    reasons: list[str] = []
    bump = classify_bump(update.from_version, update.to_version)

    if update.dep_class not in _DEP_CLASSES:
        return GateDecision(
            DECISION_BLOCK, bump,
            (f"알 수 없는 의존성 분류 {update.dep_class!r} "
             f"(허용: {', '.join(_DEP_CLASSES)})",),
        )

    if update.gate.has_conflicts:
        return GateDecision(DECISION_BLOCK, bump, ("머지 충돌 존재",))
    if not update.gate.tests_passed:
        return GateDecision(DECISION_BLOCK, bump, ("회귀 테스트 실패",))

    if bump == BUMP_DOWNGRADE:
        return GateDecision(
            DECISION_BLOCK, bump,
            (f"버전 다운그레이드 {update.from_version}→{update.to_version}",),
        )
    if bump == BUMP_UNKNOWN:
        return GateDecision(
            DECISION_REVIEW_REQUIRED, bump,
            (f"버전 파싱 불가 ({update.from_version!r}→{update.to_version!r})",),
        )
    if bump == BUMP_NONE:
        return GateDecision(
            DECISION_REVIEW_REQUIRED, bump,
            ("버전 변화 없음 — 메타데이터/해시 변경 의심",),
        )

    if not update.gate.coverage_ok:
        return GateDecision(
            DECISION_REVIEW_REQUIRED, bump,
            ("커버리지 임계 미달 — 자동 머지 자격 박탈",),
        )

    if _auto_mergeable_bump(bump, update.dep_class):
        reasons.append(f"{bump} · {update.dep_class} · 게이트 GREEN")
        return GateDecision(DECISION_AUTO_MERGE, bump, tuple(reasons))

    if bump == BUMP_MAJOR:
        reasons.append("MAJOR 점프 — 호환성 파괴 가능, 사람 리뷰 필요")
    elif bump == BUMP_MINOR and update.dep_class == CLASS_RUNTIME:
        reasons.append("MINOR · runtime — 동작 변화 가능, 사람 리뷰 필요")
    else:  # 방어적: 새 bump 종류가 자동 머지 후보에서 빠지면 여기로 떨어진다.
        reasons.append(f"{bump} · {update.dep_class} — 사람 리뷰 필요")
    return GateDecision(DECISION_REVIEW_REQUIRED, bump, tuple(reasons))


# 정책 매트릭스(게이트 GREEN 전제). (bump, dep_class) → decision.
# evaluate() 의 권위 있는 규칙을 사람이 한눈에 볼 수 있게 표로 투영한 것일
# 뿐, 결정은 항상 evaluate() 가 내린다(중복 로직 아님 — 테스트가 일치 강제).
POLICY_MATRIX: dict[tuple[str, str], str] = {
    (BUMP_PATCH, CLASS_RUNTIME): DECISION_AUTO_MERGE,
    (BUMP_PATCH, CLASS_DEV): DECISION_AUTO_MERGE,
    (BUMP_PATCH, CLASS_CI): DECISION_AUTO_MERGE,
    (BUMP_MINOR, CLASS_RUNTIME): DECISION_REVIEW_REQUIRED,
    (BUMP_MINOR, CLASS_DEV): DECISION_AUTO_MERGE,
    (BUMP_MINOR, CLASS_CI): DECISION_AUTO_MERGE,
    (BUMP_MAJOR, CLASS_RUNTIME): DECISION_REVIEW_REQUIRED,
    (BUMP_MAJOR, CLASS_DEV): DECISION_REVIEW_REQUIRED,
    (BUMP_MAJOR, CLASS_CI): DECISION_REVIEW_REQUIRED,
}


def policy_manifest() -> dict[str, Any]:
    """정책을 JSON 직렬화 가능한 매니페스트로 굳힌다."""
    return {
        "schema": "sdacs-dependency-gate",
        "version": "1.0",
        "decisions": [DECISION_AUTO_MERGE, DECISION_REVIEW_REQUIRED, DECISION_BLOCK],
        "dep_classes": list(_DEP_CLASSES),
        "gate_required_for_auto_merge": True,
        "matrix": [
            {"bump": bump, "dep_class": dep_class, "decision_when_green": decision}
            for (bump, dep_class), decision in POLICY_MATRIX.items()
        ],
    }


# 정책 동작을 보이는 결정적 예시(실제 리포의 적체 Dependabot 갱신 형태).
_DEMO_UPDATES: tuple[DependencyUpdate, ...] = (
    DependencyUpdate(
        "pyyaml", "pip", "6.0.2", "6.0.3", CLASS_RUNTIME,
        RegressionGate(tests_passed=True, coverage_ok=True),
    ),
    DependencyUpdate(
        "playwright", "npm", "1.56.1", "1.60.0", CLASS_DEV,
        RegressionGate(tests_passed=True, coverage_ok=True),
    ),
    DependencyUpdate(
        "electron", "npm", "39.8.10", "42.4.0", CLASS_DEV,
        RegressionGate(tests_passed=True, coverage_ok=True),
    ),
    DependencyUpdate(
        "matplotlib", "pip", "3.9.0", "3.10.9", CLASS_RUNTIME,
        RegressionGate(tests_passed=True, coverage_ok=True),
    ),
    DependencyUpdate(
        "actions/cache", "github-actions", "4", "5", CLASS_CI,
        RegressionGate(tests_passed=True, coverage_ok=True),
    ),
)


def _cmd_policy() -> None:
    print("의존성 자동 머지 정책 매트릭스 (게이트 GREEN 전제)")
    print(f"{'BUMP':<10}{'CLASS':<10}DECISION")
    for (bump, dep_class), decision in POLICY_MATRIX.items():
        print(f"{bump:<10}{dep_class:<10}{decision}")
    print("\n게이트 RED(충돌·테스트 실패)·DOWNGRADE → 항상 BLOCK")


def _cmd_demo() -> None:
    print("예시 평가:")
    for update in _DEMO_UPDATES:
        decision = evaluate(update)
        print(f"  {update.name:<16} {update.from_version}→{update.to_version}"
              f"  {decision.summary()}")


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

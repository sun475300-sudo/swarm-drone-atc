"""ODYSSEY Phase 453 — RL 자문 경계(advisory boundary) 정합성 게이트.

Phase 451(`easa_ai_conformance`)은 SDACS 의 *진짜 강점* 이 러닝 어슈어런스가 아니라
**AI 안전 위험 완화** 에 있다고 진단했다 — ML(RL) 은 항상 *자문* 이고, 안전-결정권은
결정적 5계층 안전망(APF·CBS·관제기·Failsafe·비상 프로토콜)이 보유한다. 그 매트릭스에서
유일하게 ``conformant`` 였던 두 항목(``runtime_safety_monitoring``·
``classical_safety_net_authority``)의 근거가 바로 이 *아키텍처 선택* 이다.

본 모듈은 그 **주장을 검증 가능한 구조 불변식으로 명문화** 한다. Phase 451 이 *어디까지
충족하는가* 를 자가 평가하고, Phase 452(`rl_generalization_protocol`)가 *신뢰할 수 있는
일반화 주장* 의 전제를 게이트한다면, Phase 453 은 그 둘이 의지하는 **전제 자체** — "ML 은
자문, 결정적 안전망이 결정한다" — 가 리포 구조에서 실제로 성립하는가를 결정적 게이트로
판정한다.

핵심 통찰 (실측 기반)
--------------------
SDACS 의 RL/ML 자산(``src/rl/ppo_collision.py``·``simulation/rl_path_selector.py``·
``simulation/deep_rl_controller.py`` 등)은 **활성 제어/안전 결정 경로에 연결되어 있지
않다** — 연구 코드로 격리되어 있고, 활성 루프(관제기·드론 에이전트·시뮬레이터·Failsafe)는
오직 결정적 컴포넌트(``AdvisoryGenerator``·CBS·A*·APF)만 호출한다. 따라서 자문 경계는
*약속* 이 아니라 *구조적 사실* 이다: ML 출력이 안전-크리티컬 결정에 도달할 경로 자체가
존재하지 않는다.

이 모듈의 핵심 불변식 ``ml_isolated_from_active_loop`` 는 정적 선언이 아니라 **라이브
감사** 로 뒷받침된다(`audit_active_loop_imports`): 활성 루프 모듈 소스를 스캔해 RL/ML
모듈을 임포트하는 곳이 단 하나라도 있으면 위반으로 표면화한다. 누군가 RL 을 활성 루프에
배선하면 이 감사(와 회귀 테스트)가 즉시 깨진다 — 추측이 아닌 집행 가능한 경계.

정직 공시 (CLAUDE.md)
--------------------
1. 본 게이트는 *구조적 자문 경계* (ML 이 안전 결정 경로에 닿지 않음)를 판정한다. 만약
   장차 RL 을 활성 루프에 배선한다면 본 불변식들은 *능동 가드* (출력 클램프·결정적
   재정의)로 강화되어야 한다 — 현 ``BOUNDARY_ENFORCED`` 는 "ML 이 격리되어 있음" 의
   정직한 보고이지 "능동 가드가 검증됨" 이 아니다.
2. ``status`` 는 3값(``upheld``·``partial``·``unverified``)이며 정직성 결속:
   ``unverified`` ⟺ ``evidence is None``. 충족/부분은 반드시 실재 경로를 인용한다
   (테스트가 디스크 실재를 강제).
3. ``criticality`` 가 ``critical`` 인 불변식 하나라도 ``unverified`` 면 판정은
   ``BOUNDARY_NOT_ENFORCED`` — 가중 점수가 높아도 판정을 앞당기지 않는다. 임계 불변식이
   ``partial`` 이면 ``BOUNDARY_AT_RISK``. 권장 불변식의 미완은 판정을 막지 않고 점수에만
   반영된다.

무작위성 0 · 부수효과 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python simulation/rl_advisory_boundary.py --invariants  # 전체 불변식
    python simulation/rl_advisory_boundary.py --report      # 판정 요약
    python simulation/rl_advisory_boundary.py --audit       # 라이브 임포트 감사
    python simulation/rl_advisory_boundary.py --gaps        # 미충족(unverified) 불변식
    python simulation/rl_advisory_boundary.py --critical    # 임계 불변식만
"""
from __future__ import annotations

import argparse
import ast
import pathlib
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

# 활성 제어/안전 결정 경로를 구성하는 모듈(리포 상대 경로). ML 이 닿아선 안 되는 표면.
ACTIVE_LOOP_MODULES: tuple[str, ...] = (
    "src/airspace_control/controller/airspace_controller.py",
    "simulation/simulator.py",
    "simulation/drone_agent.py",
    "simulation/failsafe_manager.py",
    "simulation/emergency_protocol.py",
    "simulation/path_deconflict.py",
    "simulation/apf_engine/apf.py",
)

# RL/ML 모듈 임포트 탐지 토큰. 활성 루프 소스에 이 중 하나라도 임포트되면 경계 위반.
ML_IMPORT_TOKENS: tuple[str, ...] = (
    "rl_path_selector",
    "deep_rl_controller",
    "reinforcement_learning_trainer",
    "marl_coordinator",
    "rl_agent",
    "ppo_collision",
    "deep_reinforcement_learning",
    "swarm_reinforcement_learning",
    "src.rl",
    "stable_baselines3",
)

# 불변식 상태 (3값). upheld=구조적 성립, partial=부분, unverified=미검증.
INVARIANT_STATUSES: tuple[str, ...] = ("upheld", "partial", "unverified")

# 가중 점수: 성립 1.0, 부분 0.5, 미검증 0.0.
_STATUS_WEIGHT: dict[str, float] = {"upheld": 1.0, "partial": 0.5, "unverified": 0.0}

# 중요도 (2값). critical=경계 판정을 게이트, recommended=점수에만 반영.
CRITICALITIES: tuple[str, ...] = ("critical", "recommended")

# 판정 (verdict). 임계 불변식 충족 상태로 결정.
VERDICT_NOT_ENFORCED = "BOUNDARY_NOT_ENFORCED"
VERDICT_AT_RISK = "BOUNDARY_AT_RISK"
VERDICT_ENFORCED = "BOUNDARY_ENFORCED"


@dataclass(frozen=True)
class BoundaryInvariant:
    """RL 자문 경계를 떠받치는 단일 구조 불변식."""

    invariant_id: str        # 안정 식별자 (snake_case)
    name: str                # 불변식 명칭
    criticality: str         # critical·recommended
    status: str              # upheld·partial·unverified
    evidence: str | None     # 떠받치는 리포 경로 (unverified 면 None)
    summary: str             # 한 줄 설명

    def __post_init__(self) -> None:
        if not self.invariant_id or self.invariant_id != self.invariant_id.strip():
            raise ValueError("invariant_id must be non-empty and unpadded")
        if " " in self.invariant_id or "\t" in self.invariant_id or "\n" in self.invariant_id:
            raise ValueError("invariant_id must be snake_case (no whitespace)")
        if self.invariant_id != self.invariant_id.lower():
            raise ValueError("invariant_id must be lowercase snake_case")
        if not self.name or not self.name.strip():
            raise ValueError("name must be a non-empty string")
        if not self.summary or not self.summary.strip():
            raise ValueError("summary must be a non-empty string")
        if self.criticality not in CRITICALITIES:
            raise ValueError(
                f"criticality must be one of {CRITICALITIES}, got {self.criticality!r}"
            )
        if self.status not in INVARIANT_STATUSES:
            raise ValueError(
                f"status must be one of {INVARIANT_STATUSES}, got {self.status!r}"
            )
        # 정직성 결속: unverified ⟺ 근거 없음. 충족/부분은 반드시 실재 경로 인용.
        if self.status == "unverified":
            if self.evidence is not None:
                raise ValueError("an unverified invariant must not cite evidence")
        else:
            if self.evidence is None or not self.evidence.strip():
                raise ValueError(
                    f"status {self.status!r} must cite a non-empty evidence path"
                )

    @property
    def is_critical(self) -> bool:
        """임계 불변식 여부."""
        return self.criticality == "critical"

    @property
    def is_unverified(self) -> bool:
        """미검증 여부."""
        return self.status == "unverified"

    @property
    def weight(self) -> float:
        """가중 점수 기여 (upheld 1.0·partial 0.5·unverified 0.0)."""
        return _STATUS_WEIGHT[self.status]


# RL 자문 경계 불변식 카탈로그 (정본).
# evidence 경로는 리포에 실재하는 모듈/산출물 — 미검증(unverified)은 None.
# 현 리포는 RL 이 활성 루프에서 격리되어 있어 임계 불변식이 모두 upheld 다(정직한 강점).
BOUNDARY_INVARIANTS: tuple[BoundaryInvariant, ...] = (
    BoundaryInvariant(
        "ml_isolated_from_active_loop",
        "ML 자산이 활성 제어/안전 결정 경로에서 격리됨",
        "critical", "upheld",
        "src/airspace_control/controller/airspace_controller.py",
        "활성 루프 모듈이 RL/ML 모듈을 임포트하지 않음 — `audit_active_loop_imports` 라이브 강제",
    ),
    BoundaryInvariant(
        "deterministic_safety_net_authority",
        "결정적 안전망이 최종 안전-결정권 보유",
        "critical", "upheld",
        "simulation/failsafe_manager.py",
        "Failsafe 에스컬레이션 사다리가 안전-결정권 보유 — Phase 441 형식 검사가 우선순위 단조성 증명",
    ),
    BoundaryInvariant(
        "deterministic_conflict_resolution",
        "충돌 회피·디컨플릭션이 결정적(비-ML)",
        "critical", "upheld",
        "simulation/path_deconflict.py",
        "4D 경로 디컨플릭션·CBS·A* 가 활성 충돌 회피 수행 — ML 추론 비의존",
    ),
    BoundaryInvariant(
        "emergency_authority_non_ml",
        "비상 프로토콜이 비-ML 결정적 권한",
        "critical", "upheld",
        "simulation/emergency_protocol.py",
        "비상 강하·RTL·LAND 결정이 결정적 규칙 — ML 출력이 비상 권한에 도달 불가",
    ),
    BoundaryInvariant(
        "graceful_degradation_without_ml",
        "ML/가속 라이브러리 부재 시 안전 강등 운영",
        "recommended", "upheld",
        "simulation/apf_engine/apf_gpu.py",
        "torch 선택 임포트 폴백으로 ML/GPU 부재 시 결정적 CPU 경로 동작 — 하드 ML 의존 없음",
    ),
    BoundaryInvariant(
        "runtime_conformance_monitoring",
        "런타임 적합성 감시가 이탈·위반 탐지",
        "recommended", "upheld",
        "simulation/compliance_checker.py",
        "런타임 적합성 감시가 계획 대비 이탈·규정 위반을 결정적으로 탐지(Phase 451 SA:RT-01)",
    ),
    BoundaryInvariant(
        "reproducible_safety_decisions",
        "안전 경로 결정의 재현성(시드 RNG)",
        "recommended", "partial",
        "src/utils/rng.py",
        "시드 RNG 규약(np.random.default_rng) 존재 — 전 안전 경로 결정성의 형식 감사는 부분",
    ),
    BoundaryInvariant(
        "advisory_role_documented",
        "ML 자문 역할의 문서화된 경계 명세",
        "recommended", "upheld",
        "docs/standards/RL_ADVISORY_BOUNDARY.md",
        "본 Phase 453 경계 명세 + Phase 451 EASA 자가 평가가 ML=자문 역할을 명문화",
    ),
)


# 로드 시점 무결성 게이트 — 중복 식별자를 임포트 시 즉시 차단.
_CATALOG_IDS = [inv.invariant_id for inv in BOUNDARY_INVARIANTS]
assert len(_CATALOG_IDS) == len(set(_CATALOG_IDS)), "duplicate invariant_id in catalog"


def audit_active_loop_imports() -> tuple[tuple[str, str], ...]:
    """활성 루프 모듈 소스를 스캔해 RL/ML 임포트 위반을 (모듈, 토큰) 정렬로 반환한다.

    `ast` 로 임포트 노드(`import`·`from ... import`)만 검사하므로 주석·문서 문자열의
    토큰 언급은 오탐하지 않고, 괄호 다중 줄 임포트·별칭(`as`)·연속 줄의 임포트 이름도
    누락 없이 탐지한다(문자열 라인 스캔의 위양성/위음성 제거). 모듈 경로(`from X`)와
    임포트되는 이름(`import a, b` / `from X import a, b`)을 모두 토큰 대조한다.
    위반이 없으면 빈 튜플 — 이것이 ``ml_isolated_from_active_loop`` 불변식의 라이브
    근거다. 파일 부재·파싱 실패는 *조용히 통과하지 않고* 위반으로 표면화한다(감사
    표면이 사라지면 경계 주장도 거짓이 되므로).
    """
    violations: list[tuple[str, str]] = []
    for rel in ACTIVE_LOOP_MODULES:
        path = _REPO_ROOT / rel
        if not path.is_file():
            violations.append((rel, "<missing-module>"))
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            violations.append((rel, "<unparseable>"))
            continue
        for node in ast.walk(tree):
            targets: list[str] = []
            if isinstance(node, ast.Import):
                targets.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    targets.append(node.module)
                targets.extend(alias.name for alias in node.names)
            else:
                continue
            for token in ML_IMPORT_TOKENS:
                if any(token in target for target in targets):
                    violations.append((rel, token))
    return tuple(sorted(set(violations)))


def isolation_holds() -> bool:
    """RL 격리 불변식이 라이브 감사 기준 성립하면 True."""
    return not audit_active_loop_imports()


@dataclass(frozen=True)
class BoundaryReport:
    """RL 자문 경계 정합성 게이트 판정 요약."""

    verdict: str
    total: int
    upheld: int
    partial: int
    unverified: int
    critical_total: int
    critical_upheld: int
    by_criticality: Mapping[str, tuple[int, int, int]]  # crit -> (upheld, partial, unverified)

    def __post_init__(self) -> None:
        if not isinstance(self.by_criticality, MappingProxyType):
            object.__setattr__(
                self, "by_criticality", MappingProxyType(dict(self.by_criticality))
            )
        counts = (
            self.total, self.upheld, self.partial, self.unverified,
            self.critical_total, self.critical_upheld,
        )
        if min(counts) < 0:
            raise ValueError("counts must be non-negative")
        if self.upheld + self.partial + self.unverified != self.total:
            raise ValueError(
                f"upheld ({self.upheld}) + partial ({self.partial}) + "
                f"unverified ({self.unverified}) != total ({self.total})"
            )
        if self.critical_total > self.total:
            raise ValueError("critical_total cannot exceed total")
        if self.critical_upheld > self.critical_total:
            raise ValueError("critical_upheld cannot exceed critical_total")
        if self.verdict not in (VERDICT_NOT_ENFORCED, VERDICT_AT_RISK, VERDICT_ENFORCED):
            raise ValueError(f"invalid verdict: {self.verdict!r}")
        # 빈 by_criticality 도 교차검증한다 — total=0(전부 0) 만 정합하고, 비-0 카운트와
        # 빈 맵의 불일치는 거부한다(빈 dict 가 검증을 건너뛰던 구멍 차단).
        invalid = set(self.by_criticality.keys()) - set(CRITICALITIES)
        if invalid:
            raise ValueError(f"by_criticality has unknown keys: {sorted(invalid)}")
        u = sum(v[0] for v in self.by_criticality.values())
        p = sum(v[1] for v in self.by_criticality.values())
        n = sum(v[2] for v in self.by_criticality.values())
        if (u, p, n) != (self.upheld, self.partial, self.unverified):
            raise ValueError(
                f"by_criticality sums ({u},{p},{n}) != "
                f"({self.upheld},{self.partial},{self.unverified})"
            )

    @property
    def weighted_score_pct(self) -> float:
        """가중 정합 점수 (%) — upheld 1.0·partial 0.5·unverified 0.0."""
        if not self.total:
            return 0.0
        score = self.upheld * 1.0 + self.partial * 0.5
        return 100.0 * score / self.total

    @property
    def is_enforced(self) -> bool:
        """판정이 BOUNDARY_ENFORCED 인지 여부."""
        return self.verdict == VERDICT_ENFORCED


def _verdict_for(invariants: tuple[BoundaryInvariant, ...]) -> str:
    """임계 불변식 상태로 판정을 결정한다.

    우선순위(서로소): 임계 미검증 → NOT_ENFORCED > 임계 부분 → AT_RISK >
    임계 전부 성립 → ENFORCED. 권장 불변식은 판정을 게이트하지 않는다.
    """
    critical = [inv for inv in invariants if inv.is_critical]
    if not critical:
        # 임계 불변식이 하나도 없으면 경계를 주장할 근거가 없다(공허한 ENFORCED 차단).
        return VERDICT_NOT_ENFORCED
    if any(inv.status == "unverified" for inv in critical):
        return VERDICT_NOT_ENFORCED
    if any(inv.status == "partial" for inv in critical):
        return VERDICT_AT_RISK
    return VERDICT_ENFORCED


def assess_boundary() -> BoundaryReport:
    """RL 자문 경계 정합성을 집계한 결정적 게이트 판정을 생성한다.

    라이브 임포트 감사가 위반을 찾으면 ``ml_isolated_from_active_loop`` 임계
    불변식의 정적 ``upheld`` 선언은 신뢰할 수 없으므로 판정에서 *강등* 한다 —
    정적 카탈로그와 실측 사이의 불일치를 정직하게 표면화한다.
    """
    isolation_violated = not isolation_holds()
    effective: list[BoundaryInvariant] = []
    for inv in BOUNDARY_INVARIANTS:
        # 라이브 감사가 위반인데 정적 선언이 충족(upheld) 이면 정직성을 위해 강등한다.
        # 이미 partial/unverified 면 더 낙관적이지 않으므로 그대로 둔다 — 특히
        # unverified(근거 None)를 partial 로 바꾸면 정직성 결속을 깨므로 강등 금지.
        if (
            inv.invariant_id == "ml_isolated_from_active_loop"
            and isolation_violated
            and inv.status == "upheld"
        ):
            # 근거는 보존하되 충족 → 부분으로 강등(BOUNDARY_AT_RISK 유발).
            effective.append(
                BoundaryInvariant(
                    inv.invariant_id, inv.name, inv.criticality,
                    "partial", inv.evidence,
                    inv.summary + " [라이브 감사 위반 — 정적 선언 강등됨]",
                )
            )
        else:
            effective.append(inv)
    invariants = tuple(effective)

    total = len(invariants)
    upheld = sum(1 for inv in invariants if inv.status == "upheld")
    partial = sum(1 for inv in invariants if inv.status == "partial")
    unverified = sum(1 for inv in invariants if inv.status == "unverified")
    critical = [inv for inv in invariants if inv.is_critical]
    critical_upheld = sum(1 for inv in critical if inv.status == "upheld")
    by_criticality: dict[str, tuple[int, int, int]] = {}
    for crit in CRITICALITIES:
        members = [inv for inv in invariants if inv.criticality == crit]
        by_criticality[crit] = (
            sum(1 for inv in members if inv.status == "upheld"),
            sum(1 for inv in members if inv.status == "partial"),
            sum(1 for inv in members if inv.status == "unverified"),
        )
    return BoundaryReport(
        verdict=_verdict_for(invariants),
        total=total,
        upheld=upheld,
        partial=partial,
        unverified=unverified,
        critical_total=len(critical),
        critical_upheld=critical_upheld,
        by_criticality=MappingProxyType(by_criticality),
    )


def find_invariant(invariant_id: str) -> BoundaryInvariant:
    """식별자로 불변식을 조회한다. 없으면 KeyError."""
    for inv in BOUNDARY_INVARIANTS:
        if inv.invariant_id == invariant_id:
            return inv
    raise KeyError(f"unknown boundary invariant: {invariant_id!r}")


def invariants_by_criticality(criticality: str) -> tuple[BoundaryInvariant, ...]:
    """중요도별 불변식을 식별자 정렬로 반환한다."""
    if criticality not in CRITICALITIES:
        raise ValueError(
            f"criticality must be one of {CRITICALITIES}, got {criticality!r}"
        )
    return tuple(
        sorted((inv for inv in BOUNDARY_INVARIANTS if inv.criticality == criticality),
               key=lambda inv: inv.invariant_id)
    )


def gaps() -> tuple[BoundaryInvariant, ...]:
    """미검증(unverified) 불변식을 식별자 정렬로 반환한다."""
    return tuple(
        sorted((inv for inv in BOUNDARY_INVARIANTS if inv.is_unverified),
               key=lambda inv: inv.invariant_id)
    )


def boundary_matrix() -> tuple[Mapping[str, object], ...]:
    """도구 간 교환용 경계 매트릭스를 (중요도, 식별자) 정렬 행으로 반환한다."""
    ordered = sorted(
        BOUNDARY_INVARIANTS,
        key=lambda inv: (CRITICALITIES.index(inv.criticality), inv.invariant_id),
    )
    return tuple(
        MappingProxyType({
            "invariant_id": inv.invariant_id,
            "name": inv.name,
            "criticality": inv.criticality,
            "status": inv.status,
            "evidence": inv.evidence,
            "summary": inv.summary,
        })
        for inv in ordered
    )


_STATUS_MARK: dict[str, str] = {"upheld": "✓", "partial": "◐", "unverified": "✗(미검증)"}


def _format_matrix() -> str:
    lines = ["RL 자문 경계 정합성 불변식 매트릭스", ""]
    for row in boundary_matrix():
        mark = _STATUS_MARK[str(row["status"])]
        kind = "임계" if row["criticality"] == "critical" else "권장"
        evidence = row["evidence"] or "—"
        lines.append(f"[{kind}] {mark} {row['invariant_id']}: {row['name']}")
        lines.append(f"      → {evidence}")
    return "\n".join(lines)


def _format_report() -> str:
    r = assess_boundary()
    audit = audit_active_loop_imports()
    lines = [
        "RL 자문 경계 정합성 게이트 판정",
        "",
        f"판정       : {r.verdict}",
        f"가중 점수   : {r.weighted_score_pct:.0f}% "
        f"(성립 {r.upheld} · 부분 {r.partial} · 미검증 {r.unverified} / 총 {r.total})",
        f"임계 불변식 : {r.critical_upheld}/{r.critical_total} 성립",
        f"라이브 감사 : {'위반 없음 (격리 성립)' if not audit else f'위반 {len(audit)}건'}",
        "",
        "중요도별 (성립/부분/미검증):",
    ]
    for crit in CRITICALITIES:
        u, p, n = r.by_criticality[crit]
        label = "임계" if crit == "critical" else "권장"
        lines.append(f"  {label}: {u}/{p}/{n}")
    lines.append("")
    lines.append(
        "정직 공시: BOUNDARY_ENFORCED 는 ML 이 활성 루프에서 격리되어 있음의 정직한"
    )
    lines.append(
        "  보고이지, 장차 RL 배선 시 필요한 능동 가드가 검증됐다는 뜻이 아니다."
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="RL 자문 경계(advisory boundary) 정합성 게이트 (ODYSSEY Phase 453)"
    )
    parser.add_argument("--invariants", action="store_true", help="전체 불변식 매트릭스 출력")
    parser.add_argument("--report", action="store_true", help="판정 요약 출력")
    parser.add_argument("--audit", action="store_true", help="라이브 임포트 감사 출력")
    parser.add_argument("--gaps", action="store_true", help="미검증 불변식 출력")
    parser.add_argument("--critical", action="store_true", help="임계 불변식만 출력")
    args = parser.parse_args(argv)

    if args.invariants:
        print(_format_matrix())
    elif args.report:
        print(_format_report())
    elif args.audit:
        violations = audit_active_loop_imports()
        if not violations:
            print("라이브 임포트 감사: 위반 없음 — RL 이 활성 루프에서 격리됨.")
        else:
            print("라이브 임포트 감사: 경계 위반 발견 —")
            for module, token in violations:
                print(f"  {module} ← {token}")
    elif args.gaps:
        for inv in gaps():
            print(f"[{inv.criticality}] {inv.invariant_id}: {inv.summary}")
    elif args.critical:
        for inv in invariants_by_criticality("critical"):
            print(f"{_STATUS_MARK[inv.status]} {inv.invariant_id} → {inv.evidence or '—'}")
    else:
        print(_format_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

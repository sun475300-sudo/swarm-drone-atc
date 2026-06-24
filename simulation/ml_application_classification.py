"""ODYSSEY Phase 454 — ML 애플리케이션 EASA Level 분류 게이트.

SDACS 의 *학습 기반(ML)* 구성요소(강화학습 충돌 회피·하이브리드 APF+RL·도메인
무작위화 정책·시뮬-실측 보정)가 EASA 신뢰 가능 AI 프레임워크의 **분류(Level 1/2/3)**
축에서 어디에 놓이는가를 결정적으로 판정하는 게이트다. ODYSSEY Track 🔬 Formal &
Research Frontier(451-460)의 후속 모듈로, Phase 451(`easa_ai_conformance`)이
*무엇이 빠졌는가* 를 매트릭스로 표면화하면서 가장 큰 갭으로 지목한
``ml_application_classification`` — "EASA Level 1A/1B/2/3 분류 기록 없음, 인증 경로
진입 전제 미충족" — 을 정면으로 채운다. 인증 경로의 *부담* 은 Level 에 따라 급격히
달라지므로(Level 1 = 경량, Level 3 = 러닝 어슈어런스 전체 부담), "각 ML 자산이
어느 Level 인가" 는 인증 가능성 논의의 **첫 관문**이다.

분류 정책 (근거)
----------------
- **EASA Concept Paper — "Guidance for Level 1 & 2 machine learning applications"**
  (Issue 02, 2024) 및 **AI Roadmap 2.0** (2023) 이 정의하는 AI Level 분류:
    * **Level 1 (assistance)** — AI 가 사람/비-AI 결정자를 *보조* (1A 인간 증강 ·
      1B 인지 보조). 결정 권한은 비-AI 측이 보유.
    * **Level 2 (cooperation)** — 인간-AI *협업*. AI 가 결정에 능동 참여하되 인간이
      감독(2A 권한 보유 · 2B 권한 축소·감독 유지).
    * **Level 3 (automation)** — AI 가 결정을 *수행* (3A 인간 재정의 가능 · 3B 재정의
      불가·완전 자율).
  Level 의 **가족(1/2/3)** 은 *과업 배분*(AI 가 보조하는가·협업하는가·대체하는가)이,
  **하위 문자(A/B)** 는 *인간/비-AI 권한 보유 정도* 가 가른다.

정직 공시 (CLAUDE.md)
--------------------
1. 본 모듈은 *기능적 자가 분류* 이며 EASA 공식 분류 인증이 아니다. ``POLICY_MATRIX``
   는 Concept Paper 의 Level 정의를 SDACS 가 *기계 검증 가능* 한 두 축(과업 배분 ×
   권한 보유)으로 환원한 것으로, 원문의 모든 세부 판정 기준을 복제하지 않는다.
2. ``sdacs_module`` 은 분류 대상 ML 자산의 실재 경로다(테스트가 디스크 실재 강제).
   허위 자산 분류를 구조적으로 금지한다.
3. **정직성 결속 — 권한에는 권한자가 필요**: ``human_authority`` 가 ``none`` 이 아니면
   반드시 그 권한을 *실제로 보유한 비-AI 모듈* 을 ``override_authority`` 로 인용해야
   한다(없으면 ``ValueError``). "감독이 유지된다" 는 주장은 감독 주체를 명시할 때만
   인정한다 — 권한자 없는 안전 주장을 차단한다.
4. **핵심 발견(정직)**: SDACS 의 모든 ML 자산은 *항상 자문* 이며 안전-결정권은 결정적
   APF+CBS 5계층 안전망이 보유한다. 따라서 전 자산이 **Level 1A** 로 분류된다 — 인증
   부담이 가장 낮은 등급이다. 이는 결함이 아니라 *설계 선택의 보상* 이다: "ML 을
   안전-크리티컬 결정에 신뢰하지 않음" 으로써 Level 2/3 의 러닝 어슈어런스 전체 부담을
   회피한다. 낮은 Level 이 곧 낮은 인증 리스크다.

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python simulation/ml_application_classification.py --matrix       # 분류 매트릭스
    python simulation/ml_application_classification.py --report       # 분류 요약
    python simulation/ml_application_classification.py --levels       # Level 정의표
    python simulation/ml_application_classification.py --constituent ppo_collision_avoidance
    python simulation/ml_application_classification.py --policy       # 분류 정책 매트릭스
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

# EASA AI Level 6 하위 등급 (분류 결과값). 가족 1/2/3 × 하위 A/B.
EASA_LEVELS: tuple[str, ...] = ("1A", "1B", "2A", "2B", "3A", "3B")

# 과업 배분 축 — Level 가족(1/2/3)을 가른다.
TASK_ALLOCATIONS: tuple[str, ...] = ("assistance", "cooperation", "automation")

# 인간/비-AI 권한 보유 정도 — 하위 문자(A/B)를 가른다.
HUMAN_AUTHORITY: tuple[str, ...] = ("retained", "reduced", "none")

# 분류 정책 매트릭스 (과업 배분 × 권한 보유) → EASA Level. 9칸 전수 정의(전함수).
# 가족(1/2/3)은 과업 배분이, 하위 문자(A/B)는 권한 보유가 가른다. 의도적 단순화:
# 권한 ``none`` 은 과업 가족 안에서 *최악 하위 등급* 으로 붕괴한다(assistance/none→1B·
# cooperation/none→2B) — 감독 부재는 같은 가족 내 가장 나쁜 자세로 본다. 권한 부재가
# 자체로 가족을 올리지는 않는다(보조는 감독이 없어도 결정 주체가 아니므로 가족 1).
# (아래 dict 리터럴은 익명이라 외부 참조가 없다 → MappingProxyType 가 사실상 불변.)
POLICY_MATRIX: Mapping[tuple[str, str], str] = MappingProxyType({
    ("assistance", "retained"): "1A",
    ("assistance", "reduced"): "1B",
    ("assistance", "none"): "1B",
    ("cooperation", "retained"): "2A",
    ("cooperation", "reduced"): "2B",
    ("cooperation", "none"): "2B",
    ("automation", "retained"): "3A",
    ("automation", "reduced"): "3A",
    ("automation", "none"): "3B",
})

# Level → 가족 번호(1/2/3). 인증 부담 비교에 사용.
LEVEL_FAMILY: Mapping[str, int] = MappingProxyType({
    "1A": 1, "1B": 1, "2A": 2, "2B": 2, "3A": 3, "3B": 3,
})

_LEVEL_DEFINITION: dict[str, str] = {
    "1A": "Human augmentation — AI 가 비-AI 결정자를 보조, 권한은 비-AI 보유",
    "1B": "Cognitive assistance — AI 가 인지 과업 보조, 권한 보유 약화",
    "2A": "Human-AI cooperation — 협업, 인간 권한·감독 보유",
    "2B": "Human-AI collaboration — 협업, 권한 축소·감독 유지",
    "3A": "Advanced automation — AI 가 결정 수행, 인간 재정의 가능",
    "3B": "Full automation — AI 자율 결정, 인간 재정의 불가",
}


def classify_level(allocation: str, human_authority: str) -> str:
    """과업 배분 × 권한 보유 → EASA Level 을 결정적으로 분류한다."""
    if allocation not in TASK_ALLOCATIONS:
        raise ValueError(
            f"allocation must be one of {TASK_ALLOCATIONS}, got {allocation!r}"
        )
    if human_authority not in HUMAN_AUTHORITY:
        raise ValueError(
            f"human_authority must be one of {HUMAN_AUTHORITY}, got {human_authority!r}"
        )
    return POLICY_MATRIX[(allocation, human_authority)]


@dataclass(frozen=True)
class MLConstituent:
    """단일 SDACS ML 자산과 그 EASA Level 분류 입력의 정의."""

    constituent_id: str          # 안정 식별자 (snake_case, 예: 'ppo_collision_avoidance')
    name: str                    # 자산 명칭
    task: str                    # ML 이 수행하는 과업
    sdacs_module: str            # 자산 실재 경로 (디스크 실재 강제)
    allocation: str              # assistance·cooperation·automation
    human_authority: str         # retained·reduced·none
    override_authority: str | None  # 권한 보유 비-AI 모듈 (none 이면 None)
    rationale: str               # 분류 근거 한 줄

    def __post_init__(self) -> None:
        if not self.constituent_id or self.constituent_id != self.constituent_id.strip():
            raise ValueError("constituent_id must be non-empty and unpadded")
        if " " in self.constituent_id:
            raise ValueError("constituent_id must not contain internal spaces (snake_case)")
        for field_name in ("name", "task", "sdacs_module", "rationale"):
            value = getattr(self, field_name)
            if not value or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if self.allocation not in TASK_ALLOCATIONS:
            raise ValueError(
                f"allocation must be one of {TASK_ALLOCATIONS}, got {self.allocation!r}"
            )
        if self.human_authority not in HUMAN_AUTHORITY:
            raise ValueError(
                f"human_authority must be one of {HUMAN_AUTHORITY}, got {self.human_authority!r}"
            )
        # 정직성 결속: 권한 보유 주장(none 아님)은 반드시 비-AI 권한자를 인용.
        # 권한 부재(none)는 인용 금지 — 권한자 없는 감독 주장을 구조적으로 차단.
        if self.human_authority == "none":
            if self.override_authority is not None:
                raise ValueError(
                    "human_authority 'none' must not cite an override_authority"
                )
        else:
            if self.override_authority is None or not self.override_authority.strip():
                raise ValueError(
                    f"human_authority {self.human_authority!r} must cite a non-empty "
                    "override_authority (the non-AI authority holder)"
                )
        # NOTE: 인용 경로(sdacs_module·override_authority)의 디스크 실재는
        # test_cited_modules_exist_on_disk·test_cited_override_authorities_exist_on_disk
        # 가 강제한다(생성자를 파일 I/O 로부터 순수하게 유지하기 위해 여기서는 미검사).

    @property
    def level(self) -> str:
        """이 자산의 EASA Level (과업 배분 × 권한 보유 분류 결과)."""
        return classify_level(self.allocation, self.human_authority)

    @property
    def family(self) -> int:
        """Level 가족 번호(1/2/3) — 인증 부담의 거시 지표."""
        return LEVEL_FAMILY[self.level]

    @property
    def is_advisory(self) -> bool:
        """ML 출력이 자문(보조)에 그치는가(가족 1) 여부."""
        return self.family == 1


# SDACS ML 자산 카탈로그 ↔ EASA Level 분류 (정본).
# 전 자산이 *자문* 이고 비-AI 결정적 권한자가 override 를 보유 → 전부 Level 1A.
# 이는 정직한 강점 공시다: 낮은 Level = 낮은 인증 부담.
ML_CONSTITUENTS: tuple[MLConstituent, ...] = (
    MLConstituent(
        "ppo_collision_avoidance",
        "PPO 강화학습 충돌 회피 정책",
        "이웃 상태로부터 회피 기동을 추천(연구 수준 RL)",
        "src/rl/ppo_collision.py",
        "assistance", "retained",
        "simulation/path_deconflict.py",
        "RL 기동 추천을 결정적 4D 디컨플릭션이 경계·재정의 → 자문, 권한은 비-AI 보유 (1A)",
    ),
    MLConstituent(
        "hybrid_apf_rl_avoidance",
        "하이브리드 APF+RL 충돌 회피",
        "규칙(APF)·학습(RL) 출력을 블렌딩하되 임계 거리 내 APF 100% 제어",
        "src/autonomy/hybrid_collision_avoidance.py",
        "assistance", "retained",
        "src/airspace_control/controller/airspace_controller.py",
        "안전 임계 내 규칙 우선 보증(RL 가중 0) → ML 자문, 결정적 관제기가 권한 보유 (1A)",
    ),
    MLConstituent(
        "domain_randomized_policy",
        "도메인 무작위화 학습 정책",
        "DR 로 분포 다양화한 정책의 강건성(배포 시 자문 출력)",
        "src/training/domain_rand.py",
        "assistance", "retained",
        "simulation/emergency_protocol.py",
        "DR 정책 출력도 배포 시 자문일 뿐 → 5계층 안전망·비상 프로토콜이 권한 보유 (1A)",
    ),
    MLConstituent(
        "sim_real_gap_calibration",
        "시뮬-실측 갭 보정",
        "DR 파라미터 자동 보정(설정 튜닝 보조, 런타임 결정 비참여)",
        "src/training/sim_real_gap.py",
        "assistance", "retained",
        "simulation/compliance_checker.py",
        "보정값은 설정 제안일 뿐 → 런타임 적합성 감시가 어떤 보정 정책이든 경계 (1A)",
    ),
)


# 로드 시점 무결성 게이트 — 임포트 시 즉시 차단.
_CATALOG_IDS = [c.constituent_id for c in ML_CONSTITUENTS]
# `assert` 는 `python -O` 에서 비활성화되므로 명시적 raise 로 집행한다.
if len(_CATALOG_IDS) != len(set(_CATALOG_IDS)):
    raise RuntimeError("duplicate constituent_id")
if set(POLICY_MATRIX.keys()) != {(a, h) for a in TASK_ALLOCATIONS for h in HUMAN_AUTHORITY}:
    raise RuntimeError("POLICY_MATRIX must cover every (allocation, authority) combination")
if not set(POLICY_MATRIX.values()) <= set(EASA_LEVELS):
    raise RuntimeError("POLICY_MATRIX yields unknown level")
if set(LEVEL_FAMILY.keys()) != set(EASA_LEVELS):
    raise RuntimeError("LEVEL_FAMILY must cover every level")


@dataclass(frozen=True)
class ClassificationReport:
    """SDACS ML 자산 EASA Level 분류 요약."""

    total: int
    by_level: Mapping[str, int]   # level -> count, read-only (6 키 전부)
    by_family: Mapping[int, int]  # family -> count, read-only

    def __post_init__(self) -> None:
        if not isinstance(self.by_level, MappingProxyType):
            object.__setattr__(self, "by_level", MappingProxyType(dict(self.by_level)))
        if not isinstance(self.by_family, MappingProxyType):
            object.__setattr__(self, "by_family", MappingProxyType(dict(self.by_family)))
        if self.total < 0 or any(v < 0 for v in self.by_level.values()):
            raise ValueError("counts must be non-negative")
        invalid = set(self.by_level.keys()) - set(EASA_LEVELS)
        if invalid:
            raise ValueError(f"by_level contains unknown levels: {sorted(invalid)}")
        if sum(self.by_level.values()) != self.total:
            raise ValueError(
                f"by_level sum ({sum(self.by_level.values())}) != total ({self.total})"
            )
        # by_family 가 by_level 가족 집계와 일치해야 함 (교차검증).
        derived: dict[int, int] = {}
        for level, count in self.by_level.items():
            derived[LEVEL_FAMILY[level]] = derived.get(LEVEL_FAMILY[level], 0) + count
        derived = {fam: n for fam, n in derived.items() if n}
        if dict(self.by_family) != derived:
            raise ValueError(
                f"by_family {dict(self.by_family)} != derived from by_level {derived}"
            )

    @property
    def all_advisory(self) -> bool:
        """전 자산이 가족 1(자문)인가 — Level 2/3 자산이 0 건이면 True."""
        return all(fam == 1 for fam in self.by_family) and self.total > 0

    @property
    def highest_family(self) -> int:
        """등록 자산 중 최고 Level 가족(없으면 0)."""
        return max(self.by_family.keys(), default=0)


def find_constituent(constituent_id: str) -> MLConstituent:
    """식별자로 ML 자산을 조회한다. 없으면 KeyError."""
    for constituent in ML_CONSTITUENTS:
        if constituent.constituent_id == constituent_id:
            return constituent
    raise KeyError(f"unknown ML constituent: {constituent_id!r}")


def constituents_by_level(level: str) -> tuple[MLConstituent, ...]:
    """EASA Level 별 자산을 식별자 정렬로 반환한다."""
    if level not in EASA_LEVELS:
        raise ValueError(f"level must be one of {EASA_LEVELS}, got {level!r}")
    return tuple(
        sorted((c for c in ML_CONSTITUENTS if c.level == level),
               key=lambda c: c.constituent_id)
    )


def classification_report() -> ClassificationReport:
    """전체 ML 자산 Level 분류 현황을 집계한 결정적 리포트를 생성한다."""
    by_level: dict[str, int] = {}
    for constituent in ML_CONSTITUENTS:
        by_level[constituent.level] = by_level.get(constituent.level, 0) + 1
    by_family: dict[int, int] = {}
    for level, count in by_level.items():
        by_family[LEVEL_FAMILY[level]] = by_family.get(LEVEL_FAMILY[level], 0) + count
    return ClassificationReport(
        total=len(ML_CONSTITUENTS),
        by_level=MappingProxyType(dict(by_level)),
        by_family=MappingProxyType(dict(by_family)),
    )


def classification_matrix() -> tuple[Mapping[str, object], ...]:
    """도구 간 교환용 분류 매트릭스를 (Level, 식별자) 정렬 행으로 반환한다."""
    ordered = sorted(
        ML_CONSTITUENTS,
        key=lambda c: (EASA_LEVELS.index(c.level), c.constituent_id),
    )
    return tuple(
        MappingProxyType({
            "constituent_id": c.constituent_id,
            "name": c.name,
            "task": c.task,
            "sdacs_module": c.sdacs_module,
            "allocation": c.allocation,
            "human_authority": c.human_authority,
            "override_authority": c.override_authority,
            "level": c.level,
            "family": c.family,
            "rationale": c.rationale,
        })
        for c in ordered
    )


def _format_matrix() -> str:
    lines = ["SDACS ML 애플리케이션 EASA Level 분류 매트릭스", ""]
    for row in classification_matrix():
        override = row["override_authority"] or "—"
        lines.append(
            f"[Level {row['level']}] {row['constituent_id']} — {row['name']}"
        )
        lines.append(f"      과업   : {row['task']}")
        lines.append(f"      모듈   : {row['sdacs_module']}")
        lines.append(
            f"      배분/권한: {row['allocation']} / {row['human_authority']} "
            f"(권한자: {override})"
        )
        lines.append(f"      근거   : {row['rationale']}")
    return "\n".join(lines)


def _format_report() -> str:
    report = classification_report()
    lines = [
        "SDACS ML 애플리케이션 EASA Level 분류 요약",
        "",
        f"총 자산   : {report.total}",
        "",
        "Level 별 분포:",
    ]
    for level in EASA_LEVELS:
        count = report.by_level.get(level, 0)
        if count:
            lines.append(f"  Level {level} ({_LEVEL_DEFINITION[level]}): {count}")
    lines.append("")
    lines.append(
        f"최고 Level 가족: {report.highest_family} "
        f"({'전 자산 자문(가족 1)' if report.all_advisory else '가족 2/3 자산 존재'})"
    )
    lines.append("")
    lines.append(
        "정직 공시: 전 ML 자산이 Level 1A 다. ML 은 항상 자문이고 안전-결정권은 결정적"
    )
    lines.append(
        "  5계층 안전망이 보유한다 — 낮은 Level 은 결함이 아니라 낮은 인증 부담의 보상이다."
    )
    return "\n".join(lines)


def _format_policy() -> str:
    lines = ["EASA Level 분류 정책 매트릭스 (과업 배분 × 권한 보유 → Level)", ""]
    for allocation in TASK_ALLOCATIONS:
        for authority in HUMAN_AUTHORITY:
            level = POLICY_MATRIX[(allocation, authority)]
            lines.append(f"  {allocation:12} × {authority:9} → Level {level}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ML 애플리케이션 EASA Level 분류 게이트 (ODYSSEY Phase 454)"
    )
    parser.add_argument("--matrix", action="store_true", help="분류 매트릭스 출력")
    parser.add_argument("--report", action="store_true", help="분류 요약 출력")
    parser.add_argument("--levels", action="store_true", help="EASA Level 정의표 출력")
    parser.add_argument("--policy", action="store_true", help="분류 정책 매트릭스 출력")
    parser.add_argument("--constituent", help="식별자로 단일 자산 분류 출력")
    args = parser.parse_args(argv)

    if args.matrix:
        print(_format_matrix())
    elif args.report:
        print(_format_report())
    elif args.levels:
        print("EASA AI Level 정의")
        print("")
        for level in EASA_LEVELS:
            print(f"  Level {level}: {_LEVEL_DEFINITION[level]}")
    elif args.policy:
        print(_format_policy())
    elif args.constituent:
        try:
            constituent = find_constituent(args.constituent)
        except KeyError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(f"{constituent.constituent_id} → Level {constituent.level}")
        print(f"  과업   : {constituent.task}")
        print(f"  모듈   : {constituent.sdacs_module}")
        print(f"  권한자 : {constituent.override_authority or '—'}")
        print(f"  근거   : {constituent.rationale}")
    else:
        print(_format_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""ODYSSEY Phase 452 — ML 애플리케이션 분류 게이트 (EASA AI Level 분류).

SDACS 의 *운영(추론) 시점* ML 구성요소를 EASA 가 제시한 AI Level(1A/1B/2A/2B/3A/3B)
분류 체계에 따라 결정적으로 분류한다. ODYSSEY Track 🔬 Formal & Research Frontier(452-460,
"RL 일반화 연구 + 인증 가능 ML 조사")의 후속 모듈로, **Phase 451(`easa_ai_conformance`)이
최대 갭으로 명시한 `ml_application_classification`(EASA Level 분류 기록 없음 — 인증 경로
진입 전제 미충족) 칸을 정면으로 메운다.**

451 과의 경계 (중복 0)
---------------------
- Phase 451(`easa_ai_conformance`): SDACS ML 이 신뢰 가능 AI *목표를 얼마나 충족* 하는가
  (적합성 매트릭스 — "objectives 를 meet 하는가").
- Phase 452(본 모듈): 각 ML 구성요소가 *어느 AI Level 인가* — 그리고 그 Level 이 *어떤
  러닝 어슈어런스 의무 강도를 부과* 하는가 ("어느 level/objectives 가 *애초에* 적용되는가").
  분류는 적합성보다 *앞* 단계다 — Level 을 먼저 정해야 어떤 목표가 적용되는지 안다.

근거 (권위 있는 출처)
--------------------
- **EASA Concept Paper — "Guidance for Level 1 & 2 machine learning applications"**
  (Issue 02, 2024). AI 애플리케이션을 *인간/시스템 대비 AI 의 자율 수준* 으로 분류한다:
  Level 1(AI 보조 — 인간/시스템이 결정)·Level 2(human-AI teaming — AI 가 행위, 감독자가
  재정의)·Level 3(AI 가 결정). 각 Level 은 A/B 로 세분된다.
- **EASA Artificial Intelligence Roadmap 2.0** (2023) — Level 이 올라갈수록 러닝
  어슈어런스 의무가 무거워진다(Level 1 이 가장 가벼움). 본 모듈은 이 단조 관계를
  ``LEVEL_ASSURANCE`` 로 인코딩한다.

분류 모델 (결정적)
-----------------
각 구성요소는 세 속성으로 선언되고, ``classify`` 가 그로부터 Level 을 유일하게 도출한다:

- ``ai_role`` — AI 가 통제 루프에서 차지하는 역할:
  * ``advisory``          : 정보/권고만 발신, 결정권은 인간/결정적 시스템 → **Level 1**
  * ``supervised_actor``  : AI 가 행위를 수행, 감독자가 재정의 가능        → **Level 2**
  * ``decider``           : AI 가 최종 안전 결정 보유                       → **Level 3**
  * ``not_operational``   : 학습-시점 자산(운영 추론 루프 밖) → 분류 대상 외 → **N/A**
- ``advisory`` 일 때 ``emits`` ∈ {``information``, ``recommendation``} → 1A / 1B
- ``supervised_actor`` 일 때 ``oversight_by`` ∈ {``human``, ``ai``}    → 2A / 2B
- ``decider`` 일 때 ``human_fallback`` (bool)                          → 3A / 3B

정직 공시 (CLAUDE.md)
--------------------
1. 본 모듈은 *기능적 자가 분류* 이며 EASA 공식 분류 결정이 아니다. Level 정의는 SDACS
   해석이며 EASA 문서를 복제하지 않는다.
2. **SDACS 의 모든 운영 ML 구성요소는 ``advisory`` 다** — 안전-결정권은 결정적 APF+CBS
   5계층 안전망이 보유하고 ML 은 절대 작동기(actuator)에 직접 연결되지 않는다(CLAUDE.md
   "검증 안 된 RL 모듈을 규칙 기반 로직에 직접 연결 금지"). 따라서 분류 결과는 전부
   **Level 1**(가장 가벼운 어슈어런스 의무 계층)에 머문다. *이것이 결함이 아니라
   아키텍처의 정직한 귀결* 이다: 연구 수준 ML 을 안전-크리티컬 권한에서 배제함으로써
   인증 부담을 최소 계층에 유지한다.
3. ``sdacs_module`` 은 구성요소를 *실제로* 구현한 리포 내 경로다 — 모든 항목이 실재
   경로를 인용하며(테스트가 디스크 실재를 강제) 근거 없는 분류를 구조적으로 금지한다.
4. 학습-시점 자산(도메인 무작위화 등)은 ``not_operational`` 로 명시 분류해 *범위 경계* 를
   기계 검증한다 — 운영 구성요소가 아니므로 Level 집계 분모에서 제외(N/A).

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python simulation/ml_application_classification.py --constituents  # 구성요소+분류
    python simulation/ml_application_classification.py --report        # 분류 요약
    python simulation/ml_application_classification.py --levels        # Level 체계·의무
    python simulation/ml_application_classification.py --matrix        # 분류 규칙 매트릭스
    python simulation/ml_application_classification.py --manifest      # JSON 매니페스트
"""
from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

# EASA AI Level (자율 수준 오름차순). N/A = 비운영(분류 대상 외).
AI_LEVELS: tuple[str, ...] = ("1A", "1B", "2A", "2B", "3A", "3B", "N/A")

# Level 별 한 줄 정의 + 러닝 어슈어런스 의무 강도(0=해당없음, 1=최저 … 6=최고).
# Level 이 오를수록 의무가 단조 증가(Roadmap 2.0).
_LEVEL_INFO: dict[str, tuple[str, int]] = {
    "1A": ("Level 1A — 인간 증강 (AI 정보 제공, 인간/시스템이 결정·행위)", 1),
    "1B": ("Level 1B — 인지 보조 (AI 행위 옵션 권고, 인간/시스템이 결정·행위)", 2),
    "2A": ("Level 2A — human-AI teaming, 인간 감독 (AI 행위, 인간 재정의)", 3),
    "2B": ("Level 2B — human-AI teaming, AI 감독 (AI 행위·감독)", 4),
    "3A": ("Level 3A — 인간 폴백 동반 고급 자동화 (AI 결정, 인간 폴백)", 5),
    "3B": ("Level 3B — 자율 AI (AI 결정, 인간 폴백 없음)", 6),
    "N/A": ("N/A — 비운영 자산 (학습-시점, 운영 추론 루프 밖 → 분류 대상 외)", 0),
}

# AI 가 통제 루프에서 차지하는 역할 (분류 1차 축).
AI_ROLES: tuple[str, ...] = ("advisory", "supervised_actor", "decider", "not_operational")
# advisory 발신 종류 (2차 축).
EMIT_KINDS: tuple[str, ...] = ("information", "recommendation")
# supervised_actor 감독 주체 (2차 축).
OVERSIGHT_BY: tuple[str, ...] = ("human", "ai")


@dataclass(frozen=True)
class MlConstituent:
    """단일 ML 구성요소와 그 운영 역할 선언."""

    constituent_id: str          # 안정 식별자 (snake_case, 예: 'ppo_collision')
    name: str                    # 구성요소 명칭
    function: str                # 기능 한 줄 설명
    ai_role: str                 # advisory·supervised_actor·decider·not_operational
    emits: str | None            # advisory 일 때만: information·recommendation
    oversight_by: str | None     # supervised_actor 일 때만: human·ai
    human_fallback: bool | None  # decider 일 때만: 인간 폴백 여부
    sdacs_module: str            # 구현 경로 (항상 실재)
    rationale: str               # 분류 근거 한 줄

    def __post_init__(self) -> None:
        if not self.constituent_id or self.constituent_id != self.constituent_id.strip():
            raise ValueError("constituent_id must be non-empty and unpadded")
        if " " in self.constituent_id:
            raise ValueError("constituent_id must be snake_case (no internal spaces)")
        for field_name in ("name", "function", "sdacs_module", "rationale"):
            value = getattr(self, field_name)
            if not value or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if self.ai_role not in AI_ROLES:
            raise ValueError(f"ai_role must be one of {AI_ROLES}, got {self.ai_role!r}")
        # 역할별 보조 축 결속 — 무관 축은 반드시 None, 관련 축은 반드시 유효값.
        self._validate_role_axes()

    def _validate_role_axes(self) -> None:
        if self.ai_role == "advisory":
            if self.emits not in EMIT_KINDS:
                raise ValueError(f"advisory requires emits in {EMIT_KINDS}, got {self.emits!r}")
            if self.oversight_by is not None or self.human_fallback is not None:
                raise ValueError("advisory must leave oversight_by/human_fallback as None")
        elif self.ai_role == "supervised_actor":
            if self.oversight_by not in OVERSIGHT_BY:
                raise ValueError(
                    f"supervised_actor requires oversight_by in {OVERSIGHT_BY}, "
                    f"got {self.oversight_by!r}"
                )
            if self.emits is not None or self.human_fallback is not None:
                raise ValueError("supervised_actor must leave emits/human_fallback as None")
        elif self.ai_role == "decider":
            if not isinstance(self.human_fallback, bool):
                raise ValueError("decider requires human_fallback as bool")
            if self.emits is not None or self.oversight_by is not None:
                raise ValueError("decider must leave emits/oversight_by as None")
        else:  # not_operational
            if (self.emits is not None or self.oversight_by is not None
                    or self.human_fallback is not None):
                raise ValueError("not_operational must leave all sub-axes as None")

    @property
    def level(self) -> str:
        """이 구성요소의 EASA AI Level (결정적 도출)."""
        return classify(self)

    @property
    def is_operational(self) -> bool:
        """운영(추론) 구성요소 여부 (not_operational 이 아니면 True)."""
        return self.ai_role != "not_operational"


def classify(constituent: MlConstituent) -> str:
    """구성요소의 선언 속성으로부터 EASA AI Level 을 유일하게 도출한다.

    순수 함수 — 무작위성 0, 부수효과 0. ``__post_init__`` 가 축 결속을 보장하므로
    아래 분기는 전수 도달 가능하고 빠짐이 없다.
    """
    role = constituent.ai_role
    if role == "advisory":
        return "1A" if constituent.emits == "information" else "1B"
    if role == "supervised_actor":
        return "2A" if constituent.oversight_by == "human" else "2B"
    if role == "decider":
        return "3A" if constituent.human_fallback else "3B"
    return "N/A"


# 분류 규칙 매트릭스 (역할 × 보조축 → Level). 테스트가 ``classify`` 와 정확 일치 강제.
POLICY_MATRIX: tuple[tuple[str, str, str], ...] = (
    ("advisory", "information", "1A"),
    ("advisory", "recommendation", "1B"),
    ("supervised_actor", "human", "2A"),
    ("supervised_actor", "ai", "2B"),
    ("decider", "fallback", "3A"),
    ("decider", "no_fallback", "3B"),
    ("not_operational", "-", "N/A"),
)

# 무결성 게이트 — 매트릭스가 classify 의 7개 잎(leaf) 경로를 빠짐없이 인코딩함을 고정.
# 행이 하나라도 누락되면 임포트 즉시 실패(테스트 이전 단계에서 차단).
assert len(POLICY_MATRIX) == 7, "POLICY_MATRIX must encode all 7 classify leaf paths"


# SDACS ML 구성요소 카탈로그 (정본). sdacs_module 은 전부 리포 실재 경로.
# 정직 공시: 모든 운영 구성요소가 advisory → 전부 Level 1(최저 의무 계층).
CONSTITUENTS: tuple[MlConstituent, ...] = (
    MlConstituent(
        "ppo_collision", "PPO 충돌 회피 정책",
        "강화학습(SB3 PPO)이 회피 기동 후보를 제안 — 채택은 결정적 안전망",
        "advisory", "recommendation", None, None,
        "src/rl/ppo_collision.py",
        "회피 행위 *옵션* 을 권고하나 결정권은 APF+CBS 결정적 계층 → 인지 보조(1B)",
    ),
    MlConstituent(
        "deep_rl_controller", "DQN 충돌 회피 컨트롤러",
        "심층 강화학습(DQN)이 회피 행동을 제안 — 결정적 컨트롤러가 경계",
        "advisory", "recommendation", None, None,
        "simulation/deep_rl_controller.py",
        "행동 권고만 발신, 안전-결정권 비-ML 보유 → 인지 보조(1B)",
    ),
    MlConstituent(
        "rl_path_selector", "강화학습 경로 선택기",
        "Q-학습이 경로 후보를 선택 권고 — 디컨플릭션이 최종 검증",
        "advisory", "recommendation", None, None,
        "simulation/rl_path_selector.py",
        "경로 *권고*, 충돌 검증은 결정적 디컨플릭션 → 인지 보조(1B)",
    ),
    MlConstituent(
        "marl_coordinator", "다중 에이전트 RL 조정기",
        "분산 정책 조정 권고 — 관제기가 재정의 가능",
        "advisory", "recommendation", None, None,
        "simulation/marl_coordinator.py",
        "협조 행동 권고, 최종 권한 결정적 관제기 → 인지 보조(1B)",
    ),
    MlConstituent(
        "anomaly_detector", "Isolation Forest 이상 탐지",
        "이상 비행(궤적·속도·배터리)을 *플래그* — 인간/시스템이 판단",
        "advisory", "information", None, None,
        "simulation/anomaly_detector_isolation.py",
        "이상 *정보* 제공만, 행위 권고 없음 → 인간 증강(1A)",
    ),
    MlConstituent(
        "domain_randomization", "도메인 무작위화 (Sim-to-Real)",
        "학습-시점 환경 파라미터 무작위화 — 운영 추론 루프에 출력 없음",
        "not_operational", None, None, None,
        "src/training/domain_rand.py",
        "학습 기법(운영 구성요소 아님) → 분류 대상 외(N/A)",
    ),
)


# 로드 시점 무결성 게이트 — 중복 식별자를 임포트 즉시 차단.
_CATALOG_IDS = [c.constituent_id for c in CONSTITUENTS]
assert len(_CATALOG_IDS) == len(set(_CATALOG_IDS)), "duplicate constituent_id in CONSTITUENTS"


@dataclass(frozen=True)
class ClassificationReport:
    """ML 애플리케이션 분류 요약."""

    total: int                            # 전체 구성요소
    operational: int                      # 운영(추론) 구성요소
    not_operational: int                  # 비운영(학습-시점)
    max_operational_level: str            # 운영 구성요소 중 최고 Level (없으면 'N/A')
    by_level: Mapping[str, int]           # level -> count (운영만), read-only

    def __post_init__(self) -> None:
        if not isinstance(self.by_level, MappingProxyType):
            object.__setattr__(self, "by_level", MappingProxyType(dict(self.by_level)))
        if min(self.total, self.operational, self.not_operational) < 0:
            raise ValueError("counts must be non-negative")
        if self.operational + self.not_operational != self.total:
            raise ValueError(
                f"operational ({self.operational}) + not_operational "
                f"({self.not_operational}) != total ({self.total})"
            )
        if self.max_operational_level not in AI_LEVELS:
            raise ValueError(f"max_operational_level must be in {AI_LEVELS}")
        invalid = set(self.by_level.keys()) - set(AI_LEVELS)
        if invalid:
            raise ValueError(f"by_level contains unknown levels: {sorted(invalid)}")
        # by_level 은 *관측된* 운영 Level 만 담는다 — 0/음수 카운트 항목은 금지(계약 명확화).
        if any(v <= 0 for v in self.by_level.values()):
            raise ValueError("by_level counts must be positive (observed levels only)")
        # by_level(운영만) 합은 operational 과 일치해야 한다.
        if sum(self.by_level.values()) != self.operational:
            raise ValueError(
                f"by_level sum ({sum(self.by_level.values())}) != operational "
                f"({self.operational})"
            )

    @property
    def all_operational_level1(self) -> bool:
        """모든 운영 구성요소가 Level 1(1A/1B)이면 True — SDACS 의 정직한 귀결."""
        if not self.operational:
            return False
        return all(level in ("1A", "1B") for level, n in self.by_level.items() if n)

    @property
    def max_assurance_burden(self) -> int:
        """운영 구성요소 최고 Level 의 어슈어런스 의무 강도(0-6)."""
        return _LEVEL_INFO[self.max_operational_level][1]


def find_constituent(constituent_id: str) -> MlConstituent:
    """식별자로 구성요소를 조회한다. 없으면 KeyError."""
    for c in CONSTITUENTS:
        if c.constituent_id == constituent_id:
            return c
    raise KeyError(f"unknown ML constituent: {constituent_id!r}")


def operational_constituents() -> tuple[MlConstituent, ...]:
    """운영(추론) 구성요소를 식별자 정렬로 반환한다."""
    return tuple(
        sorted((c for c in CONSTITUENTS if c.is_operational), key=lambda c: c.constituent_id)
    )


def constituents_by_level(level: str) -> tuple[MlConstituent, ...]:
    """주어진 Level 로 분류된 구성요소를 식별자 정렬로 반환한다."""
    if level not in AI_LEVELS:
        raise ValueError(f"level must be one of {AI_LEVELS}, got {level!r}")
    return tuple(
        sorted((c for c in CONSTITUENTS if c.level == level), key=lambda c: c.constituent_id)
    )


def _level_rank(level: str) -> int:
    """Level 자율 순위(정렬용). N/A 는 운영 비교에서 제외되므로 -1."""
    return AI_LEVELS.index(level) if level != "N/A" else -1


def classification_report() -> ClassificationReport:
    """전체 분류 현황을 집계한 결정적 리포트를 생성한다."""
    operational = [c for c in CONSTITUENTS if c.is_operational]
    by_level: dict[str, int] = {}
    for c in operational:
        by_level[c.level] = by_level.get(c.level, 0) + 1
    max_level = max((c.level for c in operational), key=_level_rank) if operational else "N/A"
    return ClassificationReport(
        total=len(CONSTITUENTS),
        operational=len(operational),
        not_operational=len(CONSTITUENTS) - len(operational),
        max_operational_level=max_level,
        by_level=MappingProxyType(by_level),
    )


def classification_matrix() -> tuple[dict[str, object], ...]:
    """도구 간 교환용 분류 매트릭스를 (Level 순위, 식별자) 정렬 행으로 반환한다."""
    ordered = sorted(CONSTITUENTS, key=lambda c: (_level_rank(c.level), c.constituent_id))
    return tuple(
        MappingProxyType({
            "constituent_id": c.constituent_id,
            "name": c.name,
            "function": c.function,
            "ai_role": c.ai_role,
            "level": c.level,
            "sdacs_module": c.sdacs_module,
            "rationale": c.rationale,
        })
        for c in ordered
    )


def manifest() -> dict[str, object]:
    """JSON 직렬화 가능한 분류 매니페스트(도구 간 교환용)."""
    r = classification_report()
    return {
        "phase": 452,
        "scheme": "EASA Concept Paper Issue 02 (2024) AI Level 1/2/3",
        "total": r.total,
        "operational": r.operational,
        "not_operational": r.not_operational,
        "max_operational_level": r.max_operational_level,
        "all_operational_level1": r.all_operational_level1,
        "by_level": dict(r.by_level),
        "constituents": [dict(row) for row in classification_matrix()],
    }


def _format_constituents() -> str:
    lines = ["SDACS ML 애플리케이션 분류 (EASA AI Level)", ""]
    for row in classification_matrix():
        lines.append(
            f"[{str(row['level']):3}] {row['constituent_id']:22} {row['name']}"
        )
        lines.append(f"      역할={row['ai_role']:16} → {row['sdacs_module']}")
        lines.append(f"      {row['rationale']}")
    return "\n".join(lines)


def _format_report() -> str:
    r = classification_report()
    lines = [
        "SDACS ML 애플리케이션 분류 요약 (ODYSSEY Phase 452)",
        "",
        f"구성요소     : 총 {r.total} (운영 {r.operational} · 비운영 {r.not_operational})",
        f"최고 운영 Level : {r.max_operational_level} "
        f"(어슈어런스 의무 강도 {r.max_assurance_burden}/6)",
        "",
        "운영 Level 분포:",
    ]
    for level in AI_LEVELS:
        n = r.by_level.get(level, 0)
        if n:
            lines.append(f"  {_LEVEL_INFO[level][0]}: {n}")
    lines.append("")
    if r.all_operational_level1:
        lines.append(
            "정직 공시: 모든 운영 ML 이 Level 1(최저 의무 계층)이다. 이는 결함이 아니라"
        )
        lines.append(
            "  ML 을 안전-크리티컬 권한에서 배제(결정적 안전망 보유)한 아키텍처의 정직한 귀결이며,"
        )
        lines.append(
            "  Phase 451 이 갭으로 지목한 'ML Level 분류 기록 부재' 를 본 모듈이 해소한다."
        )
    return "\n".join(lines)


def _format_levels() -> str:
    lines = ["EASA AI Level 체계 (자율 수준·러닝 어슈어런스 의무 강도)", ""]
    for level in AI_LEVELS:
        desc, burden = _LEVEL_INFO[level]
        lines.append(f"  [{level:3}] (의무 {burden}/6) {desc}")
    return "\n".join(lines)


def _format_matrix() -> str:
    lines = ["분류 규칙 매트릭스 (역할 × 보조축 → Level)", ""]
    for role, axis, level in POLICY_MATRIX:
        lines.append(f"  {role:18} {axis:14} → {level}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ML 애플리케이션 분류 게이트 (EASA AI Level, ODYSSEY Phase 452)"
    )
    parser.add_argument("--constituents", action="store_true", help="구성요소+분류 출력")
    parser.add_argument("--report", action="store_true", help="분류 요약 출력")
    parser.add_argument("--levels", action="store_true", help="Level 체계·의무 출력")
    parser.add_argument("--matrix", action="store_true", help="분류 규칙 매트릭스 출력")
    parser.add_argument("--manifest", action="store_true", help="JSON 매니페스트 출력")
    args = parser.parse_args(argv)

    if args.constituents:
        print(_format_constituents())
    elif args.report:
        print(_format_report())
    elif args.levels:
        print(_format_levels())
    elif args.matrix:
        print(_format_matrix())
    elif args.manifest:
        print(json.dumps(manifest(), ensure_ascii=False, indent=2))
    else:
        print(_format_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

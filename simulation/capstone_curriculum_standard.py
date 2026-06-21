"""ODYSSEY Phase 468 — 대학 캡스톤 표준 커리큘럼 제안 적합성 게이트.

Standards & Policy 트랙(Phase 461-480)에서 SDACS 를 *워크드 예제* 로 삼는 15주
학부 캡스톤 디자인 표준 커리큘럼 제안서가 (1) 강의 자료 완비도와 (2) 한국공학교육
인증원(ABEEK) 프로그램 학습성과 커버리지를 동시에 충족했는가를 결정적으로 판정하고,
현재의 *실제 채택 상태* 를 정직하게 공시한다.

GENESIS Phase 383(15주 강의 슬라이드 패키지)이 *슬라이드 산출물 자체* 라면, 본
모듈(468)은 그 슬라이드를 포함한 리포 교육 자산이 *표준 커리큘럼으로 제안될 형식
요건* 을 갖췄는가를 판정하는 게이트다 — 즉 "표준으로 제안할 준비가 됐는가" 와
"제안·채택됐는가" 를 분리해 표면화한다.

자매 모듈과의 경계 (중복 없음)
------------------------------
- Phase 463(``k_drone_policy_proposal``) 는 *단일 정책 제안서* 의 섹션 완비도만
  판정한다(단일 차원: criticality).
- 본 모듈(468)은 그와 달리 *두 차원* 을 교차 검증한다: 주차별 강의 단원의 자료
  완비도(material) **그리고** 단원이 커버하는 ABEEK 학습성과의 *프로그램 차원
  커버리지*. 모든 단원이 작성돼도 필수 학습성과 하나가 어느 단원에도 매핑되지
  않으면 표준 제안 준비가 안 된 것으로 판정한다 — 463 에는 없는 교차 불변식.

정직 공시 (CLAUDE.md)
--------------------
1. ``status`` 가 ``DRAFTED`` 인 단원은 반드시 디스크에 실재하는 강의 자산을
   인용한다 — 자료 없는 작성 주장을 구조적으로 금지한다(``MISSING`` 은 인용 금지).
   게이트의 가치는 작성 주장보다 *미작성 단원·미커버 학습성과의 가시화* 에 있다.
2. ``readiness`` 판정(표준 제안 준비도)과 ``adoption_status``(실제 채택 여부)는
   *독립* 이다. 모든 단원이 작성돼 ``READY_FOR_PROPOSAL`` 여도, 외부 대학·ABEEK
   채택은 본 리포 범위 밖이므로 현 상태는 항상 ``NOT_PROPOSED`` 로 정직 공시한다.
3. ABEEK 학습성과 매핑은 *제안* 이며 인증원의 심사·인정을 보장하지 않는다.

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python simulation/capstone_curriculum_standard.py --matrix    # 주차별 단원 매트릭스
    python simulation/capstone_curriculum_standard.py --report    # 준비도·채택 상태 요약
    python simulation/capstone_curriculum_standard.py --gaps      # 미작성 단원·미커버 학습성과
    python simulation/capstone_curriculum_standard.py --coverage  # ABEEK 학습성과 커버리지
    python simulation/capstone_curriculum_standard.py --adoption  # 채택 상태만
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

# 표준 캡스톤 학기 주차 수 (GENESIS 383 = 15주 커리큘럼).
TOTAL_WEEKS: int = 15

# 단원 작성 상태 (3값). DRAFTED=자료 완비·OUTLINED=개요만·MISSING=미작성.
STATUSES: tuple[str, ...] = ("DRAFTED", "OUTLINED", "MISSING")

# 가중 점수: 작성 1.0·개요 0.5·미작성 0.0.
_STATUS_WEIGHT: dict[str, float] = {"DRAFTED": 1.0, "OUTLINED": 0.5, "MISSING": 0.0}

# 한국공학교육인증원(ABEEK) KEC2015 프로그램 학습성과 (PO1-PO12) 중 본 캡스톤
# 표준이 다루는 학습성과 코드와 한 줄 설명. 매핑은 제안이며 인증을 보장하지 않는다.
ABEEK_OUTCOMES: Mapping[str, str] = MappingProxyType({
    "PO1": "수학·기초과학·공학 지식의 응용",
    "PO2": "자료의 분석·해석 및 실험 설계·수행",
    "PO4": "공학 문제의 인식·정식화 및 창의적 해결",
    "PO5": "공학 실무에 필요한 기술·도구·정보기술 활용",
    "PO6": "공학적 해결책의 보건·안전·경제·환경·지속가능성 영향 이해",
    "PO7": "효과적 의사소통·발표 능력",
    "PO9": "팀 구성원으로서 협동 능력",
    "PO10": "공학적 해결책이 사회에 미치는 영향 이해",
    "PO12": "기술 변화에 대응하는 자기주도·평생학습 능력",
})

# 표준 제안에 *반드시* 커버돼야 하는 핵심 학습성과 (캡스톤 인증 필수 차원).
# 나머지(PO7·PO9·PO10·PO12)는 권장 — 미커버해도 NOT_READY 로 떨어뜨리지 않는다.
REQUIRED_OUTCOMES: frozenset[str] = frozenset({"PO1", "PO2", "PO4", "PO5", "PO6"})

# 공허 참 방지: 필수 학습성과가 비면 "미커버 없음"이 공허하게 참이 돼 빈 커리큘럼이
# READY 로 오선언될 수 있다(자매 k_drone_policy_proposal 의 total>0 가드와 동형).
assert REQUIRED_OUTCOMES, "REQUIRED_OUTCOMES must not be empty — vacuous-READY guard"

# 준비도 판정 (3값).
VERDICT_READY = "READY_FOR_PROPOSAL"
VERDICT_PARTIAL = "PARTIAL"
VERDICT_NOT_READY = "NOT_READY"

# 채택 상태 단조 진행 (현재 = NOT_PROPOSED, 외부 절차 의존).
ADOPTION_STAGES: tuple[str, ...] = (
    "NOT_PROPOSED",
    "PROPOSED",
    "PILOTED",
    "ADOPTED",
)


@dataclass(frozen=True)
class CurriculumUnit:
    """캡스톤 표준 커리큘럼의 한 강의 단원(불변).

    강의 *내용* 의 산문은 인용 자산(슬라이드·가이드 등)이 유일 출처이며, 본 객체는
    주차 배정·학습성과 매핑·작성 상태·증거 경로만 보유해 자산을 가리킨다.

    Attributes:
        unit_id: 안정 식별자 (U01..).
        weeks: 배정 주차 튜플 (1..TOTAL_WEEKS, 단원 간 비중복).
        title: 단원 제목.
        outcomes: 커버하는 ABEEK 학습성과 코드 튜플 (ABEEK_OUTCOMES 의 키).
        status: DRAFTED·OUTLINED·MISSING.
        evidence: 강의 자산 리포 경로 (MISSING 이면 빈 튜플).
        summary: 한 줄 설명.
    """

    unit_id: str
    weeks: tuple[int, ...]
    title: str
    outcomes: tuple[str, ...]
    status: str
    evidence: tuple[str, ...]
    summary: str

    def __post_init__(self) -> None:
        if not self.unit_id or self.unit_id != self.unit_id.strip():
            raise ValueError("unit_id must be non-empty and unpadded")
        if " " in self.unit_id:
            raise ValueError("unit_id must not contain internal spaces")
        if not self.title or not self.title.strip():
            raise ValueError("title must be a non-empty string")
        if not self.summary or not self.summary.strip():
            raise ValueError("summary must be a non-empty string")
        if self.status not in STATUSES:
            raise ValueError(f"status must be one of {STATUSES}, got {self.status!r}")
        if not isinstance(self.weeks, tuple) or not self.weeks:
            raise ValueError("weeks must be a non-empty tuple")
        if len(self.weeks) != len(set(self.weeks)):
            raise ValueError(f"unit {self.unit_id!r} has duplicate weeks")
        for wk in self.weeks:
            if not isinstance(wk, int) or not 1 <= wk <= TOTAL_WEEKS:
                raise ValueError(
                    f"week must be int in 1..{TOTAL_WEEKS}, got {wk!r}"
                )
        if tuple(sorted(self.weeks)) != self.weeks:
            raise ValueError(f"unit {self.unit_id!r} weeks must be sorted ascending")
        # 다주차 단원은 연속이어야 한다 — _weeks_label 의 'W01-04' 표기가 비연속
        # 주차를 잘못 포괄 표시하지 않도록 모델 차원에서 차단.
        if len(self.weeks) > 1:
            contiguous = tuple(range(self.weeks[0], self.weeks[-1] + 1))
            if self.weeks != contiguous:
                raise ValueError(f"unit {self.unit_id!r} weeks must be contiguous")
        if not isinstance(self.outcomes, tuple) or not self.outcomes:
            raise ValueError("outcomes must be a non-empty tuple")
        if len(self.outcomes) != len(set(self.outcomes)):
            raise ValueError(f"unit {self.unit_id!r} has duplicate outcomes")
        for code in self.outcomes:
            if code not in ABEEK_OUTCOMES:
                raise ValueError(f"unknown ABEEK outcome code: {code!r}")
        if not isinstance(self.evidence, tuple):
            raise ValueError("evidence must be a tuple of repo paths")
        for path in self.evidence:
            if not path or path != path.strip():
                raise ValueError(f"evidence path must be non-empty and unpadded: {path!r}")
        # 정직성 결속: DRAFTED 는 반드시 증거 인용·MISSING 은 증거 인용 금지.
        if self.status == "DRAFTED" and not self.evidence:
            raise ValueError(f"unit {self.unit_id!r} is DRAFTED but cites no evidence")
        if self.status == "MISSING" and self.evidence:
            raise ValueError(f"unit {self.unit_id!r} is MISSING but cites evidence")

    @property
    def is_drafted(self) -> bool:
        """자료 완비 여부."""
        return self.status == "DRAFTED"

    @property
    def weight(self) -> float:
        """가중 점수 기여 (DRAFTED 1.0·OUTLINED 0.5·MISSING 0.0)."""
        return _STATUS_WEIGHT[self.status]


# 동반 표준 문서(커리큘럼 본문의 유일 출처).
_CURRICULUM_DOC = "docs/standards/CAPSTONE_CURRICULUM_STANDARD.md"

# 캡스톤 표준 커리큘럼 단원 레지스트리 (정본, 15주 진행 순서).
# 증거는 리포 실재 강의 자산. DRAFTED 는 워크드 예제 자료가 실재하는 단원.
CURRICULUM_UNITS: tuple[CurriculumUnit, ...] = (
    CurriculumUnit(
        "U01", (1, 2), "공역 통제 문제 정의와 시스템 개요",
        ("PO1", "PO4", "PO10"), "DRAFTED",
        (_CURRICULUM_DOC, "docs/slides_deck.md", "README.md"),
        "군집 드론 공역 통제 문제 정식화 + 4계층 아키텍처 개관 — 문제 인식·사회 영향",
    ),
    CurriculumUnit(
        "U02", (3, 4), "이산 사건 시뮬레이션과 드론 에이전트 모델링",
        ("PO1", "PO5"), "DRAFTED",
        (_CURRICULUM_DOC, "docs/architecture.md"),
        "SimPy 10Hz 드론 에이전트 + 1Hz 관제 모델링 — 도구·공학 지식 응용",
    ),
    CurriculumUnit(
        "U03", (5, 6), "충돌 회피 알고리즘 (APF·CBS) 설계",
        ("PO1", "PO4"), "DRAFTED",
        (_CURRICULUM_DOC, "docs/APF_CONVERGENCE_PROOF.md",
         "docs/CBS_COMPLETENESS_OPTIMALITY.md"),
        "인공 포텐셜장·충돌 기반 탐색의 수렴·완전성 — 창의적 문제 해결",
    ),
    CurriculumUnit(
        "U04", (7,), "5계층 안전망과 형식 명세",
        ("PO1", "PO6"), "DRAFTED",
        (_CURRICULUM_DOC, "docs/SAFETY_NET_TLA_SPEC.md",
         "docs/standards/SWARM_SAFETY_STANDARD_WHITEPAPER.md"),
        "안전 계층 우선순위 TLA+ 명세 — 안전·지속가능성 영향 이해",
    ),
    CurriculumUnit(
        "U05", (8,), "중간 설계 검토 및 발표",
        ("PO7", "PO9"), "DRAFTED",
        (_CURRICULUM_DOC, "docs/presentation/DEFENSE_KIT.md"),
        "설계 리뷰 발표·팀 역할 분담 — 의사소통·협동",
    ),
    CurriculumUnit(
        "U06", (9, 10), "실험 설계: 시나리오·Monte Carlo·KPI",
        ("PO2", "PO5"), "DRAFTED",
        (_CURRICULUM_DOC, "docs/TEST_PROCEDURES.md",
         "config/scenario_params/nominal_baseline.yaml"),
        "표준 시나리오 + MC 스윕 + 충돌 해결률 KPI — 실험 설계·수행·자료 해석",
    ),
    CurriculumUnit(
        "U07", (11,), "Sim-to-Real: 하드웨어 인 더 루프",
        ("PO5", "PO12"), "DRAFTED",
        (_CURRICULUM_DOC, "docs/hardware/README.md",
         "docs/hardware/pixhawk_sdacs_hitl.md"),
        "Pixhawk·Jetson HITL 파이프라인 — 신기술 도구 활용·자기주도 학습",
    ),
    CurriculumUnit(
        "U08", (12,), "재현성과 연구 윤리",
        ("PO6", "PO12"), "DRAFTED",
        (_CURRICULUM_DOC, "docs/REPRODUCIBILITY.md"),
        "의존성 핀·컨테이너 다이제스트 재현 — 지속가능성·평생학습",
    ),
    CurriculumUnit(
        "U09", (13,), "논문 작성과 학술 기여",
        ("PO2", "PO7"), "OUTLINED",
        (_CURRICULUM_DOC, "docs/paper/contribution_outline.md"),
        "IROS 형식 논문 outline — 자료 해석·학술 의사소통 (실측 그래프 보강 필요)",
    ),
    CurriculumUnit(
        "U10", (14, 15), "최종 발표·산학 연계와 사업화",
        ("PO7", "PO10"), "DRAFTED",
        (_CURRICULUM_DOC, "docs/track_f/README.md",
         "docs/government_presentation_script.md"),
        "최종 발표 + Track F 산학 예산·LOI — 의사소통·사회 영향",
    ),
)


# 로드 시점 무결성 게이트 — 중복 식별자·주차 충돌을 임포트 시 즉시 차단.
_REGISTRY_IDS = [u.unit_id for u in CURRICULUM_UNITS]
assert len(_REGISTRY_IDS) == len(set(_REGISTRY_IDS)), "duplicate unit_id"
_ALL_WEEKS = [wk for u in CURRICULUM_UNITS for wk in u.weeks]
assert len(_ALL_WEEKS) == len(set(_ALL_WEEKS)), "overlapping weeks across units"

# 현 표준 커리큘럼의 실제 채택 상태 (외부 절차 의존, 정직 공시).
CURRENT_ADOPTION: str = "NOT_PROPOSED"


def _repo_root() -> Path:
    """리포 루트 경로(이 파일의 상위 디렉터리)."""
    return Path(__file__).resolve().parent.parent


def evidence_present(unit: CurriculumUnit, repo_root: str | Path) -> bool:
    """단원의 모든 강의 자산이 디스크에 실재하는지 결정적으로 확인한다."""
    root = Path(repo_root)
    return all((root / rel).is_file() for rel in unit.evidence)


@dataclass(frozen=True)
class CurriculumReadiness:
    """캡스톤 표준 커리큘럼 전체의 제안 준비도 판정 결과(불변)."""

    verdict: str
    score: float                            # 가중 작성 비율 0.0~1.0
    adoption_status: str                    # 실제 채택 상태 (NOT_PROPOSED 등)
    drafted: tuple[str, ...]                # 자료 완비 단원 id(정렬)
    incomplete: tuple[str, ...]             # 미완 단원 id(정렬)
    covered_outcomes: tuple[str, ...]       # 커버된 ABEEK 학습성과(정렬)
    uncovered_required: tuple[str, ...]     # 미커버 *필수* 학습성과(정렬)
    weeks_covered: int                      # 단원이 배정된 주차 수
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.verdict not in (VERDICT_READY, VERDICT_PARTIAL, VERDICT_NOT_READY):
            raise ValueError(f"unexpected verdict {self.verdict!r}")
        if self.adoption_status not in ADOPTION_STAGES:
            raise ValueError(
                f"adoption_status must be one of {ADOPTION_STAGES}, "
                f"got {self.adoption_status!r}"
            )
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be in [0, 1], got {self.score}")
        if not 0 <= self.weeks_covered <= TOTAL_WEEKS:
            raise ValueError(f"weeks_covered out of range: {self.weeks_covered}")

    def is_ready(self) -> bool:
        """표준 제안 준비가 완료됐는가(채택 여부와 무관)."""
        return self.verdict == VERDICT_READY

    def is_adopted(self) -> bool:
        """실제로 외부 대학·인증원에 채택됐는가."""
        return self.adoption_status == "ADOPTED"

    def summary(self) -> str:
        """사람이 읽는 한 줄 요약."""
        pct = f"{self.score * 100:.1f}%"
        return (
            f"{self.verdict} ({pct}) · 채택: {self.adoption_status} — "
            f"{'; '.join(self.reasons)}"
        )


def find_unit(unit_id: str) -> CurriculumUnit:
    """식별자로 단원을 조회한다. 없으면 KeyError."""
    for unit in CURRICULUM_UNITS:
        if unit.unit_id == unit_id:
            return unit
    raise KeyError(f"unknown curriculum unit: {unit_id!r}")


def units_by_status(status: str) -> tuple[CurriculumUnit, ...]:
    """작성 상태별 단원을 식별자 정렬로 반환한다."""
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}, got {status!r}")
    return tuple(
        sorted((u for u in CURRICULUM_UNITS if u.status == status),
               key=lambda u: u.unit_id)
    )


def units_by_outcome(code: str) -> tuple[CurriculumUnit, ...]:
    """특정 ABEEK 학습성과를 커버하는 단원을 식별자 정렬로 반환한다."""
    if code not in ABEEK_OUTCOMES:
        raise ValueError(f"unknown ABEEK outcome code: {code!r}")
    return tuple(
        sorted((u for u in CURRICULUM_UNITS if code in u.outcomes),
               key=lambda u: u.unit_id)
    )


def _covered_outcomes(repo_root: str | Path) -> set[str]:
    """증거가 실재하는 DRAFTED 단원이 커버하는 학습성과 집합(결정적).

    OUTLINED·MISSING 단원이나 증거 부재 단원의 학습성과는 *커버로 인정하지
    않는다* — 거짓 커버를 금지한다.
    """
    root = Path(repo_root)
    covered: set[str] = set()
    for unit in CURRICULUM_UNITS:
        if unit.is_drafted and bool(unit.evidence) and evidence_present(unit, root):
            covered.update(unit.outcomes)
    return covered


def _verdict_for(has_units: bool, has_incomplete: bool, uncovered_required: bool) -> str:
    """판정 핵심 규칙(준비도의 권위 있는 구현).

    빈 커리큘럼은 READY 가 아니다(공허 참 차단). 필수 학습성과가 하나라도
    미커버이면 NOT_READY(교차 불변식), 단원이 하나라도 미완(자료 미작성·증거
    누락)이면 PARTIAL, 둘 다 충족이면 READY_FOR_PROPOSAL.
    """
    if not has_units:
        return VERDICT_NOT_READY
    if uncovered_required:
        return VERDICT_NOT_READY
    if has_incomplete:
        return VERDICT_PARTIAL
    return VERDICT_READY


def assess_curriculum(repo_root: str | Path | None = None) -> CurriculumReadiness:
    """표준 커리큘럼의 제안 준비도를 리포에 대해 결정적으로 판정한다.

    단원은 ``DRAFTED`` 이면서 인용 강의 자산이 디스크에 실재해야만 자료 완비로
    본다. 점수는 (증거 실재 가정 하의) 작성 가중치 합을 전체 단원 수로 나눈 비율
    (소수 넷째 자리 반올림 — 결정적). ``adoption_status`` 는 ``repo_root`` 와
    무관하게 ``CURRENT_ADOPTION``(외부 절차 의존)으로 정직 공시한다.
    """
    root = Path(repo_root) if repo_root is not None else _repo_root()

    drafted: list[str] = []
    incomplete: list[str] = []
    weeks_covered: set[int] = set()
    score_sum = 0.0

    for unit in CURRICULUM_UNITS:
        weeks_covered.update(unit.weeks)
        present = bool(unit.evidence) and evidence_present(unit, root)
        effective_drafted = unit.is_drafted and present
        score_sum += unit.weight if present else 0.0
        if effective_drafted:
            drafted.append(unit.unit_id)
        else:
            incomplete.append(unit.unit_id)

    covered = _covered_outcomes(root)
    uncovered_required = REQUIRED_OUTCOMES - covered

    total = len(CURRICULUM_UNITS)
    score = round(score_sum / total, 4) if total else 0.0
    verdict = _verdict_for(
        has_units=(total > 0),
        has_incomplete=bool(incomplete),
        uncovered_required=bool(uncovered_required),
    )

    reasons: list[str] = []
    if uncovered_required:
        reasons.append(f"필수 학습성과 미커버 {len(uncovered_required)}건")
    if incomplete:
        reasons.append(f"단원 미완 {len(incomplete)}건")
    if not reasons:
        reasons.append("전 단원 작성 + 필수 학습성과 전부 커버")
    reasons.append(f"채택 상태 {CURRENT_ADOPTION}")

    return CurriculumReadiness(
        verdict=verdict,
        score=score,
        adoption_status=CURRENT_ADOPTION,
        drafted=tuple(sorted(drafted)),
        incomplete=tuple(sorted(incomplete)),
        covered_outcomes=tuple(sorted(covered)),
        uncovered_required=tuple(sorted(uncovered_required)),
        weeks_covered=len(weeks_covered),
        reasons=tuple(reasons),
    )


def coverage_matrix(repo_root: str | Path | None = None) -> tuple[dict[str, object], ...]:
    """ABEEK 학습성과별 커버 단원·필수 여부·커버 상태를 코드 순서로 반환한다."""
    root = Path(repo_root) if repo_root is not None else _repo_root()
    covered = _covered_outcomes(root)
    rows: list[dict[str, object]] = []
    for code in ABEEK_OUTCOMES:
        units = [u.unit_id for u in units_by_outcome(code)]
        rows.append({
            "outcome": code,
            "description": ABEEK_OUTCOMES[code],
            "required": code in REQUIRED_OUTCOMES,
            "covered": code in covered,
            "units": units,
        })
    return tuple(rows)


def curriculum_matrix() -> tuple[dict[str, object], ...]:
    """도구 간 교환용 단원 매트릭스를 정의 순서로 반환한다."""
    return tuple(
        {
            "unit_id": u.unit_id,
            "weeks": list(u.weeks),
            "title": u.title,
            "outcomes": list(u.outcomes),
            "status": u.status,
            "evidence": list(u.evidence),
            "summary": u.summary,
        }
        for u in CURRICULUM_UNITS
    )


_STATUS_MARK: dict[str, str] = {"DRAFTED": "✓", "OUTLINED": "◐", "MISSING": "✗"}


def _weeks_label(weeks: tuple[int, ...]) -> str:
    if len(weeks) == 1:
        return f"W{weeks[0]:02d}"
    return f"W{weeks[0]:02d}-{weeks[-1]:02d}"


def _format_matrix() -> str:
    lines = ["캡스톤 표준 커리큘럼 단원 매트릭스 (15주 · ABEEK 매핑)", ""]
    for u in CURRICULUM_UNITS:
        mark = _STATUS_MARK[u.status]
        lines.append(f"[{_weeks_label(u.weeks)}] {mark} {u.title}")
        lines.append(f"      학습성과: {', '.join(u.outcomes)}")
        lines.append(f"      {u.summary}")
        lines.append(f"      → {', '.join(u.evidence) or '—'}")
    return "\n".join(lines)


def _format_report() -> str:
    r = assess_curriculum()
    lines = [
        "대학 캡스톤 표준 커리큘럼 — 제안 준비도 요약",
        "",
        f"준비도 판정 : {r.verdict} ({r.score * 100:.0f}%)",
        f"채택 상태   : {r.adoption_status} (외부 절차 의존 — 정직 공시)",
        f"자료 완비   : {len(r.drafted)}/{len(CURRICULUM_UNITS)} 단원",
        f"주차 커버   : {r.weeks_covered}/{TOTAL_WEEKS} 주",
        f"학습성과    : {len(r.covered_outcomes)}/{len(ABEEK_OUTCOMES)} 커버",
    ]
    if r.uncovered_required:
        lines.append(f"필수 미커버 : {', '.join(r.uncovered_required)}")
    if r.incomplete:
        lines.append(f"단원 미완   : {', '.join(r.incomplete)}")
    return "\n".join(lines)


def _format_coverage() -> str:
    lines = ["ABEEK 학습성과 커버리지 (필수 ★)", ""]
    for row in coverage_matrix():
        star = "★" if row["required"] else " "
        mark = "✓" if row["covered"] else "✗"
        units = ", ".join(row["units"]) or "—"  # type: ignore[arg-type]
        lines.append(f"{star} {mark} {row['outcome']} {row['description']}")
        lines.append(f"      ← {units}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="대학 캡스톤 표준 커리큘럼 제안 적합성 게이트 (ODYSSEY Phase 468)"
    )
    parser.add_argument("--matrix", action="store_true", help="주차별 단원 매트릭스 출력")
    parser.add_argument("--report", action="store_true", help="준비도·채택 상태 요약 출력")
    parser.add_argument("--gaps", action="store_true", help="미작성 단원·미커버 학습성과 출력")
    parser.add_argument("--coverage", action="store_true", help="ABEEK 학습성과 커버리지 출력")
    parser.add_argument("--adoption", action="store_true", help="채택 상태만 출력")
    args = parser.parse_args(argv)

    if args.matrix:
        print(_format_matrix())
    elif args.report:
        print(_format_report())
    elif args.coverage:
        print(_format_coverage())
    elif args.gaps:
        r = assess_curriculum()
        if not r.incomplete and not r.uncovered_required:
            print("미작성 단원·미커버 필수 학습성과 없음 (준비 완료)")
        for sid in r.incomplete:
            unit = find_unit(sid)
            print(f"단원 {sid} ({unit.status}): {unit.title}")
        for code in r.uncovered_required:
            print(f"미커버 필수 학습성과 {code}: {ABEEK_OUTCOMES[code]}")
    elif args.adoption:
        print(CURRENT_ADOPTION)
    else:
        print(_format_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

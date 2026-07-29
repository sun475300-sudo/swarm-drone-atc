"""GENESIS Phase 391 -- 고교·일반인 체험판 단순화 모드.

비전문가(고교생·일반인)를 위한 SDACS 시뮬레이터 체험 모듈.
전문 용어를 쉬운 한국어로 번역하고, 난이도별 프리셋과
가이드 시나리오를 제공합니다.

구성 요소
---------
1. **DifficultyPreset**: 난이도별 시뮬레이션 파라미터 프리셋
2. **GlossaryEntry**: 전문 용어 → 쉬운 설명 사전
3. **GuidedScenario**: 단계별 안내 시나리오
4. **SimplifiedMetric**: 단순화된 결과 지표
5. **DemoExperience**: 전체 체험판 패키지

설계 원칙
---------
- frozen dataclass, 결정적, 부수효과 0
- 전문 용어 → "이해하기 쉬운 한국어" 매핑
- 난이도: 쉬움(5대) → 보통(20대) → 어려움(50대)

CLI:
    python simulation/demo_experience.py --presets         # 난이도 프리셋 목록
    python simulation/demo_experience.py --preset easy     # 특정 프리셋 상세
    python simulation/demo_experience.py --glossary        # 용어 사전
    python simulation/demo_experience.py --scenarios       # 가이드 시나리오 목록
    python simulation/demo_experience.py --scenario 1      # 특정 시나리오 상세
    python simulation/demo_experience.py --explain metric  # 지표 쉬운 설명
    python simulation/demo_experience.py --json            # JSON 출력
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

VALID_PRESET_IDS: tuple[str, ...] = ("easy", "normal", "hard")


@dataclass(frozen=True)
class DifficultyPreset:
    """난이도별 시뮬레이션 파라미터 프리셋."""

    preset_id: str
    name: str
    description: str
    drone_count: int
    duration_sec: int
    wind_speed_ms: float
    conflict_probability: str
    recommended_for: str

    def __post_init__(self) -> None:
        if self.preset_id not in VALID_PRESET_IDS:
            raise ValueError(f"Invalid preset_id: {self.preset_id}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "preset_id": self.preset_id,
            "name": self.name,
            "description": self.description,
            "drone_count": self.drone_count,
            "duration_sec": self.duration_sec,
            "wind_speed_ms": self.wind_speed_ms,
            "conflict_probability": self.conflict_probability,
            "recommended_for": self.recommended_for,
        }


DIFFICULTY_PRESETS: tuple[DifficultyPreset, ...] = (
    DifficultyPreset(
        preset_id="easy",
        name="쉬움",
        description="드론 5대가 넓은 하늘에서 천천히 이동합니다. 충돌 위험이 거의 없어 안전하게 관찰할 수 있습니다.",
        drone_count=5,
        duration_sec=30,
        wind_speed_ms=2.0,
        conflict_probability="낮음",
        recommended_for="처음 접하는 고등학생, 시뮬레이터 입문자",
    ),
    DifficultyPreset(
        preset_id="normal",
        name="보통",
        description="드론 20대가 도시 상공에서 임무를 수행합니다. 가끔 서로 가까이 지나가면서 충돌 회피 시스템이 작동합니다.",
        drone_count=20,
        duration_sec=60,
        wind_speed_ms=5.0,
        conflict_probability="보통",
        recommended_for="기본 개념을 이해한 학생, 드론에 관심 있는 일반인",
    ),
    DifficultyPreset(
        preset_id="hard",
        name="어려움",
        description="드론 50대가 좁은 공역에서 동시에 비행합니다. 강한 바람과 빈번한 충돌 상황에서 시스템의 한계를 시험합니다.",
        drone_count=50,
        duration_sec=120,
        wind_speed_ms=12.0,
        conflict_probability="높음",
        recommended_for="시뮬레이션 경험자, 공학 전공 학생",
    ),
)

_PRESET_MAP: MappingProxyType[str, DifficultyPreset] = MappingProxyType(
    {p.preset_id: p for p in DIFFICULTY_PRESETS}
)


@dataclass(frozen=True)
class GlossaryEntry:
    """전문 용어 → 쉬운 설명."""

    term: str
    easy_name: str
    explanation: str
    example: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "term": self.term,
            "easy_name": self.easy_name,
            "explanation": self.explanation,
            "example": self.example,
        }


GLOSSARY: tuple[GlossaryEntry, ...] = (
    GlossaryEntry(
        term="APF (Artificial Potential Field)",
        easy_name="자동 충돌 회피",
        explanation="드론이 서로 가까워지면 보이지 않는 힘이 밀어내서 부딪히지 않게 합니다. 마치 같은 극의 자석이 서로 밀어내는 것과 비슷합니다.",
        example="두 드론이 교차로에서 만나면, APF가 한 대를 살짝 옆으로 밀어서 안전 거리를 유지합니다.",
    ),
    GlossaryEntry(
        term="CPA (Closest Point of Approach)",
        easy_name="가장 가까워지는 순간 예측",
        explanation="두 드론이 현재 속도로 계속 날면 언제, 얼마나 가까워지는지 미리 계산합니다. 90초 전에 위험을 알려줍니다.",
        example="'30초 후 두 드론이 3m까지 접근합니다' 같은 경고를 미리 보여줍니다.",
    ),
    GlossaryEntry(
        term="CBS (Conflict-Based Search)",
        easy_name="교통 정리 경로 계획",
        explanation="여러 드론이 동시에 이동할 때, 서로 부딪히지 않는 최적 경로를 찾아줍니다. 교통 경찰이 차량 흐름을 정리하는 것과 비슷합니다.",
        example="드론 A는 위로, B는 아래로 돌아가게 경로를 바꿔서 충돌을 방지합니다.",
    ),
    GlossaryEntry(
        term="Geofence",
        easy_name="비행 금지 울타리",
        explanation="드론이 넘어가면 안 되는 보이지 않는 벽입니다. 공항, 군사 시설, 학교 위를 지나지 못하게 막습니다.",
        example="공항 반경 5km 안으로 들어가려 하면, 자동으로 멈추고 방향을 바꿉니다.",
    ),
    GlossaryEntry(
        term="Voronoi Tessellation",
        easy_name="하늘 구역 나누기",
        explanation="넓은 하늘을 드론마다 담당 구역으로 나눕니다. 각 드론은 자기 구역 안에서 임무를 수행하고, 구역이 겹치지 않게 합니다.",
        example="드론 10대가 있으면 하늘이 10개 구역으로 나뉘고, 각 드론이 한 구역을 맡습니다.",
    ),
    GlossaryEntry(
        term="Monte Carlo Simulation",
        easy_name="수천 번 반복 테스트",
        explanation="같은 시뮬레이션을 랜덤하게 수천 번 돌려서, 평균적으로 어떤 일이 일어나는지 확인합니다. 주사위를 많이 던져 확률을 확인하는 것과 같습니다.",
        example="바람이 불 때 충돌이 얼마나 늘어나는지 1,000번 시뮬레이션해서 평균을 구합니다.",
    ),
    GlossaryEntry(
        term="SORA (Specific Operations Risk Assessment)",
        easy_name="비행 위험도 점수",
        explanation="드론이 어디서, 어떻게 날 때 위험한지 점수를 매깁니다. 점수가 높으면 더 엄격한 안전 장치가 필요합니다.",
        example="사람이 많은 도심 = 높은 위험 점수, 바다 위 = 낮은 위험 점수",
    ),
    GlossaryEntry(
        term="SimPy",
        easy_name="가상 시간 엔진",
        explanation="실제 시간을 기다리지 않고, 컴퓨터 안에서 시간을 빨리 감기하면서 드론의 움직임을 계산합니다.",
        example="실제로 2분 걸리는 비행을 0.1초 만에 시뮬레이션할 수 있습니다.",
    ),
    GlossaryEntry(
        term="Collision Resolution Rate",
        easy_name="충돌 방지 성공률",
        explanation="위험한 상황이 발생했을 때 시스템이 충돌을 막는 데 성공한 비율입니다. 100%에 가까울수록 안전합니다.",
        example="95%라면 100번의 위험 중 95번은 성공적으로 충돌을 막았다는 뜻입니다.",
    ),
    GlossaryEntry(
        term="Wind Compensation",
        easy_name="바람 보정",
        explanation="바람이 불면 드론이 밀리는데, 바람의 세기와 방향을 계산해서 자동으로 반대 방향으로 힘을 줍니다.",
        example="왼쪽에서 바람이 불면, 드론이 자동으로 왼쪽으로 약간 기울어져 제자리를 유지합니다.",
    ),
    GlossaryEntry(
        term="UTM (UAS Traffic Management)",
        easy_name="드론 교통 관리",
        explanation="하늘 위의 교통 시스템입니다. 자동차에 도로와 신호등이 있듯이, 드론에도 하늘길과 규칙이 필요합니다.",
        example="이 드론은 고도 50m에서 북쪽으로, 저 드론은 고도 100m에서 남쪽으로 가도록 관리합니다.",
    ),
    GlossaryEntry(
        term="5-Layer Safety Net",
        easy_name="5단계 안전망",
        explanation="드론이 충돌하지 않도록 5겹의 안전 장치를 둡니다. 하나가 실패해도 다음 장치가 작동합니다.",
        example="1단계: 경로 계획 → 2단계: 충돌 예측 → 3단계: 자동 회피 → 4단계: 비행금지 구역 → 5단계: 긴급 착륙",
    ),
)

_GLOSSARY_MAP: MappingProxyType[str, GlossaryEntry] = MappingProxyType(
    {g.term: g for g in GLOSSARY}
)


@dataclass(frozen=True)
class GuidedScenario:
    """단계별 안내 시나리오."""

    scenario_id: int
    title: str
    description: str
    learning_goal: str
    steps: tuple[str, ...]
    preset_id: str
    estimated_minutes: int

    def __post_init__(self) -> None:
        if self.scenario_id < 1:
            raise ValueError(f"scenario_id must be >= 1, got {self.scenario_id}")
        if not self.steps:
            raise ValueError("At least 1 step required")
        if self.preset_id not in VALID_PRESET_IDS:
            raise ValueError(f"Invalid preset_id: {self.preset_id}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "title": self.title,
            "description": self.description,
            "learning_goal": self.learning_goal,
            "steps": list(self.steps),
            "preset_id": self.preset_id,
            "estimated_minutes": self.estimated_minutes,
        }


GUIDED_SCENARIOS: tuple[GuidedScenario, ...] = (
    GuidedScenario(
        scenario_id=1,
        title="첫 비행: 드론 5대 관찰하기",
        description="가장 간단한 설정으로 드론이 하늘에서 어떻게 움직이는지 관찰합니다.",
        learning_goal="시뮬레이터 기본 조작법과 드론 비행 패턴 이해",
        steps=(
            "시뮬레이터를 '쉬움' 모드로 시작합니다",
            "3D 화면에서 드론 5대가 이륙하는 것을 관찰합니다",
            "마우스로 화면을 회전하여 다양한 각도에서 봅니다",
            "드론이 목적지까지 이동하는 경로를 따라가 봅니다",
            "시뮬레이션이 끝나면 결과 요약을 확인합니다",
        ),
        preset_id="easy",
        estimated_minutes=5,
    ),
    GuidedScenario(
        scenario_id=2,
        title="충돌 회피 체험: 드론끼리 부딪힐 뻔!",
        description="드론 20대가 비행하면서 서로 가까워지는 상황을 관찰합니다. 자동 충돌 회피 시스템이 어떻게 작동하는지 봅니다.",
        learning_goal="CPA 예측과 APF 충돌 회피의 기본 원리 이해",
        steps=(
            "시뮬레이터를 '보통' 모드로 시작합니다",
            "드론들이 서로 가까워질 때 빨간 경고선이 나타나는 것을 관찰합니다",
            "경고가 뜨면 드론이 자동으로 방향을 바꾸는 것을 확인합니다",
            "'가장 가까워지는 순간 예측(CPA)' 값이 줄어드는 것을 지켜봅니다",
            "시뮬레이션 결과에서 '충돌 방지 성공률'을 확인합니다",
        ),
        preset_id="normal",
        estimated_minutes=10,
    ),
    GuidedScenario(
        scenario_id=3,
        title="바람과 싸우는 드론: 기상 악화 체험",
        description="강한 바람이 부는 상황에서 드론이 어떻게 대응하는지 관찰합니다. 바람 보정 시스템의 작동을 체험합니다.",
        learning_goal="풍속이 드론 비행에 미치는 영향과 자동 보정 원리 이해",
        steps=(
            "시뮬레이터를 '어려움' 모드로 시작합니다 (바람 12m/s)",
            "드론이 바람에 밀리면서도 경로를 유지하려는 것을 관찰합니다",
            "바람이 없을 때와 있을 때의 비행 경로 차이를 비교합니다",
            "'바람 보정' 시스템이 작동하면서 드론이 안정되는 것을 확인합니다",
            "결과에서 바람으로 인한 추가 충돌 위험 건수를 확인합니다",
        ),
        preset_id="hard",
        estimated_minutes=15,
    ),
    GuidedScenario(
        scenario_id=4,
        title="하늘의 교통 정리: 구역 나누기",
        description="여러 드론이 동시에 날 때 하늘을 어떻게 구역으로 나누는지 관찰합니다.",
        learning_goal="보로노이 공역 분할과 교통 관리(UTM)의 기본 개념 이해",
        steps=(
            "시뮬레이터를 '보통' 모드로 시작합니다",
            "3D 화면에서 하늘이 색깔별 구역으로 나뉘는 것을 관찰합니다",
            "각 드론이 자기 구역 안에서 움직이는 것을 확인합니다",
            "드론이 구역 경계를 넘으려 할 때 어떤 일이 일어나는지 봅니다",
            "결과에서 구역 위반 건수와 전체 교통 효율을 확인합니다",
        ),
        preset_id="normal",
        estimated_minutes=10,
    ),
    GuidedScenario(
        scenario_id=5,
        title="비행 금지 구역: 여기는 못 가요!",
        description="공항이나 학교 같은 비행 금지 구역 근처에서 드론이 어떻게 반응하는지 체험합니다.",
        learning_goal="지오펜스(비행 금지 울타리)의 작동 원리와 필요성 이해",
        steps=(
            "시뮬레이터를 '쉬움' 모드로 시작합니다",
            "3D 화면에서 빨간색으로 표시된 비행 금지 구역을 확인합니다",
            "드론이 금지 구역 경계에 다가가면 자동으로 멈추는 것을 관찰합니다",
            "드론이 우회 경로를 찾아 안전하게 이동하는 것을 확인합니다",
            "결과에서 지오펜스 작동 횟수를 확인합니다",
        ),
        preset_id="easy",
        estimated_minutes=5,
    ),
)

_SCENARIO_MAP: MappingProxyType[int, GuidedScenario] = MappingProxyType(
    {s.scenario_id: s for s in GUIDED_SCENARIOS}
)


@dataclass(frozen=True)
class SimplifiedMetric:
    """단순화된 결과 지표."""

    metric_id: str
    display_name: str
    explanation: str
    unit: str
    good_direction: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "display_name": self.display_name,
            "explanation": self.explanation,
            "unit": self.unit,
            "good_direction": self.good_direction,
        }


SIMPLIFIED_METRICS: tuple[SimplifiedMetric, ...] = (
    SimplifiedMetric(
        metric_id="collision_resolution_rate",
        display_name="충돌 방지 성공률",
        explanation="위험한 상황이 100번 있었다면, 그 중 몇 번을 성공적으로 막았는지 보여줍니다. 95% 이상이면 매우 안전합니다.",
        unit="%",
        good_direction="높을수록 좋음",
    ),
    SimplifiedMetric(
        metric_id="total_collisions",
        display_name="실제 충돌 횟수",
        explanation="시뮬레이션 동안 드론끼리 실제로 부딪힌 횟수입니다. 0에 가까울수록 안전합니다.",
        unit="회",
        good_direction="낮을수록 좋음",
    ),
    SimplifiedMetric(
        metric_id="near_misses",
        display_name="아슬아슬한 순간",
        explanation="부딪히지는 않았지만 매우 가까이 지나간 횟수입니다. 이때 충돌 회피 시스템이 작동했습니다.",
        unit="회",
        good_direction="낮을수록 좋음",
    ),
    SimplifiedMetric(
        metric_id="average_flight_time",
        display_name="평균 비행 시간",
        explanation="각 드론이 이륙부터 착륙까지 하늘에 있었던 평균 시간입니다.",
        unit="초",
        good_direction="목표 시간에 가까울수록 좋음",
    ),
    SimplifiedMetric(
        metric_id="mission_completion",
        display_name="임무 완료율",
        explanation="드론에게 주어진 임무(목적지 도착) 중 성공적으로 완료한 비율입니다.",
        unit="%",
        good_direction="높을수록 좋음",
    ),
    SimplifiedMetric(
        metric_id="wind_impact",
        display_name="바람 영향도",
        explanation="바람이 드론 비행에 얼마나 영향을 미쳤는지 보여줍니다. 높으면 바람이 비행을 많이 방해했다는 뜻입니다.",
        unit="등급 (낮음/보통/높음)",
        good_direction="낮을수록 좋음",
    ),
)

_METRIC_MAP: MappingProxyType[str, SimplifiedMetric] = MappingProxyType(
    {m.metric_id: m for m in SIMPLIFIED_METRICS}
)


@dataclass(frozen=True)
class DemoExperience:
    """전체 체험판 패키지."""

    title: str
    subtitle: str
    presets: tuple[DifficultyPreset, ...]
    glossary: tuple[GlossaryEntry, ...]
    scenarios: tuple[GuidedScenario, ...]
    metrics: tuple[SimplifiedMetric, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "presets": [p.as_dict() for p in self.presets],
            "glossary": [g.as_dict() for g in self.glossary],
            "scenarios": [s.as_dict() for s in self.scenarios],
            "metrics": [m.as_dict() for m in self.metrics],
            "stats": get_stats(),
        }


def get_preset(preset_id: str) -> DifficultyPreset:
    """난이도 프리셋 조회."""
    if preset_id not in _PRESET_MAP:
        raise ValueError(f"Unknown preset_id={preset_id!r}. Valid: {list(_PRESET_MAP.keys())}")
    return _PRESET_MAP[preset_id]


def get_scenario(scenario_id: int) -> GuidedScenario:
    """가이드 시나리오 조회."""
    if scenario_id not in _SCENARIO_MAP:
        raise ValueError(f"Unknown scenario_id={scenario_id}. Valid: {list(_SCENARIO_MAP.keys())}")
    return _SCENARIO_MAP[scenario_id]


def get_metric(metric_id: str) -> SimplifiedMetric:
    """단순화 지표 조회."""
    if metric_id not in _METRIC_MAP:
        raise ValueError(f"Unknown metric_id={metric_id!r}. Valid: {list(_METRIC_MAP.keys())}")
    return _METRIC_MAP[metric_id]


def search_glossary(keyword: str) -> tuple[GlossaryEntry, ...]:
    """용어 사전 키워드 검색."""
    kw = keyword.lower()
    return tuple(
        g for g in GLOSSARY
        if kw in g.term.lower() or kw in g.easy_name.lower() or kw in g.explanation.lower()
    )


def list_presets() -> list[dict[str, Any]]:
    """난이도 프리셋 요약 목록."""
    return [
        {
            "preset_id": p.preset_id,
            "name": p.name,
            "drone_count": p.drone_count,
            "description": p.description,
        }
        for p in DIFFICULTY_PRESETS
    ]


def list_scenarios() -> list[dict[str, Any]]:
    """가이드 시나리오 요약 목록."""
    return [
        {
            "scenario_id": s.scenario_id,
            "title": s.title,
            "preset": s.preset_id,
            "estimated_minutes": s.estimated_minutes,
        }
        for s in GUIDED_SCENARIOS
    ]


def list_metrics() -> list[dict[str, Any]]:
    """단순화 지표 요약 목록."""
    return [
        {
            "metric_id": m.metric_id,
            "display_name": m.display_name,
            "good_direction": m.good_direction,
        }
        for m in SIMPLIFIED_METRICS
    ]


def build_experience() -> DemoExperience:
    """전체 체험판 패키지 생성."""
    return DemoExperience(
        title="SDACS 드론 관제 시뮬레이터 체험판",
        subtitle="군집드론이 하늘에서 안전하게 비행하는 원리를 직접 체험해 보세요!",
        presets=DIFFICULTY_PRESETS,
        glossary=GLOSSARY,
        scenarios=GUIDED_SCENARIOS,
        metrics=SIMPLIFIED_METRICS,
    )


def get_stats() -> dict[str, Any]:
    """체험판 통계."""
    return {
        "total_presets": len(DIFFICULTY_PRESETS),
        "total_glossary_entries": len(GLOSSARY),
        "total_scenarios": len(GUIDED_SCENARIOS),
        "total_metrics": len(SIMPLIFIED_METRICS),
        "difficulty_levels": [p.name for p in DIFFICULTY_PRESETS],
        "total_scenario_steps": sum(len(s.steps) for s in GUIDED_SCENARIOS),
    }


# -- CLI --

def _main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="GENESIS Phase 391 -- 체험판 단순화 모드")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--presets", action="store_true", help="난이도 프리셋 목록")
    group.add_argument("--preset", type=str, metavar="ID", help="특정 프리셋 상세")
    group.add_argument("--glossary", action="store_true", help="용어 사전")
    group.add_argument("--search", type=str, metavar="KEYWORD", help="용어 검색")
    group.add_argument("--scenarios", action="store_true", help="가이드 시나리오 목록")
    group.add_argument("--scenario", type=int, metavar="ID", help="특정 시나리오 상세")
    group.add_argument("--metrics", action="store_true", help="단순화 지표 목록")
    group.add_argument("--explain", type=str, metavar="METRIC_ID", help="지표 쉬운 설명")
    group.add_argument("--package", action="store_true", help="전체 체험판 패키지")
    group.add_argument("--stats", action="store_true", help="체험판 통계")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    if args.presets:
        data = list_presets()
        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print("=== 난이도 프리셋 ===")
            for p in data:
                print(f"\n  [{p['preset_id']}] {p['name']} (드론 {p['drone_count']}대)")
                print(f"    {p['description']}")

    elif args.preset:
        try:
            p = get_preset(args.preset)
        except ValueError as e:
            print(f"오류: {e}", file=sys.stderr)
            sys.exit(1)
        if args.json:
            print(json.dumps(p.as_dict(), ensure_ascii=False, indent=2))
        else:
            print(f"=== 난이도: {p.name} ===")
            print(f"  설명: {p.description}")
            print(f"  드론 수: {p.drone_count}대")
            print(f"  비행 시간: {p.duration_sec}초")
            print(f"  바람 세기: {p.wind_speed_ms} m/s")
            print(f"  충돌 위험: {p.conflict_probability}")
            print(f"  추천 대상: {p.recommended_for}")

    elif args.glossary:
        if args.json:
            print(json.dumps([g.as_dict() for g in GLOSSARY], ensure_ascii=False, indent=2))
        else:
            print("=== 드론 용어 쉬운 사전 ===")
            for g in GLOSSARY:
                print(f"\n  [{g.easy_name}] {g.term}")
                print(f"    {g.explanation}")
                print(f"    예시: {g.example}")

    elif args.search:
        results = search_glossary(args.search)
        if args.json:
            print(json.dumps([g.as_dict() for g in results], ensure_ascii=False, indent=2))
        else:
            print(f"=== '{args.search}' 검색 결과: {len(results)}건 ===")
            for g in results:
                print(f"\n  [{g.easy_name}] {g.term}")
                print(f"    {g.explanation}")

    elif args.scenarios:
        data = list_scenarios()
        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print("=== 가이드 시나리오 ===")
            for s in data:
                print(f"\n  [{s['scenario_id']}] {s['title']} (~{s['estimated_minutes']}분)")

    elif args.scenario:
        try:
            s = get_scenario(args.scenario)
        except ValueError as e:
            print(f"오류: {e}", file=sys.stderr)
            sys.exit(1)
        if args.json:
            print(json.dumps(s.as_dict(), ensure_ascii=False, indent=2))
        else:
            print(f"=== 시나리오 {s.scenario_id}: {s.title} ===")
            print(f"  설명: {s.description}")
            print(f"  학습 목표: {s.learning_goal}")
            print(f"  난이도: {get_preset(s.preset_id).name}")
            print(f"  소요 시간: ~{s.estimated_minutes}분")
            print("\n  단계:")
            for i, step in enumerate(s.steps, 1):
                print(f"    {i}. {step}")

    elif args.metrics:
        data = list_metrics()
        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print("=== 결과 지표 쉬운 설명 ===")
            for m in data:
                print(f"\n  [{m['metric_id']}] {m['display_name']}")
                print(f"    {m['good_direction']}")

    elif args.explain:
        try:
            m = get_metric(args.explain)
        except ValueError as e:
            print(f"오류: {e}", file=sys.stderr)
            sys.exit(1)
        if args.json:
            print(json.dumps(m.as_dict(), ensure_ascii=False, indent=2))
        else:
            print(f"=== {m.display_name} ===")
            print(f"  {m.explanation}")
            print(f"  단위: {m.unit}")
            print(f"  판단 기준: {m.good_direction}")

    elif args.package:
        pkg = build_experience()
        if args.json:
            print(json.dumps(pkg.as_dict(), ensure_ascii=False, indent=2))
        else:
            print(f"=== {pkg.title} ===")
            print(f"  {pkg.subtitle}")
            stats = get_stats()
            print(f"\n  난이도 프리셋: {stats['total_presets']}종")
            print(f"  용어 사전: {stats['total_glossary_entries']}개")
            print(f"  가이드 시나리오: {stats['total_scenarios']}개 ({stats['total_scenario_steps']}단계)")
            print(f"  결과 지표: {stats['total_metrics']}종")

    elif args.stats:
        stats = get_stats()
        if args.json:
            print(json.dumps(stats, ensure_ascii=False, indent=2))
        else:
            print("=== 체험판 통계 ===")
            print(f"  난이도 프리셋: {stats['total_presets']}종 ({', '.join(stats['difficulty_levels'])})")
            print(f"  용어 사전: {stats['total_glossary_entries']}개")
            print(f"  가이드 시나리오: {stats['total_scenarios']}개 ({stats['total_scenario_steps']}단계)")
            print(f"  결과 지표: {stats['total_metrics']}종")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    _main()

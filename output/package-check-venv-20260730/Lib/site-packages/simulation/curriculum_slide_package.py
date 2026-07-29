"""GENESIS Phase 383 -- 강의 슬라이드 패키지 (15주 커리큘럼).

'드론 관제 시스템 설계' 학부 캡스톤 15주 커리큘럼.
주차별 주제·학습 목표·SDACS 모듈 매핑·실습·슬라이드 개요를 정의한다.

구성 요소
---------
1. **CurriculumWeek**: 주차 ID, 주제, 학습 목표, SDACS 모듈, 실습, 슬라이드 개요
2. **CurriculumPackage**: 15주 전체 패키지 (과목명, 학점, 선수과목 등)
3. **CURRICULUM_WEEKS**: 15주 레지스트리
4. **get_week()** / **filter_by_category()**: 조회 API
5. **generate_syllabus()**: 강의 계획서 텍스트 생성

설계 원칙
---------
- frozen dataclass, 결정적, 부수효과 0
- Phase 468 (capstone_curriculum_standard.py)와 보완 관계: 468=게이트 판정, 383=콘텐츠
- Phase 382 (practice_assignments.py) 실습 과제와 연동

CLI:
    python simulation/curriculum_slide_package.py --weeks          # 15주 목록
    python simulation/curriculum_slide_package.py --week 1         # 주차 상세
    python simulation/curriculum_slide_package.py --category "기초"  # 카테고리 필터
    python simulation/curriculum_slide_package.py --syllabus       # 강의 계획서
    python simulation/curriculum_slide_package.py --stats          # 통계
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

CATEGORIES: tuple[str, ...] = ("기초", "핵심", "중간", "심화", "프로젝트")


@dataclass(frozen=True)
class CurriculumWeek:
    """주차별 강의 단원."""

    week_id: int
    category: str
    topic: str
    objectives: tuple[str, ...]
    sdacs_modules: tuple[str, ...]
    exercises: tuple[str, ...]
    slide_outline: tuple[str, ...]
    related_phases: tuple[int, ...]

    def __post_init__(self) -> None:
        if not 1 <= self.week_id <= 15:
            raise ValueError(f"week_id must be 1-15, got {self.week_id}")
        if self.category not in CATEGORIES:
            raise ValueError(f"Invalid category '{self.category}'. Valid: {CATEGORIES}")
        if len(self.objectives) < 1:
            raise ValueError("At least 1 objective required")
        if len(self.slide_outline) < 1:
            raise ValueError("At least 1 slide outline item required")


@dataclass(frozen=True)
class CurriculumPackage:
    """15주 커리큘럼 패키지."""

    course_name: str
    credits: int
    prerequisites: tuple[str, ...]
    target_audience: str
    weeks: tuple[CurriculumWeek, ...]
    total_weeks: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "course_name": self.course_name,
            "credits": self.credits,
            "prerequisites": list(self.prerequisites),
            "target_audience": self.target_audience,
            "total_weeks": self.total_weeks,
            "weeks": [
                {
                    "week": w.week_id,
                    "category": w.category,
                    "topic": w.topic,
                    "objectives": list(w.objectives),
                    "sdacs_modules": list(w.sdacs_modules),
                    "exercises": list(w.exercises),
                    "slide_sections": len(w.slide_outline),
                }
                for w in self.weeks
            ],
        }


CURRICULUM_WEEKS: tuple[CurriculumWeek, ...] = (
    CurriculumWeek(
        1, "기초", "드론 관제 시스템 개요",
        ("드론 공역 관리 개념 이해", "SDACS 4계층 아키텍처 설명", "시뮬레이션 기반 검증 방법론 소개"),
        ("simulation/simulator.py", "main.py"),
        ("SDACS 환경 구축 및 첫 시뮬레이션 실행", "4계층 구조 다이어그램 작성"),
        ("드론 산업 현황", "ATC vs UTM", "SDACS 아키텍처", "SimPy 이산 이벤트 시뮬레이션", "데모: 기본 시뮬레이션"),
        (1, 2, 3),
    ),
    CurriculumWeek(
        2, "기초", "드론 비행 물리학과 에이전트 모델링",
        ("멀티콥터 비행 원리(양력, 항력, 자세 제어) 설명", "DroneAgent 10Hz 프로세스 구조 분석"),
        ("simulation/drone_agent.py",),
        ("DroneAgent 파라미터 변경 실험", "비행 궤적 시각화"),
        ("멀티콥터 비행 원리", "자세 제어(Roll/Pitch/Yaw)", "DroneAgent 클래스 분석", "SimPy 프로세스 모델", "실습: 궤적 비교"),
        (4, 5),
    ),
    CurriculumWeek(
        3, "기초", "충돌 감지와 CPA 예측",
        ("CPA(Closest Point of Approach) 수학적 정의", "90초 선제 충돌 예측 알고리즘 이해", "충돌 해결률 공식 유도"),
        ("src/airspace_control/controller/",),
        ("CPA 예측 정확도 측정 실험", "충돌 해결률 계산 실습"),
        ("CPA 수학적 모델", "시간-거리 그래프", "90초 예측 윈도우", "충돌 해결률 = 1-C/(F+C)", "실습: CPA 시각화"),
        (10, 11, 12),
    ),
    CurriculumWeek(
        4, "핵심", "인공 포텐셜 장(APF) 충돌 회피",
        ("FIRAS 인력/척력장 수학적 모델 유도", "APF 파라미터 튜닝 원리", "강풍 모드 자동 전환 조건"),
        ("simulation/apf_engine/apf.py",),
        ("APF 파라미터(η, ρ₀) 변경에 따른 경로 비교", "강풍 모드 전환 실험"),
        ("포텐셜 장 이론", "FIRAS 모델 수식", "척력·인력 벡터 합성", "APF_PARAMS vs APF_PARAMS_WINDY", "실습: 파라미터 튜닝"),
        (20, 21, 22),
    ),
    CurriculumWeek(
        5, "핵심", "다중 에이전트 경로 계획 (CBS)",
        ("CBS(Conflict-Based Search) 알고리즘 원리", "Voronoi 동적 공역 분할 개념", "A* vs PRM 경로 탐색 비교"),
        ("simulation/simulator.py", "simulation/advanced_path_planner.py"),
        ("CBS 제약 트리 구성 실습", "Voronoi 분할 시각화"),
        ("MAPF 문제 정의", "CBS 2단계(고/저수준 탐색)", "Voronoi 다이어그램", "A* vs PRM+A* 비교", "실습: 10대 드론 경로 계획"),
        (30, 31, 32),
    ),
    CurriculumWeek(
        6, "핵심", "5계층 안전망 아키텍처",
        ("5계층 방어 심도 설계 원리", "각 계층의 독립적 기여도 분석(Ablation)", "안전 불변식과 RTM 추적"),
        ("src/airspace_control/controller/", "docs/certification/RTM_5LAYER_COVERAGE.md"),
        ("Ablation 실험: 1계층씩 비활성화 후 충돌률 비교", "RTM 추적표 작성"),
        ("Swiss Cheese 모델", "5계층 세부 역할", "Ablation 실험 설계", "RTM(Requirements Traceability Matrix)", "실습: 계층별 기여도 측정"),
        (101, 102, 103, 104, 105),
    ),
    CurriculumWeek(
        7, "핵심", "공역 규제와 인증 프레임워크",
        ("항공안전법·드론활용촉진법 주요 조항", "SORA 위험도 평가 절차", "ICAO 공역 클래스(A-G) 구분"),
        ("simulation/sora_category.py", "simulation/airspace_class.py", "docs/certification/AIR_SAFETY_ACT_MATRIX.md"),
        ("SORA 자동 계산기로 시나리오별 SAIL 등급 산정", "공역 클래스 판정 실습"),
        ("항공안전법 핵심 조항", "SORA JARUS 2.0", "SAIL 1-6 등급", "ICAO A-G 공역", "실습: SORA 위험도 평가"),
        (301, 302, 408),
    ),
    CurriculumWeek(
        8, "중간", "중간 프로젝트 발표",
        ("1-7주 학습 내용 종합 발표", "시뮬레이션 결과 분석 능력 평가", "팀 프로젝트 진행 상황 공유"),
        ("simulation/practice_assignments.py",),
        ("팀 프로젝트 중간 발표", "교수·동료 피드백 반영 계획 수립"),
        ("발표 가이드라인", "평가 루브릭", "피드백 프레임워크", "Q&A 전략"),
        (381, 382),
    ),
    CurriculumWeek(
        9, "심화", "기상 모델링과 풍속장 분석",
        ("WindModel 구현 분석", "METAR 기상 보고 해석", "TFR/NOTAM 비행 제한 처리"),
        ("simulation/wind_compensation_system.py", "simulation/metar_parser.py", "simulation/notam_manager.py"),
        ("다양한 풍속 조건에서의 드론 군집 비행 실험", "METAR 데이터 파싱 및 비행 가부 판정"),
        ("대기 경계층과 바람", "WindModel 파라미터", "METAR/TAF 해석", "NOTAM/TFR 처리", "실습: 기상 시나리오 실험"),
        (40, 41, 42),
    ),
    CurriculumWeek(
        10, "심화", "Monte Carlo 시뮬레이션과 통계 검증",
        ("Monte Carlo 스윕 방법론", "시드 기반 재현성 확보", "시나리오 파라미터 공간 탐색"),
        ("simulation/monte_carlo.py", "config/monte_carlo.yaml"),
        ("Monte Carlo 50회 스윕 실행 및 결과 분석", "시나리오별 충돌률 분포 시각화"),
        ("Monte Carlo 방법 개요", "np.random.default_rng(seed)", "파라미터 공간", "결과 통계 분석", "실습: MC 스윕 실행"),
        (50, 51, 52),
    ),
    CurriculumWeek(
        11, "심화", "차세대 자율 기술 (하이브리드 충돌 회피)",
        ("APF+RL 하이브리드 접근법", "안전 우선 오버라이드 메커니즘", "V2X 드론 간 통신"),
        ("src/autonomy/hybrid_collision_avoidance.py", "simulation/v2x_message.py"),
        ("APF(0.7)+RL(0.3) 가중 결합 실험", "V2X BSM 메시지 생성·파싱 실습"),
        ("규칙 기반 vs 학습 기반", "하이브리드 설계 원칙", "안전 오버라이드(5m)", "V2X BSM 규격", "실습: 하이브리드 CA"),
        (362, 364),
    ),
    CurriculumWeek(
        12, "심화", "실 지역 데이터 기반 운용",
        ("GIS 좌표계와 드론 운용", "NFZ 지오펜스 구현", "의료 배송 시나리오 설계"),
        ("src/applications/mokpo_harbor.py", "src/applications/jeonnam_island_sites.py", "simulation/geo_zones.py"),
        ("목포 해역 NFZ 기반 시뮬레이션", "전남 도서 의료 배송 ETA 최적화"),
        ("GIS/UTM 좌표계", "레이 캐스팅 NFZ 판정", "해도 기반 지형", "의료 배송 시나리오", "실습: 실 좌표 시뮬"),
        (341, 342),
    ),
    CurriculumWeek(
        13, "프로젝트", "팀 프로젝트 구현",
        ("시나리오 커스터마이징 능력 배양", "시뮬레이션 파라미터 최적화", "결과 분석 및 리포트 작성"),
        ("config/scenario_params/", "simulation/practice_assignments.py"),
        ("팀별 커스텀 시나리오 구현", "최적 파라미터 탐색 실험"),
        ("프로젝트 요구사항", "시나리오 설계 방법론", "파라미터 최적화", "결과 분석 프레임워크", "실습: 커스텀 시나리오"),
        (382,),
    ),
    CurriculumWeek(
        14, "프로젝트", "3D 시각화와 대시보드",
        ("Dash 3D 시각화 구현 분석", "실시간 텔레메트리 대시보드 설계", "발표용 시각 자료 제작"),
        ("visualization/simulator_3d.py", "main.py"),
        ("대시보드 커스터마이징", "팀 프로젝트 시각화 자료 제작"),
        ("Dash/Plotly 3D 그래픽", "텔레메트리 시각화", "대시보드 레이아웃", "발표 자료 제작", "실습: 대시보드 수정"),
        (60, 61, 62),
    ),
    CurriculumWeek(
        15, "프로젝트", "최종 발표 및 종합 평가",
        ("캡스톤 프로젝트 최종 발표", "교수·산업 전문가 평가", "15주 학습 성과 종합 리뷰"),
        ("docs/presentation/DEFENSE_KIT.md",),
        ("최종 발표 (팀당 15분 + Q&A 5분)", "동료 평가 및 자기 평가"),
        ("발표 가이드", "평가 기준(루브릭)", "Q&A 대비 전략", "포트폴리오 정리", "수료 체크리스트"),
        (387, 389),
    ),
)

_WEEK_MAP: MappingProxyType[int, CurriculumWeek] = MappingProxyType(
    {w.week_id: w for w in CURRICULUM_WEEKS}
)


def get_week(week_id: int) -> CurriculumWeek:
    """주차 ID로 조회."""
    if week_id not in _WEEK_MAP:
        raise ValueError(f"Unknown week_id={week_id}. Valid: 1-15")
    return _WEEK_MAP[week_id]


def filter_by_category(category: str) -> tuple[CurriculumWeek, ...]:
    """카테고리로 필터링."""
    return tuple(w for w in CURRICULUM_WEEKS if w.category == category)


def list_weeks() -> list[dict[str, Any]]:
    """주차 목록 반환."""
    return [
        {
            "week": w.week_id,
            "category": w.category,
            "topic": w.topic,
            "objectives_count": len(w.objectives),
            "modules_count": len(w.sdacs_modules),
            "exercises_count": len(w.exercises),
            "slides_count": len(w.slide_outline),
        }
        for w in CURRICULUM_WEEKS
    ]


def build_package() -> CurriculumPackage:
    """전체 커리큘럼 패키지 빌드."""
    return CurriculumPackage(
        course_name="드론 관제 시스템 설계 (Drone ATC System Design)",
        credits=3,
        prerequisites=("프로그래밍 기초 (Python)", "확률과 통계", "데이터구조"),
        target_audience="항공·드론·소프트웨어 전공 3-4학년",
        weeks=CURRICULUM_WEEKS,
        total_weeks=15,
    )


def generate_syllabus() -> str:
    """강의 계획서 텍스트 생성."""
    pkg = build_package()
    lines: list[str] = [
        f"{'=' * 60}",
        f"  {pkg.course_name}",
        f"  학점: {pkg.credits} | 대상: {pkg.target_audience}",
        f"  선수과목: {', '.join(pkg.prerequisites)}",
        f"{'=' * 60}",
        "",
    ]

    for w in pkg.weeks:
        lines.append(f"[{w.week_id:>2}주] [{w.category}] {w.topic}")
        lines.append("      학습 목표:")
        for obj in w.objectives:
            lines.append(f"        - {obj}")
        lines.append(f"      SDACS 모듈: {', '.join(w.sdacs_modules)}")
        lines.append(f"      실습: {'; '.join(w.exercises)}")
        lines.append(f"      슬라이드: {len(w.slide_outline)}개 섹션")
        lines.append("")

    return "\n".join(lines)


def get_stats() -> dict[str, Any]:
    """커리큘럼 통계."""
    category_counts: dict[str, int] = {}
    total_objectives = 0
    total_exercises = 0
    total_slides = 0
    all_modules: set[str] = set()
    all_phases: set[int] = set()

    for w in CURRICULUM_WEEKS:
        category_counts[w.category] = category_counts.get(w.category, 0) + 1
        total_objectives += len(w.objectives)
        total_exercises += len(w.exercises)
        total_slides += len(w.slide_outline)
        all_modules.update(w.sdacs_modules)
        all_phases.update(w.related_phases)

    return {
        "total_weeks": len(CURRICULUM_WEEKS),
        "by_category": dict(sorted(category_counts.items(), key=lambda x: CATEGORIES.index(x[0]))),
        "total_objectives": total_objectives,
        "total_exercises": total_exercises,
        "total_slide_sections": total_slides,
        "unique_sdacs_modules": len(all_modules),
        "related_phases_count": len(all_phases),
    }


# -- CLI --

def _main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="GENESIS Phase 383 -- 15주 커리큘럼 슬라이드 패키지")
    parser.add_argument("--weeks", action="store_true", help="15주 목록")
    parser.add_argument("--week", type=int, metavar="N", help="주차 상세 (1-15)")
    parser.add_argument("--category", type=str, metavar="CAT", help="카테고리 필터")
    parser.add_argument("--syllabus", action="store_true", help="강의 계획서")
    parser.add_argument("--stats", action="store_true", help="통계")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    if args.weeks:
        items = list_weeks()
        if args.json:
            print(json.dumps(items, ensure_ascii=False, indent=2))
        else:
            print(f"{'주':>2} {'카테고리':<6} {'주제':<30} {'목표':>2} {'모듈':>2} {'실습':>2} {'슬라이드':>4}")
            print("-" * 60)
            for item in items:
                print(f"{item['week']:>2} {item['category']:<6} {item['topic']:<30} {item['objectives_count']:>2} {item['modules_count']:>2} {item['exercises_count']:>2} {item['slides_count']:>6}")

    elif args.week is not None:
        try:
            w = get_week(args.week)
        except ValueError as exc:
            parser.error(str(exc))
        if args.json:
            print(json.dumps({
                "week": w.week_id, "category": w.category,
                "topic": w.topic,
                "objectives": list(w.objectives),
                "sdacs_modules": list(w.sdacs_modules),
                "exercises": list(w.exercises),
                "slide_outline": list(w.slide_outline),
                "related_phases": list(w.related_phases),
            }, ensure_ascii=False, indent=2))
        else:
            print(f"[{w.week_id}주] {w.topic} ({w.category})")
            print("\n  학습 목표:")
            for obj in w.objectives:
                print(f"    - {obj}")
            print("\n  SDACS 모듈:")
            for mod in w.sdacs_modules:
                print(f"    - {mod}")
            print("\n  실습:")
            for ex in w.exercises:
                print(f"    - {ex}")
            print("\n  슬라이드 개요:")
            for i, sec in enumerate(w.slide_outline, 1):
                print(f"    {i}. {sec}")
            print(f"\n  관련 Phase: {', '.join(str(p) for p in w.related_phases)}")

    elif args.category is not None:
        weeks = filter_by_category(args.category)
        if args.json:
            print(json.dumps([
                {"week": w.week_id, "topic": w.topic}
                for w in weeks
            ], ensure_ascii=False, indent=2))
        else:
            print(f"카테고리 '{args.category}' ({len(weeks)}주):")
            for w in weeks:
                print(f"  [{w.week_id:>2}주] {w.topic}")

    elif args.syllabus:
        if args.json:
            pkg = build_package()
            print(json.dumps(pkg.as_dict(), ensure_ascii=False, indent=2))
        else:
            print(generate_syllabus())

    elif args.stats:
        stats = get_stats()
        if args.json:
            print(json.dumps(stats, ensure_ascii=False, indent=2))
        else:
            print("=== 커리큘럼 통계 ===")
            print(f"  총 주차: {stats['total_weeks']}")
            print("  카테고리별:")
            for cat, cnt in stats["by_category"].items():
                print(f"    {cat}: {cnt}주")
            print(f"  총 학습 목표: {stats['total_objectives']}")
            print(f"  총 실습: {stats['total_exercises']}")
            print(f"  총 슬라이드 섹션: {stats['total_slide_sections']}")
            print(f"  SDACS 모듈 수: {stats['unique_sdacs_modules']}")
            print(f"  관련 Phase 수: {stats['related_phases_count']}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    _main()

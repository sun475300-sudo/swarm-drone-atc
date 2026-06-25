"""GENESIS Phase 384 -- 조종자 자격 이론 연계 문제은행.

드론 조종자 자격증명(1~4종) 이론시험 유형과 SDACS 시뮬레이션 상황을
매핑하여, 학부 교육 과정에서 자격 시험 대비와 시뮬 학습을 통합한다.

구성 요소
---------
1. **ExamQuestion**: 문제 ID, 자격 종별, 과목, 지문, 선택지, 정답, SDACS 모듈 매핑
2. **ExamResult**: 채점 결과 (점수, 합격 여부, 과목별 분석)
3. **QUESTION_BANK**: 40문항 (1~4종 x 10문항)
4. **grade_exam()**: 제출 답안 채점
5. **filter_by_grade()** / **filter_by_subject()**: 필터링 API

설계 원칙
---------
- frozen dataclass, 결정적, 부수효과 0
- 기존 ``docs/certification/PILOT_LICENSE_MAPPING.md`` (GENESIS 309) 참조
- 실제 기출 문제가 아닌 유형 예시 (저작권 안전)

CLI:
    python simulation/pilot_exam_bank.py --list              # 전체 문제 목록
    python simulation/pilot_exam_bank.py --grade 4           # 4종 문제 목록
    python simulation/pilot_exam_bank.py --question 1        # 문제 상세
    python simulation/pilot_exam_bank.py --subject "항공법규" # 과목 필터
    python simulation/pilot_exam_bank.py --stats             # 통계
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


@dataclass(frozen=True)
class ExamQuestion:
    """시험 문제."""

    question_id: int
    pilot_grade: int
    subject: str
    text: str
    choices: tuple[str, ...]
    correct_index: int
    sdacs_module: str
    sdacs_concept: str
    difficulty: str

    def __post_init__(self) -> None:
        if not 1 <= self.pilot_grade <= 4:
            raise ValueError(f"pilot_grade must be 1-4, got {self.pilot_grade}")
        if not 0 <= self.correct_index < len(self.choices):
            raise ValueError(
                f"correct_index={self.correct_index} out of range for {len(self.choices)} choices"
            )
        if len(self.choices) < 2:
            raise ValueError("At least 2 choices required")


@dataclass(frozen=True)
class SubjectScore:
    """과목별 점수."""

    subject: str
    correct: int
    total: int
    percentage: float


@dataclass(frozen=True)
class ExamResult:
    """시험 채점 결과."""

    pilot_grade: int
    total_correct: int
    total_questions: int
    percentage: float
    passed: bool
    subject_scores: tuple[SubjectScore, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "pilot_grade": self.pilot_grade,
            "total_correct": self.total_correct,
            "total_questions": self.total_questions,
            "percentage": round(self.percentage, 1),
            "passed": self.passed,
            "subjects": [
                {"subject": s.subject, "correct": s.correct,
                 "total": s.total, "percentage": round(s.percentage, 1)}
                for s in self.subject_scores
            ],
        }


PASS_THRESHOLD = 70.0

QUESTION_BANK: tuple[ExamQuestion, ...] = (
    # --- 4종 (초경량 비행장치, 입문) ---
    ExamQuestion(
        1, 4, "항공법규",
        "초경량 비행장치 조종자가 비행 전 반드시 확인해야 하는 사항이 아닌 것은?",
        ("기상 조건", "비행 금지 구역", "주변 건물 높이", "당일 주식 시세"),
        3, "simulation/special_flight_approval.py",
        "비행 전 점검 항목", "입문",
    ),
    ExamQuestion(
        2, 4, "항공법규",
        "비행 금지 구역(NFZ)에서 드론을 비행하려면 어떤 절차가 필요한가?",
        ("별도 허가 불필요", "관할 기관 사전 승인", "보험 가입만 필요", "기체 등록만 필요"),
        1, "simulation/geo_zones.py",
        "NFZ 규제 및 승인 절차", "입문",
    ),
    ExamQuestion(
        3, 4, "비행이론",
        "드론의 양력을 발생시키는 주된 원리는?",
        ("뉴턴 제3법칙", "아르키메데스 원리", "베르누이 원리와 뉴턴 법칙", "코리올리 효과"),
        2, "simulation/drone_agent.py",
        "드론 비행 물리학", "입문",
    ),
    ExamQuestion(
        4, 4, "비행이론",
        "멀티콥터에서 요(Yaw) 회전은 어떻게 제어하는가?",
        ("모든 모터 동시 가감속", "대각 모터 쌍의 차동 제어", "틸트 메커니즘", "날개 플랩 조절"),
        1, "simulation/drone_agent.py",
        "드론 자세 제어", "입문",
    ),
    ExamQuestion(
        5, 4, "기상학",
        "풍속이 10 m/s 초과일 때 SDACS에서 자동으로 전환되는 모드는?",
        ("절전 모드", "APF_PARAMS_WINDY", "자동 착륙", "고도 제한 모드"),
        1, "simulation/apf_engine.py",
        "강풍 모드 자동 전환", "입문",
    ),
    ExamQuestion(
        6, 4, "기상학",
        "돌풍(gust)이 드론 비행에 미치는 주된 위험은?",
        ("배터리 소모 증가만", "자세 불안정 및 충돌 위험", "GPS 신호 손실", "통신 두절"),
        1, "simulation/wind_model.py",
        "돌풍 모델링", "입문",
    ),
    ExamQuestion(
        7, 4, "안전관리",
        "드론 충돌 회피를 위한 APF(인공 포텐셜 장)에서 장애물은 어떤 힘을 발생시키는가?",
        ("인력(끌어당기는 힘)", "척력(밀어내는 힘)", "원심력", "구심력"),
        1, "simulation/apf_engine.py",
        "APF 척력장", "입문",
    ),
    ExamQuestion(
        8, 4, "안전관리",
        "SDACS 5계층 안전망에서 가장 마지막(5번째) 방어 계층은?",
        ("APF 충돌 회피", "CBS 경로 재계획", "배터리 관리", "지오펜스(UTM)", "긴급 착륙"),
        3, "src/airspace_control/controller/",
        "5계층 방어 심도", "입문",
    ),
    ExamQuestion(
        9, 4, "항공법규",
        "드론 비행 사고 발생 시 가장 먼저 해야 할 조치는?",
        ("기체 회수", "사고 현장 보존 및 인명 구호", "보험사 연락", "비행 로그 삭제"),
        1, "simulation/accident_report.py",
        "사고 보고 절차", "입문",
    ),
    ExamQuestion(
        10, 4, "비행이론",
        "드론의 최대 비행 시간에 가장 큰 영향을 미치는 요소는?",
        ("프로펠러 색상", "배터리 용량과 기체 중량", "GPS 모듈 종류", "조종기 안테나 길이"),
        1, "simulation/drone_agent.py",
        "비행 지속 시간 요소", "입문",
    ),
    # --- 3종 (기초) ---
    ExamQuestion(
        11, 3, "항공법규",
        "SORA(Specific Operations Risk Assessment)의 목적은?",
        ("드론 성능 시험", "특정 운영 위험도 평가", "통신 주파수 할당", "보험료 산정"),
        1, "simulation/sora_calculator.py",
        "SORA 위험도 평가", "기초",
    ),
    ExamQuestion(
        12, 3, "항공법규",
        "SORA에서 SAIL(Specific Assurance & Integrity Level)의 범위는?",
        ("1-3", "1-6", "A-F", "I-VI"),
        1, "simulation/sora_calculator.py",
        "SAIL 등급 체계", "기초",
    ),
    ExamQuestion(
        13, 3, "비행이론",
        "CPA(Closest Point of Approach)란 무엇인가?",
        ("최대 비행 고도", "두 비행체 간 최근접점", "배터리 교체 시점", "통신 가능 최대 거리"),
        1, "src/airspace_control/controller/",
        "CPA 충돌 예측", "기초",
    ),
    ExamQuestion(
        14, 3, "비행이론",
        "SDACS에서 CPA 예측은 몇 초 앞을 예측하는가?",
        ("10초", "30초", "60초", "90초"),
        3, "src/airspace_control/controller/",
        "90초 선제 충돌 예측", "기초",
    ),
    ExamQuestion(
        15, 3, "기상학",
        "METAR 보고에서 CAVOK의 의미는?",
        ("비행 불가", "구름/시정 양호(Ceiling And Visibility OK)", "기상 관측 불가", "강수 예보"),
        1, "simulation/metar_parser.py",
        "METAR 기상 보고 해석", "기초",
    ),
    ExamQuestion(
        16, 3, "안전관리",
        "충돌해결률 공식에서 올바른 것은?",
        ("collisions/conflicts", "1 - collisions/(conflicts + collisions)",
         "conflicts/collisions", "1 - conflicts/collisions"),
        1, "src/airspace_control/controller/",
        "충돌해결률 산정 공식", "기초",
    ),
    ExamQuestion(
        17, 3, "안전관리",
        "CBS(Conflict-Based Search)는 어떤 문제를 해결하는가?",
        ("단일 드론 경로 최적화", "다중 에이전트 경로 계획", "배터리 잔량 예측", "기상 예보"),
        1, "simulation/simulator.py",
        "CBS 다중 에이전트 경로 계획", "기초",
    ),
    ExamQuestion(
        18, 3, "항공법규",
        "야간 비행 특별비행승인 시 필수 장비는?",
        ("열화상 카메라", "충돌 방지등(Anti-collision light)", "레이더", "풍속계"),
        1, "simulation/special_flight_approval.py",
        "야간/BVLOS 특별비행승인 요건", "기초",
    ),
    ExamQuestion(
        19, 3, "비행이론",
        "Voronoi 분할은 군집 드론에서 어떤 용도로 사용되는가?",
        ("배터리 관리", "동적 공역 분할", "통신 암호화", "기체 식별"),
        1, "simulation/simulator.py",
        "Voronoi 동적 공역 분할", "기초",
    ),
    ExamQuestion(
        20, 3, "기상학",
        "난류(turbulence)가 드론 군집 운용에 미치는 영향으로 적절하지 않은 것은?",
        ("편대 유지 어려움", "충돌 위험 증가", "통신 품질 저하", "GPS 정밀도 향상"),
        3, "simulation/wind_model.py",
        "난류와 군집 비행", "기초",
    ),
    # --- 2종 (중급) ---
    ExamQuestion(
        21, 2, "항공법규",
        "EASA의 드론 운영 카테고리 중 가장 높은 위험 등급은?",
        ("Open", "Specific", "Certified", "Standard"),
        2, "simulation/sora_category.py",
        "EASA Open/Specific/Certified 분류", "중급",
    ),
    ExamQuestion(
        22, 2, "항공법규",
        "ICAO 공역 클래스에서 비제어 공역은?",
        ("Class A", "Class C", "Class E", "Class G"),
        3, "simulation/airspace_class.py",
        "ICAO A-G 공역 분류", "중급",
    ),
    ExamQuestion(
        23, 2, "비행이론",
        "Monte Carlo 시뮬레이션에서 시드(seed) 고정의 목적은?",
        ("속도 향상", "재현성 확보", "메모리 절약", "보안 강화"),
        1, "simulation/monte_carlo_sweep.py",
        "Monte Carlo 시드 기반 재현성", "중급",
    ),
    ExamQuestion(
        24, 2, "비행이론",
        "FIRAS 척력장에서 장애물까지 거리가 가까워질수록 척력은?",
        ("선형 감소", "역거리 제곱에 비례하여 급증", "일정 유지", "0으로 수렴"),
        1, "simulation/apf_engine.py",
        "FIRAS 포텐셜 장 수학적 모델", "중급",
    ),
    ExamQuestion(
        25, 2, "안전관리",
        "SDACS Ablation 실험에서 5계층 중 하나를 비활성화하는 이유는?",
        ("비용 절감", "각 계층의 독립적 기여도 측정", "속도 향상", "단순화"),
        1, "docs/certification/RTM_5LAYER_COVERAGE.md",
        "Ablation 실험을 통한 안전 계층 기여도 분석", "중급",
    ),
    ExamQuestion(
        26, 2, "안전관리",
        "지오펜스(Geofence) 위반 시 SDACS의 대응은?",
        ("경고 무시", "즉시 복귀 또는 착륙 명령", "속도 증가", "고도 상승"),
        1, "simulation/geo_zones.py",
        "지오펜스 위반 대응", "중급",
    ),
    ExamQuestion(
        27, 2, "기상학",
        "NOTAM(Notice to Airmen)에서 확인할 수 있는 정보가 아닌 것은?",
        ("임시 비행 금지 구역", "항공 시설 변경", "일기 예보 상세", "군사 훈련 공역"),
        2, "simulation/notam_manager.py",
        "NOTAM 정보 유형", "중급",
    ),
    ExamQuestion(
        28, 2, "항공법규",
        "DO-178C는 어떤 영역의 인증 표준인가?",
        ("하드웨어 설계", "항공 소프트웨어 개발", "전파 인증", "기체 구조 강도"),
        1, "docs/certification/DO178C_GAP_ANALYSIS.md",
        "DO-178C 항공 소프트웨어 인증", "중급",
    ),
    ExamQuestion(
        29, 2, "비행이론",
        "V2X(Vehicle-to-Everything) 통신에서 BSM(Basic Safety Message)의 역할은?",
        ("동영상 스트리밍", "위치·속도·방향 등 안전 정보 교환", "원격 제어 명령 전달", "펌웨어 업데이트"),
        1, "simulation/v2x_message.py",
        "V2X BSM 안전 메시지", "중급",
    ),
    ExamQuestion(
        30, 2, "안전관리",
        "하이브리드 충돌 회피에서 APF와 RL의 가중 비율은?",
        ("APF 50% + RL 50%", "APF 70% + RL 30%", "APF 30% + RL 70%", "APF 100%"),
        1, "src/autonomy/hybrid_collision_avoidance.py",
        "APF+RL 하이브리드 충돌 회피", "중급",
    ),
    # --- 1종 (고급) ---
    ExamQuestion(
        31, 1, "항공법규",
        "UTM(UAS Traffic Management)과 ATM(Air Traffic Management)의 통합에서 핵심 과제는?",
        ("드론 색상 통일", "이종 공역 체계 간 실시간 정보 교환", "조종사 유니폼 규정", "연료 표준화"),
        1, "simulation/faa_utm_gap.py",
        "UTM-ATM 통합", "고급",
    ),
    ExamQuestion(
        32, 1, "항공법규",
        "RPIC(Remote Pilot in Command)의 법적 책임 범위에 포함되지 않는 것은?",
        ("비행 안전 확보", "기상 판단", "비행 후 보고", "항공사 수익 관리"),
        3, "docs/certification/PILOT_LICENSE_MAPPING.md",
        "RPIC 법적 책임", "고급",
    ),
    ExamQuestion(
        33, 1, "비행이론",
        "Laplacian Consensus를 군집 드론 편대 제어에 적용할 때의 핵심 행렬은?",
        ("단위행렬", "그래프 라플라시안 행렬", "역행렬", "대각행렬"),
        1, "simulation/drone_formation_control.py",
        "Laplacian Consensus 편대 제어", "고급",
    ),
    ExamQuestion(
        34, 1, "비행이론",
        "PRM(Probabilistic Roadmap) + A* 경로 계획의 장점은?",
        ("계산 불필요", "고차원 공간에서 효율적 경로 탐색", "항상 최단 경로 보장", "실시간 불가"),
        1, "simulation/advanced_path_planner.py",
        "PRM+A* 경로 계획", "고급",
    ),
    ExamQuestion(
        35, 1, "안전관리",
        "군집 드론 자가 치유(Self-healing)에서 결손 드론 발생 시 수행하는 작업은?",
        ("전체 운영 중단", "임무 자동 재분배", "기지 복귀 후 대기", "수동 조종 전환"),
        1, "src/autonomy/swarm_self_healing.py",
        "스웜 자가 치유 메커니즘", "고급",
    ),
    ExamQuestion(
        36, 1, "안전관리",
        "보험 요율 산정에서 NCB(No Claim Bonus) 할인의 의미는?",
        ("신규 가입 할인", "무사고 경력 할인", "단체 가입 할인", "야간 비행 할인"),
        1, "simulation/insurance_rate_quote.py",
        "보험 요율 NCB 할인", "고급",
    ),
    ExamQuestion(
        37, 1, "기상학",
        "TFR(Temporary Flight Restriction)이 발행되는 상황이 아닌 것은?",
        ("대통령 이동", "산불 진화", "항공 축제", "일반 상업 비행"),
        3, "simulation/tfr_handler.py",
        "TFR 임시 비행 제한", "고급",
    ),
    ExamQuestion(
        38, 1, "비행이론",
        "Fisher Information Field를 드론 센서 퓨전에 활용하는 목적은?",
        ("배터리 절약", "정보 가치 기반 최적 센서 배치", "통신 암호화", "무게 감소"),
        1, "simulation/swarm_information_field.py",
        "Fisher Information 센서 퓨전", "고급",
    ),
    ExamQuestion(
        39, 1, "항공법규",
        "KC 전파인증에서 드론에 탑재되는 통신 모듈의 인증 기준은?",
        ("외관 검사만", "전파법 기반 적합성 평가", "무게 제한만", "색상 규정"),
        1, "simulation/kc_certification.py",
        "KC 전파인증 적합성 평가", "고급",
    ),
    ExamQuestion(
        40, 1, "안전관리",
        "CSAP(Cloud Security Assurance Program)에서 SDACS가 자가진단하는 통제 분야 수는?",
        ("7개", "10개", "14개", "20개"),
        2, "simulation/csap_self_assessment.py",
        "CSAP 14개 통제분야 자가진단", "고급",
    ),
)

_QUESTION_MAP: MappingProxyType[int, ExamQuestion] = MappingProxyType(
    {q.question_id: q for q in QUESTION_BANK}
)


def get_question(question_id: int) -> ExamQuestion:
    """문제 ID로 조회."""
    if question_id not in _QUESTION_MAP:
        raise ValueError(
            f"Unknown question_id={question_id}. Valid: {sorted(_QUESTION_MAP)}"
        )
    return _QUESTION_MAP[question_id]


def filter_by_grade(grade: int) -> tuple[ExamQuestion, ...]:
    """자격 종별로 필터링."""
    if not 1 <= grade <= 4:
        raise ValueError(f"grade must be 1-4, got {grade}")
    return tuple(q for q in QUESTION_BANK if q.pilot_grade == grade)


def filter_by_subject(subject: str) -> tuple[ExamQuestion, ...]:
    """과목으로 필터링."""
    return tuple(q for q in QUESTION_BANK if q.subject == subject)


def list_questions() -> list[dict[str, Any]]:
    """문제 목록 반환."""
    return [
        {
            "id": q.question_id,
            "grade": q.pilot_grade,
            "subject": q.subject,
            "difficulty": q.difficulty,
            "sdacs_module": q.sdacs_module,
        }
        for q in QUESTION_BANK
    ]


def grade_exam(
    grade: int,
    answers: dict[int, int],
) -> ExamResult:
    """시험 채점.

    Parameters
    ----------
    grade : int
        자격 종별 (1-4).
    answers : dict[int, int]
        {question_id: selected_index} 매핑.
    """
    questions = filter_by_grade(grade)
    if not questions:
        raise ValueError(f"No questions for grade {grade}")

    total = len(questions)
    correct = 0
    subject_stats: dict[str, list[bool]] = {}

    for q in questions:
        is_correct = answers.get(q.question_id) == q.correct_index
        if is_correct:
            correct += 1
        subject_stats.setdefault(q.subject, []).append(is_correct)

    percentage = (correct / total * 100.0) if total > 0 else 0.0

    subject_scores = tuple(
        SubjectScore(
            subject=subj,
            correct=sum(results),
            total=len(results),
            percentage=(sum(results) / len(results) * 100.0) if results else 0.0,
        )
        for subj, results in sorted(subject_stats.items())
    )

    return ExamResult(
        pilot_grade=grade,
        total_correct=correct,
        total_questions=total,
        percentage=percentage,
        passed=percentage >= PASS_THRESHOLD,
        subject_scores=subject_scores,
    )


def get_stats() -> dict[str, Any]:
    """문제은행 통계."""
    grade_counts: dict[int, int] = {}
    subject_counts: dict[str, int] = {}
    difficulty_counts: dict[str, int] = {}

    for q in QUESTION_BANK:
        grade_counts[q.pilot_grade] = grade_counts.get(q.pilot_grade, 0) + 1
        subject_counts[q.subject] = subject_counts.get(q.subject, 0) + 1
        difficulty_counts[q.difficulty] = difficulty_counts.get(q.difficulty, 0) + 1

    return {
        "total_questions": len(QUESTION_BANK),
        "by_grade": dict(sorted(grade_counts.items())),
        "by_subject": dict(sorted(subject_counts.items())),
        "by_difficulty": dict(sorted(difficulty_counts.items())),
        "pass_threshold": PASS_THRESHOLD,
    }


# -- CLI --

def _main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="GENESIS Phase 384 -- 조종자 자격 이론 문제은행")
    parser.add_argument("--list", action="store_true", help="전체 문제 목록")
    parser.add_argument("--grade", type=int, metavar="N", help="종별 필터 (1-4)")
    parser.add_argument("--question", type=int, metavar="ID", help="문제 상세")
    parser.add_argument("--subject", type=str, metavar="NAME", help="과목 필터")
    parser.add_argument("--stats", action="store_true", help="통계")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    if args.list:
        items = list_questions()
        if args.json:
            print(json.dumps(items, ensure_ascii=False, indent=2))
        else:
            print(f"{'ID':>3} {'종':>1} {'과목':<8} {'난이도':<4} SDACS 모듈")
            print("-" * 60)
            for item in items:
                print(f"{item['id']:>3} {item['grade']}종 {item['subject']:<8} {item['difficulty']:<4} {item['sdacs_module'][:40]}")

    elif args.grade is not None:
        try:
            questions = filter_by_grade(args.grade)
        except ValueError as exc:
            parser.error(str(exc))
        if args.json:
            print(json.dumps([
                {"id": q.question_id, "subject": q.subject, "text": q.text}
                for q in questions
            ], ensure_ascii=False, indent=2))
        else:
            print(f"{args.grade}종 문제 ({len(questions)}문항):")
            for q in questions:
                print(f"  Q{q.question_id}. [{q.subject}] {q.text[:50]}...")

    elif args.question is not None:
        try:
            q = get_question(args.question)
        except ValueError as exc:
            parser.error(str(exc))
        if args.json:
            print(json.dumps({
                "id": q.question_id, "grade": q.pilot_grade,
                "subject": q.subject, "text": q.text,
                "choices": list(q.choices),
                "correct_index": q.correct_index,
                "sdacs_module": q.sdacs_module,
                "sdacs_concept": q.sdacs_concept,
            }, ensure_ascii=False, indent=2))
        else:
            print(f"Q{q.question_id} ({q.pilot_grade}종 / {q.subject} / {q.difficulty})")
            print(f"  {q.text}")
            for i, choice in enumerate(q.choices):
                marker = "*" if i == q.correct_index else " "
                print(f"  {marker} ({i+1}) {choice}")
            print(f"  SDACS: {q.sdacs_module} -- {q.sdacs_concept}")

    elif args.subject is not None:
        questions = filter_by_subject(args.subject)
        if args.json:
            print(json.dumps([
                {"id": q.question_id, "grade": q.pilot_grade, "text": q.text}
                for q in questions
            ], ensure_ascii=False, indent=2))
        else:
            print(f"과목 '{args.subject}' ({len(questions)}문항):")
            for q in questions:
                print(f"  Q{q.question_id} ({q.pilot_grade}종) {q.text[:50]}...")

    elif args.stats:
        stats = get_stats()
        if args.json:
            print(json.dumps(stats, ensure_ascii=False, indent=2))
        else:
            print("=== 문제은행 통계 ===")
            print(f"  총 문항 수: {stats['total_questions']}")
            print(f"  합격 기준: {stats['pass_threshold']}%")
            print("  종별:")
            for g, c in stats["by_grade"].items():
                print(f"    {g}종: {c}문항")
            print("  과목별:")
            for s, c in stats["by_subject"].items():
                print(f"    {s}: {c}문항")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    _main()

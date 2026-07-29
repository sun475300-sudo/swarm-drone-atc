"""GENESIS Phase 308 — 드론 배상책임보험 요율 산정 API (Phase 67 mock 격상).

시뮬레이터 STELLAR Phase 67 ``societyInsuranceQuote`` mock(role·hours·history 3
인자 toy 공식)을 **실 보험사 요율 스펙**으로 격상한 결정적 백엔드.

근거: 항공사업법 제70조 + 시행규칙 — 초경량비행장치 *사용사업자*는 대인·대물
배상책임보험 의무 가입 대상이다. 국내 드론 배상책임보험 상품은 요율을 다음 축으로
산정한다: 기체 최대이륙중량(MTOW) 등급 · 운용 형태 · 연간 비행시간(익스포저) ·
조종자 경력 · 최근 3년 사고 이력(무사고 할인 NCB / 사고 할증) · 가입 보상한도
(증액한도계수 ILF) · 야간·비가시(BVLOS) 위험 가산.

순수 함수 — 외부 의존성·난수 없음. 동일 입력은 항상 동일 견적을 낸다.
``insurance_risk.py`` (Phase 696, 리스크 점수→예상보험료 추정)와 달리, 본 모듈은
표준 요율표 기반 *상품 견적 API*(요청→응답 스키마)다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# MTOW(kg) 등급별 기본 보험료(원/년). 등급 상한 이하에 적용.
_MTOW_BASE_KRW: tuple[tuple[float, int], ...] = (
    (2.0, 80_000),
    (7.0, 150_000),
    (25.0, 300_000),
    (150.0, 700_000),
    (float("inf"), 1_500_000),
)

# 운용 형태별 가산 계수. 의무가입 대상(사용사업) 여부도 함께 정의.
_OPERATION: dict[str, tuple[float, bool]] = {
    "delivery": (1.30, True),       # 물품 배송 — 인구밀집 통과 위험
    "survey": (1.00, True),         # 측량·점검
    "rescue": (1.50, True),         # 인명 구조 — 고위험 환경
    "agriculture": (1.20, True),    # 방제·농업
    "recreational": (0.70, False),  # 취미·비사업 — 의무가입 비대상
}

# 표준 보상한도(원)별 증액한도계수(ILF). 200백만원을 기준(1.0)으로 한 메뉴.
_COVERAGE_ILF: dict[int, float] = {
    50_000_000: 0.60,
    100_000_000: 0.80,
    150_000_000: 0.90,
    200_000_000: 1.00,
    300_000_000: 1.25,
    500_000_000: 1.60,
    1_000_000_000: 2.20,
}

# 의무가입 최소 보상한도(원) — 사용사업 대인·대물 합산 기준.
MANDATORY_MIN_LIMIT_KRW = 150_000_000

# 연간 비행시간 물리 상한 — 단일 기체는 1년(365×24시간)을 넘길 수 없다.
_MAX_ANNUAL_FLIGHT_HOURS = 8_760.0

# 위험 운용 가산 계수.
_NIGHT_LOADING = 1.15
_BVLOS_LOADING = 1.30

# 경력 할인: 연 3%씩 최대 15%. 무사고 할인(NCB) / 사고 1건당 25% 할증.
_EXPERIENCE_DISCOUNT_PER_YEAR = 0.03
_EXPERIENCE_DISCOUNT_MAX = 0.15
_NO_CLAIMS_BONUS = 0.85
_CLAIM_SURCHARGE_PER_EVENT = 0.25

# 최종 보험료 반올림 단위(원).
_ROUND_UNIT = 100


@dataclass(frozen=True)
class QuoteRequest:
    """요율 산정 요청 (불변)."""
    mtow_kg: float
    operation_type: str
    annual_flight_hours: float
    pilot_experience_years: float
    claims_in_3yr: int
    coverage_limit_krw: int
    night_ops: bool = False
    bvlos_ops: bool = False


@dataclass(frozen=True)
class PremiumLine:
    """견적 산출 명세 1행 — 라벨·적용계수·누적 보험료(원)."""
    label: str
    factor: float
    running_krw: int


@dataclass(frozen=True)
class Quote:
    """요율 산정 결과 (불변)."""
    annual_premium_krw: int
    base_premium_krw: int
    coverage_limit_krw: int
    is_mandatory: bool
    lines: tuple[PremiumLine, ...] = field(default_factory=tuple)


def _base_premium(mtow_kg: float) -> int:
    """MTOW 등급별 기본 보험료(원)."""
    for upper, premium in _MTOW_BASE_KRW:
        if mtow_kg <= upper:
            return premium
    return _MTOW_BASE_KRW[-1][1]  # pragma: no cover — inf 가드


def _experience_factor(years: float) -> float:
    """조종자 경력 할인 계수 (1.0 - 할인)."""
    discount = min(_EXPERIENCE_DISCOUNT_MAX, years * _EXPERIENCE_DISCOUNT_PER_YEAR)
    return 1.0 - discount


def _claims_factor(claims: int) -> float:
    """사고 이력 계수 — 무사고 할인(NCB) 또는 건당 할증."""
    if claims == 0:
        return _NO_CLAIMS_BONUS
    return 1.0 + _CLAIM_SURCHARGE_PER_EVENT * claims


def _validate(req: QuoteRequest) -> tuple[float, bool]:
    """입력 검증 후 (운용계수, 의무가입여부) 반환. 실패 시 ValueError."""
    if req.mtow_kg <= 0:
        raise ValueError(f"mtow_kg must be positive, got {req.mtow_kg}")
    if req.annual_flight_hours < 0:
        raise ValueError("annual_flight_hours must be non-negative")
    if req.annual_flight_hours > _MAX_ANNUAL_FLIGHT_HOURS:
        raise ValueError(
            f"annual_flight_hours cannot exceed {_MAX_ANNUAL_FLIGHT_HOURS} "
            f"(hours in one year)"
        )
    if req.pilot_experience_years < 0:
        raise ValueError("pilot_experience_years must be non-negative")
    # 사고 건수는 이산 정수 — 분수 입력은 NCB/할증 의미를 깨뜨린다 (bool 제외).
    if not isinstance(req.claims_in_3yr, int) or isinstance(req.claims_in_3yr, bool):
        raise TypeError(
            f"claims_in_3yr must be an int, got {type(req.claims_in_3yr).__name__}"
        )
    if req.claims_in_3yr < 0:
        raise ValueError("claims_in_3yr must be non-negative")
    if req.operation_type not in _OPERATION:
        raise ValueError(
            f"unknown operation_type {req.operation_type!r}; "
            f"expected one of {sorted(_OPERATION)}"
        )
    if req.coverage_limit_krw not in _COVERAGE_ILF:
        raise ValueError(
            f"coverage_limit_krw must be a standard tier {sorted(_COVERAGE_ILF)}, "
            f"got {req.coverage_limit_krw}"
        )
    op_factor, is_mandatory = _OPERATION[req.operation_type]
    if is_mandatory and req.coverage_limit_krw < MANDATORY_MIN_LIMIT_KRW:
        raise ValueError(
            f"{req.operation_type} is a commercial (mandatory) operation requiring "
            f"coverage >= {MANDATORY_MIN_LIMIT_KRW} KRW"
        )
    return op_factor, is_mandatory


def quote(req: QuoteRequest) -> Quote:
    """요청을 결정적으로 요율 산정해 ``Quote`` 반환.

    누적 곱 모델: 기본료 × 운용 × 비행시간 익스포저 × 한도(ILF) × 경력 × 사고이력
    × 야간 × 비가시. 각 단계는 ``PremiumLine`` 으로 추적된다.
    """
    op_factor, is_mandatory = _validate(req)

    base = _base_premium(req.mtow_kg)
    # 적용 순서대로의 (라벨, 계수) 단계 — 새 리스트 결합만으로 구성(무변형).
    steps = (
        [
            (f"operation:{req.operation_type}", op_factor),
            # 비행시간 익스포저: 1,000시간당 1배 가산.
            ("flight_hours_exposure", 1.0 + req.annual_flight_hours / 1000.0),
            ("coverage_ilf", _COVERAGE_ILF[req.coverage_limit_krw]),
            ("experience_discount", _experience_factor(req.pilot_experience_years)),
            ("claims_history", _claims_factor(req.claims_in_3yr)),
        ]
        + ([("night_loading", _NIGHT_LOADING)] if req.night_ops else [])
        + ([("bvlos_loading", _BVLOS_LOADING)] if req.bvlos_ops else [])
    )

    # 기본료에서 출발해 단계별 누적 곱 — 매 단계 새 리스트를 만들어 명세 추적.
    lines = [PremiumLine("base_premium", 1.0, base)]
    running = float(base)
    for label, factor in steps:
        running *= factor
        lines = lines + [PremiumLine(label, factor, int(round(running)))]

    premium = int(round(running / _ROUND_UNIT)) * _ROUND_UNIT
    return Quote(
        annual_premium_krw=premium,
        base_premium_krw=base,
        coverage_limit_krw=req.coverage_limit_krw,
        is_mandatory=is_mandatory,
        lines=tuple(lines),
    )

"""Phase 304 (GENESIS): KC 전파인증 요건 체크리스트 — 통신 모듈별 적합성평가 분류.

드론 탑재 통신 모듈(RC 링크·텔레메트리·영상 송신·셀룰러·GNSS 등)에 대해
「전파법」 제58조의2(방송통신기자재등의 적합성평가)에 따른 적합성평가 유형을
결정적으로 분류하고, 유형별 제출 서류 체크리스트를 생성한다.

외부 API 호출 없이 입력 검증 + 분류 + 체크리스트 export 만 수행한다
(결정적 분류 도구이며 법적 최종 판정을 대체하지 않는다 — 정확한 대역별
공중선전력 기술기준은 국립전파연구원 고시를 확인할 것).

적합성평가 3유형 (전파법 §58-2):
  - 적합인증: 간섭 위험이 큰 기자재 — 지정시험기관 시험성적서 + RRA 인증 필요.
  - 적합등록: 위험이 낮은 기자재 — 시험성적서(지정시험기관 또는 자기시험) + 등록.
  - 잠정인증: 기술기준이 마련되지 않은 신규 기자재.

분류 근거:
  - 셀룰러(LTE/5G) 송신 모듈 → 적합인증 (이동통신단말 추가요건 동반).
  - 비(非)면허 특정소출력 대역 내 + 공중선전력 한도 이내 송신기 → 적합등록.
  - 면허대역/특정소출력 한도 초과 송신기 → 적합인증.
  - 수신전용 기기(GNSS 수신기 등) → 적합등록(자기시험 가능).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

# 적합성평가 유형 (전파법 §58-2)
CERT_CERTIFICATION = "적합인증"
CERT_REGISTRATION = "적합등록"
CERT_PROVISIONAL = "잠정인증"

# 특정소출력(비면허) 대역 공중선전력 대표 한도 (dBm).
# 주의: 대역·용도별 정확한 한도는 국립전파연구원 고시(「신고하지 아니하고 개설할 수
# 있는 무선국용 무선설비의 기술기준」)를 따른다. 본 값은 일반 특정소출력 무선기기에
# 폭넓게 적용되는 대표 기준값(100 mW)으로, 분류 escalation 판정에만 사용한다.
SPECIFIED_LOW_POWER_EIRP_LIMIT_DBM = 20.0  # 100 mW


@dataclass(frozen=True)
class FreeUseBand:
    """비면허(특정소출력) 대역 정의."""

    name: str
    low_mhz: float
    high_mhz: float
    eirp_limit_dbm: float = SPECIFIED_LOW_POWER_EIRP_LIMIT_DBM


# 드론 통신에 주로 쓰이는 한국 비면허 대역
FREE_USE_BANDS: tuple[FreeUseBand, ...] = (
    FreeUseBand("900MHz ISM (RFID/USN)", 917.0, 923.5),
    FreeUseBand("2.4GHz ISM", 2400.0, 2483.5),
    FreeUseBand("5GHz UNII (WiFi)", 5150.0, 5350.0),
    FreeUseBand("5.8GHz ISM", 5725.0, 5825.0),
)


@dataclass(frozen=True)
class CommModule:
    """드론 탑재 통신 모듈 정보."""

    name: str
    band_mhz: float  # 중심 주파수 (MHz)
    tx_power_dbm: float = 0.0  # 송신 공중선전력 (dBm); 수신전용이면 0
    is_transmitter: bool = True
    kind: str = "data"  # data | video | telemetry | cellular | gnss | wifi | bluetooth


@dataclass(frozen=True)
class ModuleAssessment:
    """단일 모듈에 대한 적합성평가 분류 결과."""

    module_name: str
    cert_type: str
    requires_designated_lab: bool  # 지정시험기관 시험 필요 여부
    in_free_use_band: bool
    reasons: tuple[str, ...]


# 유형별 제출 서류 (적합성평가 운영고시 기준 대표 목록)
REQUIRED_DOCUMENTS: dict[str, tuple[str, ...]] = {
    CERT_CERTIFICATION: (
        "적합성평가 신청서",
        "지정시험기관 시험성적서",
        "사용자설명서(한글)",
        "외관도",
        "부품배치도 및 회로도",
        "(해외제조시) 국내대리인 지정서",
        "KC 적합성평가 표시 도안",
    ),
    CERT_REGISTRATION: (
        "적합성평가 신청서",
        "시험성적서(지정시험기관 또는 자기시험)",
        "사용자설명서(한글)",
        "외관도",
        "KC 적합성평가 표시 도안",
    ),
    CERT_PROVISIONAL: (
        "잠정인증 신청서",
        "기술기준(안)",
        "시험결과 자료",
        "안전성 평가 자료",
    ),
}

# 적합성평가 식별부호 표기 형식 안내 (RRA 부여)
KC_IDENTIFIER_FORMAT = "R-R-<업체부호>-<기자재명칭> (KC 마크와 함께 표시)"


def _find_free_use_band(band_mhz: float) -> FreeUseBand | None:
    """주파수가 속한 비면허 대역을 반환한다(없으면 ``None``)."""
    for band in FREE_USE_BANDS:
        if band.low_mhz <= band_mhz <= band.high_mhz:
            return band
    return None


def assess_module(module: CommModule) -> ModuleAssessment:
    """단일 통신 모듈의 적합성평가 유형을 결정적으로 분류한다.

    지정시험기관 시험 필요 여부는 유형에서 파생된다: 적합인증은 지정시험기관
    시험성적서가 필수이고, 적합등록은 자기시험으로 갈음할 수 있다.
    """
    reasons: list[str] = []

    # 셀룰러는 송수신 일체형 이동통신단말로 간주하므로 is_transmitter 와 무관하게
    # 항상 적합인증 대상으로 분류한다.
    if module.kind == "cellular":
        reasons.append("셀룰러(LTE/5G) 송신 모듈 — 적합인증 의무")
        reasons.append("이동통신단말: 식별번호(IMEI) 및 이동통신사 개통 별도 요건")
        return ModuleAssessment(
            module_name=module.name,
            cert_type=CERT_CERTIFICATION,
            requires_designated_lab=True,
            in_free_use_band=False,
            reasons=tuple(reasons),
        )

    if not module.is_transmitter:
        reasons.append("수신전용 기기 — 적합등록 대상(자기시험 가능)")
        return ModuleAssessment(
            module_name=module.name,
            cert_type=CERT_REGISTRATION,
            requires_designated_lab=False,
            in_free_use_band=False,
            reasons=tuple(reasons),
        )

    band = _find_free_use_band(module.band_mhz)
    if band is None:
        reasons.append(
            f"{module.band_mhz:.1f} MHz는 비면허 특정소출력 대역 외 — 적합인증 대상"
        )
        return ModuleAssessment(
            module_name=module.name,
            cert_type=CERT_CERTIFICATION,
            requires_designated_lab=True,
            in_free_use_band=False,
            reasons=tuple(reasons),
        )

    if module.tx_power_dbm > band.eirp_limit_dbm:
        reasons.append(
            f"공중선전력 {module.tx_power_dbm:.1f} dBm가 "
            f"'{band.name}' 한도 {band.eirp_limit_dbm:.1f} dBm 초과 — 적합인증 대상"
        )
        return ModuleAssessment(
            module_name=module.name,
            cert_type=CERT_CERTIFICATION,
            requires_designated_lab=True,
            in_free_use_band=True,
            reasons=tuple(reasons),
        )

    reasons.append(
        f"'{band.name}' 비면허 대역 + 공중선전력 한도 이내 "
        "— 적합등록 대상(자기시험 가능)"
    )
    return ModuleAssessment(
        module_name=module.name,
        cert_type=CERT_REGISTRATION,
        requires_designated_lab=False,
        in_free_use_band=True,
        reasons=tuple(reasons),
    )


def _validate_modules(modules: list[CommModule]) -> list[str]:
    """필수 입력값을 검증하고 누락/오류 목록을 반환한다."""
    errors: list[str] = []
    if not modules:
        errors.append("통신 모듈이 하나도 없음")
    for module in modules:
        if not module.name:
            errors.append("모듈 식별명이 비어 있음")
        if module.band_mhz <= 0:
            errors.append(f"'{module.name or '?'}' 주파수는 0보다 커야 함")
        if module.is_transmitter and module.tx_power_dbm <= 0:
            errors.append(
                f"'{module.name or '?'}' 송신기는 공중선전력이 0보다 커야 함"
            )
    return errors


def _overall_cert_type(assessments: list[ModuleAssessment]) -> str:
    """모듈별 결과 중 가장 엄격한 유형을 제품 전체 유형으로 채택한다."""
    if any(a.cert_type == CERT_CERTIFICATION for a in assessments):
        return CERT_CERTIFICATION
    return CERT_REGISTRATION


def build_checklist(product_name: str, modules: list[CommModule]) -> dict[str, Any]:
    """제품 단위 KC 적합성평가 체크리스트를 결정적으로 구성한다.

    검증 오류가 있으면 ``ValueError`` 를 발생시킨다(시스템 경계 입력 검증).
    """
    if not product_name:
        raise ValueError("KC 적합성평가 체크리스트 검증 실패: 제품명이 비어 있음")
    errors = _validate_modules(modules)
    if errors:
        raise ValueError("KC 적합성평가 체크리스트 검증 실패: " + "; ".join(errors))

    assessments = [assess_module(m) for m in modules]
    overall = _overall_cert_type(assessments)
    requires_designated_lab = any(a.requires_designated_lab for a in assessments)

    return {
        "form_type": "kc_radio_conformity_checklist",
        "product_name": product_name,
        "overall_cert_type": overall,
        "requires_designated_lab": requires_designated_lab,
        "identifier_format": KC_IDENTIFIER_FORMAT,
        "modules": [
            {
                "name": a.module_name,
                "cert_type": a.cert_type,
                "requires_designated_lab": a.requires_designated_lab,
                "in_free_use_band": a.in_free_use_band,
                "reasons": list(a.reasons),
            }
            for a in assessments
        ],
        "required_documents": list(REQUIRED_DOCUMENTS[overall]),
    }


def export_json(checklist: dict[str, Any]) -> str:
    """체크리스트 데이터를 UTF-8 JSON 문자열로 직렬화한다."""
    return json.dumps(checklist, ensure_ascii=False, indent=2, sort_keys=True)


def export_text(checklist: dict[str, Any]) -> str:
    """체크리스트 데이터를 사람이 읽는 한국어 양식 텍스트로 변환한다."""
    lab = "필요" if checklist["requires_designated_lab"] else "불요(자기시험 가능)"
    lines = [
        "═══ KC 전파인증(적합성평가) 체크리스트 ═══",
        "",
        f"제품명:        {checklist['product_name']}",
        f"전체 평가유형: {checklist['overall_cert_type']}",
        f"지정시험기관:  {lab}",
        f"식별부호 표기: {checklist['identifier_format']}",
        "",
        "[모듈별 분류]",
    ]
    for m in checklist["modules"]:
        band = "비면허대역" if m["in_free_use_band"] else "면허/대역외"
        lines.append(f"  · {m['name']}: {m['cert_type']} ({band})")
        lines += [f"     - {r}" for r in m["reasons"]]
    lines += ["", "[제출 서류]"]
    lines += [f"  □ {doc}" for doc in checklist["required_documents"]]
    return "\n".join(lines)

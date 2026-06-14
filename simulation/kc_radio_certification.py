"""Phase 304 (GENESIS): KC 전파인증 요건 체크리스트 — 통신 모듈별 적합성평가 판정.

드론에 탑재되는 통신 모듈(무선조종·영상송신·셀룰러·Wi-Fi/BT·GNSS 수신 등)에 대해
한국 「전파법」 및 국립전파연구원(RRA) 「방송통신기자재등의 적합성평가에 관한 고시」
기준으로 적합성평가 종류(적합인증/적합등록/잠정인증)와 구비서류를 결정적으로 산출한다.
외부 API 호출 없이 입력 검증 + 분류 + 주파수/출력 적합성 판정 + JSON/텍스트 export 만
수행한다.

판정 근거:
  - 셀룰러(LTE/5G) 등 간섭 우려가 큰 송신기 → 적합인증 (지정시험기관 성적서 필수)
  - 소출력 무선기기(2.4 GHz 조종·5.8 GHz 영상·Wi-Fi·BT·900 MHz 텔레메트리) → 적합등록
  - 수신전용 기기(GNSS 수신기) → 적합등록 (송신 없음 → 주파수/출력 점검 생략)
  - 적용 기술기준이 없는 신규 기술 → 잠정인증 (신청 사유서·기술기준안 추가)

주의: 기본 대역/EIRP 임계값(``KOREA_KC_BANDS``)은 국내 소출력 무선기기 기술기준을
대표하는 값이며, 실제 고시 개정에 따라 달라질 수 있다. 필요 시 ``bands`` 인자로 교체한다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

# 적합성평가 종류
CATEGORY_CERTIFICATION = "적합인증"
CATEGORY_REGISTRATION = "적합등록"
CATEGORY_PROVISIONAL = "잠정인증"

# 모듈 종류 → 적합성평가 종류 매핑
KIND_CELLULAR = "cellular"  # LTE/5G 등 → 적합인증
KIND_ISM_LOWPOWER = "ism_lowpower"  # 2.4G 조종·5.8G 영상·Wi-Fi·BT·900M → 적합등록
KIND_GNSS_RECEIVER = "gnss_receiver"  # 수신전용 → 적합등록
KIND_NOVEL = "novel"  # 적용 표준 없음 → 잠정인증

_KIND_TO_CATEGORY = {
    KIND_CELLULAR: CATEGORY_CERTIFICATION,
    KIND_ISM_LOWPOWER: CATEGORY_REGISTRATION,
    KIND_GNSS_RECEIVER: CATEGORY_REGISTRATION,
    KIND_NOVEL: CATEGORY_PROVISIONAL,
}


@dataclass(frozen=True)
class KcBand:
    """국내에서 허용되는 소출력 주파수 대역과 최대 EIRP(dBm)."""

    name: str
    f_min_mhz: float
    f_max_mhz: float
    max_eirp_dbm: float


# 국내 소출력 무선기기 대표 허용 대역 (전파연구원 기술기준 기반 대표값)
KOREA_KC_BANDS: tuple[KcBand, ...] = (
    KcBand("900 MHz USN/RFID", 917.0, 923.5, 10.0),
    KcBand("2.4 GHz ISM", 2400.0, 2483.5, 20.0),
    KcBand("5.2 GHz Wi-Fi", 5150.0, 5350.0, 23.0),
    KcBand("5.6 GHz Wi-Fi", 5470.0, 5725.0, 30.0),
    KcBand("5.8 GHz ISM", 5725.0, 5825.0, 25.0),
)


@dataclass(frozen=True)
class CommModule:
    """드론 탑재 통신 모듈 정보."""

    name: str
    kind: str  # KIND_* 중 하나
    freq_min_mhz: float
    freq_max_mhz: float
    tx_power_dbm: float = 0.0  # EIRP 기준 송신 출력 (수신전용은 무시)
    is_transmitter: bool = True


@dataclass(frozen=True)
class ModuleAssessment:
    """모듈 단위 적합성평가 판정 결과."""

    module_name: str
    category: str
    in_permitted_band: bool
    power_ok: bool
    matched_band: str
    required_documents: tuple[str, ...]
    issues: tuple[str, ...] = ()


# 적합성평가 공통 구비서류
_COMMON_DOCUMENTS = (
    "적합성평가 신청서",
    "기자재 시험성적서",
    "사용자설명서",
    "외관도",
    "부품배치도 또는 회로도",
)
# 종류별 추가 구비서류
_CATEGORY_DOCUMENTS = {
    CATEGORY_CERTIFICATION: ("지정시험기관 시험성적서(필수)",),
    CATEGORY_REGISTRATION: ("지정시험기관 또는 자기시험 성적서",),
    CATEGORY_PROVISIONAL: ("잠정인증 신청 사유서", "기술기준(안)"),
}


def classify_category(module: CommModule) -> str:
    """모듈 종류로부터 적합성평가 종류를 결정한다."""
    try:
        return _KIND_TO_CATEGORY[module.kind]
    except KeyError as exc:
        raise ValueError(f"알 수 없는 모듈 종류: {module.kind!r}") from exc


def find_band(module: CommModule, bands: tuple[KcBand, ...]) -> KcBand | None:
    """모듈 주파수 범위를 완전히 포함하는 허용 대역을 찾는다(없으면 None)."""
    for band in bands:
        if module.freq_min_mhz >= band.f_min_mhz and module.freq_max_mhz <= band.f_max_mhz:
            return band
    return None


def assess_module(
    module: CommModule, bands: tuple[KcBand, ...] | None = None
) -> ModuleAssessment:
    """단일 통신 모듈의 적합성평가 종류·대역 적합성·출력 적합성을 판정한다."""
    bands = KOREA_KC_BANDS if bands is None else bands
    category = classify_category(module)
    issues: list[str] = []

    # 수신전용 기기는 송신이 없으므로 대역/출력 점검을 생략한다.
    if not module.is_transmitter:
        documents = _COMMON_DOCUMENTS + _CATEGORY_DOCUMENTS[category]
        return ModuleAssessment(
            module_name=module.name,
            category=category,
            in_permitted_band=True,
            power_ok=True,
            matched_band="(수신전용)",
            required_documents=documents,
            issues=(),
        )

    band = find_band(module, bands)
    in_permitted_band = band is not None
    power_ok = True
    matched_band = "(허용 대역 없음)"

    if band is None:
        # 셀룰러(면허 대역)와 잠정인증(기존 표준 없음)은 소출력 대역 미포함이 정상.
        if category not in (CATEGORY_CERTIFICATION, CATEGORY_PROVISIONAL):
            issues.append(
                f"주파수 {module.freq_min_mhz:.1f}–{module.freq_max_mhz:.1f} MHz가 "
                "국내 허용 소출력 대역에 포함되지 않음"
            )
    else:
        matched_band = band.name
        if module.tx_power_dbm > band.max_eirp_dbm:
            power_ok = False
            issues.append(
                f"송신출력 {module.tx_power_dbm:.1f} dBm이 대역 한계 "
                f"{band.max_eirp_dbm:.1f} dBm(EIRP)를 초과"
            )

    documents = _COMMON_DOCUMENTS + _CATEGORY_DOCUMENTS[category]
    return ModuleAssessment(
        module_name=module.name,
        category=category,
        in_permitted_band=in_permitted_band,
        power_ok=power_ok,
        matched_band=matched_band,
        required_documents=documents,
        issues=tuple(issues),
    )


def _validate_module(module: CommModule) -> list[str]:
    """모듈 입력값을 검증하고 오류 목록을 반환한다(시스템 경계 검증)."""
    errors: list[str] = []
    if not module.name:
        errors.append("모듈 명칭이 비어 있음")
    if module.kind not in _KIND_TO_CATEGORY:
        errors.append(f"모듈 종류 '{module.kind}'가 유효하지 않음")
    if module.freq_min_mhz <= 0 or module.freq_max_mhz <= 0:
        errors.append("주파수는 0보다 커야 함")
    if module.freq_max_mhz < module.freq_min_mhz:
        errors.append("최대 주파수가 최소 주파수보다 작을 수 없음")
    if module.is_transmitter and module.freq_min_mhz == module.freq_max_mhz:
        errors.append("송신기의 최소·최대 주파수가 동일함 (영대역)")
    return errors


def build_checklist(
    modules: list[CommModule], bands: tuple[KcBand, ...] | None = None
) -> dict[str, Any]:
    """통신 모듈 목록에 대한 KC 적합성평가 체크리스트를 결정적으로 구성한다.

    검증 오류가 있으면 ``ValueError`` 를 발생시킨다(시스템 경계 입력 검증).
    """
    if not modules:
        raise ValueError("통신 모듈 목록이 비어 있음")

    errors: list[str] = []
    for module in modules:
        for err in _validate_module(module):
            errors.append(f"[{module.name or '?'}] {err}")
    if errors:
        raise ValueError("KC 전파인증 체크리스트 검증 실패: " + "; ".join(errors))

    assessments = [assess_module(m, bands) for m in modules]
    items = [
        {
            "module_name": a.module_name,
            "category": a.category,
            "in_permitted_band": a.in_permitted_band,
            "power_ok": a.power_ok,
            "matched_band": a.matched_band,
            "required_documents": list(a.required_documents),
            "issues": list(a.issues),
        }
        for a in assessments
    ]
    all_clear = all(not a.issues for a in assessments)

    return {
        "form_type": "kc_radio_certification_checklist",
        "module_count": len(items),
        "all_clear": all_clear,
        "items": items,
    }


def export_json(checklist: dict[str, Any]) -> str:
    """체크리스트를 UTF-8 JSON 문자열로 직렬화한다."""
    return json.dumps(checklist, ensure_ascii=False, indent=2, sort_keys=True)


def export_text(checklist: dict[str, Any]) -> str:
    """체크리스트를 사람이 읽는 한국어 양식 텍스트로 변환한다."""
    lines = [
        "═══ KC 전파인증(적합성평가) 요건 체크리스트 ═══",
        "",
        f"대상 모듈 수: {checklist['module_count']}개 / "
        f"종합 적합: {'예' if checklist['all_clear'] else '아니오'}",
    ]
    for idx, item in enumerate(checklist["items"], start=1):
        band_ok = "적합" if item["in_permitted_band"] else "부적합"
        power_ok = "적합" if item["power_ok"] else "초과"
        lines += [
            "",
            f"[{idx}] {item['module_name']}",
            f"  평가종류:  {item['category']}",
            f"  대역:      {item['matched_band']} ({band_ok})",
            f"  출력:      {power_ok}",
            "  구비서류:",
        ]
        lines += [f"   - {d}" for d in item["required_documents"]]
        if item["issues"]:
            lines.append("  지적사항:")
            lines += [f"   ! {i}" for i in item["issues"]]
    return "\n".join(lines)

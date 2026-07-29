"""ODYSSEY Phase 482 — 브라우저 API 폐기 감시.

Continuum 트랙(Phase 481-500)의 한 칸. HTML 시뮬레이터(`swarm_3d_simulator.html`·
`maritime_detection_simulator.html`)는 여러 브라우저 API 위에 직접 올라가 있다.
브라우저 벤더는 표준 API 를 *비표준화·실험·폐기* 단계로 옮기며, 한 API 가
의존 사슬에서 빠지면 시뮬레이터가 *조용히* 깨진다. 사람이 매번 caniuse 를
직관으로 추적하면 놓치기 쉽다.

본 모듈은 그 판단을 *결정적 정책* 으로 명문화한다 — 시뮬레이터가 *실제로*
쓰는 API 와 각 API 의 표준화 상태·의존 방식만 주어지면 항상 같은 위험 등급·
권고를 낸다. Phase 484(`electron_lts_policy`)·488(`cve_response_policy`)의
*결정적 정책 모듈·부수효과 0·자문* 패턴을 따른다.

카나리 논리
----------
핵심 통찰: *위험한 것은 실험/폐기 API 가 아니라, 그것을 hard dependency 로
요구하는 것* 이다. 같은 실험 API라도 feature-detection 으로 우아하게 폴백하면
(progressive enhancement) 스펙 변경이 와도 시뮬레이터는 살아남는다. 따라서
평가는 (표준화 상태 × 의존 방식) 2차원으로 위험을 가른다 — 실험 API 를 *필수*
로 쓰는 조합만이 카나리(조기 경보) 대상이다.

설계 원칙
--------
- **정책은 코드, 코드는 정책**: 위험 규칙을 문서(``docs/standards/
  BROWSER_API_DEPRECATION_WATCH.md``)와 본 평가기에 *한 번씩만* 적기 위해 본
  모듈이 유일한 실행 가능 명세다. 문서는 규칙을 서술할 뿐 중복 로직이 없다.
- **자문이지 집행 아님**: 본 모듈은 *권고* 할 뿐 코드를 고치거나 빌드를 막지
  않는다(부수효과 0). 사람/CI 가 결정을 집행한다.
- **정직한 스냅샷**: 리포에 caniuse/Baseline 라이브 피드가 없으므로 각 API 의
  표준화 상태는 *수동 스냅샷*(``_REGISTRY``, ``SNAPSHOT_AS_OF`` 날짜 명시)이다.
  ``shipped_registry`` 는 시뮬레이터가 실측으로 쓰는 API 목록을 *있는 그대로*
  판정한다 — 상태를 최신/안전으로 포장하지 않는다.

무작위성 0 · 결정적 · 기존 모듈 무수정 순수 추가.

CLI:
    python -m simulation.browser_api_watch --policy     # 위험 매트릭스
    python -m simulation.browser_api_watch --status     # 리포 실측 API 판정
    python -m simulation.browser_api_watch --demo       # 예시 평가
    python -m simulation.browser_api_watch --manifest   # 정책 매니페스트(JSON)
"""
from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

# 스냅샷 기준일. 표준화 상태는 이 날짜의 수동 관측이다(라이브 피드 없음).
SNAPSHOT_AS_OF = "2026-06-19"

# --- 표준화 상태 -----------------------------------------------------------
# W3C/WHATWG Baseline 개념을 단순화: 모든 주요 엔진(Chromium·Gecko·WebKit)에서
# 안정적으로 쓸 수 있는지로 가른다.
STATUS_BASELINE_WIDE = "BASELINE_WIDE"    # 전 엔진 30개월+ 안정 — 깨질 위험 낮음
STATUS_BASELINE_NEW = "BASELINE_NEW"      # 전 엔진 진입했으나 최근 — 구버전 사용자 주의
STATUS_EXPERIMENTAL = "EXPERIMENTAL"      # 일부 엔진/플래그 뒤 — 스펙 변동 위험
STATUS_DEPRECATED = "DEPRECATED"          # 제거 예고 — 능동 마이그레이션 필요
STATUS_UNKNOWN = "UNKNOWN"                # 미분류 — 사람 확인

_STATUSES = (
    STATUS_BASELINE_WIDE,
    STATUS_BASELINE_NEW,
    STATUS_EXPERIMENTAL,
    STATUS_DEPRECATED,
    STATUS_UNKNOWN,
)

# --- 의존 방식 -------------------------------------------------------------
MODE_REQUIRED = "REQUIRED"   # 없으면 시뮬레이터 hard-fail (폴백 없음)
MODE_ENHANCED = "ENHANCED"   # feature-detect + 우아한 폴백 (progressive enhancement)

_MODES = (MODE_REQUIRED, MODE_ENHANCED)

# --- 위험 등급 -------------------------------------------------------------
TIER_STABLE = "STABLE"        # baseline-wide — 조치 불필요
TIER_WATCH = "WATCH"          # baseline-new 거나 실험이지만 폴백 있음 — 감시
TIER_FRAGILE = "FRAGILE"      # 실험 API 를 필수로 사용 — 단일 실패점, 폴백 필요
TIER_SUNSET = "SUNSET"        # 폐기 API(폴백 있음) — 마이그레이션 계획
TIER_BREAKING = "BREAKING"    # 폐기 API 를 필수로 사용 — 즉시 마이그레이션
TIER_UNKNOWN = "UNKNOWN"      # 상태 미분류 — 사람 확인

# --- 권고 결정 -------------------------------------------------------------
ACTION_WITHIN_SLA = "WITHIN_SLA"          # 조치 불필요
ACTION_MONITOR = "MONITOR"                # 스펙/지원 변화 감시
ACTION_ADD_FALLBACK = "ADD_FALLBACK"      # 폴백 추가(필수 의존 → 선택 의존으로 강등)
ACTION_PLAN_MIGRATION = "PLAN_MIGRATION"  # 대체 API 로 이전 계획
ACTION_MIGRATE_NOW = "MIGRATE_NOW"        # 즉시 이전(폐기 + 필수)
ACTION_REVIEW = "REVIEW"                  # 평가 불가 — 사람 확인


# 권위 있는 위험 매트릭스: (status, mode) → (tier, action). assess() 가 이 표를
# 사용한다(중복 로직 아님 — 테스트가 일치 강제).
_RISK_MATRIX: dict[tuple[str, str], tuple[str, str]] = {
    (STATUS_BASELINE_WIDE, MODE_REQUIRED): (TIER_STABLE, ACTION_WITHIN_SLA),
    (STATUS_BASELINE_WIDE, MODE_ENHANCED): (TIER_STABLE, ACTION_WITHIN_SLA),
    (STATUS_BASELINE_NEW, MODE_REQUIRED): (TIER_WATCH, ACTION_MONITOR),
    (STATUS_BASELINE_NEW, MODE_ENHANCED): (TIER_WATCH, ACTION_MONITOR),
    # 카나리 핵심: 실험 API 를 *필수* 로 쓰면 단일 실패점.
    (STATUS_EXPERIMENTAL, MODE_REQUIRED): (TIER_FRAGILE, ACTION_ADD_FALLBACK),
    # 같은 실험 API라도 폴백 있으면 감시로 충분.
    (STATUS_EXPERIMENTAL, MODE_ENHANCED): (TIER_WATCH, ACTION_MONITOR),
    (STATUS_DEPRECATED, MODE_REQUIRED): (TIER_BREAKING, ACTION_MIGRATE_NOW),
    (STATUS_DEPRECATED, MODE_ENHANCED): (TIER_SUNSET, ACTION_PLAN_MIGRATION),
}


@dataclass(frozen=True)
class BrowserApi:
    """감시 대상 브라우저 API 한 건(불변).

    Attributes:
        name: API 식별자(예: ``"WebGPU"``).
        status: 표준화 상태(``_STATUSES`` 중 하나).
        mode: 시뮬레이터의 의존 방식(``MODE_REQUIRED``/``MODE_ENHANCED``).
        used_by: 시뮬레이터 내 사용 위치/용도(정직성 — 실측 근거).
    """

    name: str
    status: str
    mode: str
    used_by: str

    def __post_init__(self) -> None:
        # 정직성: 빈 식별자/근거는 "정직한 스냅샷" 계약을 깨므로 거부한다
        # (sibling `cve_response_policy.CveReport` 와 동일 포스처).
        if not self.name.strip():
            raise ValueError("BrowserApi.name 은 비어 있을 수 없습니다")
        if not self.used_by.strip():
            raise ValueError("BrowserApi.used_by 는 비어 있을 수 없습니다(추적 근거)")


@dataclass(frozen=True)
class ApiAssessment:
    """평가 결과(불변). action 과 그 근거(reason)."""

    name: str
    action: str
    tier: str
    status: str
    mode: str
    reason: str

    def summary(self) -> str:
        """사람이 읽는 한 줄 요약."""
        return f"{self.name}: {self.action} ({self.tier}) — {self.reason}"


def assess(api: BrowserApi) -> ApiAssessment:
    """단일 브라우저 API 의존에 대한 권고를 결정적으로 산출한다.

    상태·의존 방식이 분류 밖이면(오타·미지정) REVIEW 로 보낸다(정직성 —
    추측해서 안전 등급을 주지 않는다).
    """
    if api.status not in _STATUSES or api.mode not in _MODES:
        return ApiAssessment(
            api.name, ACTION_REVIEW, TIER_UNKNOWN, api.status, api.mode,
            f"분류 밖 입력(status={api.status!r}, mode={api.mode!r}) — 사람 확인",
        )
    if api.status == STATUS_UNKNOWN:
        return ApiAssessment(
            api.name, ACTION_REVIEW, TIER_UNKNOWN, api.status, api.mode,
            f"{api.name} 표준화 상태 미분류 — 사람 확인",
        )
    tier, action = _RISK_MATRIX[(api.status, api.mode)]
    reason = _reason_for(api, tier)
    return ApiAssessment(api.name, action, tier, api.status, api.mode, reason)


def _reason_for(api: BrowserApi, tier: str) -> str:
    """위험 등급에 맞는 사람 친화 근거 문장."""
    name, mode = api.name, api.mode
    if tier == TIER_STABLE:
        return f"{name} 은 전 엔진 안정(baseline-wide) — {mode} 의존 안전"
    if tier == TIER_WATCH:
        if api.status == STATUS_BASELINE_NEW:
            return f"{name} 은 전 엔진 진입했으나 최근 — 구버전 사용자 위해 감시"
        return f"{name} 은 실험 단계이나 폴백 있는 {mode} — 스펙 변화 감시로 충분"
    if tier == TIER_FRAGILE:
        return f"{name} 은 실험 단계인데 {mode} 의존 — 단일 실패점, feature-detect 폴백 추가 권장"
    if tier == TIER_SUNSET:
        return f"{name} 은 폐기 예고(폴백 있음) — 대체 API 이전 계획"
    if tier == TIER_BREAKING:
        return f"{name} 은 폐기 예고인데 {mode} 의존 — 즉시 이전 필요"
    # _RISK_MATRIX 가 내는 5개 tier 는 위에서 전부 처리된다. 여기 닿으면
    # 새 tier 가 추가됐는데 본 함수가 갱신 안 된 것 — 조용히 가리지 않고 즉시 노출.
    raise AssertionError(f"_reason_for 에 처리되지 않은 tier: {tier!r}")


# --- 리포 실측 레지스트리 --------------------------------------------------
# 시뮬레이터가 *실제로* 쓰는 브라우저 API 의 수동 스냅샷(2026-06-19 관측).
# 사용처는 `swarm_3d_simulator.html`·`maritime_detection_simulator.html` 실측.
# 표준화 상태는 caniuse/MDN Baseline 의 수동 관측이며, 갱신 시 SNAPSHOT_AS_OF
# 와 함께 고친다.
_REGISTRY: tuple[BrowserApi, ...] = (
    BrowserApi("WebGL", STATUS_BASELINE_WIDE, MODE_REQUIRED,
               "three.js WebGLRenderer — 3D 렌더링 코어"),
    BrowserApi("requestAnimationFrame", STATUS_BASELINE_WIDE, MODE_REQUIRED,
               "렌더 루프 프레임 구동"),
    BrowserApi("WebGL2", STATUS_BASELINE_WIDE, MODE_ENHANCED,
               "three.js 고급 셰이더(미지원 시 WebGL1 폴백)"),
    BrowserApi("WebSocket", STATUS_BASELINE_WIDE, MODE_ENHANCED,
               "ws_bridge LIVE 텔레메트리 토글(미연결 시 합성 데이터)"),
    BrowserApi("AudioContext", STATUS_BASELINE_WIDE, MODE_ENHANCED,
               "경보음(미지원 시 무음 폴백)"),
    BrowserApi("MediaRecorder", STATUS_BASELINE_NEW, MODE_ENHANCED,
               "데모 영상 녹화(미지원 시 녹화 버튼 비활성)"),
    # 카나리 대상: 실험 단계지만 모두 feature-detect 폴백 → FRAGILE 아님.
    BrowserApi("WebGPU", STATUS_EXPERIMENTAL, MODE_ENHANCED,
               "navigator.gpu 가속 경로(미지원 시 WebGL 폴백, Phase 221 실 WGSL 예정)"),
    BrowserApi("WebXR", STATUS_EXPERIMENTAL, MODE_ENHANCED,
               "navigator.xr VR 모드(미지원 시 데스크탑 뷰)"),
)


def shipped_registry() -> tuple[BrowserApi, ...]:
    """시뮬레이터가 현재 *실제* 쓰는 브라우저 API 레지스트리(스냅샷)."""
    return _REGISTRY


# 종합 자세(posture): 어떤 API 라도 BREAKING/FRAGILE 면 AT_RISK.
POSTURE_RESILIENT = "RESILIENT"  # 위험(필수+실험/폐기) 없음
POSTURE_AT_RISK = "AT_RISK"      # 카나리 한 건 이상 발화


# 종합 자세를 AT_RISK 로 끌어내리는 tier: 카나리 둘(필수+실험/폐기)에 더해
# UNKNOWN(미분류 — 안전을 *증명* 못함)을 포함한다. RESILIENT 는 "폐기에 견고함"을
# 주장하는데 분류 안 된 의존이 있으면 그 주장을 정직하게 할 수 없다.
_POSTURE_TRIPPING_TIERS = (TIER_BREAKING, TIER_FRAGILE, TIER_UNKNOWN)


@dataclass(frozen=True)
class WatchReport:
    """레지스트리 종합 평가(불변)."""

    posture: str
    assessments: tuple[ApiAssessment, ...]
    tier_counts: Mapping[str, int]

    def actionable(self) -> tuple[ApiAssessment, ...]:
        """즉시 조치/검토가 필요한(자세를 떨어뜨리는) 항목만 — BREAKING·FRAGILE·UNKNOWN."""
        return tuple(a for a in self.assessments if a.tier in _POSTURE_TRIPPING_TIERS)

    def non_stable(self) -> tuple[ApiAssessment, ...]:
        """STABLE 아닌 모든 항목(감시 대상 포함). 정보용 필터 — 위험 신호 아님."""
        return tuple(a for a in self.assessments if a.tier != TIER_STABLE)

    def summary(self) -> str:
        others = self.non_stable()
        head = f"{self.posture}: {len(self.assessments)}개 API"
        if not others:
            return f"{head} 전부 STABLE"
        # 자세별로 의미를 분리해 "RESILIENT … 주의 N건" 같은 모순 표현을 피한다.
        label = "조치" if self.posture == POSTURE_AT_RISK else "감시"
        names = ", ".join(f"{a.name}({a.tier})" for a in others)
        return f"{head} — {label} {len(others)}건: {names}"


def assess_registry(registry: tuple[BrowserApi, ...] | None = None) -> WatchReport:
    """레지스트리 전체를 평가하고 종합 자세를 결정적으로 산출한다.

    BREAKING(폐기+필수)·FRAGILE(실험+필수)·UNKNOWN(미분류)이 하나라도 있으면
    AT_RISK, 그 외에는 RESILIENT. 실험/폐기 API 라도 폴백(ENHANCED)이면 자세를
    떨어뜨리지 않는다 — 카나리는 *필수 의존* 만 발화한다.
    """
    reg = _REGISTRY if registry is None else registry
    assessments = tuple(assess(api) for api in reg)
    counts: dict[str, int] = {}
    for a in assessments:
        counts[a.tier] = counts.get(a.tier, 0) + 1
    tripping = sum(counts.get(t, 0) for t in _POSTURE_TRIPPING_TIERS)
    posture = POSTURE_AT_RISK if tripping else POSTURE_RESILIENT
    # frozen 계약을 dict 내부까지 지킨다 — 호출자가 in-place 변형 못 하도록 동결.
    return WatchReport(posture, assessments, MappingProxyType(counts))


def policy_manifest() -> dict[str, Any]:
    """정책을 JSON 직렬화 가능한 매니페스트로 굳힌다."""
    return {
        "schema": "sdacs-browser-api-watch",
        "version": "1.0",
        "snapshot_as_of": SNAPSHOT_AS_OF,
        "statuses": list(_STATUSES),
        "modes": list(_MODES),
        "actions": [
            ACTION_WITHIN_SLA, ACTION_MONITOR, ACTION_ADD_FALLBACK,
            ACTION_PLAN_MIGRATION, ACTION_MIGRATE_NOW, ACTION_REVIEW,
        ],
        "matrix": [
            {"status": status, "mode": mode, "tier": tier, "action": action}
            for (status, mode), (tier, action) in _RISK_MATRIX.items()
        ],
    }


# 정책 동작을 보이는 결정적 예시(전 등급 커버 — STABLE·WATCH·FRAGILE·SUNSET·
# BREAKING·UNKNOWN).
_DEMO_APIS: tuple[BrowserApi, ...] = (
    BrowserApi("WebGL", STATUS_BASELINE_WIDE, MODE_REQUIRED, "예시"),
    BrowserApi("MediaRecorder", STATUS_BASELINE_NEW, MODE_ENHANCED, "예시"),
    BrowserApi("WebGPU", STATUS_EXPERIMENTAL, MODE_ENHANCED, "예시(폴백 있음)"),
    BrowserApi("WebXR", STATUS_EXPERIMENTAL, MODE_REQUIRED, "예시(폴백 없음 가정)"),
    BrowserApi("WebSQL", STATUS_DEPRECATED, MODE_ENHANCED, "예시(폐기+폴백)"),
    BrowserApi("AppCache", STATUS_DEPRECATED, MODE_REQUIRED, "예시(폐기+필수)"),
    BrowserApi("LegacyAPI", STATUS_UNKNOWN, MODE_REQUIRED, "예시(상태 미분류)"),
)


def _cmd_policy() -> None:
    print(f"브라우저 API 폐기 감시 정책 (스냅샷 {SNAPSHOT_AS_OF})")
    print(f"{'STATUS':<16}{'MODE':<10}{'TIER':<10}ACTION")
    for (status, mode), (tier, action) in _RISK_MATRIX.items():
        print(f"{status:<16}{mode:<10}{tier:<10}{action}")


def _cmd_status() -> None:
    report = assess_registry()
    print(f"리포 실측 브라우저 API ({SNAPSHOT_AS_OF}) — {report.summary()}")
    for a in report.assessments:
        print(f"  {a.summary()}")


def _cmd_demo() -> None:
    print("예시 평가:")
    for api in _DEMO_APIS:
        print(f"  {assess(api).summary()}")


_KNOWN_FLAGS = ("--policy", "--status", "--demo", "--manifest")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    unknown = [a for a in args if a not in _KNOWN_FLAGS]
    if unknown:
        print(f"알 수 없는 인자: {' '.join(unknown)}", file=sys.stderr)
        print(f"사용법: {' | '.join(_KNOWN_FLAGS)}", file=sys.stderr)
        return 2
    if "--manifest" in args:
        print(json.dumps(policy_manifest(), ensure_ascii=False, indent=2))
        return 0
    if "--status" in args:
        _cmd_status()
        return 0
    if "--demo" in args:
        _cmd_demo()
        return 0
    _cmd_policy()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

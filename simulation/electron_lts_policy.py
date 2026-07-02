"""ODYSSEY Phase 484 — Electron LTS 추적 정책.

Continuum 트랙(Phase 481-500)의 한 칸. 데스크탑 앱은 Electron 런타임 위에
빌드되는데, Electron 은 **최신 3개 stable major** 만 보안 패치를 지원한다(약
8주마다 새 major 출시). 핀이 이 창(window) 밖으로 밀려나면 *보안 백포트가
끊긴* 채로 배포되는데, 이를 사람이 매번 직관으로 추적하면 놓치기 쉽다.

본 모듈은 그 판단을 *결정적 정책* 으로 명문화한다 — 핀 major 와 상류 최신
stable major 만 주어지면 항상 같은 지원 등급·권고를 낸다.

교훈(현 32→39 표류)
-------------------
v1.5.0 데스크탑 빌드는 Electron 32 로 동결되었고 핀은 그 뒤 39 로 점프했다.
32 는 39 출시 시점에 이미 *7 major* 뒤(지원 창 3 의 두 배 이상)였다 — 즉 오랜
기간 EOL 런타임으로 빌드된 셈이다. 본 정책은 그 표류가 *조용히* 일어나지
않도록, 핀이 창 끝(ENDING)에 닿는 순간 PLAN_UPGRADE, 창을 벗어나면(EOL)
UPGRADE_NOW 를 결정적으로 권고한다.

설계 원칙
--------
- **정책은 코드, 코드는 정책**: 지원 규칙을 문서(``docs/standards/
  ELECTRON_LTS_TRACKING_POLICY.md``)와 본 평가기에 *한 번씩만* 적기 위해 본
  모듈이 유일한 실행 가능 명세다. 문서는 규칙을 서술할 뿐 중복 로직이 없다.
- **자문이지 집행 아님**: 본 모듈은 *권고* 할 뿐 실제로 핀을 올리거나 빌드를
  막지 않는다(부수효과 0). 사람/CI 가 결정을 집행한다.
- **정직한 스냅샷**: 상류 최신 major 는 리포에 없으므로 *수동 스냅샷 상수*
  (``OBSERVED_LATEST_STABLE_MAJOR``, 날짜 명시)로 둔다. ``shipped_runtime`` 은
  이 스냅샷과 ``package.json`` 실측 핀을 짝지어 현 상태를 *있는 그대로* 판정
  한다 — 메타데이터를 최신으로 포장하지 않는다.

무작위성 0 · 결정적 · 기존 모듈 무수정 순수 추가.

CLI:
    python -m simulation.electron_lts_policy --policy    # 정책 매트릭스
    python -m simulation.electron_lts_policy --status    # 리포 핀 실측 판정
    python -m simulation.electron_lts_policy --demo      # 예시 평가
    python -m simulation.electron_lts_policy --manifest  # 정책 매니페스트(JSON)
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Electron 지원 정책(상류 공시): 최신 3개 stable major 만 보안 패치, 약 8주
# 주기로 새 major 출시. 출처: electronjs.org/docs/latest/tutorial/electron-timelines
SUPPORT_WINDOW_MAJORS = 3
RELEASE_CADENCE_WEEKS = 8

# 상류 최신 stable major 의 *수동 스냅샷*. 리포에 상류 캘린더가 없으므로 본
# 상수를 정직한 단일 출처로 둔다. 갱신 시 날짜를 함께 고친다.
#   2026-07-02 기준 Electron 최신 stable = 43 (npm dist-tag ``latest`` =
#   43.0.0, 42.x 는 한 major 뒤로 밀림. 리포 Dependabot 이 devDependencies
#   electron 을 ^43.0.0 으로 상향 = 상류가 43 을 stable 로 내놓았다는 실측 증거).
OBSERVED_LATEST_STABLE_MAJOR = 43
OBSERVED_LATEST_AS_OF = "2026-07-02"

# 리포 핀 출처.
_PACKAGE_JSON = "package.json"

# 선행 범위 연산자(^ ~ >= 등)·v 접두를 떼고 첫 정수 major 를 잡는다.
# `<` 는 의도적으로 제외 — `"<40"`(상한) 같은 스펙은 핀 major 를 *과대* 추정
# 하므로(40 으로 보이나 실제로는 39 이하) 차라리 거부해 REVIEW 로 보낸다.
# `>=40`·`>40` 의 선두 정수는 하한이라 보수적 근사로 허용한다.
_MAJOR = re.compile(r"^[\^~>=v\s]*(\d+)(?:\.|$)")

# --- 지원 등급 -------------------------------------------------------------
TIER_CURRENT = "CURRENT"      # lag 0 — 최신 stable
TIER_SUPPORTED = "SUPPORTED"  # 0 < lag < window-1 — 창 내부(여유 있음)
TIER_ENDING = "ENDING"        # lag == window-1 — 창의 마지막 칸(곧 EOL)
TIER_EOL = "EOL"              # lag >= window — 보안 백포트 종료
TIER_AHEAD = "AHEAD"          # lag < 0 — 핀이 알려진 최신보다 앞섬(스냅샷 stale/프리릴리스)

# --- 권고 결정 -------------------------------------------------------------
ACTION_WITHIN_SLA = "WITHIN_SLA"      # 조치 불필요
ACTION_PLAN_UPGRADE = "PLAN_UPGRADE"  # 다음 상류 major 전에 업그레이드 계획
ACTION_UPGRADE_NOW = "UPGRADE_NOW"    # EOL — 즉시 업그레이드
ACTION_REVIEW = "REVIEW"              # 평가 불가/이상 — 사람 확인


def parse_major(version: str) -> int | None:
    """버전 스펙에서 major 정수를 결정적으로 파싱한다. 실패하면 None.

    허용: ``"39.8.5"``·``"^39.8.5"``·``"~42"``·``">=40.0.0"``·``"v41"``.
    거부(→ None → REVIEW): ``"latest"``·``"*"``·빈 문자열·비숫자 선두.
    """
    match = _MAJOR.match(version.strip())
    if match is None:
        return None
    return int(match.group(1))


def support_tier(pinned_major: int, latest_major: int) -> str:
    """핀 major 와 상류 최신 major 로 지원 등급을 결정적으로 분류한다."""
    lag = latest_major - pinned_major
    if lag < 0:
        return TIER_AHEAD
    if lag == 0:
        return TIER_CURRENT
    # ENDING(창의 마지막 칸)을 EOL(창 밖) *앞에서* 검사한다 — 경계가 window
    # 값과 무관하게 명확하도록(SUPPORT_WINDOW_MAJORS 변경 시에도 안전).
    if lag == SUPPORT_WINDOW_MAJORS - 1:
        return TIER_ENDING
    if lag >= SUPPORT_WINDOW_MAJORS:
        return TIER_EOL
    return TIER_SUPPORTED


# 지원 등급 → 권고 결정(권위 있는 매핑). assess() 가 이 표를 사용한다.
_TIER_ACTION: dict[str, str] = {
    TIER_CURRENT: ACTION_WITHIN_SLA,
    TIER_SUPPORTED: ACTION_WITHIN_SLA,
    TIER_ENDING: ACTION_PLAN_UPGRADE,
    TIER_EOL: ACTION_UPGRADE_NOW,
    TIER_AHEAD: ACTION_REVIEW,
}


@dataclass(frozen=True)
class ElectronRuntime:
    """평가 대상 Electron 런타임 상태(불변).

    Attributes:
        pinned_major: 리포가 고정한 Electron major.
        latest_stable_major: 상류 최신 stable major(스냅샷).
    """

    pinned_major: int
    latest_stable_major: int

    def lag(self) -> int:
        """상류 최신 대비 핀이 몇 major 뒤인지(음수면 앞섬)."""
        return self.latest_stable_major - self.pinned_major


@dataclass(frozen=True)
class LtsAssessment:
    """평가 결과(불변). action 과 그 근거(reasons)."""

    action: str
    tier: str
    lag: int
    reasons: tuple[str, ...]

    def summary(self) -> str:
        """사람이 읽는 한 줄 요약."""
        return f"{self.action} ({self.tier}, lag={self.lag}): {'; '.join(self.reasons)}"


def assess(runtime: ElectronRuntime) -> LtsAssessment:
    """단일 Electron 런타임 상태에 대한 권고를 결정적으로 산출한다.

    등급 → 권고:
        - CURRENT/SUPPORTED → WITHIN_SLA (창 내부, 보안 패치 수신).
        - ENDING → PLAN_UPGRADE (창의 마지막 칸 — 다음 상류 major 출시 시 EOL).
        - EOL → UPGRADE_NOW (보안 백포트 종료 — 즉시 조치).
        - AHEAD → REVIEW (핀이 스냅샷보다 앞섬 — 스냅샷 갱신/프리릴리스 확인).
    """
    lag = runtime.lag()
    tier = support_tier(runtime.pinned_major, runtime.latest_stable_major)
    action = _TIER_ACTION[tier]

    pin, latest = runtime.pinned_major, runtime.latest_stable_major
    if tier == TIER_CURRENT:
        reason = f"Electron {pin} = 최신 stable"
    elif tier == TIER_SUPPORTED:
        reason = f"Electron {pin} 은 최신 {latest} 대비 {lag} 뒤 — 지원 창({SUPPORT_WINDOW_MAJORS}) 내부"
    elif tier == TIER_ENDING:
        reason = (f"Electron {pin} 은 지원 창의 마지막 칸 — 다음 상류 major "
                  f"출시(약 {RELEASE_CADENCE_WEEKS}주) 시 EOL")
    elif tier == TIER_EOL:
        reason = (f"Electron {pin} 은 최신 {latest} 대비 {lag} 뒤 — 지원 창"
                  f"({SUPPORT_WINDOW_MAJORS}) 밖, 보안 백포트 종료")
    else:  # TIER_AHEAD
        reason = f"핀 {pin} 이 알려진 최신 {latest} 보다 앞섬 — 스냅샷 stale/프리릴리스 의심"
    return LtsAssessment(action, tier, lag, (reason,))


# 정책 매트릭스: lag 대표값 → (tier, action). assess() 의 권위 있는 규칙을
# 사람이 한눈에 볼 수 있게 표로 투영한 것일 뿐, 결정은 항상 assess() 가 내린다
# (중복 로직 아님 — 테스트가 일치 강제). window=3 기준 대표 lag: -1·0·1·2·3·4.
POLICY_MATRIX: dict[int, tuple[str, str]] = {
    -1: (TIER_AHEAD, ACTION_REVIEW),
    0: (TIER_CURRENT, ACTION_WITHIN_SLA),
    1: (TIER_SUPPORTED, ACTION_WITHIN_SLA),
    2: (TIER_ENDING, ACTION_PLAN_UPGRADE),
    3: (TIER_EOL, ACTION_UPGRADE_NOW),
    4: (TIER_EOL, ACTION_UPGRADE_NOW),
}


def policy_manifest() -> dict[str, Any]:
    """정책을 JSON 직렬화 가능한 매니페스트로 굳힌다."""
    return {
        "schema": "sdacs-electron-lts-policy",
        "version": "1.0",
        "support_window_majors": SUPPORT_WINDOW_MAJORS,
        "release_cadence_weeks": RELEASE_CADENCE_WEEKS,
        "observed_latest_stable_major": OBSERVED_LATEST_STABLE_MAJOR,
        "observed_latest_as_of": OBSERVED_LATEST_AS_OF,
        "actions": [
            ACTION_WITHIN_SLA, ACTION_PLAN_UPGRADE, ACTION_UPGRADE_NOW, ACTION_REVIEW,
        ],
        "matrix": [
            {"lag": lag, "tier": tier, "action": action}
            for lag, (tier, action) in POLICY_MATRIX.items()
        ],
    }


def read_pinned_major(repo_root: str | Path) -> int | None:
    """``package.json`` 의 ``devDependencies.electron``(없으면 ``dependencies``)
    핀에서 major 를 읽는다. 파일/필드 부재·파싱 불가면 None."""
    pkg = Path(repo_root) / _PACKAGE_JSON
    if not pkg.is_file():
        return None
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    for section in ("devDependencies", "dependencies"):
        spec = data.get(section, {}).get("electron")
        if isinstance(spec, str):
            return parse_major(spec)
    return None


def shipped_runtime(repo_root: str | Path | None = None) -> ElectronRuntime | None:
    """리포의 *현 실제* Electron 핀을 스냅샷 최신과 짝지어 반환한다.

    ``package.json`` 핀을 읽지 못하면 None(정직성 — 핀을 추측하지 않음).
    핀을 최신으로 포장하지 않고 ``OBSERVED_LATEST_STABLE_MAJOR`` 스냅샷과
    있는 그대로 비교한다.
    """
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parent.parent
    pinned = read_pinned_major(root)
    if pinned is None:
        return None
    return ElectronRuntime(pinned, OBSERVED_LATEST_STABLE_MAJOR)


# 정책 동작을 보이는 결정적 예시(창 내부 → EOL 전 구간).
_DEMO_RUNTIMES: tuple[ElectronRuntime, ...] = (
    ElectronRuntime(43, 43),  # CURRENT (리포 현 핀)
    ElectronRuntime(42, 43),  # SUPPORTED
    ElectronRuntime(41, 43),  # ENDING
    ElectronRuntime(40, 43),  # EOL
    ElectronRuntime(32, 39),  # EOL (과거 32→39 표류 교훈)
)


def _cmd_policy() -> None:
    print(f"Electron LTS 추적 정책 (지원 창 = 최신 {SUPPORT_WINDOW_MAJORS} major)")
    print(f"{'LAG':<6}{'TIER':<12}ACTION")
    for lag, (tier, action) in POLICY_MATRIX.items():
        print(f"{lag:<6}{tier:<12}{action}")
    print(f"\n상류 캘린더 스냅샷: 최신 stable = {OBSERVED_LATEST_STABLE_MAJOR} "
          f"({OBSERVED_LATEST_AS_OF} 기준)")


def _cmd_status() -> None:
    runtime = shipped_runtime()
    if runtime is None:
        print("package.json 에서 electron 핀을 읽지 못했습니다.")
        return
    result = assess(runtime)
    print(f"리포 핀 Electron {runtime.pinned_major} · 상류 최신 "
          f"{runtime.latest_stable_major} ({OBSERVED_LATEST_AS_OF})")
    print(f"  → {result.summary()}")


def _cmd_demo() -> None:
    print("예시 평가:")
    for runtime in _DEMO_RUNTIMES:
        result = assess(runtime)
        print(f"  electron {runtime.pinned_major:>3} (최신 {runtime.latest_stable_major:>3})"
              f"  {result.summary()}")


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

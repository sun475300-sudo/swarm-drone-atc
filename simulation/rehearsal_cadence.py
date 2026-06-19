"""ODYSSEY Phase 486 — 연 1회 건전성 리허설 자동화 정책.

Continuum 트랙(Phase 481-500)의 한 칸. 졸업 후 10년, 손이 뜸해진 뒤에도
프로젝트가 *신규 컨테이너에서 그대로 재현되는가* 를 적어도 1년에 한 번은
독립적으로 검증해야 한다(``scripts/independent_reproduction.sh`` 가 그 리허설
하니스다). 본 모듈은 그 리허설이 *언제 다시 필요한가* 와 *하니스가 온전한가*
를 사람이 매번 직관으로 따지지 않도록 **결정적 정책**으로 명문화한다 —
같은 (마지막 리허설 기록, 기준일, 하니스 상태) 는 항상 같은 권고를 낸다.

설계 원칙
--------
- **정책은 코드, 코드는 정책**: 케이던스 규칙을 문서(``docs/standards/
  HEALTH_REHEARSAL_CADENCE_POLICY.md``)와 본 평가기에 *한 번씩만* 적기 위해
  본 모듈이 유일한 실행 가능 명세다. 문서는 규칙을 서술만 한다(테스트가
  ``POLICY_MATRIX`` ↔ ``assess`` 일치 강제).
- **자문이지 집행 아님**: 본 모듈은 *권고* 할 뿐 리허설을 실행하거나 빌드를
  막지 않는다(부수효과 0). 사람/CI 가 실제 ``independent_reproduction.sh`` 를
  돌린다.
- **하니스가 없으면 평가 불가**: 리허설 스크립트·재현 컨테이너·핀 락이
  하나라도 사라지면 케이던스 판정 이전에 REVIEW(하니스부터 복구).
- **녹색 기준선이 아니면 권고는 RUN_NOW**: 마지막 리허설이 통과(PASS)가
  아니었다면 시간이 얼마 지났든 다시 돌려 녹색 기준선을 세워야 한다.
- **정직한 스냅샷**: 마지막 실제 리허설은 리포에 기계가 읽을 로그가 없으므로
  *수동 스냅샷 상수*(``LAST_REHEARSAL_*``, 날짜 명시)로 둔다 — 일일 점검의
  독립 재현이 곧 리허설이며, 그 최신 실측을 있는 그대로 기록한다.

무작위성 0 · 결정적 · 기존 모듈 무수정 순수 추가.

CLI:
    python -m simulation.rehearsal_cadence --policy    # 케이던스 매트릭스
    python -m simulation.rehearsal_cadence --status    # 리포 현 상태 판정
    python -m simulation.rehearsal_cadence --demo      # 예시 평가
    python -m simulation.rehearsal_cadence --manifest  # 정책 매니페스트(JSON)
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

# 케이던스(상수). 연 1회 리허설 — 만기 전 30일 예고 창, 만기 후 30일 유예.
ANNUAL_INTERVAL_DAYS = 365
DUE_SOON_LEAD_DAYS = 30      # 만기 임박(예고) 창
OVERDUE_GRACE_DAYS = 30      # 만기 후 유예(이후 OVERDUE)

# 리허설 하니스(이것들이 온전해야 신규 컨테이너 재현이 가능하다). 경로는
# 리포 루트 기준 상대 경로이며 *모두* 실재해야 하니스 온전(INTACT)으로 본다.
REHEARSAL_HARNESS: tuple[str, ...] = (
    "scripts/independent_reproduction.sh",
    "Dockerfile.reproducible",
    "requirements.lock.txt",
    "docs/REPRODUCIBILITY.md",
)

# 마지막 *실제* 리허설의 정직한 스냅샷. 일일 점검(독립 재현)이 곧 리허설이며
# 그 최신 실측을 기록한다. 갱신 시 날짜·결과를 함께 고친다.
#   2026-06-19 — 신규 컨테이너에서 의존성 신규 설치 후 전체 회귀 GREEN
#   (Continuum 일원화 49차 독립 재현).
LAST_REHEARSAL_DATE = "2026-06-19"
LAST_REHEARSAL_RESULT = "PASS"

# 리허설 결과 어휘.
RESULT_PASS = "PASS"  # 녹색 기준선 확립
RESULT_FAIL = "FAIL"  # 재현 실패/회귀 — 기준선 미확립

# --- 케이던스 등급(시간 전용) ---------------------------------------------
TIER_NEVER_RUN = "NEVER_RUN"  # 기록 없음 — 기준선 미수립
TIER_CURRENT = "CURRENT"      # 만기 한참 전 — 여유
TIER_DUE_SOON = "DUE_SOON"    # 만기 임박(예고 창)
TIER_DUE = "DUE"              # 만기 도래(유예 내)
TIER_OVERDUE = "OVERDUE"      # 만기 + 유예 초과

# --- 권고 결정 -------------------------------------------------------------
ACTION_WITHIN_CADENCE = "WITHIN_CADENCE"  # 조치 불필요
ACTION_SCHEDULE = "SCHEDULE"              # 만기 전 리허설 일정 예약
ACTION_RUN_NOW = "RUN_NOW"                # 즉시 리허설 실행
ACTION_REVIEW = "REVIEW"                  # 평가 불가(하니스 손상/데이터 이상)

# 케이던스 등급 → 권고(시간 전용, 권위 있는 매핑). assess() 가 이 표를 쓴다.
# cadence_tier() 가 반환할 수 있는 4개 등급만 포함한다 — NEVER_RUN 은 시간에서
# 도출되지 않으며(경과 None) assess() 가 직접 처리하므로 이 표에 두지 않는다.
_TIER_ACTION: dict[str, str] = {
    TIER_CURRENT: ACTION_WITHIN_CADENCE,
    TIER_DUE_SOON: ACTION_SCHEDULE,
    TIER_DUE: ACTION_RUN_NOW,
    TIER_OVERDUE: ACTION_RUN_NOW,
}


def cadence_tier(days_since: int) -> str:
    """마지막 리허설로부터 경과 일수로 케이던스 등급을 결정적으로 분류한다.

    음수(미래 날짜)는 호출 전에 걸러야 한다 — 본 함수는 ``days_since >= 0``
    만 다룬다(데이터 이상은 ``assess`` 가 REVIEW 로 처리). 계약을 명시적으로
    강제해 잘못된 음수 입력이 조용히 CURRENT 로 새지 않게 한다.
    """
    if days_since < 0:
        raise ValueError(f"cadence_tier 는 days_since >= 0 만 받습니다(받은 값 {days_since})")
    if days_since < ANNUAL_INTERVAL_DAYS - DUE_SOON_LEAD_DAYS:
        return TIER_CURRENT
    if days_since < ANNUAL_INTERVAL_DAYS:
        return TIER_DUE_SOON
    if days_since < ANNUAL_INTERVAL_DAYS + OVERDUE_GRACE_DAYS:
        return TIER_DUE
    return TIER_OVERDUE


@dataclass(frozen=True)
class RehearsalRecord:
    """마지막 건전성 리허설 기록(불변).

    Attributes:
        last_run: 마지막 리허설 실행일. 한 번도 없으면 None.
        result: ``PASS``(녹색 기준선) 또는 그 외(실패 — 기준선 미확립).
    """

    last_run: date | None
    result: str = RESULT_PASS

    def is_passing(self) -> bool:
        """마지막 리허설이 녹색 기준선을 세웠는가."""
        return self.result == RESULT_PASS


def days_since(record: RehearsalRecord, today: date) -> int | None:
    """기준일까지 경과 일수. 기록이 없으면 None(음수면 미래 — 데이터 이상)."""
    if record.last_run is None:
        return None
    return (today - record.last_run).days


@dataclass(frozen=True)
class CadenceAssessment:
    """평가 결과(불변). 권고와 그 근거."""

    action: str
    tier: str
    days_since: int | None
    harness_intact: bool
    reasons: tuple[str, ...]

    def summary(self) -> str:
        """사람이 읽는 한 줄 요약."""
        elapsed = "없음" if self.days_since is None else f"{self.days_since}일"
        return f"{self.action} ({self.tier}, 경과={elapsed}): {'; '.join(self.reasons)}"


def assess(
    record: RehearsalRecord,
    today: date,
    harness_intact: bool,
) -> CadenceAssessment:
    """리허설 기록·기준일·하니스 상태로 권고를 결정적으로 산출한다.

    우선순위(위에서부터 단락):
        1. 하니스 손상 → REVIEW (재현 불가 — 케이던스보다 하니스 복구 먼저).
        2. 기록 없음(경과 None) → RUN_NOW (녹색 기준선 미수립 — 미래 날짜와 구분).
        3. 미래 날짜(경과 음수) → REVIEW (시계/데이터 이상).
        4. 마지막 리허설이 PASS 아님 → RUN_NOW (녹색 기준선 미확립).
        5. 그 외 → 케이던스 등급에 따른 시간 전용 권고(``_TIER_ACTION``).
    """
    elapsed = days_since(record, today)

    if not harness_intact:
        # 하니스 손상 → action 은 항상 REVIEW; tier 는 참고용 분류일 뿐이다.
        # 경과 음수(미래 날짜)는 max(..., 0) 으로 CURRENT 에 클램프한다(이 경로에선
        # 의미 있는 시간 분류가 불가하며 action 이 이미 REVIEW 라 무해).
        tier = TIER_NEVER_RUN if elapsed is None else cadence_tier(max(elapsed, 0))
        return CadenceAssessment(
            ACTION_REVIEW, tier, elapsed, False,
            ("리허설 하니스 손상 — 케이던스 이전에 재현 스크립트/락/컨테이너 복구 필요",),
        )

    if elapsed is None:
        return CadenceAssessment(
            ACTION_RUN_NOW, TIER_NEVER_RUN, None, True,
            ("리허설 기록 없음 — 녹색 재현 기준선 미수립",),
        )

    if elapsed < 0:
        return CadenceAssessment(
            ACTION_REVIEW, TIER_CURRENT, elapsed, True,
            (f"마지막 리허설일이 기준일보다 미래({elapsed}일) — 시계/데이터 이상",),
        )

    tier = cadence_tier(elapsed)

    if not record.is_passing():
        return CadenceAssessment(
            ACTION_RUN_NOW, tier, elapsed, True,
            (f"마지막 리허설 결과 {record.result} — 녹색 기준선 미확립, 즉시 재실행",),
        )

    action = _TIER_ACTION[tier]
    if tier == TIER_CURRENT:
        reason = f"{elapsed}일 경과 — 연 1회({ANNUAL_INTERVAL_DAYS}일) 케이던스 내부"
    elif tier == TIER_DUE_SOON:
        reason = (f"{elapsed}일 경과 — 만기({ANNUAL_INTERVAL_DAYS}일) "
                  f"임박(예고 {DUE_SOON_LEAD_DAYS}일), 리허설 일정 예약")
    elif tier == TIER_DUE:
        reason = f"{elapsed}일 경과 — 만기 도래(유예 {OVERDUE_GRACE_DAYS}일 내), 리허설 실행"
    else:  # TIER_OVERDUE
        reason = (f"{elapsed}일 경과 — 만기 + 유예({OVERDUE_GRACE_DAYS}일) 초과, "
                  f"즉시 리허설 실행")
    return CadenceAssessment(action, tier, elapsed, True, (reason,))


# 정책 매트릭스: 대표 경과 일수 → (tier, action). PASS + 하니스 온전 가정의
# 시간 전용 투영이며, 결정은 항상 assess() 가 내린다(중복 로직 아님 — 테스트가
# 일치 강제). 경계: 334/335(예고 진입)·364/365(만기)·394/395(유예 초과).
POLICY_MATRIX: dict[int, tuple[str, str]] = {
    0: (TIER_CURRENT, ACTION_WITHIN_CADENCE),
    334: (TIER_CURRENT, ACTION_WITHIN_CADENCE),
    335: (TIER_DUE_SOON, ACTION_SCHEDULE),
    364: (TIER_DUE_SOON, ACTION_SCHEDULE),
    365: (TIER_DUE, ACTION_RUN_NOW),
    394: (TIER_DUE, ACTION_RUN_NOW),
    395: (TIER_OVERDUE, ACTION_RUN_NOW),
    1000: (TIER_OVERDUE, ACTION_RUN_NOW),
}


def policy_manifest() -> dict[str, Any]:
    """정책을 JSON 직렬화 가능한 매니페스트로 굳힌다."""
    return {
        "schema": "sdacs-health-rehearsal-cadence-policy",
        "version": "1.0",
        "annual_interval_days": ANNUAL_INTERVAL_DAYS,
        "due_soon_lead_days": DUE_SOON_LEAD_DAYS,
        "overdue_grace_days": OVERDUE_GRACE_DAYS,
        "harness": list(REHEARSAL_HARNESS),
        "actions": [
            ACTION_WITHIN_CADENCE, ACTION_SCHEDULE, ACTION_RUN_NOW, ACTION_REVIEW,
        ],
        "matrix": [
            {"days_since": days, "tier": tier, "action": action}
            for days, (tier, action) in POLICY_MATRIX.items()
        ],
    }


def harness_intact(repo_root: str | Path) -> bool:
    """리허설 하니스 자산이 모두 디스크에 실재하는지 결정적으로 확인한다."""
    root = Path(repo_root)
    return all((root / rel).is_file() for rel in REHEARSAL_HARNESS)


def _parse_iso(value: str) -> date:
    """``YYYY-MM-DD`` 를 date 로 파싱한다(스냅샷 상수 전용)."""
    return date.fromisoformat(value)


def shipped_record() -> RehearsalRecord:
    """리포의 *현 실제* 마지막 리허설 기록(정직한 스냅샷)을 반환한다.

    일일 점검의 독립 재현이 곧 리허설이며, ``LAST_REHEARSAL_*`` 스냅샷을
    있는 그대로 반영한다 — 케이던스를 최신으로 포장하지 않는다.
    """
    return RehearsalRecord(_parse_iso(LAST_REHEARSAL_DATE), LAST_REHEARSAL_RESULT)


def _repo_root() -> Path:
    """리포 루트(이 파일의 부모의 부모)."""
    return Path(__file__).resolve().parent.parent


# 정책 동작을 보이는 결정적 예시(케이던스 전 구간 + 실패/하니스 손상).
_DEMO_BASE = date(2026, 1, 1)
_DEMO_CASES: tuple[tuple[str, RehearsalRecord, date, bool], ...] = (
    ("막 실행", RehearsalRecord(date(2026, 1, 1)), _DEMO_BASE, True),
    ("만기 임박", RehearsalRecord(date(2025, 1, 20)), _DEMO_BASE, True),
    ("만기 도래", RehearsalRecord(date(2024, 12, 25)), _DEMO_BASE, True),
    ("만기 초과", RehearsalRecord(date(2024, 1, 1)), _DEMO_BASE, True),
    ("기록 없음", RehearsalRecord(None), _DEMO_BASE, True),
    ("실패 기준선", RehearsalRecord(date(2025, 12, 31), RESULT_FAIL), _DEMO_BASE, True),
    ("하니스 손상", RehearsalRecord(date(2025, 12, 31)), _DEMO_BASE, False),
)


def _cmd_policy() -> None:
    print(f"건전성 리허설 케이던스 정책 (연 1회 = {ANNUAL_INTERVAL_DAYS}일, "
          f"예고 {DUE_SOON_LEAD_DAYS}일, 유예 {OVERDUE_GRACE_DAYS}일)")
    print(f"{'DAYS':<8}{'TIER':<12}ACTION")
    for days, (tier, action) in POLICY_MATRIX.items():
        print(f"{days:<8}{tier:<12}{action}")
    print(f"\n하니스: {', '.join(REHEARSAL_HARNESS)}")


def _cmd_status() -> None:
    root = _repo_root()
    record = shipped_record()
    intact = harness_intact(root)
    today = date.today()
    result = assess(record, today, intact)
    last = "없음" if record.last_run is None else record.last_run.isoformat()
    print(f"마지막 리허설 {last} ({record.result}) · 하니스 "
          f"{'온전' if intact else '손상'} · 기준일 {today.isoformat()}")
    print(f"  → {result.summary()}")


def _cmd_demo() -> None:
    print("예시 평가:")
    for label, record, today, intact in _DEMO_CASES:
        result = assess(record, today, intact)
        print(f"  {label:<10} {result.summary()}")


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

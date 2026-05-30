"""5단계 페일세이프 체인 (RTL/지오펜스) 관리 모듈."""

from __future__ import annotations

from enum import IntEnum


class FailsafeLevel(IntEnum):
    """페일세이프 단계 (낮을수록 정상)."""
    NORMAL      = 0
    LOW_BATTERY = 1
    SIGNAL_LOST = 2
    GEOFENCE    = 3
    CRITICAL    = 4


# 배터리 임계값 (%)
_LOW_BATTERY_THRESHOLD  = 20.0
_CRITICAL_BATTERY_THRESHOLD = 5.0

# 단계별 액션 매핑
_LEVEL_ACTIONS: dict[FailsafeLevel, str] = {
    FailsafeLevel.NORMAL:      "hover",
    FailsafeLevel.LOW_BATTERY: "rtl",
    FailsafeLevel.SIGNAL_LOST: "rtl",
    FailsafeLevel.GEOFENCE:    "rtl",
    FailsafeLevel.CRITICAL:    "land",
}


class FailsafeManager:
    """드론 상태를 기반으로 페일세이프 수준을 평가하고 액션을 결정한다.

    우선순위 (높음 → 낮음):
      CRITICAL > GEOFENCE > SIGNAL_LOST > LOW_BATTERY > NORMAL
    """

    def evaluate(
        self,
        battery_pct: float,
        signal_ok: bool,
        in_geofence: bool,
    ) -> FailsafeLevel:
        """현재 드론 상태로부터 페일세이프 수준을 평가한다.

        Args:
            battery_pct: 배터리 잔량 (0~100 %).
            signal_ok: RC/텔레메트리 신호 정상 여부.
            in_geofence: 드론이 지오펜스 내부에 있는지 여부.

        Returns:
            현재 FailsafeLevel.
        """
        # 가장 심각한 조건부터 평가 (최고 우선순위)
        if battery_pct < _CRITICAL_BATTERY_THRESHOLD:
            return FailsafeLevel.CRITICAL

        if not in_geofence:
            return FailsafeLevel.GEOFENCE

        if not signal_ok:
            return FailsafeLevel.SIGNAL_LOST

        if battery_pct < _LOW_BATTERY_THRESHOLD:
            return FailsafeLevel.LOW_BATTERY

        return FailsafeLevel.NORMAL

    def get_action(self, level: FailsafeLevel) -> str:
        """페일세이프 수준에 대응하는 액션 문자열을 반환한다.

        Args:
            level: FailsafeLevel 열거값.

        Returns:
            액션 문자열: "hover" | "rtl" | "land".
        """
        return _LEVEL_ACTIONS[level]

    def evaluate_and_act(
        self,
        battery_pct: float,
        signal_ok: bool,
        in_geofence: bool,
    ) -> tuple[FailsafeLevel, str]:
        """평가 + 액션을 한번에 반환하는 편의 메서드.

        Returns:
            (FailsafeLevel, action_str) 튜플.
        """
        level = self.evaluate(battery_pct, signal_ok, in_geofence)
        action = self.get_action(level)
        return level, action

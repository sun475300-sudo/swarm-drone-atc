"""TRANSCENDENCE Phase 230 — LiPo 방전 곡선 + 사이클 노화 결정적 모델.

기존 시뮬의 배터리는 선형 % 소모(`_estimate_power_w` 기반)다. 본 모듈은
공개 문헌의 LiPo 특성(비선형 전압-SoC 곡선·사이클 용량 감퇴)을 결정적으로
모델링해 (1) SoC→셀 전압 (2) 사이클 수→가용 용량 보정을 제공한다.

정직성 공시:
- 계수는 *실측 캘리브레이션이 아닌* 공개 문헌 대표값 (LiPo 1S 공칭 3.7V,
  만충 4.2V, 방전종지 3.3V, 80% 용량 도달 ≈ 300-500 사이클).
- 실 팩 캘리브레이션(Track A HW) 전까지는 *상대 비교·시나리오 민감도* 용도.
- 무작위성 0 — 동일 입력 → 동일 출력.

방전 곡선: 구간별 선형(테이블 보간) — LiPo 의 전형적 평탄 구간(3.7-3.8V,
SoC 20-80%)과 양끝 급락/급증을 8점 테이블로 근사.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["LipoAgingModel", "LipoCell", "soc_to_voltage"]

# LiPo 1S 방전 곡선 8점 테이블 (SoC 0~1 → V) — 문헌 대표 형상
_SOC_V_TABLE: tuple[tuple[float, float], ...] = (
    (0.00, 3.30),
    (0.05, 3.50),
    (0.10, 3.60),
    (0.20, 3.70),
    (0.50, 3.78),
    (0.80, 3.95),
    (0.95, 4.10),
    (1.00, 4.20),
)

# 사이클 노화: 300 사이클에 90%, 500 사이클에 80% 용량 (선형 구간 근사)
_CYCLE_CAP_TABLE: tuple[tuple[float, float], ...] = (
    (0.0, 1.00),
    (100.0, 0.97),
    (300.0, 0.90),
    (500.0, 0.80),
    (800.0, 0.65),
)


def _interp(table: tuple[tuple[float, float], ...], x: float) -> float:
    """구간별 선형 보간 — 범위 밖은 경계값 클램프 (결정적)."""
    if x <= table[0][0]:
        return table[0][1]
    if x >= table[-1][0]:
        return table[-1][1]
    for (x0, y0), (x1, y1) in zip(table, table[1:], strict=False):
        if x0 <= x <= x1:
            f = (x - x0) / (x1 - x0)
            return y0 + f * (y1 - y0)
    return table[-1][1]  # 도달 불가 (방어)


def soc_to_voltage(soc: float) -> float:
    """SoC(0~1) → 1S 셀 전압(V). 범위 밖 클램프."""
    return round(_interp(_SOC_V_TABLE, max(0.0, min(1.0, soc))), 4)


@dataclass(frozen=True)
class LipoCell:
    """LiPo 팩 사양 (frozen)."""

    cells_series: int = 4  # 4S 기본 (기존 DRONE_PROFILES 급 상용기 대표)
    capacity_wh_new: float = 80.0  # 신품 용량 — drone_profiles.battery_wh 정렬
    cycles: float = 0.0  # 누적 충방전 사이클


class LipoAgingModel:
    """방전 곡선 + 사이클 노화 결정적 모델."""

    def __init__(self, cell: LipoCell) -> None:
        if cell.cells_series < 1:
            raise ValueError("cells_series >= 1")
        if cell.capacity_wh_new <= 0:
            raise ValueError("capacity_wh_new > 0")
        if cell.cycles < 0:
            raise ValueError("cycles >= 0")
        self.cell = cell

    def capacity_factor(self) -> float:
        """사이클 노화 보정 계수 (0~1] — 300cyc≈0.90, 500cyc≈0.80."""
        return round(_interp(_CYCLE_CAP_TABLE, self.cell.cycles), 4)

    def effective_capacity_wh(self) -> float:
        """노화 반영 가용 용량 (Wh)."""
        return round(self.cell.capacity_wh_new * self.capacity_factor(), 4)

    def pack_voltage(self, soc: float) -> float:
        """SoC → 팩 전압 (셀 직렬 수 반영)."""
        return round(soc_to_voltage(soc) * self.cell.cells_series, 4)

    def endurance_scale(self) -> float:
        """기존 선형 모델의 endurance_min 에 곱할 노화 배율.

        시뮬 통합: `profile.endurance_min * model.endurance_scale()` —
        기존 `_estimate_power_w` 경로 무수정 (수술적).
        """
        return self.capacity_factor()

    def low_voltage_cutoff_soc(self, cutoff_v_per_cell: float = 3.5) -> float:
        """전압 컷오프에 대응하는 SoC — 실 기체는 잔량 % 가 아니라 전압으로
        강하하므로, 컷오프 전압 도달 SoC 를 이진 탐색(결정적)으로 산출."""
        lo, hi = 0.0, 1.0
        for _ in range(40):  # 2^-40 정밀 — 충분·결정적
            mid = (lo + hi) / 2
            if soc_to_voltage(mid) < cutoff_v_per_cell:
                lo = mid
            else:
                hi = mid
        return round(hi, 6)

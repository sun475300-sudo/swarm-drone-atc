"""TRANSCENDENCE Phase 227 — KMA(기상청) 풍속장 격자 파서 + 시뮬 통합 어댑터.

기상청 단기예보(초단기실황) 격자 API 의 응답(JSON items)을 **결정적으로 파싱**해
1km 격자 풍속장(`KmaWindField`)으로 변환하고, 시뮬레이터의 wind 모델 인터페이스
(`get_wind_vector(position, t)`) 와 호환되는 어댑터를 제공한다.

정직성 공시:
- 실 KMA API 호출은 서비스 키(공공데이터포털) 가 필요한 *외부 의존* — 본 모듈은
  네트워크를 호출하지 않는다. 가치는 (1) 응답 스키마의 결정적 파서
  (2) 격자→연속 좌표 이중선형 보간 (3) 시뮬 wind 인터페이스 어댑터.
- `SAMPLE_KMA_RESPONSE` 는 KMA 응답 *형식* 의 캐시 표본이며 실 관측값이 아니다.

KMA 초단기실황 카테고리 (사용분):
- UUU: 동서바람성분 (m/s, 동+)
- VVV: 남북바람성분 (m/s, 북+)
- WSD: 풍속 (m/s) — UUU/VVV 없을 때 폴백 (풍향 VEC 와 조합)
- VEC: 풍향 (deg, 북 0 시계방향)
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass

import numpy as np

__all__ = [
    "KmaGridPoint",
    "KmaWindField",
    "SAMPLE_KMA_RESPONSE",
    "kma_wind_adapter",
    "parse_kma_items",
]

GRID_SPACING_M = 1000.0  # KMA 국지예보 격자 1km


@dataclass(frozen=True)
class KmaGridPoint:
    """격자 1점의 바람 (nx, ny 는 KMA 격자 인덱스)."""

    nx: int
    ny: int
    u_ms: float  # 동서 성분 (동+)
    v_ms: float  # 남북 성분 (북+)


def _wind_from_speed_dir(wsd: float, vec_deg: float) -> tuple[float, float]:
    """풍속+풍향(불어오는 방향, 북 0 시계) → (u, v) 성분.

    기상 관례: VEC 는 바람이 *불어오는* 방향. 성분은 공기가 *가는* 방향이므로
    u = -WSD·sin(VEC), v = -WSD·cos(VEC).
    """
    rad = math.radians(vec_deg)
    return (-wsd * math.sin(rad), -wsd * math.cos(rad))


def parse_kma_items(items: list[dict]) -> list[KmaGridPoint]:
    """KMA 초단기실황 items 배열 → 격자점 리스트 (결정적).

    - UUU/VVV 쌍이 있으면 그대로 사용 (우선).
    - 없고 WSD+VEC 만 있으면 성분으로 변환.
    - 값이 결측 표기(-999 이하) 또는 비수치면 해당 격자점 폐기 (silent NaN 금지).
    """
    by_cell: dict[tuple[int, int], dict[str, float]] = {}
    for it in items:
        try:
            nx, ny = int(it["nx"]), int(it["ny"])
            cat = str(it["category"])
            val = float(it["obsrValue"])
        except (KeyError, TypeError, ValueError):
            continue  # 형식 위반 항목은 폐기 — 파서는 관용, 결과는 검증됨
        if not math.isfinite(val) or val <= -900.0:  # KMA 결측 코드(-999 류)
            continue
        by_cell.setdefault((nx, ny), {})[cat] = val

    points: list[KmaGridPoint] = []
    for (nx, ny) in sorted(by_cell):  # 정렬 — 결정적 순서
        c = by_cell[(nx, ny)]
        if "UUU" in c and "VVV" in c:
            u, v = c["UUU"], c["VVV"]
        elif "WSD" in c and "VEC" in c:
            u, v = _wind_from_speed_dir(c["WSD"], c["VEC"])
        else:
            continue  # 바람 성분 불충분 격자 폐기
        points.append(KmaGridPoint(nx=nx, ny=ny, u_ms=u, v_ms=v))
    return points


class KmaWindField:
    """1km 격자 풍속장 — 이중선형 보간으로 연속 좌표 질의.

    시뮬 좌표(m)는 origin 격자(nx0, ny0)의 남서 모서리를 (0,0) 으로 둔다.
    """

    def __init__(self, points: list[KmaGridPoint]) -> None:
        if not points:
            raise ValueError("빈 풍속장 — 최소 1 격자점 필요")
        self._cells: dict[tuple[int, int], KmaGridPoint] = {
            (p.nx, p.ny): p for p in points
        }
        self.nx0 = min(p.nx for p in points)
        self.ny0 = min(p.ny for p in points)

    @property
    def cell_count(self) -> int:
        return len(self._cells)

    def _cell(self, nx: int, ny: int) -> KmaGridPoint | None:
        return self._cells.get((nx, ny))

    def wind_at(self, x_m: float, y_m: float) -> tuple[float, float]:
        """연속 좌표(m) 의 (u, v) — 이중선형 보간, 결측 이웃은 최근접 폴백."""
        gx = self.nx0 + x_m / GRID_SPACING_M
        gy = self.ny0 + y_m / GRID_SPACING_M
        x0, y0 = int(math.floor(gx)), int(math.floor(gy))
        fx, fy = gx - x0, gy - y0

        corners = [
            (self._cell(x0, y0), (1 - fx) * (1 - fy)),
            (self._cell(x0 + 1, y0), fx * (1 - fy)),
            (self._cell(x0, y0 + 1), (1 - fx) * fy),
            (self._cell(x0 + 1, y0 + 1), fx * fy),
        ]
        present = [(p, w) for p, w in corners if p is not None]
        if not present:
            # 전 모서리 결측 → 최근접 격자점 폴백 (거리 → 인덱스 사전순 결정적)
            nearest = min(
                self._cells.values(),
                key=lambda p: ((p.nx - gx) ** 2 + (p.ny - gy) ** 2, p.nx, p.ny),
            )
            return (nearest.u_ms, nearest.v_ms)
        wsum = sum(w for _, w in present)
        if wsum <= 0.0:
            p = present[0][0]
            return (p.u_ms, p.v_ms)
        u = sum(p.u_ms * w for p, w in present) / wsum
        v = sum(p.v_ms * w for p, w in present) / wsum
        return (u, v)


def kma_wind_adapter(field: KmaWindField):
    """시뮬 wind 모델 인터페이스 어댑터.

    반환 객체는 `get_wind_vector(position, t) -> np.ndarray[3]` 를 제공 —
    `SwarmSimulator.wind_models` 리스트에 그대로 추가 가능. z 성분은 0
    (KMA 지상 관측은 연직 성분 미제공 — 정직 공시).
    """

    class _Adapter:
        def get_wind_vector(self, position, t: float) -> np.ndarray:  # noqa: ARG002
            pos = np.asarray(position, dtype=float)
            x = float(pos[0]) if pos.size >= 1 else 0.0
            y = float(pos[1]) if pos.size >= 2 else 0.0
            u, v = field.wind_at(x, y)
            return np.array([u, v, 0.0])

    return _Adapter()


# KMA 초단기실황 응답 *형식* 표본 (2×2 격자, UUU/VVV 완비 + 1셀 WSD/VEC 폴백 케이스)
SAMPLE_KMA_RESPONSE = json.dumps({
    "response": {"body": {"items": {"item": [
        {"nx": 58, "ny": 74, "category": "UUU", "obsrValue": "2.0"},
        {"nx": 58, "ny": 74, "category": "VVV", "obsrValue": "1.0"},
        {"nx": 59, "ny": 74, "category": "UUU", "obsrValue": "4.0"},
        {"nx": 59, "ny": 74, "category": "VVV", "obsrValue": "1.0"},
        {"nx": 58, "ny": 75, "category": "UUU", "obsrValue": "2.0"},
        {"nx": 58, "ny": 75, "category": "VVV", "obsrValue": "3.0"},
        {"nx": 59, "ny": 75, "category": "WSD", "obsrValue": "5.0"},
        {"nx": 59, "ny": 75, "category": "VEC", "obsrValue": "270"},
        {"nx": 60, "ny": 74, "category": "UUU", "obsrValue": "-999"},
    ]}}},
})


def load_sample_field() -> KmaWindField:
    """캐시 표본 → 풍속장 (테스트·데모용)."""
    data = json.loads(SAMPLE_KMA_RESPONSE)
    items = data["response"]["body"]["items"]["item"]
    return KmaWindField(parse_kma_items(items))

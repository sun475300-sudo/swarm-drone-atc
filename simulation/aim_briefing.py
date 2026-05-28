"""Phase 699: 통합 AIM(Aeronautical Information Management) 브리핑 서비스."""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from typing import Any

# 브리핑 파라미터 기본값 상수 — 하드코딩 방지
_NOTAM_QUERY_RADIUS_M: float = 500.0
_CHART_CORRIDOR_WIDTH_M: float = 300.0
_HIGH_WIND_THRESHOLD_KT: int = 25


@dataclass
class BriefingRequest:
    callsign: str
    departure: tuple[float, float]
    destination: tuple[float, float]
    route_waypoints: list[tuple[float, float]]
    planned_altitude_m: float
    departure_time: float


@dataclass
class BriefingResult:
    callsign: str
    go_nogo: str
    weather_ok: bool
    notam_conflicts: list[str] = field(default_factory=list)
    tfr_conflicts: list[str] = field(default_factory=list)
    chart_hazards: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: str = ""


_DEFAULT_BRIEFING_HISTORY = 5_000


class AimBriefingService:
    """METAR + NOTAM + TFR + 항공차트를 통합해 운영자 브리핑을 생성한다."""

    def __init__(
        self,
        notam_manager: Any | None = None,
        tfr_handler: Any | None = None,
        aero_charts: Any | None = None,
        metar_parser: Any | None = None,
        max_history: int = _DEFAULT_BRIEFING_HISTORY,
    ) -> None:
        if max_history <= 0:
            raise ValueError("max_history must be positive")
        self.notam_manager = notam_manager
        self.tfr_handler = tfr_handler
        self.aero_charts = aero_charts
        self.metar_parser = metar_parser
        self.max_history = max_history
        self.history: list[BriefingResult] = []

    def generate(
        self, request: BriefingRequest, metar_text: str | None = None
    ) -> BriefingResult:
        """Generate a GO/NO-GO briefing.

        If metar_text is None or metar_parser is not configured, weather assessment
        is SKIPPED and weather_ok defaults to True (fail-open). Check result.warnings
        for a 'weather assessment skipped' entry to detect this case.
        """
        if not math.isfinite(request.planned_altitude_m) or request.planned_altitude_m < 0:
            raise ValueError(
                f"planned_altitude_m must be a finite non-negative number, "
                f"got {request.planned_altitude_m}"
            )
        if not math.isfinite(request.departure_time) or request.departure_time < 0:
            raise ValueError(
                f"departure_time must be a finite non-negative number, "
                f"got {request.departure_time}"
            )
        for label, coord in (("departure", request.departure), ("destination", request.destination)):
            if len(coord) != 2 or not (math.isfinite(coord[0]) and math.isfinite(coord[1])):
                raise ValueError(
                    f"{label} must be a 2-element tuple of finite floats, got {coord!r}"
                )
        warnings: list[str] = []
        # route 목록을 1회만 생성해 각 수집 메서드에 전달 (DRY + 성능)
        route = [request.departure, *request.route_waypoints, request.destination]
        notam_ids = self._collect_notam_conflicts(request, route)
        tfr_ids = self._collect_tfr_conflicts(request, route)
        hazard_ids = self._collect_chart_hazards(request, route)
        weather_ok = self._assess_weather(metar_text, warnings)

        # chart_hazards도 NO-GO 조건에 포함 — 안전 로직 수정
        is_go = (
            weather_ok
            and not tfr_ids
            and not notam_ids
            and not hazard_ids
        )
        if hazard_ids:
            warnings.append(f"{len(hazard_ids)} obstacle(s) within corridor")

        result = BriefingResult(
            callsign=request.callsign,
            go_nogo="GO" if is_go else "NO-GO",
            weather_ok=weather_ok,
            notam_conflicts=notam_ids,
            tfr_conflicts=tfr_ids,
            chart_hazards=hazard_ids,
            warnings=warnings,
            summary=self._summarize(is_go, notam_ids, tfr_ids, hazard_ids, weather_ok),
        )
        # 심층 복사본을 이력에 저장 — 호출자가 반환된 result를 수정해도 이력이 오염되지 않음
        self.history.append(copy.deepcopy(result))
        overflow = len(self.history) - self.max_history
        if overflow > 0:
            del self.history[:overflow]
        return result

    def _collect_notam_conflicts(self, request: BriefingRequest, route: list[tuple[float, float]]) -> list[str]:
        if self.notam_manager is None:
            return []
        import logging
        seen: set[str] = set()
        ids: list[str] = []
        for wp in route:
            try:
                active = self.notam_manager.query_active(
                    area_center=wp, radius_m=_NOTAM_QUERY_RADIUS_M, altitude=request.planned_altitude_m
                )
            except Exception as exc:
                # Fail-safe: treat query failure as unknown conflict (conservative NO-GO)
                logging.warning("NOTAM query failed for waypoint %s: %s", wp, exc)
                ids.append("NOTAM-QUERY-ERROR")
                break
            for n in active:
                if n.notam_id not in seen:
                    seen.add(n.notam_id)
                    ids.append(n.notam_id)
        return ids

    def _collect_tfr_conflicts(self, request: BriefingRequest, route: list[tuple[float, float]]) -> list[str]:
        if self.tfr_handler is None:
            return []
        import logging
        # check_conflict_readonly() 사용 — 감사 로그 오염 방지
        seen: set[str] = set()
        ids: list[str] = []
        for wp in route:
            pos3 = (wp[0], wp[1], request.planned_altitude_m)
            try:
                conflicts = self.tfr_handler.check_conflict_readonly(request.callsign, pos3)
            except Exception as exc:
                # Fail-safe: treat query failure as unknown conflict (conservative NO-GO)
                logging.warning("TFR query failed for waypoint %s: %s", wp, exc)
                ids.append("TFR-QUERY-ERROR")
                break
            for v in conflicts:
                if v not in seen:
                    seen.add(v)
                    ids.append(v)
        return ids

    def _collect_chart_hazards(self, request: BriefingRequest, route: list[tuple[float, float]]) -> list[str]:
        if self.aero_charts is None:
            return []
        hazards = self.aero_charts.path_obstacles(
            waypoints=route, corridor_width_m=_CHART_CORRIDOR_WIDTH_M, min_altitude_m=0.0
        )
        return [h.feature_id for h in hazards]

    def _assess_weather(self, metar_text: str | None, warnings: list[str]) -> bool:
        """Assess weather from METAR text.

        Returns True (weather assumed OK / fail-open) when metar_text is None or
        metar_parser is not configured — callers must be aware of this assumption.
        Returns False (NO-GO) if METAR parsing fails or conditions are IFR.
        """
        if metar_text is None or self.metar_parser is None:
            warnings.append("weather assessment skipped (no METAR/parser available)")
            return True
        try:
            obs = self.metar_parser.parse_metar(metar_text)
        except ValueError as exc:
            # 기상 데이터 파싱 실패 → 안전 방향(fail-closed)으로 NO-GO 처리
            warnings.append(f"METAR parse failed (weather unknown): {exc}")
            return False
        if obs.wind_speed_kt >= _HIGH_WIND_THRESHOLD_KT:
            warnings.append(f"High winds {obs.wind_speed_kt} kt")
        if not self.metar_parser.is_vfr(obs):
            warnings.append("IFR conditions")
            return False
        return True

    @staticmethod
    def _summarize(
        is_go: bool,
        notams: list[str],
        tfrs: list[str],
        hazards: list[str],
        weather_ok: bool,
    ) -> str:
        verdict = "GO" if is_go else "NO-GO"
        return (
            f"{verdict}: {len(notams)} NOTAM, {len(tfrs)} TFR, "
            f"{len(hazards)} hazard; weather={'ok' if weather_ok else 'bad'}"
        )

    def stats(self) -> dict[str, Any]:
        go = sum(1 for r in self.history if r.go_nogo == "GO")
        nogo = len(self.history) - go
        return {"briefings": len(self.history), "go": go, "nogo": nogo}

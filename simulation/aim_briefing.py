"""Phase 699: 통합 AIM(Aeronautical Information Management) 브리핑 서비스."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class BriefingRequest:
    callsign: str
    departure: Tuple[float, float]
    destination: Tuple[float, float]
    route_waypoints: List[Tuple[float, float]]
    planned_altitude_m: float
    departure_time: float


@dataclass
class BriefingResult:
    callsign: str
    go_nogo: str
    weather_ok: bool
    notam_conflicts: List[str] = field(default_factory=list)
    tfr_conflicts: List[str] = field(default_factory=list)
    chart_hazards: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    summary: str = ""


_DEFAULT_BRIEFING_HISTORY = 5_000


class AimBriefingService:
    """METAR + NOTAM + TFR + 항공차트를 통합해 운영자 브리핑을 생성한다."""

    def __init__(
        self,
        notam_manager: Optional[Any] = None,
        tfr_handler: Optional[Any] = None,
        aero_charts: Optional[Any] = None,
        metar_parser: Optional[Any] = None,
        max_history: int = _DEFAULT_BRIEFING_HISTORY,
    ) -> None:
        if max_history <= 0:
            raise ValueError("max_history must be positive")
        self.notam_manager = notam_manager
        self.tfr_handler = tfr_handler
        self.aero_charts = aero_charts
        self.metar_parser = metar_parser
        self.max_history = max_history
        self.history: List[BriefingResult] = []

    def generate(
        self, request: BriefingRequest, metar_text: Optional[str] = None
    ) -> BriefingResult:
        warnings: List[str] = []
        notam_ids = self._collect_notam_conflicts(request)
        tfr_ids = self._collect_tfr_conflicts(request)
        hazard_ids = self._collect_chart_hazards(request)
        weather_ok = self._assess_weather(metar_text, warnings)

        is_go = (
            weather_ok
            and not tfr_ids
            and len(notam_ids) == 0
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
        self.history.append(result)
        overflow = len(self.history) - self.max_history
        if overflow > 0:
            del self.history[:overflow]
        return result

    def _collect_notam_conflicts(self, request: BriefingRequest) -> List[str]:
        if self.notam_manager is None:
            return []
        ids: List[str] = []
        route = [request.departure] + list(request.route_waypoints) + [request.destination]
        for wp in route:
            active = self.notam_manager.query_active(
                area_center=wp, radius_m=500.0, altitude=request.planned_altitude_m
            )
            for n in active:
                if n.notam_id not in ids:
                    ids.append(n.notam_id)
        return ids

    def _collect_tfr_conflicts(self, request: BriefingRequest) -> List[str]:
        if self.tfr_handler is None:
            return []
        ids: List[str] = []
        route = [request.departure] + list(request.route_waypoints) + [request.destination]
        for wp in route:
            pos3 = (wp[0], wp[1], request.planned_altitude_m)
            violations = self.tfr_handler.check_violation(request.callsign, pos3)
            for v in violations:
                if v not in ids:
                    ids.append(v)
        return ids

    def _collect_chart_hazards(self, request: BriefingRequest) -> List[str]:
        if self.aero_charts is None:
            return []
        route = [request.departure] + list(request.route_waypoints) + [request.destination]
        hazards = self.aero_charts.path_obstacles(
            waypoints=route, corridor_width_m=300.0, min_altitude_m=0.0
        )
        return [h.feature_id for h in hazards]

    def _assess_weather(self, metar_text: Optional[str], warnings: List[str]) -> bool:
        if metar_text is None or self.metar_parser is None:
            return True
        try:
            obs = self.metar_parser.parse_metar(metar_text)
        except ValueError as exc:
            warnings.append(f"METAR parse failed: {exc}")
            return True
        if obs.wind_speed_kt >= 25:
            warnings.append(f"High winds {obs.wind_speed_kt} kt")
        if not self.metar_parser.is_vfr(obs):
            warnings.append("IFR conditions")
            return False
        return True

    @staticmethod
    def _summarize(
        is_go: bool,
        notams: List[str],
        tfrs: List[str],
        hazards: List[str],
        weather_ok: bool,
    ) -> str:
        verdict = "GO" if is_go else "NO-GO"
        return (
            f"{verdict}: {len(notams)} NOTAM, {len(tfrs)} TFR, "
            f"{len(hazards)} hazard; weather={'ok' if weather_ok else 'bad'}"
        )

    def stats(self) -> Dict[str, Any]:
        go = sum(1 for r in self.history if r.go_nogo == "GO")
        nogo = len(self.history) - go
        return {"briefings": len(self.history), "go": go, "nogo": nogo}

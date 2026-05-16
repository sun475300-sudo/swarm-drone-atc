"""Phase 694: METAR/TAF 기상 보고 파서."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class WeatherObservation:
    station: str
    time_utc: str
    wind_dir_deg: Optional[int]
    wind_speed_kt: int
    gust_kt: Optional[int]
    visibility_m: Optional[int]
    visibility_sm: Optional[float]
    temperature_c: Optional[int]
    dewpoint_c: Optional[int]
    altimeter_hpa: Optional[int]
    conditions: List[str] = field(default_factory=list)
    clouds: List[Tuple[str, int]] = field(default_factory=list)
    raw: str = ""


@dataclass
class TafForecast:
    station: str
    issued: str
    valid_from: str
    valid_to: str
    wind_dir_deg: Optional[int]
    wind_speed_kt: int
    visibility_sm: Optional[float]
    raw: str = ""


class MetarParser:
    """METAR/TAF 문자열을 구조화된 관측/예보로 변환한다."""

    WIND_RE = re.compile(r"(\d{3}|VRB)(\d{2,3})(?:G(\d{2,3}))?KT")
    # TAF 유효기간 토큰(예: 0912/1018)의 두 부분을 모두 가시거리로 오탐하지 않도록
    # '/' 앞에 오거나('/' 뒤에 오는) 경우를 lookbehind/lookahead로 제외한다.
    VIS_M_RE = re.compile(r"(?<!/)\b(\d{4})\b(?![/\d])")
    VIS_SM_RE = re.compile(r"(\d+)SM")
    TEMP_RE = re.compile(r"\b(M?\d{2})/(M?\d{2})\b")
    ALT_RE = re.compile(r"Q(\d{4})")
    CLOUD_RE = re.compile(r"(FEW|SCT|BKN|OVC)(\d{3})")

    CONDITION_CODES = {
        "RA": "rain", "SN": "snow", "TS": "thunderstorm", "FG": "fog",
        "BR": "mist", "HZ": "haze", "DZ": "drizzle", "GR": "hail",
        "SH": "shower", "FZ": "freezing",
    }

    def parse_metar(self, text: str) -> WeatherObservation:
        if not text:
            raise ValueError("empty METAR text")
        tokens = text.strip().split()
        if len(tokens) < 3:
            raise ValueError("METAR too short")
        station = tokens[0]
        time_utc = tokens[1] if len(tokens) > 1 else ""

        wind_dir: Optional[int] = None
        wind_speed = 0
        gust: Optional[int] = None
        m = self.WIND_RE.search(text)
        if m:
            wind_dir = None if m.group(1) == "VRB" else int(m.group(1))
            wind_speed = int(m.group(2))
            gust = int(m.group(3)) if m.group(3) else None

        vis_m: Optional[int] = None
        vis_sm: Optional[float] = None
        mvm = self.VIS_M_RE.search(text)
        if mvm:
            candidate = int(mvm.group(1))
            if 0 < candidate <= 9999:
                vis_m = candidate
        mvs = self.VIS_SM_RE.search(text)
        if mvs:
            vis_sm = float(mvs.group(1))

        temp: Optional[int] = None
        dew: Optional[int] = None
        mt = self.TEMP_RE.search(text)
        if mt:
            temp = self._signed(mt.group(1))
            dew = self._signed(mt.group(2))

        alt: Optional[int] = None
        ma = self.ALT_RE.search(text)
        if ma:
            alt = int(ma.group(1))

        conditions = [
            name for code, name in self.CONDITION_CODES.items() if code in text
        ]
        clouds = [(c.group(1), int(c.group(2)) * 100) for c in self.CLOUD_RE.finditer(text)]

        return WeatherObservation(
            station=station,
            time_utc=time_utc,
            wind_dir_deg=wind_dir,
            wind_speed_kt=wind_speed,
            gust_kt=gust,
            visibility_m=vis_m,
            visibility_sm=vis_sm,
            temperature_c=temp,
            dewpoint_c=dew,
            altimeter_hpa=alt,
            conditions=conditions,
            clouds=clouds,
            raw=text.strip(),
        )

    def parse_taf(self, text: str) -> TafForecast:
        if not text:
            raise ValueError("empty TAF text")
        tokens = text.strip().split()
        if len(tokens) < 3:
            raise ValueError("TAF too short")
        idx = 0
        if tokens[0] == "TAF":
            idx = 1
        station = tokens[idx]
        issued = tokens[idx + 1] if idx + 1 < len(tokens) else ""
        valid_from = ""
        valid_to = ""
        for t in tokens:
            if "/" in t and len(t) == 9 and t[4] == "/":
                valid_from, valid_to = t.split("/")
                break

        wind_dir: Optional[int] = None
        wind_speed = 0
        m = self.WIND_RE.search(text)
        if m:
            wind_dir = None if m.group(1) == "VRB" else int(m.group(1))
            wind_speed = int(m.group(2))

        vis_sm: Optional[float] = None
        mvs = self.VIS_SM_RE.search(text)
        if mvs:
            vis_sm = float(mvs.group(1))

        return TafForecast(
            station=station,
            issued=issued,
            valid_from=valid_from,
            valid_to=valid_to,
            wind_dir_deg=wind_dir,
            wind_speed_kt=wind_speed,
            visibility_sm=vis_sm,
            raw=text.strip(),
        )

    @staticmethod
    def _signed(token: str) -> int:
        if token.startswith("M"):
            return -int(token[1:])
        return int(token)

    def is_vfr(self, obs: WeatherObservation) -> bool:
        if obs.visibility_sm is not None and obs.visibility_sm < 3:
            return False
        ceiling = None
        for cover, height in obs.clouds:
            if cover in ("BKN", "OVC"):
                ceiling = height if ceiling is None else min(ceiling, height)
        if ceiling is not None and ceiling < 1000:
            return False
        return True

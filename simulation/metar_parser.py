"""Phase 694: METAR/TAF 기상 보고 파서."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class WeatherObservation:
    station: str
    time_utc: str
    wind_dir_deg: int | None
    wind_speed_kt: int
    gust_kt: int | None
    visibility_m: int | None
    visibility_sm: float | None
    temperature_c: int | None
    dewpoint_c: int | None
    altimeter_hpa: int | None
    conditions: list[str] = field(default_factory=list)
    clouds: list[tuple[str, int]] = field(default_factory=list)
    raw: str = ""
    # CAVOK (Ceiling And Visibility OK): visibility >= 10 km, no cloud below 5000 ft.
    # When True, is_vfr() short-circuits to True regardless of parsed visibility/cloud fields.
    cavok: bool = False


@dataclass
class TafForecast:
    station: str
    issued: str
    valid_from: str
    valid_to: str
    wind_dir_deg: int | None
    wind_speed_kt: int
    visibility_sm: float | None
    raw: str = ""


class MetarParser:
    """METAR/TAF 문자열을 구조화된 관측/예보로 변환한다."""

    WIND_RE = re.compile(r"(\d{3}|VRB)(\d{2,3})(?:G(\d{2,3}))?KT")
    # TAF 유효기간 토큰(예: 0912/1018)의 두 부분을 모두 가시거리로 오탐하지 않도록
    # '/' 앞에 오거나 '/' 뒤에 오는 경우를 lookbehind/lookahead로 제외한다.
    VIS_M_RE = re.compile(r"(?<!/)\b(\d{4})\b(?![/\d])")
    # 정수 및 분수 SM 가시거리 지원: 1/2SM, 3/4SM, 10SM 등
    VIS_SM_RE = re.compile(r"(\d+(?:/\d+)?)SM")
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
        # METAR/SPECI 키워드가 앞에 붙은 경우 station/time 토큰 위치를 조정
        skip = 1 if tokens and tokens[0] in ("METAR", "SPECI") else 0
        if len(tokens) < skip + 3:
            raise ValueError("METAR too short")
        station = tokens[skip]
        time_utc = tokens[skip + 1]

        wind_dir: int | None = None
        wind_speed = 0
        gust: int | None = None
        m = self.WIND_RE.search(text)
        if m:
            wind_dir = None if m.group(1) == "VRB" else int(m.group(1))
            wind_speed = int(m.group(2))
            gust = int(m.group(3)) if m.group(3) else None

        # CAVOK (Ceiling And Visibility OK) — definitively VFR, skip detailed vis/cloud parsing
        cavok = "CAVOK" in tokens

        vis_m: int | None = None
        vis_sm: float | None = None
        mvm = self.VIS_M_RE.search(text)
        if mvm:
            candidate = int(mvm.group(1))
            if 0 < candidate <= 9999:
                vis_m = candidate
        mvs = self.VIS_SM_RE.search(text)
        if mvs:
            raw_sm = mvs.group(1)
            if "/" in raw_sm:
                num, den = raw_sm.split("/")
                den_f = float(den)
                vis_sm = float(num) / den_f if den_f != 0 else 0.0
            else:
                vis_sm = float(raw_sm)

        temp: int | None = None
        dew: int | None = None
        mt = self.TEMP_RE.search(text)
        if mt:
            temp = self._signed(mt.group(1))
            dew = self._signed(mt.group(2))

        alt: int | None = None
        ma = self.ALT_RE.search(text)
        if ma:
            alt = int(ma.group(1))

        # 스테이션 ID(index 0)와 시각(index 1)을 제외한 나머지 토큰에서만 매칭
        # — "RKSHI"처럼 스테이션 이름에 조건 코드 문자열이 포함되는 오탐 방지
        all_tokens = text.strip().split()
        # METAR/SPECI 키워드가 앞에 올 경우 건너뜀
        skip = 1 if all_tokens and all_tokens[0] in ("METAR", "SPECI") else 0
        check_tokens = set(all_tokens[skip + 2:])  # 스테이션 + 시각 이후
        conditions = [
            name
            for code, name in self.CONDITION_CODES.items()
            if any(code in tok for tok in check_tokens)
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
            cavok=cavok,
        )

    def parse_taf(self, text: str) -> TafForecast:
        if not text:
            raise ValueError("empty TAF text")
        tokens = text.strip().split()
        if len(tokens) < 3:
            raise ValueError("TAF too short")
        idx = 0
        if tokens[0] in ("TAF", "METAR", "SPECI"):
            idx = 1
        if len(tokens) < idx + 3:
            raise ValueError("TAF too short")
        station = tokens[idx]
        issued = tokens[idx + 1] if idx + 1 < len(tokens) else ""
        valid_from = ""
        valid_to = ""
        for t in tokens:
            if "/" in t and len(t) == 9 and t[4] == "/":
                valid_from, valid_to = t.split("/")
                break

        wind_dir: int | None = None
        wind_speed = 0
        m = self.WIND_RE.search(text)
        if m:
            wind_dir = None if m.group(1) == "VRB" else int(m.group(1))
            wind_speed = int(m.group(2))

        vis_sm: float | None = None
        mvs = self.VIS_SM_RE.search(text)
        if mvs:
            raw_sm = mvs.group(1)
            if "/" in raw_sm:
                num, den = raw_sm.split("/")
                den_f = float(den)
                vis_sm = float(num) / den_f if den_f != 0 else 0.0
            else:
                vis_sm = float(raw_sm)

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

    _SM_PER_M = 1.0 / 1609.344

    def is_vfr(self, obs: WeatherObservation) -> bool:
        # CAVOK guarantees ceiling >= 5000 ft and visibility >= 10 km — definitively VFR
        if obs.cavok:
            return True
        # SM 가시거리 우선, 없으면 미터 값을 SM으로 환산해 평가
        # 가시거리 정보가 전혀 없으면 VFR 확인 불가 → False
        if obs.visibility_sm is not None:
            if obs.visibility_sm < 3:
                return False
        elif obs.visibility_m is not None:
            if obs.visibility_m * self._SM_PER_M < 3:
                return False
        else:
            return False
        ceiling = None
        for cover, height in obs.clouds:
            if cover in ("BKN", "OVC"):
                ceiling = height if ceiling is None else min(ceiling, height)
        return not (ceiling is not None and ceiling < 1000)

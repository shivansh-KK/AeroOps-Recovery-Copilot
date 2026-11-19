"""METAR decoder for wind, visibility, flight category, and basic hazards."""
import re
from pydantic import BaseModel, Field

from .base import BaseTool

AIRPORT_CODES = {"DXB": "OMDB", "OMDB": "OMDB", "LHR": "EGLL", "EGLL": "EGLL", "JFK": "KJFK", "KJFK": "KJFK", "SIN": "WSSS", "WSSS": "WSSS"}
SAMPLE_METARS = {
    "OMDB": "OMDB 191200Z 34018G28KT 4000 TSRA SCT015CB BKN030 32/24 Q1008",
    "EGLL": "EGLL 191200Z 24008KT 9999 SCT025 12/08 Q1012",
    "KJFK": "KJFK 191200Z 02012KT 6000 -RA BKN018 09/07 Q1010",
    "WSSS": "WSSS 191200Z 18006KT 8000 FEW020 30/25 Q1009",
}


class METARInput(BaseModel):
    airport_code: str = Field(min_length=3, max_length=4, description="ICAO or IATA airport code")
    metar: str | None = Field(default=None, description="Optional raw METAR; uses local sample when omitted")
    runway_heading_degrees: float = Field(default=340.0, ge=0, lt=360)


class METARWeatherTool(BaseTool):
    name = "get_aviation_weather"
    description = "Decode METAR weather, flight category, wind hazards, and runway crosswind."
    args_schema = METARInput

    def _run(self, arguments: METARInput) -> dict[str, object]:
        code = AIRPORT_CODES.get(arguments.airport_code.strip().upper())
        if code is None:
            raise ValueError(f"Unknown airport code: {arguments.airport_code}")
        raw = arguments.metar or SAMPLE_METARS[code]
        wind = re.search(r"\b(\d{3}|VRB)(\d{2,3})(?:G(\d{2,3}))?KT\b", raw)
        visibility_match = re.search(r"\b(\d{4})\b", raw)
        if wind is None or visibility_match is None:
            raise ValueError("METAR is missing a supported wind or visibility group")
        direction = None if wind.group(1) == "VRB" else int(wind.group(1))
        speed = int(wind.group(2))
        gust = int(wind.group(3)) if wind.group(3) else None
        vis = int(visibility_match.group(1))
        angle = 0.0 if direction is None else abs((direction - arguments.runway_heading_degrees + 180) % 360 - 180)
        crosswind = round((gust if gust is not None else speed) * abs(__import__("math").sin(__import__("math").radians(angle))), 1)
        if vis < 1600 or re.search(r"\b(?:FG|FZFG)\b", raw):
            visibility_category = 0
        elif vis < 4800:
            visibility_category = 1
        elif vis < 8000:
            visibility_category = 2
        else:
            visibility_category = 3
        ceilings = [int(height) * 100 for cover, height in re.findall(r"\b(FEW|SCT|BKN|OVC)(\d{3})\b", raw) if cover in {"BKN", "OVC"}]
        ceiling = min(ceilings) if ceilings else None
        if ceiling is not None and ceiling < 500:
            ceiling_category = 0
        elif ceiling is not None and ceiling < 1000:
            ceiling_category = 1
        elif ceiling is not None and ceiling <= 3000:
            ceiling_category = 2
        else:
            ceiling_category = 3
        category = ("LIFR", "IFR", "MVFR", "VFR")[min(visibility_category, ceiling_category)]
        return {"airport_icao": code, "raw_metar": raw, "wind_direction_degrees": direction,
                "wind_speed_kt": speed, "wind_gust_kt": gust, "visibility_meters": vis,
                "ceiling_feet_agl": ceiling, "crosswind_component_kt": crosswind, "flight_category": category,
                "thunderstorm": bool(re.search(r"\bTS(?:RA|SN|GR|GS|PL|DZ|BR|FG|SHRA|SHSN)?\b", raw)), "convective_cloud": "CB" in raw,
                "runway_wind_hazard": crosswind >= 25, "source": "provided METAR" if arguments.metar else "synthetic local sample"}

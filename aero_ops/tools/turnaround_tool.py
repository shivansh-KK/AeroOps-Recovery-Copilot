"""Turnaround and destination curfew feasibility calculator."""
from datetime import datetime, time
from pydantic import BaseModel, Field
from aero_ops.database.db_manager import DatabaseManager
from .base import BaseTool


class TurnaroundInput(BaseModel):
    tail_number: str = Field(min_length=3)
    inbound_arrival_utc: datetime
    new_departure_utc: datetime
    destination_icao: str = Field(min_length=4, max_length=4)
    new_arrival_utc: datetime


class TurnaroundFeasibilityTool(BaseTool):
    name = "check_turnaround_feasibility"
    description = "Check minimum aircraft ground turn and destination airport curfew."
    args_schema = TurnaroundInput

    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def _run(self, arguments: TurnaroundInput) -> dict[str, object]:
        aircraft = self.database.query("SELECT min_turnaround_minutes, model FROM aircraft WHERE tail_number=?", (arguments.tail_number,))
        if not aircraft:
            raise ValueError(f"Unknown aircraft tail number: {arguments.tail_number}")
        inbound = arguments.inbound_arrival_utc
        departure = arguments.new_departure_utc
        arrival = arguments.new_arrival_utc
        if any(value.tzinfo is None for value in (inbound, departure, arrival)):
            raise ValueError("All turnaround timestamps must include a timezone")
        available = int((departure - inbound).total_seconds() // 60)
        minimum = int(aircraft[0]["min_turnaround_minutes"])
        airport_rows = self.database.query("SELECT curfew_start_utc, curfew_end_utc FROM airports WHERE icao_code=?", (arguments.destination_icao.upper(),))
        if not airport_rows:
            raise ValueError(f"Unknown destination airport: {arguments.destination_icao}")
        start, end = airport_rows[0]["curfew_start_utc"], airport_rows[0]["curfew_end_utc"]
        arrival_time = arrival.astimezone(__import__("datetime").timezone.utc).time().replace(tzinfo=None)
        in_curfew = bool(start and end and _within_window(arrival_time, time.fromisoformat(start), time.fromisoformat(end)))
        return {"tail_number": arguments.tail_number, "aircraft_model": aircraft[0]["model"],
                "available_turn_minutes": available, "minimum_turn_minutes": minimum,
                "turnaround_feasible": available >= minimum, "destination_icao": arguments.destination_icao.upper(),
                "arrival_in_curfew": in_curfew, "feasible": available >= minimum and not in_curfew}


def _within_window(value: time, start: time, end: time) -> bool:
    return start <= value < end if start <= end else value >= start or value < end

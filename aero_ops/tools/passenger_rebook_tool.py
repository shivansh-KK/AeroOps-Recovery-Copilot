"""Connection risk assessment, candidate flight matching, and indicative compensation."""
from datetime import datetime
from pydantic import BaseModel, Field
from aero_ops.database.db_manager import DatabaseManager
from .base import BaseTool


class RebookingInput(BaseModel):
    flight_number: str = Field(min_length=3)
    delay_hours: float = Field(default=0, ge=0, le=72)
    minimum_connection_minutes: int = Field(default=60, ge=0, le=600)
    eu261_eligible: bool = Field(default=False, description="Eligibility must be confirmed by an authorized policy workflow")


class PassengerRebookingTool(BaseTool):
    name = "assess_passenger_recovery"
    description = "Identify at-risk connections and candidate alternate services; estimate eligible compensation."
    args_schema = RebookingInput

    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def _run(self, arguments: RebookingInput) -> dict[str, object]:
        passengers = self.database.query("SELECT * FROM passengers WHERE flight_number=? ORDER BY CASE tier WHEN 'PLATINUM' THEN 0 WHEN 'GOLD' THEN 1 ELSE 2 END, pnr", (arguments.flight_number,))
        if not self.database.query("SELECT flight_number FROM flights WHERE flight_number=?", (arguments.flight_number,)):
            raise ValueError(f"Unknown flight: {arguments.flight_number}")
        at_risk = [row for row in passengers if row["connection_time_mins"] is not None and row["connection_time_mins"] < arguments.minimum_connection_minutes]
        candidates = self.database.query("SELECT flight_number, scheduled_departure_utc, tail_number, origin_icao, destination_icao FROM flights WHERE origin_icao=(SELECT destination_icao FROM flights WHERE flight_number=?) AND status!='CANCELLED' ORDER BY scheduled_departure_utc LIMIT 8", (arguments.flight_number,))
        compensation_per_person = 600 if arguments.eu261_eligible and arguments.delay_hours >= 3 else 0
        return {"flight_number": arguments.flight_number, "passengers_on_flight": len(passengers),
                "at_risk_connections": len(at_risk), "priority_order": [p["pnr"] for p in at_risk],
                "candidate_onward_flights": candidates, "indicative_eu261_compensation_eur_per_eligible_passenger": compensation_per_person,
                "compensation_note": "Indicative maximum only; confirm route distance, cause, and legal eligibility before offering."}

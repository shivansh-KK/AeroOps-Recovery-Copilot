"""Read-only SQL query tool with a schema helper."""
import re
from pydantic import BaseModel, Field
from aero_ops.database.db_manager import DatabaseManager
from aero_ops.guardrails.exceptions import ToolExecutionError
from .base import BaseTool

FORBIDDEN_SQL = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|DETACH|VACUUM|REINDEX|PRAGMA)\b", re.I)


class SQLInput(BaseModel):
    query: str = Field(min_length=1, max_length=4000, description="A single read-only SELECT query")


class FlightSQLTool(BaseTool):
    name = "query_flight_operations"
    description = "Run a read-only SELECT query against flight, aircraft, crew, passenger, and airport data."
    args_schema = SQLInput

    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    @staticmethod
    def get_schema() -> str:
        return ("airports(icao_code PK, iata_code, name, city, country, timezone, curfew_start_utc, curfew_end_utc); "
                "aircraft(tail_number PK, model, seating_capacity, status, min_turnaround_minutes); "
                "flights(flight_number PK, tail_number FK, origin_icao, destination_icao, scheduled_departure_utc, "
                "scheduled_arrival_utc, actual_departure_utc, actual_arrival_utc, status, gate, delay_minutes); "
                "crew_rosters(crew_id PK, flight_number FK, crew_name, role, duty_start_utc, max_duty_hours); "
                "passengers(pnr PK, flight_number FK, passenger_name, tier, connecting_flight_number, connection_time_mins)")

    def _run(self, arguments: SQLInput) -> list[dict[str, object]]:
        query = arguments.query.strip()
        if not re.match(r"^(SELECT|WITH)\b", query, re.I) or FORBIDDEN_SQL.search(query):
            raise ToolExecutionError("Only read-only SELECT statements are permitted")
        if ";" in query.rstrip("; "):
            raise ToolExecutionError("Only one SQL statement is permitted")
        try:
            return self.database.query(query)
        except Exception as exc:
            raise ToolExecutionError(f"Flight SQL query failed: {exc}") from exc

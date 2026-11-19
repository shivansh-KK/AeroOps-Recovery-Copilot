"""Tests for weather decoding, safe SQL, and turnaround calculations."""
from datetime import datetime, timezone

import pytest

from aero_ops.database.db_manager import DatabaseManager
from aero_ops.database.seed_data import seed_database
from aero_ops.tools.flight_sql_tool import FlightSQLTool
from aero_ops.tools.metar_tool import METARWeatherTool
from aero_ops.tools.turnaround_tool import TurnaroundFeasibilityTool


@pytest.fixture
def db(tmp_path):
    database = DatabaseManager(tmp_path / "test.db")
    seed_database(database)
    return database


def test_metar_decodes_hazards_and_iata():
    result = METARWeatherTool().invoke({"airport_code": "DXB"})
    assert result["airport_icao"] == "OMDB"
    assert result["wind_speed_kt"] == 18
    assert result["thunderstorm"] is True


def test_flight_sql_is_read_only(db):
    tool = FlightSQLTool(db)
    assert tool.invoke({"query": "SELECT flight_number FROM flights LIMIT 2"})
    with pytest.raises(Exception):
        tool.invoke({"query": "DELETE FROM flights"})


def test_turnaround_calculator(db):
    tool = TurnaroundFeasibilityTool(db)
    result = tool.invoke({"tail_number": "A6-EKD", "inbound_arrival_utc": datetime(2026, 11, 19, 7, tzinfo=timezone.utc),
                          "new_departure_utc": datetime(2026, 11, 19, 8, 30, tzinfo=timezone.utc),
                          "destination_icao": "KJFK", "new_arrival_utc": datetime(2026, 11, 19, 15, tzinfo=timezone.utc)})
    assert result["turnaround_feasible"] is True
    assert result["minimum_turn_minutes"] == 60

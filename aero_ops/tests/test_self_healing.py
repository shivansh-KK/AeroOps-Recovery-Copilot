"""Tests for bounded agent correction after an initial tool error."""
from aero_ops.agent.self_healing import SelfHealingEngine
from aero_ops.database.db_manager import DatabaseManager
from aero_ops.database.seed_data import seed_database
from aero_ops.tools.flight_sql_tool import FlightSQLTool


def test_agent_self_heals_malformed_sql(tmp_path):
    database = DatabaseManager(tmp_path / "heal.db")
    seed_database(database)
    tool = FlightSQLTool(database)
    engine = SelfHealingEngine(max_retries=2)
    events: list[str] = []
    result = engine.execute("query_flight_operations", {"query": "SELECT flight_id FROM flights LIMIT 1"},
                            lambda payload: tool.invoke(payload), events)
    assert result[0]["flight_number"] == "EK001"
    assert len(events) == 1

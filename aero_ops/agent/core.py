"""Grounded ReAct-style disruption workflow with tool telemetry and safety checks."""
from datetime import datetime, timedelta, timezone
from time import perf_counter
from typing import Any

from aero_ops.config.settings import get_settings
from aero_ops.database.db_manager import DatabaseManager
from aero_ops.database.seed_data import seed_database
from aero_ops.guardrails.aviation_safety_guard import AviationSafetyGuard
from aero_ops.guardrails.exceptions import AviationSafetyViolation
from aero_ops.guardrails.output_verifier import OutputVerifier
from aero_ops.tools.registry import ToolRegistry
from .self_healing import SelfHealingEngine
from .state import AgentState, StepTrace, ToolCallRecord


class AeroOpsAgent:
    """Operational decision-support agent; all recommended actions are tool-grounded."""

    def __init__(self, database: DatabaseManager | None = None) -> None:
        settings = get_settings()
        self.database = database or DatabaseManager(settings.database_path)
        seed_database(self.database)
        self.registry = ToolRegistry.discover(self.database)
        self.guard = AviationSafetyGuard()
        self.verifier = OutputVerifier()
        self.healer = SelfHealingEngine(settings.max_retries)
        self.maximum_steps = settings.maximum_agent_steps

    def _call(self, state: AgentState, step: int, thought: str, name: str, arguments: dict[str, Any]) -> Any:
        started = datetime.now(timezone.utc).isoformat()
        timer = perf_counter()
        try:
            result = self.healer.execute(name, arguments, lambda payload: self.registry.dispatch(name, payload), state.self_healing_events)
            record = ToolCallRecord(name, arguments, started, (perf_counter() - timer) * 1000, True, result)
            state.tool_calls.append(record)
            state.traces.append(StepTrace(step, thought, record, result))
            return result
        except Exception as exc:
            record = ToolCallRecord(name, arguments, started, (perf_counter() - timer) * 1000, False, error=str(exc))
            state.tool_calls.append(record)
            state.traces.append(StepTrace(step, thought, record, {"error": str(exc)}))
            raise

    def run(self, scenario: str = "Severe thunderstorm at DXB", flight_number: str = "EK001", delay_hours: float = 4.0) -> AgentState:
        state = AgentState(scenario=scenario)
        if self.maximum_steps < 3:
            raise RuntimeError("maximum_agent_steps must allow at least three tool observations")
        state.conversation.add("system", "Use tool observations and enforce aviation safety limits.")
        weather = self._call(state, 1, "Check hub weather before selecting a recovery plan.", "get_aviation_weather", {"airport_code": "DXB"})
        flight_rows = self._call(state, 2, "Read the affected flight, aircraft, and crew roster from the operations database.", "query_flight_operations", {"query": "SELECT f.flight_number, f.tail_number, f.origin_icao, f.destination_icao, f.scheduled_departure_utc, f.scheduled_arrival_utc, f.status, f.gate, f.delay_minutes, a.model, a.min_turnaround_minutes FROM flights f JOIN aircraft a ON a.tail_number=f.tail_number WHERE f.flight_number='" + flight_number.replace("'", "''") + "'"})
        if not flight_rows:
            raise ValueError(f"No flight record found for {flight_number}")
        flight = flight_rows[0]
        passenger = self._call(state, 3, "Identify disrupted connections and candidate onward services.", "assess_passenger_recovery", {"flight_number": flight_number, "delay_hours": delay_hours, "eu261_eligible": False})
        crew_rows = self.database.query("SELECT crew_id, duty_start_utc, max_duty_hours FROM crew_rosters WHERE flight_number=?", (flight_number,))
        schedule_arrival = datetime.fromisoformat(str(flight["scheduled_arrival_utc"]))
        proposed_release = schedule_arrival + timedelta(hours=delay_hours)
        crew_status = "Crew duty within recorded limit"
        if crew_rows:
            crew = crew_rows[0]
            try:
                self.guard.validate_crew_duty(datetime.fromisoformat(str(crew["duty_start_utc"])), proposed_release, float(crew["max_duty_hours"]))
            except AviationSafetyViolation:
                crew_status = "RELIEF CREW REQUIRED: proposed delay exceeds recorded crew FDP limit"
                state.self_healing_events.append("Safety hold: crew FDP limit intercepted; dispatch relief crew before departure.")
        state.recovery_options_evaluated = 3
        tail = str(flight["tail_number"])
        delay_minutes = max(int(flight["delay_minutes"]), round(delay_hours * 60))
        brief = (f"DISPATCH RECOVERY BRIEF — {flight_number}\n"
                 f"Aircraft: {tail} ({flight['model']}); current status {flight['status']}; gate {flight['gate']}.\n"
                 f"Weather: {weather['flight_category']} at {weather['airport_icao']}; visibility {weather['visibility_meters']} m; "
                 f"wind {weather['wind_speed_kt']} kt (gust {weather['wind_gust_kt'] or weather['wind_speed_kt']} kt); "
                 f"thunderstorm {'reported' if weather['thunderstorm'] else 'not reported'}.\n"
                 f"Schedule: planning delay {delay_minutes // 60}h {delay_minutes % 60:02d}m; confirm revised slot and times with operations control.\n"
                 f"Passengers: {passenger['at_risk_connections']} connections below the {60}-minute MCT; prioritize reaccommodation by tier. "
                 f"EU261 estimate: not calculated because eligibility is unconfirmed.\n"
                 f"Crew: {crew_status}.\n"
                 "Safety: no schedule release until dispatch confirms weather, slot, aircraft turn, crew legality, and curfew constraints.")
        state.final_brief = brief
        state.verification = self.verifier.verify(brief, [weather, flight_rows, passenger])
        if not state.verification["verified"]:
            state.final_brief = "HOLD — output verification failed: " + "; ".join(state.verification["errors"])
        state.conversation.add("assistant", state.final_brief)
        return state

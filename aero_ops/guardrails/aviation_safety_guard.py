"""Hard-rule checks for crew duty and aircraft turnaround proposals."""
from datetime import datetime
from typing import Any
from .exceptions import AviationSafetyViolation


class AviationSafetyGuard:
    def validate_crew_duty(self, duty_start_utc: datetime, proposed_release_utc: datetime, max_duty_hours: float = 14.0) -> None:
        if duty_start_utc.tzinfo is None or proposed_release_utc.tzinfo is None:
            raise AviationSafetyViolation("Crew duty timestamps must include timezone information")
        duty_hours = (proposed_release_utc - duty_start_utc).total_seconds() / 3600
        if duty_hours < 0:
            raise AviationSafetyViolation("Proposed crew release precedes crew duty start")
        if duty_hours > max_duty_hours:
            raise AviationSafetyViolation(f"Crew FDP would be {duty_hours:.2f}h, exceeding the {max_duty_hours:.2f}h limit; dispatch relief crew")

    def validate_turnaround(self, available_minutes: int, certified_minimum_minutes: int, tail_number: str = "unknown") -> None:
        if available_minutes < certified_minimum_minutes:
            raise AviationSafetyViolation(f"Aircraft {tail_number} has {available_minutes} minutes for turn; minimum is {certified_minimum_minutes}")

    def validate_proposal(self, proposal: dict[str, Any]) -> None:
        crew = proposal.get("crew")
        if crew:
            self.validate_crew_duty(crew["duty_start_utc"], crew["proposed_release_utc"], crew["max_duty_hours"])
        turn = proposal.get("turnaround")
        if turn:
            self.validate_turnaround(int(turn["available_turn_minutes"]), int(turn["minimum_turn_minutes"]), str(turn.get("tail_number", "unknown")))

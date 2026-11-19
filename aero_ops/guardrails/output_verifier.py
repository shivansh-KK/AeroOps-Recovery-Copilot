"""Verify operational facts in a recovery brief against tool observations."""
import re
from typing import Any


class OutputVerifier:
    def verify(self, brief: str, observations: list[dict[str, Any]]) -> dict[str, Any]:
        known_tails: set[str] = set()
        known_flights: set[str] = set()
        known_gates: set[str] = set()
        known_delays: set[int] = set()
        for observation in observations:
            rows = observation if isinstance(observation, list) else [observation]
            for row in rows:
                if not isinstance(row, dict):
                    continue
                if row.get("tail_number"):
                    known_tails.add(str(row["tail_number"]))
                if row.get("flight_number"):
                    known_flights.add(str(row["flight_number"]))
                if row.get("gate"):
                    known_gates.add(str(row["gate"]))
                if row.get("delay_minutes") is not None:
                    known_delays.add(int(row["delay_minutes"]))
        mentioned_flights = set(re.findall(r"\b(?:EK|BA|AA|SQ)\d{3,4}\b", brief.upper()))
        mentioned_tails = set(re.findall(r"\bA6-[A-Z]{3}\b", brief.upper()))
        mentioned_gates = set(re.findall(r"\bGATE\s+([A-Z0-9]+)\b", brief.upper()))
        errors: list[str] = []
        if mentioned_flights - known_flights:
            errors.append(f"Unverified flight numbers: {', '.join(sorted(mentioned_flights - known_flights))}")
        if mentioned_tails - known_tails:
            errors.append(f"Unverified tail numbers: {', '.join(sorted(mentioned_tails - known_tails))}")
        if mentioned_gates - known_gates:
            errors.append(f"Unverified gate references: {', '.join(sorted(mentioned_gates - known_gates))}")
        return {"verified": not errors, "errors": errors, "observed_flights": sorted(known_flights),
                "observed_tails": sorted(known_tails), "observed_gates": sorted(known_gates), "observed_delays_minutes": sorted(known_delays)}

"""Bounded retry and correction policy for common model/tool mistakes."""
from typing import Any, Callable
from aero_ops.config.settings import get_settings
from aero_ops.tools.metar_tool import AIRPORT_CODES
from .prompts import ERROR_REFLECTION_TEMPLATE


class SelfHealingEngine:
    def __init__(self, max_retries: int | None = None) -> None:
        self.max_retries = max_retries if max_retries is not None else get_settings().max_retries

    def execute(self, tool_name: str, arguments: dict[str, Any], call: Callable[[dict[str, Any]], Any], events: list[str]) -> Any:
        payload = dict(arguments)
        for attempt in range(self.max_retries + 1):
            try:
                return call(payload)
            except Exception as exc:
                if attempt >= self.max_retries:
                    raise
                reflection = ERROR_REFLECTION_TEMPLATE.format(tool_name=tool_name, error_details=str(exc))
                events.append(reflection)
                if "airport_code" in payload:
                    payload["airport_code"] = AIRPORT_CODES.get(str(payload["airport_code"]).upper(), payload["airport_code"])
                if "query" in payload:
                    query = str(payload["query"])
                    payload["query"] = query.replace("flight_id", "flight_number").replace("tail", "tail_number")

"""Tool registration, schema export, and safe dispatch."""
from typing import Any, Iterable

from .base import BaseTool


class ToolRegistry:
    def __init__(self, tools: Iterable[BaseTool] = ()) -> None:
        self._tools: dict[str, BaseTool] = {}
        for tool in tools:
            self.register(tool)

    @classmethod
    def discover(cls, database: Any) -> "ToolRegistry":
        """Load the package's available built-in operational tools for a database."""
        from .flight_sql_tool import FlightSQLTool
        from .metar_tool import METARWeatherTool
        from .passenger_rebook_tool import PassengerRebookingTool
        from .turnaround_tool import TurnaroundFeasibilityTool

        return cls((METARWeatherTool(), FlightSQLTool(database), TurnaroundFeasibilityTool(database), PassengerRebookingTool(database)))

    def register(self, tool: BaseTool) -> None:
        if not getattr(tool, "name", "") or tool.name in self._tools:
            raise ValueError(f"Tool name is empty or already registered: {getattr(tool, 'name', '')}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool '{name}'. Available tools: {', '.join(sorted(self._tools))}") from exc

    def dispatch(self, name: str, payload: dict[str, Any]) -> Any:
        return self.get(name).invoke(payload)

    def schemas(self, provider: str = "openai") -> list[dict[str, Any]]:
        return [tool.function_schema(provider) for tool in self._tools.values()]

    def names(self) -> tuple[str, ...]:
        return tuple(self._tools)

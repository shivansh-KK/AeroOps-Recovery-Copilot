"""Base class for validated, model-callable tools."""
from abc import ABC, abstractmethod
from typing import Any, Type

from pydantic import BaseModel


class BaseTool(ABC):
    name: str
    description: str
    args_schema: Type[BaseModel]

    @abstractmethod
    def _run(self, arguments: BaseModel) -> Any:
        """Run the tool after input validation."""

    def invoke(self, payload: dict[str, Any]) -> Any:
        parsed = self.args_schema.model_validate(payload)
        return self._run(parsed)

    def function_schema(self, provider: str = "openai") -> dict[str, Any]:
        parameters = self.args_schema.model_json_schema()
        if provider.lower() == "anthropic":
            return {"name": self.name, "description": self.description, "input_schema": parameters}
        if provider.lower() in {"gemini", "google"}:
            return {"name": self.name, "description": self.description, "parameters": parameters}
        return {"type": "function", "function": {"name": self.name, "description": self.description, "parameters": parameters}}

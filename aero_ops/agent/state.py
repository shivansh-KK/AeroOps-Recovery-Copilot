"""Serializable telemetry records for a single disruption recovery run."""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ToolCallRecord:
    tool_name: str
    arguments: dict[str, Any]
    started_at: str
    latency_ms: float
    success: bool
    result: Any = None
    error: str | None = None


@dataclass
class StepTrace:
    step: int
    thought: str
    tool_call: ToolCallRecord | None = None
    observation: Any = None


@dataclass
class ConversationHistory:
    messages: list[dict[str, str]] = field(default_factory=list)

    def add(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})


@dataclass
class AgentState:
    scenario: str = ""
    traces: list[StepTrace] = field(default_factory=list)
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    self_healing_events: list[str] = field(default_factory=list)
    recovery_options_evaluated: int = 0
    token_usage: dict[str, int] = field(default_factory=lambda: {"input": 0, "output": 0})
    conversation: ConversationHistory = field(default_factory=ConversationHistory)
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    final_brief: str = ""
    verification: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

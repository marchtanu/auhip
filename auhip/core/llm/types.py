from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class ToolStatus(str, Enum):
    SUCCEEDED = "succeeded"
    DENIED = "denied"
    FAILED = "failed"


@dataclass
class ToolResult:
    status: ToolStatus
    output: Any

    @property
    def succeeded(self) -> bool:
        return self.status == ToolStatus.SUCCEEDED

    @classmethod
    def from_output(cls, output: Any) -> "ToolResult":
        """Adapt legacy skill text until individual skills return structured results."""
        if isinstance(output, cls):
            return output
        if isinstance(output, str):
            normalized = output.lower().strip()
            if normalized.startswith(("error", "failed", "security restriction")) or "is disabled." in normalized:
                return cls(ToolStatus.FAILED, output)
        return cls(ToolStatus.SUCCEEDED, output)


@dataclass
class ToolSchema:
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)
    requires_confirmation: bool = False


@dataclass
class Message:
    role: str  # "system", "user", "assistant", "tool"
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


@dataclass
class LLMResponse:
    intent: str
    confidence: float
    requires_tool: bool
    tool_name: Optional[str]
    tool_args: Dict[str, Any]
    response: str
    escalate: bool
    raw_response: str = ""
    provider_used: str = "local"


@dataclass
class LLMRequest:
    prompt: str
    history: List[Message] = field(default_factory=list)
    available_tools: List[Any] = field(default_factory=list)
    require_structured: bool = True

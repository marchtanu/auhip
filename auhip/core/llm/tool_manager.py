import asyncio
import inspect
import logging
import os
from pathlib import Path
import uuid
from contextvars import ContextVar
from typing import Dict, Any, Callable, Awaitable, Optional, Tuple

from auhip.core.llm.config import llm_config
from auhip.core.llm.types import ToolResult, ToolSchema, ToolStatus
from auhip.core.event_bus import event_bus

logger = logging.getLogger(__name__)
_pending_tool_confirmations: Dict[str, asyncio.Future] = {}
CONFIRMATION_REQUIRED_TOOLS = frozenset({
    "write_code_file", "patch_file", "delete_file", "run_powershell_guarded",
    "send_to_antigravity", "forget_user_memory",
})
_approved_action: ContextVar[str | None] = ContextVar("approved_action", default=None)


def is_tool_authorized(tool_name: str) -> bool:
    return (_approved_action.get() == tool_name
            or os.getenv("AUHIP_ALLOW_UNSAFE_TOOLS", "").strip().lower() in {"1", "true", "yes"})


def require_tool_approval(tool_name: str) -> None:
    if not is_tool_authorized(tool_name):
        raise PermissionError(f"Tool '{tool_name}' requires approval through AUHIP's tool manager.")


def resolve_tool_confirmation(request_id: str, approved: bool) -> None:
    """Resolve a confirmation request initiated by a GUI tool call."""
    future = _pending_tool_confirmations.pop(request_id, None)
    if future is not None and not future.done():
        future.set_result(bool(approved))


class ToolManager:
    """
    Secure sandboxed central tool execution manager. Enforces argument schema validation,
    restricts filesystem path scopes to prevent directory traversals, and isolates exceptions.
    """

    def __init__(self):
        self._tools: Dict[str, Tuple[ToolSchema, Callable[..., Awaitable[Any]]]] = {}

    def register_tool(self, schema: ToolSchema, handler: Callable[..., Awaitable[Any]]):
        """Register a strongly typed skill alongside its execution pointer."""
        if schema.name in CONFIRMATION_REQUIRED_TOOLS:
            schema.requires_confirmation = True
        self._tools[schema.name] = (schema, handler)
        logger.debug(f"Registered sandboxed tool hook: '{schema.name}'")

    def get_schemas(self) -> list[ToolSchema]:
        """Expose all declared tool definitions for routing injection."""
        return [t[0] for t in self._tools.values()]

    @staticmethod
    def validate_arguments(schema: ToolSchema, args: Dict[str, Any]) -> None:
        """Validate a tool payload without invoking its handler."""
        if not isinstance(args, dict):
            raise TypeError("Tool arguments must be an object.")
        for required_name in schema.required:
            if required_name not in args:
                raise ValueError(f"Required parameter '{required_name}' missing.")

        declared_parameters = schema.parameters or {}
        unexpected = set(args) - set(declared_parameters)
        if unexpected:
            raise ValueError(f"Unexpected arguments for '{schema.name}': {sorted(unexpected)}")
        expected_types = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "object": dict,
            "array": list,
        }
        for name, value in args.items():
            parameter_type = declared_parameters.get(name, {}).get("type")
            expected = expected_types.get(parameter_type)
            if expected and (not isinstance(value, expected) or (parameter_type == "integer" and isinstance(value, bool))):
                raise TypeError(f"Argument '{name}' for '{schema.name}' must be {parameter_type}.")

    async def _request_confirmation(self, tool_name: str, args: Dict[str, Any]) -> bool:
        return await self.request_confirmation(tool_name, args)

    async def request_confirmation(
        self, action_name: str, args: Dict[str, Any], *, allow_unattended: bool = True,
    ) -> bool:
        if allow_unattended and os.getenv("AUHIP_ALLOW_UNSAFE_TOOLS", "").strip().lower() in {"1", "true", "yes"}:
            return True

        if not event_bus.has_subscribers("TOOL_CONFIRMATION_REQUESTED"):
            return False

        request_id = uuid.uuid4().hex
        future = asyncio.get_running_loop().create_future()
        _pending_tool_confirmations[request_id] = future
        try:
            await event_bus.publish("TOOL_CONFIRMATION_REQUESTED", {
                "request_id": request_id,
                "tool_name": action_name,
                "arguments": args,
            })
            return await asyncio.wait_for(future, timeout=60.0)
        except asyncio.TimeoutError:
            logger.info("Tool confirmation timed out for %s", action_name)
            return False
        finally:
            _pending_tool_confirmations.pop(request_id, None)
            await event_bus.publish("TOOL_CONFIRMATION_CLOSED", {"request_id": request_id})

    def is_path_safe(self, target_path: str) -> bool:
        """
        Validates target destination against pre-approved sandbox boundaries to block
        malicious access or relative traversal exploits.
        """
        abs_target = Path(target_path).expanduser().resolve()
        for boundary in llm_config.SANDBOX_ALLOWED_DIRS:
            try:
                abs_target.relative_to(Path(boundary).resolve())
                return True
            except ValueError:
                continue
        logger.warning(f"Path verification failed. Access denied to non-sandboxed target: {abs_target}")
        return False

    async def execute(self, tool_name: str, args: Dict[str, Any], timeout_override: Optional[float] = None) -> Any:
        result = await self.execute_result(tool_name, args, timeout_override)
        return result.output

    async def execute_result(
        self, tool_name: str, args: Dict[str, Any], timeout_override: Optional[float] = None,
    ) -> ToolResult:
        """
        Validates incoming structures and executes targeted internal handler safely
        within an isolated async execution scope.
        """
        if tool_name not in self._tools:
            logger.error(f"Unregistered tool execution requested: {tool_name}")
            raise KeyError(f"Tool {tool_name} is unknown.")

        schema, handler = self._tools[tool_name]
        logger.info(f"Orchestrating registered tool: {tool_name}")

        self.validate_arguments(schema, args)
        if schema.requires_confirmation and not await self._request_confirmation(tool_name, args):
            return ToolResult(ToolStatus.DENIED, f"Tool '{tool_name}' was not approved. No action was taken.")

        # Only validate explicitly path-like arguments; ordinary text can contain colons.
        for k, v in args.items():
            if k in {"path", "filename", "directory", "target_path"} and isinstance(v, str) and os.path.isabs(v):
                if not self.is_path_safe(v):
                    raise PermissionError(f"Argument '{k}' triggers path execution boundary violations.")

        # 3. Execution boundary isolation
        authorization = _approved_action.set(tool_name if schema.requires_confirmation else None)
        try:
            exec_timeout = timeout_override or 10.0
            
            # Support both coroutines and synchronous functions seamlessly
            if inspect.iscoroutinefunction(handler):
                result = await asyncio.wait_for(handler(**args), timeout=exec_timeout)
            else:
                result = await asyncio.wait_for(
                    asyncio.to_thread(handler, **args),
                    timeout=exec_timeout
                )
                
            logger.info(f"Successfully finalized tool execution: {tool_name}")
            return ToolResult.from_output(result)

        except asyncio.TimeoutError:
            logger.error(f"Tool execution timed out during execution: {tool_name}")
            return ToolResult(ToolStatus.FAILED, f"Error: execution of {tool_name} exceeded runtime caps.")
        except Exception as e:
            logger.exception(f"Isolated exception raised executing tool {tool_name}: {e}")
            return ToolResult(ToolStatus.FAILED, f"Error executing tool: {str(e)}")
        finally:
            _approved_action.reset(authorization)

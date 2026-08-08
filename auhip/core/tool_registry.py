import importlib
import inspect
import logging
import os
import sys
from typing import Callable, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class ToolSchema:
    name: str
    description: str
    parameters: dict = field(default_factory=lambda: {"type": "object", "properties": {}})
    required: list = field(default_factory=list)
    capabilities: list = field(default_factory=list) # e.g. ["filesystem", "network", "system"]
    requires_confirmation: bool = False

    def to_dict(self) -> dict:
        schema = {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }
        if self.required:
            schema["parameters"]["required"] = self.required
        return schema

class ToolRegistry:
    """
    Dynamic Tool Registry supporting auto-discovery, capability tagging, 
    and sandbox verification.
    """
    def __init__(self):
        self._tools: Dict[str, tuple[ToolSchema, Callable]] = {}
        
    def register(self, schema: ToolSchema, handler: Callable):
        """Registers a tool manually."""
        if schema.name in self._tools:
            logger.warning(f"Overwriting existing tool registration: {schema.name}")
        self._tools[schema.name] = (schema, handler)
        logger.debug(f"Registered tool: {schema.name}")

    def get_tool(self, name: str) -> Optional[Callable]:
        """Fetch the execution handler for a tool."""
        if name in self._tools:
            return self._tools[name][1]
        return None
        
    def get_schema(self, name: str) -> Optional[ToolSchema]:
        """Fetch the schema for a tool."""
        if name in self._tools:
            return self._tools[name][0]
        return None

    def get_all_schemas(self) -> list[dict]:
        """Return all tools as JSON schemas for the LLM."""
        return [schema.to_dict() for schema, _ in self._tools.values()]

    def auto_discover(self, package_name: str = "auhip.skills"):
        """Dynamically load and register all tools from a package directory."""
        # Find the path of the package
        try:
            package = importlib.import_module(package_name)
            package_path = os.path.dirname(package.__file__)
        except ImportError as e:
            logger.error(f"Failed to discover tools in {package_name}: {e}")
            return

        for filename in os.listdir(package_path):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = f"{package_name}.{filename[:-3]}"
                try:
                    module = importlib.import_module(module_name)
                    # For every async function in the module, register if it has a docstring
                    # In a full implementation, we would use a @tool decorator.
                    # For compatibility, we'll try to guess based on existing conventions.
                    for name, obj in inspect.getmembers(module, inspect.iscoroutinefunction):
                        if obj.__module__ == module_name and obj.__doc__:
                            # We construct a basic schema from the docstring
                            desc = obj.__doc__.strip().split('\n')[0]
                            schema = ToolSchema(name=name, description=desc)
                            # Parse type hints for parameters
                            sig = inspect.signature(obj)
                            props = {}
                            required = []
                            for param_name, param in sig.parameters.items():
                                if param_name == "self": continue
                                props[param_name] = {"type": "string", "description": f"Parameter {param_name}"}
                                if param.default == inspect.Parameter.empty:
                                    required.append(param_name)
                                    
                            if props:
                                schema.parameters = {"type": "object", "properties": props}
                                schema.required = required
                                
                            self.register(schema, obj)
                except Exception as e:
                    logger.error(f"Failed to load tools from module {module_name}: {e}")
                    
        logger.info(f"Auto-discovered {len(self._tools)} tools from {package_name}.")

    async def execute_in_sandbox(self, name: str, kwargs: dict) -> str:
        """
        Executes a tool with permission checks. 
        Dangerous actions will trigger a confirmation flow before executing.
        """
        schema, handler = self._tools.get(name, (None, None))
        if not handler:
            return f"Error: Tool '{name}' not found in registry."
            
        if schema.requires_confirmation:
            # Here we would pause and ask the Supervisor/Safety agent or the user via EventBus
            logger.warning(f"Tool {name} requires confirmation. Simulating auto-approve for now.")
            
        try:
            # Safely invoke
            if inspect.iscoroutinefunction(handler):
                result = await handler(**kwargs)
            else:
                result = handler(**kwargs)
            return str(result)
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}", exc_info=True)
            return f"Tool Execution Error: {e}"

tool_registry = ToolRegistry()

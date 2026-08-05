import asyncio
import json
import logging
import time
import aiohttp
from typing import Dict, Any, Optional

from auhip.core.llm.base import BaseLLMProvider
from auhip.core.llm.config import llm_config
from auhip.core.llm.response_parser import ResponseParser
from auhip.core.llm.types import LLMRequest, LLMResponse

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """
    Fully non-blocking asynchronous REST adapter communicating directly with local Ollama
    instances. Enforces JSON output formats and embeds circuit breaking timeouts.
    """

    def __init__(self):
        self.base_url = llm_config.OLLAMA_BASE_URL.rstrip("/")
        self.model = llm_config.LOCAL_MODEL_NAME
        self.timeout = aiohttp.ClientTimeout(total=llm_config.LOCAL_TIMEOUT_SECONDS)
        self.supports_tools = True
        self._cached_health = None
        self._last_health_check = 0.0
        self._health_check_cooldown = 15.0 # Check health every 15s max
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Lazy-init a reusable aiohttp session to avoid per-request TCP overhead."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self._session

    async def close(self):
        """Gracefully close the underlying HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def is_healthy(self) -> bool:
        now = time.time()
        if self._cached_health is not None and (now - self._last_health_check) < self._health_check_cooldown:
            return self._cached_health

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=1.5)) as session:
                async with session.get(f"{self.base_url}/api/tags") as resp:
                    is_ok = (resp.status == 200)
                    self._cached_health = is_ok
                    self._last_health_check = now
                    return is_ok
        except Exception:
            self._cached_health = False
            self._last_health_check = now
            return False

    async def generate_structured(self, request: LLMRequest) -> LLMResponse:
        url = f"{self.base_url}/api/chat"
        
        # Inject structural instructions ensuring strict compliance
        schema_guidance = (
            "Output your entire decision strictly as a single raw, valid JSON object matching this schema exactly:\n"
            "{\n"
            '  "intent": "string (classified core task)",\n'
            '  "confidence": float (0.0 to 1.0),\n'
            '  "requires_tool": boolean,\n'
            '  "tool_name": "string (name of targeted skill or null)",\n'
            '  "tool_args": { "arg_name": "value" },\n'
            '  "response": "string (your actual short, direct spoken reply to Master adopting your Jarvis executive persona exactly)",\n'
            '  "escalate": boolean (true if complexity requires external high-end reasoning)\n'
            "}\n"
            "CRITICAL: Do NOT wrap the JSON in markdown code blocks (e.g. ```json). Do NOT add conversational intro or outro text. Return ONLY the raw literal JSON string starting with { and ending with }."
        )

        if request.available_tools:
            tool_defs = []
            for t in request.available_tools:
                tool_defs.append(f"- {t.name}: {t.description}")
            schema_guidance += "\n\nAvailable Tools:\n" + "\n".join(tool_defs)

        system_content = schema_guidance if request.require_structured else ""
        
        messages = []
        # Compile existing historical context, merging system instructions cleanly
        for msg in request.history:
            if msg.role == "system":
                # Combine identity context directly with structural guidance
                system_content = f"{msg.content}\n\n{system_content}".strip()
            else:
                messages.append({"role": msg.role, "content": msg.content})
                
        if system_content:
            messages.insert(0, {"role": "system", "content": system_content})

        # NOTE: The user message is already present in request.history (appended by the router).
        # Do NOT re-append request.prompt here to avoid duplicate user messages.

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.4, # Balanced warmth for persona fidelity alongside reliable format constraints
                "num_ctx": 8192    # Expanded window prevents buffer overflows and repetitive hallucination loops
            }
        }
        
        # Append tool declarations if native execution wrappers are active
        if request.available_tools and self.supports_tools:
            tools_mapped = []
            for t in request.available_tools:
                tools_mapped.append({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": {
                            "type": "object",
                            "properties": t.parameters,
                            "required": t.required
                        }
                    }
                })
            payload["tools"] = tools_mapped

        session = await self._get_session()
        last_error = None
        attempts_left = llm_config.LOCAL_MAX_RETRIES
        attempt = 0
        while attempt < attempts_left:
            attempt += 1
            try:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        err_text = await resp.text()
                        if resp.status == 400 and "does not support tools" in err_text and "tools" in payload:
                            logger.info("Discovered local model does not natively support tools. Caching state and retrying payload gracefully...")
                            self.supports_tools = False
                            payload.pop("tools")
                            attempts_left += 1  # Don't count tool strip attempt against limit
                            continue
                        logger.error(f"Local core REST rejection ({resp.status}): {err_text}")
                        raise RuntimeError(f"Ollama execution error: {resp.status}")
                    
                    data = await resp.json()
                    raw_text = data.get("message", {}).get("content", "")
                    self._cached_health = True
                    
                    # Extract tools if returned directly by Ollama format
                    tool_calls = data.get("message", {}).get("tool_calls", [])
                    if tool_calls and not raw_text:
                        # Project native function response directly into AUHIP structure
                        call = tool_calls[0]["function"]
                        return LLMResponse(
                            intent=call["name"],
                            confidence=0.95,
                            requires_tool=True,
                            tool_name=call["name"],
                            tool_args=call.get("arguments", {}),
                            response=f"Executing {call['name']}...",
                            escalate=False,
                            raw_response=json.dumps(data),
                            provider_used="local"
                        )

                    return ResponseParser.parse_structured(raw_text, provider="local")

            except asyncio.TimeoutError:
                last_error = "Execution timed out."
                logger.warning(f"Ollama runtime stall on attempt {attempt}. Retrying...")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Ollama connection error on attempt {attempt}: {e}")
                await asyncio.sleep(0.2)

        # Total local core failure triggers escalation hook flag safely
        self._cached_health = False
        logger.error(f"Local primary model failed after {llm_config.LOCAL_MAX_RETRIES} attempts. Triggering cloud fallback.")
        return LLMResponse(
            intent="error",
            confidence=0.0,
            requires_tool=False,
            tool_name=None,
            tool_args={},
            response="Neural execution timed out.",
            escalate=True, # Escalate safely to ensure seamless continuity
            raw_response=str(last_error),
            provider_used="local"
        )


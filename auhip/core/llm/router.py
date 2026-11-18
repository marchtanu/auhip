import asyncio
import json
import logging
import os
from typing import Dict, Any, Optional, List

from auhip.core.llm.base import BaseLLMProvider
from auhip.core.llm.cloud_model import GeminiProvider
from auhip.core.llm.context_manager import ContextManager
from auhip.core.llm.local_model import OllamaProvider
from auhip.core.llm.prompt_builder import PromptBuilder
from auhip.core.llm.tool_manager import ToolManager
from auhip.core.llm.tool_selection import select_relevant_tools
from auhip.core.llm.types import LLMRequest, LLMResponse, Message, ToolSchema

logger = logging.getLogger(__name__)


class HybridLLMRouter:
    """
    Central production-grade asynchronous routing engine orchestrating local-first neural
    execution, tool encapsulation, context pruning, and automated fallback escalation logic.
    """

    def __init__(self, tool_manager: ToolManager, context_manager: ContextManager):
        self.tool_manager = tool_manager
        self.context_manager = context_manager

        # Swappable neural backend adapters
        self.local_provider: BaseLLMProvider = OllamaProvider()
        self.cloud_provider: BaseLLMProvider = GeminiProvider()

        # Cloud escalation gate — set CLOUD_ENABLED=false in .env to run fully local
        self.cloud_enabled: bool = os.getenv("CLOUD_ENABLED", "false").strip().lower() in ("true", "1", "yes")

        self.current_mode: str = "VOICE_MODE"
        if not self.cloud_enabled:
            logger.info("[Router] CLOUD_ENABLED=false — running in local-only mode. Cloud escalation disabled.")

    def set_mode(self, mode: str):
        """Update current operational machine context tracking."""
        self.current_mode = mode
        # Refresh the system message in the context window so the LLM
        # always sees the current execution state.
        sys_text = PromptBuilder.build_system_prompt(mode)
        self.context_manager.refresh_system_message(sys_text)
        logger.debug(f"Hybrid router execution context transitioned to: {mode}")

    async def close(self):
        """Gracefully close provider HTTP sessions."""
        for provider in (self.local_provider, self.cloud_provider):
            if hasattr(provider, "close"):
                await provider.close()

    @staticmethod
    def cloud_was_explicitly_requested(prompt: str) -> bool:
        """Cloud use requires a direct user instruction for this specific request."""
        normalized = " ".join(prompt.lower().split())
        cues = (
            "use gemini", "ask gemini", "send to gemini", "send this to gemini",
            "use cloud", "ask the cloud", "use the cloud", "use online model",
        )
        negations = ("don't", "do not", "never", "avoid", "without", "not")
        for cue in cues:
            start = 0
            while (index := normalized.find(cue, start)) >= 0:
                prefix = normalized[max(0, index - 24):index]
                if not any(negation in prefix for negation in negations):
                    return True
                start = index + len(cue)
        return False

    async def generate_json(
        self,
        prompt: str,
        schemas: Optional[List[dict]] = None,
        allow_cloud: bool = False,
    ) -> str:
        """
        Generates structured JSON directly using the local or cloud model.
        Used by PlannerAgent for Acyclic Action Graph synthesis.
        """
        req = LLMRequest(
            prompt=prompt,
            history=[Message(role="user", content=prompt)],
            available_tools=select_relevant_tools(
                prompt,
                schemas if schemas is not None else self.tool_manager.get_schemas(),
            ),
            require_structured=True
        )
        if allow_cloud and not self.cloud_enabled:
            return ""

        if allow_cloud:
            cloud_request = LLMRequest(
                prompt=prompt,
                history=[Message(role="user", content=prompt)],
                available_tools=req.available_tools,
                require_structured=True,
            )
            if await self.cloud_provider.is_healthy():
                resp = await self.cloud_provider.generate_structured(cloud_request)
                if resp and resp.intent != "error":
                    return resp.response
            return ""

        if await self.local_provider.is_healthy():
            resp = await self.local_provider.generate_structured(req)
            if resp and resp.intent != "error":
                return resp.response

        # An empty result makes the planner stop; guessed fallback actions are unsafe.
        return ""

    async def execute(self, user_text: str) -> str:
        """
        Orchestrates an end-to-end command request. Prioritizes local engine inference,
        triggers sandboxed internal tool execution, and falls back to cloud providers safely.
        """
        from auhip.core.agents.memory import memory_agent

        prompt = user_text.strip()
        if not prompt:
            return ""

        logger.info(f"Dispatching intent processing for prompt: '{prompt}'")

        self.context_manager.append(Message(role="user", content=prompt))
        memory_agent.add_session_message("user", prompt)
        relevant_tools = select_relevant_tools(prompt, self.tool_manager.get_schemas())
        cloud_requested = self.cloud_was_explicitly_requested(prompt)

        if cloud_requested and not self.cloud_enabled:
            response_text = (
                "Cloud access is disabled. No prompt was sent outside AUHIP. Enable CLOUD_ENABLED "
                "only if you want to allow an explicitly requested cloud task."
            )
            self.context_manager.append(Message(role="assistant", content=response_text))
            memory_agent.add_session_message("assistant", response_text)
            return response_text

        if cloud_requested:
            # This explicit one-shot consent sends only the current prompt, not saved memories,
            # identity files, or earlier turns.
            cloud_request = LLMRequest(
                prompt=prompt,
                history=[Message(role="user", content=prompt)],
                available_tools=relevant_tools,
                require_structured=True,
            )
            if not await self.cloud_provider.is_healthy():
                return "The explicitly requested cloud provider is unavailable. The prompt was not sent; ask me to try locally instead."
            response = await self.cloud_provider.generate_structured(cloud_request)
        else:
            sys_text = PromptBuilder.build_system_prompt(self.current_mode)
            try:
                memories = await memory_agent.search_memory(prompt, limit=5)
                memory_lines = [
                    f"[{item['memory_type']} | {item['source']} | confidence {item['confidence']:.2f}] {item['text']}"
                    for item in memories
                ]
                if memory_lines:
                    sys_text += "\nRelevant curated local memories (use only when applicable):\n" + "\n".join(memory_lines)
            except Exception:
                logger.exception("Curated memory retrieval failed; continuing without recalled memories.")

            self.context_manager.refresh_system_message(sys_text)
            local_request = LLMRequest(
                prompt=prompt,
                history=self.context_manager.get_context(),
                available_tools=relevant_tools,
                require_structured=True,
            )
            response: Optional[LLMResponse] = None
            if await self.local_provider.is_healthy():
                response = await self.local_provider.generate_structured(local_request)
            else:
                logger.warning("Local model unavailable. Cloud fallback requires an explicit user request.")

        # Safety catchall for total neural connection failure
        if not response or response.intent == "error":
            if cloud_requested:
                return "The explicitly requested cloud request failed. It was not retried locally; you can ask me to retry locally."
            return (
                "I'm unable to reach the local AI engine (Ollama). Cloud access was not used. "
                "Please ensure Ollama is running ('ollama serve') or explicitly ask for an enabled cloud provider."
            )

        logger.info(f"Finalized structural resolution: Intent='{response.intent}', Confidence={response.confidence:.2f}, Tool={response.tool_name}")

        # 5. Layer 2 — Execute declared tool safely if requested
        final_answer = response.response
        if response.requires_tool and response.tool_name:
            available_tool_names = {schema.name for schema in relevant_tools}
            if response.tool_name not in available_tool_names:
                logger.warning("Model requested unavailable tool '%s'; refusing the call.", response.tool_name)
                return "I couldn't safely match that request to an available action. Please rephrase it."
            # Preserve deterministic tool intent inside conversational flow context
            self.context_manager.append(Message(role="assistant", content=f"Triggering skill: {response.tool_name}"))

            tool_result = await self.tool_manager.execute(response.tool_name, response.tool_args)

            # Append isolated tool result directly into interaction buffers
            res_str = str(tool_result)
            self.context_manager.append(Message(role="tool", content=res_str, name=response.tool_name))

            # Cleanly merge text returns to optimize user responsiveness feedback
            if not final_answer or final_answer in ("Executing tool...", "Searching web..."):
                final_answer = res_str
            else:
                final_answer = f"{final_answer} Result: {res_str}"
        else:
            # Record final pure language message context directly
            if final_answer:
                self.context_manager.append(Message(role="assistant", content=final_answer))

        result_text = final_answer.strip() if (final_answer and final_answer.strip()) else "I'm listening, sir. How can I assist you?"
        memory_agent.add_session_message("assistant", result_text)

        return result_text



import json
import logging
import re
from typing import Dict, Any, Optional
from auhip.core.llm.types import LLMResponse

logger = logging.getLogger(__name__)

# Heuristic keyword → (intent, tool_name) mapping for broken JSON fallback.
# Ordered longest-match-first within each group; checked top-down.
_HEURISTIC_TOOL_MAP = [
    # Parameterised tools (need argument extraction)
    (["search for", "search google", "google"],  "search_web",    "search_web"),
    (["search youtube music", "play music"],      "search_youtube_music", "search_youtube_music"),
    (["set timer", "set a timer", "countdown"],   "set_timer",     "set_timer"),
    (["weather in", "forecast for", "weather"],   "get_weather",   "get_weather"),
    (["stock price", "lookup stock", "stock"],     "lookup_stock",  "lookup_stock"),
    (["open app", "launch", "open notepad", "open calculator"], "open_app", "open_app"),
    # Parameterless tools
    (["what time", "tell time", "current time"],  "tell_time",     "tell_time"),
    (["what date", "today", "tell date"],         "tell_date",     "tell_date"),
    (["volume up"],                               "volume_up",     "volume_up"),
    (["volume down"],                             "volume_down",   "volume_down"),
    (["mute"],                                    "mute_volume",   "mute_volume"),
    (["screenshot", "capture screen"],            "take_screenshot", "take_screenshot"),
    (["system status", "cpu", "ram"],             "system_status", "system_status"),
    (["help", "commands"],                        "get_help",      "get_help"),
    (["play pause", "media pause", "pause music"],"media_play_pause", "media_play_pause"),
    (["next track", "skip track", "next song"],   "media_next_track", "media_next_track"),
    (["prev track", "previous track"],            "media_prev_track", "media_prev_track"),
    (["youtube music", "open music"],             "open_youtube_music", "open_youtube_music"),
    (["sleep", "goodbye", "goodnight"],           "sleep_mode",    "sleep_mode"),
]


class ResponseParser:
    """
    Robust JSON extraction engine capable of stripping markdown fenced wrappers,
    repairing syntax errors, and projecting natural text fallback into valid structs.
    """

    @staticmethod
    def parse_structured(raw_text: str, provider: str = "local") -> LLMResponse:
        text = raw_text.strip()
        
        # 1. Try stripping code blocks if model wrapped the JSON
        if "```" in text:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if match:
                text = match.group(1).strip()
            else:
                # Fallback: remove all triple backtick markers manually
                text = re.sub(r"```[a-z]*", "", text).strip()

        # 1b. Locate the outermost JSON block via index scanning if nested inside unstructured dialogue
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            text = text[start_idx:end_idx+1].strip()
            # Clean common syntax errors introduced by smaller quantized local models
            text = re.sub(r"//.*", "", text)  # Strip inline double-slash comments
            text = re.sub(r",\s*\}", "}", text)  # Strip trailing commas in objects
            text = re.sub(r",\s*\]", "]", text)  # Strip trailing commas in arrays

        # 2. Attempt raw JSON validation
        try:
            data = json.loads(text)
            return LLMResponse(
                intent=data.get("intent", "chat"),
                confidence=float(data.get("confidence", 1.0)),
                requires_tool=bool(data.get("requires_tool", False)),
                tool_name=data.get("tool_name"),
                tool_args=data.get("tool_args", {}),
                response=data.get("response", ""),
                escalate=bool(data.get("escalate", False)),
                raw_response=raw_text,
                provider_used=provider
            )
        except json.JSONDecodeError as e:
            logger.warning(f"Malformed structured JSON received from {provider}: {e}. Extracted segment: {text!r}. Activating heuristic projection.")
            
            # ── Heuristic intent extraction for broken responses ─────────
            intent = "chat"
            requires_tool = False
            tool_name = None
            tool_args = {}
            escalate = False
            
            lower_text = text.lower()

            # Check explicit escalation signals
            if "complex" in lower_text or "escalate" in lower_text:
                escalate = True

            # Walk the heuristic map to find the best matching tool intent
            for keywords, mapped_intent, mapped_tool in _HEURISTIC_TOOL_MAP:
                if any(kw in lower_text for kw in keywords):
                    intent = mapped_intent
                    requires_tool = True
                    tool_name = mapped_tool

                    # Extract argument for parameterised tools
                    if mapped_tool == "search_web":
                        for marker in ["search for", "search", "google"]:
                            if marker in lower_text:
                                query = text[lower_text.find(marker) + len(marker):].strip()
                                tool_args = {"query": query if query else "latest news"}
                                break
                    elif mapped_tool == "get_weather":
                        for marker in ["weather in", "forecast for"]:
                            if marker in lower_text:
                                tool_args = {"city": text[lower_text.find(marker) + len(marker):].strip()}
                                break
                    elif mapped_tool == "set_timer":
                        for marker in ["set a timer for", "set timer for", "timer for", "timer"]:
                            if marker in lower_text:
                                tool_args = {"duration_str": text[lower_text.find(marker) + len(marker):].strip()}
                                break
                    elif mapped_tool == "lookup_stock":
                        for marker in ["stock price", "lookup stock", "stock"]:
                            if marker in lower_text:
                                tool_args = {"ticker": text[lower_text.find(marker) + len(marker):].strip()}
                                break
                    break  # Use first match
                
            # Attempt regex extraction of the response property string if JSON parsing crashed
            fallback_response = raw_text.strip()
            resp_match = re.search(r'"response"\s*:\s*"((?:[^"\\]|\\.)*)"', raw_text, re.DOTALL)
            if resp_match:
                try:
                    fallback_response = resp_match.group(1).encode().decode('unicode_escape')
                except Exception:
                    fallback_response = resp_match.group(1)
            else:
                # Clean up wrapping markdown formatting if returning plain text buffer directly
                fallback_response = re.sub(r"```[a-z]*", "", raw_text).strip()

            return LLMResponse(
                intent=intent,
                confidence=0.5, # Low confidence ensures proper safety escalation checking
                requires_tool=requires_tool,
                tool_name=tool_name,
                tool_args=tool_args,
                response=fallback_response,
                escalate=escalate,
                raw_response=raw_text,
                provider_used=provider
            )


"""Small, deterministic tool shortlist for local models with limited context."""

from __future__ import annotations

import re
from typing import Any

_WORD = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "can", "could", "did", "do",
    "does", "for", "from", "get", "give", "how", "i", "in", "is", "it", "me", "my", "of",
    "on", "or", "please", "tell", "that", "the", "this", "to", "was", "what", "when", "where",
    "which", "who", "why", "with", "would", "you", "your",
}
_TOOL_TERMS: dict[str, set[str]] = {
    "remember_user_memory": {"remember", "memory", "fact", "preference", "decide", "decision", "project"},
    "search_user_memories": {"memory", "remember", "fact", "preference", "decide", "decision", "decided", "project"},
    "list_user_memories": {"memory", "remember", "list", "show", "saved"},
    "correct_user_memory": {"correct", "update", "edit", "fix", "memory", "remember"},
    "forget_user_memory": {"forget", "delete", "remove", "memory", "remember"},
    "search_conversation_history": {"conversation", "history", "chat", "remember", "past"},
    "search_agent_task_history": {"task", "receipt", "delegated", "agent", "work", "history", "completed"},
    "search_second_brain": {"second", "brain", "notes", "document", "coursework", "assignment", "deadline", "syllabus"},
    "get_university_deadlines": {"coursework", "assignment", "deadline", "exam", "due", "university"},
    "send_to_antigravity": {"antigravity", "delegate", "coding", "code", "implement", "refactor", "build"},
    "search_codebase": {"code", "search", "find", "pattern", "source"},
    "list_workspace_files": {"workspace", "file", "directory", "folder"},
    "view_directory_tree": {"tree", "directory", "folder", "structure"},
    "search_web": {"web", "internet", "google", "online", "search"},
    "get_weather": {"weather", "forecast", "temperature"},
    "tell_time": {"time", "clock"},
    "tell_date": {"date", "today", "calendar"},
    "set_timer": {"timer", "countdown", "remind"},
    "add_task": {"task", "todo", "remind", "add"},
    "list_tasks": {"task", "todo", "list", "show"},
    "complete_task": {"task", "todo", "complete", "finish"},
    "add_calendar_event": {"calendar", "event", "schedule", "meeting"},
    "list_calendar_events": {"calendar", "event", "schedule", "meeting", "upcoming"},
    "get_acting_call_time": {"acting", "call", "shoot", "filming", "production"},
    "get_financial_status": {"finance", "money", "revenue", "invoice", "payment"},
    "get_startup_sprint": {"startup", "sprint", "stagelink", "blackbox"},
    "sync_workspace": {"sync", "synchronize", "workspace", "moodle"},
    "summarize_notebook": {"notebook", "summarize", "summary", "briefing"},
    "write_code_file": {"write", "create", "file", "code"},
    "patch_file": {"patch", "edit", "modify", "file", "code"},
    "delete_file": {"delete", "remove", "file"},
    "run_powershell_guarded": {"powershell", "command", "shell", "terminal"},
    "open_app": {"open", "launch", "application", "app"},
    "open_browser": {"browser", "open", "web"},
    "system_status": {"system", "status", "cpu", "ram", "memory"},
    "volume_up": {"volume", "louder", "increase"},
    "volume_down": {"volume", "quieter", "decrease"},
    "mute_volume": {"mute", "silence", "volume"},
    "take_screenshot": {"screenshot", "screen", "capture"},
    "open_youtube_music": {"youtube", "music", "player"},
    "search_youtube_music": {"youtube", "music", "song", "play"},
    "media_play_pause": {"media", "play", "pause", "music"},
    "media_next_track": {"next", "track", "song", "music"},
    "media_prev_track": {"previous", "track", "song", "music"},
}


def _terms(value: str) -> set[str]:
    result = set()
    for word in _WORD.findall(value.lower()):
        if word in _STOP_WORDS:
            continue
        if len(word) > 4 and word.endswith("ies"):
            word = word[:-3] + "y"
        elif len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]
        result.add(word)
    return result


def select_relevant_tools(prompt: str, available_tools: list[Any], limit: int = 7) -> list[Any]:
    """Rank tool names/descriptions plus task aliases and return only useful candidates."""
    query_terms = _terms(prompt)
    if not query_terms:
        return []
    ranked: list[tuple[float, int, Any]] = []
    for index, schema in enumerate(available_tools):
        name = schema.name if hasattr(schema, "name") else str(schema.get("name", ""))
        description = schema.description if hasattr(schema, "description") else str(schema.get("description", ""))
        name_terms = _terms(name.replace("_", " "))
        description_terms = _terms(description)
        aliases = _TOOL_TERMS.get(name, set())
        name_hits = query_terms & name_terms
        description_hits = query_terms & description_terms
        alias_hits = query_terms & aliases
        score = len(name_hits) * 3.0 + len(alias_hits) * 1.5 + len(description_hits)
        if score > 0:
            ranked.append((score, index, schema))
    ranked.sort(key=lambda entry: (-entry[0], entry[1]))
    return [entry[2] for entry in ranked[:max(1, limit)]]

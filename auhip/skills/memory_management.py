"""Explicit user controls for durable personal memories."""

from typing import Any

from auhip.core.agents.memory import memory_agent


def _format_memory(record: dict[str, Any]) -> str:
    return (
        f"[{record['memory_id']}] ({record['memory_type']}, {record['created_at'][:10]}, "
        f"confidence {record['confidence']:.2f}, "
        f"source: {record['source']}) {record['text']}"
    )


async def remember_user_memory(text: str, memory_type: str = "fact") -> str:
    """Save an explicitly stated fact, preference, decision, or project detail locally."""
    record = await memory_agent.remember(text, memory_type=memory_type, source="user", confidence=1.0)
    return f"Saved local {record['memory_type']} memory. {_format_memory(record)}"


async def search_user_memories(query: str) -> str:
    """Search curated local facts, preferences, decisions, and project memories."""
    results = await memory_agent.search_memory(query, limit=5)
    if not results:
        return "No sufficiently relevant curated memory was found."
    return "Relevant local memories:\n" + "\n".join(_format_memory(record) for record in results)


async def list_user_memories(memory_type: str = "") -> str:
    """List saved durable memories so the user can inspect their IDs and sources."""
    results = memory_agent.list_memories(memory_type=memory_type, limit=30)
    if not results:
        return "No saved memories found."
    return "Saved local memories:\n" + "\n".join(_format_memory(record) for record in results)


async def correct_user_memory(memory_id: str, text: str, memory_type: str = "") -> str:
    """Correct the text or category of a previously saved memory by its ID."""
    record = await memory_agent.correct(memory_id, text, memory_type=memory_type or None)
    return f"Updated local memory. {_format_memory(record)}"


async def forget_user_memory(memory_id: str) -> str:
    """Permanently delete a saved memory by its ID."""
    if not await memory_agent.forget(memory_id):
        return "No saved memory has that ID."
    return f"Deleted local memory {memory_id}."


async def search_conversation_history(query: str) -> str:
    """Search legacy conversation summaries separately from curated personal memories."""
    results = await memory_agent.search_history(query, limit=5)
    if not results:
        return "No matching archived conversation history was found. New conversations are not saved as durable memories."
    return "Archived local conversation history (not curated memories):\n" + "\n".join(
        _format_memory(record) for record in results
    )

"""Read local AUHIP task receipts as a source distinct from personal memory."""

from __future__ import annotations

from datetime import datetime
import json
import logging
import os
from pathlib import Path
import re
from typing import Any

logger = logging.getLogger(__name__)
_WORD = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_STOP_WORDS = {"a", "an", "and", "are", "at", "did", "do", "for", "from", "how", "i", "in", "is", "it", "me", "my", "of", "on", "or", "the", "this", "to", "was", "what", "when", "where", "who", "with", "you"}


def _receipt_directory() -> Path:
    configured = os.getenv("AUHIP_HANDOFF_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[2] / ".auhip" / "handoff"


def _tokens(text: str) -> set[str]:
    tokens = set()
    for token in _WORD.findall(text.lower()):
        if len(token) > 4 and token.endswith("ies"):
            token = token[:-3] + "y"
        elif len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
            token = token[:-1]
        if token not in _STOP_WORDS and len(token) > 1:
            tokens.add(token)
    return tokens


def _receipt_text(receipt: dict[str, Any]) -> str:
    values = [receipt.get("summary", "")]
    for key in ("files_changed", "checks", "follow_up"):
        entries = receipt.get(key, [])
        if isinstance(entries, list):
            values.extend(entries[:100])
    return " ".join(str(value)[:2000] for value in values if isinstance(value, (str, int, float)))[:20000]


async def search_agent_task_history(query: str = "") -> str:
    """Search AUHIP handoff receipts without mixing them into personal-memory recall."""
    directory = _receipt_directory()
    if not directory.is_dir():
        return "No AUHIP task receipts have been saved yet."

    query_terms = _tokens(query)
    receipts: list[tuple[float, dict[str, Any]]] = []
    try:
        paths = sorted(directory.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)[:500]
    except OSError:
        logger.exception("Could not list local AUHIP task receipts.")
        return "AUHIP task history is unavailable right now."

    for path in paths:
        try:
            with path.open("r", encoding="utf-8") as receipt_file:
                receipt = json.load(receipt_file)
            if not isinstance(receipt, dict):
                continue
            text = _receipt_text(receipt)
            receipt_terms = _tokens(text)
            overlap = len(query_terms & receipt_terms)
            if query_terms and overlap == 0:
                continue
            recency = path.stat().st_mtime
            relevance = overlap / max(len(query_terms), 1)
            score = relevance * 100 + recency / 1e12
            receipt["task_id"] = str(receipt.get("task_id") or path.stem)
            receipt["reported_at"] = str(receipt.get("reported_at") or datetime.fromtimestamp(recency).isoformat())
            receipts.append((score, receipt))
        except (OSError, json.JSONDecodeError, TypeError):
            logger.warning("Skipping malformed task receipt %s.", path.name)

    receipts.sort(key=lambda item: item[0], reverse=True)
    if not receipts:
        return "No matching AUHIP task receipts were found."

    formatted = []
    for _, receipt in receipts[:5]:
        files = ", ".join(str(path) for path in receipt.get("files_changed", [])) or "none reported"
        checks = "; ".join(str(check) for check in receipt.get("checks", [])) or "none reported"
        follow_up = "; ".join(str(item) for item in receipt.get("follow_up", [])) or "none"
        formatted.append(
            f"[{receipt['task_id']}] {receipt.get('status', 'unknown')} — {receipt['reported_at']}\n"
            f"Summary: {receipt.get('summary', 'No summary')}\n"
            f"Files: {files}\nChecks: {checks}\nFollow-up: {follow_up}"
        )
    return "Local AUHIP task history (handoff receipts):\n" + "\n\n".join(formatted)

"""Create durable coding-agent receipts and notify a running AUHIP instance."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any

TASK_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
MAX_NOTIFICATION_LENGTH = 500


def get_handoff_directory() -> Path:
    configured_directory = os.getenv("AUHIP_HANDOFF_DIR")
    if configured_directory:
        return Path(configured_directory).expanduser().resolve()
    repository_root = Path(__file__).resolve().parents[2]
    return repository_root / ".auhip" / "handoff"


def validate_task_id(task_id: str) -> str:
    normalized = task_id.strip()
    if not TASK_ID_PATTERN.fullmatch(normalized):
        raise ValueError("Task ID must contain only letters, numbers, dots, underscores, or hyphens.")
    return normalized


def write_receipt(payload: dict[str, Any]) -> Path:
    handoff_directory = get_handoff_directory()
    handoff_directory.mkdir(parents=True, exist_ok=True)
    destination = handoff_directory / f"{payload['task_id']}.json"
    if destination.exists():
        raise FileExistsError(f"A receipt already exists for task {payload['task_id']}.")

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{payload['task_id']}.", suffix=".tmp", dir=handoff_directory
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as receipt_file:
            json.dump(payload, receipt_file, ensure_ascii=False, indent=2)
            receipt_file.write("\n")
        os.link(temporary_name, destination)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
    return destination


def format_announcement(status: str, summary: str) -> str:
    clean_summary = " ".join(summary.split())
    announcement = f"Delegated task {status}: {clean_summary}"
    return announcement[:MAX_NOTIFICATION_LENGTH]


async def notify_auhip(text: str, task_id: str | None = None) -> bool:
    try:
        import websockets
    except ImportError:
        return False

    uri = os.getenv("AUHIP_IPC_URI", "ws://127.0.0.1:8765")
    request = {
        "type": "AUHIP_NOTIFY",
        "payload": {"text": text[:MAX_NOTIFICATION_LENGTH], "task_id": task_id},
    }
    try:
        async with websockets.connect(uri, open_timeout=1.5, close_timeout=1.0) as socket:
            await socket.send(json.dumps(request, ensure_ascii=False))
            loop = asyncio.get_running_loop()
            deadline = loop.time() + 2.0
            while loop.time() < deadline:
                message = await asyncio.wait_for(socket.recv(), timeout=deadline - loop.time())
                acknowledgement = json.loads(message)
                if "ok" in acknowledgement:
                    return bool(acknowledgement["ok"])
            return False
    except Exception:
        return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send a local completion notice to AUHIP.")
    subparsers = parser.add_subparsers(dest="action", required=True)

    complete_parser = subparsers.add_parser("complete", help="Save a task receipt and announce it to AUHIP.")
    complete_parser.add_argument("--task-id", required=True)
    complete_parser.add_argument("--status", required=True, choices=("completed", "blocked"))
    complete_parser.add_argument("--summary", required=True)
    complete_parser.add_argument("--file", action="append", default=[])
    complete_parser.add_argument("--check", action="append", default=[])
    complete_parser.add_argument("--follow-up", action="append", default=[])

    notify_parser = subparsers.add_parser("speak", help="Ask a running AUHIP instance to speak a short message.")
    notify_parser.add_argument("--text", required=True)
    return parser


async def run_cli(args: argparse.Namespace) -> int:
    if args.action == "speak":
        sent = await notify_auhip(args.text)
        if sent:
            print("AUHIP accepted the message.")
            return 0
        print("AUHIP is not running or did not accept the message.", file=sys.stderr)
        return 2

    try:
        task_id = validate_task_id(args.task_id)
        summary = " ".join(args.summary.split())
        if not summary:
            raise ValueError("Summary cannot be empty.")
        receipt = {
            "schema_version": 1,
            "task_id": task_id,
            "status": args.status,
            "summary": summary,
            "files_changed": args.file,
            "checks": args.check,
            "follow_up": args.follow_up,
            "reported_at": datetime.now(timezone.utc).isoformat(),
        }
        path = write_receipt(receipt)
    except (ValueError, FileExistsError, OSError) as error:
        print(f"Could not save AUHIP receipt: {error}", file=sys.stderr)
        return 1

    print(f"Saved AUHIP receipt: {path}")
    announcement = format_announcement(args.status, summary)
    if await notify_auhip(announcement, task_id):
        print("AUHIP accepted the completion notice.")
    else:
        print("Receipt saved; AUHIP is not running or did not accept the notice.")
    return 0


def main() -> int:
    return asyncio.run(run_cli(build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())

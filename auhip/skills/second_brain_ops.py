"""
AUHIP Second Brain Operations Skill.
Connects AUHIP directly to March's Second Brain & Single Source of Truth (march_workspace).
Provides voice commands and agent tools for:
  - Synchronizing Moodle & workspace databases
  - Checking Me Mind Y acting queues and call times
  - Reporting Mahidol ICT university coursework deadlines & exams
  - Reporting freelance cash flow and client deliverables
  - Inspecting startup sprints (StageLink & BlackBox)
  - Searching documents across the Second Brain
"""

import logging
import asyncio
from typing import Dict, Any, Optional

from auhip.core.second_brain import second_brain

logger = logging.getLogger(__name__)


async def sync_workspace() -> str:
    """
    Executes the master workspace synchronization pipeline in march_workspace.
    Connects to Chrome CDP (port 9222) to scrape Mahidol Moodle, check Me Mind Y clashes,
    and recalibrate flat JSON databases.
    """
    logger.info("SKILL: sync_workspace triggered.")
    success, output = await second_brain.trigger_workspace_sync()
    if success:
        # Fetch fresh academic metrics for briefing
        academic = second_brain.get_academic_status()
        due_soon = academic.get("due_soon_count", 0)
        overdue = academic.get("overdue_count", 0)
        return (
            f"Workspace synchronized successfully, Sir. "
            f"Analyzed {academic.get('total_courses', 0)} courses: "
            f"{due_soon} items due this week, {overdue} overdue items. All databases updated."
        )
    else:
        return f"Workspace synchronization encountered an issue: {output[:200]}"


async def get_acting_call_time() -> str:
    """
    Retrieves the next Me Mind Y studio filming queue, call time, location, and conflicts.
    """
    logger.info("SKILL: get_acting_call_time triggered.")
    queue = second_brain.get_next_acting_queue()
    if not queue:
        return "No upcoming acting queues found in the schedule, Sir."

    title = queue.get("title", "Production")
    call_time = queue.get("callTime", "TBD")
    date_str = queue.get("date", "Upcoming")
    location = queue.get("location", "Studio")
    conflicts = queue.get("conflictsWith", [])

    conflict_msg = ""
    if conflicts:
        conflict_msg = f" Warning: Date clashes with {', '.join(conflicts)}."

    return (
        f"Your next acting call for '{title}' is at {call_time} on {date_str} at {location}.{conflict_msg}"
    )


async def get_university_deadlines() -> str:
    """
    Reports upcoming Mahidol ICT coursework deadlines, overdue counts, and next assignments.
    """
    logger.info("SKILL: get_university_deadlines triggered.")
    status = second_brain.get_academic_status()
    total_courses = status.get("total_courses", 0)
    due_soon_count = status.get("due_soon_count", 0)
    overdue_count = status.get("overdue_count", 0)
    next_deadline = status.get("next_deadline")

    next_msg = ""
    if next_deadline:
        c_code = next_deadline.get("courseCode", "")
        name = next_deadline.get("name", "")
        due = next_deadline.get("dueDateFormatted") or next_deadline.get("dueDateRaw") or "Soon"
        next_msg = f" Next closest submission: [{c_code}] {name}, due {due}."

    return (
        f"Academic status: {total_courses} courses tracked. "
        f"{due_soon_count} assignments due this week, and {overdue_count} overdue.{next_msg}"
    )


async def get_financial_status() -> str:
    """
    Reports freelance income progress toward the monthly ฿75k goal and active client contracts.
    """
    logger.info("SKILL: get_financial_status triggered.")
    fin = second_brain.get_freelance_status()
    target = fin.get("monthly_target", 75000)
    paid = fin.get("total_paid", 0)
    pending = fin.get("total_pending", 0)
    pct = fin.get("progress_percent", 0)
    currency = fin.get("currency", "THB")
    active_count = fin.get("total_active", 0)

    return (
        f"Financial overview, Sir: Total revenue collected is {paid:,} {currency} against your {target:,} {currency} goal "
        f"({pct}% complete). Pending invoices: {pending:,} {currency}. {active_count} active contracts in progress."
    )


async def get_startup_sprint() -> str:
    """
    Reports the active sprint, completion percentage, and roadmap for startups (StageLink & BlackBox).
    """
    logger.info("SKILL: get_startup_sprint triggered.")
    startups = second_brain.get_startup_status()
    if not startups:
        return "No active startup records found in the Second Brain."

    summaries = []
    for s in startups:
        name = s.get("name", "Venture")
        sprint = s.get("currentSprint", "Active Sprint")
        pct = s.get("progressPercent", 0)
        target = s.get("targetLaunch", "Q4")
        summaries.append(f"{name}: {sprint} ({pct}% complete, launch target {target}).")

    return "Startup telemetry: " + " ".join(summaries)


async def search_second_brain(query: str = "") -> str:
    """
    Searches documents, syllabi, notes, and operations files across the Second Brain.
    """
    logger.info(f"SKILL: search_second_brain '{query}'.")
    if not query:
        return "Please specify what you would like me to search for in your Second Brain."

    matches = second_brain.search_notes(query, max_results=4)
    if not matches:
        return f"No matches found for '{query}' in the Second Brain."

    formatted = []
    for m in matches:
        formatted.append(f"[{m.get('source', 'personal_knowledge')} | {m['file']}#L{m['line']} | score {m.get('score', 0)}]: {m['snippet']}")

    return f"Found {len(matches)} reference(s) for '{query}':\n" + "\n".join(formatted)

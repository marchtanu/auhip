import os
import json
import logging
import asyncio
from collections import Counter
from datetime import datetime, date
import math
import re
from typing import Dict, Any, List, Optional, Tuple

from auhip.core.config import config

logger = logging.getLogger(__name__)
_SEARCH_WORDS = re.compile(r"[\w'-]+", re.UNICODE)
_SEARCH_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "did", "do", "does", "for",
    "from", "had", "has", "have", "how", "i", "in", "into", "is", "it", "me", "my", "of",
    "on", "or", "our", "please", "tell", "that", "the", "their", "them", "this", "to", "was",
    "we", "what", "when", "where", "which", "who", "why", "with", "you", "your",
}


class SecondBrainService:
    """
    SecondBrainService connects AUHIP directly to march_workspace (March's Second Brain & SSOT).
    Provides typed, non-blocking asynchronous access to:
      - Acting shooting queues & studio call times (data/acting.json)
      - Mahidol ICT Moodle coursework, deadlines & exams (university/semester_1_2026/)
      - Freelance client deliverables & cash flow (data/freelance.json)
      - Startup sprints for StageLink & BlackBox (data/startups.json)
      - Profile & professor registry for leave emails (data/profile.json)
      - Master sync automation execution (ai_tools/sync_workspace.py)
    """

    def __init__(self, root_path: Optional[str] = None):
        self.root_path = root_path or config.SECOND_BRAIN_PATH
        logger.info(f"SecondBrainService initialized pointing to: {self.root_path}")

    def _resolve(self, *parts: str) -> str:
        return os.path.normpath(os.path.join(self.root_path, *parts))

    def _load_json(self, rel_path: str, default: Any = None) -> Any:
        full_path = self._resolve(rel_path)
        if not os.path.exists(full_path):
            logger.warning(f"SecondBrain: File not found: {full_path}")
            return default
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"SecondBrain: Error reading {full_path}: {e}")
            return default

    # ── Profile & Identity ──────────────────────────────────────────────────

    def get_profile(self) -> Dict[str, Any]:
        """Returns March's profile including student ID, degree, agency, and professor contacts."""
        return self._load_json("data/profile.json", default={})

    # ── Acting & Call Times ─────────────────────────────────────────────────

    def get_acting_schedule(self, upcoming_only: bool = True) -> List[Dict[str, Any]]:
        """Returns acting queues from Me Mind Y Studio, sorted by date."""
        data = self._load_json("data/acting.json", default={})
        queues = data.get("queues", [])
        if not upcoming_only:
            return queues

        today_str = date.today().isoformat()
        upcoming = [q for q in queues if q.get("date", "9999-99-99") >= today_str]
        return sorted(upcoming, key=lambda x: x.get("date", ""))

    def get_next_acting_queue(self) -> Optional[Dict[str, Any]]:
        """Returns the immediate next acting queue or call time."""
        upcoming = self.get_acting_schedule(upcoming_only=True)
        return upcoming[0] if upcoming else None

    # ── Mahidol University & Coursework ──────────────────────────────────────

    def get_academic_status(self) -> Dict[str, Any]:
        """
        Calculates coursework deadline metrics and upcoming exams for Mahidol ICT.
        Returns total coursework count, overdue count, due soon count, and next urgent items.
        """
        # Try primary semester path, fallback to root university
        assignments_path = "university/semester_1_2026/assignments_data.json"
        raw_data = self._load_json(assignments_path)
        if raw_data is None:
            raw_data = self._load_json("university/assignments_data.json", default=[])

        all_items: List[Dict[str, Any]] = []
        unique_courses = set()

        if isinstance(raw_data, list):
            all_items = raw_data
            for it in all_items:
                c_code = it.get("courseCode") or it.get("course_code")
                if c_code:
                    unique_courses.add(c_code)
        elif isinstance(raw_data, dict):
            courses = raw_data.get("courses", {})
            for course_code, course_info in courses.items():
                unique_courses.add(course_code)
                for item in course_info.get("assignments", []):
                    item_copy = dict(item)
                    item_copy["courseCode"] = course_code
                    item_copy["courseName"] = course_info.get("name", course_code)
                    all_items.append(item_copy)

        overdue: List[Dict[str, Any]] = []
        due_soon: List[Dict[str, Any]] = []
        upcoming: List[Dict[str, Any]] = []

        now_ms = time.time() * 1000 if "time" in globals() else 0
        import time as _t
        now_ms = _t.time() * 1000

        for item in all_items:
            category = (item.get("category") or item.get("status") or "").upper()
            sub_status = (item.get("submissionStatusRaw") or "").lower()
            if "submitted" in sub_status:
                continue

            due_ts = item.get("dueTimestamp")

            if "OVERDUE" in category or (due_ts and due_ts < now_ms):
                overdue.append(item)
            elif "DUE_SOON" in category:
                due_soon.append(item)
                upcoming.append(item)
            else:
                upcoming.append(item)
                # If due within 7 days (7 * 86400 * 1000 ms)
                if due_ts and (0 <= (due_ts - now_ms) <= 7 * 86400 * 1000):
                    due_soon.append(item)

        # Sort upcoming by dueTimestamp if available
        def _sort_key(x):
            ts = x.get("dueTimestamp")
            return ts if ts else 9999999999999

        upcoming_sorted = sorted(upcoming, key=_sort_key)

        # Exam calendar
        exam_data = self._load_json("data/exam_calendar.json", default={})

        return {
            "total_courses": len(unique_courses),
            "total_assignments": len(all_items),
            "overdue_count": len(overdue),
            "due_soon_count": len(due_soon),
            "overdue_items": overdue,
            "due_soon_items": due_soon,
            "next_deadline": upcoming_sorted[0] if upcoming_sorted else None,
            "exams": exam_data.get("exams", []),
        }

    # ── Freelance & Cash Flow ────────────────────────────────────────────────

    def get_freelance_status(self) -> Dict[str, Any]:
        """Calculates revenue progress toward ฿75k monthly goal and active client contracts."""
        data = self._load_json("data/freelance.json", default={})
        target = data.get("monthlyTarget", 75000)
        projects = data.get("projects", [])

        total_paid = sum(p.get("paidAmount", 0) for p in projects)
        total_pending = sum(p.get("pendingAmount", 0) for p in projects)
        currency = data.get("currency", "THB")

        active_projects = [p for p in projects if p.get("status") == "in_progress"]

        progress_pct = min(100, int((total_paid / target) * 100)) if target > 0 else 0

        return {
            "currency": currency,
            "monthly_target": target,
            "total_paid": total_paid,
            "total_pending": total_pending,
            "progress_percent": progress_pct,
            "active_projects": active_projects,
            "total_active": len(active_projects),
        }

    # ── Startups (StageLink & BlackBox) ──────────────────────────────────────

    def get_startup_status(self) -> List[Dict[str, Any]]:
        """Returns startup venture sprints, progress %, and feature statuses."""
        data = self._load_json("data/startups.json", default={})
        return data.get("startups", [])

    # ── Automation Engine (Master Sync) ──────────────────────────────────────

    async def trigger_workspace_sync(self) -> Tuple[bool, str]:
        """
        Asynchronously runs python ai_tools/sync_workspace.py inside march_workspace.
        Scrapes Mahidol Moodle, checks conflict matrix, and recalibrates JSON databases.
        """
        sync_script = self._resolve("ai_tools", "sync_workspace.py")
        if not os.path.exists(sync_script):
            return False, f"Sync script not found at {sync_script}"

        logger.info(f"SecondBrain: Launching {sync_script}...")
        try:
            proc = await asyncio.create_subprocess_exec(
                "python",
                sync_script,
                cwd=self.root_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120.0)
            output = stdout.decode("utf-8", errors="ignore").strip()
            err_msg = stderr.decode("utf-8", errors="ignore").strip()

            if proc.returncode == 0:
                logger.info("SecondBrain: Workspace sync completed successfully.")
                return True, output or "Workspace sync completed successfully."
            else:
                logger.warning(f"SecondBrain: Workspace sync exited with code {proc.returncode}: {err_msg}")
                return False, err_msg or output or f"Sync failed with return code {proc.returncode}"
        except asyncio.TimeoutError:
            logger.error("SecondBrain: Workspace sync timed out (120s limit reached).")
            return False, "Workspace sync timed out after 120 seconds."
        except Exception as e:
            logger.error(f"SecondBrain: Exception during workspace sync: {e}")
            return False, str(e)

    # ── Second Brain Document Search ─────────────────────────────────────────

    def search_notes(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """
        Searches user-owned second-brain files using ranked local lexical retrieval.
        Agent receipts and conversation records are stored elsewhere and are excluded.
        """
        query_text = query.lower().strip()
        query_terms = self._search_terms(query_text)
        if not query_terms:
            return []

        search_dirs = [
            self._resolve("university"),
            self._resolve("documents"),
            self._resolve("operations"),
            self._resolve("media_production"),
        ]

        candidates: List[Dict[str, Any]] = []
        for d in search_dirs:
            if not os.path.exists(d):
                continue
            for root, _, files in os.walk(d):
                for file in files:
                    if not file.endswith((".md", ".txt", ".json")):
                        continue
                    full_p = os.path.join(root, file)
                    try:
                        if os.path.getsize(full_p) > 2_000_000:
                            continue
                        with open(full_p, "r", encoding="utf-8", errors="ignore") as f:
                            lines = f.readlines()
                        for idx, line in enumerate(lines):
                            words = self._search_terms(line)
                            overlap = query_terms.intersection(words)
                            if not overlap:
                                continue
                            rel = os.path.relpath(full_p, self.root_path).replace("\\", "/")
                            candidates.append({
                                "file": rel,
                                "line": str(idx + 1),
                                "snippet": line.strip()[:240],
                                "source": "personal_knowledge",
                                "_terms": words,
                                "_phrase_match": query_text in line.lower(),
                                "_path_match": bool(query_terms.intersection(self._search_terms(rel))),
                            })
                    except Exception:
                        continue

        if not candidates:
            return []
        document_frequency: Counter[str] = Counter()
        for candidate in candidates:
            document_frequency.update(set(candidate["_terms"]))
        average_length = sum(len(candidate["_terms"]) for candidate in candidates) / len(candidates)
        for candidate in candidates:
            term_frequencies = Counter(candidate["_terms"])
            score = 0.0
            for term in query_terms:
                frequency = term_frequencies.get(term, 0)
                if frequency == 0:
                    continue
                inverse_frequency = math.log(
                    1 + (len(candidates) - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5)
                )
                denominator = frequency + 1.2 * (0.25 + 0.75 * len(candidate["_terms"]) / max(average_length, 1.0))
                score += inverse_frequency * frequency * 2.2 / denominator
            if candidate["_phrase_match"]:
                score += 1.0
            if candidate["_path_match"]:
                score += 0.2
            candidate["score"] = round(score, 4)
            candidate.pop("_terms", None)
            candidate.pop("_phrase_match", None)
            candidate.pop("_path_match", None)

        candidates.sort(key=lambda result: result["score"], reverse=True)
        return candidates[:max(1, min(max_results, 20))]

    @staticmethod
    def _search_terms(text: str) -> set[str]:
        terms = set()
        for raw in _SEARCH_WORDS.findall(text.lower()):
            word = raw.strip("'-_")
            if len(word) > 5 and word.endswith("ies"):
                word = word[:-3] + "y"
            elif len(word) > 5 and word.endswith("ing"):
                word = word[:-3]
            elif len(word) > 4 and word.endswith("ed"):
                word = word[:-2]
            elif len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
                word = word[:-1]
            if word and word not in _SEARCH_STOP_WORDS and len(word) > 1:
                terms.add(word)
        return terms


# Singleton instance
second_brain = SecondBrainService()

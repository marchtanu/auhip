import os
import json
import logging
import asyncio
import urllib.parse
import webbrowser
import aiohttp
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

DATA_DIR = "data"
TASKS_FILE = os.path.join(DATA_DIR, "tasks.json")
CALENDAR_FILE = os.path.join(DATA_DIR, "calendar.json")

def _init_data_files():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
    if not os.path.exists(CALENDAR_FILE):
        with open(CALENDAR_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)

_session: Optional[aiohttp.ClientSession] = None

async def _get_session() -> aiohttp.ClientSession:
    """Provides a singleton aiohttp.ClientSession to prevent connection churn."""
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession()
    return _session

# ── Stock Lookup ─────────────────────────────────────────────────────────────
async def lookup_stock(ticker: str) -> str:
    """Queries Yahoo Finance for the real-time stock price of a given ticker symbol."""
    symbol = ticker.strip().upper()
    if not symbol:
        return "Please specify a ticker symbol, for example 'AAPL'."

    logger.info(f"SKILL: Lookup Stock '{symbol}'.")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        session = await _get_session()
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5.0)) as resp:
            if resp.status == 200:
                data = await resp.json()
                result = data.get("chart", {}).get("result")
                if result and len(result) > 0:
                    meta = result[0].get("meta", {})
                    price = meta.get("regularMarketPrice")
                    currency = meta.get("currency", "USD")
                    if price is not None:
                        return f"The current price of {symbol} is {price:.2f} {currency}."

            # Fallback to opening Google Finance
            fallback_url = f"https://www.google.com/finance/quote/{symbol}:NASDAQ"
            webbrowser.open(fallback_url)
            return f"Could not fetch real-time data directly, opening Google Finance for {symbol}."
    except Exception as e:
        logger.error(f"Error querying stock price for {symbol}: {e}")
        # Fallback to opening Google Finance
        fallback_url = f"https://www.google.com/finance/quote/{symbol}:NASDAQ"
        webbrowser.open(fallback_url)
        return f"Error querying price directly. Opening Google Finance for {symbol}."

# ── GitHub Search ────────────────────────────────────────────────────────────
async def search_github(query: str, search_type: str = "repositories") -> str:
    """Searches GitHub for the given query."""
    q = query.strip()
    if not q:
        return "What would you like me to search for on GitHub?"

    logger.info(f"SKILL: GitHub Search '{q}'.")
    encoded_query = urllib.parse.quote(q)

    t = search_type.strip().lower()
    if t not in ("repositories", "issues", "code", "users"):
        t = "repositories"

    url = f"https://github.com/search?q={encoded_query}&type={t}"
    webbrowser.open(url)
    return f"Searching GitHub for '{q}' under {t}."

# ── Tasks Organizer ──────────────────────────────────────────────────────────
async def add_task(title: str) -> str:
    """Adds a new task to the task list."""
    _init_data_files()
    t = title.strip()
    if not t:
        return "Please specify the task description."

    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            tasks = json.load(f)

        tasks.append({"title": t, "completed": False, "created_at": datetime.now().isoformat()})

        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=4, ensure_ascii=False)

        return f"Task added: '{t}'."
    except Exception as e:
        logger.error(f"Failed to add task: {e}")
        return f"Failed to add task: {str(e)}"

async def list_tasks() -> str:
    """Lists all active and completed tasks."""
    _init_data_files()
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            tasks = json.load(f)

        if not tasks:
            return "You have no tasks in your list."

        active_tasks = [t for t in tasks if not t.get("completed")]
        completed_tasks = [t for t in tasks if t.get("completed")]

        lines = []
        if active_tasks:
            lines.append("📋 Active Tasks:")
            for i, t in enumerate(active_tasks, 1):
                orig_idx = tasks.index(t)
                lines.append(f" {i}. [ ] {t['title']} (ID: {orig_idx + 1})")
        else:
            lines.append("No active tasks.")

        if completed_tasks:
            lines.append("\n✅ Completed Tasks:")
            for i, t in enumerate(completed_tasks, 1):
                lines.append(f" - [x] {t['title']}")

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        return f"Failed to list tasks: {str(e)}"

async def complete_task(index: int) -> str:
    """Marks a task as completed based on its index ID."""
    _init_data_files()
    try:
        idx = int(index) - 1
    except ValueError:
        return "Please specify a valid numeric ID."

    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            tasks = json.load(f)

        if idx < 0 or idx >= len(tasks):
            return f"Invalid task ID. Please specify a number between 1 and {len(tasks)}."

        tasks[idx]["completed"] = True
        tasks[idx]["completed_at"] = datetime.now().isoformat()

        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=4, ensure_ascii=False)

        return f"Task completed: '{tasks[idx]['title']}'."
    except Exception as e:
        logger.error(f"Failed to complete task: {e}")
        return f"Failed to complete task: {str(e)}"

# ── Calendar Organizer ───────────────────────────────────────────────────────
async def add_calendar_event(title: str, date_str: str, time_str: str = "") -> str:
    """Adds an event to the calendar list."""
    _init_data_files()
    t = title.strip()
    d = date_str.strip()
    tm = time_str.strip()
    if not t or not d:
        return "Please specify both the event title and the date."

    try:
        with open(CALENDAR_FILE, "r", encoding="utf-8") as f:
            events = json.load(f)

        events.append({
            "title": t,
            "date": d,
            "time": tm,
            "created_at": datetime.now().isoformat()
        })

        try:
            events.sort(key=lambda x: x.get("date", ""))
        except Exception:
            pass

        with open(CALENDAR_FILE, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=4, ensure_ascii=False)

        time_part = f" at {tm}" if tm else ""
        return f"Calendar event added: '{t}' on {d}{time_part}."
    except Exception as e:
        logger.error(f"Failed to add calendar event: {e}")
        return f"Failed to add calendar event: {str(e)}"

async def list_calendar_events() -> str:
    """Lists all upcoming calendar events."""
    _init_data_files()
    try:
        with open(CALENDAR_FILE, "r", encoding="utf-8") as f:
            events = json.load(f)

        if not events:
            return "You have no upcoming events in your calendar."

        lines = ["📅 Upcoming Calendar Events:"]
        for i, ev in enumerate(events, 1):
            time_part = f" at {ev.get('time')}" if ev.get("time") else ""
            lines.append(f" {i}. {ev['title']} — {ev['date']}{time_part}")

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Failed to list calendar events: {e}")
        return f"Failed to list calendar events: {str(e)}"

# ── Handless Coding & Second Brain Workspace Utilities ──────────────────────
def _get_workspace_root() -> str:
    """Returns the Second Brain (march_workspace) root path, or fallback to current dir."""
    try:
        from auhip.core.config import config
        if getattr(config, "SECOND_BRAIN_PATH", None) and os.path.exists(config.SECOND_BRAIN_PATH):
            return os.path.realpath(config.SECOND_BRAIN_PATH)
    except Exception:
        pass
    return os.path.realpath(".")


def _resolve_workspace_path(path: str) -> str:
    """Resolve a user supplied path and reject traversal or symlink escapes."""
    workspace_root = os.path.realpath(_get_workspace_root())
    candidate = os.path.realpath(os.path.join(workspace_root, path) if not os.path.isabs(path) else path)
    try:
        if os.path.commonpath([candidate, workspace_root]) != workspace_root:
            raise PermissionError("Path is outside the workspace.")
    except ValueError as exc:
        raise PermissionError("Path is outside the workspace.") from exc
    return candidate

async def list_workspace_files() -> str:
    """Lists key files in the current workspace directory (Second Brain)."""
    logger.info("SKILL: List Workspace Files.")
    try:
        root = _get_workspace_root()
        files = os.listdir(root)
        filtered_files = [f for f in files if f not in (".git", ".venv", "__pycache__", ".agents", "scratch", "vosk-model-small-en-us-0.15", "node_modules", ".next")]

        dir_list = []
        file_list = []
        for f in sorted(filtered_files):
            full_item = os.path.join(root, f)
            if os.path.isdir(full_item):
                dir_list.append(f"{f}/")
            else:
                file_list.append(f)

        lines = [f"📁 Second Brain Workspace ({os.path.basename(root)}):"]
        if dir_list:
            lines.append("Directories:")
            lines.append("  " + ", ".join(dir_list))
        if file_list:
            lines.append("Files:")
            lines.append("  " + ", ".join(file_list))

        return "\n".join(lines)
    except Exception as e:
        return f"Failed to list workspace contents: {str(e)}"

async def read_code_file(filename: str) -> str:
    """Reads a file in the workspace and returns its contents (capped to first 80 lines for readability)."""
    logger.info(f"SKILL: Read Code File '{filename}'.")
    try:
        workspace_root = _get_workspace_root()
        target_path = None

        # 1. Direct path check with boundary verification
        candidate = os.path.realpath(os.path.join(workspace_root, filename) if not os.path.isabs(filename) else filename)
        try:
            if os.path.commonpath([candidate, workspace_root]) == workspace_root and os.path.isfile(candidate):
                target_path = candidate
        except ValueError:
            target_path = None

        # 2. Search workspace if not found directly
        if not target_path:
            for root, dirs, files in os.walk(workspace_root):
                dirs[:] = [d for d in dirs if d not in (".venv", ".git", "__pycache__", "data", "scratch")]
                if filename in files:
                    found = os.path.realpath(os.path.join(root, filename))
                    try:
                        if os.path.commonpath([found, workspace_root]) == workspace_root:
                            target_path = found
                            break
                    except ValueError:
                        continue

        if not target_path:
            return f"Security restriction or file not found: '{filename}' not accessible in workspace."

        with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        cap = 80
        total_lines = len(lines)
        truncated = total_lines > cap
        selected_lines = lines[:cap]

        content = "".join(selected_lines)
        info = f"Showing first {cap} of {total_lines} lines:\n\n" if truncated else f"Full file ({total_lines} lines):\n\n"

        return f"File: {os.path.basename(target_path)}\n{info}{content}"
    except Exception as e:
        return f"Failed to read file: {str(e)}"

async def write_code_file(filename: str, content: str) -> str:
    """Writes or overwrites a file in the workspace with specific code content."""
    logger.info(f"SKILL: Write Code File '{filename}'.")
    try:
        try:
            target_path = _resolve_workspace_path(filename)
        except PermissionError:
            return "Security restriction: Cannot write files outside the workspace."

        from auhip.core.llm.tool_manager import require_tool_approval
        require_tool_approval("write_code_file")
        os.makedirs(os.path.dirname(target_path), exist_ok=True)

        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)

        return f"Successfully wrote code to '{filename}'."
    except Exception as e:
        return f"Failed to write file: {str(e)}"

# ── Clean-up Utilities ───────────────────────────────────────────────────────
async def list_unused_files() -> str:
    """Scans the workspace to identify unused Python files (not imported anywhere)."""
    import ast
    logger.info("SKILL: List Unused Files")
    try:
        workspace_root = os.path.abspath(".")

        # 1. Walk the workspace to find all python files in 'auhip' directory and root
        all_files = []
        if os.path.exists(os.path.join(workspace_root, "main.py")):
            all_files.append(os.path.join(workspace_root, "main.py"))

        auhip_dir = os.path.join(workspace_root, "auhip")
        if os.path.exists(auhip_dir):
            for root, dirs, files in os.walk(auhip_dir):
                # Ignore common virtual env, git, and internal data directories
                dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", ".venv", "data", "scratch")]
                for file in files:
                    if file.endswith(".py"):
                        all_files.append(os.path.join(root, file))

        # Normalize files to relative paths for mapping
        rel_files = [os.path.relpath(f, workspace_root).replace("\\", "/") for f in all_files]

        # 2. Build a map of file path to its module path
        file_to_module = {}
        for f in rel_files:
            if f.endswith("__init__.py"):
                parts = f.split("/")[:-1]
                mod = ".".join(parts)
            else:
                parts = f[:-3].split("/")
                mod = ".".join(parts)
            file_to_module[f] = mod

        # 3. Parse imports from all files using AST
        imported_modules = set()
        for f in rel_files:
            abs_path = os.path.join(workspace_root, f)
            try:
                with open(abs_path, "r", encoding="utf-8", errors="ignore") as file_obj:
                    tree = ast.parse(file_obj.read(), filename=f)

                file_parts = f.split("/")[:-1]

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imported_modules.add(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            base_mod = node.module
                        else:
                            base_mod = ""

                        if node.level > 0:
                            lvl = node.level
                            if lvl <= len(file_parts):
                                pkg_parts = file_parts[:len(file_parts) - lvl + 1]
                                pkg = ".".join(pkg_parts)
                                if base_mod:
                                    base_mod = f"{pkg}.{base_mod}"
                                else:
                                    base_mod = pkg

                        imported_modules.add(base_mod)
                        for alias in node.names:
                            imported_modules.add(f"{base_mod}.{alias.name}")
            except Exception as e:
                logger.warning(f"Error parsing imports from {f}: {e}")

        # 4. Check which modules are never imported
        protected_basenames = {"main.py", "theme.py", "main_window.py", "requirements.txt", "organizer.py"}
        unused_files = []
        for f in rel_files:
            if f.endswith("__init__.py"):
                continue
            basename = os.path.basename(f)
            if basename in protected_basenames:
                continue

            mod = file_to_module[f]
            is_used = False
            for imported in imported_modules:
                if imported == mod or imported.startswith(mod + "."):
                    is_used = True
                    break

            # Substring scan fallback to handle dynamic registration or string usage
            if not is_used:
                base_name_no_ext = basename[:-3]
                for other_f in rel_files:
                    if other_f == f:
                        continue
                    try:
                        other_abs = os.path.join(workspace_root, other_f)
                        with open(other_abs, "r", encoding="utf-8", errors="ignore") as other_file_obj:
                            content = other_file_obj.read()
                            if base_name_no_ext in content:
                                is_used = True
                                break
                    except Exception:
                        pass

            if not is_used:
                unused_files.append(f)

        if not unused_files:
            return "No unused Python files found in the workspace."

        lines = ["🔍 Unused Python files identified in workspace (safe to delete):"]
        for uf in sorted(unused_files):
            lines.append(f" - {uf}")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error listing unused files: {e}")
        return f"Failed to list unused files: {str(e)}"

async def delete_file(filename: str) -> str:
    """Deletes a file in the workspace securely, preventing deletion of core files."""
    logger.info(f"SKILL: Delete File '{filename}'.")
    try:
        workspace_root = os.path.realpath(_get_workspace_root())
        try:
            target_path = _resolve_workspace_path(filename)
        except PermissionError:
            return "Security restriction: Cannot delete files outside the workspace."
        norm_basename = os.path.basename(filename).lower()

        # Protected files mapping and extensions
        protected_files = {
            "main.py",
            "auhip/gui/theme.py",
            "auhip/gui/main_window.py",
            "auhip/skills/organizer.py",
            "requirements.txt",
            "auhip/core/config.py",
            "auhip/core/state_machine.py",
            ".env",
            ".gitignore",
        }

        protected_basenames = {
            "main.py", "theme.py", "main_window.py", "organizer.py",
            "__init__.py", "config.py", "state_machine.py", ".env",
            ".gitignore", "requirements.txt"
        }

        protected_exts = {".key", ".pem", ".db", ".sqlite", ".sqlite3"}

        if (
            norm_basename in protected_basenames
            or any(norm_basename.endswith(ext) for ext in protected_exts)
            or ".env" in norm_basename
            or filename.endswith("__init__.py")
        ):
            return f"Security restriction: Deletion of protected file '{filename}' is blocked."

        if not os.path.exists(target_path):
            # Fallback search inside workspace
            found_path = None
            for root, dirs, files in os.walk(workspace_root):
                dirs[:] = [d for d in dirs if d not in (".git", ".venv", "__pycache__", "data")]
                if filename in files:
                    try:
                        found_path = _resolve_workspace_path(os.path.join(root, filename))
                    except PermissionError:
                        continue
                    break
            if found_path:
                target_path = found_path
            else:
                return f"File '{filename}' not found in workspace."

        rel_path = os.path.relpath(target_path, workspace_root).replace("\\", "/")
        target_basename = os.path.basename(target_path).lower()

        if (
            rel_path in protected_files
            or rel_path.endswith("__init__.py")
            or target_basename in protected_basenames
            or any(target_basename.endswith(ext) for ext in protected_exts)
            or ".env" in target_basename
            or ".git" in target_path.replace("\\", "/").split("/")
        ):
            return f"Security restriction: Deletion of protected file '{rel_path}' is blocked."

        from auhip.core.llm.tool_manager import require_tool_approval
        require_tool_approval("delete_file")
        os.remove(target_path)
        return f"Successfully deleted file: '{rel_path}'."
    except Exception as e:
        logger.error(f"Failed to delete file {filename}: {e}")
        return f"Failed to delete file: {str(e)}"


# ── Agentic Workspace Tools (Milestone 2 & Cowork) ───────────────────────────

async def patch_file(path: str, target: str, replacement: str) -> str:
    """Patches an existing file by replacing a target snippet with new replacement text."""
    logger.info(f"SKILL: Patch File '{path}'.")
    try:
        try:
            clean_path = _resolve_workspace_path(path.strip())
        except PermissionError:
            return "Security restriction: Cannot patch files outside the workspace."
        if not os.path.exists(clean_path):
            return f"Error: File '{clean_path}' does not exist."

        with open(clean_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        if target not in content:
            return f"Error: Target snippet not found in '{clean_path}'."

        count = content.count(target)
        if count > 1:
            return f"Error: Target snippet appears {count} times in '{clean_path}'. Please provide more surrounding context to make it unique."

        new_content = content.replace(target, replacement, 1)
        from auhip.core.llm.tool_manager import require_tool_approval
        require_tool_approval("patch_file")
        with open(clean_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return f"Successfully patched '{clean_path}' (1 replacement applied)."
    except Exception as e:
        logger.error(f"Failed to patch file {path}: {e}")
        return f"Failed to patch file: {str(e)}"


async def view_directory_tree(path: str = ".", max_depth: int = 3) -> str:
    """Generates an ASCII directory tree of the workspace up to max_depth."""
    target_path = _get_workspace_root() if path == "." else path
    logger.info(f"SKILL: View Directory Tree from '{target_path}' (depth: {max_depth}).")
    try:
        ignore_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules", ".gemini", "brain", "data"}
        root_dir = os.path.abspath(target_path)
        lines = [f"📁 {os.path.basename(root_dir) or '.'}/"]

        def _walk(curr_path: str, prefix: str, depth: int):
            if depth > max_depth:
                return
            try:
                entries = sorted(os.listdir(curr_path))
            except PermissionError:
                return

            dirs = [e for e in entries if os.path.isdir(os.path.join(curr_path, e)) and e not in ignore_dirs]
            files = [e for e in entries if os.path.isfile(os.path.join(curr_path, e))]

            all_items = [(d, True) for d in dirs] + [(f, False) for f in files]
            count = len(all_items)

            for i, (item, is_dir) in enumerate(all_items):
                is_last = (i == count - 1)
                connector = "└── " if is_last else "├── "
                icon = "📁 " if is_dir else "📄 "
                lines.append(f"{prefix}{connector}{icon}{item}")

                if is_dir:
                    sub_prefix = prefix + ("    " if is_last else "│   ")
                    _walk(os.path.join(curr_path, item), sub_prefix, depth + 1)

        _walk(root_dir, "", 1)
        return "\n".join(lines[:120])  # Cap at 120 lines
    except Exception as e:
        logger.error(f"Failed to view directory tree: {e}")
        return f"Failed to generate tree: {str(e)}"


async def search_codebase(query: str, extension: str = "") -> str:
    """Searches for a text pattern across project code files and returns matching lines."""
    logger.info(f"SKILL: Search Codebase for '{query}'.")
    q = query.strip().lower()
    if not q:
        return "Please specify a search term."

    ext = extension.strip().lower()
    matches = []
    ignore_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules", ".gemini", "brain"}
    search_root = _get_workspace_root()

    for root, dirs, files in os.walk(search_root):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for f in files:
            if ext and not f.endswith(ext):
                continue
            if not f.endswith((".py", ".md", ".json", ".bat", ".txt", ".html", ".css", ".js")):
                continue

            file_path = os.path.join(root, f)
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as fl:
                    for line_num, line in enumerate(fl, 1):
                        if q in line.lower():
                            rel_p = os.path.relpath(file_path, search_root).replace("\\", "/")
                            matches.append(f"  {rel_p}:{line_num} | {line.strip()[:90]}")
                            if len(matches) >= 35:
                                break
            except Exception:
                pass
        if len(matches) >= 35:
            break

    if not matches:
        return f"No matches found for '{query}'."

    header = f"🔍 Found {len(matches)} matches for '{query}':\n"
    return header + "\n".join(matches)


async def run_powershell_guarded(command: str) -> str:
    """Executes a safe PowerShell command in the workspace with safety bounds."""
    logger.info(f"SKILL: Run PowerShell Guarded: '{command}'.")
    from auhip.core.llm.tool_manager import is_tool_authorized
    if not is_tool_authorized("run_powershell_guarded"):
        return "PowerShell execution is disabled. Submit the command through AUHIP for approval."
    cmd_lower = command.strip().lower()

    # Guard against destructive or rogue commands
    blocked_terms = [
        "rmdir /s /q c:", "del /f /s /q *", "format ", "drop database",
        ":(){ :|:& };:", "rm -rf /", "shutdown /s", "reg delete"
    ]
    for term in blocked_terms:
        if term in cmd_lower:
            return f"Security Restriction: The command contains a blocked term ('{term}')."

    try:
        if os.name != "nt":
            return "PowerShell execution is supported on Windows only."
        proc = await asyncio.create_subprocess_exec(
            "powershell.exe", "-NoProfile", "-Command", command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.abspath(".")
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return "Command timed out after 15 seconds."
        except asyncio.CancelledError:
            if proc.returncode is None:
                proc.kill()
                await proc.wait()
            raise

        out_str = stdout.decode("utf-8", errors="replace").strip()
        err_str = stderr.decode("utf-8", errors="replace").strip()

        if err_str and not out_str:
            return f"PowerShell Stderr:\n{err_str[:800]}"
        elif err_str:
            return f"PowerShell Output:\n{out_str[:800]}\n(Warnings:\n{err_str[:300]})"
        return f"PowerShell Output:\n{out_str[:800]}" if out_str else "Command completed with zero output."
    except Exception as e:
        logger.error(f"Failed to execute powershell command: {e}")
        return f"Execution error: {str(e)}"


# ── NotebookLM Skills (Local Synthesis & Dual-Host Podcast) ──────────────────

async def summarize_notebook(name: str = "project") -> str:
    """Generates an executive briefing and summary of project notebooks and documents."""
    logger.info(f"SKILL: Summarize Notebook '{name}'.")
    notes_dir = "user/notebooks"
    os.makedirs(notes_dir, exist_ok=True)

    # Ingest text files from notes_dir or docs/
    found_docs = []
    for d in [notes_dir, "docs"]:
        if os.path.exists(d):
            for root, _, files in os.walk(d):
                for f in files:
                    if f.endswith((".md", ".txt")):
                        found_docs.append(os.path.join(root, f))

    if not found_docs:
        return "No documents found in user/notebooks or docs to summarize."

    summary_lines = [f"📚 Notebook Summary & Executive Briefing ({len(found_docs)} sources indexed):"]
    for p in found_docs[:8]:
        rel = os.path.relpath(p, ".").replace("\\", "/")
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as fl:
                first_few = [l.strip() for l in fl.readlines() if l.strip() and not l.startswith("#")][:2]
                snippet = " ".join(first_few)[:120]
                summary_lines.append(f" • [{rel}]: {snippet}...")
        except Exception:
            pass

    return "\n".join(summary_lines)


async def generate_audio_overview(topic: str = "AUHIP Capabilities") -> str:
    """Generates a conversational dual-host audio overview dialogue (Deep Dive Podcast)."""
    logger.info(f"SKILL: Generate Audio Overview for '{topic}'.")
    podcast_script = (
        f"🎙️ Deep Dive Audio Overview: {topic}\n\n"
        "[Host 1 (Alex - British Jarvis)]: Welcome to the AUHIP deep dive. Today we are looking at our local-first AI operating system.\n"
        "[Host 2 (Taylor - US Co-host)]: Right, and what's fascinating is how it combines full voice conversation with contactless air-mouse control and a live developer cockpit.\n"
        "[Host 1]: Precisely. You get immediate barge-in voice turn-taking, sub-pixel fingertip cursor tracking, and autonomous workspace tools running 100% locally on your machine.\n"
        "[Host 2]: Zero cloud lock-in, complete privacy, and effortless productivity."
    )
    return podcast_script

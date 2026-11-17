"""
actions/todo_action.py - Auto-discovered action for managing To-Do items and reminders.

Supports:
- Adding tasks via voice or text (Date-only or Time-specific).
- Listing active / pending tasks.
- Completing tasks.
- Deleting tasks.
- Syncs automatically with Settings > To-Do List & Reminders UI and Origin Island.
"""
from __future__ import annotations

import difflib
from datetime import datetime
from typing import Any, Dict, Optional

from core import outcome
from core import todo_manager
from core.origin_island import get_origin_island


def manage_todo(
    parameters: Dict[str, Any],
    player=None,
    speak=None,
    response=None,
    session_memory=None,
) -> str:
    """Handles To-Do list operations: add, list, complete, delete."""
    action = str(parameters.get("action", "list")).strip().lower()
    title = str(parameters.get("title", "")).strip()
    date_str = str(parameters.get("date", "")).strip()
    time_str = str(parameters.get("time", "")).strip() if parameters.get("time") else None
    task_id = str(parameters.get("task_id", "")).strip()

    def _notify(text: str, success: bool = True):
        if player and hasattr(player, "ui") and player.ui:
            try:
                player.ui.notify_task_completed(text, success)
                return
            except Exception:
                pass
        island = get_origin_island()
        if island:
            try:
                island.set_task_result(text, success)
            except Exception:
                pass

    # ── 1. ADD TASK ──────────────────────────────────────────────────────────
    if action == "add":
        if not title:
            return outcome.done("manage_todo", message="Please specify the title or description of the task to add.")

        norm_date = todo_manager.parse_date_input(date_str) if date_str else datetime.now().strftime("%Y-%m-%d")
        norm_time = todo_manager.parse_time_input(time_str) if time_str else None

        task_type = "time" if norm_time else "date"
        task = todo_manager.add_task(
            title=title,
            date_str=norm_date,
            time_str=norm_time,
            task_type=task_type,
        )

        _notify(f"To-Do Saved: {title[:25]}", True)

        if player and hasattr(player, "write_log"):
            player.write_log(f"SYS: To-Do added: '{title}' on {norm_date}" + (f" at {norm_time}" if norm_time else ""))

        if task_type == "time":
            msg = (
                f"Task '{title}' has been added to your To-Do list for {norm_date} at {norm_time}. "
                f"I will start reminding you 10 minutes before, and again 5 minutes before."
            )
        else:
            msg = (
                f"Task '{title}' has been saved to your To-Do list for {norm_date}. "
                f"I will remind you the day before whenever you open JARVIS or boot your laptop."
            )
        return outcome.done("manage_todo", message=msg)

    # ── 2. LIST TASKS ────────────────────────────────────────────────────────
    elif action in ("list", "show", "view", "get"):
        pending = todo_manager.get_pending_tasks()
        if not pending:
            return outcome.done("manage_todo", message="Your To-Do list is currently empty. You have no pending tasks.")

        lines = ["Here are your pending tasks in the To-Do list:"]
        for idx, t in enumerate(pending, 1):
            t_title = t.get("title", "")
            t_date = t.get("date", "")
            t_time = t.get("time")
            when = f"{t_date} at {t_time}" if t_time else t_date
            lines.append(f"{idx}. {t_title} (Due: {when})")

        return outcome.done("manage_todo", message="\n".join(lines))

    # ── 3. COMPLETE TASK ─────────────────────────────────────────────────────
    elif action in ("complete", "done", "finish", "check"):
        pending = todo_manager.get_pending_tasks()
        if not pending:
            return outcome.done("manage_todo", message="You have no pending tasks to complete.")

        target = None
        # Match by ID or fuzzy title match
        if task_id:
            for t in pending:
                if t.get("id") == task_id or task_id.lower() in t.get("title", "").lower():
                    target = t
                    break

        if not target and title:
            for t in pending:
                if title.lower() in t.get("title", "").lower():
                    target = t
                    break

        if not target and (task_id or title):
            # Try fuzzy match
            query = (title or task_id).lower()
            titles = [t.get("title", "").lower() for t in pending]
            matches = difflib.get_close_matches(query, titles, n=1, cutoff=0.4)
            if matches:
                for t in pending:
                    if t.get("title", "").lower() == matches[0]:
                        target = t
                        break

        # Fallback to the first pending task if only one exists
        if not target and len(pending) == 1:
            target = pending[0]

        if not target:
            return outcome.done("manage_todo", message="I could not find which task you wanted to complete. Please specify the task name.")

        todo_manager.complete_task(target["id"])
        _notify(f"Completed: {target['title'][:25]}", True)

        return outcome.done("manage_todo", message=f"Marked '{target['title']}' as completed in your To-Do list.")

    # ── 4. DELETE TASK ───────────────────────────────────────────────────────
    elif action in ("delete", "remove", "cancel"):
        pending = todo_manager.get_pending_tasks()
        if not pending:
            return outcome.done("manage_todo", message="You have no pending tasks to delete.")

        target = None
        query = (title or task_id).lower()
        if query:
            for t in pending:
                if query in t.get("title", "").lower() or t.get("id") == query:
                    target = t
                    break

        if not target:
            return outcome.done("manage_todo", message="I could not find the task you wanted to delete.")

        todo_manager.delete_task(target["id"])
        _notify(f"Deleted: {target['title'][:25]}", False)

        return outcome.done("manage_todo", message=f"Removed '{target['title']}' from your To-Do list.")

    # ── 5. MODIFY / EDIT TASK ────────────────────────────────────────────────
    elif action in ("modify", "edit", "update", "change"):
        pending = todo_manager.get_pending_tasks()
        if not pending:
            return outcome.done("manage_todo", message="You have no pending tasks to modify.")

        target = None
        query = (task_id or title).lower()
        if query:
            for t in pending:
                if query in t.get("title", "").lower() or t.get("id") == query:
                    target = t
                    break

        if not target and query:
            titles = [t.get("title", "").lower() for t in pending]
            matches = difflib.get_close_matches(query, titles, n=1, cutoff=0.35)
            if matches:
                for t in pending:
                    if t.get("title", "").lower() == matches[0]:
                        target = t
                        break

        if not target and len(pending) == 1:
            target = pending[0]

        if not target:
            return outcome.done("manage_todo", message="I could not find which task you wanted to modify. Please state the task name.")

        new_title = parameters.get("new_title")
        new_date = parameters.get("date")
        new_time = parameters.get("time")

        todo_manager.update_task(
            task_id=target["id"],
            title=new_title,
            date_str=new_date,
            time_str=new_time,
        )

        _notify(f"Modified: {target['title'][:20]}", True)

        updated_info = []
        if new_date:
            updated_info.append(f"date: {new_date}")
        if new_time:
            updated_info.append(f"time: {new_time}")
        details = f" ({', '.join(updated_info)})" if updated_info else ""
        return outcome.done("manage_todo", message=f"Task '{target['title']}' has been updated{details}.")

    return outcome.done("manage_todo", message=f"Unknown to-do action '{action}'. Supported actions are add, list, complete, delete, modify.")


TOOL = {
    "name": "manage_todo",
    "description": (
        "Manages the user's To-Do list and scheduled tasks/reminders. "
        "Use this whenever the user asks to save a task, modify an existing task, remind them about something, "
        "view their to-do list, or mark a task complete. Supports Date-only tasks (e.g. Birthday on 20 January) "
        "and Time-specific tasks (e.g. Sonda 9 tai medicine khabo). "
        "Time tasks alert 10 minutes before, 5 minutes before, and when due ('5 min por por'). "
        "Date tasks alert proactively the day before on startup/opening."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "enum": ["add", "list", "complete", "delete", "modify"],
                "description": "Action: 'add', 'list', 'complete', 'delete', or 'modify'"
            },
            "title": {
                "type": "STRING",
                "description": "Task title or description (e.g. 'Medicine at 9pm', 'Birthday 20 Jan')"
            },
            "new_title": {
                "type": "STRING",
                "description": "Optional new title when modifying a task"
            },
            "date": {
                "type": "STRING",
                "description": "Target date: e.g. 'YYYY-MM-DD', 'today', 'tomorrow', '20 january', '5th'"
            },
            "time": {
                "type": "STRING",
                "description": "Optional target time: e.g. '15:30', '9pm', 'sonda 9 tai', '10:00 am'"
            },
            "task_id": {
                "type": "STRING",
                "description": "Optional task ID or search keyword when completing, modifying, or deleting"
            }
        },
        "required": ["action"]
    },
    "handler": manage_todo,
}

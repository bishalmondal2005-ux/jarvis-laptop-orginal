"""
core/todo_manager.py - Persistent To-Do List & Smart Reminder Engine for Mark-LVI (JARVIS).

Features:
- Stores tasks persistently in memory/todo_list.json.
- Strictly operates in Asia/Kolkata timezone (IST, UTC+05:30).
- Supports both Date-only tasks (e.g. Birthday on 20 January) and Time-specific tasks (e.g. 9:00 PM).
- Smart Reminders:
  * Time-based tasks: Alerts at 10 minutes before, 5 minutes before, and when due ("5 min por por").
  * Date-based tasks: Proactive alert on the day before (e.g. 19 January for 20 January)
    on startup / background check ("You have these tasks scheduled for tomorrow...").
- CRUD operations: Add, list pending, update/modify, mark completed, uncomplete, delete, clear completed.
- Startup briefing integration: Collects pending tasks for today and tomorrow.
"""
from __future__ import annotations

import json
import os
import re
import uuid
import datetime as dt
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

TODO_FILE_PATH = Path(__file__).resolve().parent.parent / "memory" / "todo_list.json"

MONTH_MAP: Dict[str, int] = {
    "jan": 1, "january": 1, "জানুয়ারি": 1,
    "feb": 2, "february": 2, "ফেব্রুয়ারি": 2,
    "mar": 3, "march": 3, "মার্চ": 3,
    "apr": 4, "april": 4, "এপ্রিল": 4,
    "may": 5, "মে": 5,
    "jun": 6, "june": 6, "জুন": 6,
    "jul": 7, "july": 7, "জুলাই": 7,
    "aug": 8, "august": 8, "আগস্ট": 8,
    "sep": 9, "september": 9, "সেপ্টেম্বর": 9,
    "oct": 10, "october": 10, "অক্টোবর": 10,
    "nov": 11, "november": 11, "নভেম্বর": 11,
    "dec": 12, "december": 12, "ডিসেম্বর": 12,
}


def _get_kolkata_now() -> datetime:
    """Returns current datetime strictly in Asia/Kolkata timezone (IST, UTC+05:30)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Kolkata"))
    except Exception:
        ist_tz = dt.timezone(dt.timedelta(hours=5, minutes=30))
        return datetime.now(ist_tz)


def get_todo_file_path() -> Path:
    TODO_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return TODO_FILE_PATH


def load_tasks() -> List[Dict[str, Any]]:
    path = get_todo_file_path()
    if not path.exists():
        return []
    try:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return []
        data = json.loads(content)
        if isinstance(data, list):
            return data
    except Exception as e:
        print(f"[TodoManager] Error loading tasks: {e}")
    return []


def save_tasks(tasks: List[Dict[str, Any]]) -> None:
    path = get_todo_file_path()
    try:
        path.write_text(json.dumps(tasks, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"[TodoManager] Error saving tasks: {e}")


def parse_date_input(date_str: str, now: Optional[datetime] = None) -> str:
    """
    Parses flexible date inputs like:
    'today', 'tomorrow', 'কাল', 'আজ', 'আগামীকাল', '2026-11-15', '20 january', 'january 20', '5th', '5 tarikh'
    Returns normalized 'YYYY-MM-DD'.
    """
    if now is None:
        now = _get_kolkata_now()

    raw = str(date_str).strip().lower()
    if not raw or raw in ("today", "আজ", "aj", "aaj"):
        return now.strftime("%Y-%m-%d")

    if raw in ("tomorrow", "কাল", "কালকে", "kal", "kalke", "আগামীকাল", "agamikal"):
        return (now + timedelta(days=1)).strftime("%Y-%m-%d")

    if raw in ("day after tomorrow", "পরশু", "পরশুদিন", "porshu"):
        return (now + timedelta(days=2)).strftime("%Y-%m-%d")

    # Match YYYY-MM-DD
    m_iso = re.match(r"^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$", raw)
    if m_iso:
        y, m, d = int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))
        try:
            return date(y, m, d).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Match DD-MM-YYYY
    m_dmy = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", raw)
    if m_dmy:
        d, m, y = int(m_dmy.group(1)), int(m_dmy.group(2)), int(m_dmy.group(3))
        try:
            return date(y, m, d).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Replace Bengali digits
    bengali_digits = "০১২৩৪৫৬৭৮৯"
    for b_idx, b_char in enumerate(bengali_digits):
        raw = raw.replace(b_char, str(b_idx))

    # Match Month Name and Day (e.g. '20 january', '20th jan', 'january 20', '20 জানুয়ারি')
    for m_name, m_num in MONTH_MAP.items():
        if m_name in raw:
            # Look for number in string
            m_num_match = re.search(r"\b(\d{1,2})(?:st|nd|rd|th|e)?\b", raw)
            if m_num_match:
                d = int(m_num_match.group(1))
                y = now.year
                try:
                    candidate = date(y, m_num, d)
                    # If this date in current year has already passed, schedule for next year
                    if candidate < now.date():
                        candidate = date(y + 1, m_num, d)
                    return candidate.strftime("%Y-%m-%d")
                except ValueError:
                    pass

    # Match single day number (e.g. "5", "5th", "5 tarikh", "৫")
    m_day = re.search(r"\b(\d{1,2})(?:st|nd|rd|th|e| tarikh| tarik)?\b", raw)
    if m_day:
        target_day = int(m_day.group(1))
        if 1 <= target_day <= 31:
            y, m = now.year, now.month
            try:
                candidate = date(y, m, target_day)
                if candidate < now.date():
                    if m == 12:
                        candidate = date(y + 1, 1, target_day)
                    else:
                        candidate = date(y, m + 1, target_day)
                return candidate.strftime("%Y-%m-%d")
            except ValueError:
                pass

    return now.strftime("%Y-%m-%d")


def parse_time_input(time_str: Optional[str]) -> Optional[str]:
    """
    Parses flexible time input like:
    '15:30', '3:30 pm', '3pm', 'সকাল ১০টা', 'রাত ৯টা', 'sonda 9 tai', 'shondha 9 ta', '10:00'
    Returns normalized 'HH:MM' (24-hour format) or None if invalid/empty.
    """
    if not time_str:
        return None
    raw = str(time_str).strip().lower()
    if not raw:
        return None

    # Replace Bengali digits
    bengali_digits = "০১২৩৪৫৬৭৮৯"
    for b_idx, b_char in enumerate(bengali_digits):
        raw = raw.replace(b_char, str(b_idx))

    is_pm = any(k in raw for k in ("pm", "রাত", "সন্ধ্যা", "বিকাল", "দুপুর", "sonda", "shonda", "shondha", "rat", "raat", "bikal", "dupur"))
    is_am = any(k in raw for k in ("am", "সকাল", "ভোর", "sokal", "shokal", "bhor"))

    # Match HH:MM or HH:MM:SS
    m_colon = re.search(r"(\d{1,2}):(\d{2})", raw)
    if m_colon:
        h = int(m_colon.group(1))
        m = int(m_colon.group(2))
        if is_pm and h < 12:
            h += 12
        elif is_am and h == 12:
            h = 0
        if 0 <= h <= 23 and 0 <= m <= 59:
            return f"{h:02d}:{m:02d}"

    # Match single hour like "3pm", "10 am", "9 tai", "9 ta"
    m_hour = re.search(r"\b(\d{1,2})\s*(?:pm|am|tai|ta|টা|baje)?\b", raw)
    if m_hour:
        h = int(m_hour.group(1))
        m = 0
        if is_pm and h < 12:
            h += 12
        elif is_am and h == 12:
            h = 0
        if 0 <= h <= 23:
            return f"{h:02d}:{m:02d}"

    return None


def add_task(
    title: str,
    date_str: str,
    time_str: Optional[str] = None,
    task_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Creates and stores a new task.
    task_type: 'time' if time is provided or explicitly chosen, otherwise 'date'.
    """
    clean_title = str(title).strip()
    norm_date = parse_date_input(date_str)
    norm_time = parse_time_input(time_str)

    if task_type:
        resolved_type = task_type.strip().lower()
    else:
        resolved_type = "time" if norm_time else "date"

    task = {
        "id": f"task_{uuid.uuid4().hex[:8]}",
        "title": clean_title,
        "type": resolved_type,
        "date": norm_date,
        "time": norm_time if resolved_type == "time" else None,
        "completed": False,
        "created_at": _get_kolkata_now().isoformat(),
        "completed_at": None,
        "reminder_10m_sent": False,
        "reminder_5m_sent": False,
        "reminder_due_sent": False,
        "day_before_alert_sent": False,
        "day_of_alert_sent": False,
    }

    tasks = load_tasks()
    tasks.append(task)
    save_tasks(tasks)
    print(f"[TodoManager] Added task: '{clean_title}' on {norm_date} ({resolved_type})")
    return task


def update_task(
    task_id: str,
    title: Optional[str] = None,
    date_str: Optional[str] = None,
    time_str: Optional[str] = None,
    task_type: Optional[str] = None,
) -> bool:
    """Updates an existing task's title, date, time, or type, and resets reminder flags."""
    tasks = load_tasks()
    found = False
    for t in tasks:
        if t.get("id") == task_id:
            if title is not None and title.strip():
                t["title"] = title.strip()
            if date_str is not None:
                t["date"] = parse_date_input(date_str)
            if time_str is not None:
                t["time"] = parse_time_input(time_str)
            if task_type is not None:
                t["type"] = task_type.strip().lower()
            elif time_str is not None:
                t["type"] = "time" if t.get("time") else "date"

            # Reset alert flags because task was modified
            t["reminder_10m_sent"] = False
            t["reminder_5m_sent"] = False
            t["reminder_due_sent"] = False
            t["day_before_alert_sent"] = False
            t["day_of_alert_sent"] = False
            t["updated_at"] = _get_kolkata_now().isoformat()
            found = True
            break
    if found:
        save_tasks(tasks)
        print(f"[TodoManager] Updated task {task_id}")
    return found


def complete_task(task_id: str) -> bool:
    tasks = load_tasks()
    found = False
    for t in tasks:
        if t.get("id") == task_id:
            t["completed"] = True
            t["completed_at"] = _get_kolkata_now().isoformat()
            found = True
            break
    if found:
        save_tasks(tasks)
    return found


def uncomplete_task(task_id: str) -> bool:
    tasks = load_tasks()
    found = False
    for t in tasks:
        if t.get("id") == task_id:
            t["completed"] = False
            t["completed_at"] = None
            found = True
            break
    if found:
        save_tasks(tasks)
    return found


def delete_task(task_id: str) -> bool:
    tasks = load_tasks()
    initial_len = len(tasks)
    tasks = [t for t in tasks if t.get("id") != task_id]
    if len(tasks) != initial_len:
        save_tasks(tasks)
        return True
    return False


def clear_completed_tasks() -> int:
    tasks = load_tasks()
    pending = [t for t in tasks if not t.get("completed")]
    removed_count = len(tasks) - len(pending)
    if removed_count > 0:
        save_tasks(pending)
    return removed_count


def get_pending_tasks() -> List[Dict[str, Any]]:
    tasks = load_tasks()
    return [t for t in tasks if not t.get("completed")]


def get_completed_tasks() -> List[Dict[str, Any]]:
    tasks = load_tasks()
    return [t for t in tasks if t.get("completed")]


def check_pending_reminders(now: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """
    Evaluates pending tasks against current time:
    1. Time-based tasks:
       - 10-minute warning: when 300 < diff_sec <= 600 and not reminder_10m_sent
       - 5-minute warning: when 0 < diff_sec <= 300 and not reminder_5m_sent
       - Due time: when -300 <= diff_sec <= 0 and not reminder_due_sent
    2. Date-based tasks:
       - Day-before reminder: when (task_date - today) == 1 and not day_before_alert_sent
       - Day-of reminder: when (task_date - today) == 0 and not day_of_alert_sent

    Returns a list of alerts to be dispatched (Origin Island, spoken, and logged).
    """
    if now is None:
        now = _get_kolkata_now()

    today = now.date()
    tasks = load_tasks()
    alerts: List[Dict[str, Any]] = []
    modified = False

    for t in tasks:
        if t.get("completed"):
            continue

        task_id = t.get("id", "")
        title = t.get("title", "Task")
        task_date_str = t.get("date", "")
        task_time_str = t.get("time")
        task_type = t.get("type", "date")

        try:
            task_date = datetime.strptime(task_date_str, "%Y-%m-%d").date()
        except Exception:
            continue

        delta_days = (task_date - today).days

        # ── 1. TIME-BASED TASKS ──────────────────────────────────────────────
        if task_type == "time" and task_time_str:
            try:
                target_dt_naive = datetime.strptime(f"{task_date_str} {task_time_str}", "%Y-%m-%d %H:%M")
                # Make timezone-aware if now is timezone-aware
                if now.tzinfo is not None:
                    target_dt = target_dt_naive.replace(tzinfo=now.tzinfo)
                else:
                    target_dt = target_dt_naive

                diff_sec = (target_dt - now).total_seconds()

                # Also alert day-before for time tasks if scheduled for tomorrow
                if delta_days == 1 and not t.get("day_before_alert_sent"):
                    t["day_before_alert_sent"] = True
                    modified = True
                    alerts.append({
                        "task_id": task_id,
                        "title": title,
                        "alert_type": "day_before",
                        "time_str": task_time_str,
                        "date_str": task_date_str,
                        "message": f"Upcoming tomorrow at {task_time_str}: {title}",
                        "bengali_message": f"কালকে {task_time_str} এ তোমার কাজ আছে: {title}",
                    })

                # If scheduled for today: evaluate 10m, 5m, and due alerts
                if delta_days == 0:
                    # 10-Minute Warning: between 5m (300s) and 10m (600s) remaining
                    if 300 < diff_sec <= 600 and not t.get("reminder_10m_sent"):
                        t["reminder_10m_sent"] = True
                        modified = True
                        mins_left = max(6, int(round(diff_sec / 60.0)))
                        alerts.append({
                            "task_id": task_id,
                            "title": title,
                            "alert_type": "10m",
                            "time_str": task_time_str,
                            "date_str": task_date_str,
                            "message": f"Reminder: '{title}' is scheduled in {mins_left} minutes (at {task_time_str}).",
                            "bengali_message": f"রিমাইন্ডার: ১০ মিনিট পর ({task_time_str} এ) তোমার কাজ আছে: {title}",
                        })

                    # 5-Minute Warning: 5m (300s) or less remaining
                    if 0 < diff_sec <= 300 and not t.get("reminder_5m_sent"):
                        t["reminder_5m_sent"] = True
                        t["reminder_10m_sent"] = True
                        modified = True
                        mins_left = max(1, int(round(diff_sec / 60.0)))
                        alerts.append({
                            "task_id": task_id,
                            "title": title,
                            "alert_type": "5m",
                            "time_str": task_time_str,
                            "date_str": task_date_str,
                            "message": f"Urgent Reminder: '{title}' is in {mins_left} minutes (at {task_time_str})!",
                            "bengali_message": f"জরুরি রিমাইন্ডার: আর ৫ মিনিট বাকি! {task_time_str} এ: {title}",
                        })

                    # Due Time Warning: reached or within 5 mins past
                    if -300 <= diff_sec <= 0 and not t.get("reminder_due_sent"):
                        t["reminder_due_sent"] = True
                        t["reminder_10m_sent"] = True
                        t["reminder_5m_sent"] = True
                        modified = True
                        alerts.append({
                            "task_id": task_id,
                            "title": title,
                            "alert_type": "due",
                            "time_str": task_time_str,
                            "date_str": task_date_str,
                            "message": f"It is now {task_time_str}! Time for your scheduled task: '{title}'.",
                            "bengali_message": f"সময় হয়ে গেছে! {task_time_str} এ তোমার শিডিউল করা কাজ: {title}",
                        })

            except Exception as e:
                print(f"[TodoManager] Time task calculation error for {task_id}: {e}")

        # ── 2. DATE-BASED TASKS ──────────────────────────────────────────────
        else:
            # Day-Before Alert (e.g. 19 Jan when Birthday is on 20 Jan)
            if delta_days == 1 and not t.get("day_before_alert_sent"):
                t["day_before_alert_sent"] = True
                modified = True
                alerts.append({
                    "task_id": task_id,
                    "title": title,
                    "alert_type": "day_before",
                    "date_str": task_date_str,
                    "message": f"Tomorrow's Task: You have '{title}' scheduled for tomorrow ({task_date_str}).",
                    "bengali_message": f"তোমার কালকে একটি কাজ শিডিউল করা আছে: {title}",
                })

            # Day-Of Alert
            elif delta_days == 0 and not t.get("day_of_alert_sent"):
                t["day_of_alert_sent"] = True
                modified = True
                alerts.append({
                    "task_id": task_id,
                    "title": title,
                    "alert_type": "day_of",
                    "date_str": task_date_str,
                    "message": f"Today's Task: You have '{title}' scheduled for today.",
                    "bengali_message": f"আজকের শিডিউল করা কাজ: {title}",
                })

    if modified:
        save_tasks(tasks)

    return alerts


def get_startup_briefing(now: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Gathers tasks that should be briefed when JARVIS starts or laptop opens:
    - Tasks scheduled for tomorrow (day-before alert)
    - Tasks scheduled for today
    """
    if now is None:
        now = _get_kolkata_now()
    today = now.date()
    tasks = load_tasks()

    tomorrow_tasks = []
    today_tasks = []

    for t in tasks:
        if t.get("completed"):
            continue
        date_str = t.get("date", "")
        try:
            task_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            continue

        delta_days = (task_date - today).days
        title = t.get("title", "Task")
        time_str = t.get("time")

        desc = f"{title} (at {time_str})" if time_str else title

        if delta_days == 1:
            tomorrow_tasks.append(desc)
        elif delta_days == 0:
            today_tasks.append(desc)

    summary_en = []
    summary_bn = []

    if tomorrow_tasks:
        list_str = ", ".join(tomorrow_tasks)
        summary_en.append(f"Upcoming tomorrow: {list_str}.")
        summary_bn.append(f"কালকে তোমার শিডিউল করা কাজ: {list_str}।")

    if today_tasks:
        list_str = ", ".join(today_tasks)
        summary_en.append(f"Scheduled for today: {list_str}.")
        summary_bn.append(f"আজকের জন্য কাজ: {list_str}।")

    return {
        "tomorrow_count": len(tomorrow_tasks),
        "today_count": len(today_tasks),
        "tomorrow_tasks": tomorrow_tasks,
        "today_tasks": today_tasks,
        "briefing_en": " ".join(summary_en),
        "briefing_bn": " ".join(summary_bn),
    }

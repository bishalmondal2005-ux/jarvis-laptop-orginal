"""
actions/current_time.py - Live, accurate India / Kolkata Time & Date tool for Mark-LVI.

Provides exact real-time hour, minute, date, day of week, and timezone for Asia/Kolkata (IST, UTC+05:30).
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict

from core import outcome


def _get_kolkata_now() -> dt.datetime:
    """Returns current datetime strictly in Asia/Kolkata timezone (IST, UTC+05:30)."""
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("Asia/Kolkata"))
    except Exception:
        ist_tz = dt.timezone(dt.timedelta(hours=5, minutes=30))
        return dt.datetime.now(ist_tz)


def get_current_time(
    parameters: Dict[str, Any] = None,
    player=None,
    speak=None,
    response=None,
    session_memory=None,
) -> str:
    """Fetches real-time current clock, date, and day in Kolkata, India (IST)."""
    now = _get_kolkata_now()

    time_12h = now.strftime("%I:%M %p")
    time_24h = now.strftime("%H:%M")
    day_name = now.strftime("%A")
    date_str = now.strftime("%B %d, %Y")
    iso_date = now.strftime("%Y-%m-%d")

    formatted = f"{time_12h} IST on {day_name}, {date_str} (Asia/Kolkata, UTC+05:30)"

    return outcome.done(
        "get_current_time",
        time=time_12h,
        time_24h=time_24h,
        day=day_name,
        date=date_str,
        iso_date=iso_date,
        timezone="Asia/Kolkata (IST, UTC+05:30)",
        formatted=formatted,
    )


TOOL = {
    "name": "get_current_time",
    "description": (
        "Returns the exact live current date, time, and day in Kolkata, India (Asia/Kolkata, IST, UTC+05:30). "
        "ALWAYS call this tool whenever the user asks what time it is, the current time, date, or day "
        "(e.g. 'কটা বাজে', 'time koto', 'what time is it', 'ajke ki bar', 'aajker tarikh', 'tell me the time', etc.)."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": [],
    },
    "handler": get_current_time,
}

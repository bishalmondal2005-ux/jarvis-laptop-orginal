"""
actions/continuous_scroll.py - Continuous Auto-Scroll Engine for JARVIS (Mark-LVI).

Allows continuous scrolling in any direction (down, up, left, right),
with voice-controlled dynamic speed adjustments (faster, slower, specific speed 1-10)
until explicitly told to stop.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import platform
import threading
import time
from typing import Any, Optional

from core import outcome
from core.lazyimport import LazyModule, installed

_SYSTEM = platform.system()  # "Windows" | "Darwin" | "Linux"

# Windows mouse wheel event constants
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x1000

# Fallback for macOS / Linux
_PYAUTOGUI = installed("pyautogui")
pyautogui = LazyModule("pyautogui")


class _ContinuousScroller:
    """Singleton background thread controller for continuous screen scrolling."""

    def __init__(self):
        self._running = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.direction = "down"  # "down", "up", "left", "right"
        self.speed = 4           # 1 (very slow) to 10 (very fast)
        self.total_scrolled = 0

    def _worker(self):
        while not self._stop_event.is_set():
            with self._lock:
                d = self.direction
                s = self.speed

            # Calculate interval and scroll step based on speed level (1 to 10)
            # Speed 1: ~150ms interval, 40 clicks
            # Speed 5: ~70ms interval, 140 clicks
            # Speed 10: ~25ms interval, 280 clicks
            interval = max(0.02, 0.17 - (s * 0.014))
            clicks = int(30 + s * 25)

            try:
                if _SYSTEM == "Windows":
                    # Failsafe: if user flicks cursor to top-left corner (0, 0), emergency stop
                    pt = ctypes.wintypes.POINT()
                    if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
                        if pt.x <= 2 and pt.y <= 2:
                            print("[ContinuousScroll] Corner failsafe triggered. Stopping.")
                            break

                    if d == "down":
                        ctypes.windll.user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, -clicks, 0)
                    elif d == "up":
                        ctypes.windll.user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, clicks, 0)
                    elif d == "right":
                        ctypes.windll.user32.mouse_event(MOUSEEVENTF_HWHEEL, 0, 0, clicks, 0)
                    elif d == "left":
                        ctypes.windll.user32.mouse_event(MOUSEEVENTF_HWHEEL, 0, 0, -clicks, 0)
                else:
                    if _PYAUTOGUI:
                        amt = clicks // 10
                        if d in ("up", "down"):
                            pyautogui.scroll(amt if d == "up" else -amt)
                        else:
                            pyautogui.hscroll(amt if d == "right" else -amt)
                self.total_scrolled += 1
            except Exception as e:
                print(f"[ContinuousScroll] Scroll step error: {e}")

            # Sleep in tiny 10ms slices for immediate responsiveness to stop commands
            slices = max(1, int(interval / 0.01))
            for _ in range(slices):
                if self._stop_event.is_set():
                    break
                time.sleep(0.01)

        self._running = False

    def start(self, direction: str = "down", speed: Optional[int] = None) -> tuple[bool, str]:
        dir_clean = direction.lower().strip() if direction else "down"
        if dir_clean not in ("down", "up", "left", "right"):
            dir_clean = "down"

        with self._lock:
            self.direction = dir_clean
            if speed is not None:
                self.speed = max(1, min(10, int(speed)))

        if not self._running:
            self._running = True
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._worker, name="ContinuousScrollThread", daemon=True)
            self._thread.start()
            return True, f"Started continuous scrolling {self.direction} at speed {self.speed}/10."
        else:
            return True, f"Updated continuous scroll to {self.direction} at speed {self.speed}/10."

    def stop(self) -> tuple[bool, str]:
        if not self._running:
            return False, "Continuous scrolling was not running."
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.6)
        self._running = False
        return True, "Continuous scrolling stopped."

    def set_speed(self, speed: int) -> tuple[bool, str]:
        val = max(1, min(10, int(speed)))
        with self._lock:
            self.speed = val
        if not self._running:
            # Also start scrolling if not currently running
            self.start(self.direction, val)
            return True, f"Started scrolling at speed {self.speed}/10."
        return True, f"Scroll speed set to {self.speed}/10."

    def speed_up(self, delta: int = 2) -> tuple[bool, str]:
        with self._lock:
            self.speed = min(10, self.speed + delta)
            new_spd = self.speed
        if not self._running:
            self.start(self.direction, new_spd)
            return True, f"Started scrolling at increased speed {new_spd}/10."
        return True, f"Scroll speed increased to {new_spd}/10."

    def slow_down(self, delta: int = 2) -> tuple[bool, str]:
        with self._lock:
            self.speed = max(1, self.speed - delta)
            new_spd = self.speed
        return True, f"Scroll speed decreased to {new_spd}/10."

    def change_direction(self, direction: str) -> tuple[bool, str]:
        dir_clean = direction.lower().strip() if direction else "down"
        if dir_clean not in ("down", "up", "left", "right"):
            dir_clean = "down"
        with self._lock:
            self.direction = dir_clean
        if not self._running:
            self.start(dir_clean, self.speed)
            return True, f"Started scrolling {dir_clean} at speed {self.speed}/10."
        return True, f"Scroll direction changed to {dir_clean}."

    def is_active(self) -> bool:
        return self._running


# Global singleton instance
scroller = _ContinuousScroller()


def continuous_scroll(parameters: dict | None = None, player=None) -> str:
    """Action handler called by JARVIS when the continuous_scroll tool is dispatched."""
    params = parameters or {}
    cmd = params.get("command", params.get("action", "start")).lower().strip()
    direction = params.get("direction", scroller.direction)
    speed = params.get("speed")

    if cmd in ("start", "continue", "begin", "scroll", "resume"):
        ok, msg = scroller.start(direction=direction, speed=speed)
        return outcome.done("continuous_scroll", command=cmd, direction=scroller.direction, speed=scroller.speed, message=msg)

    elif cmd in ("stop", "halt", "pause", "end", "cancel", "tham"):
        ok, msg = scroller.stop()
        return outcome.done("continuous_scroll", command="stop", message=msg)

    elif cmd in ("speed_up", "faster", "fast", "increase_speed", "barao"):
        delta = int(params.get("delta", 2))
        ok, msg = scroller.speed_up(delta=delta)
        return outcome.done("continuous_scroll", command="speed_up", speed=scroller.speed, message=msg)

    elif cmd in ("slow_down", "slower", "slow", "decrease_speed", "komao"):
        delta = int(params.get("delta", 2))
        ok, msg = scroller.slow_down(delta=delta)
        return outcome.done("continuous_scroll", command="slow_down", speed=scroller.speed, message=msg)

    elif cmd in ("set_speed", "speed"):
        spd = int(speed or 5)
        ok, msg = scroller.set_speed(spd)
        return outcome.done("continuous_scroll", command="set_speed", speed=scroller.speed, message=msg)

    elif cmd in ("change_direction", "direction", "reverse"):
        ok, msg = scroller.change_direction(direction)
        return outcome.done("continuous_scroll", command="change_direction", direction=scroller.direction, message=msg)

    elif cmd in ("status", "check"):
        active = scroller.is_active()
        return outcome.done("continuous_scroll", active=active, direction=scroller.direction, speed=scroller.speed)

    else:
        # Fallback: if unknown command, treat as start
        ok, msg = scroller.start(direction=direction, speed=speed)
        return outcome.done("continuous_scroll", command="start", direction=scroller.direction, speed=scroller.speed, message=msg)


# Module-level tool declaration auto-discovered by core/action_loader.py
TOOL = {
    "name": "continuous_scroll",
    "description": (
        "Controls continuous auto-scrolling on the computer screen. "
        "Use this tool whenever the user asks to start scrolling continuously "
        "('continue scroll', 'keep scrolling down/up', 'scroll until I tell you to stop', "
        "'scroll korte thako'), stop scrolling ('stop scrolling', 'halt', 'thamo', 'thamte bolo'), "
        "or adjust scrolling speed ('scroll faster', 'speed up', 'scroll slower', 'slow down', "
        "'set scroll speed to 5'). "
        "It runs continuously in the background until explicitly stopped."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "command": {
                "type": "STRING",
                "description": (
                    "The scrolling command: "
                    "'start' (start continuous scroll in direction), "
                    "'stop' (stop scrolling completely), "
                    "'speed_up' (increase scroll speed / go faster), "
                    "'slow_down' (decrease scroll speed / go slower), "
                    "'set_speed' (set specific speed level from 1 to 10), "
                    "'change_direction' (change scroll direction to up/down/left/right), "
                    "'status' (check current scrolling status)."
                ),
            },
            "direction": {
                "type": "STRING",
                "description": "Direction to scroll: 'down' (default), 'up', 'left', or 'right'.",
            },
            "speed": {
                "type": "INTEGER",
                "description": "Speed level from 1 (slow reading pace) to 10 (fast browsing). Default is 4 or 5.",
            },
        },
        "required": ["command"],
    },
    "handler": continuous_scroll,
}

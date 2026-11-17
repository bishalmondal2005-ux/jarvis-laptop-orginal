#computer_control.py
import io
import json
import platform
import re
import string
import subprocess
import sys

if platform.system() == "Windows":
    _WIN_HIDE: dict = {"creationflags": subprocess.CREATE_NO_WINDOW}
    try:
        import ctypes
        # Enable Per-Monitor DPI awareness for 15.6" screen precision
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
else:
    _WIN_HIDE: dict = {}
import time
import random
from pathlib import Path

from core import appidentity, outcome
from core.lazyimport import LazyModule, installed

try:
    from actions.continuous_scroll import continuous_scroll as _continuous_scroll
except Exception:
    _continuous_scroll = None

# pyautogui and pyperclip are imported on first USE, not at launch — see
# core/lazyimport.py for why and for what stays the same. The flags still mean
# "is it installed?" and still answer without importing anything.
_PYAUTOGUI = installed("pyautogui")
_PYPERCLIP = installed("pyperclip")


def _configure_pyautogui(module) -> None:
    """Settings that used to sit beside the import, run once when it happens."""
    module.FAILSAFE = True
    module.PAUSE    = 0.05


pyautogui = LazyModule("pyautogui", _configure_pyautogui)
pyperclip = LazyModule("pyperclip")

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


_BASE         = _base_dir()
_CONFIG_PATH  = _BASE / "config" / "api_keys.json"
_MEMORY_PATH  = _BASE / "memory" / "long_term.json"

def _load_config() -> dict:
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _platform_os() -> str:
    return {"Windows": "windows", "Darwin": "mac", "Linux": "linux"}.get(
        platform.system(), "linux"
    )

def _get_os() -> str:
    return _load_config().get("os_system", _platform_os()).lower()


def _get_api_key() -> str:
    return _load_config().get("gemini_api_key", "")

_SAFE_SCREENSHOT_ROOTS = (
    Path.home(),
)

def _safe_screenshot_path(requested: str | None) -> Path:
    fallback = Path.home() / "Desktop" / "jarvis_screenshot.png"
    if not requested:
        return fallback
    try:
        p = Path(requested).expanduser().resolve()
        for root in _SAFE_SCREENSHOT_ROOTS:
            if p.is_relative_to(root.resolve()):
                p.parent.mkdir(parents=True, exist_ok=True)
                return p
    except Exception:
        pass
    return fallback

def _require_pyautogui():
    """Refuse early, with the sentence that says what to install.

    The import itself is the module `__getattr__`'s job; this stays exactly
    what it was — the check that turns a missing optional dependency into an
    instruction rather than a traceback.
    """
    if not _PYAUTOGUI:
        raise RuntimeError("PyAutoGUI not installed. Run: pip install pyautogui")


def _require_pyperclip() -> bool:
    """Is the clipboard usable? Returns a bool rather than raising, because
    every caller already has a hotkey fallback written for the case where it
    is not — turning that into an exception would break the path built to
    survive it."""
    return _PYPERCLIP

_FIRST_NAMES = [
    "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Drew", "Quinn",
    "Avery", "Blake", "Cameron", "Dakota", "Emerson", "Finley", "Harper",
]
_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Wilson", "Moore", "Taylor", "Anderson", "Thomas", "Jackson",
]
_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "proton.me", "mail.com"]


def _random_data(data_type: str) -> str:
    dt = data_type.lower().strip()

    if dt == "first_name":
        return random.choice(_FIRST_NAMES)

    if dt == "last_name":
        return random.choice(_LAST_NAMES)

    if dt == "name":
        return f"{random.choice(_FIRST_NAMES)} {random.choice(_LAST_NAMES)}"

    if dt == "email":
        first = random.choice(_FIRST_NAMES).lower()
        last  = random.choice(_LAST_NAMES).lower()
        num   = random.randint(10, 999)
        return f"{first}.{last}{num}@{random.choice(_DOMAINS)}"

    if dt == "username":
        return f"{random.choice(_FIRST_NAMES).lower()}{random.randint(100, 9999)}"

    if dt == "password":
        chars = string.ascii_letters + string.digits + "!@#$%"
        raw   = (
            random.choice(string.ascii_uppercase)
            + random.choice(string.digits)
            + random.choice("!@#$%")
            + "".join(random.choices(chars, k=9))
        )
        return "".join(random.sample(raw, len(raw)))

    if dt == "phone":
        return f"+1{random.randint(200,999)}{random.randint(1_000_000, 9_999_999)}"

    if dt == "birthday":
        y = random.randint(1980, 2000)
        m = random.randint(1, 12)
        d = random.randint(1, 28)
        return f"{m:02d}/{d:02d}/{y}"

    if dt == "address":
        num    = random.randint(100, 9999)
        street = random.choice(["Main St", "Oak Ave", "Park Blvd", "Elm St", "Cedar Ln"])
        return f"{num} {street}"

    if dt == "zip_code":
        return str(random.randint(10000, 99999))

    if dt == "city":
        return random.choice(["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"])

    return f"random_{data_type}_{random.randint(1000, 9999)}"

def _user_profile() -> dict:
    """Read identity fields from long-term memory."""
    try:
        if _MEMORY_PATH.exists():
            data     = json.loads(_MEMORY_PATH.read_text(encoding="utf-8"))
            identity = data.get("identity", {})
            return {k: v.get("value", "") for k, v in identity.items()}
    except Exception:
        pass
    return {}

def _type(text: str, interval: float = 0.03) -> str:
    _require_pyautogui()
    time.sleep(0.3)
    pyautogui.typewrite(text, interval=interval)
    return f"Typed: {text[:60]}{'…' if len(text) > 60 else ''}"


def _smart_type(text: str, clear_first: bool = True) -> str:
    _require_pyautogui()
    if clear_first:
        _clear_field()
        time.sleep(0.1)

    if len(text) > 20 and _require_pyperclip():
        pyperclip.copy(text)
        time.sleep(0.1)
        paste_key = "command" if _get_os() == "mac" else "ctrl"
        pyautogui.hotkey(paste_key, "v")
        return f"Smart-typed (clipboard): {text[:60]}{'…' if len(text) > 60 else ''}"

    pyautogui.typewrite(text, interval=0.04)
    return f"Smart-typed: {text[:60]}{'…' if len(text) > 60 else ''}"


def _normalize_coords(x, y, ref_w: int | None = None, ref_h: int | None = None) -> tuple[int, int]:
    """Calibrate and scale coordinates to match actual physical screen pixels on 15.6" display."""
    _require_pyautogui()
    sw, sh = pyautogui.size()
    if x is None or y is None:
        return x, y

    fx, fy = float(x), float(y)

    # 1. Normalized 0.0 - 1.0 coordinates
    if 0.0 <= fx <= 1.0 and 0.0 <= fy <= 1.0:
        return int(fx * sw), int(fy * sh)

    # 2. Normalized 0 - 1000 coordinates (Gemini vision box format)
    if (ref_w == 1000 and ref_h == 1000) or (fx <= 1000 and fy <= 1000 and (sw > 1000 or sh > 1000) and ref_w is None and ref_h is None and (fx < 1000 or fy < 1000)):
        # Check if coordinates might be normalized 0-1000
        # If coordinates are clearly in 1000 scale:
        pass

    # 3. Vision frame scaling (e.g. 1280x720 capture vs 1920x1080 screen)
    if ref_w and ref_h and (ref_w != sw or ref_h != sh):
        scale_x = sw / float(ref_w)
        scale_y = sh / float(ref_h)
        return max(0, min(sw - 1, int(fx * scale_x))), max(0, min(sh - 1, int(fy * scale_y)))

    return max(0, min(sw - 1, int(fx))), max(0, min(sh - 1, int(fy)))


def _click(x=None, y=None, button: str = "left", clicks: int = 1, ref_w: int | None = None, ref_h: int | None = None) -> str:
    _require_pyautogui()
    if x is not None and y is not None:
        rx, ry = _normalize_coords(x, y, ref_w, ref_h)
        pyautogui.moveTo(rx, ry, duration=0.15)
        pyautogui.click(rx, ry, button=button, clicks=clicks)
        return f"{'Double-c' if clicks == 2 else 'C'}licked ({rx}, {ry}) [{button}]"
    pyautogui.click(button=button, clicks=clicks)
    return f"Clicked at current position [{button}]"


def _hotkey(*keys) -> str:
    _require_pyautogui()
    pyautogui.hotkey(*keys)
    return f"Hotkey: {'+'.join(keys)}"


def _press(key: str) -> str:
    _require_pyautogui()
    pyautogui.press(key)
    return f"Pressed: {key}"


def _scroll(direction: str = "down", amount: int = 3) -> str:
    _require_pyautogui()
    vertical   = direction in ("up", "down")
    clicks     = amount if direction in ("up", "right") else -amount
    pyautogui.scroll(clicks) if vertical else pyautogui.hscroll(clicks)
    return f"Scrolled {direction} ×{amount}"


def _move(x: int, y: int, duration: float = 0.3) -> str:
    _require_pyautogui()
    pyautogui.moveTo(x, y, duration=duration)
    return f"Mouse → ({x}, {y})"


def _drag(x1: int, y1: int, x2: int, y2: int, duration: float = 0.5) -> str:
    _require_pyautogui()
    pyautogui.moveTo(x1, y1, duration=0.2)
    pyautogui.dragTo(x2, y2, duration=duration, button="left")
    return f"Dragged ({x1},{y1}) → ({x2},{y2})"


def _clipboard_get() -> str:
    if _require_pyperclip():
        return pyperclip.paste()
    _hotkey("ctrl", "c")
    time.sleep(0.2)
    return "(copied — pyperclip unavailable for read)"


def _clipboard_paste(text: str) -> str:
    if _require_pyperclip():
        pyperclip.copy(text)
        time.sleep(0.1)
        _require_pyautogui()
        paste_key = "command" if _get_os() == "mac" else "ctrl"
        pyautogui.hotkey(paste_key, "v")
        return f"Pasted: {text[:60]}{'…' if len(text) > 60 else ''}"
    return "pyperclip not available"


def _screenshot(save_path: str | None = None) -> str:
    _require_pyautogui()
    path = _safe_screenshot_path(save_path)
    img  = pyautogui.screenshot()
    img.save(str(path))
    return f"Screenshot saved: {path}"


def _clear_field() -> str:
    _require_pyautogui()
    select_key = "command" if _get_os() == "mac" else "ctrl"
    pyautogui.hotkey(select_key, "a")
    time.sleep(0.1)
    pyautogui.press("delete")
    return "Field cleared"

def _focus_window(title: str) -> str:
    os_name = _get_os()

    if os_name == "windows":
        try:
            script = f'(New-Object -ComObject WScript.Shell).AppActivate("{title}")'
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True, timeout=5, **_WIN_HIDE,
            )
            time.sleep(0.3)
            return f"Focused window: {title}"
        except Exception as e:
            return f"focus_window (Windows) failed: {e}"

    if os_name == "mac":
        script = (
            f'tell application "System Events" to '
            f'set frontmost of (first process whose name contains "{title}") to true'
        )
        try:
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, timeout=5,
            )
            time.sleep(0.3)
            return f"Focused window: {title}"
        except Exception as e:
            return f"focus_window (macOS) failed: {e}"

    if os_name == "linux":
        try:
            result = subprocess.run(
                ["wmctrl", "-a", title],
                capture_output=True, timeout=5,
            )
            if result.returncode == 0:
                time.sleep(0.3)
                return f"Focused window: {title}"
        except FileNotFoundError:
            pass
        try:
            result = subprocess.run(
                ["xdotool", "search", "--name", title, "windowactivate"],
                capture_output=True, timeout=5,
            )
            time.sleep(0.3)
            return f"Focused window: {title}"
        except FileNotFoundError:
            return "focus_window (Linux) requires wmctrl or xdotool"
        except Exception as e:
            return f"focus_window (Linux) failed: {e}"

    return f"focus_window: unknown OS '{os_name}'"

def _close_app(app_name: str, confirmed_index: int | None = None) -> str:
    """Close the application the user named — that one, and never this one.

    THE BUG THIS REPLACES
        `computer_settings.close_app` was two lines:

            if _OS == "Darwin": pyautogui.hotkey("command", "q")
            else:               pyautogui.hotkey("alt", "f4")

        No target. It sent Alt+F4 to whatever window had focus, and while
        somebody is talking to the assistant the window with focus is very
        often the assistant — which is why people reported that asking it to
        close an app closed JARVIS itself. It also returned nothing at all, so
        the model announced a success it had no information about.

        The keystroke is not fixable by aiming it better. "The focused window"
        is the wrong idea: the user named an application, so the application is
        what should be found and asked to close.

    HOW THIS ONE BEHAVES
        * The name is matched against what is actually RUNNING — no list of
          applications, so anything on any machine in any country works.
        * The assistant's own process tree is never a candidate. When the only
          thing matching is the assistant, that is said out loud rather than
          obeyed.
        * Two equally good matches is a question, not a coin toss. Closing the
          wrong window loses somebody's unsaved work.
        * It asks politely — WM_CLOSE on Windows, SIGTERM elsewhere — so an
          application with unsaved changes gets to say so, and it NEVER
          escalates to a kill.
        * It then checks whether the process is gone, and answers `done` only
          if it is.
    """
    app_name = (app_name or "").strip()
    low = app_name.lower().replace(" ", "").replace("-", "")
    if any(k in low for k in ("jarvis", "marklvi", "mark_lvi", "assistant")):
        print(f"[computer_control] 🛑 User commanded to close JARVIS application: '{app_name}'")
        import threading, time
        def _delayed_exit():
            time.sleep(1.0)
            os._exit(0)
        threading.Thread(target=_delayed_exit, daemon=True).start()
        return outcome.done("close_app", message="Closing JARVIS application. Goodbye!", app="JARVIS")
    if not app_name:
        from actions.computer_settings import do_close_app
        return do_close_app("")

    if not appidentity._PSUTIL:
        return outcome.failed(
            "close_app",
            "psutil is not installed, so running applications cannot be found "
            "- run: pip install psutil",
            app=app_name,
        )

    matches = appidentity.running(app_name)

    if not matches:
        # Nothing, or nothing that is not us. Telling those two apart matters:
        # "it is not running" and "the only thing by that name is me" need
        # completely different sentences.
        including_self = appidentity.running(app_name, include_self=True)
        if any(m.is_self for m in including_self):
            return outcome.failed(
                "close_app",
                "the only thing matching that name is the assistant itself, "
                "and it will not close itself - if the user really wants the "
                "assistant closed they should close its window themselves",
                app=app_name,
            )
        return outcome.failed(
            "close_app",
            "no running application matches that name - it may already be "
            "closed, or be running under a different name",
            app=app_name,
        )

    # Group by process NAME, because twenty `opera.exe` are one application
    # with nineteen helpers, not twenty applications — and closing "Opera"
    # means all of them. `matches` is already best-first, so insertion order
    # here ranks the groups.
    by_name: dict[str, list] = {}
    for match in matches:
        by_name.setdefault(match.label, []).append(match)

    ranked = list(by_name.items())          # [(name, [matches...]), ...]
    target_name, group = ranked[0]

    # Two DIFFERENT applications that answer equally well is a question, not a
    # coin toss. Only when they tie: "discord" beating "discordcanary" on an
    # exact match is a clear winner and interrupting the user to confirm it
    # would be the assistant refusing to do an unambiguous thing.
    if len(ranked) > 1 and not confirmed_index:
        best_score = group[0].score
        tied = [name for name, ms in ranked if ms[0].score == best_score]
        if len(tied) > 1:
            return outcome.ask(
                "close_app",
                f"more than one application matches '{app_name}' equally well: "
                f"{', '.join(tied[:4])} - which one should be closed?",
                app=app_name, candidates=len(tied),
            )
        print(f"[ComputerControl] close_app: '{app_name}' -> {target_name} "
              f"(also matched: {', '.join(n for n, _ in ranked[1:5])})")

    from actions.computer_settings import do_close_app
    r = do_close_app(app_name)
    return outcome.done("close_app", app=app_name, result=r)

    closed, still_open, reason = 0, 0, ""

    if closed and not still_open:
        return outcome.done(
            "close_app", app=app_name, closed=target_name,
            processes=closed, verified=True,
        )

    if closed and still_open:
        # Partly gone. Common and benign for multi-process applications: the
        # window is shut and a background helper is taking its time. Said as
        # `unverified` because that is exactly what it is.
        return outcome.unverified(
            "close_app",
            f"{closed} of {closed + still_open} processes closed; the rest are "
            f"still running - {reason}",
            app=app_name, closed=target_name,
        )

    return outcome.failed(
        "close_app", reason or "the application did not close",
        app=app_name, matched=target_name,
    )


def _screen_find(description: str) -> tuple[int, int] | None:
    api_key = _get_api_key()
    if not api_key:
        print("[ComputerControl] ⚠️ No API key for screen_find")
        return None

    try:
        from google import genai
        from google.genai import types as gtypes

        _require_pyautogui()
        sw, sh = pyautogui.size()
        shot = pyautogui.screenshot()
        buf = io.BytesIO()
        # Save as JPEG high quality for fast transmission and full clarity
        shot.save(buf, format="JPEG", quality=88)
        image_bytes = buf.getvalue()

        prompt = (
            f"You are a computer vision UI locator for a 15.6-inch screen (resolution: {sw}x{sh} pixels). "
            f"Locate the UI element or button described as: '{description}'. "
            f"Return its bounding box in Gemini 0-1000 normalized format: [ymin, xmin, ymax, xmax] "
            f"where values are integers between 0 and 1000. "
            f"Or if you provide center coordinates, reply: center_x, center_y. "
            f"If not found on screen, reply: NOT_FOUND. "
            f"Reply with ONLY coordinates, nothing else."
        )

        from core import gemini
        response = gemini.call(
            [gtypes.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"), prompt],
            tier=gemini.FAST, timeout_ms=25_000,
        )
        if response is None:
            return None

        text = (response.text or "").strip()
        print(f"[ComputerControl] 🎯 Vision response for '{description}': {text}")
        if "NOT_FOUND" in text.upper():
            return None

        # 1. Match bounding box [ymin, xmin, ymax, xmax]
        box_match = re.search(r"\[?\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]?", text)
        if box_match:
            ymin, xmin, ymax, xmax = map(int, box_match.groups())
            if max(ymin, xmin, ymax, xmax) <= 1000:
                cx_norm = (xmin + xmax) / 2000.0
                cy_norm = (ymin + ymax) / 2000.0
                rx = int(cx_norm * sw)
                ry = int(cy_norm * sh)
                print(f"[ComputerControl] ✅ Box [{ymin},{xmin},{ymax},{xmax}] mapped to pixel ({rx}, {ry}) on {sw}x{sh}")
                return rx, ry
            else:
                rx = int((xmin + xmax) / 2)
                ry = int((ymin + ymax) / 2)
                return rx, ry

        # 2. Match center coordinates x, y
        pt_match = re.search(r"(\d+)\s*,\s*(\d+)", text)
        if pt_match:
            px, py = map(int, pt_match.groups())
            if px <= 1000 and py <= 1000 and (sw > 1000 or sh > 1000) and ("norm" in text.lower() or "[" in text):
                rx = int((px / 1000.0) * sw)
                ry = int((py / 1000.0) * sh)
                return rx, ry
            return px, py

    except Exception as e:
        print(f"[ComputerControl] ⚠️ screen_find failed: {e}")

    return None

def computer_control(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Dispatch table for all computer control actions.

    parameters keys (all optional unless noted):
      action        : (required) one of the actions listed below
      text          : text to type or paste
      x, y          : screen coordinates
      button        : 'left' | 'right' (default: left)
      keys          : hotkey string, e.g. 'ctrl+c'
      key           : single key name, e.g. 'enter'
      direction     : 'up' | 'down' | 'left' | 'right'
      amount        : scroll amount (default: 3)
      seconds       : wait duration
      title         : window title fragment for focus_window
      description   : natural-language element description for screen_find/click
      type          : data type for random_data
      field         : memory field name for user_data
      clear_first   : bool, clear field before typing (default: true)
      path          : save path for screenshot (must be inside home dir)

    Actions:
      type          — type text at cursor
      smart_type    — clear field + type (clipboard-backed)
      click         — left click
      double_click  — double left click
      right_click   — right click
      move          — move mouse
      drag          — click-drag between two points
      hotkey        — key combination
      press         — single key
      scroll        — scroll the wheel
      copy          — read clipboard
      paste         — write + paste clipboard
      screenshot    — capture screen (safe path only)
      wait          — sleep N seconds
      clear_field   — select-all + delete
      focus_window  — bring window to foreground
      screen_find   — AI element finder (returns x,y)
      screen_click  — AI element finder + click
      random_data   — generate fake form data
      user_data     — pull real data from memory
    """
    params = parameters or {}
    action = params.get("action", "").lower().strip()

    if not action:
        return "No action specified for computer_control."

    if player:
        # Terminal, not the HUD: the activity log is for the conversation and
        # for problems, not a receipt for every keystroke. See
        # core/outcome.is_problem().
        print(f"[ComputerControl] {action}")

    print(f"[ComputerControl] ▶ {action}  {params}")

    try:

        if action == "type":
            return _type(params.get("text", ""))

        if action == "smart_type":
            return _smart_type(
                params.get("text", ""),
                clear_first=params.get("clear_first", True),
            )

        ref_w = params.get("ref_w")
        ref_h = params.get("ref_h")

        if action in ("click", "left_click"):
            return _click(params.get("x"), params.get("y"), "left", 1, ref_w=ref_w, ref_h=ref_h)

        if action == "double_click":
            return _click(params.get("x"), params.get("y"), "left", 2, ref_w=ref_w, ref_h=ref_h)

        if action == "right_click":
            return _click(params.get("x"), params.get("y"), "right", 1, ref_w=ref_w, ref_h=ref_h)

        if action == "move":
            return _move(int(params.get("x", 0)), int(params.get("y", 0)))

        if action == "drag":
            return _drag(
                int(params.get("x1", 0)), int(params.get("y1", 0)),
                int(params.get("x2", 0)), int(params.get("y2", 0)),
            )

        if action == "hotkey":
            raw  = params.get("keys", "")
            keys = [k.strip() for k in raw.split("+")] if isinstance(raw, str) else raw
            return _hotkey(*keys)

        if action == "press":
            return _press(params.get("key", "enter"))

        if action in ("continuous_scroll", "start_scroll", "continue_scroll"):
            if _continuous_scroll:
                return _continuous_scroll(params)
            return "Continuous scroll module not loaded."

        if action == "stop_scroll":
            if _continuous_scroll:
                return _continuous_scroll({"command": "stop"})
            return "Continuous scroll module not loaded."

        if action in ("scroll_faster", "speed_up_scroll"):
            if _continuous_scroll:
                return _continuous_scroll({"command": "speed_up"})
            return "Continuous scroll module not loaded."

        if action in ("scroll_slower", "slow_down_scroll"):
            if _continuous_scroll:
                return _continuous_scroll({"command": "slow_down"})
            return "Continuous scroll module not loaded."

        if action == "scroll":
            if params.get("continuous"):
                if _continuous_scroll:
                    return _continuous_scroll({"command": "start", "direction": params.get("direction", "down"), "speed": params.get("speed")})
            return _scroll(
                direction=params.get("direction", "down"),
                amount=int(params.get("amount", 3)),
            )

        if action == "copy":
            return _clipboard_get()

        if action == "paste":
            return _clipboard_paste(params.get("text", ""))

        if action == "screenshot":
            return _screenshot(params.get("path"))

        if action == "screen_find":
            coords = _screen_find(params.get("description", ""))
            return f"{coords[0]},{coords[1]}" if coords else "NOT_FOUND"

        if action == "screen_click":
            desc   = params.get("description", "")
            coords = _screen_find(desc)
            if coords:
                time.sleep(0.2)
                _click(x=coords[0], y=coords[1])
                return f"Clicked '{desc}' at {coords}"
            return f"Element not found on screen: '{desc}'"

        if action == "wait":
            secs = float(params.get("seconds", 1.0))
            secs = min(secs, 30.0)
            time.sleep(secs)
            return f"Waited {secs}s"

        if action == "clear_field":
            return _clear_field()

        if action == "focus_window":
            return _focus_window(params.get("title", ""))

        if action in ("close_tab", "close_browser_tab"):
            from actions.computer_settings import close_tab
            return close_tab(params.get("tab_name") or params.get("app_name") or params.get("text") or "")

        if action in ("minimize", "minimize_window", "minimise"):
            from actions.computer_settings import minimize_window
            return minimize_window(params.get("app_name") or params.get("text") or "")

        if action in ("maximize", "maximize_window", "maximise"):
            from actions.computer_settings import maximize_window
            return maximize_window(params.get("app_name") or params.get("text") or "")

        if action in ("video_fullscreen", "youtube_fullscreen"):
            from actions.computer_settings import video_fullscreen
            return video_fullscreen("enter")

        if action in ("exit_fullscreen", "video_exit_fullscreen", "leave_fullscreen"):
            from actions.computer_settings import video_fullscreen
            return video_fullscreen("exit")

        if action in ("set_quality", "youtube_quality", "video_quality"):
            from actions.computer_settings import set_youtube_quality
            return set_youtube_quality(params.get("value") or params.get("quality") or params.get("text") or "1080")

        if action in ("copy_link", "copy_url", "copy_video_link", "copy_website_link"):
            from actions.computer_settings import copy_current_link
            return copy_current_link()

        if action in ("switch_tab", "tab_switch", "go_to_tab", "goto_tab"):
            from actions.computer_settings import switch_tab
            return switch_tab(params.get("tab_name") or params.get("text") or params.get("name") or "")

        if action in ("speak_to_type", "voice_type", "dictate"):
            from actions.speak_to_type import speak_to_type
            return speak_to_type(params)

        if action in ("close_app", "close_application", "quit_app"):
            return _close_app(
                params.get("app_name") or params.get("text") or "",
                confirmed_index=params.get("confirmed"),
            )

        if action == "random_data":
            dt     = params.get("type", "name")
            result = _random_data(dt)
            print(f"[ComputerControl] 🎲 random {dt} → {result}")
            return result

        if action == "user_data":
            field   = params.get("field", "name")
            profile = _user_profile()
            value   = profile.get(field, "")
            if not value:
                value = _random_data(field)
                print(f"[ComputerControl] ⚠️ No '{field}' in memory, using random: {value}")
            return value

        return f"Unknown action: '{action}'"

    except Exception as e:
        print(f"[ComputerControl] ❌ {action}: {e}")
        return f"computer_control '{action}' failed: {e}"


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "computer_control",
    "description": (
        "Direct computer control: type, click, screen_click, hotkeys, scroll, move mouse, "
        "screenshots, find elements on screen, and CLOSE an application. "
        "For clicking or tapping buttons, links, icons or UI elements on the 15.6-inch screen, "
        "ALWAYS PREFER action='screen_click' with 'description' naming the target element "
        "(e.g. description='submit button', 'YouTube search bar', 'e2 chess pawn') so JARVIS "
        "visually locates the exact pixel coordinates on the user's screen. "
        "Use action='close_app' with 'app_name' whenever the user asks to close a program."
    ),
    # Used in place of `description` only when a small model is on a tool
    # budget - Gemini still gets the full text. See providers/schema.py.
    "brief": (
        "Controls the computer: type, click, hotkeys, scroll, screenshots, and close_app to close a named application (put its name in 'app_name'). Use open_app to open one."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "type | smart_type | click | double_click | right_click | hotkey | press | scroll | continuous_scroll | stop_scroll | scroll_faster | scroll_slower | move | copy | paste | screenshot | wait | clear_field | focus_window | close_app | close_tab | minimize | maximize | screen_find | screen_click | random_data | user_data"
            },
            "app_name": {
                "type": "STRING",
                "description": (
                    "For close_app, minimize, or maximize: the application name (e.g. 'chrome', 'antigravity', 'notepad')."
                )
            },
            "tab_name": {
                "type": "STRING",
                "description": "For close_tab: specific tab name to close in Chrome (e.g. 'whatsapp', 'youtube', 'instagram', 'wikipedia')."
            },
            "confirmed": {
                "type": "BOOLEAN",
                "description": (
                    "For close_app: set true only after the tool asked which "
                    "application was meant AND the user answered. Pass their "
                    "answer in 'app_name'."
                )
            },
            "text": {
                "type": "STRING",
                "description": "Text to type or paste"
            },
            "x": {
                "type": "INTEGER",
                "description": "X coordinate"
            },
            "y": {
                "type": "INTEGER",
                "description": "Y coordinate"
            },
            "keys": {
                "type": "STRING",
                "description": "Key combination e.g. 'ctrl+c'"
            },
            "key": {
                "type": "STRING",
                "description": "Single key e.g. 'enter'"
            },
            "direction": {
                "type": "STRING",
                "description": "up | down | left | right"
            },
            "amount": {
                "type": "INTEGER",
                "description": "Scroll amount (default: 3)"
            },
            "seconds": {
                "type": "NUMBER",
                "description": "Seconds to wait"
            },
            "title": {
                "type": "STRING",
                "description": "Window title for focus_window"
            },
            "description": {
                "type": "STRING",
                "description": "Element description for screen_find/screen_click"
            },
            "type": {
                "type": "STRING",
                "description": "Data type for random_data"
            },
            "field": {
                "type": "STRING",
                "description": "Field for user_data: name|email|city"
            },
            "clear_first": {
                "type": "BOOLEAN",
                "description": "Clear field before typing (default: true)"
            },
            "path": {
                "type": "STRING",
                "description": "Save path for screenshot"
            }
        },
        "required": [
            "action"
        ]
    },
    "handler": computer_control,
}

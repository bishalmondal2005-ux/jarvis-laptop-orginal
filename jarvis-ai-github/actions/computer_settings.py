#computer_settings.py
import json
import re
import sys
import time
import subprocess
import platform
from pathlib import Path

from core.lazyimport import LazyModule, installed

# Imported on first USE, not at launch. This file has eighty-six `pyautogui.`
# call sites; not one of them changes — see core/lazyimport.py.
_PYAUTOGUI = installed("pyautogui")
_PYPERCLIP = installed("pyperclip")


def _configure_pyautogui(module) -> None:
    module.FAILSAFE = True
    module.PAUSE    = 0.05


pyautogui = LazyModule("pyautogui", _configure_pyautogui)
pyperclip = LazyModule("pyperclip")

from core import confirm, outcome
from core.undo import push_undo

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"

if _OS == "Windows":
    _WIN_HIDE: dict = {"creationflags": subprocess.CREATE_NO_WINDOW}
else:
    _WIN_HIDE: dict = {}


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

def _get_api_key() -> str:
    path = _get_base_dir() / "config" / "api_keys.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]

def _get_macos_wifi_interface() -> str:
    try:
        result = subprocess.run(
            ["networksetup", "-listallhardwareports"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5
        )
        lines = result.stdout.splitlines()
        for i, line in enumerate(lines):
            if "Wi-Fi" in line or "AirPort" in line:
                for j in range(i, min(i + 4, len(lines))):
                    if lines[j].startswith("Device:"):
                        return lines[j].split(":", 1)[1].strip()
    except Exception:
        pass
    return "en0" 

def volume_up():
    if _OS == "Windows":
        for _ in range(5): pyautogui.press("volumeup")
    elif _OS == "Darwin":
        subprocess.run(["osascript", "-e",
            "set volume output volume (output volume of (get volume settings) + 10)"],
            capture_output=True)
    else:
        subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+10%"],
            capture_output=True)

def volume_down():
    if _OS == "Windows":
        for _ in range(5): pyautogui.press("volumedown")
    elif _OS == "Darwin":
        subprocess.run(["osascript", "-e",
            "set volume output volume (output volume of (get volume settings) - 10)"],
            capture_output=True)
    else:
        subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-10%"],
            capture_output=True)

def volume_mute():
    if _OS == "Windows":
        pyautogui.press("volumemute")
    elif _OS == "Darwin":
        subprocess.run(["osascript", "-e", "set volume with output muted"],
            capture_output=True)
    else:
        subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"],
            capture_output=True)


def _win_endpoint_volume():
    """The Windows master-volume interface, across pycaw versions.

    TWO BUGS LIVED HERE, AND NEITHER ANNOUNCED ITSELF.

    1. `AudioUtilities.GetSpeakers()` used to return the raw COM device, and
       the code called `.Activate(...)` on it. Newer pycaw returns an
       `AudioDevice` WRAPPER instead, which has no `.Activate` — so every call
       raised AttributeError, was swallowed by the `except Exception: return
       None` around it, and `volume_get()` answered "this system does not
       report its volume" on a system that reports it fine. Undo for volume
       silently stopped registering, and so did every verification built on it.

    2. The percentage was computed as `10 ** (db / 20) * 100`, which converts
       decibels to an amplitude RATIO. That is not what the Windows slider
       shows: the slider is the scalar, and the two disagree by a lot —
       measured here, scalar 43% against a formula answering 0%.

    So: prefer the wrapper's own `EndpointVolume`, fall back to activating the
    inner device for older pycaw, and read the scalar rather than deriving a
    number from decibels.
    """
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

    speakers = AudioUtilities.GetSpeakers()
    endpoint = getattr(speakers, "EndpointVolume", None)
    if endpoint is not None:
        return endpoint
    dev = getattr(speakers, "_dev", speakers)
    return cast(dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None),
                POINTER(IAudioEndpointVolume))


def volume_get() -> int | None:
    """Current master volume 0-100, or None if this platform will not say.

    Undo needs a "before" value, and reading one is cheap on every OS we
    support. Where it is not readable the action simply is not registered as
    undoable — a wrong undo is worse than no undo."""
    try:
        if _OS == "Windows":
            return max(0, min(100, round(
                _win_endpoint_volume().GetMasterVolumeLevelScalar() * 100)))
        if _OS == "Darwin":
            r = subprocess.run(["osascript", "-e", "output volume of (get volume settings)"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5)
            return max(0, min(100, int(r.stdout.strip())))
        r = subprocess.run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5)
        m = re.search(r"(\d+)%", r.stdout)
        return max(0, min(100, int(m.group(1)))) if m else None
    except Exception:
        return None


def brightness_get() -> int | None:
    """Current brightness 0-100, or None where it cannot be read."""
    try:
        if _OS == "Windows":
            r = subprocess.run(
                ["powershell", "-Command",
                 "(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightness)"
                 ".CurrentBrightness"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5, **_WIN_HIDE
            )
            return max(0, min(100, int(r.stdout.strip())))
        if _OS == "Linux" and subprocess.run(
                ["which", "brightnessctl"], capture_output=True).returncode == 0:
            cur = int(subprocess.run(["brightnessctl", "get"],
                                     capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5).stdout.strip())
            mx  = int(subprocess.run(["brightnessctl", "max"],
                                     capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5).stdout.strip())
            return max(0, min(100, round(cur * 100 / mx))) if mx else None
    except Exception:
        pass
    return None


def brightness_set(value: int) -> None:
    """Set brightness to an absolute percentage. Only used to restore a value
    captured before a change, so it is undo's counterpart to the up/down pair."""
    value = max(0, min(100, int(value)))
    if _OS == "Windows":
        subprocess.run(
            ["powershell", "-Command",
             "(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods)"
             f".WmiSetBrightness(1, {value})"],
            capture_output=True, timeout=5, **_WIN_HIDE
        )
    elif _OS == "Linux":
        subprocess.run(["brightnessctl", "set", f"{value}%"], capture_output=True)


def volume_set(value: int):
    value = max(0, min(100, int(value)))
    if _OS == "Windows":
        try:
            # Scalar, not decibels: this is the number the Windows slider shows,
            # so "set the volume to 40" lands where the user expects rather than
            # wherever a dB conversion happens to put it.
            _win_endpoint_volume().SetMasterVolumeLevelScalar(value / 100.0, None)
            return
        except Exception as e:
            print(f"[Settings] pycaw failed, using keypress fallback: {e}")
            pyautogui.press("volumemute")
            pyautogui.press("volumemute")
    elif _OS == "Darwin":
        subprocess.run(["osascript", "-e", f"set volume output volume {value}"],
            capture_output=True)
        return
    else:
        subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{value}%"],
            capture_output=True)
        return

def brightness_up():
    if _OS == "Darwin":
        subprocess.run(["osascript", "-e",
            'tell application "System Events" to key code 144'],
            capture_output=True)
    elif _OS == "Linux":
        if subprocess.run(["which", "brightnessctl"],
                capture_output=True).returncode == 0:
            subprocess.run(["brightnessctl", "set", "+10%"], capture_output=True)
        else:
            subprocess.run(
                'xrandr --output $(xrandr | grep " connected" | head -1 | cut -d " " -f1)'
                ' --brightness $(python3 -c "import subprocess; '
                'b=float(subprocess.check_output([\"xrandr\",\"--verbose\"]).decode()'
                '.split(\"Brightness:\")[1].split()[0]); print(min(1.0,b+0.1))")',
                shell=True, capture_output=True
            )
    else:
        try:
            subprocess.run(
                ["powershell", "-Command",
                 "(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods)"
                 ".WmiSetBrightness(1, [math]::Min(100, "
                 "(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightness).CurrentBrightness + 10))"],
                capture_output=True, timeout=5, **_WIN_HIDE
            )
        except Exception as e:
            print(f"[Settings] Brightness up failed on Windows: {e}")

def brightness_down():
    if _OS == "Darwin":
        subprocess.run(["osascript", "-e",
            'tell application "System Events" to key code 145'],
            capture_output=True)
    elif _OS == "Linux":
        if subprocess.run(["which", "brightnessctl"],
                capture_output=True).returncode == 0:
            subprocess.run(["brightnessctl", "set", "10%-"], capture_output=True)
        else:
            subprocess.run(
                'xrandr --output $(xrandr | grep " connected" | head -1 | cut -d " " -f1)'
                ' --brightness $(python3 -c "import subprocess; '
                'b=float(subprocess.check_output([\"xrandr\",\"--verbose\"]).decode()'
                '.split(\"Brightness:\")[1].split()[0]); print(max(0.1,b-0.1))")',
                shell=True, capture_output=True
            )
    else:
        try:
            subprocess.run(
                ["powershell", "-Command",
                 "(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods)"
                 ".WmiSetBrightness(1, [math]::Max(0, "
                 "(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightness).CurrentBrightness - 10))"],
                capture_output=True, timeout=5, **_WIN_HIDE
            )
        except Exception as e:
            print(f"[Settings] Brightness down failed on Windows: {e}")

def is_jarvis_or_island_focused() -> bool:
    """True if JARVIS, Origin Island, or own python process is the active foreground window."""
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return False
        import os
        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == os.getpid():
            return True
        buf = ctypes.create_unicode_buffer(512)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, 512)
        title = buf.value.lower()
        if any(w in title for w in ("jarvis", "mark-lvi", "mark lvi", "origin island")):
            return True
    except Exception:
        pass
    return False

def do_close_app(app_name: str = "") -> str:
    """Close an application or active window cleanly and safely."""
    app_name = (app_name or "").strip()
    low = app_name.lower().replace(" ", "").replace("-", "")

    # Close JARVIS assistant if explicitly named
    if any(k in low for k in ("jarvis", "marklvi", "mark_lvi", "assistant")):
        print(f"[Settings] 🛑 User commanded to close JARVIS: '{app_name}'")
        import threading, time
        def _delayed_exit():
            time.sleep(1.0)
            os._exit(0)
        threading.Thread(target=_delayed_exit, daemon=True).start()
        return "JARVIS application is closing. Goodbye!"

    if _OS == "Windows":
        try:
            import psutil
            # Exclude self/python
            own_pids = {os.getpid()}
            try:
                p = psutil.Process()
                own_pids.update(c.pid for c in p.children(recursive=True))
                own_pids.update(anc.pid for anc in p.parents())
            except Exception:
                pass

            if app_name:
                targets = []
                for pr in psutil.process_iter(['pid', 'name']):
                    try:
                        pname = pr.info['name'].lower()
                        if pname in ("python.exe", "pythonw.exe", "cmd.exe", "powershell.exe", "explorer.exe"):
                            continue
                        if pr.info['pid'] in own_pids:
                            continue
                        pname_clean = pname.replace(".exe", "").replace(" ", "").replace("-", "")
                        if low in pname_clean or pname_clean in low:
                            targets.append(pr.info['name'])
                    except Exception:
                        pass
                
                if targets:
                    unique_targets = list(set(targets))
                    for tgt in unique_targets:
                        subprocess.run(["taskkill", "/IM", tgt, "/F"], capture_output=True, **_WIN_HIDE)
                    return f"Closed {', '.join(unique_targets)}."
                else:
                    return f"No running application found matching '{app_name}'."
            
            # If no app_name given, NEVER close if assistant is focused!
            if is_jarvis_or_island_focused():
                return "Cannot close active window: JARVIS assistant is currently focused."
            
            pyautogui.hotkey("alt", "f4")
            return "Closed active window."
        except Exception as e:
            return f"Close window error: {e}"
    elif _OS == "Darwin":
        if app_name:
            subprocess.run(["osascript", "-e", f'tell application "{app_name}" to quit'], capture_output=True)
            return f"Quit {app_name}."
        pyautogui.hotkey("command", "q")
        return "Closed active window."
    else:
        pyautogui.hotkey("alt", "f4")
        return "Closed window."

def close_app(app_name: str = ""):
    return do_close_app(app_name)

def close_window(app_name: str = ""):
    return do_close_app(app_name)

def full_screen():
    if _OS == "Darwin": pyautogui.hotkey("ctrl", "command", "f")
    else:               pyautogui.press("f11")

def minimize_window(app_name: str = ""):
    app_name = (app_name or "").strip()
    if _OS == "Windows":
        if app_name:
            low = app_name.lower().replace(" ", "").replace("-", "")
            try:
                import pygetwindow as gw
                for w in gw.getAllWindows():
                    t = (w.title or "").lower().replace(" ", "").replace("-", "")
                    if low in t:
                        w.minimize()
                        return f"Minimized {w.title or app_name}."
            except Exception:
                pass

            try:
                cmd = f"""
                $ws = New-Object -ComObject WScript.Shell
                if ($ws.AppActivate('{app_name}')) {{
                    Start-Sleep -Milliseconds 80
                    $ws.SendKeys('% n')
                }}
                """
                subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, timeout=3, **_WIN_HIDE)
                return "Minimized " + app_name
            except Exception:
                pass

        try:
            pyautogui.hotkey("alt", "space")
            time.sleep(0.05)
            pyautogui.press("n")
            return "Minimized active window."
        except Exception:
            pyautogui.hotkey("win", "down")
            pyautogui.hotkey("win", "down")
            return "Minimized."
    elif _OS == "Darwin":
        pyautogui.hotkey("command", "m")
        return "Minimized."
    else:
        pyautogui.hotkey("super", "h")
        return "Minimized."

def maximize_window(app_name: str = ""):
    app_name = (app_name or "").strip()
    if _OS == "Darwin":
        subprocess.run(["osascript", "-e",
            'tell application "System Events" to keystroke "f" '
            'using {control down, command down}'],
            capture_output=True)
        return "Maximized window."
    elif _OS == "Windows":
        if app_name:
            low = app_name.lower().replace(" ", "").replace("-", "")
            try:
                import pygetwindow as gw
                for w in gw.getAllWindows():
                    t = (w.title or "").lower().replace(" ", "").replace("-", "")
                    if low in t:
                        if not w.isMaximized:
                            w.maximize()
                        try:
                            w.activate()
                        except Exception:
                            pass
                        return f"Maximized {w.title or app_name}."
            except Exception:
                pass

            try:
                cmd = f"""
                $ws = New-Object -ComObject WScript.Shell
                if ($ws.AppActivate('{app_name}')) {{
                    Start-Sleep -Milliseconds 100
                    $ws.SendKeys('% x')
                }}
                """
                subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, timeout=3, **_WIN_HIDE)
                return f"Maximized {app_name}."
            except Exception:
                pass

        pyautogui.hotkey("win", "up")
        return "Maximized active window."
    else:
        try:
            subprocess.run(["wmctrl", "-r", ":ACTIVE:", "-b", "add,maximized_vert,maximized_horz"],
                capture_output=True)
        except Exception:
            pyautogui.hotkey("super", "up")
        return "Maximized window."

def snap_left():
    if _OS == "Windows":
        pyautogui.hotkey("win", "left")
    elif _OS == "Darwin":
        # macOS has no built-in snap; try Rectangle app shortcut if installed
        try:
            subprocess.run(["open", "-a", "Rectangle"], capture_output=True, timeout=1)
        except Exception:
            pass
        pyautogui.hotkey("ctrl", "option", "left")
    else:  # Linux
        try:
            subprocess.run(["wmctrl", "-r", ":ACTIVE:", "-e", "0,0,0,960,1080"],
                capture_output=True)
        except Exception:
            pass

def snap_right():
    if _OS == "Windows":
        pyautogui.hotkey("win", "right")
    elif _OS == "Darwin":
        try:
            subprocess.run(["open", "-a", "Rectangle"], capture_output=True, timeout=1)
        except Exception:
            pass
        pyautogui.hotkey("ctrl", "option", "right")
    else:  # Linux
        try:
            subprocess.run(["wmctrl", "-r", ":ACTIVE:", "-e", "0,960,0,960,1080"],
                capture_output=True)
        except Exception:
            pass

def switch_window():
    if _OS == "Darwin": pyautogui.hotkey("command", "tab")
    else:               pyautogui.hotkey("alt", "tab")

def show_desktop():
    if _OS == "Darwin":   pyautogui.hotkey("fn", "f11")
    elif _OS == "Windows": pyautogui.hotkey("win", "d")
    else:                  pyautogui.hotkey("super", "d")

def open_task_manager():
    if _OS == "Windows":
        pyautogui.hotkey("ctrl", "shift", "esc")
    elif _OS == "Darwin":
        subprocess.Popen(["open", "-a", "Activity Monitor"])
    else:
        for cmd in [["gnome-system-monitor"], ["xfce4-taskmanager"], ["htop"]]:
            if subprocess.run(["which", cmd[0]], capture_output=True).returncode == 0:
                subprocess.Popen(cmd)
                break


_LAST_COPIED_LINK: str = ""

def set_last_copied_link(link: str) -> None:
    global _LAST_COPIED_LINK
    _LAST_COPIED_LINK = str(link or "").strip()

def get_last_copied_link() -> str:
    global _LAST_COPIED_LINK
    return _LAST_COPIED_LINK

def _focus_browser() -> bool:
    """Ensure Google Chrome, Edge, or the active browser is focused."""
    if _OS == "Windows":
        try:
            import pygetwindow as gw
            for w in gw.getAllWindows():
                title = (w.title or "").lower()
                if any(b in title for b in ("chrome", "youtube", "edge", "firefox", "brave", "opera")):
                    if w.isMinimized:
                        w.restore()
                    try:
                        w.activate()
                    except Exception:
                        pass
                    return True
        except Exception:
            pass
        try:
            ps_act = """
            $w = New-Object -ComObject WScript.Shell
            $w.AppActivate('Google Chrome') -or $w.AppActivate('Chrome') -or $w.AppActivate('YouTube') -or $w.AppActivate('Edge')
            """
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_act], capture_output=True, timeout=2, **_WIN_HIDE)
            return True
        except Exception:
            pass
    return False

def video_fullscreen(action: str = "toggle") -> str:
    """Toggle, enter, or exit fullscreen for YouTube or web video."""
    _focus_browser()
    time.sleep(0.12)
    act = (action or "toggle").lower().strip()
    if act in ("exit", "exit_fullscreen", "choto", "small", "normal", "leave", "off"):
        pyautogui.press("escape")
        time.sleep(0.08)
        return "Exited video fullscreen."
    elif act in ("enter", "maximize", "boro", "on", "full"):
        pyautogui.press("escape")
        time.sleep(0.08)
        pyautogui.press("f")
        return "Set video to fullscreen."
    else:
        pyautogui.press("f")
        return "Toggled video fullscreen."

def set_youtube_quality(quality: str) -> str:
    """Change YouTube playback resolution: pauses video, clicks gear & quality, sets resolution, resumes video."""
    _focus_browser()
    time.sleep(0.15)

    # 1. Step 1: PAUSE the video so controls are frozen and steady
    pyautogui.press("k")
    time.sleep(0.4)

    q_raw = str(quality or "1080").lower().strip().replace("p", "")
    if q_raw in ("2160", "4k", "uhd"):
        target_name = "2160p (4K)"
        target_desc = "2160p"
    elif q_raw in ("1440", "2k", "qhd"):
        target_name = "1440p"
        target_desc = "1440p"
    elif q_raw == "1080":
        target_name = "1080p (HD)"
        target_desc = "1080p"
    elif q_raw == "720":
        target_name = "720p"
        target_desc = "720p"
    elif q_raw == "480":
        target_name = "480p"
        target_desc = "480p"
    elif q_raw == "360":
        target_name = "360p"
        target_desc = "360p"
    elif q_raw == "240":
        target_name = "240p"
        target_desc = "240p"
    elif q_raw == "144":
        target_name = "144p"
        target_desc = "144p"
    elif q_raw == "auto":
        target_name = "Auto"
        target_desc = "Auto"
    else:
        target_name = f"{q_raw}p"
        target_desc = f"{q_raw}p"

    try:
        from actions.computer_control import _screen_find
        sw, sh = pyautogui.size()
        pyautogui.moveTo(sw // 2, sh // 2)
        time.sleep(0.25)

        # 2. Step 2: Click settings gear icon
        gear_pt = _screen_find("YouTube video player settings gear button at bottom right")
        if not gear_pt:
            gear_pt = _screen_find("settings gear icon on video player")
        
        if gear_pt:
            pyautogui.click(gear_pt[0], gear_pt[1])
            time.sleep(0.4)
        else:
            pyautogui.press("k")  # resume playback
            return "Could not locate YouTube settings gear icon on screen."

        # 3. Step 3: Click 'Quality' or 'Video Quality'
        q_pt = _screen_find("Quality or Video Quality menu option in YouTube settings menu popup")
        if not q_pt:
            q_pt = _screen_find("Quality option in YouTube settings menu")
        
        if q_pt:
            pyautogui.click(q_pt[0], q_pt[1])
            time.sleep(0.4)
        else:
            pyautogui.press("escape")
            time.sleep(0.1)
            pyautogui.press("k")
            return "Could not find Quality menu in YouTube settings."

        # 4. Step 4: Click requested quality resolution
        res_pt = _screen_find(f"{target_desc} resolution option in YouTube quality popup list")
        if not res_pt:
            res_pt = _screen_find(f"{q_raw} option in YouTube quality menu")

        if res_pt:
            pyautogui.click(res_pt[0], res_pt[1])
            time.sleep(0.3)
            # 5. Step 5: Resume playback
            pyautogui.press("k")
            pyautogui.moveTo(20, sh // 2)
            return f"Set YouTube video quality to {target_desc} and resumed playback."
        else:
            pyautogui.press("escape")
            time.sleep(0.1)
            pyautogui.press("k")
            return f"Resolution {target_desc} was not found in available qualities."
    except Exception as e:
        pyautogui.press("escape")
        time.sleep(0.1)
        pyautogui.press("k")
        return f"Failed to set YouTube quality: {e}"

def copy_current_link() -> str:
    """Focus active browser, copy current URL to clipboard, and save it."""
    _focus_browser()
    time.sleep(0.12)

    if _OS == "Darwin":
        pyautogui.hotkey("command", "l")
        time.sleep(0.1)
        pyautogui.hotkey("command", "c")
    else:
        pyautogui.hotkey("ctrl", "l")
        time.sleep(0.12)
        pyautogui.hotkey("ctrl", "c")

    time.sleep(0.15)
    link = ""
    try:
        import pyperclip
        link = (pyperclip.paste() or "").strip()
    except Exception:
        pass

    if link:
        pyautogui.press("escape")
        set_last_copied_link(link)
        return f"Copied link: {link}"
    else:
        return "Could not copy link from the browser address bar."

def focus_search():
    if _OS == "Darwin": pyautogui.hotkey("command", "l")
    else:               pyautogui.hotkey("ctrl", "l")

def pause_video():      pyautogui.press("space")

def refresh_page():
    if _OS == "Darwin": pyautogui.hotkey("command", "r")
    else:               pyautogui.press("f5")

def close_tab(tab_name: str = ""):
    """Close the current tab, or a specific named tab in Google Chrome."""
    tab_name = (tab_name or "").strip()
    if _OS == "Windows":
        try:
            try:
                import pygetwindow as gw
                for w in gw.getAllWindows():
                    if "chrome" in (w.title or "").lower():
                        w.activate()
                        time.sleep(0.12)
                        break
            except Exception:
                pass

            ps_act = """
            $w = New-Object -ComObject WScript.Shell
            $w.AppActivate('Google Chrome') -or $w.AppActivate('Chrome')
            """
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_act], capture_output=True, timeout=2, **_WIN_HIDE)
            time.sleep(0.1)

            if tab_name:
                pyautogui.hotkey("ctrl", "shift", "a")
                time.sleep(0.2)
                pyautogui.write(tab_name, interval=0.02)
                time.sleep(0.2)
                pyautogui.press("enter")
                time.sleep(0.25)
                pyautogui.hotkey("ctrl", "w")
                time.sleep(0.08)
                pyautogui.press("escape")
                return f"Closed {tab_name} tab in Chrome."
            else:
                pyautogui.hotkey("ctrl", "w")
                return "Tab closed."
        except Exception as e:
            pyautogui.hotkey("ctrl", "w")
            return f"Tab closed: {e}"
    elif _OS == "Darwin":
        if tab_name:
            pyautogui.hotkey("command", "shift", "a")
            time.sleep(0.2)
            pyautogui.write(tab_name, interval=0.02)
            time.sleep(0.2)
            pyautogui.press("return")
            time.sleep(0.25)
            pyautogui.hotkey("command", "w")
            pyautogui.press("escape")
            return f"Closed {tab_name} tab."
        pyautogui.hotkey("command", "w")
        return "Tab closed."
    else:
        pyautogui.hotkey("ctrl", "w")
        return "Tab closed."

def switch_tab(tab_name: str = ""):
    """Switch to a specific open tab by name or keyword in Google Chrome, or cycle to next tab."""
    tab_name = (tab_name or "").strip()
    _focus_browser()
    time.sleep(0.12)

    if not tab_name:
        if _OS == "Darwin":
            pyautogui.hotkey("command", "option", "right")
        else:
            pyautogui.hotkey("ctrl", "tab")
        return "Switched to next tab."

    if _OS == "Windows":
        try:
            import pyperclip
            pyautogui.hotkey("ctrl", "shift", "a")
            time.sleep(0.2)
            pyperclip.copy(tab_name)
            time.sleep(0.05)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.25)
            pyautogui.press("enter")
            time.sleep(0.15)
            pyautogui.press("escape")
            return f"Switched to {tab_name} tab in Chrome."
        except Exception as e:
            return f"Failed to switch to {tab_name} tab: {e}"
    elif _OS == "Darwin":
        pyautogui.hotkey("command", "shift", "a")
        time.sleep(0.2)
        pyautogui.write(tab_name, interval=0.02)
        time.sleep(0.2)
        pyautogui.press("return")
        time.sleep(0.15)
        pyautogui.press("escape")
        return f"Switched to {tab_name} tab."
    else:
        pyautogui.hotkey("ctrl", "shift", "a")
        time.sleep(0.2)
        pyautogui.write(tab_name, interval=0.02)
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(0.15)
        pyautogui.press("escape")
        return f"Switched to {tab_name} tab."

def new_tab():
    if _OS == "Darwin": pyautogui.hotkey("command", "t")
    else:               pyautogui.hotkey("ctrl", "t")

def next_tab():
    if _OS == "Darwin": pyautogui.hotkey("command", "shift", "bracketright")
    else:               pyautogui.hotkey("ctrl", "tab")

def prev_tab():
    if _OS == "Darwin": pyautogui.hotkey("command", "shift", "bracketleft")
    else:               pyautogui.hotkey("ctrl", "shift", "tab")

def go_back():
    if _OS == "Darwin": pyautogui.hotkey("command", "left")
    else:               pyautogui.hotkey("alt", "left")

def go_forward():
    if _OS == "Darwin": pyautogui.hotkey("command", "right")
    else:               pyautogui.hotkey("alt", "right")

def zoom_in():
    if _OS == "Darwin": pyautogui.hotkey("command", "equal")
    else:               pyautogui.hotkey("ctrl", "equal")

def zoom_out():
    if _OS == "Darwin": pyautogui.hotkey("command", "minus")
    else:               pyautogui.hotkey("ctrl", "minus")

def zoom_reset():
    if _OS == "Darwin": pyautogui.hotkey("command", "0")
    else:               pyautogui.hotkey("ctrl", "0")

def find_on_page():
    if _OS == "Darwin": pyautogui.hotkey("command", "f")
    else:               pyautogui.hotkey("ctrl", "f")

def reload_page_n(n: int):
    for _ in range(max(1, n)):
        refresh_page()
        time.sleep(0.8)


def scroll_up(amount: int = 500):    pyautogui.scroll(amount)
def scroll_down(amount: int = 500):  pyautogui.scroll(-amount)

def scroll_top():
    if _OS == "Darwin": pyautogui.hotkey("command", "up")
    else:               pyautogui.hotkey("ctrl", "home")

def scroll_bottom():
    if _OS == "Darwin": pyautogui.hotkey("command", "down")
    else:               pyautogui.hotkey("ctrl", "end")

def page_up():   pyautogui.press("pageup")
def page_down(): pyautogui.press("pagedown")


def copy():
    if _OS == "Darwin": pyautogui.hotkey("command", "c")
    else:               pyautogui.hotkey("ctrl", "c")

def paste():
    if _OS == "Darwin": pyautogui.hotkey("command", "v")
    else:               pyautogui.hotkey("ctrl", "v")

def cut():
    if _OS == "Darwin": pyautogui.hotkey("command", "x")
    else:               pyautogui.hotkey("ctrl", "x")

def undo():
    if _OS == "Darwin": pyautogui.hotkey("command", "z")
    else:               pyautogui.hotkey("ctrl", "z")

def redo():
    if _OS == "Darwin": pyautogui.hotkey("command", "shift", "z")
    else:               pyautogui.hotkey("ctrl", "y")

def select_all():
    if _OS == "Darwin": pyautogui.hotkey("command", "a")
    else:               pyautogui.hotkey("ctrl", "a")

def save_file():
    if _OS == "Darwin": pyautogui.hotkey("command", "s")
    else:               pyautogui.hotkey("ctrl", "s")

def press_enter():   pyautogui.press("enter")
def press_escape():  pyautogui.press("escape")
def press_key(key: str): pyautogui.press(key)

def type_text(text: str, press_enter_after: bool = False):
    if not text:
        return
    if _PYPERCLIP:
        pyperclip.copy(str(text))
        time.sleep(0.15)
        paste()
    else:
        pyautogui.write(str(text), interval=0.03)
    if press_enter_after:
        time.sleep(0.1)
        pyautogui.press("enter")

def take_screenshot():
    if _OS == "Windows":
        pyautogui.hotkey("win", "shift", "s")
    elif _OS == "Darwin":
        pyautogui.hotkey("command", "shift", "3")
    else:
        for cmd in [["scrot"], ["gnome-screenshot"], ["import", "-window", "root", "screenshot.png"]]:
            if subprocess.run(["which", cmd[0]], capture_output=True).returncode == 0:
                subprocess.Popen(cmd)
                return
        pyautogui.hotkey("ctrl", "print_screen")

def lock_screen():
    if _OS == "Windows":
        pyautogui.hotkey("win", "l")
    elif _OS == "Darwin":
        subprocess.run(["pmset", "displaysleepnow"], capture_output=True)
    else:
        for cmd in [
            ["gnome-screensaver-command", "-l"],
            ["xdg-screensaver", "lock"],
            ["loginctl", "lock-session"],
        ]:
            if subprocess.run(["which", cmd[0]], capture_output=True).returncode == 0:
                subprocess.run(cmd, capture_output=True)
                return

def open_system_settings():
    if _OS == "Windows":
        pyautogui.hotkey("win", "i")
    elif _OS == "Darwin":
        subprocess.Popen(["open", "-a", "System Preferences"])
    else:
        for cmd in [["gnome-control-center"], ["xfce4-settings-manager"], ["kcmshell5"]]:
            if subprocess.run(["which", cmd[0]], capture_output=True).returncode == 0:
                subprocess.Popen(cmd)
                return

def open_file_explorer():
    if _OS == "Windows":
        pyautogui.hotkey("win", "e")
    elif _OS == "Darwin":
        subprocess.Popen(["open", str(Path.home())])
    else:
        for cmd in [["nautilus"], ["thunar"], ["dolphin"], ["nemo"]]:
            if subprocess.run(["which", cmd[0]], capture_output=True).returncode == 0:
                subprocess.Popen(cmd)
                return
        subprocess.Popen(["xdg-open", str(Path.home())])

def sleep_display():
    if _OS == "Windows":
        try:
            import ctypes
            ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
        except Exception as e:
            print(f"[Settings] sleep_display failed: {e}")
    elif _OS == "Darwin":
        subprocess.run(["pmset", "displaysleepnow"], capture_output=True)
    else:
        subprocess.run(["xset", "dpms", "force", "off"], capture_output=True)

def open_run():
    if _OS == "Windows":
        pyautogui.hotkey("win", "r")

def dark_mode():
    if _OS == "Darwin":
        subprocess.run(["osascript", "-e",
            'tell app "System Events" to tell appearance preferences '
            'to set dark mode to not dark mode'],
            capture_output=True)
    elif _OS == "Windows":
        try:
            import winreg
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            current, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.SetValueEx(key, "AppsUseLightTheme", 0, winreg.REG_DWORD, 1 - current)
            winreg.SetValueEx(key, "SystemUsesLightTheme", 0, winreg.REG_DWORD, 1 - current)
            winreg.CloseKey(key)
        except Exception as e:
            print(f"[Settings] dark_mode registry failed: {e}")
    else:
        try:
            result = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                capture_output=True, text=True, encoding="utf-8", errors="replace"
            )
            current = result.stdout.strip()
            new_scheme = "'default'" if "dark" in current else "'prefer-dark'"
            subprocess.run(
                ["gsettings", "set", "org.gnome.desktop.interface", "color-scheme", new_scheme],
                capture_output=True
            )
        except Exception as e:
            print(f"[Settings] dark_mode Linux failed: {e}")

def toggle_wifi():
    if _OS == "Darwin":
        iface = _get_macos_wifi_interface()
        result = subprocess.run(
            ["networksetup", "-getairportpower", iface],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        state = "off" if "On" in result.stdout else "on"
        subprocess.run(["networksetup", "-setairportpower", iface, state],
            capture_output=True)
    elif _OS == "Windows":
        try:
            subprocess.run(
                ["powershell", "-Command",
                 "$adapter = Get-NetAdapter | Where-Object {$_.PhysicalMediaType -eq 'Native 802.11'};"
                 "if ($adapter.Status -eq 'Up') { Disable-NetAdapter -Name $adapter.Name -Confirm:$false }"
                 "else { Enable-NetAdapter -Name $adapter.Name -Confirm:$false }"],
                capture_output=True, timeout=10, **_WIN_HIDE
            )
        except Exception as e:
            print(f"[Settings] toggle_wifi Windows failed: {e}")
    else:
        try:
            result = subprocess.run(["nmcli", "radio", "wifi"], capture_output=True, text=True, encoding="utf-8", errors="replace")
            state  = "off" if "enabled" in result.stdout else "on"
            subprocess.run(["nmcli", "radio", "wifi", state], capture_output=True)
        except Exception as e:
            print(f"[Settings] toggle_wifi Linux failed: {e}")

def restart_computer():
    if _OS == "Windows":
        subprocess.run(["shutdown", "/r", "/t", "10"], capture_output=True, **_WIN_HIDE)
    elif _OS == "Darwin":
        subprocess.run(["osascript", "-e",
            'tell application "System Events" to restart'],
            capture_output=True)
    else:
        subprocess.run(["systemctl", "reboot"], capture_output=True)

def shutdown_computer():
    if _OS == "Windows":
        subprocess.run(["shutdown", "/s", "/t", "2"], capture_output=True)
    elif _OS == "Darwin":
        subprocess.run(["osascript", "-e",
            'tell application "System Events" to shut down'],
            capture_output=True)
    else:
        subprocess.run(["systemctl", "poweroff"], capture_output=True)

ACTION_MAP: dict[str, callable] = {
    "volume_up":           volume_up,
    "volume_down":         volume_down,
    "mute":                volume_mute,
    "unmute":              volume_mute,
    "toggle_mute":         volume_mute,
    "brightness_up":       brightness_up,
    "brightness_down":     brightness_down,
    "sleep_display":       sleep_display,
    "screen_off":          sleep_display,
    "pause_video":         pause_video,
    "play_pause":          pause_video,
    "video_fullscreen":    lambda: video_fullscreen("enter"),
    "exit_fullscreen":     lambda: video_fullscreen("exit"),
    "toggle_video_fullscreen": lambda: video_fullscreen("toggle"),
    "copy_link":           copy_current_link,
    "copy_url":            copy_current_link,
    "set_quality":         set_youtube_quality,
    "close_app":           close_app,
    "close_window":        close_window,
    "full_screen":         full_screen,
    "fullscreen":          full_screen,
    "minimize":            minimize_window,
    "maximize":            maximize_window,
    "snap_left":           snap_left,
    "snap_right":          snap_right,
    "switch_window":       switch_window,
    "show_desktop":        show_desktop,
    "task_manager":        open_task_manager,
    "focus_search":        focus_search,
    "refresh_page":        refresh_page,
    "reload":              refresh_page,
    "close_tab":           close_tab,
    "switch_tab":          switch_tab,
    "tab_switch":          switch_tab,
    "go_to_tab":           switch_tab,
    "speak_to_type":       type_text,
    "new_tab":             new_tab,
    "next_tab":            next_tab,
    "prev_tab":            prev_tab,
    "go_back":             go_back,
    "go_forward":          go_forward,
    "zoom_in":             zoom_in,
    "zoom_out":            zoom_out,
    "zoom_reset":          zoom_reset,
    "find_on_page":        find_on_page,
    "scroll_up":           scroll_up,
    "scroll_down":         scroll_down,
    "scroll_top":          scroll_top,
    "scroll_bottom":       scroll_bottom,
    "page_up":             page_up,
    "page_down":           page_down,
    "copy":                copy,
    "paste":               paste,
    "cut":                 cut,
    "undo":                undo,
    "redo":                redo,
    "select_all":          select_all,
    "save":                save_file,
    "enter":               press_enter,
    "escape":              press_escape,
    "screenshot":          take_screenshot,
    "lock_screen":         lock_screen,
    "open_settings":       open_system_settings,
    "file_explorer":       open_file_explorer,
    "open_run":            open_run,
    "dark_mode":           dark_mode,
    "toggle_wifi":         toggle_wifi,
    "restart":             restart_computer,
    "shutdown":            shutdown_computer,
}

# ── What needs a human, and what just needs an undo ──────────────────────────
#
# The old gate was `_DANGEROUS_ACTIONS = {"restart", "shutdown"}` checked against
# a `confirmed` parameter the MODEL filled in — so the model confirmed its own
# shutdowns, and everything else (switching off the WiFi this assistant is
# talking over) had no gate at all.
#
# Two lists now, and the split is about reversibility, not about how alarming
# the word sounds:
#
#   _IRREVERSIBLE — a human presses a button on the HUD. Nothing else.
#   everything else — done immediately, with an undo pushed if it can be undone.
#
# Asking before every action is what makes an assistant unusable, and every
# question costs a round trip. Undo is both faster and safer than a prompt.
_IRREVERSIBLE = {
    "restart":     ("Restart this computer",
                    "Anything unsaved will be lost. The computer restarts in 10 seconds."),
    # "shutdown" removed per user requirement: shuts down directly without confirmation
    # Not obviously destructive, and that is exactly why it was missed: turning
    # the WiFi off cuts the assistant's own connection to the Live API, so it
    # cannot be asked to turn it back on.
    "toggle_wifi": ("Switch WiFi off or on",
                    "If this switches WiFi off, JARVIS loses its connection and "
                    "cannot switch it back on by voice."),
}

# Kept so anything still importing the old name keeps working.
_DANGEROUS_ACTIONS = set(_IRREVERSIBLE)


# ── Local intent resolution ──────────────────────────────────────────────────
#
# This used to be an entire extra Gemini call, made INSIDE the tool: the Live
# model called computer_settings, and computer_settings then asked a second
# model which action was meant. Every "turn the volume down" paid for two round
# trips — and when that second call failed, the fallback was
# `description.lower().replace(" ", "_")`, which turns the Turkish for "turn it
# down" into `sesi_kis`, i.e. straight to "Unknown action".
#
# Nothing here needs a language model. The Live model already understands the
# sentence; it only needed the vocabulary, which the tool declaration now spells
# out in full. What is left is spelling tolerance, and difflib does that in
# microseconds instead of ~600 ms and a quota unit.
_ALIASES = {
    "volume_up":       ("louder", "raise volume", "turn it up", "increase volume"),
    "volume_down":     ("quieter", "lower volume", "turn it down", "decrease volume"),
    "mute":            ("silence", "sound off", "no sound"),
    "brightness_up":   ("brighter", "raise brightness", "increase brightness"),
    "brightness_down": ("dimmer", "dim", "lower brightness", "decrease brightness"),
    "close_tab":       ("close tab", "close the tab", "close this tab", "tab close", "close chrome tab", "close browser tab", "tab bondho koro", "chrome tab close", "chrome tab", "tab bondho"),
    "close_app":       ("close app", "close the app", "close application", "close program", "exit app", "quit app", "shut app", "kill app", "app bondho koro", "close software", "chrome close", "close chrome"),
    "close_window":    ("close this", "close it", "close window", "window close"),
    "minimize":        ("minimize", "minimise", "minimize window", "minimise window", "minimize app", "minimise app", "minimize this", "minimise this", "minimize current window", "niche nambao", "chrome minimize", "antigravity minimize"),
    "maximize":        ("maximize", "maximise", "maximize window", "maximise window", "maximize app", "maximise app", "boro koro", "boro koro window", "maximize this", "chrome maximize", "antigravity maximize"),
    "video_fullscreen": ("youtube fullscreen", "youtube full screen", "video fullscreen", "video full screen", "youtube boro koro", "video boro koro", "fullscreen video", "video maximize"),
    "exit_fullscreen":  ("exit fullscreen", "exit full screen", "choto koro", "video choto koro", "youtube choto koro", "fullscreen bondho koro", "fullscreen theke ber hou", "normal screen", "leave fullscreen"),
    "set_quality":      ("set quality", "video quality", "change quality", "youtube quality", "quality set", "quality change"),
    "copy_link":        ("copy link", "copy url", "copy video link", "copy website link", "link copy koro", "video link copy", "website link copy", "url copy", "copy address"),
    "switch_tab":       ("switch tab", "tab switch", "switch to tab", "tab e jaao", "go to tab", "open tab", "change tab", "goto tab", "select tab", "tab change koro", "tab e switch koro"),
    "speak_to_type":    ("speak to type", "jarvis type", "type koro", "jarvis lekho", "start typing", "dictate", "dictation"),
    "full_screen":     ("fullscreen", "maximise screen"),
    "show_desktop":    ("minimise everything", "go to desktop"),
    "lock_screen":     ("lock", "lock the pc", "lock computer"),
    "sleep_display":   ("screen off", "turn off the screen", "display off"),
    "dark_mode":       ("night mode", "light mode", "toggle theme"),
    "toggle_wifi":     ("wifi", "wi-fi", "internet off", "internet on"),
    "task_manager":    ("processes", "task list"),
    "screenshot":      ("capture screen", "take a screenshot", "snip"),
    "refresh_page":    ("refresh", "reload page"),
    "new_tab":         ("open a tab", "open new tab"),
    "shutdown":        ("power off", "turn off the computer", "switch off the pc", "shutdown", "shut down", "laptop shutdown", "shutdown laptop", "shutdown computer"),
    "restart":         ("reboot", "restart the pc"),
}

_VALUE_ACTIONS = {"volume_set", "type_text", "press_key", "reload_n",
                  "scroll_up", "scroll_down"}


def _normalise(text: str) -> str:
    return (text or "").strip().lower().replace("-", "_").replace(" ", "_")


def _detect_action(description: str) -> dict:
    """Resolve a free-text description to an action name, locally.

    Returns {"action": name, "value": ...}; `action` is "" when nothing matched,
    which the caller turns into a message naming real candidates — one round
    trip, and only in the case that used to cost one anyway."""
    raw  = (description or "").strip()
    norm = _normalise(raw)
    if not norm:
        return {"action": "", "value": None}

    known = set(ACTION_MAP) | _VALUE_ACTIONS

    # 1. Already an action name.
    if norm in known:
        return {"action": norm, "value": None}

    low = raw.lower()

    # 2. "set volume to 30", "sesi 30 yap" — a number next to a volume word.
    num = re.search(r"(\d{1,3})\s*%?", low)
    if num and any(w in low for w in ("volume", "ses", "sound", "lautstark", "громкость")):
        return {"action": "volume_set", "value": max(0, min(100, int(num.group(1))))}

    # 3. Alias phrases.
    for action, phrases in _ALIASES.items():
        if any(_normalise(p) == norm or p in low for p in phrases):
            return {"action": action, "value": None}

    # 4. Fuzzy match on the action names — catches "fullscren", "volumeup".
    import difflib
    close = difflib.get_close_matches(norm, sorted(known), n=1, cutoff=0.72)
    if close:
        return {"action": close[0], "value": None}

    # 5. Substring: "increase_the_brightness" contains "brightness".
    for action in sorted(known, key=len, reverse=True):
        if len(action) > 4 and (action in norm or norm in action):
            return {"action": action, "value": None}

    return {"action": "", "value": None}


def _suggest(description: str) -> str:
    """What to tell the model when nothing matched. Names real actions so its
    retry lands, instead of the old 'Unknown action' dead end."""
    import difflib
    near = difflib.get_close_matches(_normalise(description),
                                     sorted(ACTION_MAP), n=5, cutoff=0.3)
    hint = ", ".join(near) if near else ", ".join(sorted(ACTION_MAP)[:12])
    return outcome.ask(
        "computer_settings",
        f"'{description}' does not match any computer action - the closest "
        f"are: {hint}. Which was meant?",
        said=description)

def computer_settings(
    parameters: dict = None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    if not _PYAUTOGUI:
        return outcome.failed(
            "computer_settings",
            "pyautogui is not installed, so the keyboard cannot be driven - "
            "run: pip install pyautogui")

    params      = parameters or {}
    raw_action  = params.get("action", "").strip()
    description = params.get("description", "").strip()
    value       = params.get("value", None)

    if not raw_action and description:
        detected   = _detect_action(description)
        raw_action = detected.get("action", "")
        if value is None:
            value = detected.get("value")

    action = raw_action.lower().strip().replace(" ", "_").replace("-", "_")

    if not action:
        return _suggest(description or raw_action)

    print(f"[Settings] Action: {action}  Value: {value}  OS: {_OS}")
    if player:
        print(f"[Settings] {action}")            # terminal, not the HUD

    # ── The gate ─────────────────────────────────────────────────────────────
    # A human presses a button, or this does not happen. The model can no longer
    # write its own permission slip, and the action itself is handed to the UI
    # rather than performed here — so returning early is not "declining", it is
    # "parked until someone says yes".
    if action in _IRREVERSIBLE:
        title, detail = _IRREVERSIBLE[action]
        func = ACTION_MAP.get(action)
        if func is None:
            return outcome.failed("computer_settings",
                                  "that is not an action this tool has",
                                  wanted=raw_action)
        if confirm.pending_title():
            return outcome.ask(
                "computer_settings",
                "there is already a confirmation waiting on screen - the user "
                "has to answer that one first",
                wanted=action)
        return confirm.request(
            key=action, title=title, detail=detail,
            run=lambda f=func, a=action: (f(), f"{a} done.")[1],
        )

    if action == "volume_set":
        try:
            target = int(value if value is not None else 50)
            before = volume_get()
            volume_set(target)
            if before is not None:
                push_undo(f"volume {before}% → {target}%",
                          lambda b=before: (volume_set(b), f"Back to {b}%.")[1])
            now = volume_get()
            if now is None:
                return outcome.unverified(
                    "computer_settings",
                    "this system does not report its volume, so the new "
                    "level could not be read back", wanted=action, asked=target)
            return outcome.done("computer_settings", wanted=action,
                                volume=now, verified=True)
        except Exception as e:
            return outcome.failed("computer_settings",
                                  f"the volume could not be set: {e}", wanted=action)

    if action in ("type_text", "write_on_screen", "type", "write"):
        text = str(value or params.get("text", "")).strip()
        if not text:
            return outcome.failed("computer_settings",
                                  "no text was given to type", wanted=action)
        enter_after = str(params.get("press_enter", "false")).lower() in ("true", "1", "yes")
        type_text(text, press_enter_after=enter_after)
        return outcome.done("computer_settings", wanted=action,
                            typed=text[:60])

    if action in ("close_app", "close_application", "quit_app"):
        app = params.get("app_name") or params.get("text") or str(value or "")
        r = do_close_app(app)
        return outcome.done("computer_settings", wanted=action, result=r)

    if action in ("minimize", "minimize_window", "minimise"):
        app = params.get("app_name") or params.get("text") or str(value or "")
        r = minimize_window(app)
        return outcome.done("computer_settings", wanted=action, result=r)

    if action in ("maximize", "maximize_window", "maximise"):
        app = params.get("app_name") or params.get("text") or str(value or "")
        r = maximize_window(app)
        return outcome.done("computer_settings", wanted=action, result=r)

    if action in ("video_fullscreen", "youtube_fullscreen"):
        act = str(value or params.get("mode") or "enter").lower()
        r = video_fullscreen(act)
        return outcome.done("computer_settings", wanted=action, result=r)

    if action in ("exit_fullscreen", "video_exit_fullscreen", "leave_fullscreen"):
        r = video_fullscreen("exit")
        return outcome.done("computer_settings", wanted=action, result=r)

    if action in ("set_quality", "youtube_quality", "video_quality"):
        q = str(value or params.get("quality") or params.get("text") or "1080").strip()
        r = set_youtube_quality(q)
        return outcome.done("computer_settings", wanted=action, result=r)

    if action in ("copy_link", "copy_url", "copy_video_link", "copy_website_link"):
        r = copy_current_link()
        return outcome.done("computer_settings", wanted=action, result=r)

    if action in ("switch_tab", "tab_switch", "go_to_tab", "goto_tab"):
        tab = params.get("tab_name") or params.get("app_name") or params.get("text") or str(value or "")
        r = switch_tab(tab)
        return outcome.done("computer_settings", wanted=action, result=r)

    if action in ("speak_to_type", "type_dictation", "voice_typing"):
        text = str(value or params.get("text", "")).strip()
        type_text(text)
        return outcome.done("computer_settings", wanted=action, typed=text[:60])

    if action == "close_tab":
        tab = params.get("tab_name") or params.get("app_name") or params.get("text") or str(value or "")
        r = close_tab(tab)
        return outcome.done("computer_settings", wanted=action, result=r)

    if action == "press_key":
        key = str(value or params.get("key", "")).strip()
        if not key:
            return outcome.failed("computer_settings",
                                  "no key was given to press", wanted=action)
        press_key(key)
        return outcome.done("computer_settings", wanted=action, key=key)

    if action in ("reload_n", "refresh_n", "reload_page_n"):
        try:
            reload_page_n(int(value or 1))
            return outcome.done("computer_settings", wanted=action,
                                times=value or 1)
        except Exception as e:
            return outcome.failed("computer_settings",
                                  f"the reload failed: {e}", wanted=action)

    if action == "scroll_up":
        scroll_up(int(value or 500))
        return outcome.done("computer_settings", wanted=action)

    if action == "scroll_down":
        scroll_down(int(value or 500))
        return outcome.done("computer_settings", wanted=action)

    func = ACTION_MAP.get(action)
    if not func:
        return _suggest(raw_action or description)

    # ── Capture "before" so the change can be taken back ─────────────────────
    # Read-then-write is the whole mechanism for settings: there is no clever
    # inverse to compute, just a value to remember. Where the platform will not
    # tell us the current value, nothing is registered — an undo that restores
    # a guess is worse than no undo at all.
    _before = None
    if action in ("volume_up", "volume_down", "mute", "unmute", "toggle_mute"):
        _before = ("volume", volume_get())
    elif action in ("brightness_up", "brightness_down"):
        _before = ("brightness", brightness_get())

    try:
        func()
    except Exception as e:
        print(f"[Settings] Action failed ({action}): {e}")
        return outcome.failed("computer_settings", f"it failed: {e}",
                              wanted=action)

    if _before:
        kind, old = _before
        if old is not None:
            if kind == "volume":
                push_undo(f"volume ({action})",
                          lambda b=old: (volume_set(b), f"Volume back to {b}%.")[1])
            elif kind == "brightness":
                push_undo(f"brightness ({action})",
                          lambda b=old: (brightness_set(b), f"Brightness back to {b}%.")[1])
    elif action == "dark_mode":
        # A pure toggle: calling it again is the undo.
        push_undo("dark mode toggled",
                  lambda: (dark_mode(), "Theme switched back.")[1])

    # ── Say what is known, and only that ─────────────────────────────────────
    #
    # This used to be `return f"Done: {action}."`, sent whether or not anything
    # had changed, because `func()` returns nothing and nobody looked.
    #
    # WHERE THE LINE IS, AND WHY IT IS NOT "VERIFY EVERYTHING"
    #     Volume and brightness are a state the machine will read back, and the
    #     "before" value has ALREADY been read two blocks above for undo — so
    #     checking costs one more call and turns a claim into a fact.
    #
    #     Most of the other fifty-odd actions are a keystroke sent to whatever
    #     has focus, and there is nothing to read. But they are also things the
    #     user is looking straight at: scrolling, switching tabs, snapping a
    #     window. Hedging on those would have the assistant say "I sent a scroll
    #     and cannot confirm it" about something the person just watched happen,
    #     which is noise dressed as honesty.
    #
    #     So the rule is not "verify everything", it is: claim an OUTCOME only
    #     where the outcome was observed, and otherwise claim only what was
    #     actually done. `open_app` lied because it reported an application
    #     opening from a shell starting — two different events. Reporting a
    #     keystroke as a keystroke is not that.
    if _before:
        kind, old_value = _before
        now = volume_get() if kind == "volume" else brightness_get()
        if old_value is None or now is None:
            return outcome.unverified(
                "computer_settings",
                f"this system does not report its {kind}, so the change could "
                f"not be read back",
                wanted=action)
        if now == old_value:
            return outcome.unverified(
                "computer_settings",
                f"the {kind} still reads {now}% - it may already have been at "
                f"the limit, or this system may not have accepted the change",
                wanted=action, value=now)
        return outcome.done("computer_settings", wanted=action,
                            **{kind: now}, verified=True)

    return outcome.done("computer_settings", wanted=action)


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "computer_settings",
    "description": "Controls the computer: volume, brightness, window management (minimize, maximize, close), keyboard shortcuts, typing text on screen, closing apps, closing specific tabs by tab_name, fullscreen, dark mode, WiFi, restart, shutdown, scrolling, tab management, zoom, screenshots, lock screen, refresh/reload page. Use for ANY single computer control command. restart and toggle_wifi put a confirmation on the user's screen. shutdown powers down the computer directly without confirmation. Volume, brightness and dark mode can be reversed with the `undo` tool.",
    # Used in place of `description` only when a small model is on a tool
    # budget - Gemini still gets the full text. See providers/schema.py.
    "brief": (
        "Changes a computer setting: volume, brightness, WiFi, window layout, power. Name the action in 'action'."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            # The exact vocabulary, spelled out.
            #
            # This used to say only "The action to perform", so the model
            # usually filled `description` instead — and computer_settings then
            # made a SECOND Gemini call, inside the tool, purely to translate
            # that sentence into one of these names. Every "turn the volume
            # down" cost two model round trips.
            #
            # Naming the actions here costs ~600 characters once per session and
            # removes a whole round trip from every computer command.
            "app_name": {
                "type": "STRING",
                "description": "Application name to close, minimize, or maximize (e.g. 'chrome', 'antigravity', 'notepad', 'vlc', 'code')"
            },
            "tab_name": {
                "type": "STRING",
                "description": "Specific tab name or keyword to close in Chrome (e.g. 'whatsapp', 'youtube', 'instagram', 'wikipedia')"
            },
            "action": {
                "type": "STRING",
                "description": (
                    "The exact action. Prefer this over `description` — pick one of: "
                    "speak_to_type | switch_tab | video_fullscreen | exit_fullscreen | set_quality | copy_link | volume_up | volume_down | volume_set | mute | "
                    "brightness_up | brightness_down | sleep_display | "
                    "pause_video | close_window | full_screen | "
                    "minimize | maximize | snap_left | snap_right | "
                    "switch_window | show_desktop | task_manager | focus_search | "
                    "refresh_page | close_tab | new_tab | next_tab | prev_tab | "
                    "go_back | go_forward | zoom_in | zoom_out | zoom_reset | "
                    "find_on_page | scroll_up | scroll_down | scroll_top | "
                    "scroll_bottom | page_up | page_down | copy | paste | cut | "
                    "undo | redo | select_all | save | enter | escape | press_key | "
                    "type_text | screenshot | lock_screen | open_settings | "
                    "file_explorer | open_run | dark_mode | toggle_wifi | "
                    "restart | shutdown"
                )
            },
            "description": {
                "type": "STRING",
                "description": (
                    "Fallback only, when no action name above fits. "
                    "Resolved locally — no extra model call."
                )
            },
            "value": {
                "type": "STRING",
                "description": "Optional value: volume level 0-100, text to type, key name, etc."
            }
        },
        "required": []
    },
    "handler": computer_settings,
}

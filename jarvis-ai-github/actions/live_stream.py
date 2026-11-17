"""
actions/live_stream.py - Continuous Live Camera & Live Screen Streaming for JARVIS.

Enables:
1. Continuous Live Camera Mode (Video Call Experience):
   Keeps the camera stream on continuously. JARVIS sees live camera frames
   in real-time and answers user questions (like a FaceTime / Google Meet video call)
   without shutting off the camera until told to stop.
2. Continuous Live Screen Mode (Online Chess / Gaming / Screen Watch):
   Continuously streams the user's desktop screen into the session so JARVIS can
   watch gameplay (e.g. online chess moves), give real-time tactical recommendations,
   and monitor tasks until explicitly told to stop.
"""
from __future__ import annotations

import threading
from typing import Callable, Optional
from core import outcome


class _LiveStreamController:
    def __init__(self):
        self.camera_active = False
        self.screen_active = False
        self._lock = threading.Lock()
        self.on_camera_toggle: Optional[Callable[[bool], None]] = None
        self.on_screen_toggle: Optional[Callable[[bool], None]] = None

    def set_camera(self, active: bool) -> tuple[bool, str]:
        with self._lock:
            self.camera_active = active
        if self.on_camera_toggle:
            try:
                self.on_camera_toggle(active)
            except Exception as e:
                print(f"[LiveStream] Camera callback error: {e}")
        status_text = "started (video call mode active)" if active else "stopped"
        return True, f"Continuous live camera stream {status_text}."

    def set_screen(self, active: bool) -> tuple[bool, str]:
        with self._lock:
            self.screen_active = active
        if self.on_screen_toggle:
            try:
                self.on_screen_toggle(active)
            except Exception as e:
                print(f"[LiveStream] Screen callback error: {e}")
        status_text = "started (watching screen continuously)" if active else "stopped"
        return True, f"Continuous live screen stream {status_text}."

    def status(self) -> dict:
        return {
            "camera_active": self.camera_active,
            "screen_active": self.screen_active
        }


# Global singleton
live_stream_controller = _LiveStreamController()


def live_stream(parameters: dict | None = None) -> str:
    params = parameters or {}
    action = params.get("action", "").lower().strip()
    mode = params.get("mode", "").lower().strip()

    if action in ("start_camera", "camera_on", "video_call") or (action == "start" and mode == "camera"):
        ok, msg = live_stream_controller.set_camera(True)
        return outcome.done("live_stream", stream="camera", active=True, message=msg)

    elif action in ("stop_camera", "camera_off") or (action == "stop" and mode == "camera"):
        ok, msg = live_stream_controller.set_camera(False)
        return outcome.done("live_stream", stream="camera", active=False, message=msg)

    elif action in ("start_screen", "screen_on", "watch_screen", "chess_mode") or (action == "start" and mode == "screen"):
        ok, msg = live_stream_controller.set_screen(True)
        return outcome.done("live_stream", stream="screen", active=True, message=msg)

    elif action in ("stop_screen", "screen_off") or (action == "stop" and mode == "screen"):
        ok, msg = live_stream_controller.set_screen(False)
        return outcome.done("live_stream", stream="screen", active=False, message=msg)

    elif action in ("status", "check"):
        st = live_stream_controller.status()
        return outcome.done("live_stream", camera=st["camera_active"], screen=st["screen_active"])

    else:
        # Default smart routing based on target
        if "camera" in action or mode == "camera":
            ok, msg = live_stream_controller.set_camera(True)
            return outcome.done("live_stream", stream="camera", active=True, message=msg)
        else:
            ok, msg = live_stream_controller.set_screen(True)
            return outcome.done("live_stream", stream="screen", active=True, message=msg)


TOOL = {
    "name": "live_stream",
    "description": (
        "Controls continuous live video streaming (webcam video call mode) and continuous live screen watching "
        "(e.g. for online chess, gaming, or monitoring the screen). "
        "Use action='start_camera' when the user asks to keep the camera on, start a video call, or continuously look at them through the webcam. "
        "Use action='start_screen' when the user asks to continuously watch their screen, play online chess with them, or monitor screen moves until told to stop. "
        "Use action='stop_camera' or action='stop_screen' when the user asks to stop watching."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": (
                    "'start_camera' (keep live camera on like a video call), "
                    "'stop_camera' (turn off live camera), "
                    "'start_screen' (watch live screen continuously for chess/games/tasks), "
                    "'stop_screen' (stop watching live screen), "
                    "'status' (check stream status)."
                ),
            },
            "mode": {
                "type": "STRING",
                "description": "'camera' or 'screen'.",
            },
        },
        "required": ["action"],
    },
    "handler": live_stream,
}

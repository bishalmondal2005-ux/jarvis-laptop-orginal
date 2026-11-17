"""
Screen & webcam capture for JARVIS vision.

Provides the two capture entry points main.py uses — `_capture_screen()` and
`_capture_camera()` — plus their helpers (compression, camera auto-detection,
config access). main.py grabs a frame here on demand, then injects it into the
main Gemini Live session; there is no separate vision session here.
"""
from __future__ import annotations

import io
import json
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from core.lazyimport import LazyModule, installed

_CV2 = installed("cv2")
cv2 = LazyModule("cv2")

try:
    import mss
    import mss.tools
    _MSS = True
except ImportError:
    _MSS = False

try:
    import PIL.Image
    _PIL = True
except ImportError:
    _PIL = False


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


_BASE        = _base_dir()
_CONFIG_PATH = _BASE / "config" / "api_keys.json"


def _load_config() -> dict:
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_config_key(key: str, value) -> None:
    try:
        cfg = _load_config()
        cfg[key] = value
        _CONFIG_PATH.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
    except Exception as e:
        print(f"[Vision] ⚠️  Could not save config key '{key}': {e}")


def _get_os() -> str:
    return _load_config().get("os_system", "windows").lower()


# Increased to Full HD 1920x1080 so 15.6" screen elements and vision coordinates
# match physical pixels with 1:1 precision!
_IMG_MAX_W = 1920
_IMG_MAX_H = 1080
_JPEG_Q    = 85


def _compress(img_bytes: bytes, source_format: str = "PNG") -> tuple[bytes, str]:
    if not _PIL:
        return img_bytes, f"image/{source_format.lower()}"

    try:
        img = PIL.Image.open(io.BytesIO(img_bytes)).convert("RGB")
        if img.width > _IMG_MAX_W or img.height > _IMG_MAX_H:
            img.thumbnail((_IMG_MAX_W, _IMG_MAX_H), PIL.Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=_JPEG_Q, optimize=False)
        return buf.getvalue(), "image/jpeg"
    except Exception as e:
        print(f"[Vision] ⚠️  Image compress failed: {e}")
        return img_bytes, f"image/{source_format.lower()}"


def _capture_screen() -> tuple[bytes, str]:
    if not _MSS:
        raise RuntimeError("mss is not installed. Run: pip install mss")

    with mss.mss() as sct:
        monitors = sct.monitors          # [0] = all combined, [1..n] = real screens
        target   = monitors[1] if len(monitors) > 1 else monitors[0]
        shot     = sct.grab(target)
        png      = mss.tools.to_png(shot.rgb, shot.size)

    return _compress(png, "PNG")


def _cv2_backend() -> int:
    """Return the best OpenCV camera backend for the current OS."""
    if not _CV2:
        return 0
    os_name = _get_os()
    if os_name == "windows":
        return cv2.CAP_DSHOW
    if os_name == "mac":
        return cv2.CAP_AVFOUNDATION
    return cv2.CAP_ANY


def _probe_camera(index: int, backend: int, warmup: int = 5) -> bool:
    if not _CV2:
        return False
    cap = cv2.VideoCapture(index, backend)
    if not cap.isOpened() and backend != 0:
        cap = cv2.VideoCapture(index, 0)
    if not cap.isOpened():
        return False
    for _ in range(warmup):
        cap.read()
    ret, frame = cap.read()
    cap.release()
    if not ret or frame is None:
        return False
    return bool(np.mean(frame) > 8)


def _detect_camera_index() -> int:
    backend = _cv2_backend()
    print("[Vision] 🔍 Auto-detecting camera...")
    for idx in range(6):
        if _probe_camera(idx, backend):
            print(f"[Vision] ✅ Camera found at index {idx}")
            _save_config_key("camera_index", idx)
            return idx
        print(f"[Vision] ⚠️  Camera index {idx}: no usable frame")

    print("[Vision] ⚠️  No camera found — defaulting to index 0")
    _save_config_key("camera_index", 0)
    return 0


def _get_camera_index() -> int:
    cfg = _load_config()
    if "camera_index" in cfg:
        return int(cfg["camera_index"])
    return _detect_camera_index()


# ── Thread-Safe Unified Camera Manager ────────────────────────────────────────
class CameraStreamManager:
    """Unified camera controller that eliminates device collisions and buffer lag.
    Guarantees that both HUD UI and vision calls receive the absolute latest,
    zero-latency real-time frame."""

    def __init__(self):
        self._lock = threading.Lock()
        self._streaming = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._latest_jpeg: Optional[bytes] = None
        self._latest_frame: Optional[np.ndarray] = None
        self._last_time: float = 0.0
        self._subscribers: list[Callable[[bytes], None]] = []
        self._cap = None

    def subscribe(self, callback: Callable[[bytes], None]):
        with self._lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[bytes], None]):
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def is_streaming(self) -> bool:
        return self._streaming

    def start_stream(self, index: Optional[int] = None) -> bool:
        with self._lock:
            if self._streaming:
                return True
            if index is None:
                index = _get_camera_index()
            backend = _cv2_backend()
            cap = cv2.VideoCapture(index, backend)
            if not cap.isOpened() and backend != 0:
                cap = cv2.VideoCapture(index, 0)
            if not cap.isOpened() and index != 0:
                cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                print(f"[CameraManager] ⚠️ Could not open camera {index}")
                return False

            try:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                pass

            self._cap = cap
            self._streaming = True
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._worker, daemon=True, name="cam-manager-worker"
            )
            self._thread.start()
            print(f"[CameraManager] ✅ Camera stream started on index {index}")
            return True

    def _worker(self):
        # Warmup and clear initial driver queue
        for _ in range(3):
            if self._cap and self._cap.isOpened():
                self._cap.read()

        while not self._stop_event.is_set() and self._cap and self._cap.isOpened():
            ret, frame = self._cap.read()
            if ret and frame is not None:
                _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, _JPEG_Q])
                jpeg_bytes = buf.tobytes()
                with self._lock:
                    self._latest_frame = frame
                    self._latest_jpeg = jpeg_bytes
                    self._last_time = time.time()
                    subs = list(self._subscribers)
                for cb in subs:
                    try:
                        cb(jpeg_bytes)
                    except Exception:
                        pass
            time.sleep(0.033)  # ~30 FPS

        if self._cap:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None
        self._streaming = False
        print("[CameraManager] 🛑 Camera stream stopped")

    def stop_stream(self):
        self._stop_event.set()
        self._streaming = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None
        if self._cap:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None

    def get_latest_frame(self) -> tuple[bytes, str]:
        # If streaming, return the latest cached frame immediately (0 ms)
        if self._streaming and self._latest_jpeg:
            with self._lock:
                return self._latest_jpeg, "image/jpeg"

        # If stream was just starting, wait briefly for frame
        if self._streaming:
            for _ in range(25):
                time.sleep(0.04)
                if self._latest_jpeg:
                    with self._lock:
                        return self._latest_jpeg, "image/jpeg"

        # Not streaming: capture single fresh frame with buffer flush
        return self.capture_single()

    def capture_single(self) -> tuple[bytes, str]:
        index = _get_camera_index()
        backend = _cv2_backend()
        cap = cv2.VideoCapture(index, backend)
        if not cap.isOpened() and backend != 0:
            cap = cv2.VideoCapture(index, 0)
        if not cap.isOpened() and index != 0:
            cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise RuntimeError(f"Camera index {index} could not be opened.")

        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        # Flush stale driver buffer (5 frames) so new object is instantly visible
        for _ in range(5):
            cap.read()

        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            raise RuntimeError("Camera returned no frame.")

        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, _JPEG_Q])
        return buf.tobytes(), "image/jpeg"


# Global singleton instance
camera_manager = CameraStreamManager()


def _capture_camera() -> tuple[bytes, str]:
    """Capture fresh webcam frame without driver conflicts."""
    if not _CV2:
        raise RuntimeError("OpenCV (cv2) is not installed. Run: pip install opencv-python")
    return camera_manager.get_latest_frame()

"""
core/origin_island.py - Dynamic "Origin Island" for Mark-LVI (JARVIS).

A sleek, always-on-top, floating Dynamic Island widget inspired by the iPhone Dynamic Island
and Iron Man's Stark Arc Reactor.

Features:
- Floats at a fixed or customizable position on screen.
- Draggable with mouse; position automatically persists to config/origin_island.json.
- Left side: Live animated Arc Reactor with pulsing core, rotating rings, and reactive state colors:
  * LISTENING: Vivid Cyan/Electric Blue (#00e5ff) with reactive pulse
  * SPEAKING: Stark Green/Gold (#00ff88 / #ffcc00)
  * THINKING/TASK: Energetic Orange (#ff9100)
  * TASK COMPLETED: Bright Violet (#a855f7)
  * IDLE: Gentle breathing Cyan (#00b4d8)
  * SLEEPING: Dimmed Deep Blue (#003366)
- Custom GIF / Image support: User can set custom animations per state (Speaking, Listening, Idle).
- Middle section: Live dynamic status text ("LISTENING...", "SPEAKING...", "TASK COMPLETED", etc.).
- Click-to-Expand: Expands into an interactive control island with Mic Toggle (Mute/Unmute)
  and Jarvis Sleep/Wake buttons.
- Voice Wakeup: Responds to voice wakeup and wake-word events.
"""
from __future__ import annotations

import json
import math
import os
import time
from pathlib import Path
from typing import Callable, Optional

from PyQt6.QtCore import (
    QPoint,
    QRect,
    QRectF,
    QSize,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QIcon,
    QLinearGradient,
    QMovie,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PyQt6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "origin_island.json"

DEFAULT_CONFIG = {
    "enabled": True,
    "preset": "top_center",
    "x": -1,
    "y": 18,
    "width": 290,
    "height": 44,
    "bg_color": "#06090e",
    "bg_opacity": 0.94,
    "accent_color": "#00d4ff",
    "border_enabled": True,
    "border_color": "#00d4ff",
    "border_width": 1,
    "border_glow": True,
    "custom_speaking_gif": "",
    "custom_listening_gif": "",
    "custom_idle_gif": "",
}


def load_island_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            cfg = dict(DEFAULT_CONFIG)
            cfg.update(data)
            return cfg
        except Exception as e:
            print(f"[OriginIsland] Config read error: {e}")
    return dict(DEFAULT_CONFIG)


def save_island_config(cfg: dict) -> None:
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
    except Exception as e:
        print(f"[OriginIsland] Config save error: {e}")


# ── Built-in Mini Arc Reactor Widget ──────────────────────────────────────────
class MiniArcReactor(QWidget):
    """Miniature animated vector Arc Reactor for the Origin Island."""

    def __init__(self, size: int = 34, parent=None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.state = "IDLE"
        self.speaking = False
        self.muted = False
        self.audio_level = 0.0

        self._angle = 0.0
        self._pulse = 0.0
        self._pulse_dir = 1.0

        # Animation timer at ~30 FPS
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self._timer.start(33)

    def _step(self):
        # Rotation speed depends on state
        speed = 2.0
        if self.state in ("THINKING", "PROCESSING"):
            speed = 7.0
        elif self.state == "LISTENING":
            speed = 4.5
        elif self.speaking:
            speed = 5.0
        elif self.state == "SLEEPING":
            speed = 0.5

        self._angle = (self._angle + speed) % 360.0

        # Pulse phase
        p_speed = 0.04 if self.state != "SLEEPING" else 0.015
        self._pulse += p_speed * self._pulse_dir
        if self._pulse >= 1.0:
            self._pulse = 1.0
            self._pulse_dir = -1.0
        elif self._pulse <= 0.0:
            self._pulse = 0.0
            self._pulse_dir = 1.0

        self.update()

    def set_state(self, state: str, speaking: bool = False, muted: bool = False):
        self.state = state.upper()
        self.speaking = speaking
        self.muted = muted
        self.update()

    def set_audio_level(self, level: float):
        self.audio_level = max(0.0, min(1.0, level))

    def _get_colors(self) -> tuple[QColor, QColor]:
        if self.muted:
            return QColor("#ff4444"), QColor("#882222")
        if self.state == "SLEEPING":
            return QColor("#1e3a5f"), QColor("#0d1b2a")
        if self.speaking:
            return QColor("#00ff88"), QColor("#00b359")
        if self.state == "LISTENING":
            return QColor("#00f0ff"), QColor("#0099cc")
        if self.state in ("THINKING", "PROCESSING"):
            return QColor("#ff9900"), QColor("#cc6600")
        if "TASK" in self.state or "DONE" in self.state:
            return QColor("#bf5af2"), QColor("#7928ca")
        # Default Idle
        return QColor("#00d4ff"), QColor("#007799")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        r = min(w, h) / 2.0 - 2.0

        pri_col, sec_col = self._get_colors()

        # Audio / pulse boost
        boost = 0.25 * self._pulse + 0.5 * self.audio_level
        if self.speaking:
            boost += 0.3

        # 1. Outer Glow
        glow_r = r * (0.85 + 0.2 * boost)
        grad = QRadialGradient(cx, cy, glow_r)
        g_col = QColor(pri_col)
        g_col.setAlpha(int(min(240, 70 + 130 * boost)))
        grad.setColorAt(0.0, g_col)
        g_fade = QColor(sec_col)
        g_fade.setAlpha(0)
        grad.setColorAt(1.0, g_fade)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(QRectF(cx - glow_r, cy - glow_r, glow_r * 2, glow_r * 2))

        # 2. Outer Ring
        ring_pen = QPen(sec_col, 1.4)
        p.setPen(ring_pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(cx - r + 2, cy - r + 2, (r - 2) * 2, (r - 2) * 2))

        # 3. Rotating Segmented Core Ticks (Arc Reactor teeth)
        p.save()
        p.translate(cx, cy)
        p.rotate(self._angle)
        tick_pen = QPen(pri_col, 1.5)
        p.setPen(tick_pen)
        num_ticks = 8
        tick_r_out = r - 3
        tick_r_in = r - 7
        for i in range(num_ticks):
            deg = i * (360.0 / num_ticks)
            rad = math.radians(deg)
            x1 = tick_r_in * math.cos(rad)
            y1 = tick_r_in * math.sin(rad)
            x2 = tick_r_out * math.cos(rad)
            y2 = tick_r_out * math.sin(rad)
            p.drawLine(int(x1), int(y1), int(x2), int(y2))
        p.restore()

        # 4. Inner Reactor Core
        core_r = max(3.0, (r - 9) * (0.8 + 0.3 * boost))
        core_grad = QRadialGradient(cx, cy, core_r)
        core_white = QColor("#ffffff")
        core_white.setAlpha(int(min(255, 180 + 75 * boost)))
        core_grad.setColorAt(0.0, core_white)
        core_grad.setColorAt(0.6, pri_col)
        c_edge = QColor(sec_col)
        c_edge.setAlpha(160)
        core_grad.setColorAt(1.0, c_edge)

        p.setPen(QPen(pri_col, 1.0))
        p.setBrush(QBrush(core_grad))
        p.drawEllipse(QRectF(cx - core_r, cy - core_r, core_r * 2, core_r * 2))
        p.end()


# ── The Dynamic Origin Island Window ──────────────────────────────────────────
class OriginIslandWindow(QWidget):
    """Top-level floating Dynamic Island widget for Mark-LVI."""

    state_changed_sig = pyqtSignal(str)
    mute_toggled_sig = pyqtSignal(bool)
    sleep_toggled_sig = pyqtSignal(bool)
    task_started_sig = pyqtSignal(str)
    task_result_sig = pyqtSignal(str, bool)
    reminder_alert_sig = pyqtSignal(str, str, str)
    typing_sig = pyqtSignal(bool, str)

    def _close_application(self):
        print("[OriginIsland] 🛑 User requested application exit.")
        try:
            self.notify_task_completed("Shutting down JARVIS...", success=True)
            self.close()
        except Exception:
            pass
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.quit()
        import os, threading, time
        threading.Thread(target=lambda: (time.sleep(0.4), os._exit(0)), daemon=True).start()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self.cfg = load_island_config()

        # State flags
        self.current_state = "READY"
        self.is_speaking = False
        self.is_muted = False
        self.is_asleep = False
        self.is_typing = False
        self.expanded = False
        self._dynamic_width: Optional[int] = None
        self._task_timeout_timer: Optional[QTimer] = None

        # Dragging support
        self._dragging = False
        self._drag_start_pos = QPoint()

        # Callbacks to main / ui
        self.on_mute_click: Optional[Callable[[], None]] = None
        self.on_sleep_click: Optional[Callable[[], None]] = None
        self.on_wake_click: Optional[Callable[[], None]] = None
        self.on_settings_click: Optional[Callable[[], None]] = None
        self.on_todo_click: Optional[Callable[[], None]] = None

        self._custom_movie: Optional[QMovie] = None
        self._custom_pixmap: Optional[QPixmap] = None

        self._setup_ui()
        self._apply_geometry()

    def _setup_ui(self):
        # Root layout with padding for shadow & glow
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(10, 10, 10, 10)
        self.root_layout.setSpacing(0)

        # Container pill
        self.pill = QWidget(self)
        self.pill.setObjectName("OriginIslandPill")
        self.root_layout.addWidget(self.pill)

        self.pill_layout = QVBoxLayout(self.pill)
        self.pill_layout.setContentsMargins(8, 4, 10, 4)
        self.pill_layout.setSpacing(6)

        # ── Compact Bar (always visible) ──
        self.bar_widget = QWidget(self.pill)
        self.bar_layout = QHBoxLayout(self.bar_widget)
        self.bar_layout.setContentsMargins(0, 0, 0, 0)
        self.bar_layout.setSpacing(8)

        # 1. Left Icon Container (Arc Reactor or Custom GIF/Image)
        self.icon_container = QWidget(self.bar_widget)
        self.icon_container.setFixedSize(36, 36)
        self.icon_layout = QHBoxLayout(self.icon_container)
        self.icon_layout.setContentsMargins(0, 0, 0, 0)
        self.icon_layout.setSpacing(0)

        # Built-in Arc Reactor
        self.arc_reactor = MiniArcReactor(size=34, parent=self.icon_container)
        self.icon_layout.addWidget(self.arc_reactor)

        # Custom GIF/Image Label (hidden unless custom asset exists)
        self.custom_media_lbl = QLabel(self.icon_container)
        self.custom_media_lbl.setFixedSize(34, 34)
        self.custom_media_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.custom_media_lbl.hide()
        self.icon_layout.addWidget(self.custom_media_lbl)

        self.bar_layout.addWidget(self.icon_container)

        # 2. Middle Status & Label
        self.status_box = QWidget(self.bar_widget)
        self.status_layout = QVBoxLayout(self.status_box)
        self.status_layout.setContentsMargins(0, 2, 0, 2)
        self.status_layout.setSpacing(1)

        self.title_lbl = QLabel("J.A.R.V.I.S.")
        self.title_lbl.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        self.title_lbl.setStyleSheet("color: #718096; background: transparent; letter-spacing: 1px;")

        self.status_lbl = QLabel("READY")
        self.status_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        self.status_lbl.setStyleSheet(f"color: {self.cfg.get('accent_color', '#00d4ff')}; background: transparent;")

        self.status_layout.addWidget(self.title_lbl)
        self.status_layout.addWidget(self.status_lbl)
        self.bar_layout.addWidget(self.status_box, stretch=1)

        # 3. Right Quick Indicator / Chevron
        self.badge_lbl = QLabel("◈")
        self.badge_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.badge_lbl.setStyleSheet("color: #4a5568; background: transparent;")
        self.bar_layout.addWidget(self.badge_lbl)

        self.pill_layout.addWidget(self.bar_widget)

        # ── Expanded Drawer (shown when clicked) ──
        self.drawer_widget = QWidget(self.pill)
        self.drawer_layout = QVBoxLayout(self.drawer_widget)
        self.drawer_layout.setContentsMargins(4, 6, 4, 4)
        self.drawer_layout.setSpacing(6)

        # Divider line
        div = QWidget()
        div.setFixedHeight(1)
        div.setStyleSheet("background: rgba(255, 255, 255, 0.12);")
        self.drawer_layout.addWidget(div)

        # Quick Control Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        # Mic Toggle Button
        self.mic_btn = QPushButton("🎙️ MIC: ON")
        self.mic_btn.setFixedHeight(30)
        self.mic_btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mic_btn.clicked.connect(self._handle_mic_btn)
        btn_row.addWidget(self.mic_btn)

        # Sleep / Wakeup Toggle Button
        self.sleep_btn = QPushButton("💤 SLEEP")
        self.sleep_btn.setFixedHeight(30)
        self.sleep_btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.sleep_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sleep_btn.clicked.connect(self._handle_sleep_btn)
        btn_row.addWidget(self.sleep_btn)

        # To-Do List Button
        self.todo_btn = QPushButton("📝 TO-DO")
        self.todo_btn.setFixedHeight(30)
        self.todo_btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.todo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.todo_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 212, 255, 0.15);
                color: #00d4ff;
                border: 1px solid rgba(0, 212, 255, 0.4);
                border-radius: 6px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: rgba(0, 212, 255, 0.35);
                color: #ffffff;
                border: 1px solid #00d4ff;
            }
        """)
        self.todo_btn.clicked.connect(self._handle_todo_btn)
        btn_row.addWidget(self.todo_btn)

        # Settings Button
        self.settings_btn = QPushButton("⚙ SETTINGS")
        self.settings_btn.setFixedHeight(30)
        self.settings_btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.clicked.connect(self._handle_settings_btn)
        btn_row.addWidget(self.settings_btn)

        # Exit Button
        self.exit_btn = QPushButton("✕ EXIT")
        self.exit_btn.setFixedHeight(30)
        self.exit_btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.exit_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.2);
                color: #fca5a5;
                border: 1px solid rgba(239, 68, 68, 0.5);
                border-radius: 6px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.45);
                color: #ffffff;
                border: 1px solid #ef4444;
            }
        """)
        self.exit_btn.clicked.connect(self._close_application)
        btn_row.addWidget(self.exit_btn)

        # Collapse Button
        self.collapse_btn = QPushButton("▲")
        self.collapse_btn.setFixedSize(30, 30)
        self.collapse_btn.setFont(QFont("Segoe UI", 8))
        self.collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.collapse_btn.clicked.connect(self.collapse)
        btn_row.addWidget(self.collapse_btn)

        self.drawer_layout.addLayout(btn_row)
        self.pill_layout.addWidget(self.drawer_widget)
        self.drawer_widget.hide()

        # Connect internal cross-thread queued signals
        self.task_started_sig.connect(self._do_set_task_progress)
        self.task_result_sig.connect(self._do_set_task_result)
        self.reminder_alert_sig.connect(self._do_show_reminder_alert)
        self.typing_sig.connect(self._do_set_typing)

        self._apply_styles()

    def _apply_styles(self):
        bg = self.cfg.get("bg_color", "#06090e")
        accent = self.cfg.get("accent_color", "#00d4ff")
        h = int(self.cfg.get("height", 44))
        radius = h // 2 if not self.expanded else 16

        # Border add/remove & color customization
        has_border = self.cfg.get("border_enabled", True)
        b_color = self.cfg.get("border_color") or self.cfg.get("accent_color", "#00d4ff")
        b_width = int(self.cfg.get("border_width", 1))

        if has_border and b_width > 0:
            border_css = f"border: {b_width}px solid {b_color};"
        else:
            border_css = "border: none;"

        self.pill.setStyleSheet(f"""
            QWidget#OriginIslandPill {{
                background-color: {bg};
                border-radius: {radius}px;
                {border_css}
            }}
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.08);
                color: #e2e8f0;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 4px 8px;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 212, 255, 0.2);
                border: 1px solid {b_color};
                color: #ffffff;
            }}
            QPushButton:pressed {{
                background-color: rgba(0, 212, 255, 0.35);
            }}
        """)

        # Sync button text & colors
        if self.is_muted:
            self.mic_btn.setText("🔇 MIC: OFF")
            self.mic_btn.setStyleSheet("background: rgba(239, 68, 68, 0.25); color: #fca5a5; border: 1px solid #ef4444; border-radius: 6px;")
        else:
            self.mic_btn.setText("🎙️ MIC: ON")
            self.mic_btn.setStyleSheet("background: rgba(16, 185, 129, 0.2); color: #6ee7b7; border: 1px solid #10b981; border-radius: 6px;")

        if self.is_asleep:
            self.sleep_btn.setText("⚡ WAKE UP")
            self.sleep_btn.setStyleSheet(f"background: rgba(0, 212, 255, 0.25); color: {accent}; border: 1px solid {accent}; border-radius: 6px;")
        else:
            self.sleep_btn.setText("💤 SLEEP")
            self.sleep_btn.setStyleSheet("background: rgba(255, 255, 255, 0.08); color: #cbd5e1; border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 6px;")

    def _apply_geometry(self):
        screen = QApplication.primaryScreen().availableGeometry()
        base_w = int(self.cfg.get("width", 290))
        w = self._dynamic_width if getattr(self, "_dynamic_width", None) else base_w
        h = int(self.cfg.get("height", 44))

        exp_w = max(w + 50, 340)
        exp_h = h + 62

        win_w = exp_w if self.expanded else w
        win_h = exp_h if self.expanded else h

        full_w = win_w + 20
        full_h = win_h + 20

        compact_full_w = w + 20
        compact_full_h = h + 20

        preset = self.cfg.get("preset", "top_center")
        saved_x = self.cfg.get("x", -1)
        saved_y = self.cfg.get("y", 18)

        # 1. Base compact position
        if saved_x >= 0 and preset == "custom":
            base_x = saved_x
            base_y = saved_y
        elif preset == "top_left":
            base_x = screen.x() + 24
            base_y = screen.y() + (saved_y if saved_y >= 0 else 18)
        elif preset == "top_right":
            base_x = screen.x() + screen.width() - compact_full_w - 24
            base_y = screen.y() + (saved_y if saved_y >= 0 else 18)
        elif preset == "bottom_center":
            base_x = screen.x() + (screen.width() - compact_full_w) // 2
            base_y = screen.y() + screen.height() - compact_full_h - 16
        else:  # top_center default
            base_x = screen.x() + (screen.width() - compact_full_w) // 2
            base_y = screen.y() + (saved_y if saved_y >= 0 else 18)

        # 2. Responsive expansion direction: if near bottom, expand UPWARDS so it never goes off screen!
        screen_bottom = screen.y() + screen.height()
        screen_mid_y = screen.y() + (screen.height() / 2.0)
        expand_upward = False

        if (base_y > screen_mid_y) or (base_y + exp_h + 20 > screen_bottom - 8):
            expand_upward = True

        # Reorder layout widgets and strictly anchor pill alignment to prevent any sinking/drift
        if expand_upward:
            self.pill_layout.removeWidget(self.bar_widget)
            self.pill_layout.removeWidget(self.drawer_widget)
            self.pill_layout.addWidget(self.drawer_widget)
            self.pill_layout.addWidget(self.bar_widget)
            self.collapse_btn.setText("▼")
            self.root_layout.setAlignment(self.pill, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
        else:
            self.pill_layout.removeWidget(self.bar_widget)
            self.pill_layout.removeWidget(self.drawer_widget)
            self.pill_layout.addWidget(self.bar_widget)
            self.pill_layout.addWidget(self.drawer_widget)
            self.collapse_btn.setText("▲")
            self.root_layout.setAlignment(self.pill, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        # 3. Calculate target position (strictly anchored)
        if self.expanded:
            dx = (exp_w - w) // 2
            pos_x = base_x - dx
            if expand_upward:
                # Bottom stays anchored, expands upward
                pos_y = (base_y + compact_full_h) - full_h
            else:
                pos_y = base_y
        else:
            pos_x = base_x
            pos_y = base_y

        # 4. Strict screen bounds clamping: 100% responsive, never off screen
        pos_x = max(screen.x(), min(pos_x, screen.x() + screen.width() - full_w))
        pos_y = max(screen.y(), min(pos_y, screen_bottom - full_h))

        self.setFixedSize(full_w, full_h)
        self.move(pos_x, pos_y)
        self.pill.setFixedSize(win_w, win_h)
        self._apply_styles()

    def set_task_progress(self, task_text: str):
        """Thread-safe: display expanding live progress for a running task in the island."""
        self.task_started_sig.emit(task_text)

    def _do_set_task_progress(self, task_text: str):
        if getattr(self, "is_asleep", False) or getattr(self, "is_typing", False):
            return
        fm = QFontMetrics(self.status_lbl.font())
        needed_w = fm.horizontalAdvance(task_text) + 120
        base_w = int(self.cfg.get("width", 290))
        self._dynamic_width = max(base_w, min(needed_w, 750))

        self.current_state = "PROCESSING"
        self._update_media_for_state("PROCESSING")
        self.status_lbl.setText(task_text)
        self.status_lbl.setStyleSheet("color: #ff9900; background: transparent; font-weight: 600;")
        self.arc_reactor.set_state("THINKING", speaking=False, muted=self.is_muted)
        self.badge_lbl.setText("⏳")
        self.badge_lbl.setStyleSheet("color: #ff9900; background: transparent;")
        if self._task_timeout_timer:
            self._task_timeout_timer.stop()
        self._apply_geometry()

    def set_task_result(self, result_text: str, success: bool = True):
        """Thread-safe: display task outcome in the island with dynamic width, then auto-revert to normal."""
        self.task_result_sig.emit(result_text, success)

    def _do_set_task_result(self, result_text: str, success: bool = True):
        if getattr(self, "is_asleep", False):
            return
        if getattr(self, "is_typing", False):
            return
        prefix = "✓ " if success else "✗ "
        full_text = prefix + result_text
        fm = QFontMetrics(self.status_lbl.font())
        needed_w = fm.horizontalAdvance(full_text) + 120
        base_w = int(self.cfg.get("width", 290))
        self._dynamic_width = max(base_w, min(needed_w, 750))

        color = "#10b981" if success else "#ef4444"
        badge_symbol = "✓" if success else "✗"
        self.current_state = "TASK_COMPLETED" if success else "TASK_FAILED"
        self._update_media_for_state("TASK_COMPLETED")
        self.status_lbl.setText(full_text)
        self.status_lbl.setStyleSheet(f"color: {color}; background: transparent; font-weight: bold;")
        self.arc_reactor.set_state("TASK_COMPLETED" if success else "IDLE", speaking=False, muted=self.is_muted)
        self.badge_lbl.setText(badge_symbol)
        self.badge_lbl.setStyleSheet(f"color: {color}; background: transparent; font-weight: bold;")
        self._apply_geometry()

        # Revert to normal configured size and READY state after 3.5 seconds
        if self._task_timeout_timer:
            self._task_timeout_timer.stop()
        self._task_timeout_timer = QTimer(self)
        self._task_timeout_timer.setSingleShot(True)
        def _revert():
            if getattr(self, "is_asleep", False):
                return
            self._dynamic_width = None
            self.update_state("READY")
            self._apply_geometry()
        self._task_timeout_timer.timeout.connect(_revert)
        self._task_timeout_timer.start(3500)

    # ── State Updates & Media Switcher ────────────────────────────────────────
    def update_state(self, state: str, detail: str = ""):
        st = state.upper().strip()
        # Strictly lock island in SLEEPING state while asleep:
        if getattr(self, "is_asleep", False) and st != "SLEEPING":
            return
        # Strictly lock island in TYPING state while typing is active:
        if getattr(self, "is_typing", False) and st not in ("TYPING", "DICTATION", "SLEEPING"):
            return

        self.current_state = st
        accent = self.cfg.get("accent_color", "#00d4ff")

        # Handle custom media or arc reactor
        self._update_media_for_state(self.current_state)

        if self.current_state == "SPEAKING":
            self.status_lbl.setText(detail or "SPEAKING...")
            self.status_lbl.setStyleSheet("color: #00ff88; background: transparent;")
            self.arc_reactor.set_state("SPEAKING", speaking=True, muted=self.is_muted)
            self.badge_lbl.setText("🔊")
            self.badge_lbl.setStyleSheet("color: #00ff88; background: transparent;")

        elif self.current_state == "LISTENING":
            self.status_lbl.setText(detail or "LISTENING...")
            self.status_lbl.setStyleSheet(f"color: {accent}; background: transparent;")
            self.arc_reactor.set_state("LISTENING", speaking=False, muted=self.is_muted)
            self.badge_lbl.setText("🎙️")
            self.badge_lbl.setStyleSheet(f"color: {accent}; background: transparent;")

        elif self.current_state in ("TYPING", "DICTATION"):
            self.status_lbl.setText(detail or "TYPING...")
            self.status_lbl.setStyleSheet("color: #a855f7; background: transparent; font-weight: bold;")
            self.arc_reactor.set_state("LISTENING", speaking=False, muted=self.is_muted)
            self.badge_lbl.setText("⌨️")
            self.badge_lbl.setStyleSheet("color: #a855f7; background: transparent;")

        elif self.current_state in ("THINKING", "PROCESSING"):
            self.status_lbl.setText(detail or "THINKING...")
            self.status_lbl.setStyleSheet("color: #ff9900; background: transparent;")
            self.arc_reactor.set_state("THINKING", speaking=False, muted=self.is_muted)
            self.badge_lbl.setText("⚙️")
            self.badge_lbl.setStyleSheet("color: #ff9900; background: transparent;")

        elif "TASK" in self.current_state or "COMPLETE" in self.current_state or "DONE" in self.current_state:
            self.status_lbl.setText(detail or "TASK COMPLETED")
            self.status_lbl.setStyleSheet("color: #bf5af2; background: transparent;")
            self.arc_reactor.set_state("TASK_COMPLETED", speaking=False, muted=self.is_muted)
            self.badge_lbl.setText("✓")
            self.badge_lbl.setStyleSheet("color: #bf5af2; background: transparent;")

            # Auto-revert to READY after 3.5 seconds
            if self._task_timeout_timer:
                self._task_timeout_timer.stop()
            self._task_timeout_timer = QTimer(self)
            self._task_timeout_timer.setSingleShot(True)
            def _task_revert():
                if getattr(self, "is_asleep", False):
                    return
                self.update_state("READY")
            self._task_timeout_timer.timeout.connect(_task_revert)
            self._task_timeout_timer.start(3500)

        elif self.current_state == "SLEEPING":
            self.is_asleep = True
            if self._task_timeout_timer:
                self._task_timeout_timer.stop()
            self._dynamic_width = None
            self.status_lbl.setText("SLEEPING")
            self.status_lbl.setStyleSheet("color: #718096; background: transparent; font-weight: bold;")
            self.arc_reactor.set_state("SLEEPING", speaking=False, muted=self.is_muted)
            self.badge_lbl.setText("💤")
            self.badge_lbl.setStyleSheet("color: #718096; background: transparent;")
            self._apply_styles()
            self._apply_geometry()

        else:  # READY / IDLE
            if not getattr(self, "is_asleep", False):
                self.status_lbl.setText(detail or "READY")
                self.status_lbl.setStyleSheet(f"color: {accent}; background: transparent;")
                self.arc_reactor.set_state("IDLE", speaking=False, muted=self.is_muted)
                self.badge_lbl.setText("◈")
                self.badge_lbl.setStyleSheet(f"color: {accent}; background: transparent;")
                self._apply_styles()

    def set_audio_level(self, level: float):
        if getattr(self, "is_asleep", False):
            self.arc_reactor.set_audio_level(0.0)
            return
        self.arc_reactor.set_audio_level(level)

    def set_muted(self, muted: bool):
        self.is_muted = muted
        self.arc_reactor.set_state(self.current_state, speaking=self.is_speaking, muted=muted)
        self._apply_styles()

    def set_asleep(self, asleep: bool):
        self.is_asleep = asleep
        if self._task_timeout_timer:
            try:
                self._task_timeout_timer.stop()
            except Exception:
                pass
        self._dynamic_width = None
        if asleep:
            self.update_state("SLEEPING")
        else:
            self.is_asleep = False
            self.update_state("READY")
            self._apply_geometry()

    def set_typing(self, typing: bool, text: str = ""):
        """Thread-safe: toggle typing/dictation mode on Origin Island."""
        self.typing_sig.emit(typing, text)

    def _do_set_typing(self, typing: bool, text: str = ""):
        self.is_typing = bool(typing)
        if self._task_timeout_timer:
            try:
                self._task_timeout_timer.stop()
            except Exception:
                pass
        self._dynamic_width = None
        if typing:
            self.current_state = "TYPING"
            display_text = text or "TYPING..."
            self.status_lbl.setText(display_text)
            self.status_lbl.setStyleSheet("color: #a855f7; background: transparent; font-weight: bold;")
            self.arc_reactor.set_state("LISTENING", speaking=False, muted=self.is_muted)
            self.badge_lbl.setText("⌨️")
            self.badge_lbl.setStyleSheet("color: #a855f7; background: transparent;")
            self._update_media_for_state("TYPING")
            self._apply_geometry()
        else:
            self.is_typing = False
            self.set_task_result("TEXT TYPED", True)

    def _update_media_for_state(self, state: str):
        """Switches between built-in Arc Reactor and user-selected custom GIF/image."""
        path_str = ""
        if state == "SPEAKING":
            path_str = self.cfg.get("custom_speaking_gif", "")
        elif state == "LISTENING":
            path_str = self.cfg.get("custom_listening_gif", "")
        else:
            path_str = self.cfg.get("custom_idle_gif", "")

        if path_str and Path(path_str).exists():
            ext = Path(path_str).suffix.lower()
            if ext == ".gif":
                if self._custom_movie:
                    self._custom_movie.stop()
                self._custom_movie = QMovie(path_str)
                self._custom_movie.setScaledSize(QSize(34, 34))
                self.custom_media_lbl.setMovie(self._custom_movie)
                self._custom_movie.start()
            else:
                pm = QPixmap(path_str).scaled(
                    34, 34,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.custom_media_lbl.setPixmap(pm)

            self.arc_reactor.hide()
            self.custom_media_lbl.show()
        else:
            if self._custom_movie:
                self._custom_movie.stop()
                self._custom_movie = None
            self.custom_media_lbl.hide()
            self.arc_reactor.show()

    # ── Interactive Expand / Collapse ─────────────────────────────────────────
    def toggle_expand(self):
        if self.expanded:
            self.collapse()
        else:
            self.expand()

    def expand(self):
        self.expanded = True
        self.drawer_widget.show()
        self._apply_geometry()

    def collapse(self):
        self.expanded = False
        self.drawer_widget.hide()
        self._apply_geometry()

    def _handle_mic_btn(self):
        if self.on_mute_click:
            self.on_mute_click()
        else:
            self.set_muted(not self.is_muted)

    def _handle_sleep_btn(self):
        if self.is_asleep:
            if self.on_wake_click:
                self.on_wake_click()
            else:
                self.set_asleep(False)
        else:
            if self.on_sleep_click:
                self.on_sleep_click()
            else:
                self.set_asleep(True)

    # ── Mouse Interaction (Locked Fixed Position — Click to Expand/Collapse) ──

    def _handle_todo_btn(self):
        if self.on_todo_click:
            self.on_todo_click()
        elif self.on_settings_click:
            self.on_settings_click()

    def _handle_settings_btn(self):
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #06090e;
                color: #e2e8f0;
                border: 1px solid #00d4ff;
                padding: 4px;
                border-radius: 6px;
            }
            QMenu::item {
                padding: 6px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: rgba(0, 212, 255, 0.25);
                color: #ffffff;
            }
        """)
        act_todo = menu.addAction("📝 To-Do List & Reminders Menu")
        act_island = menu.addAction("⚙ Origin Island Configuration")

        pos = self.settings_btn.mapToGlobal(QPoint(0, self.settings_btn.height() + 2))
        chosen = menu.exec(pos)
        if chosen == act_todo:
            self._handle_todo_btn()
        elif chosen == act_island:
            if self.on_settings_click:
                self.on_settings_click()

    def show_reminder_alert(self, title: str, message: str, alert_type: str = "due"):
        """Thread-safe: displays proactive reminder alert on Origin Island with audio chime and dynamic width."""
        self.reminder_alert_sig.emit(title, message, alert_type)

    def _do_show_reminder_alert(self, title: str, message: str, alert_type: str = "due"):
        def _beep():
            try:
                import winsound
                freqs = [880, 1108, 1318] if alert_type == "5m" else [784, 988]
                for f in freqs:
                    winsound.Beep(f, 120)
            except Exception:
                pass
        import threading
        threading.Thread(target=_beep, daemon=True).start()

        full_text = f"🔔 {message}"
        fm = QFontMetrics(self.status_lbl.font())
        needed_w = fm.horizontalAdvance(full_text) + 120
        base_w = int(self.cfg.get("width", 290))
        self._dynamic_width = max(base_w, min(needed_w, 780))

        color = "#ff9900" if alert_type in ("10m", "5m") else "#00d4ff"
        self.current_state = "PROCESSING"
        self._update_media_for_state("PROCESSING")
        self.status_lbl.setText(full_text)
        self.status_lbl.setStyleSheet(f"color: {color}; background: transparent; font-weight: bold;")
        self.arc_reactor.set_state("THINKING", speaking=False, muted=self.is_muted)
        self.badge_lbl.setText("🔔")
        self.badge_lbl.setStyleSheet(f"color: {color}; background: transparent; font-weight: bold;")
        self._apply_geometry()

        if self._task_timeout_timer:
            try:
                self._task_timeout_timer.stop()
            except Exception:
                pass
        self._task_timeout_timer = QTimer(self)
        self._task_timeout_timer.setSingleShot(True)
        def _revert():
            if getattr(self, "is_asleep", False):
                return
            self._dynamic_width = None
            self.update_state("READY")
            self._apply_geometry()
        self._task_timeout_timer.timeout.connect(_revert)
        self._task_timeout_timer.start(5500)

    def contextMenuEvent(self, event):
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #06090e;
                color: #e2e8f0;
                border: 1px solid #00d4ff;
                padding: 4px;
                border-radius: 6px;
            }
            QMenu::item {
                padding: 6px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: rgba(0, 212, 255, 0.25);
                color: #ffffff;
            }
        """)
        action_toggle_expand = menu.addAction("▲ Collapse Island" if self.expanded else "▼ Expand Island")
        has_b = self.cfg.get("border_enabled", True)
        action_toggle_border = menu.addAction("○ Remove Border (Borderless)" if has_b else "◉ Add Border")
        action_todo = menu.addAction("📝 To-Do List & Reminders...")
        action_settings = menu.addAction("⚙ Origin Island Settings...")
        menu.addSeparator()
        action_exit = menu.addAction("🛑 Exit / Close JARVIS")

        chosen = menu.exec(event.globalPos())
        if chosen == action_toggle_expand:
            self.toggle_expand()
        elif chosen == action_toggle_border:
            self.cfg["border_enabled"] = not has_b
            save_island_config(self.cfg)
            self._apply_styles()
        elif chosen == action_todo:
            self._handle_todo_btn()
        elif chosen == action_settings:
            if self.on_settings_click:
                self.on_settings_click()
        elif chosen == action_exit:
            self._close_application()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()

    def mouseMoveEvent(self, event):
        # The island position is strictly locked on-screen.
        # It cannot be moved or dragged with the mouse.
        # Position can only be adjusted from the Origin Island Settings panel.
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Single click exclusively expands/collapses the island without moving it
            self.toggle_expand()
            event.accept()


# Global Singleton for Origin Island
_island_instance: Optional[OriginIslandWindow] = None


def get_origin_island() -> Optional[OriginIslandWindow]:
    return _island_instance


def init_origin_island() -> OriginIslandWindow:
    global _island_instance
    if _island_instance is None:
        _island_instance = OriginIslandWindow()
    return _island_instance
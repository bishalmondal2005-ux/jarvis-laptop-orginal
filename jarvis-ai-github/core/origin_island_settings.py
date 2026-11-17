"""
core/origin_island_settings.py - Settings Overlay for Origin Island in Mark-LVI.

Provides an intuitive UI inside Mark-LVI to configure:
1. Origin Island Position:
   - Presets (Top-Center iPhone style, Top-Left, Top-Right, Bottom-Center, Custom)
   - Arrow nudge buttons (Up, Down, Left, Right)
   - Exact X, Y coordinate adjustments
2. Dimensions (Width / Choura, Height / Lomba):
   - Sliders and numeric spinboxes
3. Visual Styling & Themes:
   - Background Color & Opacity
   - Accent & Border Glow Color
   - Color presets (AMOLED Dark, Stark Cyan, Neon Emerald, Arc Gold, Cyber Crimson)
4. Custom Media Uploaders (GIF & Images):
   - Custom Speaking State Animation (GIF / Image)
   - Custom Listening State Animation (GIF / Image)
   - Custom Idle State Animation (GIF / Image)
   - Built-in Fallback to Arc Reactor if cleared
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QColorDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.origin_island import (
    get_origin_island,
    load_island_config,
    save_island_config,
)
from core.todo_ui import TodoListWidget


class OriginIslandSettingsOverlay(QWidget):
    """Floating overlay to customize Origin Island settings."""

    _OW, _OH = 490, 690

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            OriginIslandSettingsOverlay {
                background: rgba(0, 8, 14, 248);
                border: 1px solid #00d4ff;
                border-radius: 8px;
            }
            QLabel {
                color: #e2e8f0;
                font-family: 'Segoe UI', sans-serif;
            }
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #cbd5e1;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 4px;
                padding: 4px 8px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(0, 212, 255, 0.2);
                border: 1px solid #00d4ff;
                color: #ffffff;
            }
            QSpinBox {
                background: #00121a;
                color: #ffffff;
                border: 1px solid rgba(0, 212, 255, 0.4);
                border-radius: 4px;
                padding: 3px 6px;
                font-family: 'Segoe UI', sans-serif;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: rgba(255, 255, 255, 0.15);
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #00d4ff;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #00d4ff;
                width: 14px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 7px;
            }
        """)

        self.cfg = load_island_config()
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(10)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("⚙  SYSTEM SETTINGS & TASKS")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setStyleSheet("color: #00d4ff; letter-spacing: 0.5px;")
        hdr.addWidget(title)
        hdr.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("background: transparent; border: none; font-size: 13px; color: #94a3b8;")
        close_btn.clicked.connect(self.hide)
        hdr.addWidget(close_btn)
        main_layout.addLayout(hdr)

        # Tab Navigation
        tab_row = QHBoxLayout()
        tab_row.setSpacing(8)
        self.btn_tab_island = QPushButton("🏝 ORIGIN ISLAND")
        self.btn_tab_island.setFixedHeight(30)
        self.btn_tab_island.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_island.clicked.connect(lambda: self._switch_tab(0))

        self.btn_tab_todo = QPushButton("📝 TO-DO LIST & REMINDERS")
        self.btn_tab_todo.setFixedHeight(30)
        self.btn_tab_todo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_todo.clicked.connect(lambda: self._switch_tab(1))

        tab_row.addWidget(self.btn_tab_island)
        tab_row.addWidget(self.btn_tab_todo)
        main_layout.addLayout(tab_row)

        div0 = QFrame()
        div0.setFrameShape(QFrame.Shape.HLine)
        div0.setStyleSheet("color: rgba(0, 212, 255, 0.3);")
        main_layout.addWidget(div0)

        self.stack = QStackedWidget(self)
        main_layout.addWidget(self.stack)

        # Page 0: Island Settings
        self.page_island = QWidget()
        page_island_layout = QVBoxLayout(self.page_island)
        page_island_layout.setContentsMargins(0, 0, 0, 0)
        page_island_layout.setSpacing(10)

        # Scrollable Area for all options
        scroll = QScrollArea(self.page_island)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(4, 4, 8, 4)
        lay.setSpacing(12)

        # ── 1. Enable / Disable ──
        sec1_hdr = QLabel("1. ACTIVE STATUS")
        sec1_hdr.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        sec1_hdr.setStyleSheet("color: #7dd3fc;")
        lay.addWidget(sec1_hdr)

        status_row = QHBoxLayout()
        self.toggle_btn = QPushButton("◉  ENABLED" if self.cfg.get("enabled", True) else "○  DISABLED")
        self.toggle_btn.setFixedHeight(28)
        self.toggle_btn.clicked.connect(self._toggle_enabled)
        status_row.addWidget(self.toggle_btn)
        lay.addLayout(status_row)

        # ── 2. Position & Nudge Controls ──
        sec2_hdr = QLabel("2. SCREEN POSITION & PLACEMENT (🔒 LOCKED ON SCREEN)")
        sec2_hdr.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        sec2_hdr.setStyleSheet("color: #7dd3fc;")
        lay.addWidget(sec2_hdr)

        lock_notice = QLabel("🔒 Island is locked in place. Adjust position exclusively using the controls below:")
        lock_notice.setFont(QFont("Segoe UI", 7))
        lock_notice.setStyleSheet("color: #94a3b8; background: rgba(0, 212, 255, 0.06); padding: 4px; border-radius: 4px;")
        lay.addWidget(lock_notice)

        preset_row = QHBoxLayout()
        presets = [
            ("top_center", "Top Center"),
            ("top_left", "Top Left"),
            ("top_right", "Top Right"),
            ("bottom_center", "Bottom Center"),
        ]
        self.preset_btns = {}
        for key, text in presets:
            btn = QPushButton(text)
            btn.setFixedHeight(26)
            btn.clicked.connect(lambda _, k=key: self._set_preset(k))
            preset_row.addWidget(btn)
            self.preset_btns[key] = btn
        lay.addLayout(preset_row)

        # Directional Nudge Grid (Up, Down, Left, Right)
        nudge_box = QWidget()
        nudge_grid = QGridLayout(nudge_box)
        nudge_grid.setContentsMargins(0, 2, 0, 2)
        nudge_grid.setSpacing(6)

        btn_up = QPushButton("⬆  Up")
        btn_up.clicked.connect(lambda: self._nudge(0, -18))
        btn_down = QPushButton("⬇  Down")
        btn_down.clicked.connect(lambda: self._nudge(0, 18))
        btn_left = QPushButton("⬅  Left")
        btn_left.clicked.connect(lambda: self._nudge(-25, 0))
        btn_right = QPushButton("➡  Right")
        btn_right.clicked.connect(lambda: self._nudge(25, 0))

        nudge_grid.addWidget(btn_up, 0, 1)
        nudge_grid.addWidget(btn_left, 1, 0)
        nudge_grid.addWidget(btn_down, 1, 1)
        nudge_grid.addWidget(btn_right, 1, 2)
        lay.addWidget(nudge_box)

        # Exact Coordinates
        coord_row = QHBoxLayout()
        coord_row.addWidget(QLabel("X Coordinate:"))
        self.spin_x = QSpinBox()
        self.spin_x.setRange(-1, 3840)
        self.spin_x.setValue(int(self.cfg.get("x", -1)))
        self.spin_x.valueChanged.connect(self._coord_changed)
        coord_row.addWidget(self.spin_x)

        coord_row.addWidget(QLabel("Y Coordinate:"))
        self.spin_y = QSpinBox()
        self.spin_y.setRange(0, 2160)
        self.spin_y.setValue(int(self.cfg.get("y", 18)))
        self.spin_y.valueChanged.connect(self._coord_changed)
        coord_row.addWidget(self.spin_y)
        lay.addLayout(coord_row)

        # ── 3. Dimensions (Width & Height / Lomba & Choura) ──
        sec3_hdr = QLabel("3. DIMENSIONS & SIZING (Lomba & Choura)")
        sec3_hdr.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        sec3_hdr.setStyleSheet("color: #7dd3fc;")
        lay.addWidget(sec3_hdr)

        # Width
        w_lbl_row = QHBoxLayout()
        w_lbl_row.addWidget(QLabel("Width (Choura):"))
        self.w_val_lbl = QLabel(f"{self.cfg.get('width', 290)} px")
        self.w_val_lbl.setStyleSheet("color: #00d4ff; font-weight: bold;")
        w_lbl_row.addWidget(self.w_val_lbl)
        lay.addLayout(w_lbl_row)

        self.w_slider = QSlider(Qt.Orientation.Horizontal)
        self.w_slider.setRange(200, 560)
        self.w_slider.setValue(int(self.cfg.get("width", 290)))
        self.w_slider.valueChanged.connect(self._on_width_change)
        lay.addWidget(self.w_slider)

        # Height
        h_lbl_row = QHBoxLayout()
        h_lbl_row.addWidget(QLabel("Height (Lomba):"))
        self.h_val_lbl = QLabel(f"{self.cfg.get('height', 44)} px")
        self.h_val_lbl.setStyleSheet("color: #00d4ff; font-weight: bold;")
        h_lbl_row.addWidget(self.h_val_lbl)
        lay.addLayout(h_lbl_row)

        self.h_slider = QSlider(Qt.Orientation.Horizontal)
        self.h_slider.setRange(36, 75)
        self.h_slider.setValue(int(self.cfg.get("height", 44)))
        self.h_slider.valueChanged.connect(self._on_height_change)
        lay.addWidget(self.h_slider)

        # ── 4. Border & Outline Customization (Remove / Add & Color) ──
        sec_border_hdr = QLabel("4. BORDER & OUTLINE (Remove / Add & Color)")
        sec_border_hdr.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        sec_border_hdr.setStyleSheet("color: #7dd3fc;")
        lay.addWidget(sec_border_hdr)

        border_btn_row = QHBoxLayout()
        self.border_toggle_btn = QPushButton()
        self.border_toggle_btn.setFixedHeight(28)
        self.border_toggle_btn.clicked.connect(self._toggle_border)
        self._update_border_btn_ui()
        border_btn_row.addWidget(self.border_toggle_btn)

        self.pick_border_btn = QPushButton(f"Border Color: {self.cfg.get('border_color', self.cfg.get('accent_color', '#00d4ff'))}")
        self.pick_border_btn.setFixedHeight(28)
        self.pick_border_btn.clicked.connect(self._pick_custom_border_color)
        border_btn_row.addWidget(self.pick_border_btn)
        lay.addLayout(border_btn_row)

        # Border Color Presets
        border_col_row = QHBoxLayout()
        border_presets = [
            ("Cyan", "#00d4ff"),
            ("White", "#ffffff"),
            ("Gold", "#ffb703"),
            ("Emerald", "#10b981"),
            ("Crimson", "#ef4444"),
            ("Purple", "#a855f7"),
            ("Titanium", "#64748b"),
        ]
        for name, col in border_presets:
            b_btn = QPushButton(name)
            b_btn.setFixedHeight(22)
            b_btn.setStyleSheet(f"background: rgba(255,255,255,0.06); border: 1px solid {col}; color: {col}; font-size: 10px;")
            b_btn.clicked.connect(lambda _, c=col: self._set_border_color(c))
            border_col_row.addWidget(b_btn)
        lay.addLayout(border_col_row)

        # Border Width Slider
        bw_row = QHBoxLayout()
        bw_row.addWidget(QLabel("Border Width:"))
        self.bw_lbl = QLabel(f"{self.cfg.get('border_width', 1)} px")
        self.bw_lbl.setStyleSheet("color: #00d4ff; font-weight: bold;")
        bw_row.addWidget(self.bw_lbl)
        lay.addLayout(bw_row)

        self.bw_slider = QSlider(Qt.Orientation.Horizontal)
        self.bw_slider.setRange(1, 5)
        self.bw_slider.setValue(int(self.cfg.get('border_width', 1)))
        self.bw_slider.valueChanged.connect(self._on_border_width_change)
        lay.addWidget(self.bw_slider)

        # ── 5. Colors & Theme Customization ──
        sec4_hdr = QLabel("5. COLOR & THEME STYLING")
        sec4_hdr.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        sec4_hdr.setStyleSheet("color: #7dd3fc;")
        lay.addWidget(sec4_hdr)

        # Quick Theme Presets
        theme_row = QHBoxLayout()
        themes = [
            ("Cyan", "#00d4ff"),
            ("Gold", "#ffb703"),
            ("Emerald", "#10b981"),
            ("Crimson", "#ef4444"),
            ("Purple", "#a855f7"),
        ]
        for name, col in themes:
            btn = QPushButton(name)
            btn.setFixedHeight(24)
            btn.setStyleSheet(f"background: rgba(255,255,255,0.06); border: 1px solid {col}; color: {col};")
            btn.clicked.connect(lambda _, c=col: self._set_accent_color(c))
            theme_row.addWidget(btn)
        lay.addLayout(theme_row)

        # Custom Pickers
        col_pick_row = QHBoxLayout()
        self.pick_accent_btn = QPushButton(f"Accent Color: {self.cfg.get('accent_color', '#00d4ff')}")
        self.pick_accent_btn.clicked.connect(self._pick_custom_accent)
        col_pick_row.addWidget(self.pick_accent_btn)

        self.pick_bg_btn = QPushButton(f"Background: {self.cfg.get('bg_color', '#06090e')}")
        self.pick_bg_btn.clicked.connect(self._pick_custom_bg)
        col_pick_row.addWidget(self.pick_bg_btn)
        lay.addLayout(col_pick_row)

        # ── 5. Custom GIF / Image Animations per State ──
        sec5_hdr = QLabel("6. CUSTOM GIF / IMAGE ANIMATIONS (Default: Arc Reactor)")
        sec5_hdr.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        sec5_hdr.setStyleSheet("color: #7dd3fc;")
        lay.addWidget(sec5_hdr)

        # Speaking State Media
        lay.addWidget(QLabel("Speaking State (When JARVIS speaks):"))
        spk_row = QHBoxLayout()
        self.spk_input = QLineEdit(self.cfg.get("custom_speaking_gif", ""))
        self.spk_input.setPlaceholderText("Default: Built-in Arc Reactor (or select .gif/.png)")
        self.spk_input.setReadOnly(True)
        spk_row.addWidget(self.spk_input)
        spk_browse = QPushButton("📁 Browse")
        spk_browse.clicked.connect(lambda: self._browse_media("custom_speaking_gif", self.spk_input))
        spk_row.addWidget(spk_browse)
        spk_clear = QPushButton("✕ Clear")
        spk_clear.clicked.connect(lambda: self._clear_media("custom_speaking_gif", self.spk_input))
        spk_row.addWidget(spk_clear)
        lay.addLayout(spk_row)

        # Listening State Media
        lay.addWidget(QLabel("Listening State (When listening to command):"))
        lis_row = QHBoxLayout()
        self.lis_input = QLineEdit(self.cfg.get("custom_listening_gif", ""))
        self.lis_input.setPlaceholderText("Default: Built-in Arc Reactor (or select .gif/.png)")
        self.lis_input.setReadOnly(True)
        lis_row.addWidget(self.lis_input)
        lis_browse = QPushButton("📁 Browse")
        lis_browse.clicked.connect(lambda: self._browse_media("custom_listening_gif", self.lis_input))
        lis_row.addWidget(lis_browse)
        lis_clear = QPushButton("✕ Clear")
        lis_clear.clicked.connect(lambda: self._clear_media("custom_listening_gif", self.lis_input))
        lis_row.addWidget(lis_clear)
        lay.addLayout(lis_row)

        # Idle State Media
        lay.addWidget(QLabel("Idle / Ready State:"))
        idle_row = QHBoxLayout()
        self.idle_input = QLineEdit(self.cfg.get("custom_idle_gif", ""))
        self.idle_input.setPlaceholderText("Default: Built-in Arc Reactor (or select .gif/.png)")
        self.idle_input.setReadOnly(True)
        idle_row.addWidget(self.idle_input)
        idle_browse = QPushButton("📁 Browse")
        idle_browse.clicked.connect(lambda: self._browse_media("custom_idle_gif", self.idle_input))
        idle_row.addWidget(idle_browse)
        idle_clear = QPushButton("✕ Clear")
        idle_clear.clicked.connect(lambda: self._clear_media("custom_idle_gif", self.idle_input))
        idle_row.addWidget(idle_clear)
        lay.addLayout(idle_row)

        scroll.setWidget(container)
        page_island_layout.addWidget(scroll)

        # Bottom Actions
        bot_row = QHBoxLayout()
        test_btn = QPushButton("⚡ PREVIEW & TEST ISLAND")
        test_btn.setFixedHeight(34)
        test_btn.setStyleSheet("background: rgba(0, 212, 255, 0.2); border: 1px solid #00d4ff; color: #00d4ff; font-weight: bold;")
        test_btn.clicked.connect(self._preview_island)
        bot_row.addWidget(test_btn)

        save_btn = QPushButton("💾 SAVE SETTINGS")
        save_btn.setFixedHeight(34)
        save_btn.setStyleSheet("background: #00d4ff; color: #000d12; border: none; font-weight: bold;")
        save_btn.clicked.connect(self._save_and_close)
        bot_row.addWidget(save_btn)
        page_island_layout.addLayout(bot_row)

        self.stack.addWidget(self.page_island)

        # Page 1: To-Do List & Reminders
        self.page_todo = QWidget()
        page_todo_layout = QVBoxLayout(self.page_todo)
        page_todo_layout.setContentsMargins(0, 0, 0, 0)
        self.todo_widget = TodoListWidget(self.page_todo)
        page_todo_layout.addWidget(self.todo_widget)
        self.stack.addWidget(self.page_todo)

        self._switch_tab(0)

    def _switch_tab(self, index: int):
        self.stack.setCurrentIndex(index)
        if index == 0:
            self.btn_tab_island.setStyleSheet(
                "background: rgba(0, 212, 255, 0.25); color: #00d4ff; border: 1px solid #00d4ff; font-weight: bold; border-radius: 4px; padding: 4px;"
            )
            self.btn_tab_todo.setStyleSheet(
                "background: rgba(255, 255, 255, 0.06); color: #94a3b8; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 4px; padding: 4px;"
            )
        else:
            self.btn_tab_todo.setStyleSheet(
                "background: rgba(0, 212, 255, 0.25); color: #00d4ff; border: 1px solid #00d4ff; font-weight: bold; border-radius: 4px; padding: 4px;"
            )
            self.btn_tab_island.setStyleSheet(
                "background: rgba(255, 255, 255, 0.06); color: #94a3b8; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 4px; padding: 4px;"
            )
            if hasattr(self, "todo_widget"):
                self.todo_widget.refresh_tasks()

    def open_todo_tab(self):
        self._switch_tab(1)
        self.show()
        self.raise_()
        self.activateWindow()

    # ── Configuration Callbacks ──
    def _toggle_enabled(self):
        curr = self.cfg.get("enabled", True)
        self.cfg["enabled"] = not curr
        self.toggle_btn.setText("◉  ENABLED" if self.cfg["enabled"] else "○  DISABLED")
        island = get_origin_island()
        if island:
            if self.cfg["enabled"]:
                island.show()
            else:
                island.hide()

    def _set_preset(self, preset_key: str):
        self.cfg["preset"] = preset_key
        island = get_origin_island()
        if island:
            if island.expanded:
                island.collapse()
            island.cfg["preset"] = preset_key
            island._apply_geometry()
            self.spin_x.setValue(island.x())
            self.spin_y.setValue(island.y())
            self.cfg["x"] = island.x()
            self.cfg["y"] = island.y()
            save_island_config(self.cfg)

    def _nudge(self, dx: int, dy: int):
        island = get_origin_island()
        if island:
            curr_x = self.cfg.get("x", -1)
            curr_y = self.cfg.get("y", 18)
            if curr_x < 0:
                curr_x = island.x()
            new_x = max(0, curr_x + dx)
            new_y = max(0, curr_y + dy)
            self.cfg["preset"] = "custom"
            self.cfg["x"] = new_x
            self.cfg["y"] = new_y
            save_island_config(self.cfg)
            island.cfg["preset"] = "custom"
            island.cfg["x"] = new_x
            island.cfg["y"] = new_y
            island._apply_geometry()
            self.spin_x.setValue(new_x)
            self.spin_y.setValue(new_y)

    def _coord_changed(self):
        self.cfg["preset"] = "custom"
        self.cfg["x"] = self.spin_x.value()
        self.cfg["y"] = self.spin_y.value()
        save_island_config(self.cfg)
        island = get_origin_island()
        if island:
            island.cfg["preset"] = "custom"
            island.cfg["x"] = self.spin_x.value()
            island.cfg["y"] = self.spin_y.value()
            island._apply_geometry()

    def _on_width_change(self, val: int):
        self.cfg["width"] = val
        self.w_val_lbl.setText(f"{val} px")
        island = get_origin_island()
        if island:
            island.cfg["width"] = val
            island._apply_geometry()

    def _on_height_change(self, val: int):
        self.cfg["height"] = val
        self.h_val_lbl.setText(f"{val} px")
        island = get_origin_island()
        if island:
            island.cfg["height"] = val
            island._apply_geometry()

    def _set_accent_color(self, hex_col: str):
        self.cfg["accent_color"] = hex_col
        self.pick_accent_btn.setText(f"Accent Color: {hex_col}")
        island = get_origin_island()
        if island:
            island.cfg["accent_color"] = hex_col
            island._apply_styles()
            island.update_state(island.current_state)

    def _update_border_btn_ui(self):
        enabled = self.cfg.get("border_enabled", True)
        if enabled:
            self.border_toggle_btn.setText("◉  BORDER: ON (Visible - Click to Remove)")
            self.border_toggle_btn.setStyleSheet("background: rgba(16, 185, 129, 0.25); color: #6ee7b7; border: 1px solid #10b981; font-weight: bold; border-radius: 4px;")
        else:
            self.border_toggle_btn.setText("○  BORDER: OFF (Borderless - Click to Add)")
            self.border_toggle_btn.setStyleSheet("background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid #ef4444; font-weight: bold; border-radius: 4px;")

    def _toggle_border(self):
        curr = self.cfg.get("border_enabled", True)
        self.cfg["border_enabled"] = not curr
        self._update_border_btn_ui()
        save_island_config(self.cfg)
        island = get_origin_island()
        if island:
            island.cfg["border_enabled"] = self.cfg["border_enabled"]
            island._apply_styles()

    def _set_border_color(self, hex_col: str):
        self.cfg["border_color"] = hex_col
        self.cfg["border_enabled"] = True
        self._update_border_btn_ui()
        self.pick_border_btn.setText(f"Border Color: {hex_col}")
        save_island_config(self.cfg)
        island = get_origin_island()
        if island:
            island.cfg["border_color"] = hex_col
            island.cfg["border_enabled"] = True
            island._apply_styles()

    def _pick_custom_border_color(self):
        col = QColorDialog.getColor(QColor(self.cfg.get("border_color", "#00d4ff")), self, "Choose Border Color")
        if col.isValid():
            self._set_border_color(col.name())

    def _on_border_width_change(self, val: int):
        self.cfg["border_width"] = val
        self.bw_lbl.setText(f"{val} px")
        save_island_config(self.cfg)
        island = get_origin_island()
        if island:
            island.cfg["border_width"] = val
            island._apply_styles()

    def _pick_custom_accent(self):
        col = QColorDialog.getColor(QColor(self.cfg.get("accent_color", "#00d4ff")), self, "Choose Accent Color")
        if col.isValid():
            self._set_accent_color(col.name())

    def _pick_custom_bg(self):
        col = QColorDialog.getColor(QColor(self.cfg.get("bg_color", "#06090e")), self, "Choose Background Color")
        if col.isValid():
            self.cfg["bg_color"] = col.name()
            self.pick_bg_btn.setText(f"Background: {col.name()}")
            island = get_origin_island()
            if island:
                island.cfg["bg_color"] = col.name()
                island._apply_styles()

    def _browse_media(self, key: str, line_edit: QLineEdit):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select GIF or Image", "", "Media Files (*.gif *.png *.jpg *.jpeg *.webp)"
        )
        if path:
            self.cfg[key] = path
            line_edit.setText(path)
            island = get_origin_island()
            if island:
                island.cfg[key] = path
                island._update_media_for_state(island.current_state)

    def _clear_media(self, key: str, line_edit: QLineEdit):
        self.cfg[key] = ""
        line_edit.setText("")
        island = get_origin_island()
        if island:
            island.cfg[key] = ""
            island._update_media_for_state(island.current_state)

    def _preview_island(self):
        island = get_origin_island()
        if island:
            island.show()
            island.update_state("LISTENING", "VOICE COMMAND READY")
            QTimer.singleShot(2500, lambda: island.update_state("SPEAKING", "ONLINE & MONITORING"))
            QTimer.singleShot(5000, lambda: island.update_state("TASK_COMPLETED", "TASK COMPLETED"))
            QTimer.singleShot(7500, lambda: island.update_state("READY"))

    def _save_and_close(self):
        save_island_config(self.cfg)
        island = get_origin_island()
        if island:
            island.cfg = dict(self.cfg)
            island._apply_geometry()
            island._apply_styles()
        self.hide()

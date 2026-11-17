"""
core/todo_ui.py - Interactive To-Do List & Reminder Widget for Mark-LVI.

Provides:
- Input form to create and MODIFY/EDIT tasks (Date Only or Time & Date).
- Dynamic list of Pending / Active tasks with due countdown.
- Ability to Edit/Modify existing tasks with Save and Cancel.
- Ability to mark completed, restore, or delete tasks.
- Completed tasks archive section with "Clear All".
- Seamlessly styled in Stark Cyan Iron Man theme to match Origin Island.
"""
from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from PyQt6.QtCore import QDate, QTime, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QButtonGroup,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from core import todo_manager


class TaskItemWidget(QFrame):
    """Card widget representing an individual task."""

    status_changed = pyqtSignal()
    edit_requested = pyqtSignal(dict)

    def __init__(self, task: dict, parent=None):
        super().__init__(parent)
        self.task = task
        self.task_id = task.get("id", "")
        self.is_completed = task.get("completed", False)
        self._setup_ui()

    def _setup_ui(self):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        if self.is_completed:
            self.setStyleSheet("""
                TaskItemWidget {
                    background: rgba(15, 23, 42, 0.45);
                    border: 1px solid rgba(148, 163, 184, 0.15);
                    border-radius: 6px;
                }
            """)
        else:
            self.setStyleSheet("""
                TaskItemWidget {
                    background: rgba(0, 20, 32, 0.65);
                    border: 1px solid rgba(0, 212, 255, 0.25);
                    border-radius: 6px;
                }
                TaskItemWidget:hover {
                    border: 1px solid rgba(0, 212, 255, 0.55);
                    background: rgba(0, 28, 45, 0.85);
                }
            """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        # Icon / Type Indicator
        task_type = self.task.get("type", "date")
        icon_str = "⏰" if task_type == "time" else "📅"
        type_lbl = QLabel(icon_str)
        type_lbl.setFont(QFont("Segoe UI Emoji", 10))
        layout.addWidget(type_lbl)

        # Text Block
        text_box = QVBoxLayout()
        text_box.setSpacing(2)

        title_str = self.task.get("title", "")
        title_lbl = QLabel(title_str)
        title_lbl.setWordWrap(True)
        if self.is_completed:
            title_lbl.setFont(QFont("Segoe UI", 9))
            title_lbl.setStyleSheet("color: #64748b; text-decoration: line-through;")
        else:
            title_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            title_lbl.setStyleSheet("color: #f1f5f9;")
        text_box.addWidget(title_lbl)

        # Sub-info: Date / Time + Relative time
        date_str = self.task.get("date", "")
        time_str = self.task.get("time")

        sub_text = self._format_schedule_subtext(date_str, time_str, task_type)
        sub_lbl = QLabel(sub_text)
        sub_lbl.setFont(QFont("Segoe UI", 7))
        sub_lbl.setStyleSheet("color: #00d4ff;" if not self.is_completed else "color: #475569;")
        text_box.addWidget(sub_lbl)

        layout.addLayout(text_box, stretch=1)

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(4)

        if not self.is_completed:
            # Edit Button
            edit_btn = QPushButton("✎ Edit")
            edit_btn.setFixedHeight(24)
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(0, 212, 255, 0.15);
                    color: #00d4ff;
                    border: 1px solid rgba(0, 212, 255, 0.35);
                    border-radius: 4px;
                    font-size: 10px;
                    padding: 2px 8px;
                }
                QPushButton:hover {
                    background: rgba(0, 212, 255, 0.35);
                    color: #ffffff;
                    border: 1px solid #00d4ff;
                }
            """)
            edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.task))
            btn_box.addWidget(edit_btn)

            # Done Button
            done_btn = QPushButton("✓ Done")
            done_btn.setFixedHeight(24)
            done_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            done_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(16, 185, 129, 0.2);
                    color: #34d399;
                    border: 1px solid rgba(16, 185, 129, 0.4);
                    border-radius: 4px;
                    font-size: 10px;
                    padding: 2px 8px;
                }
                QPushButton:hover {
                    background: rgba(16, 185, 129, 0.4);
                    color: #ffffff;
                    border: 1px solid #10b981;
                }
            """)
            done_btn.clicked.connect(self._mark_done)
            btn_box.addWidget(done_btn)
        else:
            restore_btn = QPushButton("⟲ Restore")
            restore_btn.setFixedHeight(24)
            restore_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            restore_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(56, 189, 248, 0.15);
                    color: #7dd3fc;
                    border: 1px solid rgba(56, 189, 248, 0.3);
                    border-radius: 4px;
                    font-size: 10px;
                    padding: 2px 8px;
                }
                QPushButton:hover {
                    background: rgba(56, 189, 248, 0.35);
                    color: #ffffff;
                }
            """)
            restore_btn.clicked.connect(self._restore)
            btn_box.addWidget(restore_btn)

        del_btn = QPushButton("✕")
        del_btn.setFixedSize(24, 24)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.12);
                color: #f87171;
                border: 1px solid rgba(239, 68, 68, 0.25);
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.35);
                color: #ffffff;
                border: 1px solid #ef4444;
            }
        """)
        del_btn.clicked.connect(self._delete)
        btn_box.addWidget(del_btn)

        layout.addLayout(btn_box)

    def _format_schedule_subtext(self, date_str: str, time_str: Optional[str], task_type: str) -> str:
        try:
            today = date.today()
            t_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            delta = (t_date - today).days

            if delta == 0:
                day_prefix = "Today"
            elif delta == 1:
                day_prefix = "Tomorrow"
            elif delta == -1:
                day_prefix = "Yesterday"
            elif delta > 1:
                day_prefix = f"In {delta} days ({date_str})"
            else:
                day_prefix = f"{abs(delta)} days ago ({date_str})"

            if task_type == "time" and time_str:
                now = datetime.now()
                target_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                diff_sec = (target_dt - now).total_seconds()
                if diff_sec > 0 and delta == 0:
                    mins = int(diff_sec // 60)
                    if mins < 60:
                        countdown = f" (in {mins} min{'s' if mins != 1 else ''})"
                    else:
                        hours = mins // 60
                        rem_m = mins % 60
                        countdown = f" (in {hours}h {rem_m}m)"
                elif diff_sec < 0 and delta == 0:
                    countdown = " (Due / Passed)"
                else:
                    countdown = ""
                return f"⏰ {day_prefix} at {time_str}{countdown} • 10m & 5m alerts active"
            else:
                return f"📅 {day_prefix} • Day-before startup reminder active"
        except Exception:
            return f"{date_str} {time_str or ''}"

    def _mark_done(self):
        todo_manager.complete_task(self.task_id)
        self.status_changed.emit()

    def _restore(self):
        todo_manager.uncomplete_task(self.task_id)
        self.status_changed.emit()

    def _delete(self):
        todo_manager.delete_task(self.task_id)
        self.status_changed.emit()


class TodoListWidget(QWidget):
    """Full To-Do List Management Widget for Settings (Create, Modify, Delete)."""

    task_count_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._editing_task_id: Optional[str] = None
        self._setup_ui()
        self.refresh_tasks()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(10)

        # ── Form Card: Create / Modify Task ──
        self.form_card = QFrame()
        self.form_card.setStyleSheet("""
            QFrame {
                background: rgba(0, 16, 26, 0.7);
                border: 1px solid rgba(0, 212, 255, 0.35);
                border-radius: 8px;
                padding: 4px;
            }
        """)
        form_layout = QVBoxLayout(self.form_card)
        form_layout.setSpacing(8)

        self.form_title = QLabel("➕ ADD NEW TASK / REMINDER")
        self.form_title.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.form_title.setStyleSheet("color: #7dd3fc; border: none; letter-spacing: 0.5px;")
        form_layout.addWidget(self.form_title)

        # Task Title Input
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Task description (e.g. 'Sonda 9 tai medicine khabo', '20 January Birthday')...")
        self.title_input.setFixedHeight(30)
        self.title_input.setStyleSheet("""
            QLineEdit {
                background: #00121a;
                color: #ffffff;
                border: 1px solid rgba(0, 212, 255, 0.4);
                border-radius: 4px;
                padding: 4px 8px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 1px solid #00d4ff;
                background: #001924;
            }
        """)
        form_layout.addWidget(self.title_input)

        # Mode Selection: Time & Date vs Date Only
        type_row = QHBoxLayout()
        type_row.setSpacing(16)

        self.radio_time = QRadioButton("⏰ Specific Time & Date")
        self.radio_time.setChecked(True)
        self.radio_time.setFont(QFont("Segoe UI", 8))
        self.radio_time.setStyleSheet("color: #e2e8f0; border: none;")

        self.radio_date = QRadioButton("📅 Specific Date Only")
        self.radio_date.setFont(QFont("Segoe UI", 8))
        self.radio_date.setStyleSheet("color: #e2e8f0; border: none;")

        self.type_group = QButtonGroup(self)
        self.type_group.addButton(self.radio_time)
        self.type_group.addButton(self.radio_date)
        self.radio_time.toggled.connect(self._on_type_toggled)

        type_row.addWidget(self.radio_time)
        type_row.addWidget(self.radio_date)
        type_row.addStretch()
        form_layout.addLayout(type_row)

        # Date & Time Pickers Row
        picker_row = QHBoxLayout()
        picker_row.setSpacing(8)

        # Date Picker
        lbl_d = QLabel("Date:")
        lbl_d.setStyleSheet("color: #94a3b8; border: none; font-size: 11px;")
        picker_row.addWidget(lbl_d)

        self.date_picker = QDateEdit()
        self.date_picker.setCalendarPopup(True)
        self.date_picker.setDate(QDate.currentDate())
        self.date_picker.setFixedHeight(28)
        self.date_picker.setStyleSheet("""
            QDateEdit {
                background: #00121a;
                color: #00d4ff;
                border: 1px solid rgba(0, 212, 255, 0.4);
                border-radius: 4px;
                padding: 2px 6px;
                font-weight: bold;
            }
        """)
        picker_row.addWidget(self.date_picker)

        # Time Picker
        self.lbl_t = QLabel("Time:")
        self.lbl_t.setStyleSheet("color: #94a3b8; border: none; font-size: 11px;")
        picker_row.addWidget(self.lbl_t)

        self.time_picker = QTimeEdit()
        self.time_picker.setTime(QTime.currentTime().addSecs(3600))
        self.time_picker.setFixedHeight(28)
        self.time_picker.setStyleSheet("""
            QTimeEdit {
                background: #00121a;
                color: #00d4ff;
                border: 1px solid rgba(0, 212, 255, 0.4);
                border-radius: 4px;
                padding: 2px 6px;
                font-weight: bold;
            }
        """)
        picker_row.addWidget(self.time_picker)

        picker_row.addStretch()

        # Action Buttons: Add / Save & Cancel
        self.add_btn = QPushButton("➕ Add Task")
        self.add_btn.setFixedHeight(28)
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 212, 255, 0.2);
                color: #00d4ff;
                border: 1px solid #00d4ff;
                border-radius: 4px;
                font-weight: bold;
                padding: 4px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(0, 212, 255, 0.4);
                color: #ffffff;
            }
        """)
        self.add_btn.clicked.connect(self._add_or_save_task)
        picker_row.addWidget(self.add_btn)

        self.cancel_edit_btn = QPushButton("✕ Cancel")
        self.cancel_edit_btn.setFixedHeight(28)
        self.cancel_edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_edit_btn.setStyleSheet("""
            QPushButton {
                background: rgba(148, 163, 184, 0.15);
                color: #cbd5e1;
                border: 1px solid rgba(148, 163, 184, 0.3);
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(148, 163, 184, 0.3);
                color: #ffffff;
            }
        """)
        self.cancel_edit_btn.clicked.connect(self._cancel_editing)
        self.cancel_edit_btn.hide()
        picker_row.addWidget(self.cancel_edit_btn)

        form_layout.addLayout(picker_row)

        # Info label describing reminder behavior
        self.info_lbl = QLabel("🔔 Time reminders alert 10m before, 5m before, and at exact time.")
        self.info_lbl.setFont(QFont("Segoe UI", 7))
        self.info_lbl.setStyleSheet("color: #38bdf8; border: none; padding-top: 2px;")
        form_layout.addWidget(self.info_lbl)

        main_layout.addWidget(self.form_card)

        # ── Section Header: Active Tasks ──
        active_hdr_row = QHBoxLayout()
        self.active_hdr_lbl = QLabel("PENDING TASKS (0)")
        self.active_hdr_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.active_hdr_lbl.setStyleSheet("color: #7dd3fc;")
        active_hdr_row.addWidget(self.active_hdr_lbl)

        active_hdr_row.addStretch()

        refresh_btn = QPushButton("⟳ Refresh")
        refresh_btn.setFixedHeight(22)
        refresh_btn.setStyleSheet("font-size: 10px; padding: 2px 6px;")
        refresh_btn.clicked.connect(self.refresh_tasks)
        active_hdr_row.addWidget(refresh_btn)

        main_layout.addLayout(active_hdr_row)

        # ── Scroll Area for Tasks ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        self.tasks_container = QWidget()
        self.tasks_layout = QVBoxLayout(self.tasks_container)
        self.tasks_layout.setContentsMargins(0, 0, 4, 0)
        self.tasks_layout.setSpacing(6)
        self.tasks_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(self.tasks_container)
        main_layout.addWidget(scroll, stretch=1)

        # ── Completed Tasks Header & Container ──
        comp_hdr_row = QHBoxLayout()
        self.comp_hdr_lbl = QLabel("COMPLETED (0)")
        self.comp_hdr_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.comp_hdr_lbl.setStyleSheet("color: #64748b;")
        comp_hdr_row.addWidget(self.comp_hdr_lbl)

        comp_hdr_row.addStretch()

        self.clear_comp_btn = QPushButton("Clear Completed")
        self.clear_comp_btn.setFixedHeight(22)
        self.clear_comp_btn.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.15);
                color: #fca5a5;
                border: 1px solid rgba(239, 68, 68, 0.3);
                font-size: 9px;
                padding: 1px 6px;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.35);
                color: #ffffff;
            }
        """)
        self.clear_comp_btn.clicked.connect(self._clear_completed)
        comp_hdr_row.addWidget(self.clear_comp_btn)

        main_layout.addLayout(comp_hdr_row)

        # Completed list container
        self.comp_container = QWidget()
        self.comp_layout = QVBoxLayout(self.comp_container)
        self.comp_layout.setContentsMargins(0, 0, 4, 0)
        self.comp_layout.setSpacing(4)
        main_layout.addWidget(self.comp_container)

    def _on_type_toggled(self):
        is_time = self.radio_time.isChecked()
        self.lbl_t.setVisible(is_time)
        self.time_picker.setVisible(is_time)
        if is_time:
            self.info_lbl.setText("🔔 Time reminders alert 10m before, 5m before, and at exact time.")
        else:
            self.info_lbl.setText("🔔 Date reminders alert proactively on laptop startup & check the day before.")

    def _start_editing(self, task: dict):
        """Populates form with task data to allow modifying it."""
        self._editing_task_id = task.get("id")
        self.form_title.setText(f"✏️ MODIFY TASK: '{task.get('title', '')[:30]}'")
        self.form_title.setStyleSheet("color: #fbbf24; font-weight: bold; border: none;")

        self.title_input.setText(task.get("title", ""))

        # Set date
        d_str = task.get("date", "")
        try:
            parts = [int(p) for p in d_str.split("-")]
            self.date_picker.setDate(QDate(parts[0], parts[1], parts[2]))
        except Exception:
            pass

        # Set type & time
        if task.get("type") == "time":
            self.radio_time.setChecked(True)
            t_str = task.get("time") or "12:00"
            try:
                th, tm = [int(x) for x in t_str.split(":")[:2]]
                self.time_picker.setTime(QTime(th, tm))
            except Exception:
                pass
        else:
            self.radio_date.setChecked(True)

        self.add_btn.setText("💾 Save Changes")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background: rgba(245, 158, 11, 0.25);
                color: #fbbf24;
                border: 1px solid #f59e0b;
                border-radius: 4px;
                font-weight: bold;
                padding: 4px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(245, 158, 11, 0.45);
                color: #ffffff;
            }
        """)
        self.cancel_edit_btn.show()
        self.title_input.setFocus()

    def _cancel_editing(self):
        """Resets the form back to Add mode."""
        self._editing_task_id = None
        self.form_title.setText("➕ ADD NEW TASK / REMINDER")
        self.form_title.setStyleSheet("color: #7dd3fc; border: none;")
        self.title_input.clear()
        self.add_btn.setText("➕ Add Task")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 212, 255, 0.2);
                color: #00d4ff;
                border: 1px solid #00d4ff;
                border-radius: 4px;
                font-weight: bold;
                padding: 4px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(0, 212, 255, 0.4);
                color: #ffffff;
            }
        """)
        self.cancel_edit_btn.hide()

    def _add_or_save_task(self):
        title = self.title_input.text().strip()
        if not title:
            self.title_input.setFocus()
            return

        date_val = self.date_picker.date().toString("yyyy-MM-dd")
        if self.radio_time.isChecked():
            time_val = self.time_picker.time().toString("HH:mm")
            task_type = "time"
        else:
            time_val = None
            task_type = "date"

        if self._editing_task_id:
            # Modify existing task
            todo_manager.update_task(
                task_id=self._editing_task_id,
                title=title,
                date_str=date_val,
                time_str=time_val,
                task_type=task_type,
            )
            self._cancel_editing()
        else:
            # Create new task
            todo_manager.add_task(title=title, date_str=date_val, time_str=time_val, task_type=task_type)
            self.title_input.clear()

        self.refresh_tasks()

    def _clear_completed(self):
        todo_manager.clear_completed_tasks()
        self.refresh_tasks()

    def refresh_tasks(self):
        """Reloads pending and completed tasks from JSON storage."""
        # Clear existing active widgets
        while self.tasks_layout.count():
            item = self.tasks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Clear existing completed widgets
        while self.comp_layout.count():
            item = self.comp_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        pending = todo_manager.get_pending_tasks()
        completed = todo_manager.get_completed_tasks()

        self.active_hdr_lbl.setText(f"PENDING TASKS ({len(pending)})")
        self.comp_hdr_lbl.setText(f"COMPLETED ({len(completed)})")
        self.task_count_changed.emit(len(pending))

        if not pending:
            empty_lbl = QLabel("No pending tasks. Add a task above or tell JARVIS via voice!")
            empty_lbl.setFont(QFont("Segoe UI", 9))
            empty_lbl.setStyleSheet("color: #64748b; font-style: italic; padding: 12px;")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tasks_layout.addWidget(empty_lbl)
        else:
            for t in pending:
                card = TaskItemWidget(t, parent=self.tasks_container)
                card.status_changed.connect(self.refresh_tasks)
                card.edit_requested.connect(self._start_editing)
                self.tasks_layout.addWidget(card)

        if not completed:
            self.comp_container.hide()
            self.clear_comp_btn.hide()
        else:
            self.comp_container.show()
            self.clear_comp_btn.show()
            for t in completed[:5]:
                card = TaskItemWidget(t, parent=self.comp_container)
                card.status_changed.connect(self.refresh_tasks)
                self.comp_layout.addWidget(card)

import asyncio
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QFrame,
    QCheckBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from auhip.skills.organizer import add_task, complete_task, TASKS_FILE, _init_data_files
import json
import os


class TaskManagerModal(QDialog):
    """
    Interactive Task Manager modal allowing users to view, add, and complete tasks
    connected directly to auhip's organizer storage (data/tasks.json).
    """

    tasks_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Task & Project Manager")
        self.setFixedSize(480, 520)
        self.setStyleSheet("""
            QDialog {
                background: #FFFFFF;
                border-radius: 16px;
            }
        """)
        self._build_ui()
        self.refresh_tasks()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("📋 Tasks & Priorities")
        title.setFont(QFont("Inter", 14, QFont.Weight.DemiBold))
        title.setStyleSheet("color: #0C0A09;")
        hdr.addWidget(title)
        hdr.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("border: none; color: #777169; font-size: 14px;")
        close_btn.clicked.connect(self.accept)
        hdr.addWidget(close_btn)
        layout.addLayout(hdr)

        # Add task row
        add_box = QHBoxLayout()
        add_box.setSpacing(8)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Add a new task...")
        self.input_field.setFont(QFont("Inter", 11))
        self.input_field.setStyleSheet("""
            QLineEdit {
                background: #FAFAFA;
                border: 1px solid #E7E5E4;
                border-radius: 8px;
                padding: 6px 10px;
                color: #0C0A09;
            }
            QLineEdit:focus {
                border: 1px solid #0C0A09;
                background: #FFFFFF;
            }
        """)
        self.input_field.returnPressed.connect(self._add_task)
        add_box.addWidget(self.input_field, 1)

        add_btn = QPushButton("+ Add")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setFont(QFont("Inter", 10, QFont.Weight.DemiBold))
        add_btn.setStyleSheet("""
            QPushButton {
                background: #292524;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 6px 14px;
            }
            QPushButton:hover { background: #0C0A09; }
        """)
        add_btn.clicked.connect(self._add_task)
        add_box.addWidget(add_btn)
        layout.addLayout(add_box)

        # Task list container
        self.task_list = QListWidget()
        self.task_list.setFont(QFont("Inter", 11))
        self.task_list.setStyleSheet("""
            QListWidget {
                background: #FAFAFA;
                border: 1px solid #E7E5E4;
                border-radius: 10px;
                padding: 6px;
            }
            QListWidget::item {
                background: #FFFFFF;
                border: 1px solid #E7E5E4;
                border-radius: 8px;
                margin-bottom: 4px;
                padding: 6px 8px;
            }
        """)
        layout.addWidget(self.task_list, 1)

        # Footer
        footer = QHBoxLayout()
        self.status_lbl = QLabel("")
        self.status_lbl.setFont(QFont("Inter", 10))
        self.status_lbl.setStyleSheet("color: #777169;")
        footer.addWidget(self.status_lbl)
        footer.addStretch()

        done_btn = QPushButton("Done")
        done_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        done_btn.setFont(QFont("Inter", 10, QFont.Weight.Medium))
        done_btn.setStyleSheet("""
            QPushButton {
                background: #F0EFED;
                color: #292524;
                border: 1px solid #E7E5E4;
                border-radius: 8px;
                padding: 6px 16px;
            }
            QPushButton:hover { background: #E7E5E4; }
        """)
        done_btn.clicked.connect(self.accept)
        footer.addWidget(done_btn)
        layout.addLayout(footer)

    def refresh_tasks(self):
        self.task_list.clear()
        _init_data_files()
        try:
            with open(TASKS_FILE, "r", encoding="utf-8") as f:
                tasks = json.load(f)

            active = [t for t in tasks if not t.get("completed")]
            self.status_lbl.setText(f"{len(active)} active tasks")

            for i, t in enumerate(tasks):
                item = QListWidgetItem()
                chk = QCheckBox(t.get("title", ""))
                chk.setChecked(t.get("completed", False))
                chk.setFont(QFont("Inter", 11))
                if t.get("completed"):
                    chk.setStyleSheet("color: #A8A29E; text-decoration: line-through;")
                else:
                    chk.setStyleSheet("color: #0C0A09;")

                chk.toggled.connect(lambda checked, idx=i: self._toggle_task(idx, checked))

                item.setSizeHint(chk.sizeHint())
                self.task_list.addItem(item)
                self.task_list.setItemWidget(item, chk)
        except Exception as e:
            self.status_lbl.setText(f"Error: {e}")

    def _add_task(self):
        txt = self.input_field.text().strip()
        if txt:
            asyncio.create_task(self._do_add(txt))
            self.input_field.clear()

    async def _do_add(self, title: str):
        await add_task(title)
        self.refresh_tasks()
        self.tasks_updated.emit()

    def _toggle_task(self, index: int, completed: bool):
        asyncio.create_task(self._do_toggle(index, completed))

    async def _do_toggle(self, index: int, completed: bool):
        _init_data_files()
        try:
            with open(TASKS_FILE, "r", encoding="utf-8") as f:
                tasks = json.load(f)
            if 0 <= index < len(tasks):
                tasks[index]["completed"] = completed
                with open(TASKS_FILE, "w", encoding="utf-8") as f:
                    json.dump(tasks, f, indent=4, ensure_ascii=False)
            self.refresh_tasks()
            self.tasks_updated.emit()
        except Exception:
            pass

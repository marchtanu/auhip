from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QProgressBar,
    QPushButton,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class CommandHistoryCard(QFrame):
    """Right Column Card 1: Chronological Command History."""

    view_history_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            CommandHistoryCard {
                background: #FFFFFF;
                border: 1px solid #E7E5E4;
                border-radius: 16px;
            }
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(6)

        # Header
        header = QHBoxLayout()
        title = QLabel("COMMAND HISTORY")
        title.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        title.setStyleSheet("color: #777169; letter-spacing: 0.6px; border: none; background: transparent;")
        header.addWidget(title)
        header.addStretch()

        icon = QLabel("↺")
        icon.setStyleSheet("color: #A8A29E; font-size: 11px; border: none; background: transparent;")
        header.addWidget(icon)
        layout.addLayout(header)

        layout.addSpacing(2)

        # Static reference list items (will also support dynamic appending)
        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(6)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)

        initial_history = [
            ("Analyze my AUHIP project", "02:14 PM"),
            ("Open camera", "02:10 PM"),
            ("Set timer for 25 minutes", "01:48 PM"),
            ("Search for MCP docs", "01:32 PM"),
            ("Read file: agent.py", "01:29 PM"),
        ]

        for cmd, tm in initial_history:
            self._add_row(cmd, tm)

        layout.addLayout(self.rows_layout)
        layout.addStretch(1)

        # Footer Link
        footer_btn = QPushButton("View all history →")
        footer_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        footer_btn.setFont(QFont("Inter", 10, QFont.Weight.Medium))
        footer_btn.setStyleSheet("""
            QPushButton {
                color: #777169;
                background: transparent;
                border: none;
                text-align: left;
                padding: 0;
            }
            QPushButton:hover {
                color: #0C0A09;
            }
        """)
        footer_btn.clicked.connect(self.view_history_clicked.emit)
        layout.addWidget(footer_btn)

    def _add_row(self, cmd_text: str, time_str: str):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        lbl = QLabel(cmd_text)
        lbl.setFont(QFont("Inter", 11))
        lbl.setStyleSheet("color: #4E4E4E; border: none; background: transparent;")
        row.addWidget(lbl, 1)

        t_lbl = QLabel(time_str)
        t_lbl.setFont(QFont("Inter", 10))
        t_lbl.setStyleSheet("color: #A8A29E; border: none; background: transparent;")
        row.addWidget(t_lbl)

        self.rows_layout.addWidget(self._wrap(row))

    def _wrap(self, layout):
        w = QWidget()
        w.setStyleSheet("background: transparent; border: none;")
        w.setLayout(layout)
        return w

    def add_command(self, cmd_text: str, time_str: str = ""):
        from datetime import datetime
        t = time_str if time_str else datetime.now().strftime("%I:%M %p")
        self._add_row(cmd_text, t)


class ActiveTasksCard(QFrame):
    """Right Column Card 2: Active Agents and Focus Sessions."""

    view_tasks_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            ActiveTasksCard {
                background: #FFFFFF;
                border: 1px solid #E7E5E4;
                border-radius: 16px;
            }
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(8)

        # Header
        header = QHBoxLayout()
        title = QLabel("ACTIVE TASKS")
        title.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        title.setStyleSheet("color: #777169; letter-spacing: 0.6px; border: none; background: transparent;")
        header.addWidget(title)
        header.addStretch()

        icon = QLabel("↺")
        icon.setStyleSheet("color: #A8A29E; font-size: 11px; border: none; background: transparent;")
        header.addWidget(icon)
        layout.addLayout(header)

        layout.addSpacing(2)

        # Task 1: Code Agent (progress bar)
        t1 = QVBoxLayout()
        t1.setSpacing(3)
        t1_hdr = QHBoxLayout()
        t1_icon = QLabel("✦")
        t1_icon.setStyleSheet("color: #7E22CE; font-size: 12px; background: #F5F3FF; border-radius: 6px; padding: 2px 5px;")
        t1_hdr.addWidget(t1_icon)
        t1_title = QLabel("Code Agent")
        t1_title.setFont(QFont("Inter", 11, QFont.Weight.DemiBold))
        t1_title.setStyleSheet("color: #0C0A09; border: none; background: transparent;")
        t1_hdr.addWidget(t1_title, 1)
        t1_val = QLabel("68%")
        t1_val.setFont(QFont("Inter", 10, QFont.Weight.DemiBold))
        t1_val.setStyleSheet("color: #7E22CE; border: none; background: transparent;")
        t1_hdr.addWidget(t1_val)
        t1.addLayout(t1_hdr)

        t1_sub = QLabel("Refactoring event system")
        t1_sub.setFont(QFont("Inter", 10))
        t1_sub.setStyleSheet("color: #777169; border: none; background: transparent;")
        t1.addWidget(t1_sub)

        t1_bar = QProgressBar()
        t1_bar.setRange(0, 100)
        t1_bar.setValue(68)
        t1_bar.setTextVisible(False)
        t1_bar.setFixedHeight(4)
        t1_bar.setStyleSheet("""
            QProgressBar { background: #F0EFED; border: none; border-radius: 2px; }
            QProgressBar::chunk { background: #7E22CE; border-radius: 2px; }
        """)
        t1.addWidget(t1_bar)
        layout.addWidget(self._wrap(t1))

        # Task 2: Research Agent (completed badge)
        t2 = QVBoxLayout()
        t2.setSpacing(3)
        t2_hdr = QHBoxLayout()
        t2_icon = QLabel("⬡")
        t2_icon.setStyleSheet("color: #059669; font-size: 12px; background: #ECFDF5; border-radius: 6px; padding: 2px 5px;")
        t2_hdr.addWidget(t2_icon)
        t2_title = QLabel("Research Agent")
        t2_title.setFont(QFont("Inter", 11, QFont.Weight.DemiBold))
        t2_title.setStyleSheet("color: #0C0A09; border: none; background: transparent;")
        t2_hdr.addWidget(t2_title, 1)

        t2_badge = QLabel("Completed")
        t2_badge.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        t2_badge.setStyleSheet("color: #059669; background: #ECFDF5; border-radius: 6px; padding: 1px 6px;")
        t2_hdr.addWidget(t2_badge)
        t2.addLayout(t2_hdr)

        t2_sub = QLabel("Analyzing LLM architectures")
        t2_sub.setFont(QFont("Inter", 10))
        t2_sub.setStyleSheet("color: #777169; border: none; background: transparent;")
        t2.addWidget(t2_sub)
        layout.addWidget(self._wrap(t2))

        # Task 3: Focus Session (running badge)
        t3 = QVBoxLayout()
        t3.setSpacing(3)
        t3_hdr = QHBoxLayout()
        t3_icon = QLabel("📄")
        t3_icon.setStyleSheet("font-size: 11px; background: #FEF3C7; border-radius: 6px; padding: 2px 5px;")
        t3_hdr.addWidget(t3_icon)
        t3_title = QLabel("Focus Session")
        t3_title.setFont(QFont("Inter", 11, QFont.Weight.DemiBold))
        t3_title.setStyleSheet("color: #0C0A09; border: none; background: transparent;")
        t3_hdr.addWidget(t3_title, 1)

        t3_badge = QLabel("Running")
        t3_badge.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        t3_badge.setStyleSheet("color: #2563EB; background: #EFF6FF; border-radius: 6px; padding: 1px 6px;")
        t3_hdr.addWidget(t3_badge)
        t3.addLayout(t3_hdr)

        t3_sub = QLabel("25:00 remaining")
        t3_sub.setFont(QFont("Inter", 10))
        t3_sub.setStyleSheet("color: #777169; border: none; background: transparent;")
        t3.addWidget(t3_sub)
        layout.addWidget(self._wrap(t3))

        layout.addStretch(1)

        # Footer Link
        footer_btn = QPushButton("View all tasks →")
        footer_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        footer_btn.setFont(QFont("Inter", 10, QFont.Weight.Medium))
        footer_btn.setStyleSheet("""
            QPushButton {
                color: #777169;
                background: transparent;
                border: none;
                text-align: left;
                padding: 0;
            }
            QPushButton:hover {
                color: #0C0A09;
            }
        """)
        footer_btn.clicked.connect(self.view_tasks_clicked.emit)
        layout.addWidget(footer_btn)

    def _wrap(self, layout):
        w = QWidget()
        w.setStyleSheet("background: transparent; border: none;")
        w.setLayout(layout)
        return w

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


class PrioritiesCard(QFrame):
    """Bento Card 1: Prioritized Task List with status badge and quick footer."""

    view_tasks_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            PrioritiesCard {
                background: #FFFFFF;
                border: 1px solid #E7E5E4;
                border-radius: 16px;
            }
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        # Header Row: PRIORITIES + Count badge
        header = QHBoxLayout()
        title = QLabel("PRIORITIES")
        title.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        title.setStyleSheet("color: #777169; letter-spacing: 0.6px; border: none; background: transparent;")
        header.addWidget(title)

        badge = QLabel("3")
        badge.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        badge.setStyleSheet("""
            background: #F0EFED;
            color: #292524;
            border-radius: 6px;
            padding: 1px 6px;
            border: none;
        """)
        header.addWidget(badge)
        header.addStretch()
        layout.addLayout(header)

        layout.addSpacing(2)

        # Task Items with colored status bullets
        self.items = [
            ("🟣", "Finish AUHIP architecture", "#0C0A09"),
            ("🟡", "Meeting tomorrow — 10:00", "#4E4E4E"),
            ("⚪", "Review StageLink deployment", "#777169"),
        ]

        for dot, text, color in self.items:
            row = QHBoxLayout()
            row.setSpacing(6)
            row.setContentsMargins(0, 0, 0, 0)

            dot_lbl = QLabel(dot)
            dot_lbl.setStyleSheet("font-size: 8px; border: none; background: transparent;")
            row.addWidget(dot_lbl)

            txt_lbl = QLabel(text)
            txt_lbl.setFont(QFont("Inter", 11, QFont.Weight.Medium))
            txt_lbl.setStyleSheet(f"color: {color}; border: none; background: transparent;")
            row.addWidget(txt_lbl, 1)

            layout.addLayout(row)

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


class InProgressCard(QFrame):
    """Bento Card 2: Current active project, agent count, and progress bar."""

    open_workspace_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            InProgressCard {
                background: #FFFFFF;
                border: 1px solid #E7E5E4;
                border-radius: 16px;
            }
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        # Header: ● IN PROGRESS
        header = QHBoxLayout()
        header.setSpacing(6)
        dot = QLabel("●")
        dot.setStyleSheet("color: #16A34A; font-size: 8px; border: none; background: transparent;")
        header.addWidget(dot)

        title = QLabel("IN PROGRESS")
        title.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        title.setStyleSheet("color: #777169; letter-spacing: 0.6px; border: none; background: transparent;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # Project Name + Subtitle
        proj_title = QLabel("AUHIP Project")
        proj_title.setFont(QFont("Inter", 14, QFont.Weight.DemiBold))
        proj_title.setStyleSheet("color: #0C0A09; border: none; background: transparent;")
        layout.addWidget(proj_title)

        agent_sub = QLabel("2 agents running")
        agent_sub.setFont(QFont("Inter", 10))
        agent_sub.setStyleSheet("color: #777169; border: none; background: transparent;")
        layout.addWidget(agent_sub)

        layout.addSpacing(4)

        # Progress row
        p_row = QHBoxLayout()
        p_lbl = QLabel("Refactoring event architecture")
        p_lbl.setFont(QFont("Inter", 10))
        p_lbl.setStyleSheet("color: #4E4E4E; border: none; background: transparent;")
        p_row.addWidget(p_lbl)

        p_val = QLabel("68%")
        p_val.setFont(QFont("Inter", 10, QFont.Weight.DemiBold))
        p_val.setStyleSheet("color: #0C0A09; border: none; background: transparent;")
        p_row.addWidget(p_val)
        layout.addLayout(p_row)

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(68)
        bar.setTextVisible(False)
        bar.setFixedHeight(5)
        bar.setStyleSheet("""
            QProgressBar {
                background-color: #F0EFED;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7E22CE, stop:1 #2563EB);
                border-radius: 2px;
            }
        """)
        layout.addWidget(bar)

        layout.addStretch(1)

        # Footer Link
        footer_btn = QPushButton("Open workspace →")
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
        footer_btn.clicked.connect(self.open_workspace_clicked.emit)
        layout.addWidget(footer_btn)


class SystemOverviewCard(QFrame):
    """Bento Card 3: System Overview, LLM model pill, memory & CPU summary."""

    system_status_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            SystemOverviewCard {
                background: #FFFFFF;
                border: 1px solid #E7E5E4;
                border-radius: 16px;
            }
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        # Header: ● SYSTEM
        header = QHBoxLayout()
        header.setSpacing(6)
        dot = QLabel("●")
        dot.setStyleSheet("color: #16A34A; font-size: 8px; border: none; background: transparent;")
        header.addWidget(dot)

        title = QLabel("SYSTEM")
        title.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        title.setStyleSheet("color: #777169; letter-spacing: 0.6px; border: none; background: transparent;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # State + Model Pill
        model_row = QHBoxLayout()
        model_row.setSpacing(8)

        state_lbl = QLabel("● Ready")
        state_lbl.setFont(QFont("Inter", 13, QFont.Weight.DemiBold))
        state_lbl.setStyleSheet("color: #16A34A; border: none; background: transparent;")
        model_row.addWidget(state_lbl)
        model_row.addStretch()

        model_tag = QLabel("Qwen 7B")
        model_tag.setFont(QFont("Inter", 9, QFont.Weight.DemiBold))
        model_tag.setStyleSheet("""
            background: #F0EFED;
            color: #292524;
            border: 1px solid #E7E5E4;
            border-radius: 6px;
            padding: 2px 7px;
        """)
        model_row.addWidget(model_tag)
        layout.addLayout(model_row)

        brain_sub = QLabel("Local Brain")
        brain_sub.setFont(QFont("Inter", 10))
        brain_sub.setStyleSheet("color: #777169; border: none; background: transparent;")
        layout.addWidget(brain_sub)

        layout.addSpacing(2)

        # Stats summary row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)

        for name, val in [("Mem", "42%"), ("CPU", "8%"), ("RAM", "42%")]:
            item = QLabel(f"{name}: <b style='color:#0C0A09;'>{val}</b>")
            item.setFont(QFont("Inter", 10))
            item.setStyleSheet("color: #777169; border: none; background: transparent;")
            stats_row.addWidget(item)

        stats_row.addStretch()
        layout.addLayout(stats_row)

        layout.addStretch(1)

        # Footer Link
        footer_btn = QPushButton("System status →")
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
        footer_btn.clicked.connect(self.system_status_clicked.emit)
        layout.addWidget(footer_btn)

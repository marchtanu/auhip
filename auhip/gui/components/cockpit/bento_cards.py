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


from auhip.core.second_brain import second_brain


class PrioritiesCard(QFrame):
    """Bento Card 1: Live Second Brain Priorities (Acting Queues, Coursework Deadlines, Overdue Alerts)."""

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

        # Query Second Brain live data
        self.items = []
        try:
            acting = second_brain.get_next_acting_queue()
            if acting:
                call_t = acting.get("callTime", "TBD")
                date_t = acting.get("date", "")
                title_t = acting.get("title", "Shoot")
                self.items.append(("🎬", f"{title_t}: Call {call_t} ({date_t})", "#0C0A09"))
        except Exception:
            pass

        try:
            acad = second_brain.get_academic_status()
            next_d = acad.get("next_deadline")
            if next_d:
                c_code = next_d.get("courseCode", "ICT")
                d_name = next_d.get("name", "Assignment")[:24]
                self.items.append(("🎓", f"[{c_code}] {d_name}", "#4E4E4E"))
            overdue_cnt = acad.get("overdue_count", 0)
            if overdue_cnt > 0:
                self.items.append(("⚠️", f"{overdue_cnt} Overdue Assignments", "#DC2626"))
        except Exception:
            pass

        if not self.items:
            self.items = [
                ("🟣", "Second Brain Online", "#0C0A09"),
                ("⚪", "Ready for commands", "#777169"),
            ]

        # Header Row: PRIORITIES + Count badge
        header = QHBoxLayout()
        title = QLabel("PRIORITIES")
        title.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        title.setStyleSheet("color: #777169; letter-spacing: 0.6px; border: none; background: transparent;")
        header.addWidget(title)

        badge = QLabel(str(len(self.items)))
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

        for dot, text, color in self.items:
            row = QHBoxLayout()
            row.setSpacing(6)
            row.setContentsMargins(0, 0, 0, 0)

            dot_lbl = QLabel(dot)
            dot_lbl.setStyleSheet("font-size: 10px; border: none; background: transparent;")
            row.addWidget(dot_lbl)

            txt_lbl = QLabel(text)
            txt_lbl.setFont(QFont("Inter", 11, QFont.Weight.Medium))
            txt_lbl.setStyleSheet(f"color: {color}; border: none; background: transparent;")
            row.addWidget(txt_lbl, 1)

            layout.addLayout(row)

        layout.addStretch(1)

        # Footer Link
        footer_btn = QPushButton("Sync Second Brain →")
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
    """Bento Card 2: Current active project, startup sprint progress, and deliverables."""

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

        # Pull live startup telemetry from Second Brain
        proj_name = "StageLink Marketplace"
        proj_sub = "Co-Founder & Full-Stack Engineer"
        sprint_lbl = "Sprint 5: Omise Escrow & Auth"
        progress_val = 70

        try:
            startups = second_brain.get_startup_status()
            if startups:
                s0 = startups[0]
                proj_name = s0.get("name", proj_name)
                metrics = s0.get("metrics", {})
                talents = metrics.get("onboardedTalents", 52)
                orgs = metrics.get("betaOrganizers", 14)
                proj_sub = f"{talents} Talents · {orgs} Organizers · Launch {s0.get('targetLaunch', 'Oct 15')}"
                sprint_lbl = s0.get("currentSprint", sprint_lbl)[:34]
                progress_val = s0.get("progressPercent", progress_val)
        except Exception:
            pass

        # Project Name + Subtitle
        proj_title = QLabel(f"🚀 {proj_name}")
        proj_title.setFont(QFont("Inter", 13, QFont.Weight.DemiBold))
        proj_title.setStyleSheet("color: #0C0A09; border: none; background: transparent;")
        layout.addWidget(proj_title)

        agent_sub = QLabel(proj_sub)
        agent_sub.setFont(QFont("Inter", 10))
        agent_sub.setStyleSheet("color: #777169; border: none; background: transparent;")
        layout.addWidget(agent_sub)

        layout.addSpacing(4)

        # Progress row
        p_row = QHBoxLayout()
        p_lbl = QLabel(sprint_lbl)
        p_lbl.setFont(QFont("Inter", 10))
        p_lbl.setStyleSheet("color: #4E4E4E; border: none; background: transparent;")
        p_row.addWidget(p_lbl)

        p_val = QLabel(f"{progress_val}%")
        p_val.setFont(QFont("Inter", 10, QFont.Weight.DemiBold))
        p_val.setStyleSheet("color: #0C0A09; border: none; background: transparent;")
        p_row.addWidget(p_val)
        layout.addLayout(p_row)

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(progress_val)
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
        footer_btn = QPushButton("Open Second Brain Explorer →")
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

        model_name = "qwen2.5-coder:3b"
        try:
            from auhip.core.llm.config import llm_config
            model_name = llm_config.LOCAL_MODEL_NAME
        except Exception:
            pass
        model_tag = QLabel(model_name)
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

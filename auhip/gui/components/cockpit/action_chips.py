from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class ActionChip(QFrame):
    """Single clickable pill/chip card with category icon, title, and prompt subtitle."""

    clicked = pyqtSignal(str)

    def __init__(self, icon: str, title: str, subtitle: str, full_prompt: str, icon_color: str, parent=None):
        super().__init__(parent)
        self._full_prompt = full_prompt
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            ActionChip {{
                background: #FFFFFF;
                border: 1px solid #E7E5E4;
                border-radius: 12px;
            }}
            ActionChip:hover {{
                background: #FAFAFA;
                border: 1px solid #D6D3D1;
            }}
        """)
        self.setFixedHeight(50)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 14, 6)
        layout.setSpacing(10)

        # Icon badge
        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Segoe UI Symbol", 13))
        icon_lbl.setStyleSheet(f"""
            color: {icon_color};
            background: #F0EFED;
            border-radius: 8px;
            padding: 2px 6px;
            border: none;
        """)
        layout.addWidget(icon_lbl)

        # Text column
        txt_col = QVBoxLayout()
        txt_col.setContentsMargins(0, 0, 0, 0)
        txt_col.setSpacing(1)

        t_lbl = QLabel(title)
        t_lbl.setFont(QFont("Inter", 11, QFont.Weight.DemiBold))
        t_lbl.setStyleSheet("color: #0C0A09; border: none; background: transparent;")
        txt_col.addWidget(t_lbl)

        s_lbl = QLabel(subtitle)
        s_lbl.setFont(QFont("Inter", 10))
        s_lbl.setStyleSheet("color: #777169; border: none; background: transparent;")
        txt_col.addWidget(s_lbl)

        layout.addLayout(txt_col)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._full_prompt)
            event.accept()
        else:
            super().mousePressEvent(event)


class ContinueConversationBar(QWidget):
    """Horizontal shelf of Quick Action Chips per reference image."""

    prompt_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(6)

        # Section Header
        sec_title = QLabel("CONTINUE THE CONVERSATION")
        sec_title.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        sec_title.setStyleSheet("color: #777169; letter-spacing: 0.6px; border: none; background: transparent;")
        layout.addWidget(sec_title)

        # Chips row
        chips_row = QHBoxLayout()
        chips_row.setContentsMargins(0, 0, 0, 0)
        chips_row.setSpacing(8)

        chips_data = [
            ("⬡", "Analyze", "my AUHIP project", "Analyze my AUHIP project and find performance bottlenecks", "#2563EB"),
            ("⬡", "Explain", "event architecture", "Explain how the AUHIP event architecture works", "#059669"),
            ("⬡", "Improve", "performance", "Give suggestions to improve performance and reduce latency", "#D97706"),
            ("⬡", "Find", "unused files", "Scan the workspace and list unused Python files", "#DC2626"),
        ]

        for icon, title, sub, prompt, color in chips_data:
            chip = ActionChip(icon, title, sub, prompt, color)
            chip.clicked.connect(self.prompt_selected.emit)
            chips_row.addWidget(chip, 1)

        # Right chevron button
        arrow_btn = QPushButton("›")
        arrow_btn.setFixedSize(28, 50)
        arrow_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        arrow_btn.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        arrow_btn.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                color: #777169;
                border: 1px solid #E7E5E4;
                border-radius: 12px;
            }
            QPushButton:hover {
                background: #F0EFED;
                color: #0C0A09;
            }
        """)
        chips_row.addWidget(arrow_btn)

        layout.addLayout(chips_row)

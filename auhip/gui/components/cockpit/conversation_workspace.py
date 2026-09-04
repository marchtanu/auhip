from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class StepItem(QWidget):
    """Single step in the assistant's execution checklist."""

    def __init__(self, icon: str, text: str, time_str: str, icon_color: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)

        i_lbl = QLabel(icon)
        i_lbl.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        i_lbl.setStyleSheet(f"color: {icon_color}; border: none; background: transparent;")
        layout.addWidget(i_lbl)

        t_lbl = QLabel(text)
        t_lbl.setFont(QFont("Inter", 11))
        t_lbl.setStyleSheet("color: #4E4E4E; border: none; background: transparent;")
        layout.addWidget(t_lbl, 1)

        tm_lbl = QLabel(time_str)
        tm_lbl.setFont(QFont("Inter", 10))
        tm_lbl.setStyleSheet("color: #A8A29E; border: none; background: transparent;")
        layout.addWidget(tm_lbl)


class ConversationWorkspace(QFrame):
    """
    Main Center Conversation Card replicating the reference image:
    - User message bubble
    - Assistant response with step checklist card & file pill
    - Floating prompt bar with mic & send button
    """

    prompt_submitted = pyqtSignal(str)
    open_file_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            ConversationWorkspace {
                background: #FFFFFF;
                border: 1px solid #E7E5E4;
                border-radius: 16px;
            }
        """)
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(10)

        # Header
        header = QLabel("Chat with AUHIP")
        header.setFont(QFont("Inter", 12, QFont.Weight.DemiBold))
        header.setStyleSheet("color: #0C0A09; border: none; background: transparent;")
        main_layout.addWidget(header)

        # Scrollable Conversation View
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_layout.setSpacing(14)

        # Seed initial rich message thread matching reference visual
        self._populate_reference_conversation()

        self.chat_layout.addStretch(1)
        self.scroll_area.setWidget(self.chat_container)
        main_layout.addWidget(self.scroll_area, 1)

        # ── Floating Prompt Input Bar ─────────────────────────────────────────
        input_container = QFrame()
        input_container.setFixedHeight(46)
        input_container.setStyleSheet("""
            QFrame {
                background: #FAFAFA;
                border: 1px solid #E7E5E4;
                border-radius: 23px;
                padding: 2px 8px;
            }
            QFrame:focus-within {
                border: 1px solid #0C0A09;
                background: #FFFFFF;
            }
        """)
        in_layout = QHBoxLayout(input_container)
        in_layout.setContentsMargins(12, 0, 8, 0)
        in_layout.setSpacing(8)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask AUHIP anything...")
        self.input_field.setFont(QFont("Inter", 12))
        self.input_field.setStyleSheet("border: none; background: transparent; color: #0C0A09; padding: 0;")
        self.input_field.returnPressed.connect(self._handle_send)
        in_layout.addWidget(self.input_field, 1)

        # Mic icon button
        self.mic_btn = QPushButton("🎙️")
        self.mic_btn.setFixedSize(30, 30)
        self.mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mic_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 15px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #F0EFED;
            }
        """)
        in_layout.addWidget(self.mic_btn)

        # Send action button (ink pill)
        self.send_btn = QPushButton("⌘ ↵")
        self.send_btn.setFixedHeight(30)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setFont(QFont("Inter", 11, QFont.Weight.DemiBold))
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: #292524;
                color: #FFFFFF;
                border: none;
                border-radius: 15px;
                padding: 0 12px;
            }
            QPushButton:hover {
                background: #0C0A09;
            }
        """)
        self.send_btn.clicked.connect(self._handle_send)
        in_layout.addWidget(self.send_btn)

        main_layout.addWidget(input_container)

    def _populate_reference_conversation(self):
        """Builds the reference conversation showing the user query, checklist, and file pill."""
        # 1. User Bubble
        u_box = QHBoxLayout()
        u_box.addStretch(1)

        u_bubble = QFrame()
        u_bubble.setStyleSheet("""
            QFrame {
                background: #F4F1FD;
                border: 1px solid #E4DCFB;
                border-radius: 14px;
            }
        """)
        ub_layout = QVBoxLayout(u_bubble)
        ub_layout.setContentsMargins(14, 10, 14, 10)
        ub_layout.setSpacing(4)

        u_hdr = QHBoxLayout()
        u_tag = QLabel("You")
        u_tag.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        u_tag.setStyleSheet("color: #7E22CE; border: none; background: transparent;")
        u_hdr.addWidget(u_tag)
        u_hdr.addStretch()

        u_time = QLabel("02:14 PM")
        u_time.setFont(QFont("Inter", 9))
        u_time.setStyleSheet("color: #A8A29E; border: none; background: transparent;")
        u_hdr.addWidget(u_time)
        ub_layout.addLayout(u_hdr)

        u_msg = QLabel("Analyze my AUHIP project and find performance bottlenecks.")
        u_msg.setFont(QFont("Inter", 11, QFont.Weight.Medium))
        u_msg.setStyleSheet("color: #0C0A09; border: none; background: transparent;")
        ub_layout.addWidget(u_msg)

        u_box.addWidget(u_bubble)
        self.chat_layout.addLayout(u_box)

        # 2. Assistant Response Block
        a_card = QFrame()
        a_card.setStyleSheet("background: transparent; border: none;")
        a_layout = QVBoxLayout(a_card)
        a_layout.setContentsMargins(0, 0, 0, 0)
        a_layout.setSpacing(8)

        # Assistant Header
        a_hdr = QHBoxLayout()
        a_tag = QLabel("✦ AUHIP")
        a_tag.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        a_tag.setStyleSheet("color: #2563EB; border: none; background: transparent;")
        a_hdr.addWidget(a_tag)
        a_hdr.addStretch()

        a_time = QLabel("02:14 PM")
        a_time.setFont(QFont("Inter", 9))
        a_time.setStyleSheet("color: #A8A29E; border: none; background: transparent;")
        a_hdr.addWidget(a_time)
        a_layout.addLayout(a_hdr)

        lead_msg = QLabel("I'll inspect the architecture and execution flow.")
        lead_msg.setFont(QFont("Inter", 11))
        lead_msg.setStyleSheet("color: #4E4E4E; border: none; background: transparent;")
        a_layout.addWidget(lead_msg)

        # Execution Checklist Card
        chk_card = QFrame()
        chk_card.setStyleSheet("""
            QFrame {
                background: #FAFAFA;
                border: 1px solid #E7E5E4;
                border-radius: 12px;
                padding: 6px 10px;
            }
        """)
        chk_layout = QVBoxLayout(chk_card)
        chk_layout.setContentsMargins(10, 8, 10, 8)
        chk_layout.setSpacing(4)

        chk_layout.addWidget(StepItem("✓", "Read architecture.md", "02:14 PM", "#16A34A"))
        chk_layout.addWidget(StepItem("✓", "Scan workspace", "02:14 PM", "#16A34A"))
        chk_layout.addWidget(StepItem("⚙", "Analyze imports and dependencies", "02:14 PM", "#2563EB"))
        chk_layout.addWidget(StepItem("○", "Run performance analysis", "....", "#A8A29E"))
        a_layout.addWidget(chk_card)

        # Detailed Diagnosis
        body_text = QLabel(
            "<b>Primary bottleneck identified:</b><br>"
            "Camera pipeline remains unnecessarily active during Standby Mode, consuming ~28% CPU. "
            "I recommend lazy-loading the VisionWorker only when entering Vision or Control Mode."
        )
        body_text.setFont(QFont("Inter", 11))
        body_text.setWordWrap(True)
        body_text.setStyleSheet("color: #0C0A09; line-height: 1.4; border: none; background: transparent;")
        a_layout.addWidget(body_text)

        # File Action Pill
        file_pill = QFrame()
        file_pill.setStyleSheet("""
            QFrame {
                background: #F0EFED;
                border: 1px solid #E7E5E4;
                border-radius: 8px;
            }
        """)
        f_layout = QHBoxLayout(file_pill)
        f_layout.setContentsMargins(10, 6, 10, 6)
        f_layout.setSpacing(8)

        f_icon = QLabel("📄")
        f_icon.setStyleSheet("border: none; background: transparent;")
        f_layout.addWidget(f_icon)

        f_name = QLabel("vision/vision_worker.py")
        f_name.setFont(QFont("JetBrains Mono", 10, QFont.Weight.Medium))
        f_name.setStyleSheet("color: #0C0A09; border: none; background: transparent;")
        f_layout.addWidget(f_name, 1)

        open_btn = QPushButton("Open in Workspace")
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.setFont(QFont("Inter", 10, QFont.Weight.DemiBold))
        open_btn.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                color: #292524;
                border: 1px solid #D6D3D1;
                border-radius: 6px;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background: #0C0A09;
                color: #FFFFFF;
                border-color: #0C0A09;
            }
        """)
        open_btn.clicked.connect(lambda: self.open_file_requested.emit("auhip/vision/worker.py"))
        f_layout.addWidget(open_btn)

        a_layout.addWidget(file_pill)
        self.chat_layout.addWidget(a_card)

    def add_user_message(self, text: str):
        u_box = QHBoxLayout()
        u_box.addStretch(1)

        bubble = QFrame()
        bubble.setStyleSheet("""
            QFrame {
                background: #F4F1FD;
                border: 1px solid #E4DCFB;
                border-radius: 14px;
            }
        """)
        b_layout = QVBoxLayout(bubble)
        b_layout.setContentsMargins(14, 10, 14, 10)
        b_layout.setSpacing(4)

        t_lbl = QLabel(datetime.now().strftime("%I:%M %p"))
        t_lbl.setFont(QFont("Inter", 9))
        t_lbl.setStyleSheet("color: #A8A29E; border: none; background: transparent;")
        b_layout.addWidget(t_lbl, alignment=Qt.AlignmentFlag.AlignRight)

        msg = QLabel(text)
        msg.setFont(QFont("Inter", 11, QFont.Weight.Medium))
        msg.setStyleSheet("color: #0C0A09; border: none; background: transparent;")
        msg.setWordWrap(True)
        b_layout.addWidget(msg)

        u_box.addWidget(bubble)
        self.chat_layout.insertLayout(self.chat_layout.count() - 1, u_box)
        self._scroll_to_bottom()

    def add_assistant_message(self, text: str):
        card = QFrame()
        card.setStyleSheet("background: transparent; border: none;")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        hdr = QHBoxLayout()
        tag = QLabel("✦ AUHIP")
        tag.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        tag.setStyleSheet("color: #2563EB; border: none; background: transparent;")
        hdr.addWidget(tag)
        hdr.addStretch()

        time_lbl = QLabel(datetime.now().strftime("%I:%M %p"))
        time_lbl.setFont(QFont("Inter", 9))
        time_lbl.setStyleSheet("color: #A8A29E; border: none; background: transparent;")
        hdr.addWidget(time_lbl)
        layout.addLayout(hdr)

        body = QLabel(text)
        body.setFont(QFont("Inter", 11))
        body.setWordWrap(True)
        body.setStyleSheet("color: #0C0A09; border: none; background: transparent; line-height: 1.4;")
        layout.addWidget(body)

        self.chat_layout.insertWidget(self.chat_layout.count() - 1, card)
        self._scroll_to_bottom()

    def set_input_text(self, text: str):
        self.input_field.setText(text)
        self.input_field.setFocus()

    def _handle_send(self):
        txt = self.input_field.text().strip()
        if txt:
            self.add_user_message(txt)
            self.input_field.clear()
            self.prompt_submitted.emit(txt)

    def _scroll_to_bottom(self):
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )

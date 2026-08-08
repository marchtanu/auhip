from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from PyQt6.QtGui import QTextCursor
from auhip.gui.theme import COLORS


class TranscriptPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setPlaceholderText("Recognized speech appears here…")
        self._text.setStyleSheet(f"""
            QTextEdit {{
                background: transparent;
                border: none;
                color: {COLORS['text_body']};
                font-size: 13px;
                line-height: 1.6;
                padding: 0;
            }}
        """)
        layout.addWidget(self._text)

    def add_text(self, text: str, speaker: str = "USER"):
        if speaker == "USER":
            badge_bg = COLORS["accent_dim"] if "accent_dim" in COLORS else COLORS["border"]
            badge_color = COLORS["accent"]
            text_color = COLORS["text"]
            speaker_name = "YOU"
        else:
            badge_bg = COLORS["panel_soft"]
            badge_color = COLORS["text_muted"]
            text_color = COLORS["text_body"]
            speaker_name = "AUHIP"

        self._text.append(
            f'<div style="margin-bottom: 12px;">'
            f'<span style="color: {badge_color}; background-color: {badge_bg}; '
            f'font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 4px; '
            f'letter-spacing: 0.5px;">{speaker_name}</span>'
            f'<div style="margin-top: 6px; color: {text_color}; font-size: 13px; line-height: 1.5;">{text}</div>'
            f'</div>'
        )
        self._text.moveCursor(QTextCursor.MoveOperation.End)

    def refresh_theme(self):
        """Re-apply styles after a theme switch."""
        self._text.setStyleSheet(f"""
            QTextEdit {{
                background: transparent;
                border: none;
                color: {COLORS['text_body']};
                font-size: 13px;
                line-height: 1.6;
                padding: 0;
            }}
        """)



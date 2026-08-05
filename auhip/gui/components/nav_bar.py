from datetime import datetime
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import QTimer
from auhip.gui.theme import COLORS
from .last_command_widget import LastCommandWidget


class NavBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self._apply_style()
        self._build_ui()

    def _apply_style(self):
        self.setStyleSheet(
            f"background: {COLORS['surface']}; "
            f"border-bottom: 1px solid {COLORS['border']}; "
            "border-radius: 0;"
        )

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(12)

        # Wordmark icon
        self._mark = QLabel("✦")
        self._mark.setStyleSheet(f"color: {COLORS['accent']}; font-size: 16px; border: none;")
        layout.addWidget(self._mark)

        # App title
        self._title = QLabel("auhip")
        self._title.setStyleSheet(
            f"color: {COLORS['text']}; font-size: 13px; font-weight: 600;"
            "letter-spacing: -0.1px; border: none;"
        )
        layout.addWidget(self._title)
        layout.addStretch()

        # Last activated command indicator
        self._last_cmd_widget = LastCommandWidget()
        layout.addWidget(self._last_cmd_widget)

        # Separator
        self._sep = QLabel("│")
        self._sep.setStyleSheet(
            f"color: {COLORS['border_dark']}; font-size: 14px; border: none; margin: 0 6px;"
        )
        layout.addWidget(self._sep)

        # Status badge
        self._status_badge = QLabel("● Standby")
        self._status_badge.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px; border: none;"
        )
        layout.addWidget(self._status_badge)

        # Dark mode toggle button
        self._theme_btn = QPushButton("🌙")
        self._theme_btn.setFixedSize(32, 28)
        self._theme_btn.setStyleSheet(
            f"background: {COLORS['panel_soft']}; "
            f"border: 1px solid {COLORS['border']}; "
            "border-radius: 6px; "
            "font-size: 14px; "
            "padding: 0; "
            "margin-left: 8px;"
        )
        self._theme_btn.setToolTip("Toggle dark / light mode")
        self._theme_btn.clicked.connect(self._on_theme_toggle)
        layout.addWidget(self._theme_btn)

        # Clock
        self._clock_label = QLabel()
        self._clock_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px; border: none; margin-left: 8px;"
        )
        self._update_clock()

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        layout.addWidget(self._clock_label)

    def _update_clock(self):
        self._clock_label.setText(datetime.now().strftime("%H:%M"))

    def set_status(self, label: str, color: str):
        self._status_badge.setText(f"● {label}")
        self._status_badge.setStyleSheet(f"color: {color}; font-size: 12px; border: none;")

    def _on_theme_toggle(self):
        import asyncio
        from auhip.core.event_bus import event_bus
        asyncio.create_task(event_bus.publish("TOGGLE_THEME", {}))

    def refresh_theme(self, dark: bool):
        """Re-apply styles after a theme switch."""
        self._apply_style()
        self._mark.setStyleSheet(f"color: {COLORS['accent']}; font-size: 16px; border: none;")
        self._title.setStyleSheet(
            f"color: {COLORS['text']}; font-size: 13px; font-weight: 600;"
            "letter-spacing: -0.1px; border: none;"
        )
        self._sep.setStyleSheet(
            f"color: {COLORS['border_dark']}; font-size: 14px; border: none; margin: 0 6px;"
        )
        self._status_badge.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px; border: none;"
        )
        self._clock_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px; border: none; margin-left: 8px;"
        )
        self._theme_btn.setStyleSheet(
            f"background: {COLORS['panel_soft']}; "
            f"border: 1px solid {COLORS['border']}; "
            "border-radius: 6px; "
            "font-size: 14px; "
            "padding: 0; "
            "margin-left: 8px;"
        )
        self._theme_btn.setText("☀️" if dark else "🌙")

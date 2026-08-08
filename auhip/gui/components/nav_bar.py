from datetime import datetime
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QTimer
from auhip.gui.theme import COLORS
from .last_command_widget import LastCommandWidget



class NavBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self._apply_style()
        self._build_ui()

    def _apply_style(self):
        self.setObjectName("NavBar")
        self.setStyleSheet(f"""
            #NavBar {{
                background: {COLORS['surface']};
                border-bottom: 1px solid {COLORS['border']};
                border-radius: 0px;
            }}
            #NavBar QLabel {{
                background: transparent;
                border: none;
            }}
        """)

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(8)

        # Wordmark icon
        self._mark = QLabel("✦")
        self._mark.setStyleSheet(f"color: {COLORS['accent']}; font-size: 14px; border: none; background: transparent;")
        layout.addWidget(self._mark)

        # App title
        self._title = QLabel("auhip")
        self._title.setStyleSheet(
            f"color: {COLORS['text']}; font-size: 13px; font-weight: 700; "
            "letter-spacing: -0.2px; border: none; background: transparent;"
        )
        layout.addWidget(self._title)

        # Sub-version pill badge
        self._ver_badge = QLabel("v2.4 OS")
        self._ver_badge.setStyleSheet(
            f"color: {COLORS['text_soft']}; font-size: 10px; font-weight: 600; "
            f"background: transparent; border: 1px solid {COLORS['border_soft']}; "
            "padding: 1px 5px; border-radius: 4px;"
        )
        layout.addWidget(self._ver_badge)

        # Stretch before center
        layout.addStretch(1)

        # Last activated command indicator (centered)
        self._last_cmd_widget = LastCommandWidget()
        layout.addWidget(self._last_cmd_widget)

        # Stretch after center
        layout.addStretch(1)

        # Status badge
        self._status_badge = QLabel("● Standby")
        self._status_badge.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px; font-weight: 500; border: none; background: transparent;"
        )
        layout.addWidget(self._status_badge)

        # Separator
        self._sep = QLabel("│")
        self._sep.setStyleSheet(
            f"color: {COLORS['border']}; font-size: 12px; border: none; background: transparent; margin: 0 2px;"
        )
        layout.addWidget(self._sep)

        # Clock
        self._clock_label = QLabel()
        self._clock_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px; font-weight: 500; border: none; background: transparent;"
        )
        self._update_clock()

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        layout.addWidget(self._clock_label)

        # Dark mode toggle button
        self._theme_btn = QPushButton("🌙")
        self._theme_btn.setFixedSize(28, 24)
        self._theme_btn.setCursor(Qt.CursorShape.PointingHandCursor if hasattr(Qt, 'CursorShape') else Qt.PointingHandCursor)
        self._theme_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {COLORS['border']};
                border-radius: 5px;
                font-size: 12px;
                padding: 0;
                margin-left: 4px;
            }}
            QPushButton:hover {{
                background: {COLORS['panel_soft']};
            }}
        """)
        self._theme_btn.setToolTip("Toggle dark / light mode")
        self._theme_btn.clicked.connect(self._on_theme_toggle)
        layout.addWidget(self._theme_btn)

    def _update_clock(self):
        self._clock_label.setText(datetime.now().strftime("%H:%M"))

    def set_status(self, label: str, color: str):
        self._status_badge.setText(f"● {label}")
        self._status_badge.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 500; border: none; background: transparent;")

    def _on_theme_toggle(self):
        import asyncio
        from auhip.core.event_bus import event_bus
        asyncio.create_task(event_bus.publish("TOGGLE_THEME", {}))

    def refresh_theme(self, dark: bool):
        """Re-apply styles after a theme switch."""
        self._apply_style()
        self._mark.setStyleSheet(f"color: {COLORS['accent']}; font-size: 14px; border: none; background: transparent;")
        self._title.setStyleSheet(
            f"color: {COLORS['text']}; font-size: 13px; font-weight: 700; "
            "letter-spacing: -0.2px; border: none; background: transparent;"
        )
        self._ver_badge.setStyleSheet(
            f"color: {COLORS['text_soft']}; font-size: 10px; font-weight: 600; "
            f"background: transparent; border: 1px solid {COLORS['border_soft']}; "
            "padding: 1px 5px; border-radius: 4px;"
        )
        self._sep.setStyleSheet(
            f"color: {COLORS['border']}; font-size: 12px; border: none; background: transparent; margin: 0 2px;"
        )
        self._status_badge.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px; font-weight: 500; border: none; background: transparent;"
        )
        self._clock_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px; font-weight: 500; border: none; background: transparent;"
        )
        self._theme_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {COLORS['border']};
                border-radius: 5px;
                font-size: 12px;
                padding: 0;
                margin-left: 4px;
            }}
            QPushButton:hover {{
                background: {COLORS['panel_soft']};
            }}
        """)
        self._theme_btn.setText("☀️" if dark else "🌙")
        self._last_cmd_widget.refresh_theme()



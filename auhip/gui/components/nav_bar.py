from datetime import datetime
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QFrame, QLineEdit
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
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

        # Floating center search / command pill (matching reference design)
        self._search_pill = QFrame()
        self._search_pill.setFixedHeight(28)
        self._search_pill.setStyleSheet("""
            QFrame {
                background: #FFFFFF;
                border: 1px solid #E7E5E4;
                border-radius: 14px;
                padding: 0 10px;
            }
            QFrame:focus-within {
                border: 1px solid #0C0A09;
            }
        """)
        sp_layout = QHBoxLayout(self._search_pill)
        sp_layout.setContentsMargins(4, 0, 4, 0)
        sp_layout.setSpacing(6)

        cmd_k = QLabel("⌘ K")
        cmd_k.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        cmd_k.setStyleSheet("color: #777169; border: none; background: transparent;")
        sp_layout.addWidget(cmd_k)

        self._nav_search_input = QLineEdit()
        self._nav_search_input.setPlaceholderText("Search, ask, or command anything...")
        self._nav_search_input.setFont(QFont("Inter", 11))
        self._nav_search_input.setFixedWidth(260)
        self._nav_search_input.setStyleSheet("border: none; background: transparent; color: #0C0A09; padding: 0;")
        self._nav_search_input.returnPressed.connect(self._on_search_submitted)
        sp_layout.addWidget(self._nav_search_input)

        layout.addWidget(self._search_pill)

        # Stretch after center
        layout.addStretch(1)

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

        # Status badge
        self._status_badge = QLabel("● Ready")
        self._status_badge.setStyleSheet(
            "color: #16A34A; font-size: 12px; font-weight: 500; border: none; background: transparent;"
        )
        layout.addWidget(self._status_badge)

        # Separator
        self._sep = QLabel("│")
        self._sep.setStyleSheet(
            f"color: {COLORS['border']}; font-size: 12px; border: none; background: transparent; margin: 0 2px;"
        )
        layout.addWidget(self._sep)

        # Dark mode toggle button
        self._theme_btn = QPushButton("🌙")
        self._theme_btn.setFixedSize(26, 24)
        self._theme_btn.setCursor(Qt.CursorShape.PointingHandCursor if hasattr(Qt, 'CursorShape') else Qt.PointingHandCursor)
        self._theme_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {COLORS['border']};
                border-radius: 9999px;
                font-size: 12px;
                padding: 0;
                margin-left: 2px;
            }}
            QPushButton:hover {{
                background: {COLORS['panel_soft']};
                border-color: {COLORS['border_dark']};
            }}
        """)
        self._theme_btn.setToolTip("Toggle dark / light mode")
        self._theme_btn.clicked.connect(self._on_theme_toggle)
        layout.addWidget(self._theme_btn)

        # View Mode toggle button (Voice HUD vs Cockpit)
        self._mode_btn = QPushButton("Cockpit 🎛️")
        self._mode_btn.setFixedHeight(24)
        self._mode_btn.setCursor(Qt.CursorShape.PointingHandCursor if hasattr(Qt, 'CursorShape') else Qt.PointingHandCursor)
        self._mode_btn.setStyleSheet("""
            QPushButton {
                background: #292524;
                color: #FFFFFF;
                border: 1px solid #292524;
                border-radius: 9999px;
                font-family: Inter;
                font-size: 11px;
                font-weight: 500;
                padding: 0 10px;
                margin-left: 4px;
            }
            QPushButton:hover {
                background: #0C0A09;
            }
        """)
        self._mode_btn.setToolTip("Toggle Aesthetic Voice HUD / Developer Cockpit (Ctrl+Tab)")
        self._mode_btn.clicked.connect(self._on_mode_toggle)
        layout.addWidget(self._mode_btn)

        # User profile avatar pill
        self._avatar_btn = QPushButton("👤")
        self._avatar_btn.setFixedSize(24, 24)
        self._avatar_btn.setCursor(Qt.CursorShape.PointingHandCursor if hasattr(Qt, 'CursorShape') else Qt.PointingHandCursor)
        self._avatar_btn.setStyleSheet("""
            QPushButton {
                background: #F0EFED;
                color: #292524;
                border: 1px solid #E7E5E4;
                border-radius: 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #E7E5E4;
            }
        """)
        layout.addWidget(self._avatar_btn)


    def _update_clock(self):
        self._clock_label.setText(datetime.now().strftime("%H:%M"))

    def set_status(self, label: str, color: str):
        self._status_badge.setText(f"● {label}")
        self._status_badge.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 500; border: none; background: transparent;")

    def _on_theme_toggle(self):
        import asyncio
        from auhip.core.event_bus import event_bus
        asyncio.create_task(event_bus.publish("TOGGLE_THEME", {}))

    def _on_mode_toggle(self):
        import asyncio
        from auhip.core.event_bus import event_bus
        asyncio.create_task(event_bus.publish("TOGGLE_UI_MODE", {}))

    def _on_search_submitted(self):
        txt = self._nav_search_input.text().strip()
        if txt:
            import asyncio
            from auhip.core.event_bus import event_bus
            asyncio.create_task(event_bus.publish("PROCESS_COMMAND", {"command": txt}))
            self._nav_search_input.clear()

    def update_mode_button(self, stack_index: int):
        """Updates button label depending on current mode."""
        if stack_index == 0:
            self._mode_btn.setText("🎛️ Cockpit")
            self._mode_btn.setToolTip("Switch to Developer Cockpit (Ctrl+Tab)")
        else:
            self._mode_btn.setText("🌌 Voice HUD")
            self._mode_btn.setToolTip("Switch to Aesthetic Voice HUD (Ctrl+Tab)")


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
                border-radius: 9999px;
                font-size: 12px;
                padding: 0;
                margin-left: 4px;
            }}
            QPushButton:hover {{
                background: {COLORS['panel_soft']};
                border-color: {COLORS['border_dark']};
            }}
        """)
        self._theme_btn.setText("☀️" if dark else "🌙")
        self._mode_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS['text_body']};
                border: 1px solid {COLORS['border_dark']};
                border-radius: 9999px;
                font-family: Inter;
                font-size: 11px;
                font-weight: 500;
                padding: 0 10px;
                margin-left: 4px;
            }}
            QPushButton:hover {{
                background: {COLORS['panel_soft']};
                color: {COLORS['text']};
                border-color: {COLORS['accent']};
            }}
        """)

        self._last_cmd_widget.refresh_theme()




from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QWidget,
    QScrollArea,
    QFrame,
    QGridLayout,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class CockpitGuideModal(QDialog):
    """
    Comprehensive, high-fidelity User Guide & Cheat Sheet for Cockpit Mode & AUHIP.
    Contains 4 visual tabs:
    1. 🎮 Air-Mouse & Hand Gestures
    2. 🎙️ Voice Commands & Wake Words
    3. 🎛️ Cockpit Layout & Workstation
    4. ⌨️ Keyboard Shortcuts
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AUHIP Cockpit User Guide & Capabilities")
        self.setFixedSize(680, 560)
        self.setStyleSheet("""
            QDialog {
                background: #FFFFFF;
                border-radius: 16px;
            }
            QTabWidget::pane {
                border: 1px solid #E7E5E4;
                border-radius: 12px;
                background: #FAFAFA;
                padding: 12px;
            }
            QTabBar::tab {
                background: #F0EFED;
                color: #57534E;
                padding: 8px 16px;
                border-radius: 8px;
                margin-right: 6px;
                font-family: 'Inter';
                font-size: 11px;
                font-weight: 500;
            }
            QTabBar::tab:selected {
                background: #0C0A09;
                color: #FFFFFF;
                font-weight: 600;
            }
            QTabBar::tab:hover:!selected {
                background: #E7E5E4;
                color: #0C0A09;
            }
        """)
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 18, 20, 18)
        main_layout.setSpacing(12)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title = QLabel("📖 AUHIP Cockpit & Feature Guide")
        title.setFont(QFont("Inter", 14, QFont.Weight.DemiBold))
        title.setStyleSheet("color: #0C0A09;")
        title_box.addWidget(title)

        sub = QLabel("Master all voice commands, air-mouse gestures, and workstation tools")
        sub.setFont(QFont("Inter", 10))
        sub.setStyleSheet("color: #777169;")
        title_box.addWidget(sub)
        hdr.addLayout(title_box)

        hdr.addStretch(1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #F0EFED;
                color: #57534E;
                border: none;
                border-radius: 13px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #FEE2E2;
                color: #DC2626;
            }
        """)
        close_btn.clicked.connect(self.accept)
        hdr.addWidget(close_btn)

        main_layout.addLayout(hdr)

        # ── Tabs ──────────────────────────────────────────────────────────────
        self.tabs = QTabWidget()

        self.tabs.addTab(self._build_gestures_tab(), "🎮 Air-Mouse & Gestures")
        self.tabs.addTab(self._build_voice_tab(), "🎙️ Voice Commands")
        self.tabs.addTab(self._build_cockpit_tab(), "🎛️ Cockpit Features")
        self.tabs.addTab(self._build_shortcuts_tab(), "⌨️ Shortcuts")

        main_layout.addWidget(self.tabs, 1)

        # ── Footer ────────────────────────────────────────────────────────────
        footer = QHBoxLayout()
        hint = QLabel("💡 Tip: Press F2 or Ctrl+Tab anytime to toggle between Voice UI and Cockpit Mode")
        hint.setFont(QFont("Inter", 10))
        hint.setStyleSheet("color: #4F46E5;")
        footer.addWidget(hint)
        footer.addStretch(1)

        ok_btn = QPushButton("Got it")
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.setFont(QFont("Inter", 10, QFont.Weight.DemiBold))
        ok_btn.setStyleSheet("""
            QPushButton {
                background: #0C0A09;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 6px 18px;
            }
            QPushButton:hover { background: #292524; }
        """)
        ok_btn.clicked.connect(self.accept)
        footer.addWidget(ok_btn)

        main_layout.addLayout(footer)

    def _build_gestures_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(10)

        intro = QLabel("<b>How Air-Mouse Control Works:</b> Point your hand at the camera. AUHIP tracks your 21 hand landmarks in real time to provide contactless computer control.")
        intro.setFont(QFont("Inter", 10))
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #292524; margin-bottom: 4px;")
        layout.addWidget(intro)

        gestures = [
            ("👆 Point Index Finger", "Move Cursor", "Extend your index finger forward. The mouse cursor on your computer will smoothly follow your fingertip with sub-pixel 1€ filtering."),
            ("🤏 Pinch Index & Thumb", "Left Click", "Briefly pinch your index finger and thumb together (< 0.5s) to trigger an immediate single left-click."),
            ("✊ Pinch & Hold", "Drag & Drop", "Pinch your index finger and thumb and hold for more than 0.5 seconds. The mouse button stays pressed down so you can drag windows or files. Release pinch to drop."),
            ("✌️ Double Pinch", "Double Click", "Pinch twice quickly within 0.4 seconds to trigger a double-click (opens files, selects words)."),
            ("✊ Move Fist Up / Down", "Scroll Page", "Close your hand into a fist and move it upwards to scroll up, or downwards to scroll down smoothly."),
            ("🤘 Rock-On Sign (🤘)", "Exit Air-Mouse", "Raise index and pinky fingers (Rock sign) to exit Air-Mouse mode and return to normal Voice Mode."),
            ("🖐️ 3 Fingers Up / Down", "Adjust Volume", "Hold 3 fingers up to raise PC master volume, or 3 fingers down to lower volume."),
        ]

        for title, action, desc in gestures:
            card = self._make_guide_card(title, action, desc, "#2563EB")
            layout.addWidget(card)

        scroll.setWidget(container)
        return scroll

    def _build_voice_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(10)

        categories = [
            ("⚡ System Wake & Sleep", [
                ("“daddy home”", "Wakes up the assistant from sleep/standby mode immediately."),
                ("“goodbye jojo”", "Puts the assistant to sleep and unloads camera/models to save battery."),
            ]),
            ("🎮 Mode Switching", [
                ("“control mode” / “air mouse”", "Enters Air-Mouse Computer Control mode with live hand tracking."),
                ("“open camera” / “vision mode”", "Enters Camera HUD with face, gaze, and attention detection."),
                ("“voice mode”", "Returns to the minimal ambient Voice UI."),
            ]),
            ("📁 Coding & Workspace Tools", [
                ("“analyze my project”", "Runs a structural workspace scan and reports performance bottlenecks."),
                ("“find unused files”", "Scans the codebase for orphaned Python modules and unused files."),
                ("“scan workspace”", "Lists project files and structure."),
            ]),
            ("📋 Task & Organizer Skills", [
                ("“add task <description>”", "Adds a new task to your organizer list (e.g. 'add task fix tts')."),
                ("“list tasks”", "Lists all active and completed to-do tasks."),
                ("“complete task <id>”", "Marks the specified task as done."),
                ("“check stock AAPL”", "Queries real-time financial stock price."),
                ("“play music <song>”", "Searches and opens YouTube Music for your request."),
            ]),
        ]

        for cat_title, items in categories:
            cat_lbl = QLabel(cat_title)
            cat_lbl.setFont(QFont("Inter", 11, QFont.Weight.Bold))
            cat_lbl.setStyleSheet("color: #0C0A09; margin-top: 4px;")
            layout.addWidget(cat_lbl)

            for phrase, desc in items:
                card = self._make_guide_card(phrase, "", desc, "#059669")
                layout.addWidget(card)

        scroll.setWidget(container)
        return scroll

    def _build_cockpit_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(10)

        features = [
            ("Left Column: System Status Card", "Hardware & Audio Gauges", "Monitors FSM state, microphone capture, acoustic snap detection count, CPU/RAM/GPU activity meters, and contains an embedded mini audio-reactive orb."),
            ("Top Bento Cards", "Priorities, In-Progress, Local AI", "• Priorities Card: Shows urgent tasks. Click 'View all tasks →' to open the interactive Task Manager.<br>• In Progress Card: Tracks project progress bar. Click 'Open workspace →' to view project files.<br>• System Overview: Displays Ollama model status (Qwen 7B) and RAM allocation."),
            ("Center Deck Navigation", "3 Switchable Workspaces", "• 💬 Chat Workspace: Complete conversational history, step execution checklist, and prompt bar.<br>• 👁️ Vision & Air-Mouse HUD: Live camera viewport, iris gaze tracking, eye blinks, and air-mouse controls.<br>• 📁 Workspace Explorer: File tree inspector, code reader with syntax styling, and unused files scan."),
            ("Right Column", "History & Active Sub-Agents", "• Command History: Click any past command to immediately re-run it.<br>• Active Tasks: Shows background autonomous agents (Code Agent, Research Agent)."),
            ("Bottom Debug Drawer", "Collapsible Controls", "Click 'DEBUG & CONTROLS ∨' to test hardware devices, trigger mode overrides, run manual prompt inputs, and stream live system events."),
        ]

        for title, subtitle, desc in features:
            card = self._make_guide_card(title, subtitle, desc, "#7C3AED")
            layout.addWidget(card)

        scroll.setWidget(container)
        return scroll

    def _build_shortcuts_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(12)

        shortcuts = [
            ("Ctrl + Tab  /  F2", "Toggle Voice UI ↔ Cockpit Mode", "Instantly switches between the minimal Voice Interface and the full developer Cockpit."),
            ("Escape", "Stop Listening / Cancel", "Immediately cancels active listening, stops speech recognition, or exits sub-modes."),
            ("Click [ 👁️ Vision ]", "Open Camera Feed", "Switches center deck to live Camera Viewport with gaze and gesture detection."),
            ("Click [ 🎮 Air-Mouse ]", "Enable Mouse Control", "Enables finger-tracking cursor control and pinch clicking."),
            ("Click [ 📖 Guide ]", "Open User Guide", "Opens this comprehensive documentation window at any time."),
        ]

        for keys, action, desc in shortcuts:
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background: #FFFFFF;
                    border: 1px solid #E7E5E4;
                    border-radius: 10px;
                    padding: 8px 12px;
                }
            """)
            c_layout = QHBoxLayout(card)
            c_layout.setContentsMargins(10, 8, 10, 8)

            key_badge = QLabel(keys)
            key_badge.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
            key_badge.setStyleSheet("""
                color: #0C0A09;
                background: #F0EFED;
                border: 1px solid #D6D3D1;
                border-radius: 6px;
                padding: 4px 8px;
            """)
            c_layout.addWidget(key_badge)

            text_box = QVBoxLayout()
            text_box.setSpacing(2)
            act_lbl = QLabel(action)
            act_lbl.setFont(QFont("Inter", 11, QFont.Weight.DemiBold))
            act_lbl.setStyleSheet("color: #0C0A09;")
            text_box.addWidget(act_lbl)

            desc_lbl = QLabel(desc)
            desc_lbl.setFont(QFont("Inter", 10))
            desc_lbl.setStyleSheet("color: #777169;")
            text_box.addWidget(desc_lbl)

            c_layout.addLayout(text_box, 1)
            layout.addWidget(card)

        layout.addStretch(1)
        return container

    def _make_guide_card(self, title: str, subtitle: str, description: str, tag_color: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: #FFFFFF;
                border: 1px solid #E7E5E4;
                border-radius: 10px;
                padding: 8px 12px;
            }
        """)
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(10, 8, 10, 8)
        c_layout.setSpacing(4)

        hdr_row = QHBoxLayout()
        t_lbl = QLabel(title)
        t_lbl.setFont(QFont("Inter", 11, QFont.Weight.DemiBold))
        t_lbl.setStyleSheet("color: #0C0A09;")
        hdr_row.addWidget(t_lbl)

        if subtitle:
            sub_badge = QLabel(subtitle)
            sub_badge.setFont(QFont("Inter", 9, QFont.Weight.Bold))
            sub_badge.setStyleSheet(f"""
                color: {tag_color};
                background: #FAFAFA;
                border: 1px solid #E7E5E4;
                border-radius: 6px;
                padding: 2px 6px;
            """)
            hdr_row.addWidget(sub_badge)

        hdr_row.addStretch(1)
        c_layout.addLayout(hdr_row)

        desc_lbl = QLabel(description)
        desc_lbl.setFont(QFont("Inter", 10))
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #57534E; line-height: 1.3;")
        c_layout.addWidget(desc_lbl)

        return card

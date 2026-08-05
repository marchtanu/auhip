import psutil
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import QTimer
from auhip.gui.theme import COLORS
from .state_panel import StatePanel


class LeftPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(260)
        self._apply_style()
        self._build_ui()

        # Poll CPU/RAM every 3 seconds
        self._stats_timer = QTimer(self)
        self._stats_timer.timeout.connect(self._update_stats)
        self._stats_timer.start(3000)

    def _apply_style(self):
        self.setStyleSheet(
            f"QFrame {{ background: {COLORS['panel']}; border: 1px solid {COLORS['border']};"
            "border-radius: 12px; }"
        )

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(0)

        # State panel (custom painted)
        self.state_panel = StatePanel()
        layout.addWidget(self.state_panel)

        # Divider
        self._dividers = []
        layout.addWidget(self._make_divider())

        # Mic status row
        self._mic_dot = QLabel("●")
        self._mic_dot.setStyleSheet(f"color: {COLORS['success']}; font-size: 10px; border: none;")

        mic_row = QWidget()
        mic_row.setStyleSheet("background: transparent; border: none;")
        mic_layout = QHBoxLayout(mic_row)
        mic_layout.setContentsMargins(0, 8, 0, 0)
        mic_layout.setSpacing(6)
        mic_layout.addWidget(self._mic_dot)

        self.mic_lbl = QLabel("Microphone")
        self.mic_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 13px; border: none;")
        mic_layout.addWidget(self.mic_lbl)
        mic_layout.addStretch()
        layout.addWidget(mic_row)

        # Snap detector
        layout.addSpacing(8)
        self.snap_label = QLabel("Snap detector")
        self.snap_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; border: none;")
        layout.addWidget(self.snap_label)

        snap_dots_row = QWidget()
        snap_dots_row.setStyleSheet("background: transparent; border: none;")
        snap_dots_layout = QHBoxLayout(snap_dots_row)
        snap_dots_layout.setContentsMargins(0, 4, 0, 0)
        snap_dots_layout.setSpacing(6)

        self.snap_dot_1 = QLabel("○")
        self.snap_dot_1.setStyleSheet(f"color: {COLORS['border']}; font-size: 16px; border: none;")
        self.snap_dot_2 = QLabel("○")
        self.snap_dot_2.setStyleSheet(f"color: {COLORS['border']}; font-size: 16px; border: none;")

        snap_dots_layout.addWidget(self.snap_dot_1)
        snap_dots_layout.addWidget(self.snap_dot_2)
        snap_dots_layout.addStretch()
        layout.addWidget(snap_dots_row)

        layout.addStretch()

        # Divider before system stats
        layout.addWidget(self._make_divider())

        # ── System Stats Widget ──────────────────────────────────────────
        self.stats_label = QLabel("System")
        self.stats_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; font-weight: 600;"
            "letter-spacing: 0.4px; text-transform: uppercase; border: none;"
        )
        layout.addWidget(self.stats_label)
        layout.addSpacing(8)

        # CPU row
        cpu_row = QWidget()
        cpu_row.setStyleSheet("background: transparent; border: none;")
        cpu_layout = QHBoxLayout(cpu_row)
        cpu_layout.setContentsMargins(0, 0, 0, 0)
        cpu_layout.setSpacing(4)

        self.cpu_icon = QLabel("CPU")
        self.cpu_icon.setStyleSheet(
            f"color: {COLORS['text_soft']}; font-size: 11px; font-weight: 600; border: none; min-width: 32px;"
        )
        cpu_layout.addWidget(self.cpu_icon)

        self._cpu_bar_bg = QFrame()
        self._cpu_bar_bg.setFixedHeight(6)
        self._cpu_bar_bg.setStyleSheet(
            f"background: {COLORS['border']}; border-radius: 3px; border: none;"
        )
        cpu_layout.addWidget(self._cpu_bar_bg, 1)

        self._cpu_label = QLabel("0%")
        self._cpu_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; border: none; min-width: 32px;"
        )
        cpu_layout.addWidget(self._cpu_label)
        layout.addWidget(cpu_row)

        # CPU progress bar (child of bg frame for layering)
        self._cpu_bar = QFrame(self._cpu_bar_bg)
        self._cpu_bar.setFixedHeight(6)
        self._cpu_bar.setStyleSheet(
            f"background: {COLORS['accent']}; border-radius: 3px; border: none;"
        )
        self._cpu_bar.setFixedWidth(0)

        layout.addSpacing(6)

        # RAM row
        ram_row = QWidget()
        ram_row.setStyleSheet("background: transparent; border: none;")
        ram_layout = QHBoxLayout(ram_row)
        ram_layout.setContentsMargins(0, 0, 0, 0)
        ram_layout.setSpacing(4)

        self.ram_icon = QLabel("RAM")
        self.ram_icon.setStyleSheet(
            f"color: {COLORS['text_soft']}; font-size: 11px; font-weight: 600; border: none; min-width: 32px;"
        )
        ram_layout.addWidget(self.ram_icon)

        self._ram_bar_bg = QFrame()
        self._ram_bar_bg.setFixedHeight(6)
        self._ram_bar_bg.setStyleSheet(
            f"background: {COLORS['border']}; border-radius: 3px; border: none;"
        )
        ram_layout.addWidget(self._ram_bar_bg, 1)

        self._ram_label = QLabel("0%")
        self._ram_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; border: none; min-width: 32px;"
        )
        ram_layout.addWidget(self._ram_label)
        layout.addWidget(ram_row)

        # RAM progress bar
        self._ram_bar = QFrame(self._ram_bar_bg)
        self._ram_bar.setFixedHeight(6)
        self._ram_bar.setStyleSheet(
            f"background: {COLORS['success']}; border-radius: 3px; border: none;"
        )
        self._ram_bar.setFixedWidth(0)

        layout.addSpacing(4)

    # ── Private Helpers ───────────────────────────────────────────────────────

    def _make_divider(self) -> QWidget:
        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background: {COLORS['border_soft']}; border: none; border-radius: 0;")
        self._dividers.append(line)
        container = QWidget()
        container.setStyleSheet("background: transparent; border: none;")
        l = QVBoxLayout(container)
        l.setContentsMargins(0, 16, 0, 12)
        l.addWidget(line)
        return container

    def _update_stats(self):
        """Refresh CPU and RAM bar widths and labels every 3 seconds."""
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent

        self._cpu_label.setText(f"{int(cpu)}%")
        self._ram_label.setText(f"{int(ram)}%")

        # Scale bars relative to their parent container widths
        cpu_w = max(1, int(self._cpu_bar_bg.width() * cpu / 100))
        ram_w = max(1, int(self._ram_bar_bg.width() * ram / 100))

        self._cpu_bar.setFixedWidth(cpu_w)
        self._ram_bar.setFixedWidth(ram_w)

        # Colour the CPU bar red when under heavy load
        if cpu >= 80:
            self._cpu_bar.setStyleSheet(
                f"background: {COLORS['danger']}; border-radius: 3px; border: none;"
            )
        elif cpu >= 50:
            self._cpu_bar.setStyleSheet(
                f"background: {COLORS['warning']}; border-radius: 3px; border: none;"
            )
        else:
            self._cpu_bar.setStyleSheet(
                f"background: {COLORS['accent']}; border-radius: 3px; border: none;"
            )

        # Colour the RAM bar similarly
        if ram >= 85:
            self._ram_bar.setStyleSheet(
                f"background: {COLORS['danger']}; border-radius: 3px; border: none;"
            )
        elif ram >= 65:
            self._ram_bar.setStyleSheet(
                f"background: {COLORS['warning']}; border-radius: 3px; border: none;"
            )
        else:
            self._ram_bar.setStyleSheet(
                f"background: {COLORS['success']}; border-radius: 3px; border: none;"
            )

    # ── Public API ────────────────────────────────────────────────────────────

    def set_mic_active(self, active: bool):
        color = COLORS["success"] if active else COLORS["text_soft"]
        self._mic_dot.setStyleSheet(f"color: {color}; font-size: 10px; border: none;")

    def update_snaps(self, count: int):
        coral = COLORS["accent"]
        soft = COLORS["border"]
        if count == 0:
            self.snap_dot_1.setText("○")
            self.snap_dot_1.setStyleSheet(f"color: {soft}; font-size: 16px; border: none;")
            self.snap_dot_2.setText("○")
            self.snap_dot_2.setStyleSheet(f"color: {soft}; font-size: 16px; border: none;")
        elif count == 1:
            self.snap_dot_1.setText("●")
            self.snap_dot_1.setStyleSheet(f"color: {coral}; font-size: 16px; border: none;")
            self.snap_dot_2.setText("○")
            self.snap_dot_2.setStyleSheet(f"color: {soft}; font-size: 16px; border: none;")
        else:
            self.snap_dot_1.setText("●")
            self.snap_dot_1.setStyleSheet(f"color: {coral}; font-size: 16px; border: none;")
            self.snap_dot_2.setText("●")
            self.snap_dot_2.setStyleSheet(f"color: {coral}; font-size: 16px; border: none;")

        if count > 0:
            QTimer.singleShot(1000, lambda: self.update_snaps(0))

    def refresh_theme(self):
        """Re-apply all colours after a theme switch."""
        self._apply_style()
        self.state_panel.update()

        # Refresh all child widgets styling
        self._mic_dot.setStyleSheet(f"color: {COLORS['success']}; font-size: 10px; border: none;")
        self.mic_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 13px; border: none;")
        self.snap_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; border: none;")

        soft = COLORS["border"]
        self.snap_dot_1.setStyleSheet(f"color: {soft}; font-size: 16px; border: none;")
        self.snap_dot_2.setStyleSheet(f"color: {soft}; font-size: 16px; border: none;")

        self.stats_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; font-weight: 600;"
            "letter-spacing: 0.4px; text-transform: uppercase; border: none;"
        )
        self.cpu_icon.setStyleSheet(
            f"color: {COLORS['text_soft']}; font-size: 11px; font-weight: 600; border: none; min-width: 32px;"
        )
        self._cpu_bar_bg.setStyleSheet(
            f"background: {COLORS['border']}; border-radius: 3px; border: none;"
        )
        self._cpu_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; border: none; min-width: 32px;"
        )
        self.ram_icon.setStyleSheet(
            f"color: {COLORS['text_soft']}; font-size: 11px; font-weight: 600; border: none; min-width: 32px;"
        )
        self._ram_bar_bg.setStyleSheet(
            f"background: {COLORS['border']}; border-radius: 3px; border: none;"
        )
        self._ram_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; border: none; min-width: 32px;"
        )

        # Dividers
        for div in getattr(self, '_dividers', []):
            div.setStyleSheet(f"background: {COLORS['border_soft']}; border: none; border-radius: 0;")

        self._update_stats()  # Re-colours the bars with new theme colours


import math
from collections import deque
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen
from auhip.gui.theme import COLORS


class WaveformWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(48)
        self._data = deque(maxlen=100)
        self._idle_phase = 0.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(33)  # ~30fps smooth animation

    def add_energy(self, energy: float):
        self._data.append(min(energy * 5.0, 1.0))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        mid = h // 2

        # Transparent background
        painter.fillRect(0, 0, w, h, QColor(0, 0, 0, 0))

        # Center line — subtle hairline border
        border_col = QColor(COLORS["border"])
        painter.setPen(QPen(border_col, 1))
        painter.drawLine(0, mid, w, mid)

        accent = QColor(COLORS["accent"])

        if len(self._data) < 2:
            # Idle wave visualization with ambient points
            self._idle_phase += 0.05
            for x in range(0, w, 4):
                t = x / max(w, 1)
                y = mid + int(6 * math.sin(t * 4 * math.pi + self._idle_phase))
                color = QColor(COLORS["border"])
                painter.setPen(QPen(color, 1.5))
                painter.drawPoint(x, y)
            return

        # Dynamic frequency audio bars
        n = len(self._data)
        bar_gap = 2
        total_gaps = (n - 1) * bar_gap
        bar_w = max(2, (w - total_gaps) // n)

        for i, energy in enumerate(self._data):
            x = int(i * (bar_w + bar_gap))
            bar_h = max(2, int(energy * (mid - 4)))
            alpha = int(70 + 185 * energy)
            color = QColor(accent)
            color.setAlpha(alpha)

            # Draw upper and lower bar with rounded rect corners
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(x, mid - bar_h, bar_w, bar_h * 2, 2, 2)


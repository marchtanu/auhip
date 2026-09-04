import time
import math
import numpy as np
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QBrush,
    QRadialGradient,
    QLinearGradient,
)


class AmbientOrbWidget(QWidget):
    """
    Volumetric AI Voice Orb & Continuous Horizontal Audio Waveform
    matching the AUHIP high-fidelity design mockup:
    - Single large floating AI orb (380-450px)
    - Liquid plasma, flowing silk, gas clouds, and subtle aurora textures
    - Colors blending between deep blue, indigo, lavender, purple, pale pink, and white
    - Soft blurred elliptical shadow underneath to create floating depth
    - Continuous horizontal audio waveform spanning across the middle directly behind the orb
    - Waveform has clusters of louder peaks, fades toward edges, and reacts live to microphone audio
    - Gentle idle breathing and harmonic fluid motion
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_energy = 0.0
        self._target_energy = 0.0
        self._energy_history = [0.0] * 96
        self._is_speaking = False
        self._state_label = "Listening"
        self._start_time = time.time()

        # 60 FPS animation timer for fluid physics
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._on_tick)
        self._anim_timer.start(16)

    def update_audio(self, chunk):
        """Processes audio chunk and updates energy levels and waveform history."""
        if chunk is None or len(chunk) == 0:
            return
        try:
            rms = float(np.sqrt(np.mean(chunk**2)))
            normalized = min(1.0, rms * 5.8)
            self._target_energy = max(self._target_energy, normalized)

            self._energy_history.pop(0)
            self._energy_history.append(normalized)
        except Exception:
            pass

    def set_speaking_state(self, is_speaking: bool):
        self._is_speaking = is_speaking

    def set_status_label(self, label: str):
        self._state_label = label

    def _on_tick(self):
        alpha = 0.28 if self._target_energy > self._current_energy else 0.12
        self._current_energy += (self._target_energy - self._current_energy) * alpha
        self._target_energy *= 0.90
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        width = self.width()
        height = self.height()
        cx = width / 2.0
        cy = height / 2.0

        t = time.time() - self._start_time

        # Gentle idle breathing oscillation (2-3px)
        breathing = math.sin(t * 1.5) * 3.0

        # Base radius: ~195px (diameter ~390px, expanding up to ~440px with voice volume)
        base_radius = min(width * 0.22, height * 0.32, 210.0)
        energy_expand = self._current_energy * (base_radius * 0.22)
        radius = base_radius + breathing + energy_expand

        # ── 1. Soft Blurred Elliptical Shadow Underneath ──────────────────────
        self._draw_floor_shadow(painter, cx, cy, radius)

        # ── 2. Continuous Horizontal Audio Waveform (Runs Behind the Orb) ─────
        self._draw_horizontal_waveform(painter, cx, cy, width, radius, t)

        # ── 3. Large Volumetric Floating AI Orb ───────────────────────────────
        self._draw_volumetric_orb(painter, cx, cy, radius, t)

        painter.end()

    def _draw_floor_shadow(self, painter: QPainter, cx: float, cy: float, r: float):
        """Draws a very soft blurred elliptical shadow underneath the orb to ground it in 3D space."""
        shadow_y = cy + r + 45.0
        shadow_w = r * 1.55
        shadow_h = r * 0.26

        shadow_rect = QRectF(cx - shadow_w / 2.0, shadow_y - shadow_h / 2.0, shadow_w, shadow_h)
        grad = QRadialGradient(QPointF(cx, shadow_y), shadow_w / 2.0)
        # Deep indigo-slate diffused shadow
        grad.setColorAt(0.0, QColor(67, 56, 202, 60))
        grad.setColorAt(0.35, QColor(99, 102, 241, 35))
        grad.setColorAt(0.70, QColor(165, 180, 252, 12))
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawEllipse(shadow_rect)

    def _draw_horizontal_waveform(self, painter: QPainter, cx: float, cy: float, width: float, orb_r: float, t: float):
        """
        Continuous horizontal audio waveform spanning across the middle of the screen,
        composed of thin vertical white lines with varying heights and peak clusters,
        fading toward both outer edges.
        """
        num_bars = 92
        bar_w = 2.4
        bar_gap = 5.4
        total_span = (num_bars - 1) * (bar_w + bar_gap)
        start_x = cx - (total_span / 2.0)

        for i in range(num_bars):
            # Normalized position from center (-1.0 to +1.0)
            norm_x = (i / float(num_bars - 1)) * 2.0 - 1.0
            bx = start_x + i * (bar_w + bar_gap)

            # Fade gradually toward far left and right edges
            edge_falloff = math.cos(norm_x * (math.pi / 2.0))
            edge_falloff = max(0.0, edge_falloff) ** 1.30

            # Create natural clusters of louder peaks (around x = -0.65, -0.35, +0.35, +0.65)
            cluster_1 = math.exp(-((abs(norm_x) - 0.48) ** 2) / 0.04) * 1.5
            cluster_2 = math.exp(-((abs(norm_x) - 0.72) ** 2) / 0.03) * 1.1
            peak_factor = 0.55 + (cluster_1 + cluster_2) * 0.65

            # Historical audio energy sample
            hist_idx = int(abs(norm_x) * (len(self._energy_history) - 1))
            energy_sample = self._energy_history[hist_idx]

            # Dynamic harmonic audio wave modulation
            wave_mod = (
                math.sin(t * 3.4 + i * 0.24) * 0.25 +
                math.sin(t * 5.2 - i * 0.16) * 0.15 +
                0.60
            )

            # Bar height computation
            h = 4.0 + (edge_falloff * peak_factor * (energy_sample * 95.0 + 16.0) * wave_mod)
            by = cy - (h / 2.0)

            # Soft glowing white with periwinkle bloom alpha
            alpha = int(max(0, min(245, edge_falloff * 205 + (energy_sample * 50))))
            bar_color = QColor(255, 255, 255, alpha)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(bar_color))
            painter.drawRoundedRect(QRectF(bx, by, bar_w, h), 1.2, 1.2)

    def _draw_volumetric_orb(self, painter: QPainter, cx: float, cy: float, r: float, t: float):
        """
        Renders the large 3D volumetric floating AI orb:
        - 380-450px perfectly circular volume
        - Liquid plasma, flowing silk, and gas cloud textures
        - Blending deep blue, indigo, lavender, purple, pale pink, and white
        - Glowing softly around the edge with no hard outlines
        - Volumetric lighting with light offset towards top-left
        """
        # ── 1. Soft Atmospheric Outer Glow (Radiates behind the orb) ──────────
        glow_r = r * 1.40
        glow_grad = QRadialGradient(QPointF(cx, cy), glow_r)
        glow_grad.setColorAt(0.0, QColor(224, 231, 255, 95))
        glow_grad.setColorAt(0.45, QColor(199, 210, 254, 50))
        glow_grad.setColorAt(0.80, QColor(237, 233, 254, 18))
        glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow_grad))
        painter.drawEllipse(QPointF(cx, cy), glow_r, glow_r)

        # ── 2. Primary 3D Volumetric Body (Celestial Indigo/Lavender/Sky) ─────
        light_x = cx - r * 0.28
        light_y = cy - r * 0.28

        body_grad = QRadialGradient(QPointF(light_x, light_y), r * 1.25)
        body_grad.setColorAt(0.0, QColor(255, 255, 255, 250))   # White specular core
        body_grad.setColorAt(0.16, QColor(186, 230, 253, 240))  # Pale sky-blue (#BAE6FD)
        body_grad.setColorAt(0.38, QColor(196, 181, 253, 230))  # Soft lavender (#C4B5FD)
        body_grad.setColorAt(0.62, QColor(99, 102, 241, 220))   # Deep indigo (#6366F1)
        body_grad.setColorAt(0.84, QColor(67, 56, 202, 200))    # Deep royal blue (#4338CA)
        body_grad.setColorAt(0.96, QColor(79, 70, 229, 160))    # Soft gaseous rim
        body_grad.setColorAt(1.0, QColor(79, 70, 229, 0))       # Foggy falloff (no hard outline)

        painter.setBrush(QBrush(body_grad))
        painter.drawEllipse(QPointF(cx, cy), r * 1.02, r * 1.02)

        # ── 3. Internal Liquid Plasma Layer 1 (Warm Pink & Peach Aurora) ───────
        swirl1_x = math.sin(t * 1.2) * (r * 0.18)
        swirl1_y = math.cos(t * 1.0) * (r * 0.14)

        swirl1_grad = QRadialGradient(QPointF(cx + swirl1_x + r * 0.10, cy + swirl1_y + r * 0.06), r * 0.82)
        swirl1_grad.setColorAt(0.0, QColor(254, 215, 170, 195))  # Peach (#FED7AA)
        swirl1_grad.setColorAt(0.35, QColor(244, 114, 182, 160)) # Pale pink (#F472B6)
        swirl1_grad.setColorAt(0.70, QColor(196, 181, 253, 90))  # Lavender
        swirl1_grad.setColorAt(1.0, QColor(0, 0, 0, 0))

        painter.setBrush(QBrush(swirl1_grad))
        painter.drawEllipse(QPointF(cx + swirl1_x * 0.5, cy + swirl1_y * 0.5), r * 0.82, r * 0.82)

        # ── 4. Internal Liquid Plasma Layer 2 (Deep Ocean Indigo & Violet Cloud)
        swirl2_x = math.cos(t * 1.3) * (r * 0.16)
        swirl2_y = math.sin(t * 1.4) * (r * 0.14)

        swirl2_grad = QRadialGradient(QPointF(cx - swirl2_x - r * 0.12, cy - swirl2_y - r * 0.08), r * 0.78)
        swirl2_grad.setColorAt(0.0, QColor(37, 99, 235, 165))    # Royal blue (#2563EB)
        swirl2_grad.setColorAt(0.40, QColor(147, 51, 234, 130))  # Deep purple (#9333EA)
        swirl2_grad.setColorAt(0.80, QColor(99, 102, 241, 55))   # Indigo
        swirl2_grad.setColorAt(1.0, QColor(0, 0, 0, 0))

        painter.setBrush(QBrush(swirl2_grad))
        painter.drawEllipse(QPointF(cx - swirl2_x * 0.4, cy - swirl2_y * 0.4), r * 0.78, r * 0.78)

        # ── 5. Internal Flowing Silk Layer 3 (Counter-Rotating Ethereal Mist) ──
        silk_x = math.sin(t * 1.6) * (r * 0.12)
        silk_y = math.cos(t * 1.7) * (r * 0.10)

        silk_grad = QRadialGradient(QPointF(cx + silk_x, cy + silk_y - r * 0.12), r * 0.65)
        silk_grad.setColorAt(0.0, QColor(255, 255, 255, 175))
        silk_grad.setColorAt(0.45, QColor(224, 231, 255, 110))   # Ethereal sky
        silk_grad.setColorAt(0.85, QColor(237, 233, 254, 45))    # Lavender
        silk_grad.setColorAt(1.0, QColor(0, 0, 0, 0))

        painter.setBrush(QBrush(silk_grad))
        painter.drawEllipse(QPointF(cx + silk_x * 0.3, cy + silk_y * 0.3), r * 0.65, r * 0.65)

        # ── 6. Top-Left Specular Surface Bloom (Volumetric glass curve) ────────
        spec_grad = QRadialGradient(QPointF(light_x, light_y), r * 0.48)
        spec_grad.setColorAt(0.0, QColor(255, 255, 255, 235))
        spec_grad.setColorAt(0.45, QColor(255, 255, 255, 75))
        spec_grad.setColorAt(1.0, QColor(255, 255, 255, 0))

        painter.setBrush(QBrush(spec_grad))
        painter.drawEllipse(QPointF(light_x, light_y), r * 0.48, r * 0.48)

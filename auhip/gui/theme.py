# auhip GUI Theme — Dual-Mode Design System
# Light:  Claude's warm cream canvas, Apple's minimal typography, Notion's clean borders
# Dark:   Deep charcoal-navy canvas with electric cyan accent and neon glow highlights

# ── Light Theme ───────────────────────────────────────────────────────────────

LIGHT_COLORS = {
    # Surfaces
    "bg":            "#F8F5F0",
    "surface":       "#FFFFFF",
    "panel":         "#FFFFFF",
    "panel_soft":    "#F0EBE3",
    "nav":           "#141413",
    "dark_card":     "#1C1A18",

    # Borders
    "border":        "#E6DFD8",
    "border_soft":   "#EBE6DF",
    "border_dark":   "#2E2B27",

    # Accent
    "accent":        "#CC785C",
    "accent_hover":  "#A9583E",
    "accent_dim":    "#F0E8E2",
    "accent_yellow": "#E8A55A",

    # Text on light
    "text":          "#141413",
    "text_body":     "#3D3D3A",
    "text_muted":    "#6C6A64",
    "text_soft":     "#8E8B82",

    # Text on dark
    "text_on_dark":       "#FAF9F5",
    "text_on_dark_muted": "#A09D96",

    # Semantic
    "success": "#5DB872",
    "warning": "#E8A55A",
    "danger":  "#C64545",

    # Legacy aliases
    "processing": "#CC785C",
    "shutdown":   "#C64545",
}

# ── Dark Theme ────────────────────────────────────────────────────────────────

DARK_COLORS = {
    # Surfaces
    "bg":            "#0D0F14",
    "surface":       "#141720",
    "panel":         "#1A1E2B",
    "panel_soft":    "#1F2435",
    "nav":           "#0A0C11",
    "dark_card":     "#0D0F14",

    # Borders
    "border":        "#2A2F3E",
    "border_soft":   "#232840",
    "border_dark":   "#3D4460",

    # Accent — electric cyan/teal
    "accent":        "#00D4FF",
    "accent_hover":  "#00A8CC",
    "accent_dim":    "#0D2535",
    "accent_yellow": "#F5A623",

    # Text on dark surfaces
    "text":          "#E8EAF0",
    "text_body":     "#C0C4D0",
    "text_muted":    "#7B82A0",
    "text_soft":     "#555B72",

    # Text on dark (same as text for dark mode)
    "text_on_dark":       "#E8EAF0",
    "text_on_dark_muted": "#7B82A0",

    # Semantic
    "success": "#00E676",
    "warning": "#F5A623",
    "danger":  "#FF4444",

    # Legacy aliases
    "processing": "#00D4FF",
    "shutdown":   "#FF4444",
}

# ── Active Theme (mutable reference) ─────────────────────────────────────────

# Start in light mode
COLORS = LIGHT_COLORS.copy()
_dark_mode_active = False


def get_dark_mode() -> bool:
    return _dark_mode_active


def set_theme(dark: bool):
    """Switch the active COLORS dict between light and dark. Returns the new palette."""
    global COLORS, _dark_mode_active
    _dark_mode_active = dark
    source = DARK_COLORS if dark else LIGHT_COLORS
    COLORS.clear()
    COLORS.update(source)
    return COLORS


# ── State Colors ──────────────────────────────────────────────────────────────

LIGHT_STATE_COLORS = {
    "STANDBY":           "#8E8B82",
    "SNAP_DETECTED":     "#E8A55A",
    "WAITING_WAKE_WORD": "#CC785C",
    "VOICE_MODE":        "#141413",
    "CAMERA_MODE":       "#5DB872",
    "CONTROL_MODE":      "#3B82F6",
    "PROCESSING":        "#CC785C",
    "SLEEP":             "#8E8B82",
    "SHUTDOWN":          "#C64545",
    "COMMAND_MODE":      "#141413",
}

DARK_STATE_COLORS = {
    "STANDBY":           "#555B72",
    "SNAP_DETECTED":     "#F5A623",
    "WAITING_WAKE_WORD": "#00D4FF",
    "VOICE_MODE":        "#E8EAF0",
    "CAMERA_MODE":       "#00E676",
    "CONTROL_MODE":      "#4A9EFF",
    "PROCESSING":        "#00D4FF",
    "SLEEP":             "#555B72",
    "SHUTDOWN":          "#FF4444",
    "COMMAND_MODE":      "#E8EAF0",
}

STATE_COLORS = LIGHT_STATE_COLORS.copy()


def _sync_state_colors(dark: bool):
    source = DARK_STATE_COLORS if dark else LIGHT_STATE_COLORS
    STATE_COLORS.clear()
    STATE_COLORS.update(source)


# ── Response Colors ───────────────────────────────────────────────────────────

RESPONSE_COLORS = {
    "info":     "#6C6A64",
    "success":  "#5DB872",
    "warning":  "#E8A55A",
    "response": "#141413",
    "shutdown": "#C64545",
    "greeting": "#CC785C",
}

DARK_RESPONSE_COLORS = {
    "info":     "#7B82A0",
    "success":  "#00E676",
    "warning":  "#F5A623",
    "response": "#E8EAF0",
    "shutdown": "#FF4444",
    "greeting": "#00D4FF",
}

# ── Stylesheet Builder ────────────────────────────────────────────────────────

def build_stylesheet(dark: bool = False) -> str:
    c = DARK_COLORS if dark else LIGHT_COLORS
    return f"""
QMainWindow, QWidget {{
    background-color: {c['bg']};
    color: {c['text']};
    font-family: 'Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Helvetica', 'sans-serif';
    font-size: 14px;
}}
QFrame {{
    background-color: {c['panel']};
    border: 1px solid {c['border']};
    border-radius: 12px;
}}
QLabel {{
    background-color: transparent;
    border: none;
    color: {c['text']};
}}
QTextEdit {{
    background-color: {c['panel']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    color: {c['text_body']};
    padding: 12px;
    font-size: 14px;
    line-height: 1.55;
    selection-background-color: {c['accent_dim']};
    selection-color: {c['text']};
}}
QListWidget {{
    background-color: transparent;
    border: none;
    color: {c['text_body']};
    font-size: 14px;
}}
QListWidget::item {{
    padding: 10px 0;
    border-bottom: 1px solid {c['border_soft']};
}}
QListWidget::item:selected {{
    background: transparent;
    color: {c['accent']};
}}
QPushButton {{
    background-color: {c['accent']};
    border: none;
    border-radius: 8px;
    color: {'#FFFFFF' if not dark else '#0D0F14'};
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {c['accent_hover']};
}}
QPushButton:pressed {{
    background-color: {c['accent_hover']};
    opacity: 0.8;
}}
QCheckBox {{
    color: {c['text_muted']};
    font-size: 13px;
    spacing: 6px;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 5px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {c['border']};
    min-height: 20px;
    border-radius: 2px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QSplitter::handle {{
    background: transparent;
}}
"""


# Default stylesheet (light mode on startup)
STYLESHEET = build_stylesheet(dark=False)

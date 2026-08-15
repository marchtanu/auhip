# auhip GUI Theme — Dual-Mode Premium Minimal Design System
# Light:  Crisp white canvas, monochrome aesthetic, flat modern look
# Dark:   Deep black void, monochrome white accent, high-contrast flat layout

# ── Light Theme ───────────────────────────────────────────────────────────────

LIGHT_COLORS = {
    # Surfaces
    "bg":            "#FFFFFF",
    "surface":       "#FAFAFA",
    "panel":         "#FAFAFA",
    "panel_soft":    "#F4F4F5",
    "nav":           "#FFFFFF",
    "dark_card":     "#18181B",

    # Borders - subtle
    "border":        "#F4F4F5",
    "border_soft":   "#FAFAFA",
    "border_dark":   "#E4E4E7",

    # Accent
    "accent":        "#000000",
    "accent_hover":  "#3F3F46",
    "accent_dim":    "#F4F4F5",
    "accent_yellow": "#EAB308",

    # Text on light
    "text":          "#09090B",
    "text_body":     "#3F3F46",
    "text_muted":    "#71717A",
    "text_soft":     "#A1A1AA",

    # Text on dark
    "text_on_dark":       "#FAFAFA",
    "text_on_dark_muted": "#A1A1AA",

    # Semantic
    "success": "#10B981",
    "warning": "#F59E0B",
    "danger":  "#EF4444",

    # Legacy aliases
    "processing": "#000000",
    "shutdown":   "#EF4444",
}

# ── Dark Theme ────────────────────────────────────────────────────────────────

DARK_COLORS = {
    # Surfaces
    "bg":            "#000000",
    "surface":       "#09090B",
    "panel":         "#09090B",
    "panel_soft":    "#18181B",
    "nav":           "#000000",
    "dark_card":     "#09090B",

    # Borders
    "border":        "#18181B",
    "border_soft":   "#09090B",
    "border_dark":   "#27272A",

    # Accent 
    "accent":        "#FFFFFF",
    "accent_hover":  "#D4D4D8",
    "accent_dim":    "#18181B",
    "accent_yellow": "#F59E0B",

    # Text on dark surfaces
    "text":          "#FAFAFA",
    "text_body":     "#D4D4D8",
    "text_muted":    "#A1A1AA",
    "text_soft":     "#71717A",

    # Text on dark
    "text_on_dark":       "#FAFAFA",
    "text_on_dark_muted": "#71717A",

    # Semantic
    "success": "#10B981",
    "warning": "#F59E0B",
    "danger":  "#EF4444",

    # Legacy aliases
    "processing": "#FFFFFF",
    "shutdown":   "#EF4444",
}

# ── Active Theme (mutable reference) ─────────────────────────────────────────

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
    "STANDBY":           "#A1A1AA",
    "SNAP_DETECTED":     "#F59E0B",
    "WAITING_WAKE_WORD": "#000000",
    "VOICE_MODE":        "#09090B",
    "CAMERA_MODE":       "#10B981",
    "CONTROL_MODE":      "#3B82F6",
    "PROCESSING":        "#000000",
    "SLEEP":             "#A1A1AA",
    "SHUTDOWN":          "#EF4444",
    "COMMAND_MODE":      "#09090B",
}

DARK_STATE_COLORS = {
    "STANDBY":           "#71717A",
    "SNAP_DETECTED":     "#F59E0B",
    "WAITING_WAKE_WORD": "#FFFFFF",
    "VOICE_MODE":        "#FAFAFA",
    "CAMERA_MODE":       "#10B981",
    "CONTROL_MODE":      "#3B82F6",
    "PROCESSING":        "#FFFFFF",
    "SLEEP":             "#71717A",
    "SHUTDOWN":          "#EF4444",
    "COMMAND_MODE":      "#FAFAFA",
}

STATE_COLORS = LIGHT_STATE_COLORS.copy()


def _sync_state_colors(dark: bool):
    source = DARK_STATE_COLORS if dark else LIGHT_STATE_COLORS
    STATE_COLORS.clear()
    STATE_COLORS.update(source)


# ── Response Colors ───────────────────────────────────────────────────────────

RESPONSE_COLORS = {
    "info":     "#71717A",
    "success":  "#10B981",
    "warning":  "#F59E0B",
    "response": "#09090B",
    "shutdown": "#EF4444",
    "greeting": "#000000",
}

DARK_RESPONSE_COLORS = {
    "info":     "#A1A1AA",
    "success":  "#10B981",
    "warning":  "#F59E0B",
    "response": "#FAFAFA",
    "shutdown": "#EF4444",
    "greeting": "#FFFFFF",
}

# ── Stylesheet Builder ────────────────────────────────────────────────────────

def build_stylesheet(dark: bool = False) -> str:
    c = DARK_COLORS if dark else LIGHT_COLORS
    return f"""
QMainWindow, QWidget {{
    background-color: {c['bg']};
    color: {c['text']};
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
}}
QFrame {{
    background-color: {c['panel']};
    border: 1px solid {c['border']};
    border-radius: 4px;
}}
QLabel {{
    background-color: transparent;
    border: none;
    color: {c['text']};
}}
QTextEdit {{
    background-color: {c['panel']};
    border: 1px solid {c['border']};
    border-radius: 4px;
    color: {c['text_body']};
    padding: 12px;
    font-size: 13px;
    line-height: 1.55;
    selection-background-color: {c['accent_dim']};
    selection-color: {c['text']};
}}
QListWidget {{
    background-color: transparent;
    border: none;
    color: {c['text_body']};
    font-size: 13px;
}}
QListWidget::item {{
    padding: 10px 0;
    border-bottom: 1px solid {c['border']};
}}
QListWidget::item:selected {{
    background: transparent;
    color: {c['accent']};
}}
QPushButton {{
    background-color: {c['accent']};
    border: none;
    border-radius: 4px;
    color: {'#FFFFFF' if not dark else '#000000'};
    padding: 7px 16px;
    font-size: 12px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {c['accent_hover']};
}}
QPushButton:pressed {{
    background-color: {c['accent_hover']};
    opacity: 0.85;
}}
QCheckBox {{
    color: {c['text_muted']};
    font-size: 12px;
    spacing: 6px;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 4px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {c['border_dark']};
    min-height: 24px;
    border-radius: 2px;
}}
QScrollBar::handle:vertical:hover {{
    background: {c['text_muted']};
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

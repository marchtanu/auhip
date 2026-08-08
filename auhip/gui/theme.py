# auhip GUI Theme — Dual-Mode Premium Design System
# Light:  Claude's warm cream canvas, Apple typography, Notion clean borders
# Dark:   Deep obsidian void, electric cyan glow accent, high-contrast HUD elements

# ── Light Theme ───────────────────────────────────────────────────────────────

LIGHT_COLORS = {
    # Surfaces
    "bg":            "#F7F6F3",
    "surface":       "#FFFFFF",
    "panel":         "#FFFFFF",
    "panel_soft":    "#F3F0EA",
    "nav":           "#18181B",
    "dark_card":     "#18181B",

    # Borders
    "border":        "#E5E2DB",
    "border_soft":   "#EFECE6",
    "border_dark":   "#27272A",

    # Accent
    "accent":        "#D96338",
    "accent_hover":  "#B84F2A",
    "accent_dim":    "#F9EFE9",
    "accent_yellow": "#EAB308",

    # Text on light
    "text":          "#18181B",
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
    "processing": "#D96338",
    "shutdown":   "#EF4444",
}

# ── Dark Theme ────────────────────────────────────────────────────────────────

DARK_COLORS = {
    # Surfaces
    "bg":            "#080A0F",
    "surface":       "#0F121A",
    "panel":         "#151924",
    "panel_soft":    "#1C2232",
    "nav":           "#05070A",
    "dark_card":     "#090C12",

    # Borders
    "border":        "#262E42",
    "border_soft":   "#1E2436",
    "border_dark":   "#374151",

    # Accent — electric cyan / neon teal
    "accent":        "#00E5FF",
    "accent_hover":  "#00B3CC",
    "accent_dim":    "#0B2838",
    "accent_yellow": "#FFB800",

    # Text on dark surfaces
    "text":          "#F4F4F5",
    "text_body":     "#D4D4D8",
    "text_muted":    "#71717A",
    "text_soft":     "#52525B",

    # Text on dark
    "text_on_dark":       "#F4F4F5",
    "text_on_dark_muted": "#71717A",

    # Semantic
    "success": "#00F59B",
    "warning": "#FFB800",
    "danger":  "#FF4D4D",

    # Legacy aliases
    "processing": "#00E5FF",
    "shutdown":   "#FF4D4D",
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
    "STANDBY":           "#71717A",
    "SNAP_DETECTED":     "#F59E0B",
    "WAITING_WAKE_WORD": "#D96338",
    "VOICE_MODE":        "#18181B",
    "CAMERA_MODE":       "#10B981",
    "CONTROL_MODE":      "#3B82F6",
    "PROCESSING":        "#D96338",
    "SLEEP":             "#71717A",
    "SHUTDOWN":          "#EF4444",
    "COMMAND_MODE":      "#18181B",
}

DARK_STATE_COLORS = {
    "STANDBY":           "#52525B",
    "SNAP_DETECTED":     "#FFB800",
    "WAITING_WAKE_WORD": "#00E5FF",
    "VOICE_MODE":        "#F4F4F5",
    "CAMERA_MODE":       "#00F59B",
    "CONTROL_MODE":      "#3B82F6",
    "PROCESSING":        "#00E5FF",
    "SLEEP":             "#52525B",
    "SHUTDOWN":          "#FF4D4D",
    "COMMAND_MODE":      "#F4F4F5",
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
    "response": "#18181B",
    "shutdown": "#EF4444",
    "greeting": "#D96338",
}

DARK_RESPONSE_COLORS = {
    "info":     "#71717A",
    "success":  "#00F59B",
    "warning":  "#FFB800",
    "response": "#F4F4F5",
    "shutdown": "#FF4D4D",
    "greeting": "#00E5FF",
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
    color: {'#FFFFFF' if not dark else '#080A0F'};
    padding: 7px 16px;
    font-size: 12px;
    font-weight: 600;
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
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {c['border']};
    min-height: 24px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical:hover {{
    background: {c['accent']};
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


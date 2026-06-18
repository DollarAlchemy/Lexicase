"""theme.py — palette tokens + a QSS builder.

Two named palettes (LIGHT, DARK). The whole UI's colors come from one of these
dicts, so:
  - changing the look is a token edit, not a hunt through the code, and
  - the v0.2 light/dark TOGGLE is just `build_qss(other_palette)` at runtime.

Design note: purple is used as the ACCENT (brand, panel headers, focus), with
dark ink for body text. Purple body text on a light field is low-contrast and
tiring to read — accent-only keeps it readable.
"""
from __future__ import annotations

LIGHT = {
    "window": "#e6e8ec",   # silver desktop
    "panel":  "#fbfbfd",   # near-white cards
    "panel2": "#eceef3",   # button surface
    "hover":  "#e1e4ea",
    "border": "#ccd1db",
    "ink":    "#20263a",   # body text — dark, high contrast
    "muted":  "#5c6478",
    "accent": "#6d28d9",   # purple — brand, headers, edges
    "topbar": "#dde0e7",
    "ticker": "#dde0e7",
}

DARK = {
    "window": "#0c0e13",
    "panel":  "#11141c",
    "panel2": "#161a24",
    "hover":  "#1b2030",
    "border": "#2a2f3d",
    "ink":    "#e9ecf4",
    "muted":  "#8b93a7",
    "accent": "#a06bff",   # purple keeps the brand identity in both themes
    "topbar": "#11141c",
    "ticker": "#11141c",
}


def build_qss(p: dict) -> str:
    """Return the application stylesheet for a palette dict."""
    return f"""
* {{ font-family: "Segoe UI", -apple-system, Roboto, Helvetica, Arial, sans-serif; }}
QMainWindow, QWidget#root {{ background: {p['window']}; }}
QLabel {{ color: {p['ink']}; }}

QFrame#topbar {{ background: {p['topbar']}; border-bottom: 1px solid {p['border']}; }}
QLabel#brand {{ font-size: 16px; font-weight: 800; color: {p['ink']}; }}
QLabel#brand b {{ color: {p['accent']}; }}
QLabel#clock {{ color: {p['muted']}; font-size: 12px; }}

QPushButton {{
    color: {p['ink']}; background: {p['panel2']}; border: 1px solid {p['border']};
    border-radius: 8px; padding: 6px 12px; font-size: 12px;
}}
QPushButton:hover {{ background: {p['hover']}; border-color: {p['accent']}; }}
QPushButton:disabled {{ color: {p['muted']}; }}

QFrame.panel {{ background: {p['panel']}; border: 1px solid {p['border']}; border-radius: 10px; }}
QLabel.panelHeader {{ color: {p['accent']}; font-size: 10px; font-weight: 800; letter-spacing: 1.2px; }}
QLabel.empty {{ color: {p['muted']}; font-size: 12px; }}
QLabel.emptyBig {{ color: {p['muted']}; font-size: 13px; }}
QLabel.caseItem {{ color: {p['ink']}; font-size: 13px; padding: 6px 8px; border-radius: 6px; }}
QLabel.caseItem:hover {{ background: {p['hover']}; }}
QLabel.activeCase {{ color: {p['ink']}; font-size: 12px; font-weight: 700; padding: 0 2px 9px; }}

QListWidget, QTreeWidget {{
    background: transparent; border: none; color: {p['ink']};
    font-size: 13px; outline: none;
}}
QListWidget::item {{ padding: 6px 8px; border-radius: 6px; margin: 1px 0; }}
QTreeWidget::item {{ padding: 4px 2px; }}
QListWidget::item:hover, QTreeWidget::item:hover {{ background: {p['hover']}; }}
QListWidget::item:selected, QTreeWidget::item:selected {{ background: {p['accent']}; color: #ffffff; }}
QHeaderView::section {{ background: transparent; border: none; color: {p['muted']}; }}

QDialog {{ background: {p['window']}; color: {p['ink']}; }}
QScrollArea {{ border: none; background: {p['window']}; }}
QScrollArea#formScroll, QWidget#formInner {{ background: {p['window']}; }}
QWidget#formInner QLabel {{ color: {p['ink']}; }}
QLineEdit, QPlainTextEdit {{
    background: {p['panel']}; color: {p['ink']}; border: 1px solid {p['border']};
    border-radius: 6px; padding: 5px 7px; font-size: 13px;
    selection-background-color: {p['accent']}; selection-color: #ffffff;
}}
QLineEdit:focus, QPlainTextEdit:focus {{ border-color: {p['accent']}; }}
QPushButton:default {{ background: {p['accent']}; color: #ffffff; border-color: {p['accent']}; }}
QPushButton:default:hover {{ background: {p['accent']}; border-color: {p['accent']}; }}

QFrame#ticker {{ background: {p['ticker']}; border-top: 1px solid {p['border']}; }}
QLabel#tickerText {{ color: {p['muted']}; font-size: 12px; }}

QSplitter::handle {{ background: transparent; }}
"""


# The palette the app uses. Change this one line (LIGHT/DARK) — the v0.2
# toggle will flip it at runtime.
ACTIVE = LIGHT

"""
Terminal text color overrides.
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal, QCoreApplication
from PyQt6.QtGui import QColor

from core.theme import COLORS, ThemeManager


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
CATEGORY_TIMESTAMPS   = "timestamps"
CATEGORY_PING         = "ping"
CATEGORY_TX_PREFIX    = "tx_prefix"
CATEGORY_TX_TEXT      = "tx_text"
CATEGORY_RX_TEXT      = "rx_text"
CATEGORY_PEER_PREFIX  = "peer_prefix"
CATEGORY_SERVER_EVENT = "server_event"
CATEGORY_SCENARIO     = "scenario"      # NEW — [SCENARIO] log lines

CATEGORY_ORDER = [
    CATEGORY_TIMESTAMPS,
    CATEGORY_PING,
    CATEGORY_TX_PREFIX,
    CATEGORY_TX_TEXT,
    CATEGORY_RX_TEXT,
    CATEGORY_PEER_PREFIX,
    CATEGORY_SERVER_EVENT,
    CATEGORY_SCENARIO,
]

CATEGORY_SOURCE = {
    CATEGORY_TIMESTAMPS:   "Timestamps",
    CATEGORY_PING:         "[PING:] output",
    CATEGORY_TX_PREFIX:    "[Transmit:] prefix",
    CATEGORY_TX_TEXT:      "Transmitted payload",
    CATEGORY_RX_TEXT:      "Received data",
    CATEGORY_PEER_PREFIX:  "[peer] prefix",
    CATEGORY_SERVER_EVENT: "Server events",
    CATEGORY_SCENARIO:     "[SCENARIO] output",
}

CATEGORY_LABELS = CATEGORY_SOURCE


def category_label(category_id: str) -> str:
    if category_id == CATEGORY_TIMESTAMPS:
        return QCoreApplication.translate("TerminalColors", "Timestamps")
    if category_id == CATEGORY_PING:
        return QCoreApplication.translate("TerminalColors", "[PING:] output")
    if category_id == CATEGORY_TX_PREFIX:
        return QCoreApplication.translate("TerminalColors", "[Transmit:] prefix")
    if category_id == CATEGORY_TX_TEXT:
        return QCoreApplication.translate("TerminalColors", "Transmitted payload")
    if category_id == CATEGORY_RX_TEXT:
        return QCoreApplication.translate("TerminalColors", "Received data")
    if category_id == CATEGORY_PEER_PREFIX:
        return QCoreApplication.translate("TerminalColors", "[peer] prefix")
    if category_id == CATEGORY_SERVER_EVENT:
        return QCoreApplication.translate("TerminalColors", "Server events")
    if category_id == CATEGORY_SCENARIO:
        return QCoreApplication.translate("TerminalColors", "[SCENARIO] output")
    return CATEGORY_SOURCE.get(category_id, category_id)


CATEGORY_PALETTE_KEY = {
    CATEGORY_TIMESTAMPS:   "accent",
    CATEGORY_PING:         "danger",
    CATEGORY_TX_PREFIX:    "ok",
    CATEGORY_TX_TEXT:      "text_dim",
    CATEGORY_RX_TEXT:      "text",
    CATEGORY_PEER_PREFIX:  "accent",
    CATEGORY_SERVER_EVENT: "warn",
    CATEGORY_SCENARIO:     "warn",        # по умолчанию — жёлтый
}


# ---------------------------------------------------------------------------
# Named colors
# ---------------------------------------------------------------------------
NAMED_COLORS: dict[str, tuple[str, str]] = {
    "purple":    ("Purple",    "#a855f7"),
    "green":     ("Green",     "#2ecc71"),
    "red":       ("Red",       "#e74c3c"),
    "gray":      ("Gray",      "#9aa0b0"),
    "white":     ("White",     "#ffffff"),
    "black":     ("Black",     "#000000"),
    "beige":     ("Beige",     "#d4b499"),
    "turquoise": ("Turquoise", "#4ecdc4"),
    "orange":    ("Orange",    "#e88a4a"),
    "graphite":  ("Graphite",  "#5a5a63"),
    "sand":      ("Sand",      "#c9a76a"),
    "gold":      ("Gold",      "#e6c15c"),
    "coral":     ("Coral",     "#e87a70"),
    "mint":      ("Mint",      "#7bd9a4"),
    "navy":      ("Navy",      "#3a5680"),
    "crimson":   ("Crimson",   "#e63976"),
}

NAMED_COLOR_ORDER = list(NAMED_COLORS.keys())


def color_label(color_id: str) -> str:
    if color_id == "purple":    return QCoreApplication.translate("TerminalColors", "Purple")
    if color_id == "green":     return QCoreApplication.translate("TerminalColors", "Green")
    if color_id == "red":       return QCoreApplication.translate("TerminalColors", "Red")
    if color_id == "gray":      return QCoreApplication.translate("TerminalColors", "Gray")
    if color_id == "white":     return QCoreApplication.translate("TerminalColors", "White")
    if color_id == "black":     return QCoreApplication.translate("TerminalColors", "Black")
    if color_id == "beige":     return QCoreApplication.translate("TerminalColors", "Beige")
    if color_id == "turquoise": return QCoreApplication.translate("TerminalColors", "Turquoise")
    if color_id == "orange":    return QCoreApplication.translate("TerminalColors", "Orange")
    if color_id == "graphite":  return QCoreApplication.translate("TerminalColors", "Graphite")
    if color_id == "sand":      return QCoreApplication.translate("TerminalColors", "Sand")
    if color_id == "gold":      return QCoreApplication.translate("TerminalColors", "Gold")
    if color_id == "coral":     return QCoreApplication.translate("TerminalColors", "Coral")
    if color_id == "mint":      return QCoreApplication.translate("TerminalColors", "Mint")
    if color_id == "navy":      return QCoreApplication.translate("TerminalColors", "Navy")
    if color_id == "crimson":   return QCoreApplication.translate("TerminalColors", "Crimson")
    return NAMED_COLORS.get(color_id, (color_id,))[0]


def color_hex(color_id: str) -> str:
    return NAMED_COLORS[color_id][1]


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------
class TerminalColorManager(QObject):
    colors_changed = pyqtSignal()

    _instance = None

    @classmethod
    def instance(cls) -> "TerminalColorManager":
        if cls._instance is None:
            cls._instance = TerminalColorManager()
        return cls._instance

    def __init__(self):
        super().__init__()
        self._overrides: dict[str, str] = {}
        ThemeManager.instance().theme_changed.connect(self._on_theme_changed)

    # -- queries -----------------------------------------------------------
    def get_color_id(self, category_id: str) -> str | None:
        return self._overrides.get(category_id)

    def get_qcolor(self, category_id: str) -> QColor:
        override = self._overrides.get(category_id)
        if override is not None:
            return QColor(NAMED_COLORS[override][1])
        palette_key = CATEGORY_PALETTE_KEY[category_id]
        return QColor(COLORS[palette_key])

    def is_color_taken(self, color_id: str) -> str | None:
        for cat, cid in self._overrides.items():
            if cid == color_id:
                return cat
        return None

    # -- mutations ---------------------------------------------------------
    def set_color(self, category_id: str, color_id: str) -> None:
        if category_id not in CATEGORY_ORDER:
            return
        if color_id not in NAMED_COLORS:
            return
        holder = self.is_color_taken(color_id)
        if holder is not None and holder != category_id:
            del self._overrides[holder]
        self._overrides[category_id] = color_id
        self.colors_changed.emit()

    def clear_color(self, category_id: str) -> None:
        if category_id in self._overrides:
            del self._overrides[category_id]
            self.colors_changed.emit()

    def reset_all(self) -> None:
        if self._overrides:
            self._overrides.clear()
            self.colors_changed.emit()

    def _on_theme_changed(self, _theme_id: str) -> None:
        self.colors_changed.emit()


def get_terminal_color_manager() -> TerminalColorManager:
    return TerminalColorManager.instance()
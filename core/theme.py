"""
XYrminal theme — palette system + global QSS.

Exposes:
    apply_theme(app)       — install stylesheet on QApplication
    refresh_qss()          — rebuild stylesheet (e.g. after scale change)
    COLORS                 — ACTIVE palette (dict)
    ThemeManager           — singleton with `theme_changed(str)` signal
    set_theme(theme_id)    — switch palette (or SYSTEM/CUSTOM), re-apply QSS
    current_theme_id()     — active palette id (never 'system')
    current_theme_choice() — what the user picked
    available_themes()     — [(id, label), ...] for menus
    theme_icon(theme_id)   — QIcon for the theme menu
    ToggleButton           — on/off button that follows the active palette
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal, Qt, QPointF, QSettings
from PyQt6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QPolygonF, QGuiApplication,
)
from PyQt6.QtWidgets import QPushButton, QApplication

from core.ui_scale import ui_scale, scale_changed_signal
from core.custom_theme import (
    CUSTOM_THEME_ID,
    load_custom_palette,
    has_custom_palette,
    default_custom_palette,
)


PALETTES: dict[str, dict] = {

    "purple": {
        "label":           "Purple",
        "theme_bg":        "#a855f7",
        "bg_root":         "#1a1225",
        "bg_panel":        "#241833",
        "bg_input":        "#2c1e3f",
        "bg_button":       "#36264b",
        "bg_button_hover": "#453359",
        "accent":          "#a855f7",
        "accent_dim":      "#7a3fb8",
        "accent_text":     "#ffffff",
        "ok":              "#2ecc71",
        "ok_hover":        "#27ae60",
        "danger":          "#e74c3c",
        "danger_hover":    "#c0392b",
        "warn":            "#f1c40f",
        "text":            "#e6dcf5",
        "text_dim":        "#a395b8",
        "text_muted":      "#6b5f7d",
        "border":          "#3d2f52",
        "border_focus":    "#a855f7",
        "tx_prefix":       "#2ecc71",
        "tx_text":         "#a395b8",
    },

    "gray": {
        "label":           "Gray",
        "theme_bg":        "#9aa0b0",
        "bg_root":         "#1a1a1c",
        "bg_panel":        "#232326",
        "bg_input":        "#2b2b2f",
        "bg_button":       "#35353a",
        "bg_button_hover": "#424247",
        "accent":          "#9aa0b0",
        "accent_dim":      "#6e7382",
        "accent_text":     "#ffffff",
        "ok":              "#2ecc71",
        "ok_hover":        "#27ae60",
        "danger":          "#e74c3c",
        "danger_hover":    "#c0392b",
        "warn":            "#f1c40f",
        "text":            "#e4e4e6",
        "text_dim":        "#9d9da3",
        "text_muted":      "#6a6a70",
        "border":          "#38383d",
        "border_focus":    "#9aa0b0",
        "tx_prefix":       "#2ecc71",
        "tx_text":         "#9d9da3",
    },

    "white": {
        "label":           "White",
        "theme_bg":        "#ffffff",
        "bg_root":         "#f4f4f6",
        "bg_panel":        "#ffffff",
        "bg_input":        "#fafafb",
        "bg_button":       "#e8e8ec",
        "bg_button_hover": "#dcdce0",
        "accent":          "#1a1a1c",
        "accent_dim":      "#404044",
        "accent_text":     "#ffffff",
        "ok":              "#2ecc71",
        "ok_hover":        "#27ae60",
        "danger":          "#e74c3c",
        "danger_hover":    "#c0392b",
        "warn":            "#e6b800",
        "text":            "#1a1a1c",
        "text_dim":        "#555558",
        "text_muted":      "#8a8a8e",
        "border":          "#c8c8ce",
        "border_focus":    "#1a1a1c",
        "tx_prefix":       "#2ecc71",
        "tx_text":         "#555558",
    },

    "black": {
        "label":           "Black",
        "theme_bg":        "#000000",
        "bg_root":         "#000000",
        "bg_panel":        "#0a0a0c",
        "bg_input":        "#131315",
        "bg_button":       "#1c1c1f",
        "bg_button_hover": "#28282c",
        "accent":          "#b0b0b8",
        "accent_dim":      "#7c7c85",
        "accent_text":     "#0a0a0c",
        "ok":              "#2ecc71",
        "ok_hover":        "#27ae60",
        "danger":          "#e74c3c",
        "danger_hover":    "#c0392b",
        "warn":            "#f1c40f",
        "text":            "#dadade",
        "text_dim":        "#94949c",
        "text_muted":      "#616168",
        "border":          "#27272e",
        "border_focus":    "#b0b0b8",
        "tx_prefix":       "#2ecc71",
        "tx_text":         "#94949c",
    },

    "beige": {
        "label":           "Beige",
        "theme_bg":        "#d4b499",
        "bg_root":         "#241d16",
        "bg_panel":        "#2f261d",
        "bg_input":        "#392e23",
        "bg_button":       "#44382b",
        "bg_button_hover": "#534534",
        "accent":          "#d4b499",
        "accent_dim":      "#a8886d",
        "accent_text":     "#241d16",
        "ok":              "#2ecc71",
        "ok_hover":        "#27ae60",
        "danger":          "#e74c3c",
        "danger_hover":    "#c0392b",
        "warn":            "#f1c40f",
        "text":            "#f0e6d8",
        "text_dim":        "#b8a890",
        "text_muted":      "#82725c",
        "border":          "#4a3d2d",
        "border_focus":    "#d4b499",
        "tx_prefix":       "#2ecc71",
        "tx_text":         "#b8a890",
    },

    "turquoise_orange": {
        "label":           "Turquoise-Orange",
        "theme_bg":        "#ff8c42",
        "bg_root":         "#ff8c42",
        "bg_panel":        "#ff9b55",
        "bg_input":        "#ffa768",
        "bg_button":       "#ffb17a",
        "bg_button_hover": "#ffc08f",
        "accent":          "#00b8a9",
        "accent_dim":      "#00958a",
        "accent_text":     "#ffffff",
        "ok":              "#2ecc71",
        "ok_hover":        "#27ae60",
        "danger":          "#e74c3c",
        "danger_hover":    "#c0392b",
        "warn":            "#f1c40f",
        "text":            "#1a0d05",
        "text_dim":        "#4a2a15",
        "text_muted":      "#7a4a2a",
        "border":          "#e67a2e",
        "border_focus":    "#00b8a9",
        "tx_prefix":       "#2ecc71",
        "tx_text":         "#4a2a15",
    },

    "graphite_sand": {
        "label":           "Graphite-Sand",
        "theme_bg":        "#3a3a40",
        "bg_root":         "#1a1a1c",
        "bg_panel":        "#232326",
        "bg_input":        "#2b2b2f",
        "bg_button":       "#34343a",
        "bg_button_hover": "#42424a",
        "accent":          "#d4b483",
        "accent_dim":      "#a88c62",
        "accent_text":     "#1a1a1c",
        "ok":              "#2ecc71",
        "ok_hover":        "#27ae60",
        "danger":          "#e74c3c",
        "danger_hover":    "#c0392b",
        "warn":            "#f1c40f",
        "text":            "#ece7dd",
        "text_dim":        "#aea68f",
        "text_muted":      "#787260",
        "border":          "#3a3a40",
        "border_focus":    "#d4b483",
        "tx_prefix":       "#2ecc71",
        "tx_text":         "#aea68f",
    },

    "purple_gold": {
        "label":           "Purple-Gold",
        "theme_bg":        "#a855f7",
        "bg_root":         "#1a1225",
        "bg_panel":        "#241833",
        "bg_input":        "#2c1e3f",
        "bg_button":       "#36264b",
        "bg_button_hover": "#453359",
        "accent":          "#e6c15c",
        "accent_dim":      "#b89841",
        "accent_text":     "#1a1225",
        "ok":              "#2ecc71",
        "ok_hover":        "#27ae60",
        "danger":          "#e74c3c",
        "danger_hover":    "#c0392b",
        "warn":            "#f1c40f",
        "text":            "#ede5f5",
        "text_dim":        "#b1a3c4",
        "text_muted":      "#7d7194",
        "border":          "#3d2f52",
        "border_focus":    "#e6c15c",
        "tx_prefix":       "#2ecc71",
        "tx_text":         "#b1a3c4",
    },

    "coral_mint": {
        "label":           "Coral-Mint",
        "theme_bg":        "#ff7a70",
        "bg_root":         "#ff7a70",
        "bg_panel":        "#ff8a80",
        "bg_input":        "#ff9a90",
        "bg_button":       "#ffaaa0",
        "bg_button_hover": "#ffb8b0",
        "accent":          "#2eb894",
        "accent_dim":      "#23947a",
        "accent_text":     "#ffffff",
        "ok":              "#2ecc71",
        "ok_hover":        "#27ae60",
        "danger":          "#e74c3c",
        "danger_hover":    "#c0392b",
        "warn":            "#f1c40f",
        "text":            "#2a0a0a",
        "text_dim":        "#5c1e1e",
        "text_muted":      "#8f4040",
        "border":          "#e65a50",
        "border_focus":    "#2eb894",
        "tx_prefix":       "#2ecc71",
        "tx_text":         "#5c1e1e",
    },

    "navy_crimson": {
        "label":           "Navy-Crimson",
        "theme_bg":        "#253353",
        "bg_root":         "#0e1626",
        "bg_panel":        "#162036",
        "bg_input":        "#1d2a44",
        "bg_button":       "#253353",
        "bg_button_hover": "#324266",
        "accent":          "#e63976",
        "accent_dim":      "#b82a5c",
        "accent_text":     "#ffffff",
        "ok":              "#2ecc71",
        "ok_hover":        "#27ae60",
        "danger":          "#e74c3c",
        "danger_hover":    "#c0392b",
        "warn":            "#f1c40f",
        "text":            "#e0e6f0",
        "text_dim":        "#95a3c0",
        "text_muted":      "#5f6c88",
        "border":          "#28385e",
        "border_focus":    "#e63976",
        "tx_prefix":       "#2ecc71",
        "tx_text":         "#95a3c0",
    },
}

DEFAULT_THEME_ID = "purple"

SYSTEM_THEME_ID    = "system"
SYSTEM_LIGHT_THEME = "white"
SYSTEM_DARK_THEME  = "black"

TWO_COLOR_THEMES = {
    "turquoise_orange",
    "graphite_sand",
    "purple_gold",
    "coral_mint",
    "navy_crimson",
}


COLORS: dict = {
    k: v for k, v in PALETTES[DEFAULT_THEME_ID].items()
    if k not in ("label", "theme_bg")
}


def system_theme_id() -> str:
    app = QGuiApplication.instance()
    if app is None:
        return SYSTEM_DARK_THEME

    try:
        hints = app.styleHints()
        scheme = hints.colorScheme()
    except AttributeError:
        return SYSTEM_DARK_THEME

    if scheme == Qt.ColorScheme.Light:
        return SYSTEM_LIGHT_THEME
    if scheme == Qt.ColorScheme.Dark:
        return SYSTEM_DARK_THEME
    return SYSTEM_DARK_THEME


class _ThemeTranslator(QObject):
    pass


_theme_tr = _ThemeTranslator()


def _tr(source: str) -> str:
    return _theme_tr.tr(source)


class ThemeManager(QObject):
    theme_changed = pyqtSignal(str)

    _instance = None

    @classmethod
    def instance(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = ThemeManager()
        return cls._instance

    def __init__(self):
        super().__init__()
        self._choice_id = DEFAULT_THEME_ID
        self._current_id = DEFAULT_THEME_ID

        app = QGuiApplication.instance()
        if app is not None:
            try:
                app.styleHints().colorSchemeChanged.connect(
                    self._on_os_scheme_changed
                )
            except AttributeError:
                pass

        try:
            scale_changed_signal().connect(self._on_ui_scale_changed)
        except Exception:
            pass

    # -- public ------------------------------------------------------------
    def current_id(self) -> str:
        return self._current_id

    def choice_id(self) -> str:
        return self._choice_id

    def is_system(self) -> bool:
        return self._choice_id == SYSTEM_THEME_ID

    def is_custom(self) -> bool:
        return self._choice_id == CUSTOM_THEME_ID

    def custom_palette(self) -> dict[str, str]:
        p = load_custom_palette()
        if p is None:
            p = default_custom_palette()
        return p

    def set_theme(self, theme_id: str) -> None:
        if theme_id == SYSTEM_THEME_ID:
            self._choice_id = SYSTEM_THEME_ID
            self._apply_palette(system_theme_id())
            return

        if theme_id == CUSTOM_THEME_ID:
            self._choice_id = CUSTOM_THEME_ID
            self._apply_palette(CUSTOM_THEME_ID)
            return

        if theme_id not in PALETTES:
            return

        self._choice_id = theme_id
        self._apply_palette(theme_id)

    def restore_from_settings(self) -> None:
        s = QSettings()
        saved = s.value("ui/theme", DEFAULT_THEME_ID, type=str)

        if saved == SYSTEM_THEME_ID:
            self._choice_id = SYSTEM_THEME_ID
            self._apply_palette(system_theme_id())
        elif saved == CUSTOM_THEME_ID and has_custom_palette():
            self._choice_id = CUSTOM_THEME_ID
            self._apply_palette(CUSTOM_THEME_ID)
        elif saved in PALETTES:
            self._choice_id = saved
            self._apply_palette(saved)
        else:
            self._choice_id = DEFAULT_THEME_ID
            self._apply_palette(DEFAULT_THEME_ID)

    # -- internal ----------------------------------------------------------
    def _apply_palette(self, theme_id: str) -> None:
        if theme_id == CUSTOM_THEME_ID:
            palette = self.custom_palette()
            palette = {k: v for k, v in palette.items() if k != "theme_bg"}
            marker = CUSTOM_THEME_ID
        else:
            if theme_id == self._current_id and self._choice_id != CUSTOM_THEME_ID:
                self._persist()
                return
            palette = {
                k: v for k, v in PALETTES[theme_id].items()
                if k not in ("label", "theme_bg")
            }
            marker = theme_id

        same = (palette == dict(COLORS)) and (marker == self._current_id)
        if same:
            self._persist()
            return

        COLORS.clear()
        COLORS.update(palette)
        self._current_id = marker

        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(_build_qss())
            for w in app.allWidgets():
                if isinstance(w, ToggleButton):
                    w.refresh_style()

        self._persist()
        self.theme_changed.emit(marker)

    def _persist(self) -> None:
        QSettings().setValue("ui/theme", self._choice_id)

    def _on_os_scheme_changed(self, _scheme) -> None:
        if not self.is_system():
            return
        self._apply_palette(system_theme_id())

    def _on_ui_scale_changed(self, _scale: float) -> None:
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(_build_qss())
            for w in app.allWidgets():
                if isinstance(w, ToggleButton):
                    w.refresh_style()


def set_theme(theme_id: str) -> None:
    ThemeManager.instance().set_theme(theme_id)


def current_theme_id() -> str:
    return ThemeManager.instance().current_id()


def current_theme_choice() -> str:
    return ThemeManager.instance().choice_id()


def available_themes() -> list[tuple[str, str]]:
    return [
        (SYSTEM_THEME_ID,    _tr("System")),
        ("purple",           _tr("Purple")),
        ("gray",             _tr("Gray")),
        ("white",            _tr("White")),
        ("black",            _tr("Black")),
        ("beige",            _tr("Beige")),
        ("turquoise_orange", _tr("Turquoise-Orange")),
        ("graphite_sand",    _tr("Graphite-Sand")),
        ("purple_gold",      _tr("Purple-Gold")),
        ("coral_mint",       _tr("Coral-Mint")),
        ("navy_crimson",     _tr("Navy-Crimson")),
    ]


def theme_icon(theme_id: str, size: int = 14) -> QIcon:
    if theme_id == SYSTEM_THEME_ID:
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)

        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        half = size // 2
        p.fillRect(0, 0, half, size, QColor("#f0f0f0"))
        p.fillRect(half, 0, size - half, size, QColor("#1a1a1c"))
        p.setPen(QColor("#888888"))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(0, 0, size - 1, size - 1)
        p.end()
        return QIcon(pix)

    if theme_id == CUSTOM_THEME_ID:
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        half = size // 2
        p.fillRect(0, 0, half, half, QColor("#e74c3c"))
        p.fillRect(half, 0, size - half, half, QColor("#f1c40f"))
        p.fillRect(0, half, half, size - half, QColor("#2ecc71"))
        p.fillRect(half, half, size - half, size - half, QColor("#3498db"))
        p.setPen(QColor("#888888"))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(0, 0, size - 1, size - 1)
        p.end()
        return QIcon(pix)

    palette = PALETTES.get(theme_id)
    if palette is None:
        pix = QPixmap(size, size)
        pix.fill(QColor("#888888"))
        return QIcon(pix)

    accent = palette.get("accent", "#888888")
    theme_bg = palette.get("theme_bg", accent)

    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, False)

    if theme_id in TWO_COLOR_THEMES:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(accent))
        p.drawPolygon(QPolygonF([
            QPointF(0, 0),
            QPointF(size, 0),
            QPointF(size, size),
        ]))
        p.setBrush(QColor(theme_bg))
        p.drawPolygon(QPolygonF([
            QPointF(0, 0),
            QPointF(0, size),
            QPointF(size, size),
        ]))
    else:
        p.fillRect(0, 0, size, size, QColor(accent))

    p.end()
    return QIcon(pix)


class ToggleButton(QPushButton):
    toggled_state = pyqtSignal(bool)

    def __init__(self, text: str, *, on: bool = False, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setChecked(on)
        self._refresh_style()
        self.toggled.connect(self._on_toggled)

    def _on_toggled(self, checked: bool) -> None:
        self._refresh_style()
        self.toggled_state.emit(checked)

    def refresh_style(self) -> None:
        self._refresh_style()

    def _refresh_style(self) -> None:
        if self.isChecked():
            bg, hover = COLORS["ok"], COLORS["ok_hover"]
        else:
            bg, hover = COLORS["danger"], COLORS["danger_hover"]

        sc = ui_scale()
        f = lambda v: max(1, int(round(v * sc)))

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: #ffffff;
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: {f(5)}px {f(12)}px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
            QPushButton:pressed {{ background-color: {bg}; }}
        """)


def _build_qss() -> str:
    c = COLORS
    sc = ui_scale()
    f = lambda v: max(1, int(round(v * sc)))

    return f"""
    /* ---------- base ---------- */
    QWidget {{
        background-color: {c['bg_root']};
        color: {c['text']};
        font-family: "Consolas", "Menlo", "DejaVu Sans Mono", monospace;
        font-size: {f(12)}px;
    }}

    /* ---------- menu bar ---------- */
    QMenuBar {{
        background-color: {c['bg_panel']};
        color: {c['text']};
        border-bottom: 1px solid {c['border']};
        padding: 2px 4px;
    }}
    QMenuBar::item {{
        background: transparent;
        padding: {f(6)}px {f(12)}px;
        border-radius: 4px;
    }}
    QMenuBar::item:selected {{
        background-color: {c['accent']};
        color: {c['accent_text']};
    }}
    QMenuBar::item:pressed {{
        background-color: {c['accent_dim']};
    }}

    /* ---------- menus ---------- */
    QMenu {{
        background-color: {c['bg_panel']};
        color: {c['text']};
        border: 1px solid {c['border']};
        padding: 4px 0;
    }}
    QMenu::item {{
        padding: {f(6)}px {f(28)}px {f(6)}px {f(24)}px;
        background: transparent;
    }}
    QMenu::item:selected {{
        background-color: {c['accent']};
        color: {c['accent_text']};
    }}
    QMenu::item:disabled {{
        color: {c['text_muted']};
    }}
    QMenu::item:checked {{
        background-color: {c['accent_dim']};
        color: {c['accent_text']};
        font-weight: 700;
    }}
    QMenu::item:checked:selected {{
        background-color: {c['accent']};
        color: {c['accent_text']};
    }}
    QMenu::separator {{
        height: 1px;
        background: {c['border']};
        margin: 4px 8px;
    }}
    QMenu::indicator {{
        width: 14px;
        height: 14px;
        left: 6px;
    }}
    QMenu::indicator:checked {{
        background-color: {c['accent']};
        border: 1px solid {c['accent']};
        border-radius: 2px;
    }}
    QMenu::indicator:unchecked {{
        background-color: {c['bg_input']};
        border: 1px solid {c['border']};
        border-radius: 2px;
    }}

    /* ---------- group boxes ---------- */
    QGroupBox {{
        background-color: {c['bg_panel']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        margin-top: {f(14)}px;
        padding-top: {f(10)}px;
        font-weight: 600;
        color: {c['text_dim']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 10px;
        padding: 0 6px;
        background-color: {c['bg_panel']};
        color: {c['accent']};
    }}

    /* ---------- tabs ---------- */
    QTabWidget::pane {{
        border: 1px solid {c['border']};
        background-color: {c['bg_root']};
        top: -1px;
    }}
    QTabBar::tab {{
        background-color: {c['bg_button']};
        color: {c['text_dim']};
        padding: {f(10)}px {f(20)}px;
        border: 1px solid {c['border']};
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 2px;
        font-weight: 600;
        font-size: {f(13)}px;
        min-width: {f(60)}px;
    }}
    QTabBar::tab:selected {{
        background-color: {c['accent']};
        color: {c['accent_text']};
    }}
    QTabBar::tab:hover:!selected {{
        background-color: {c['bg_button_hover']};
    }}

    /* ---------- buttons ---------- */
    QPushButton {{
        background-color: {c['bg_button']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 4px;
        padding: {f(5)}px {f(12)}px;
        font-weight: 600;
    }}
    QPushButton:hover {{ background-color: {c['bg_button_hover']}; }}
    QPushButton:pressed {{ background-color: {c['accent_dim']}; }}
    QPushButton:disabled {{
        background-color: {c['bg_root']};
        color: {c['text_muted']};
        border-color: {c['bg_root']};
    }}

    QPushButton[btnStyle="ok"] {{
        background-color: {c['ok']};
        color: #fff;
    }}
    QPushButton[btnStyle="ok"]:hover {{ background-color: {c['ok_hover']}; }}
    QPushButton[btnStyle="ok"]:disabled {{
        background-color: {c['bg_root']}; color: {c['text_muted']};
    }}

    QPushButton[btnStyle="danger"] {{
        background-color: {c['danger']};
        color: #fff;
    }}
    QPushButton[btnStyle="danger"]:hover {{ background-color: {c['danger_hover']}; }}
    QPushButton[btnStyle="danger"]:disabled {{
        background-color: {c['bg_root']}; color: {c['text_muted']};
    }}

    QPushButton[btnStyle="accent"] {{
        background-color: {c['accent']};
        color: {c['accent_text']};
    }}
    QPushButton[btnStyle="accent"]:hover {{ background-color: {c['accent_dim']}; }}

    QPushButton[btnStyle="macro"] {{
        background-color: {c['bg_button']};
        color: {c['text_dim']};
        border: 1px solid {c['border']};
        border-radius: 3px;
        padding: {f(1)}px {f(6)}px;
        font-weight: 600;
        font-size: {f(11)}px;
    }}
    QPushButton[btnStyle="macro"]:hover {{
        background-color: {c['bg_button_hover']};
        color: {c['text']};
    }}
    QPushButton[btnStyle="macro"]:pressed {{
        background-color: {c['accent_dim']};
        color: {c['accent_text']};
    }}
    QPushButton[btnStyle="macro"]:disabled {{
        background-color: {c['bg_root']};
        color: {c['text_muted']};
        border-color: {c['bg_root']};
    }}

    /* ---------- inputs ---------- */
    QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {{
        background-color: {c['bg_input']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 4px;
        padding: {f(4)}px {f(8)}px;
        selection-background-color: {c['accent']};
    }}
    QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 1px solid {c['border_focus']};
    }}
    QComboBox::drop-down {{
        border: none;
        width: {f(20)}px;
    }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {c['text_dim']};
        margin-right: 6px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {c['bg_input']};
        color: {c['text']};
        selection-background-color: {c['accent']};
        border: 1px solid {c['border']};
        outline: none;
    }}

    /* ---------- terminal ---------- */
    QPlainTextEdit, QTextBrowser {{
        background-color: {c['bg_input']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 4px;
        padding: {f(6)}px;
        selection-background-color: {c['accent']};
        font-family: "Consolas", "Menlo", "DejaVu Sans Mono", monospace;
        font-size: {f(12)}px;
    }}

    /* ---------- scrollbars ---------- */
    QScrollBar:vertical {{
        background: {c['bg_root']};
        width: {f(12)}px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {c['border']};
        min-height: 20px;
        border-radius: 6px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {c['accent_dim']}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

    QScrollBar:horizontal {{
        background: {c['bg_root']};
        height: {f(12)}px;
    }}
    QScrollBar::handle:horizontal {{
        background: {c['border']};
        min-width: 20px;
        border-radius: 6px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {c['accent_dim']}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

    /* ---------- labels ---------- */
    QLabel {{ background: transparent; }}

    QLabel[role="info"] {{
        background-color: {c['bg_input']};
        border: 1px solid {c['border']};
        border-radius: 4px;
        padding: {f(4)}px {f(8)}px;
        color: {c['accent']};
        font-weight: 600;
    }}
    QLabel[role="dim"] {{ color: {c['text_dim']}; }}

    /* ---------- dialogs ---------- */
    QDialog {{
        background-color: {c['bg_root']};
    }}
    """


def refresh_qss() -> None:
    """Rebuild the app stylesheet (call after a UI-scale change)."""
    app = QApplication.instance()
    if app is not None:
        app.setStyleSheet(_build_qss())


def apply_theme(app: QApplication) -> None:
    app.setStyleSheet(_build_qss())
"""
XYrminal — terminal-like application with COM/TCP/UDP tabs.

Entry point. Creates QApplication, applies theme, shows main window.
"""

import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from core.i18n import init_translations
from core.paths import resource_root
from core.theme import apply_theme, ThemeManager, refresh_qss
from core.ui_scale import _UIScale
from ui.main_window import MainWindow


_ICON_PATH = resource_root() / "assets" / "icon.ico"


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("XYrminal")
    app.setOrganizationName("XYrminal")

    init_translations(app)

    if _ICON_PATH.exists():
        icon = QIcon(str(_ICON_PATH))
        app.setWindowIcon(icon)

    # сначала восстановим масштаб, потом тему, потом перерисуем QSS
    _UIScale.instance().restore_from_settings()

    apply_theme(app)
    ThemeManager.instance().restore_from_settings()
    refresh_qss()

    window = MainWindow()
    window.show()

    code = app.exec()

    try:
        window.shutdown()
    except Exception:
        pass

    return code


if __name__ == "__main__":
    sys.exit(main())
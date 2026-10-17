"""
Helpers for locating files at runtime.

Two modes are supported:

    * running as a script  (`python main.py`) — the project tree
    * running as a frozen app (`XYrminal.exe`) — the folder that contains
      the .exe next to it (NOT the temporary _MEIPASS directory)

Use `app_root()` when you need a place to *write* files (logs, configs, etc.).
Use `resource_root()` for *reading* resources bundled into the .exe (i18n,
icons, etc.).
"""

from __future__ import annotations

import sys
from pathlib import Path


def app_root() -> Path:
    """
    Directory the user "sees" as the app's home.

    * If frozen (PyInstaller .exe): the folder containing the .exe.
    * Otherwise: the folder containing the top-level project (parent of core/).
    """
    if getattr(sys, "frozen", False):
        # sys.executable is the path to XYrminal.exe
        return Path(sys.executable).resolve().parent
    # __file__ = .../core/paths.py → parent.parent = project root
    return Path(__file__).resolve().parent.parent


def resource_root() -> Path:
    """
    Directory where bundled resources live.

    * If frozen: sys._MEIPASS — the temporary folder PyInstaller extracts into.
    * Otherwise: same as app_root().
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent
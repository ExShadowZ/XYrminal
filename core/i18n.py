"""
i18n subsystem for XYrminal.

Provides:
    LANGUAGES               — list of supported (code, label) pairs
    init_translations(app)  — call once at startup, loads saved language
    apply_language(code)    — switch language at runtime
    current_language()      — returns the active language code
    language_label(code)    — human-readable label for a code
    language_changed        — signal emitted after a successful switch

The active language is persisted via QSettings under the key
"ui/language". If no saved value exists, the system locale is used
(falling back to English).

IMPORTANT — global tr() override:
    Our .ts/.qm files put every message under a single context "XYrminal"
    (see build_en_ts.py). But PyQt's QObject.tr() uses the class name as
    the context (e.g. "TransmitGroup"), so lookups would miss.

    To fix that, init_translations() monkey-patches QObject.tr so every
    .tr(...) call in the app resolves against the fixed context
    "XYrminal". This is a one-line-of-magic workaround that lets all
    existing self.tr(...) calls keep working without any code changes.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import (
    QObject, QTranslator, QLocale, QLibraryInfo, QSettings,
    QCoreApplication, pyqtSignal, QEvent,
)
from PyQt6.QtWidgets import QApplication

from core.paths import resource_root


# ---------------------------------------------------------------------------
# Paths — .qm files are bundled resources, so use resource_root()
# ---------------------------------------------------------------------------
_I18N_DIR = resource_root() / "i18n"


# ---------------------------------------------------------------------------
# Supported languages
# ---------------------------------------------------------------------------
LANGUAGES: list[tuple[str, str]] = [
    ("en", "English"),
    ("ru", "Русский"),
    ("be", "Беларуская"),
    ("de", "Deutsch"),
    ("fr", "Français"),
    ("zh", "中文"),
    ("ja", "日本語"),
    ("ko", "한국어"),
]

DEFAULT_LANGUAGE = "en"

# The single translation context used across the entire app.
TRANSLATION_CONTEXT = "XYrminal"


def language_label(code: str) -> str:
    for c, label in LANGUAGES:
        if c == code:
            return label
    return code


def _is_supported(code: str) -> bool:
    return any(c == code for c, _ in LANGUAGES)


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------
class _I18nManager(QObject):
    language_changed = pyqtSignal(str)

    _instance = None

    @classmethod
    def instance(cls) -> "_I18nManager":
        if cls._instance is None:
            cls._instance = _I18nManager()
        return cls._instance

    def __init__(self) -> None:
        super().__init__()
        self._app: QApplication | None = None
        self._app_translator: QTranslator | None = None
        self._qt_translator: QTranslator | None = None
        self._current: str = DEFAULT_LANGUAGE

    # -- startup -----------------------------------------------------------
    def init(self, app: QApplication) -> None:
        self._app = app

        settings = QSettings()
        saved = settings.value("ui/language", "", type=str)
        if saved and _is_supported(saved):
            code = saved
        else:
            code = self._system_language_code()

        self._current = code
        self._install_translators(code)

    # -- runtime switch ----------------------------------------------------
    def apply(self, code: str) -> None:
        if not _is_supported(code):
            return
        if code == self._current:
            return

        self._current = code
        QSettings().setValue("ui/language", code)
        self._install_translators(code)

        self.language_changed.emit(code)

    # -- queries -----------------------------------------------------------
    def current(self) -> str:
        return self._current

    # -- internal ----------------------------------------------------------
    def _system_language_code(self) -> str:
        name = QLocale.system().name()
        short = name.split("_", 1)[0]
        if _is_supported(short):
            return short
        return DEFAULT_LANGUAGE

    def _install_translators(self, code: str) -> None:
        app = self._app or QApplication.instance()
        if app is None:
            return

        # remove old translators
        if self._app_translator is not None:
            app.removeTranslator(self._app_translator)
            self._app_translator = None
        if self._qt_translator is not None:
            app.removeTranslator(self._qt_translator)
            self._qt_translator = None

        # load our app translations
        if code != "en":
            app_qm = _I18N_DIR / f"xyrminal_{code}.qm"
            if app_qm.exists():
                tr = QTranslator(app)
                if tr.load(str(app_qm)):
                    app.installTranslator(tr)
                    self._app_translator = tr

        # load Qt's own translations (for built-in dialogs / standard buttons)
        qt_qm_dir = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        qt_tr = QTranslator(app)
        if qt_tr.load(f"qtbase_{code}", qt_qm_dir):
            app.installTranslator(qt_tr)
            self._qt_translator = qt_tr

    # -- re-translate the whole widget tree -------------------------------
    def refresh_widgets(self) -> None:
        """
        Send a LanguageChange event to every widget in the application.

        Qt does NOT do this automatically when we install/remove a
        QTranslator. We have to walk the widget tree ourselves.

        We also call _retranslate() directly on widgets that define it —
        this is a safety net in case sendEvent() doesn't reach some
        deeply-nested or container widgets.
        """
        app = self._app or QApplication.instance()
        if app is None:
            return

        event = QEvent(QEvent.Type.LanguageChange)

        seen: set[int] = set()

        def _visit(obj: QObject) -> None:
            oid = id(obj)
            if oid in seen:
                return
            seen.add(oid)

            # 1. standard path
            try:
                app.sendEvent(obj, event)
            except Exception:
                pass

            # 2. safety net — direct call
            rt = getattr(obj, "_retranslate", None)
            if callable(rt):
                try:
                    rt()
                except Exception:
                    pass

        for w in app.allWidgets():
            _visit(w)
            for child in w.findChildren(QObject):
                _visit(child)


# ---------------------------------------------------------------------------
# Global tr() override
# ---------------------------------------------------------------------------
def _install_global_tr() -> None:
    """
    Replace QObject.tr() so that every .tr(...) call in the app uses
    a single, fixed translation context "XYrminal".

    This matches the context used in our .ts / .qm files (see
    build_en_ts.py), so translations actually resolve.

    Without this, self.tr("Transmit") inside TransmitGroup would look up
    context "TransmitGroup", which doesn't exist in our .qm → English
    fallback (the source string).

    Idempotent: safe to call multiple times.
    """
    if getattr(QObject, "_xyrminal_tr_patched", False):
        return

    def _tr(self, source, disambiguation=None, n=-1):
        # We deliberately ignore `self` and always use our fixed context.
        if n >= 0:
            if disambiguation is not None:
                return QCoreApplication.translate(
                    TRANSLATION_CONTEXT, source, disambiguation, n
                )
            return QCoreApplication.translate(
                TRANSLATION_CONTEXT, source, None, n
            )
        if disambiguation is not None:
            return QCoreApplication.translate(
                TRANSLATION_CONTEXT, source, disambiguation
            )
        return QCoreApplication.translate(TRANSLATION_CONTEXT, source)

    QObject.tr = _tr
    QObject._xyrminal_tr_patched = True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def init_translations(app: QApplication) -> None:
    _install_global_tr()
    _I18nManager.instance().init(app)


def apply_language(code: str) -> None:
    mgr = _I18nManager.instance()
    mgr.apply(code)
    mgr.refresh_widgets()


def current_language() -> str:
    return _I18nManager.instance().current()


def language_changed_signal():
    return _I18nManager.instance().language_changed
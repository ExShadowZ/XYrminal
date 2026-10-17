"""
Global UI scale factor.

    UI_SCALE       — current multiplier (0.75 … 1.5)
    ui_scale()     — getter
    set_ui_scale() — setter, emits `scale_changed`
    scale_changed_signal() — QObject signal

The value is persisted in QSettings under "ui/scale".
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal, QSettings


DEFAULT_SCALE = 1.0
MIN_SCALE     = 0.75
MAX_SCALE     = 1.5

ALLOWED_SCALES = [0.75, 1.0, 1.25, 1.5]


class _UIScale(QObject):
    scale_changed = pyqtSignal(float)

    _instance = None

    @classmethod
    def instance(cls) -> "_UIScale":
        if cls._instance is None:
            cls._instance = _UIScale()
        return cls._instance

    def __init__(self):
        super().__init__()
        self._scale = DEFAULT_SCALE

    def scale(self) -> float:
        return self._scale

    def set_scale(self, value: float) -> None:
        try:
            value = float(value)
        except (TypeError, ValueError):
            return
        if value < MIN_SCALE or value > MAX_SCALE:
            return
        if abs(value - self._scale) < 1e-6:
            return
        self._scale = value
        QSettings().setValue("ui/scale", value)
        self.scale_changed.emit(value)

    def restore_from_settings(self) -> None:
        s = QSettings()
        saved = s.value("ui/scale", DEFAULT_SCALE)
        try:
            saved = float(saved)
        except (TypeError, ValueError):
            saved = DEFAULT_SCALE
        if saved < MIN_SCALE or saved > MAX_SCALE:
            saved = DEFAULT_SCALE
        self._scale = saved


def ui_scale() -> float:
    return _UIScale.instance().scale()


def set_ui_scale(value: float) -> None:
    _UIScale.instance().set_scale(value)


def scale_changed_signal():
    return _UIScale.instance().scale_changed


def px(value: int | float) -> int:
    """Scale a pixel value by the current UI scale (rounded, min 1)."""
    return max(1, int(round(value * ui_scale())))
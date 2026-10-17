"""
Typed accessors over QSettings for XYrminal.

All keys live under an application-specific prefix managed by Qt itself
(QSettings already uses organizationName + applicationName set in main.py).
We just wrap primitives with sane defaults and types, so the rest of the
code doesn't have to remember types, section names, etc.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QSettings


class Settings:
    """Thin, typed wrapper around QSettings."""

    def __init__(self) -> None:
        self._s = QSettings()

    # -- generic -----------------------------------------------------------
    def get_str(self, key: str, default: str = "") -> str:
        return self._s.value(key, default, type=str)

    def set_str(self, key: str, value: str) -> None:
        self._s.setValue(key, value)

    def get_int(self, key: str, default: int = 0) -> int:
        try:
            return self._s.value(key, default, type=int)
        except (TypeError, ValueError):
            return default

    def set_int(self, key: str, value: int) -> None:
        self._s.setValue(key, int(value))

    def get_float(self, key: str, default: float = 0.0) -> float:
        try:
            return self._s.value(key, default, type=float)
        except (TypeError, ValueError):
            return default

    def set_float(self, key: str, value: float) -> None:
        self._s.setValue(key, float(value))

    def get_bool(self, key: str, default: bool = False) -> bool:
        val = self._s.value(key, default)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("1", "true", "yes", "on")
        return bool(val)

    def set_bool(self, key: str, value: bool) -> None:
        self._s.setValue(key, bool(value))

    # -- compound ----------------------------------------------------------
    def get_bytes(self, key: str, default: bytes = b"") -> bytes:
        val = self._s.value(key, default)
        if isinstance(val, bytes):
            return val
        if isinstance(val, bytearray):
            return bytes(val)
        return default

    def set_bytes(self, key: str, value: bytes) -> None:
        self._s.setValue(key, bytes(value))

    def sync(self) -> None:
        self._s.sync()
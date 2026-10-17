"""
Macro storage for XYrminal.

Each tab (com / tcp_client / tcp_server / udp_client / udp_server) has
10 slots. Each slot can be EITHER:

    * a plain macro
        text    — raw string as the user typed it ("hello", "AA BB CC")
        is_hex  — True if the text should be parsed as hex bytes
        add_cr  — True if a line ending should be appended
        crlf    — if add_cr is on: True → CR+LF, False → CR only

    * a scenario script (.xyscen)
        is_script    — True
        script_path  — full path to the file

Line-ending flags are IGNORED when is_hex is True (same as TransmitGroup):
in HEX mode the user enters line endings manually ("AA BB 0D 0A").

Persistence goes through the same QSettings wrapper as the rest of the app.

A single global MacroStore instance emits `macros_changed(prefix)` whenever
a set of macros is edited or reset. TransmitGroup subscribes to that signal
and refreshes its buttons.
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from core.settings import Settings


MACRO_COUNT = 10

PREFIXES = (
    "com",
    "tcp_client",
    "tcp_server",
    "udp_client",
    "udp_server",
)

PREFIX_LABELS = {
    "com":        "COM",
    "tcp_client": "TCP Client",
    "tcp_server": "TCP Server",
    "udp_client": "UDP Client",
    "udp_server": "UDP Server",
}


def prefix_label(prefix: str) -> str:
    """Return a human-readable label for a macro prefix."""
    return PREFIX_LABELS.get(prefix, prefix.upper())


def parse_hex(text: str) -> bytes | None:
    """
    Parse a hex string like "AA BB CC" / "aa,bb,cc" / "AABBCC" / "AA-BB-CC".
    Returns bytes, or None if invalid.
    """
    cleaned = (
        text.replace(" ", "")
            .replace(",", "")
            .replace("-", "")
            .replace("_", "")
    )
    if not cleaned:
        return b""
    if len(cleaned) % 2 != 0:
        return None
    try:
        return bytes.fromhex(cleaned)
    except ValueError:
        return None


class MacroStore(QObject):
    """
    Global singleton. Stores 10 slots per prefix.

    Signals:
        macros_changed(prefix) — emitted after set() / reset() /
                                 set_script() / clear_script().
                                 prefix in PREFIXES or "all".
    """

    macros_changed = pyqtSignal(str)

    _instance = None

    @classmethod
    def instance(cls) -> "MacroStore":
        if cls._instance is None:
            cls._instance = MacroStore()
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = Settings()

    # -- queries -----------------------------------------------------------
    def text(self, prefix: str, index: int) -> str:
        return self._settings.get_str(f"macros/{prefix}/{index}/text", "")

    def is_hex(self, prefix: str, index: int) -> bool:
        return self._settings.get_bool(f"macros/{prefix}/{index}/hex", False)

    def add_cr(self, prefix: str, index: int) -> bool:
        return self._settings.get_bool(f"macros/{prefix}/{index}/cr", False)

    def crlf(self, prefix: str, index: int) -> bool:
        return self._settings.get_bool(f"macros/{prefix}/{index}/crlf", False)

    def is_script(self, prefix: str, index: int) -> bool:
        return self._settings.get_bool(
            f"macros/{prefix}/{index}/is_script", False
        )

    def scenario_path(self, prefix: str, index: int) -> str:
        return self._settings.get_str(
            f"macros/{prefix}/{index}/script_path", ""
        )

    def get(self, prefix: str, index: int) -> tuple[str, bool, bool, bool]:
        """
        Return (text, is_hex, add_cr, crlf).
        """
        return (
            self.text(prefix, index),
            self.is_hex(prefix, index),
            self.add_cr(prefix, index),
            self.crlf(prefix, index),
        )

    def is_empty(self, prefix: str, index: int) -> bool:
        if self.is_script(prefix, index):
            return not self.scenario_path(prefix, index)
        return self.text(prefix, index).strip() == ""

    def as_bytes(self, prefix: str, index: int) -> bytes | None:
        """
        Return the macro's payload as bytes, or None if invalid (bad hex).

        Not used for scripts — scripts are executed by ScenarioExecutor.
        """
        if self.is_script(prefix, index):
            return b""

        text, is_hex, add_cr, crlf = self.get(prefix, index)

        if is_hex:
            return parse_hex(text)

        data = text.encode("utf-8", errors="replace")
        if add_cr:
            data += b"\r\n" if crlf else b"\r"
        return data

    # -- mutations ---------------------------------------------------------
    def set(self, prefix: str, index: int,
            text: str, is_hex: bool,
            add_cr: bool = False, crlf: bool = False,
            is_script: bool = False, script_path: str = "") -> None:
        s = self._settings
        s.set_str(f"macros/{prefix}/{index}/text", text)
        s.set_bool(f"macros/{prefix}/{index}/hex",  is_hex)
        s.set_bool(f"macros/{prefix}/{index}/cr",   add_cr)
        s.set_bool(f"macros/{prefix}/{index}/crlf", crlf)
        s.set_bool(f"macros/{prefix}/{index}/is_script", is_script)
        s.set_str(f"macros/{prefix}/{index}/script_path", script_path)
        s.sync()
        self.macros_changed.emit(prefix)

    def set_script(self, prefix: str, index: int, path: str) -> None:
        """Mark slot as a scenario script (keeps other flags)."""
        s = self._settings
        s.set_bool(f"macros/{prefix}/{index}/is_script", True)
        s.set_str(f"macros/{prefix}/{index}/script_path", path)
        s.sync()
        self.macros_changed.emit(prefix)

    def clear_script(self, prefix: str, index: int) -> None:
        """Turn slot back into a plain macro."""
        s = self._settings
        s.set_bool(f"macros/{prefix}/{index}/is_script", False)
        s.set_str(f"macros/{prefix}/{index}/script_path", "")
        s.sync()
        self.macros_changed.emit(prefix)

    def reset(self, prefix: str) -> None:
        """Wipe all 10 slots for a given prefix. prefix may be 'all'."""
        targets = PREFIXES if prefix == "all" else (prefix,)
        for p in targets:
            for i in range(MACRO_COUNT):
                self._settings.set_str(f"macros/{p}/{i}/text", "")
                self._settings.set_bool(f"macros/{p}/{i}/hex",  False)
                self._settings.set_bool(f"macros/{p}/{i}/cr",   False)
                self._settings.set_bool(f"macros/{p}/{i}/crlf", False)
                self._settings.set_bool(f"macros/{p}/{i}/is_script", False)
                self._settings.set_str(f"macros/{p}/{i}/script_path", "")
        self._settings.sync()
        self.macros_changed.emit(prefix)
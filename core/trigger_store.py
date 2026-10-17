"""
Text trigger storage for XYrminal.

A trigger is a plain substring (case-insensitive) plus a foreground and
background color. Whenever the terminal emits a line, TriggerStore is
asked which ranges of the text should be highlighted, with what colors.

Triggers are per-prefix (com / tcp_client / tcp_server / udp_client /
udp_server), exactly like macros. Up to MAX_TRIGGERS entries per prefix.

If two triggers overlap, the one with the lower index wins — the list
order is the priority.

Signals:
    triggers_changed(prefix) — emitted after set_all() / reset().
                               prefix in PREFIXES or "all".
"""

from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import QObject, pyqtSignal

from core.macros import PREFIXES
from core.settings import Settings


MAX_TRIGGERS = 50

DEFAULT_FG = "#000000"
DEFAULT_BG = "#e74c3c"


@dataclass
class Trigger:
    text: str
    fg:   str   # "#rrggbb"
    bg:   str   # "#rrggbb"

    def is_valid(self) -> bool:
        return bool(self.text.strip())


@dataclass
class Match:
    start: int
    end:   int
    fg:    str
    bg:    str


class TriggerStore(QObject):
    triggers_changed = pyqtSignal(str)

    _instance = None

    @classmethod
    def instance(cls) -> "TriggerStore":
        if cls._instance is None:
            cls._instance = TriggerStore()
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = Settings()

    # -- queries -----------------------------------------------------------
    def count(self, prefix: str) -> int:
        return self._settings.get_int(f"triggers/{prefix}/count", 0)

    def get(self, prefix: str, index: int) -> Trigger:
        s = self._settings
        return Trigger(
            text=s.get_str(f"triggers/{prefix}/{index}/text", ""),
            fg  =s.get_str(f"triggers/{prefix}/{index}/fg", DEFAULT_FG),
            bg  =s.get_str(f"triggers/{prefix}/{index}/bg", DEFAULT_BG),
        )

    def all(self, prefix: str) -> list[Trigger]:
        result: list[Trigger] = []
        n = self.count(prefix)
        for i in range(n):
            t = self.get(prefix, i)
            if t.is_valid():
                result.append(t)
        return result

    # -- matching ----------------------------------------------------------
    def find_matches(self, prefix: str, text: str) -> list[Match]:
        """
        Return non-overlapping matches of all triggers in `text`.
        Matching is case-insensitive. Earlier triggers win on overlap.
        """
        if not text:
            return []

        triggers = self.all(prefix)
        if not triggers:
            return []

        lowered = text.lower()
        hits: list[Match] = []

        for t in triggers:
            needle = t.text.lower()
            if not needle:
                continue

            start = 0
            while True:
                idx = lowered.find(needle, start)
                if idx < 0:
                    break
                end = idx + len(needle)
                hits.append(Match(start=idx, end=end, fg=t.fg, bg=t.bg))
                start = end   # non-overlapping per trigger

        if not hits:
            return []

        # Sort by start, then by length descending (longer wins on tie)
        hits.sort(key=lambda m: (m.start, -(m.end - m.start)))

        # Resolve overlaps: keep first (leftmost, longest); drop any that
        # overlap an already-kept range.
        result: list[Match] = []
        last_end = -1
        for m in hits:
            if m.start >= last_end:
                result.append(m)
                last_end = m.end

        return result

    # -- mutations ---------------------------------------------------------
    def set_all(self, prefix: str, triggers: list[Trigger]) -> None:
        s = self._settings

        # wipe all previous entries, then write the new list
        old_n = self.count(prefix)
        for i in range(max(old_n, len(triggers))):
            s.set_str(f"triggers/{prefix}/{i}/text", "")
            s.set_str(f"triggers/{prefix}/{i}/fg", DEFAULT_FG)
            s.set_str(f"triggers/{prefix}/{i}/bg", DEFAULT_BG)

        for i, t in enumerate(triggers):
            s.set_str(f"triggers/{prefix}/{i}/text", t.text)
            s.set_str(f"triggers/{prefix}/{i}/fg", t.fg)
            s.set_str(f"triggers/{prefix}/{i}/bg", t.bg)

        s.set_int(f"triggers/{prefix}/count", len(triggers))
        s.sync()
        self.triggers_changed.emit(prefix)

    def reset(self, prefix: str) -> None:
        """Wipe triggers for one prefix, or for every prefix with 'all'."""
        targets = PREFIXES if prefix == "all" else (prefix,)
        for p in targets:
            old_n = self.count(p)
            for i in range(old_n):
                self._settings.set_str(f"triggers/{p}/{i}/text", "")
                self._settings.set_str(f"triggers/{p}/{i}/fg", DEFAULT_FG)
                self._settings.set_str(f"triggers/{p}/{i}/bg", DEFAULT_BG)
            self._settings.set_int(f"triggers/{p}/count", 0)
        self._settings.sync()
        self.triggers_changed.emit(prefix)
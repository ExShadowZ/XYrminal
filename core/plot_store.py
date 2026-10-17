"""
Plot data storage + live parser for XYrminal.

A single global PlotStore instance listens to raw text chunks emitted by
TerminalView. When it is 'running' (not paused, not stopped), it scans
each chunk for the configured markers and extracts a numeric value that
follows the marker.

Marker rules:
    * If marker is non-empty → find it in text, parse the first number after.
    * If marker is empty      → parse the first number anywhere in the chunk.

Each sample stores BOTH a value and a monotonic timestamp (seconds from
the session start). PlotWidget uses the timestamp in "time mode" to draw
a time-based X axis; in normal mode it just uses the index.

Signals:
    channel_data_added()  — a new point was appended to some channel
    state_changed()       — running / paused / stopped changed

Each channel keeps up to MAX_POINTS points; oldest are dropped.

CSV export:
    export_csv(path) writes a spreadsheet-friendly file:
        index,time_s,<channel 1>,<channel 2>,...
        0,0.000,3.14,9.81
        1,0.101,3.15,9.80
        ...
    Missing tail values are left empty. UTF-8 with BOM so Excel opens
    Cyrillic channel names correctly.
"""

from __future__ import annotations

import csv
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal


MAX_POINTS = 1000

_NUMBER_RE = re.compile(r"[-+]?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?")


@dataclass
class PlotChannel:
    name:    str
    marker:  str
    color:   str
    values:  list[float] = field(default_factory=list)
    times:   list[float] = field(default_factory=list)   # monotonic seconds

    def add(self, value: float, t: float) -> None:
        self.values.append(value)
        self.times.append(t)
        if len(self.values) > MAX_POINTS:
            excess = len(self.values) - MAX_POINTS
            del self.values[:excess]
            del self.times[:excess]

    def clear(self) -> None:
        self.values.clear()
        self.times.clear()


class PlotStore(QObject):
    channel_data_added = pyqtSignal()
    state_changed      = pyqtSignal()

    _instance = None

    @classmethod
    def instance(cls) -> "PlotStore":
        if cls._instance is None:
            cls._instance = PlotStore()
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self._channels: list[PlotChannel] = []
        self._running: bool = False
        self._paused:  bool = False

        # monotonic clock: seconds since start()
        self._t0: float = 0.0

    # -- state -------------------------------------------------------------
    def is_running(self) -> bool:
        return self._running and not self._paused

    def is_active(self) -> bool:
        return self._running

    def is_paused(self) -> bool:
        return self._paused

    def channels(self) -> list[PlotChannel]:
        return self._channels

    def now_seconds(self) -> float:
        """Seconds elapsed since the current session started."""
        if not self._running:
            return 0.0
        return time.monotonic() - self._t0

    def session_seconds(self) -> float:
        """Duration of the current (or last) session, in seconds."""
        return self.now_seconds()

    # -- configuration -----------------------------------------------------
    def configure(self, channels: list[tuple[str, str]]) -> None:
        self._channels.clear()

        palette = [
            "#e74c3c", "#2ecc71", "#3498db", "#f1c40f", "#9b59b6",
            "#e67e22", "#1abc9c", "#e84393", "#95a5a6", "#34495e",
        ]

        for i, (name, marker) in enumerate(channels):
            name = name.strip()
            marker = marker.strip()
            if not name:
                continue
            color = palette[i % len(palette)]
            self._channels.append(PlotChannel(name=name, marker=marker, color=color))

        self.channel_data_added.emit()

    # -- session control ---------------------------------------------------
    def start(self, channels: list[tuple[str, str]]) -> None:
        self._t0 = time.monotonic()
        self.configure(channels)
        self._running = True
        self._paused = False
        self.state_changed.emit()

    def pause(self) -> None:
        if not self._running:
            return
        self._paused = True
        self.state_changed.emit()

    def resume(self) -> None:
        if not self._running:
            return
        self._paused = False
        self.state_changed.emit()

    def stop(self) -> None:
        self._running = False
        self._paused = False
        self.state_changed.emit()

    def toggle_pause(self) -> None:
        if not self._running:
            return
        self._paused = not self._paused
        self.state_changed.emit()

    def clear_data(self) -> None:
        for ch in self._channels:
            ch.clear()
        self.channel_data_added.emit()

    # -- parser ------------------------------------------------------------
    def feed(self, text: str) -> None:
        if not self._running or self._paused or not text:
            return

        t = time.monotonic() - self._t0
        appended = False
        for ch in self._channels:
            value = self._extract_value(text, ch.marker)
            if value is not None:
                ch.add(value, t)
                appended = True

        if appended:
            self.channel_data_added.emit()

    @staticmethod
    def _extract_value(text: str, marker: str) -> Optional[float]:
        if not marker:
            m = _NUMBER_RE.search(text)
            if not m:
                return None
            raw = m.group(0).replace(",", ".")
            try:
                return float(raw)
            except ValueError:
                return None

        idx = text.find(marker)
        if idx < 0:
            return None

        tail = text[idx + len(marker):]
        tail = tail.lstrip(" \t:=,")

        m = _NUMBER_RE.match(tail)
        if not m:
            return None

        raw = m.group(0).replace(",", ".")
        try:
            return float(raw)
        except ValueError:
            return None

    # -- export ------------------------------------------------------------
    def has_data(self) -> bool:
        """True if at least one channel has at least one point."""
        return any(ch.values for ch in self._channels)

    def export_csv(self, path: str | Path) -> Path:
        """
        Write all channels into a CSV file.

        Layout:
            index,time_s,<name1>,<name2>,...
            0,0.000,3.14,9.81
            1,0.101,3.15,
            ...

        * index     — 0-based sample number
        * time_s    — seconds since session start (monotonic), 3 decimals
        * each ch   — its values in order; missing tail values → empty cell

        Encoding is UTF-8 with BOM so Excel opens Cyrillic names cleanly.
        Excel-friendly: comma separator, dot as decimal mark.
        """
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)

        # Determine the maximum length across all channels. All channels
        # share the same "time grid" for the first min(len) samples; beyond
        # that a channel just has no more data (empty cells).
        max_len = max((len(ch.values) for ch in self._channels), default=0)

        header = ["index", "time_s"] + [ch.name for ch in self._channels]

        # Open with utf-8-sig so Excel recognises UTF-8
        with p.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(header)

            for i in range(max_len):
                # Pick the timestamp of the first channel that has this index.
                # All channels that received a value from the same incoming
                # chunk share the same `t`, but we don't strictly guarantee
                # that — so "first available" is a good approximation.
                t: Optional[float] = None
                for ch in self._channels:
                    if i < len(ch.times):
                        t = ch.times[i]
                        break

                row: list[str] = [str(i)]
                row.append(f"{t:.3f}" if t is not None else "")

                for ch in self._channels:
                    if i < len(ch.values):
                        v = ch.values[i]
                        # Use repr-like formatting but drop trailing zeros
                        # for readability: 3.140 → 3.14, 3.000 → 3
                        row.append(_fmt_value(v))
                    else:
                        row.append("")

                writer.writerow(row)

        return p


def _fmt_value(v: float) -> str:
    """
    Format a float for CSV: up to 6 decimals, trailing zeros stripped.
    Avoid scientific notation for normal magnitudes.
    """
    if v == int(v):
        return str(int(v))
    s = f"{v:.6f}".rstrip("0").rstrip(".")
    return s if s else "0"
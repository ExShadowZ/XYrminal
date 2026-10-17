"""
TCP ping — like PowerShell's Test-Connection but over TCP.

Actually measures TCP connect() round-trip time to <host>:<port>.

Two modes:
    * run_series(count, period)  — ping <count> times, spaced <period> sec
    * start_periodic(period)     — ping forever every <period> sec
    * stop()                     — stop either mode

Signals:
    line(str)         — a formatted PowerShell-style output line (no timestamp)
    finished()        — emitted when a series completes or periodic is stopped
    busy_changed(bool)— True while pinging, False when idle
"""

from __future__ import annotations

import socket
import time
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class TcpPinger(QObject):
    line          = pyqtSignal(str)
    finished      = pyqtSignal()
    busy_changed  = pyqtSignal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timer)

        self._host: str = ""
        self._port: int = 0
        self._timeout: float = 4.0
        self._period: float = 1.0

        # series state
        self._mode: str = "idle"          # "series" | "periodic" | "idle"
        self._remaining: int = 0
        self._sent: int = 0
        self._received: int = 0
        self._rtts: list[float] = []

    # -- public API --------------------------------------------------------
    def run_series(self, host: str, port: int, timeout: float,
                   count: int, period: float) -> None:
        """Ping <host>:<port> <count> times, <period> seconds apart."""
        self.stop()   # cancel any previous run

        self._host = host
        self._port = port
        self._timeout = timeout
        self._period = max(0.0, period)
        self._remaining = count

        self._sent = 0
        self._received = 0
        self._rtts.clear()

        self._mode = "series"
        self.busy_changed.emit(True)

        self.line.emit(
            self.tr("Pinging {host}:{port} with {count} probes:")
            .format(host=host, port=port, count=count)
        )
        # Start immediately, no initial delay.
        self._do_one_ping()

    def start_periodic(self, host: str, port: int, timeout: float,
                       period: float) -> None:
        """Ping <host>:<port> forever every <period> seconds."""
        self.stop()

        self._host = host
        self._port = port
        self._timeout = timeout
        self._period = max(0.1, period)

        self._sent = 0
        self._received = 0
        self._rtts.clear()
        self._remaining = -1

        self._mode = "periodic"
        self.busy_changed.emit(True)

        self.line.emit(
            self.tr("Pinging {host}:{port} periodically:")
            .format(host=host, port=port)
        )
        self._do_one_ping()

    def stop(self) -> None:
        if self._mode == "idle":
            return

        self._timer.stop()

        # For a series that was cut short, still print the summary.
        was_series = (self._mode == "series" and self._sent > 0)
        self._mode = "idle"
        self.busy_changed.emit(False)

        if was_series:
            self._print_summary()

        self.finished.emit()

    def is_busy(self) -> bool:
        return self._mode != "idle"

    # -- internal ----------------------------------------------------------
    def _do_one_ping(self) -> None:
        if self._mode == "idle":
            return

        self._sent += 1
        t0 = time.perf_counter()
        ok = self._try_connect()
        t1 = time.perf_counter()

        if ok:
            rtt_ms = (t1 - t0) * 1000.0
            self._received += 1
            self._rtts.append(rtt_ms)
            self.line.emit(
                self.tr("Reply from {host}:{port}: time={ms}ms")
                .format(host=self._host, port=self._port, ms=int(rtt_ms))
            )
        else:
            self.line.emit(self.tr("Request timed out."))

        if self._mode == "series":
            self._remaining -= 1
            if self._remaining <= 0:
                self._print_summary()
                self._mode = "idle"
                self.busy_changed.emit(False)
                self.finished.emit()
                return

        # schedule next
        delay_ms = int(self._period * 1000)
        self._timer.start(max(1, delay_ms))

    def _try_connect(self) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(self._timeout)
                s.connect((self._host, self._port))
            return True
        except Exception:
            return False

    def _on_timer(self) -> None:
        self._do_one_ping()

    def _print_summary(self) -> None:
        sent = self._sent
        received = self._received
        lost = sent - received
        lost_pct = (lost / sent * 100.0) if sent else 0.0

        self.line.emit(
            self.tr("Ping statistics for {host}:{port}:")
            .format(host=self._host, port=self._port)
        )
        self.line.emit(
            self.tr("    Packets: Sent = {sent}, Received = {recv}, Lost = {lost}")
            .format(sent=sent, recv=received, lost=lost)
        )
        self.line.emit(
            self.tr("    ({pct}% loss)").format(pct=int(lost_pct))
        )

        if self._rtts:
            self.line.emit(self.tr("Approximate round trip times in ms:"))
            self.line.emit(
                self.tr("    Minimum = {mn}ms, Maximum = {mx}ms, Average = {av}ms")
                .format(
                    mn=int(min(self._rtts)),
                    mx=int(max(self._rtts)),
                    av=int(sum(self._rtts) / len(self._rtts)),
                )
            )
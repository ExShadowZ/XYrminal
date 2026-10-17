"""
Serial I/O worker.

Runs entirely in the UI thread and polls the port with a QTimer.
No QThread, no signal queues, no race conditions.

Responsibilities:
    * scan available COM ports (static helper)
    * open / close the port
    * poll for incoming bytes and emit them
    * write bytes when the UI requests it
    * toggle DTR / RTS lines
    * emit modem status lines (CD / RI / DSR / CTS) when they change
    * emit error / state-change signals

The worker does NOT know about UI widgets. It only emits bytes/strings.
Formatting happens in the UI layer.
"""

from __future__ import annotations

from typing import Optional

import serial
import serial.tools.list_ports
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from core.modem_lines import ModemLines


# ---------------------------------------------------------------------------
# Port scanning
# ---------------------------------------------------------------------------
def list_ports() -> list[tuple[str, str]]:
    result = []
    for p in serial.tools.list_ports.comports():
        result.append((p.device, p.description or p.device))
    result.sort(key=lambda x: x[0])
    return result


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------
class SerialWorker(QObject):
    data_received       = pyqtSignal(bytes)
    opened              = pyqtSignal(str)
    closed              = pyqtSignal()
    error               = pyqtSignal(str)
    modem_lines_changed = pyqtSignal(object)   # ModemLines

    POLL_MS = 10

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._serial: Optional[serial.Serial] = None
        self._port_name: str = ""
        self._last_lines: ModemLines = ModemLines()

        self._timer = QTimer(self)
        self._timer.setInterval(self.POLL_MS)
        self._timer.timeout.connect(self._poll)

    # -- public API --------------------------------------------------------
    def open_port(self, config: dict) -> None:
        self._close_quietly()

        try:
            self._serial = serial.Serial(
                port          = config["port"],
                baudrate      = config["baudrate"],
                bytesize      = config["bytesize"],
                parity        = config["parity"],
                stopbits      = config["stopbits"],
                timeout       = 0,
                write_timeout = 1.0,
                rtscts        = config.get("rtscts", False),
                xonxoff       = config.get("xonxoff", False),
            )
        except Exception as exc:
            self.error.emit(f"Open failed: {exc}")
            self._serial = None
            return

        if config.get("rts_on_tx"):
            try:
                self._serial.rts = False
            except Exception:
                pass

        self._port_name = config["port"]
        self._last_lines = ModemLines()
        self._timer.start()
        self.opened.emit(self._port_name)

    def close_port(self) -> None:
        self._timer.stop()
        self._close_quietly()
        self.closed.emit()

    def is_open(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def write(self, data: bytes) -> None:
        if not self._serial or not self._serial.is_open:
            self.error.emit("Not connected")
            return
        try:
            self._serial.write(data)
        except Exception as exc:
            self.error.emit(f"Write failed: {exc}")

    def set_dtr(self, on: bool) -> None:
        if not self._serial or not self._serial.is_open:
            return
        try:
            self._serial.dtr = on
        except Exception as exc:
            self.error.emit(f"DTR set failed: {exc}")

    def set_rts(self, on: bool) -> None:
        if not self._serial or not self._serial.is_open:
            return
        try:
            self._serial.rts = on
        except Exception as exc:
            self.error.emit(f"RTS set failed: {exc}")

    # -- internal ----------------------------------------------------------
    def _poll(self) -> None:
        if not self._serial or not self._serial.is_open:
            return

        # --- modem status lines (cheap reads, no exception risk) ---
        try:
            lines = ModemLines(
                cd  = bool(self._serial.cd),
                ri  = bool(self._serial.ri),
                dsr = bool(self._serial.dsr),
                cts = bool(self._serial.cts),
            )
            if lines != self._last_lines:
                self._last_lines = lines
                self.modem_lines_changed.emit(lines)
        except Exception:
            pass

        # --- data ---
        try:
            n = self._serial.in_waiting
            if n > 0:
                chunk = self._serial.read(n)
                if chunk:
                    self.data_received.emit(chunk)
                return

            chunk = self._serial.read(1)
            if chunk:
                self.data_received.emit(chunk)
        except Exception as exc:
            self.error.emit(f"Read failed: {exc}")
            self.close_port()

    def _close_quietly(self) -> None:
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None
        self._port_name = ""
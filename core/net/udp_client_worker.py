"""
UDP client worker — "connected" UDP socket.

Config keys for open_connection():
    host           : str          — remote host or IP
    port           : int          — remote port
    local_host     : str | None   — local bind address (optional)
    local_port     : int | None   — local bind port (optional, 0 = any)
    timeout        : float        — reserved; UDP has no connect timeout
"""

from __future__ import annotations

import socket
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class UdpClientWorker(QObject):
    data_received = pyqtSignal(bytes)
    opened        = pyqtSignal(str)
    closed        = pyqtSignal()
    error         = pyqtSignal(str)

    POLL_MS = 20

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._sock: Optional[socket.socket] = None
        self._peer: str = ""

        self._timer = QTimer(self)
        self._timer.setInterval(self.POLL_MS)
        self._timer.timeout.connect(self._poll)

    # -- public API --------------------------------------------------------
    def open_connection(self, config: dict) -> None:
        self._close_quietly()

        host       = config.get("host", "").strip()
        port       = int(config.get("port", 0))
        local_host = (config.get("local_host") or "").strip()
        local_port = int(config.get("local_port") or 0)

        if not host or port <= 0:
            self.error.emit("Invalid host or port")
            return

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            if local_host or local_port:
                sock.bind((local_host or "0.0.0.0", local_port))

            sock.connect((host, port))
            sock.setblocking(False)

            self._sock = sock
            self._peer = f"{host}:{port}"
        except Exception as exc:
            self.error.emit(f"Open failed: {exc}")
            self._sock = None
            return

        self._timer.start()
        self.opened.emit(self._peer)

    def close_connection(self) -> None:
        self._timer.stop()
        self._close_quietly()
        self.closed.emit()

    def write(self, data: bytes) -> None:
        if not self._sock:
            self.error.emit("Not connected")
            return
        try:
            self._sock.send(data)
        except Exception as exc:
            self.error.emit(f"Send failed: {exc}")

    def is_open(self) -> bool:
        return self._sock is not None

    def peer(self) -> str:
        return self._peer

    # -- internal ----------------------------------------------------------
    def _poll(self) -> None:
        if not self._sock:
            return
        try:
            chunk = self._sock.recv(65535)
            if chunk:
                self.data_received.emit(chunk)
        except BlockingIOError:
            pass
        except Exception as exc:
            self.error.emit(f"Recv failed: {exc}")
            self.close_connection()

    def _close_quietly(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        self._peer = ""


# Backwards-compat alias
UdpWorker = UdpClientWorker
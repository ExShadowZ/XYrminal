"""
UDP server worker.

Binds a UDP socket on a local port without connecting it, so it receives
datagrams from any sender. Remembers the last sender's address for replies.
Also supports broadcasting to 255.255.255.255.

Emits:
    data_received(peer, bytes)  — `peer` is "host:port" of the sender
    opened(str)
    closed()
    error(str)

API:
    start(local_port, local_host="0.0.0.0") -> bool
    stop()
    send(data)                          — to last known remote
    send_to(host, port, data)           — to explicit address
    broadcast(port, data)               — to 255.255.255.255:port
    is_open() -> bool
    last_peer() -> str
"""

from __future__ import annotations

import socket
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class UdpServerWorker(QObject):
    data_received = pyqtSignal(str, bytes)
    opened        = pyqtSignal(str)
    closed        = pyqtSignal()
    error         = pyqtSignal(str)

    POLL_MS = 20

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._sock: Optional[socket.socket] = None
        self._local_desc: str = ""
        self._last_peer: Optional[tuple[str, int]] = None

        self._timer = QTimer(self)
        self._timer.setInterval(self.POLL_MS)
        self._timer.timeout.connect(self._poll)

    # -- public API --------------------------------------------------------
    def start(self, local_port: int, local_host: str = "0.0.0.0") -> None:
        self._close_quietly()

        if local_port <= 0 or local_port > 65535:
            self.error.emit("Invalid local port")
            return

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.bind((local_host or "0.0.0.0", local_port))
            sock.setblocking(False)

            self._sock = sock
            self._local_desc = f"{local_host or '0.0.0.0'}:{local_port}"
        except Exception as exc:
            self.error.emit(f"Bind failed: {exc}")
            self._sock = None
            return

        self._timer.start()
        self.opened.emit(self._local_desc)

    def stop(self) -> None:
        self._timer.stop()
        self._close_quietly()
        self.closed.emit()

    def send(self, data: bytes) -> None:
        """Send to the last known remote address."""
        if not self._sock:
            self.error.emit("Not bound")
            return
        if self._last_peer is None:
            self.error.emit("No remote address yet")
            return
        try:
            self._sock.sendto(data, self._last_peer)
        except Exception as exc:
            self.error.emit(f"Send failed: {exc}")

    def send_to(self, host: str, port: int, data: bytes) -> None:
        if not self._sock:
            self.error.emit("Not bound")
            return
        try:
            self._sock.sendto(data, (host, port))
            self._last_peer = (host, port)
        except Exception as exc:
            self.error.emit(f"Send failed: {exc}")

    def broadcast(self, port: int, data: bytes) -> None:
        if not self._sock:
            self.error.emit("Not bound")
            return
        try:
            self._sock.sendto(data, ("255.255.255.255", port))
        except Exception as exc:
            self.error.emit(f"Broadcast failed: {exc}")

    def is_open(self) -> bool:
        return self._sock is not None

    def last_peer(self) -> str:
        if self._last_peer is None:
            return ""
        return f"{self._last_peer[0]}:{self._last_peer[1]}"

    # -- internal ----------------------------------------------------------
    def _poll(self) -> None:
        if not self._sock:
            return
        try:
            data, addr = self._sock.recvfrom(65535)
            if data:
                self._last_peer = addr
                peer = f"{addr[0]}:{addr[1]}"
                self.data_received.emit(peer, data)
        except BlockingIOError:
            pass
        except Exception as exc:
            self.error.emit(f"Recv failed: {exc}")
            self.stop()

    def _close_quietly(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        self._local_desc = ""
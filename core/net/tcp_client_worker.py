"""
TCP client worker.

Runs entirely in the UI thread and polls the socket with a QTimer.

Auto-reconnect:
    If `keep_connection=True` in the last open_connection() config,
    then whenever the connection drops (peer closed, read error,
    explicit disconnect from peer), the worker will retry every
    RECONNECT_DELAY_MS milliseconds until either it succeeds or the
    user calls close_connection() / open_connection() again.

Config keys for open_connection():
    host            : str          — remote host or IP
    port            : int          — remote port
    local_host      : str | None   — local bind address (optional)
    local_port      : int | None   — local bind port (optional, 0 = any)
    timeout         : float        — connect timeout in seconds
    keep_connection : bool         — auto-reconnect on drop (default False)
"""

from __future__ import annotations

import socket
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class TcpClientWorker(QObject):
    data_received = pyqtSignal(bytes)
    opened        = pyqtSignal(str)     # "host:port"
    closed        = pyqtSignal()        # emitted when the user asked to close
    error         = pyqtSignal(str)
    reconnecting  = pyqtSignal(int)     # emit attempt counter while retrying

    POLL_MS = 20
    RECONNECT_DELAY_MS = 2000

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._sock: Optional[socket.socket] = None
        self._peer: str = ""
        self._config: dict = {}
        self._keep_connection: bool = False
        self._user_closed: bool = False
        self._reconnect_attempt: int = 0

        self._timer = QTimer(self)
        self._timer.setInterval(self.POLL_MS)
        self._timer.timeout.connect(self._poll)

        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setSingleShot(True)
        self._reconnect_timer.timeout.connect(self._try_reconnect)

    # -- public API --------------------------------------------------------
    def open_connection(self, config: dict) -> None:
        self._close_quietly()
        self._reconnect_timer.stop()
        self._user_closed = False
        self._reconnect_attempt = 0

        self._config = dict(config)
        self._keep_connection = bool(config.get("keep_connection", False))

        if not self._try_connect_now():
            self._schedule_reconnect()

    def close_connection(self) -> None:
        self._user_closed = True
        self._reconnect_timer.stop()
        self._timer.stop()
        self._close_quietly()
        self.closed.emit()

    def write(self, data: bytes) -> None:
        if not self._sock:
            self.error.emit("Not connected")
            return
        try:
            self._sock.sendall(data)
        except Exception as exc:
            self.error.emit(f"Write failed: {exc}")
            # drop the socket, let reconnect logic pick it up
            self._on_socket_lost()

    def is_open(self) -> bool:
        return self._sock is not None

    def peer(self) -> str:
        return self._peer

    def keep_connection(self) -> bool:
        return self._keep_connection

    # -- internal ----------------------------------------------------------
    def _try_connect_now(self) -> bool:
        host       = self._config.get("host", "").strip()
        port       = int(self._config.get("port", 0))
        local_host = (self._config.get("local_host") or "").strip()
        local_port = int(self._config.get("local_port") or 0)
        timeout    = float(self._config.get("timeout", 5.0))

        if not host or port <= 0:
            self.error.emit("Invalid host or port")
            return False

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)

            if local_host or local_port:
                sock.bind((local_host or "0.0.0.0", local_port))

            sock.connect((host, port))
            sock.setblocking(False)

            self._sock = sock
            self._peer = f"{host}:{port}"
        except Exception as exc:
            self.error.emit(f"Connect failed: {exc}")
            self._sock = None
            return False

        self._reconnect_attempt = 0
        self._timer.start()
        self.opened.emit(self._peer)
        return True

    def _schedule_reconnect(self) -> None:
        if not self._keep_connection or self._user_closed:
            return
        self._reconnect_attempt += 1
        self.reconnecting.emit(self._reconnect_attempt)
        self._reconnect_timer.start(self.RECONNECT_DELAY_MS)

    def _try_reconnect(self) -> None:
        if self._user_closed or not self._keep_connection:
            return
        if self._try_connect_now():
            return
        self._schedule_reconnect()

    def _on_socket_lost(self) -> None:
        self._timer.stop()
        self._close_quietly()

        if self._keep_connection and not self._user_closed:
            self._schedule_reconnect()
        else:
            self.closed.emit()

    def _poll(self) -> None:
        if not self._sock:
            return
        try:
            chunk = self._sock.recv(4096)
            if chunk:
                self.data_received.emit(chunk)
            else:
                self.error.emit("Connection closed by peer")
                self._on_socket_lost()
        except BlockingIOError:
            pass
        except Exception as exc:
            self.error.emit(f"Read failed: {exc}")
            self._on_socket_lost()

    def _close_quietly(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        self._peer = ""


TcpWorker = TcpClientWorker
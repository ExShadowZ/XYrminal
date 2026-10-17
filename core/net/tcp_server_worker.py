"""
TCP server worker.

Uses Qt's QTcpServer / QTcpSocket so everything runs in the UI thread —
no threads, no queues, no race conditions.

Emits:
    data_received(peer, bytes)  — `peer` is "host:port" of the sender
    opened(str)                 — "listening on <host>:<port>"
    closed()                    — server stopped
    error(str)
    client_connected(peer)
    client_disconnected(peer)
    clients_changed(list[str])  — full list of currently-connected peers

API:
    start(port, host="0.0.0.0") -> bool
    stop()
    write(data)                  — broadcast to all clients
    write_to(peer, data)         — send to one specific client
    disconnect_client(peer)
    disconnect_all()
    is_open() -> bool
    clients() -> list[str]
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtNetwork import QTcpServer, QTcpSocket, QHostAddress


class TcpServerWorker(QObject):
    data_received       = pyqtSignal(str, bytes)   # peer, data
    opened              = pyqtSignal(str)
    closed              = pyqtSignal()
    error               = pyqtSignal(str)
    client_connected    = pyqtSignal(str)
    client_disconnected = pyqtSignal(str)
    clients_changed     = pyqtSignal(list)         # list[str] of peers

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._server: Optional[QTcpServer] = None
        self._clients: dict[str, QTcpSocket] = {}   # peer → socket
        self._listen_desc: str = ""

    # -- public API --------------------------------------------------------
    def start(self, port: int, host: str = "0.0.0.0") -> None:
        self._close_quietly()

        if port <= 0 or port > 65535:
            self.error.emit("Invalid port")
            return

        server = QTcpServer(self)
        bind_addr = QHostAddress(host) if host else QHostAddress.SpecialAddress.Any

        if not server.listen(bind_addr, port):
            self.error.emit(f"Listen failed: {server.errorString()}")
            server.deleteLater()
            return

        server.newConnection.connect(self._on_new_connection)
        self._server = server
        self._listen_desc = f"{host or '0.0.0.0'}:{port}"

        self.opened.emit(self._listen_desc)

    def stop(self) -> None:
        self._close_quietly()
        self.closed.emit()

    def write(self, data: bytes) -> None:
        """Broadcast to all connected clients."""
        if not self._clients:
            self.error.emit("No clients connected")
            return
        for peer, sock in list(self._clients.items()):
            try:
                sock.write(data)
            except Exception as exc:
                self.error.emit(f"Write to {peer} failed: {exc}")

    def write_to(self, peer: str, data: bytes) -> None:
        sock = self._clients.get(peer)
        if sock is None:
            self.error.emit(f"Unknown client: {peer}")
            return
        try:
            sock.write(data)
        except Exception as exc:
            self.error.emit(f"Write to {peer} failed: {exc}")

    def disconnect_client(self, peer: str) -> None:
        sock = self._clients.get(peer)
        if sock is None:
            return
        try:
            sock.disconnectFromHost()
        except Exception:
            pass

    def disconnect_all(self) -> None:
        for peer in list(self._clients.keys()):
            self.disconnect_client(peer)

    def is_open(self) -> bool:
        return self._server is not None and self._server.isListening()

    def clients(self) -> list[str]:
        return list(self._clients.keys())

    # -- internal ----------------------------------------------------------
    def _on_new_connection(self) -> None:
        while self._server is not None and self._server.hasPendingConnections():
            sock = self._server.nextPendingConnection()
            if sock is None:
                break

            peer = f"{sock.peerAddress().toString()}:{sock.peerPort()}"
            self._clients[peer] = sock

            sock.readyRead.connect(lambda p=peer: self._on_ready_read(p))
            sock.disconnected.connect(lambda p=peer: self._on_disconnected(p))

            self.client_connected.emit(peer)
            self.clients_changed.emit(self.clients())

    def _on_ready_read(self, peer: str) -> None:
        sock = self._clients.get(peer)
        if sock is None:
            return
        try:
            chunk = bytes(sock.readAll())
            if chunk:
                self.data_received.emit(peer, chunk)
        except Exception as exc:
            self.error.emit(f"Read from {peer} failed: {exc}")

    def _on_disconnected(self, peer: str) -> None:
        sock = self._clients.pop(peer, None)
        if sock is not None:
            try:
                sock.deleteLater()
            except Exception:
                pass
        self.client_disconnected.emit(peer)
        self.clients_changed.emit(self.clients())

    def _close_quietly(self) -> None:
        # close all client sockets
        for peer, sock in list(self._clients.items()):
            try:
                sock.disconnectFromHost()
                sock.deleteLater()
            except Exception:
                pass
        self._clients.clear()

        if self._server is not None:
            try:
                self._server.close()
                self._server.deleteLater()
            except Exception:
                pass
            self._server = None

        self._listen_desc = ""
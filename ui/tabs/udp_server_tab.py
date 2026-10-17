"""
UDP server tab.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout

from core.net.udp_server_worker import UdpServerWorker

from ui.net_tab_base import NetTabBase
from ui.widgets.udp_server_group import UdpServerGroup


class UdpServerTab(NetTabBase):
    _log_suffix      = "udp_server"
    _transmit_prefix = "udp_server"
    _state_prefix    = "udp_server"
    _file_transfer_enabled = False
    _group_visibility_keys = ("server", "term_settings")

    def _build_top(self):
        top = QVBoxLayout()
        top.setSpacing(8)

        self.server = UdpServerGroup()
        top.addWidget(self.server)
        return top

    def _create_worker(self):
        return UdpServerWorker(self)

    def _wire_worker(self) -> None:
        self.server.listen_requested.connect(self._on_listen)
        self.server.stop_requested.connect(self._on_stop)

        self.worker.opened.connect(self._on_opened)
        self.worker.closed.connect(self._on_closed)
        self.worker.error.connect(self._on_error)
        self.worker.data_received.connect(self._on_server_data)

    def _on_listen(self, host: str, port: int, echo: bool) -> None:
        self._echo = echo
        self.worker.start(port, host)

    def _on_stop(self) -> None:
        self.worker.stop()

    def _on_opened(self, desc: str) -> None:
        self.server.set_listening(True)
        self.terminal.append_server_event(f"[UDP Server] listening on {desc}")

    def _on_closed(self) -> None:
        self.server.set_listening(False)
        self.terminal.append_server_event("[UDP Server] stopped")

    def _on_server_data(self, peer: str, chunk: bytes) -> None:
        self._rx_bytes += len(chunk)
        self.counters_changed.emit(self._tx_bytes, self._rx_bytes)

        from core.formatter import format_bytes, RAW_MODES
        text = format_bytes(chunk, self._format_mode)
        is_raw = self._format_mode in RAW_MODES
        self.terminal.append_peer_text(f"[{peer}] ", text, raw=is_raw)

        self.server.set_last_peer(peer)

        if getattr(self, "_echo", False):
            try:
                self.worker.send(chunk)
            except Exception:
                pass

    def _on_send(self, data: bytes) -> None:
        if not data:
            return
        self._tx_bytes += len(data)
        self.counters_changed.emit(self._tx_bytes, self._rx_bytes)

        from core.formatter import format_preview
        preview = format_preview(data)

        if self.server.is_broadcast():
            host, port = self.server.get_remote()
            if port <= 0:
                port = 4023
            self.terminal.append_tx_text(f"[broadcast :{port}] {preview}")
            self.worker.broadcast(port, data)
        else:
            host, port = self.server.get_remote()
            if host and port > 0:
                self.terminal.append_tx_text(f"[{host}:{port}] {preview}")
                self.worker.send_to(host, port, data)
            else:
                self.terminal.append_tx_text(f"[last] {preview}")
                self.worker.send(data)

    def worker_is_connected(self) -> bool:
        return self.worker.is_open()

    def available_groups(self) -> dict[str, str]:
        return {
            "server":        self.tr("Server"),
            "term_settings": self.tr("Setting terminal"),
        }

    def _group_widget(self, name: str):
        return {
            "server":        self.server,
            "term_settings": self.term_settings,
        }.get(name)

    def _save_top_state(self, s) -> None:
        self.server.save_state(s, "udp_server")

    def _restore_top_state(self, s) -> None:
        self.server.restore_state(s, "udp_server")

    def _shutdown_worker(self) -> None:
        self.worker.stop()
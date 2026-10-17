"""
TCP server tab.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout

from core.net.tcp_server_worker import TcpServerWorker

from ui.net_tab_base import NetTabBase
from ui.widgets.tcp_server_group import TcpServerGroup


class TcpServerTab(NetTabBase):
    _log_suffix      = "tcp_server"
    _transmit_prefix = "tcp_server"
    _state_prefix    = "tcp_server"
    _file_transfer_enabled = False
    _group_visibility_keys = ("server", "term_settings")

    def _build_top(self):
        top = QVBoxLayout()
        top.setSpacing(8)

        self.server = TcpServerGroup()
        top.addWidget(self.server)
        return top

    def _create_worker(self):
        return TcpServerWorker(self)

    def _wire_worker(self) -> None:
        self.server.listen_requested.connect(self._on_listen)
        self.server.stop_requested.connect(self._on_stop)
        self.server.disconnect_requested.connect(self.worker.disconnect_client)
        self.server.disconnect_all_requested.connect(self.worker.disconnect_all)

        self.worker.opened.connect(self._on_opened)
        self.worker.closed.connect(self._on_closed)
        self.worker.error.connect(self._on_error)
        self.worker.data_received.connect(self._on_server_data)
        self.worker.client_connected.connect(self._on_client_connected)
        self.worker.client_disconnected.connect(self._on_client_disconnected)
        self.worker.clients_changed.connect(self.server.set_clients)

    # -- listen ------------------------------------------------------------
    def _on_listen(self, host: str, port: int, echo: bool) -> None:
        self._echo = echo
        self.worker.start(port, host)

    def _on_stop(self) -> None:
        self.worker.stop()

    def _on_opened(self, desc: str) -> None:
        self.server.set_listening(True)
        self.terminal.append_server_event(f"[TCP Server] listening on {desc}")

    def _on_closed(self) -> None:
        self.server.set_listening(False)
        self.terminal.append_server_event("[TCP Server] stopped")

    def _on_client_connected(self, peer: str) -> None:
        self.terminal.append_server_event(f"[+] {peer}")

    def _on_client_disconnected(self, peer: str) -> None:
        self.terminal.append_server_event(f"[-] {peer}")

    # -- data --------------------------------------------------------------
    def _on_server_data(self, peer: str, chunk: bytes) -> None:
        self._rx_bytes += len(chunk)
        self.counters_changed.emit(self._tx_bytes, self._rx_bytes)

        from core.formatter import format_bytes, RAW_MODES
        text = format_bytes(chunk, self._format_mode)
        is_raw = self._format_mode in RAW_MODES
        self.terminal.append_peer_text(f"[{peer}] ", text, raw=is_raw)

        if getattr(self, "_echo", False):
            try:
                self.worker.write_to(peer, chunk)
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
            self.terminal.append_tx_text(f"[broadcast] {preview}")
            self.worker.write(data)
        else:
            peer = self.server.current_selected_peer()
            if peer:
                self.terminal.append_tx_text(f"[{peer}] {preview}")
                self.worker.write_to(peer, data)
            else:
                self.terminal.append_tx_text(f"[broadcast] {preview}")
                self.worker.write(data)

    # -- no file transfer in server mode ----------------------------------
    # Base class already blocks it via _file_transfer_enabled = False.

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
        self.server.save_state(s, "tcp_server")

    def _restore_top_state(self, s) -> None:
        self.server.restore_state(s, "tcp_server")

    def _shutdown_worker(self) -> None:
        self.worker.stop()
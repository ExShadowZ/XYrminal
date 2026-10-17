"""
TCP client tab.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QMessageBox

from core.net.tcp_client_worker import TcpClientWorker
from core.net.pinger import TcpPinger

from ui.net_tab_base import NetTabBase
from ui.widgets.net_connecting_group import NetConnectingGroup
from ui.widgets.ping_group            import PingGroup


class TcpClientTab(NetTabBase):
    _log_suffix      = "tcp"
    _transmit_prefix = "tcp_client"
    _state_prefix    = "tcp_client"
    _file_transfer_enabled = True
    _group_visibility_keys = ("connecting", "ping", "term_settings")

    def _build_top(self):
        top = QHBoxLayout()
        top.setSpacing(8)

        # show_keep=True → render the "Keep connection" checkbox
        self.connecting = NetConnectingGroup(show_keep=True)
        self.ping       = PingGroup()

        top.addWidget(self.connecting, stretch=1)
        top.addWidget(self.ping,       stretch=1)
        return top

    def _create_worker(self):
        return TcpClientWorker(self)

    def _wire_worker(self) -> None:
        self.connecting.connect_requested.connect(self._on_connect)
        self.connecting.disconnect_requested.connect(self._on_disconnect)

        self.ping.check_requested.connect(self._on_ping_check)
        self.ping.start_requested.connect(self._on_ping_start)
        self.ping.stop_requested.connect(self._on_ping_stop)

        self.worker.data_received.connect(self._on_data_received)
        self.worker.opened.connect(self._on_opened)
        self.worker.closed.connect(self._on_closed)
        self.worker.error.connect(self._on_error)
        self.worker.reconnecting.connect(self._on_reconnecting)

        self.pinger = TcpPinger(self)
        self.pinger.line.connect(self.terminal.append_ping_text)
        self.pinger.busy_changed.connect(self.ping.set_busy)

    def _on_connect(self) -> None:
        self.worker.open_connection(self.connecting.get_config())

    def _on_disconnect(self) -> None:
        self.worker.close_connection()

    def _on_opened(self, peer: str) -> None:
        self.connecting.set_connected(True)
        self.terminal.append_text(f"[TCP] {peer}\n")

    def _on_closed(self) -> None:
        self.connecting.set_connected(False)
        self.terminal.append_text("[TCP] Disconnected\n")

    def _on_reconnecting(self, attempt: int) -> None:
        self.terminal.append_text(f"[TCP] reconnect attempt #{attempt}…\n")

    def worker_is_connected(self) -> bool:
        return self.worker.is_open()

    def _on_ping_check(self, cfg: dict) -> None:
        self.pinger.run_series(
            cfg["host"], cfg["port"], cfg["timeout"],
            cfg["count"], cfg["period"],
        )

    def _on_ping_start(self, cfg: dict) -> None:
        self.pinger.start_periodic(
            cfg["host"], cfg["port"], cfg["timeout"], cfg["period"],
        )

    def _on_ping_stop(self) -> None:
        self.pinger.stop()

    def available_groups(self) -> dict[str, str]:
        return {
            "connecting":    self.tr("Connecting"),
            "ping":          self.tr("Ping"),
            "term_settings": self.tr("Setting terminal"),
        }

    def _group_widget(self, name: str):
        return {
            "connecting":    self.connecting,
            "ping":          self.ping,
            "term_settings": self.term_settings,
        }.get(name)

    def _save_top_state(self, s) -> None:
        self.connecting.save_state(s, "tcp_client")
        self.ping.save_state(s, "tcp_client_ping")

    def _restore_top_state(self, s) -> None:
        self.connecting.restore_state(s, "tcp_client")
        self.ping.restore_state(s, "tcp_client_ping")

    def _shutdown_worker(self) -> None:
        try:
            self.pinger.stop()
        except Exception:
            pass
        self.worker.close_connection()
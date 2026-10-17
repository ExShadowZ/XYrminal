"""
'Server' group for the TCP server tab.
"""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal, QEvent
from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLineEdit, QSpinBox, QPushButton, QLabel, QListWidget,
    QCheckBox, QWidget,
)


class TcpServerGroup(QGroupBox):
    listen_requested        = pyqtSignal(str, int, bool)
    stop_requested          = pyqtSignal()
    disconnect_requested    = pyqtSignal(str)
    disconnect_all_requested = pyqtSignal()
    send_mode_changed       = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()
        self._retranslate()
        self.set_listening(False)

    def _build(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(10, 18, 10, 10)
        outer.setSpacing(14)

        left = QGridLayout()
        left.setHorizontalSpacing(10)
        left.setVerticalSpacing(6)

        self.lbl_host = QLabel()
        self.lbl_port = QLabel()

        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("0.0.0.0")

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(5000)

        self.echo_chk = QCheckBox()
        self.broadcast_chk = QCheckBox()
        self.broadcast_chk.setChecked(True)

        btn_row = QHBoxLayout()
        self.listen_btn = QPushButton()
        self.listen_btn.setProperty("btnStyle", "ok")
        self.listen_btn.clicked.connect(self._on_listen)

        self.stop_btn = QPushButton()
        self.stop_btn.setProperty("btnStyle", "danger")
        self.stop_btn.clicked.connect(self.stop_requested.emit)

        btn_row.addWidget(self.listen_btn)
        btn_row.addWidget(self.stop_btn)
        btn_row.addStretch(1)

        left.addWidget(self.lbl_host,       0, 0)
        left.addWidget(self.host_edit,      0, 1)
        left.addWidget(self.lbl_port,       1, 0)
        left.addWidget(self.port_spin,      1, 1)
        left.addLayout(btn_row,             2, 0, 1, 2)
        left.addWidget(self.echo_chk,       3, 0, 1, 2)
        left.addWidget(self.broadcast_chk,  4, 0, 1, 2)
        left.setColumnStretch(1, 1)

        left_w = QWidget()
        left_w.setLayout(left)

        right = QVBoxLayout()
        right.setSpacing(6)

        self.lbl_clients = QLabel()
        right.addWidget(self.lbl_clients)

        self.clients_list = QListWidget()
        self.clients_list.setMinimumWidth(140)
        right.addWidget(self.clients_list, stretch=1)

        clients_btns = QHBoxLayout()
        self.disconnect_btn = QPushButton()
        self.disconnect_btn.clicked.connect(self._on_disconnect_selected)
        self.disconnect_all_btn = QPushButton()
        self.disconnect_all_btn.clicked.connect(self.disconnect_all_requested.emit)
        clients_btns.addWidget(self.disconnect_btn)
        clients_btns.addWidget(self.disconnect_all_btn)
        clients_btns.addStretch(1)
        right.addLayout(clients_btns)

        right_w = QWidget()
        right_w.setLayout(right)

        outer.addWidget(left_w,  stretch=3)
        outer.addWidget(right_w, stretch=4)

        self.broadcast_chk.toggled.connect(self.send_mode_changed.emit)

    def _retranslate(self) -> None:
        self.setTitle(self.tr("Server"))
        self.lbl_host.setText(self.tr("Local host:"))
        self.lbl_port.setText(self.tr("Port:"))
        self.listen_btn.setText(self.tr("Listen"))
        self.stop_btn.setText(self.tr("Stop"))
        self.echo_chk.setText(self.tr("Echo"))
        self.broadcast_chk.setText(self.tr("Broadcast to all"))
        self.lbl_clients.setText(self.tr("Clients:"))
        self.disconnect_btn.setText(self.tr("Disconnect selected"))
        self.disconnect_all_btn.setText(self.tr("Disconnect all"))

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate()
        super().changeEvent(event)

    def get_listen_config(self) -> tuple[str, int, bool]:
        return (
            self.host_edit.text().strip() or "0.0.0.0",
            self.port_spin.value(),
            self.echo_chk.isChecked(),
        )

    def is_broadcast(self) -> bool:
        return self.broadcast_chk.isChecked()

    def set_listening(self, listening: bool) -> None:
        self.listen_btn.setEnabled(not listening)
        self.stop_btn.setEnabled(listening)
        self.host_edit.setEnabled(not listening)
        self.port_spin.setEnabled(not listening)
        self.echo_chk.setEnabled(not listening)

    def set_clients(self, peers: list[str]) -> None:
        self.clients_list.clear()
        for p in peers:
            self.clients_list.addItem(p)
        self.lbl_clients.setText(
            self.tr("Clients: {n}").format(n=len(peers))
        )

    def current_selected_peer(self) -> str:
        item = self.clients_list.currentItem()
        return item.text() if item else ""

    def _on_listen(self) -> None:
        host, port, echo = self.get_listen_config()
        self.listen_requested.emit(host, port, echo)

    def _on_disconnect_selected(self) -> None:
        peer = self.current_selected_peer()
        if peer:
            self.disconnect_requested.emit(peer)

    def save_state(self, s, prefix: str) -> None:
        s.set_str(f"{prefix}/host", self.host_edit.text().strip())
        s.set_int(f"{prefix}/port", self.port_spin.value())
        s.set_bool(f"{prefix}/echo", self.echo_chk.isChecked())
        s.set_bool(f"{prefix}/broadcast", self.broadcast_chk.isChecked())

    def restore_state(self, s, prefix: str) -> None:
        self.host_edit.setText(s.get_str(f"{prefix}/host", "0.0.0.0"))
        self.port_spin.setValue(s.get_int(f"{prefix}/port", 5000))
        self.echo_chk.setChecked(s.get_bool(f"{prefix}/echo", False))
        self.broadcast_chk.setChecked(s.get_bool(f"{prefix}/broadcast", True))
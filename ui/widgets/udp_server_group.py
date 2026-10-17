"""
'Server' group for the UDP server tab.

Layout:
    [Local host] [Local port] [Listen] [Stop]   [x] Echo
    Remote host: [____] Port: [____]             [x] Broadcast
    [Use last sender as remote] [Send to remote]

Signals:
    listen_requested(local_host, local_port, echo)
    stop_requested()
    use_last_requested()
    send_mode_changed(broadcast: bool)
"""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal, QEvent
from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLineEdit, QSpinBox, QPushButton, QLabel, QCheckBox, QWidget,
)


class UdpServerGroup(QGroupBox):
    listen_requested = pyqtSignal(str, int, bool)   # local_host, local_port, echo
    stop_requested   = pyqtSignal()
    send_mode_changed = pyqtSignal(bool)            # broadcast

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()
        self._retranslate()
        self.set_listening(False)

    def _build(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(10, 18, 10, 10)
        outer.setSpacing(14)

        # left: listen
        left = QGridLayout()
        left.setHorizontalSpacing(10)
        left.setVerticalSpacing(6)

        self.lbl_local_host = QLabel()
        self.lbl_local_port = QLabel()

        self.local_host_edit = QLineEdit()
        self.local_host_edit.setPlaceholderText("0.0.0.0")

        self.local_port_spin = QSpinBox()
        self.local_port_spin.setRange(1, 65535)
        self.local_port_spin.setValue(4023)

        self.echo_chk = QCheckBox()

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

        left.addWidget(self.lbl_local_host,  0, 0)
        left.addWidget(self.local_host_edit, 0, 1)
        left.addWidget(self.lbl_local_port,  1, 0)
        left.addWidget(self.local_port_spin, 1, 1)
        left.addLayout(btn_row,              2, 0, 1, 2)
        left.addWidget(self.echo_chk,        3, 0, 1, 2)
        left.setColumnStretch(1, 1)

        left_w = QWidget()
        left_w.setLayout(left)

        # right: remote + broadcast
        right = QGridLayout()
        right.setHorizontalSpacing(10)
        right.setVerticalSpacing(6)

        self.lbl_remote_host = QLabel()
        self.lbl_remote_port = QLabel()

        self.remote_host_edit = QLineEdit()
        self.remote_host_edit.setPlaceholderText("192.168.1.100")

        self.remote_port_spin = QSpinBox()
        self.remote_port_spin.setRange(1, 65535)
        self.remote_port_spin.setValue(23)

        self.broadcast_chk = QCheckBox()
        self.broadcast_chk.toggled.connect(self.send_mode_changed.emit)

        self.lbl_last = QLabel()
        self.lbl_last.setProperty("role", "dim")

        right.addWidget(self.lbl_remote_host,  0, 0)
        right.addWidget(self.remote_host_edit, 0, 1)
        right.addWidget(self.lbl_remote_port,  1, 0)
        right.addWidget(self.remote_port_spin, 1, 1)
        right.addWidget(self.broadcast_chk,    2, 0, 1, 2)
        right.addWidget(self.lbl_last,         3, 0, 1, 2)
        right.setColumnStretch(1, 1)

        right_w = QWidget()
        right_w.setLayout(right)

        outer.addWidget(left_w,  stretch=3)
        outer.addWidget(right_w, stretch=4)

    def _retranslate(self) -> None:
        self.setTitle(self.tr("Server"))
        self.lbl_local_host.setText(self.tr("Local host:"))
        self.lbl_local_port.setText(self.tr("Local port:"))
        self.listen_btn.setText(self.tr("Listen"))
        self.stop_btn.setText(self.tr("Stop"))
        self.echo_chk.setText(self.tr("Server echo"))
        self.lbl_remote_host.setText(self.tr("Remote host:"))
        self.lbl_remote_port.setText(self.tr("Remote port:"))
        self.broadcast_chk.setText(self.tr("Broadcast"))
        self.lbl_last.setText(self.tr("Last sender: —"))

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate()
        super().changeEvent(event)

    # -- public API --------------------------------------------------------
    def get_listen_config(self) -> tuple[str, int, bool]:
        return (
            self.local_host_edit.text().strip() or "0.0.0.0",
            self.local_port_spin.value(),
            self.echo_chk.isChecked(),
        )

    def get_remote(self) -> tuple[str, int]:
        return (
            self.remote_host_edit.text().strip(),
            self.remote_port_spin.value(),
        )

    def is_broadcast(self) -> bool:
        return self.broadcast_chk.isChecked()

    def set_listening(self, listening: bool) -> None:
        self.listen_btn.setEnabled(not listening)
        self.stop_btn.setEnabled(listening)
        self.local_host_edit.setEnabled(not listening)
        self.local_port_spin.setEnabled(not listening)
        self.echo_chk.setEnabled(not listening)

    def set_last_peer(self, peer: str) -> None:
        if peer:
            self.lbl_last.setText(self.tr("Last sender: {p}").format(p=peer))
        else:
            self.lbl_last.setText(self.tr("Last sender: —"))

    # -- slots -------------------------------------------------------------
    def _on_listen(self) -> None:
        host, port, echo = self.get_listen_config()
        self.listen_requested.emit(host, port, echo)

    # -- state -------------------------------------------------------------
    def save_state(self, s, prefix: str) -> None:
        s.set_str(f"{prefix}/local_host", self.local_host_edit.text().strip())
        s.set_int(f"{prefix}/local_port", self.local_port_spin.value())
        s.set_bool(f"{prefix}/echo", self.echo_chk.isChecked())
        s.set_str(f"{prefix}/remote_host", self.remote_host_edit.text().strip())
        s.set_int(f"{prefix}/remote_port", self.remote_port_spin.value())
        s.set_bool(f"{prefix}/broadcast", self.broadcast_chk.isChecked())

    def restore_state(self, s, prefix: str) -> None:
        self.local_host_edit.setText(s.get_str(f"{prefix}/local_host", "0.0.0.0"))
        self.local_port_spin.setValue(s.get_int(f"{prefix}/local_port", 4023))
        self.echo_chk.setChecked(s.get_bool(f"{prefix}/echo", False))
        self.remote_host_edit.setText(s.get_str(f"{prefix}/remote_host", ""))
        self.remote_port_spin.setValue(s.get_int(f"{prefix}/remote_port", 23))
        self.broadcast_chk.setChecked(s.get_bool(f"{prefix}/broadcast", False))
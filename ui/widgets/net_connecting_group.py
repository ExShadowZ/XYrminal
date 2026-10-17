"""
'Connecting' group for TCP / UDP tabs.
"""

from PyQt6.QtCore import pyqtSignal, QEvent
from PyQt6.QtWidgets import (
    QGroupBox, QGridLayout, QHBoxLayout, QVBoxLayout,
    QLineEdit, QPushButton, QLabel, QSpinBox, QDoubleSpinBox, QWidget,
    QCheckBox,
)


class NetConnectingGroup(QGroupBox):
    connect_requested    = pyqtSignal()
    disconnect_requested = pyqtSignal()

    def __init__(self, parent=None, show_keep: bool = True):
        super().__init__(parent)
        self._show_keep = show_keep
        self._build()
        self._retranslate()

    def _build(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(10, 18, 10, 10)
        outer.setSpacing(14)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        self.lbl_host       = QLabel()
        self.lbl_port       = QLabel()
        self.lbl_local_host = QLabel()
        self.lbl_local_port = QLabel()
        self.lbl_timeout    = QLabel()

        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("192.168.1.100")

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(5000)

        self.local_host_edit = QLineEdit()
        self.local_host_edit.setPlaceholderText("0.0.0.0")

        self.local_port_spin = QSpinBox()
        self.local_port_spin.setRange(0, 65535)
        self.local_port_spin.setValue(0)

        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(0.1, 600.0)
        self.timeout_spin.setDecimals(1)
        self.timeout_spin.setValue(5.0)

        grid.addWidget(self.lbl_host,        0, 0)
        grid.addWidget(self.host_edit,       0, 1)
        grid.addWidget(self.lbl_port,        1, 0)
        grid.addWidget(self.port_spin,       1, 1)
        grid.addWidget(self.lbl_local_host,  2, 0)
        grid.addWidget(self.local_host_edit, 2, 1)
        grid.addWidget(self.lbl_local_port,  3, 0)
        grid.addWidget(self.local_port_spin, 3, 1)
        grid.addWidget(self.lbl_timeout,     4, 0)
        grid.addWidget(self.timeout_spin,    4, 1)

        # keep-connection checkbox (row 5)
        self.keep_chk = QCheckBox()
        self.keep_chk.setChecked(False)
        if self._show_keep:
            grid.addWidget(self.keep_chk, 5, 0, 1, 2)

        grid.setColumnStretch(1, 1)

        fields_w = QWidget()
        fields_w.setLayout(grid)

        btns = QVBoxLayout()
        btns.setSpacing(6)
        btns.addStretch(1)

        self.connect_btn = QPushButton()
        self.connect_btn.setProperty("btnStyle", "ok")
        self.connect_btn.clicked.connect(self.connect_requested.emit)

        self.disconnect_btn = QPushButton()
        self.disconnect_btn.setProperty("btnStyle", "danger")
        self.disconnect_btn.clicked.connect(self.disconnect_requested.emit)

        btns.addWidget(self.connect_btn)
        btns.addWidget(self.disconnect_btn)
        btns.addStretch(1)

        outer.addWidget(fields_w, stretch=4)
        outer.addLayout(btns,      stretch=1)

        self.set_connected(False)

    def _retranslate(self) -> None:
        self.setTitle(self.tr("Connecting"))
        self.lbl_host.setText(self.tr("Remote host:"))
        self.lbl_port.setText(self.tr("Remote port:"))
        self.lbl_local_host.setText(self.tr("Local host:"))
        self.lbl_local_port.setText(self.tr("Local port:"))
        self.lbl_timeout.setText(self.tr("Timeout:"))
        self.keep_chk.setText(self.tr("Keep connection"))
        self.timeout_spin.setSuffix(self.tr(" s"))
        self.connect_btn.setText(self.tr("Connect"))
        self.disconnect_btn.setText(self.tr("Disconnect"))

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate()
        super().changeEvent(event)

    # -- public ------------------------------------------------------------
    def get_config(self) -> dict:
        return {
            "host":            self.host_edit.text().strip(),
            "port":            self.port_spin.value(),
            "local_host":      self.local_host_edit.text().strip(),
            "local_port":      self.local_port_spin.value(),
            "timeout":         self.timeout_spin.value(),
            "keep_connection": self.keep_chk.isChecked(),
        }

    def set_connected(self, connected: bool) -> None:
        self.connect_btn.setEnabled(not connected)
        self.disconnect_btn.setEnabled(connected)
        self._set_fields_enabled(not connected)

    def _set_fields_enabled(self, enabled: bool) -> None:
        for w in (self.host_edit, self.port_spin,
                  self.local_host_edit, self.local_port_spin,
                  self.timeout_spin, self.keep_chk):
            w.setEnabled(enabled)

    # -- persistence -------------------------------------------------------
    def save_state(self, s, prefix: str) -> None:
        s.set_str(f"{prefix}/host",       self.host_edit.text().strip())
        s.set_int(f"{prefix}/port",       self.port_spin.value())
        s.set_str(f"{prefix}/local_host", self.local_host_edit.text().strip())
        s.set_int(f"{prefix}/local_port", self.local_port_spin.value())
        s.set_float(f"{prefix}/timeout",  self.timeout_spin.value())
        s.set_bool(f"{prefix}/keep",      self.keep_chk.isChecked())

    def restore_state(self, s, prefix: str) -> None:
        self.host_edit.setText(s.get_str(f"{prefix}/host", ""))
        self.port_spin.setValue(s.get_int(f"{prefix}/port", 5000))
        self.local_host_edit.setText(s.get_str(f"{prefix}/local_host", ""))
        self.local_port_spin.setValue(s.get_int(f"{prefix}/local_port", 0))
        self.timeout_spin.setValue(s.get_float(f"{prefix}/timeout", 5.0))
        self.keep_chk.setChecked(s.get_bool(f"{prefix}/keep", False))
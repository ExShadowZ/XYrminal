"""
'Ping' group.
"""

from PyQt6.QtCore import pyqtSignal, QEvent
from PyQt6.QtWidgets import (
    QGroupBox, QGridLayout, QHBoxLayout, QVBoxLayout,
    QLineEdit, QSpinBox, QDoubleSpinBox, QPushButton,
    QLabel, QWidget,
)


class PingGroup(QGroupBox):
    check_requested = pyqtSignal(dict)
    start_requested = pyqtSignal(dict)
    stop_requested  = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._busy = False
        self._build()
        self._retranslate()
        self._refresh_buttons()

    def _build(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(10, 18, 10, 10)
        outer.setSpacing(14)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("8.8.8.8")

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(80)

        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(0.1, 60.0)
        self.timeout_spin.setDecimals(1)
        self.timeout_spin.setValue(2.0)

        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 100000)
        self.quantity_spin.setValue(4)

        self.period_spin = QDoubleSpinBox()
        self.period_spin.setRange(0.1, 3600.0)
        self.period_spin.setDecimals(1)
        self.period_spin.setValue(1.0)

        self.lbl_host     = QLabel()
        self.lbl_port     = QLabel()
        self.lbl_timeout  = QLabel()
        self.lbl_quantity = QLabel()
        self.lbl_period   = QLabel()

        grid.addWidget(self.lbl_host,     0, 0)
        grid.addWidget(self.host_edit,    0, 1)
        grid.addWidget(self.lbl_port,     1, 0)
        grid.addWidget(self.port_spin,    1, 1)
        grid.addWidget(self.lbl_timeout,  2, 0)
        grid.addWidget(self.timeout_spin, 2, 1)
        grid.addWidget(self.lbl_quantity, 3, 0)
        grid.addWidget(self.quantity_spin,3, 1)
        grid.addWidget(self.lbl_period,   4, 0)
        grid.addWidget(self.period_spin,  4, 1)
        grid.setColumnStretch(1, 1)

        fields_w = QWidget()
        fields_w.setLayout(grid)

        btns = QGridLayout()
        btns.setVerticalSpacing(6)
        btns.addWidget(QLabel(""), 0, 0)
        btns.addWidget(QLabel(""), 1, 0)
        btns.addWidget(QLabel(""), 2, 0)

        self.check_btn = QPushButton()
        self.check_btn.setProperty("btnStyle", "ok")
        self.check_btn.clicked.connect(self._on_check)

        self.start_btn = QPushButton()
        self.start_btn.setProperty("btnStyle", "ok")
        self.start_btn.clicked.connect(self._on_start)

        btns.addWidget(self.check_btn, 3, 0)
        btns.addWidget(self.start_btn, 4, 0)
        btns.setRowStretch(5, 1)

        outer.addWidget(fields_w, stretch=4)
        outer.addLayout(btns,     stretch=1)

    def _retranslate(self) -> None:
        self.setTitle(self.tr("Ping"))

        self.lbl_host.setText(self.tr("Host:"))
        self.lbl_port.setText(self.tr("Port:"))
        self.lbl_timeout.setText(self.tr("Timeout:"))
        self.lbl_quantity.setText(self.tr("Quantity:"))
        self.lbl_period.setText(self.tr("Period:"))

        self.timeout_spin.setSuffix(self.tr(" s"))
        self.period_spin.setSuffix(self.tr(" s"))

        self.check_btn.setText(self.tr("Check"))
        self._refresh_buttons()

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate()
        super().changeEvent(event)

    def get_config(self) -> dict:
        return {
            "host":     self.host_edit.text().strip(),
            "port":     self.port_spin.value(),
            "timeout":  self.timeout_spin.value(),
            "count":    self.quantity_spin.value(),
            "period":   self.period_spin.value(),
        }

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._refresh_buttons()

    def _on_check(self) -> None:
        self.check_requested.emit(self.get_config())

    def _on_start(self) -> None:
        if self._busy:
            self.stop_requested.emit()
        else:
            self.start_requested.emit(self.get_config())

    def _refresh_buttons(self) -> None:
        if self._busy:
            self.check_btn.setEnabled(False)
            self.start_btn.setText(self.tr("Stop ping"))
            self.start_btn.setProperty("btnStyle", "danger")
        else:
            self.check_btn.setEnabled(True)
            self.start_btn.setText(self.tr("Start ping"))
            self.start_btn.setProperty("btnStyle", "ok")

        self.start_btn.style().unpolish(self.start_btn)
        self.start_btn.style().polish(self.start_btn)

    def save_state(self, s, prefix: str) -> None:
        s.set_str(f"{prefix}/host",      self.host_edit.text().strip())
        s.set_int(f"{prefix}/port",      self.port_spin.value())
        s.set_float(f"{prefix}/timeout", self.timeout_spin.value())
        s.set_int(f"{prefix}/quantity",  self.quantity_spin.value())
        s.set_float(f"{prefix}/period",  self.period_spin.value())

    def restore_state(self, s, prefix: str) -> None:
        self.host_edit.setText(s.get_str(f"{prefix}/host", ""))
        self.port_spin.setValue(s.get_int(f"{prefix}/port", 80))
        self.timeout_spin.setValue(s.get_float(f"{prefix}/timeout", 2.0))
        self.quantity_spin.setValue(s.get_int(f"{prefix}/quantity", 4))
        self.period_spin.setValue(s.get_float(f"{prefix}/period", 1.0))
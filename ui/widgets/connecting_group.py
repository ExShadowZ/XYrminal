"""
'Connecting' group — port selector, Scan, Connect / Disconnect, DTR / RTS,
and modem-status line indicators (CD / RI / DSR / CTS).

Emits:
    connect_requested(port_name)
    disconnect_requested()
    dtr_changed(bool)
    rts_changed(bool)
"""

from PyQt6.QtCore import pyqtSignal, QEvent, Qt
from PyQt6.QtWidgets import (
    QGroupBox, QHBoxLayout, QVBoxLayout, QComboBox, QPushButton, QLabel,
)

from core.serial_worker import list_ports
from core.modem_lines import ModemLines
from core.theme import ToggleButton, COLORS


class _StatusLed(QLabel):
    """Small colored dot for a modem status line."""

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self._on = False
        self._label = label
        self.setFixedSize(38, 20)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._refresh()

    def set_on(self, on: bool) -> None:
        if on == self._on:
            return
        self._on = on
        self._refresh()

    def _refresh(self) -> None:
        from PyQt6.QtGui import QColor
        on_color = COLORS.get("ok", "#2ecc71")
        off_color = COLORS.get("text_muted", "#6b6480")
        fg = on_color if self._on else off_color
        border = COLORS.get("border", "#3a3454")
        self.setStyleSheet(
            f"QLabel {{"
            f"  color: {fg};"
            f"  border: 1px solid {border};"
            f"  border-radius: 3px;"
            f"  font-size: 10px;"
            f"  font-weight: 700;"
            f"}}"
        )
        self.setText(self._label)


class ConnectingGroup(QGroupBox):
    connect_requested    = pyqtSignal(str)
    disconnect_requested = pyqtSignal()
    dtr_changed          = pyqtSignal(bool)
    rts_changed          = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()
        self._retranslate()
        self.refresh_ports()

    def _build(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 18, 10, 10)
        root.setSpacing(10)

        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(130)
        root.addWidget(self.port_combo, stretch=1)

        self.scan_btn = QPushButton()
        self.scan_btn.clicked.connect(self.refresh_ports)
        root.addWidget(self.scan_btn)

        right = QVBoxLayout()
        right.setSpacing(4)

        conn_row = QHBoxLayout()
        conn_row.setSpacing(4)

        self.connect_btn = QPushButton()
        self.connect_btn.setProperty("btnStyle", "ok")
        self.connect_btn.clicked.connect(self._on_connect)
        conn_row.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton()
        self.disconnect_btn.setProperty("btnStyle", "danger")
        self.disconnect_btn.clicked.connect(self._on_disconnect)
        conn_row.addWidget(self.disconnect_btn)

        right.addLayout(conn_row)

        line_row = QHBoxLayout()
        line_row.setSpacing(4)

        self.dtr_btn = ToggleButton("", on=False)
        self.dtr_btn.toggled_state.connect(self.dtr_changed.emit)
        line_row.addWidget(self.dtr_btn)

        self.rts_btn = ToggleButton("", on=False)
        self.rts_btn.toggled_state.connect(self.rts_changed.emit)
        line_row.addWidget(self.rts_btn)

        line_row.addSpacing(10)
        self.led_cd  = _StatusLed("CD")
        self.led_ri  = _StatusLed("RI")
        self.led_dsr = _StatusLed("DSR")
        self.led_cts = _StatusLed("CTS")
        for led in (self.led_cd, self.led_ri, self.led_dsr, self.led_cts):
            line_row.addWidget(led)

        right.addLayout(line_row)

        root.addLayout(right)

        self.set_connected(False)

    def _retranslate(self) -> None:
        self.setTitle(self.tr("Connecting"))
        self.scan_btn.setText(self.tr("Scan"))
        self.connect_btn.setText(self.tr("Connect"))
        self.disconnect_btn.setText(self.tr("Disconnect"))
        self.dtr_btn.setText(self.tr("DTR"))
        self.rts_btn.setText(self.tr("RTS"))
        self.refresh_ports()

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate()
        super().changeEvent(event)

    def refresh_ports(self) -> None:
        prev = self.port_combo.currentData()

        self.port_combo.blockSignals(True)
        self.port_combo.clear()
        for device, desc in list_ports():
            self.port_combo.addItem(f"{device} — {desc}", device)
        self.port_combo.blockSignals(False)

        if prev is not None:
            idx = self.port_combo.findData(prev)
            if idx >= 0:
                self.port_combo.setCurrentIndex(idx)

    def current_port(self) -> str | None:
        return self.port_combo.currentData()

    def set_connected(self, connected: bool) -> None:
        self.connect_btn.setEnabled(not connected)
        self.disconnect_btn.setEnabled(connected)
        self.port_combo.setEnabled(not connected)
        self.scan_btn.setEnabled(not connected)
        self.dtr_btn.setEnabled(connected)
        self.rts_btn.setEnabled(connected)
        if not connected:
            self.set_modem_lines(ModemLines())

    def set_modem_lines(self, lines: ModemLines) -> None:
        self.led_cd.set_on(lines.cd)
        self.led_ri.set_on(lines.ri)
        self.led_dsr.set_on(lines.dsr)
        self.led_cts.set_on(lines.cts)

    def _on_connect(self) -> None:
        port = self.current_port()
        if not port:
            return
        self.connect_requested.emit(port)

    def _on_disconnect(self) -> None:
        self.disconnect_requested.emit()

    def save_state(self, s) -> None:
        s.set_str("com/last_port", self.port_combo.currentData() or "")

    def restore_state(self, s) -> None:
        last = s.get_str("com/last_port", "")
        if last:
            idx = self.port_combo.findData(last)
            if idx >= 0:
                self.port_combo.setCurrentIndex(idx)
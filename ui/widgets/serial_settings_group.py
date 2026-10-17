"""
'Setting serial' group.
"""

from PyQt6.QtCore import QEvent
from PyQt6.QtWidgets import (
    QGroupBox, QGridLayout, QHBoxLayout,
    QComboBox, QLineEdit, QLabel, QWidget,
)


BAUDRATES = [
    600, 1200, 2400, 4800, 9600, 14400, 19200, 28800,
    38400, 56000, 57600, 115200, 128000, 256000,
]

DATABITS = [5, 6, 7, 8]

PARITY_LABELS = [
    ("None",  "N"),
    ("Odd",   "O"),
    ("Even",  "E"),
    ("Mark",  "M"),
    ("Space", "S"),
]

STOPBITS = [
    ("1",   1),
    ("1.5", 1.5),
    ("2",   2),
]

HANDSHAKE = [
    ("None",                 (False, False, False)),
    ("RTS/CTS",              (True,  False, False)),
    ("XON/XOFF",             (False, True,  False)),
    ("RTS/CTS + XON/XOFF",   (True,  True,  False)),
    ("RTS on TX",            (False, False, True)),
]

CUSTOM_LABEL = "Custom…"


class _ComboWithCustom(QWidget):
    def __init__(self, standard_items: list[str], *, default: str,
                 placeholder: str = "", custom_label: str = CUSTOM_LABEL,
                 parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.combo = QComboBox()
        self.combo.addItems(standard_items)
        self.combo.addItem(custom_label)
        self.combo.setCurrentText(default)

        self.custom = QLineEdit()
        self.custom.setPlaceholderText(placeholder)
        self.custom.setEnabled(False)

        self.combo.currentTextChanged.connect(self._on_combo_changed)

        layout.addWidget(self.combo, stretch=1)
        layout.addWidget(self.custom, stretch=1)

        self._custom_label = custom_label

    def _on_combo_changed(self, text: str) -> None:
        is_custom = (text == self._custom_label)
        self.custom.setEnabled(is_custom)
        if not is_custom:
            self.custom.clear()

    def is_custom(self) -> bool:
        return self.combo.currentText() == self._custom_label

    def value_text(self) -> str:
        if self.is_custom():
            return self.custom.text().strip()
        return self.combo.currentText()

    def set_enabled_controls(self, enabled: bool) -> None:
        self.combo.setEnabled(enabled)
        self.custom.setEnabled(enabled and self.is_custom())


class SerialSettingsGroup(QGroupBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()
        self._retranslate()

    def _build(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(10, 18, 10, 10)
        outer.setSpacing(20)

        # left column
        left = QGridLayout()
        left.setHorizontalSpacing(10)
        left.setVerticalSpacing(6)

        self.lbl_baud     = QLabel()
        self.lbl_databits = QLabel()
        self.lbl_stopbits = QLabel()

        self.baud = _ComboWithCustom(
            [str(b) for b in BAUDRATES],
            default="115200",
            placeholder="5…4000000",
        )
        self.databits = _ComboWithCustom(
            [str(b) for b in DATABITS],
            default="8",
            placeholder="5..8",
        )
        self.stopbits = _ComboWithCustom(
            [label for label, _ in STOPBITS],
            default="1",
            placeholder="1 / 1.5 / 2",
        )

        left.addWidget(self.lbl_baud,     0, 0)
        left.addWidget(self.baud,         0, 1)
        left.addWidget(self.lbl_databits, 1, 0)
        left.addWidget(self.databits,     1, 1)
        left.addWidget(self.lbl_stopbits, 2, 0)
        left.addWidget(self.stopbits,     2, 1)
        left.setColumnStretch(1, 1)

        left_w = QWidget()
        left_w.setLayout(left)

        # right column
        right = QGridLayout()
        right.setHorizontalSpacing(10)
        right.setVerticalSpacing(6)

        self.lbl_parity    = QLabel()
        self.lbl_handshake = QLabel()

        self.parity_combo = QComboBox()
        for label, code in PARITY_LABELS:
            self.parity_combo.addItem(label, code)

        self.handshake_combo = QComboBox()
        for label, _ in HANDSHAKE:
            self.handshake_combo.addItem(label)

        right.addWidget(self.lbl_parity,    0, 0)
        right.addWidget(self.parity_combo,  0, 1)
        right.addWidget(self.lbl_handshake, 1, 0)
        right.addWidget(self.handshake_combo, 1, 1)
        right.setColumnStretch(1, 1)

        right_w = QWidget()
        right_w.setLayout(right)

        outer.addWidget(left_w,  stretch=1)
        outer.addWidget(right_w, stretch=1)

    def _retranslate(self) -> None:
        self.setTitle(self.tr("Setting serial"))

        self.lbl_baud.setText(self.tr("Baud rate:"))
        self.lbl_databits.setText(self.tr("Data bits:"))
        self.lbl_stopbits.setText(self.tr("Stop bits:"))
        self.lbl_parity.setText(self.tr("Parity:"))
        self.lbl_handshake.setText(self.tr("Handshaking:"))

        # update "Custom…" entry in each combo
        for cc in (self.baud, self.databits, self.stopbits):
            idx = cc.combo.count() - 1
            if idx >= 0:
                cc.combo.setItemText(idx, self.tr("Custom…"))
                cc._custom_label = self.tr("Custom…")

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate()
        super().changeEvent(event)

    def get_config(self) -> dict:
        try:
            baud = int(self.baud.value_text())
        except ValueError:
            baud = 115200

        try:
            bits = int(self.databits.value_text())
        except ValueError:
            bits = 8
        if bits not in (5, 6, 7, 8):
            bits = 8

        raw_stop = self.stopbits.value_text()
        try:
            stopbits = float(raw_stop)
        except ValueError:
            stopbits = 1.0
        if stopbits not in (1.0, 1.5, 2.0):
            stopbits = 1.0

        parity = self.parity_combo.currentData() or "N"

        hs_label = self.handshake_combo.currentText()
        rtscts, xonxoff, rts_on_tx = False, False, False
        for label, (r, x, rt) in HANDSHAKE:
            if label == hs_label:
                rtscts, xonxoff, rts_on_tx = r, x, rt
                break

        return {
            "baudrate":  baud,
            "bytesize":  bits,
            "parity":    parity,
            "stopbits":  stopbits,
            "rtscts":    rtscts,
            "xonxoff":   xonxoff,
            "rts_on_tx": rts_on_tx,
        }

    def set_enabled_controls(self, enabled: bool) -> None:
        self.baud.set_enabled_controls(enabled)
        self.databits.set_enabled_controls(enabled)
        self.stopbits.set_enabled_controls(enabled)
        self.parity_combo.setEnabled(enabled)
        self.handshake_combo.setEnabled(enabled)

    # -- persistence -------------------------------------------------------
    def save_state(self, s) -> None:
        # baud
        s.set_str("serial/baud",      self.baud.combo.currentText())
        s.set_str("serial/baud_custom", self.baud.custom.text())
        s.set_bool("serial/baud_is_custom", self.baud.is_custom())

        # data bits
        s.set_str("serial/databits",  self.databits.combo.currentText())
        s.set_str("serial/databits_custom", self.databits.custom.text())
        s.set_bool("serial/databits_is_custom", self.databits.is_custom())

        # stop bits
        s.set_str("serial/stopbits",  self.stopbits.combo.currentText())
        s.set_str("serial/stopbits_custom", self.stopbits.custom.text())
        s.set_bool("serial/stopbits_is_custom", self.stopbits.is_custom())

        # parity / handshake
        s.set_int("serial/parity_index", self.parity_combo.currentIndex())
        s.set_int("serial/handshake_index", self.handshake_combo.currentIndex())

    def restore_state(self, s) -> None:
        # baud
        baud_std = s.get_str("serial/baud", "115200")
        self.baud.combo.setCurrentText(baud_std)
        self.baud.custom.setText(s.get_str("serial/baud_custom", ""))
        if s.get_bool("serial/baud_is_custom"):
            self.baud.combo.setCurrentText("Custom…")
            self.baud.custom.setEnabled(True)

        # data bits
        dbits_std = s.get_str("serial/databits", "8")
        self.databits.combo.setCurrentText(dbits_std)
        self.databits.custom.setText(s.get_str("serial/databits_custom", ""))
        if s.get_bool("serial/databits_is_custom"):
            self.databits.combo.setCurrentText("Custom…")
            self.databits.custom.setEnabled(True)

        # stop bits
        sbits_std = s.get_str("serial/stopbits", "1")
        self.stopbits.combo.setCurrentText(sbits_std)
        self.stopbits.custom.setText(s.get_str("serial/stopbits_custom", ""))
        if s.get_bool("serial/stopbits_is_custom"):
            self.stopbits.combo.setCurrentText("Custom…")
            self.stopbits.custom.setEnabled(True)

        # parity / handshake — по индексу
        p_idx = s.get_int("serial/parity_index", 0)
        if 0 <= p_idx < self.parity_combo.count():
            self.parity_combo.setCurrentIndex(p_idx)

        h_idx = s.get_int("serial/handshake_index", 0)
        if 0 <= h_idx < self.handshake_combo.count():
            self.handshake_combo.setCurrentIndex(h_idx)
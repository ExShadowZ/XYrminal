"""
'Setting terminal' group.
"""

from PyQt6.QtCore import pyqtSignal, QEvent
from PyQt6.QtWidgets import (
    QGroupBox, QHBoxLayout, QComboBox, QPushButton, QLabel,
)

from core.formatter import FormatMode
from core.theme import ToggleButton


class TerminalSettingsGroup(QGroupBox):
    autoscroll_changed      = pyqtSignal(bool)
    timestamps_changed      = pyqtSignal(bool)
    format_changed          = pyqtSignal(object)
    clear_requested         = pyqtSignal()
    save_log_requested      = pyqtSignal()
    plot_requested          = pyqtSignal()
    auto_save_toggled       = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._restore_guard = False
        self._build()
        self._retranslate()

    def _build(self) -> None:
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 18, 10, 10)
        row.setSpacing(10)

        self.autoscroll_btn = ToggleButton("", on=True)
        self.autoscroll_btn.toggled_state.connect(self.autoscroll_changed.emit)
        row.addWidget(self.autoscroll_btn)

        self.timestamps_btn = ToggleButton("", on=False)
        self.timestamps_btn.toggled_state.connect(self.timestamps_changed.emit)
        row.addWidget(self.timestamps_btn)

        # --- auto-save toggle ---
        self.autosave_btn = ToggleButton("", on=False)
        self.autosave_btn.toggled_state.connect(self.auto_save_toggled.emit)
        row.addWidget(self.autosave_btn)

        row.addSpacing(20)

        self.lbl_format = QLabel()
        row.addWidget(self.lbl_format)

        self.format_combo = QComboBox()

        for m in (FormatMode.HEX, FormatMode.DEC, FormatMode.OCT, FormatMode.BIN):
            self.format_combo.addItem(m.value, m)

        self.format_combo.insertSeparator(self.format_combo.count())

        for m in (
            FormatMode.ASCII,
            FormatMode.UTF8,
            FormatMode.UTF16LE,
            FormatMode.UTF16BE,
            FormatMode.CP1251,
            FormatMode.CP1252,
            FormatMode.CP866,
            FormatMode.KOI8R,
            FormatMode.LATIN1,
            FormatMode.SHIFTJIS,
            FormatMode.GB2312,
            FormatMode.GBK,
        ):
            self.format_combo.addItem(m.value, m)

        self.format_combo.setCurrentIndex(
            self.format_combo.findData(FormatMode.ASCII)
        )
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
        row.addWidget(self.format_combo)

        self.format_info = QLabel(FormatMode.ASCII.value)
        self.format_info.setProperty("role", "info")
        row.addWidget(self.format_info)

        row.addStretch(1)

        self.plot_btn = QPushButton()
        self.plot_btn.setProperty("btnStyle", "ok")
        self.plot_btn.clicked.connect(self.plot_requested.emit)
        row.addWidget(self.plot_btn)

        self.clear_btn = QPushButton()
        self.clear_btn.clicked.connect(self.clear_requested.emit)
        row.addWidget(self.clear_btn)

        self.save_btn = QPushButton()
        self.save_btn.setProperty("btnStyle", "accent")
        self.save_btn.clicked.connect(self.save_log_requested.emit)
        row.addWidget(self.save_btn)

    def _retranslate(self) -> None:
        self.setTitle(self.tr("Setting terminal"))
        self.autoscroll_btn.setText(self.tr("AutoScroll"))
        self.timestamps_btn.setText(self.tr("Timestamps"))
        self.autosave_btn.setText(self.tr("Auto-save log"))
        self.lbl_format.setText(self.tr("Encoding:")) 
        self.plot_btn.setText(self.tr("Plot"))
        self.clear_btn.setText(self.tr("Clear"))
        self.save_btn.setText(self.tr("Save log"))

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate()
        super().changeEvent(event)

    def current_format(self) -> FormatMode:
        data = self.format_combo.currentData()
        return data if data is not None else FormatMode.ASCII

    def set_format_by_mode(self, mode: FormatMode) -> None:
        idx = self.format_combo.findData(mode)
        if idx >= 0:
            self.format_combo.setCurrentIndex(idx)

    def _on_format_changed(self, _idx: int) -> None:
        mode = self.current_format()
        self.format_info.setText(mode.value)
        if not self._restore_guard:
            self.format_changed.emit(mode)

    # -- persistence -------------------------------------------------------
    def save_state(self, s, prefix: str = "term") -> None:
        s.set_bool(f"{prefix}/autoscroll", self.autoscroll_btn.isChecked())
        s.set_bool(f"{prefix}/timestamps", self.timestamps_btn.isChecked())
        s.set_bool(f"{prefix}/autosave",   self.autosave_btn.isChecked())
        s.set_str(f"{prefix}/format",      self.current_format().value)

    def restore_state(self, s, prefix: str = "term") -> None:
        self._restore_guard = True
        try:
            self.autoscroll_btn.setChecked(s.get_bool(f"{prefix}/autoscroll", True))
            self.timestamps_btn.setChecked(s.get_bool(f"{prefix}/timestamps", False))
            self.autosave_btn.setChecked(s.get_bool(f"{prefix}/autosave", False))

            fmt_str = s.get_str(f"{prefix}/format", FormatMode.ASCII.value)
            try:
                fmt_mode = FormatMode(fmt_str)
            except ValueError:
                fmt_mode = FormatMode.ASCII
            self.set_format_by_mode(fmt_mode)
        finally:
            self._restore_guard = False

        self.autoscroll_changed.emit(self.autoscroll_btn.isChecked())
        self.timestamps_changed.emit(self.timestamps_btn.isChecked())
        self.format_changed.emit(self.current_format())
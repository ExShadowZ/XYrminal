"""
'Transmit' group — macros, file row, input line, Send / CR / HEX.

Layout (top → bottom):
    [file_path...........................] [Browse] [Raw ▼] [Send file]
    [████████████░░░░░░░░] 45%  512 KB / 1.2 MB                 [Cancel]
    [M1] [M2] ... [M10]    [Stop]     ← or [S1]... for scenario slots
    [input.......................] [Send] [HEX] [+CR] [CR=CR+LF]

If `show_file=False`, the file row and progress row are not created at
all (used by TCP/UDP server tabs where file transfer makes no sense).

Scenario buttons (S1…S10) execute a .xyscen file step by step via
ScenarioExecutor. While a scenario is running, all input and macro
buttons are disabled, and a Stop button appears next to the macro row.
RX bytes are routed into the executor via push_rx() so that `expect`
steps can match incoming data.
"""

from __future__ import annotations

import os

from PyQt6.QtCore import pyqtSignal, QEvent, Qt, QTimer
from PyQt6.QtWidgets import (
    QGroupBox, QHBoxLayout, QVBoxLayout, QLineEdit, QPushButton,
    QComboBox, QProgressBar, QFileDialog, QLabel, QMessageBox, QWidget,
)

from core.macros import MacroStore, MACRO_COUNT, parse_hex
from core.scenario import ScenarioExecutor
from core.settings import Settings
from core.theme import ToggleButton


HISTORY_MAX = 100


PROTOCOLS = [
    ("raw",    "Raw"),
    ("xmodem", "XMODEM"),
    ("ymodem", "YMODEM"),
    ("zmodem", "ZMODEM (not implemented)"),
]


class TransmitGroup(QGroupBox):
    send_requested        = pyqtSignal(bytes)
    file_send_requested   = pyqtSignal(str, str)   # path, protocol
    file_cancel_requested = pyqtSignal()
    scenario_log_line     = pyqtSignal(str)        # extra lines for terminal

    def __init__(self, prefix: str = "com", *,
                 show_file: bool = True, parent=None):
        super().__init__(parent)
        self._prefix = prefix
        self._show_file = show_file
        self._history: list[str] = []
        self._history_pos: int = -1
        self._macro_buttons: list[QPushButton] = []
        self._settings = Settings()

        self._scenario = ScenarioExecutor(self)
        self._scenario.send_requested.connect(self.send_requested)
        self._scenario.line.connect(self.scenario_log_line)
        self._scenario.busy_changed.connect(self._on_scenario_busy)

        self._build()
        self._retranslate()
        self._refresh_macros()
        if self._show_file:
            self._restore_file_path()

        MacroStore.instance().macros_changed.connect(self._on_macros_changed)

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 18, 10, 10)
        outer.setSpacing(6)

        if self._show_file:
            file_row = QHBoxLayout()
            file_row.setSpacing(6)

            self.file_edit = QLineEdit()
            self.file_edit.setPlaceholderText("")
            file_row.addWidget(self.file_edit, stretch=1)

            self.browse_btn = QPushButton()
            self.browse_btn.clicked.connect(self._on_browse)
            file_row.addWidget(self.browse_btn)

            self.proto_combo = QComboBox()
            for _key, label in PROTOCOLS:
                self.proto_combo.addItem(label, _key)
            self.proto_combo.setCurrentIndex(0)
            self.proto_combo.currentIndexChanged.connect(self._on_proto_changed)
            file_row.addWidget(self.proto_combo)

            self.file_send_btn = QPushButton()
            self.file_send_btn.setProperty("btnStyle", "ok")
            self.file_send_btn.clicked.connect(self._on_file_send)
            file_row.addWidget(self.file_send_btn)

            outer.addLayout(file_row)

            self.progress_row = QHBoxLayout()
            self.progress_row.setSpacing(6)

            self.progress = QProgressBar()
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            self.progress.setTextVisible(True)
            self.progress_row.addWidget(self.progress, stretch=1)

            self.cancel_btn = QPushButton()
            self.cancel_btn.setProperty("btnStyle", "danger")
            self.cancel_btn.clicked.connect(self._on_cancel)
            self.progress_row.addWidget(self.cancel_btn)

            outer.addLayout(self.progress_row)
            self._set_progress_visible(False)
        else:
            self.file_edit     = QLineEdit(self)
            self.browse_btn    = QPushButton(self)
            self.proto_combo   = QComboBox(self)
            self.file_send_btn = QPushButton(self)
            self.progress      = QProgressBar(self)
            self.cancel_btn    = QPushButton(self)
            self.file_edit.hide()
            self.browse_btn.hide()
            self.proto_combo.hide()
            self.file_send_btn.hide()
            self.progress.hide()
            self.cancel_btn.hide()

        macro_row = QHBoxLayout()
        macro_row.setSpacing(4)

        for i in range(MACRO_COUNT):
            btn = QPushButton(f"M{i + 1}")
            btn.setProperty("btnStyle", "macro")
            btn.setFixedHeight(22)
            btn.setMinimumWidth(38)
            btn.clicked.connect(lambda _checked=False, idx=i: self._on_macro(idx))
            macro_row.addWidget(btn)
            self._macro_buttons.append(btn)

        self.stop_scenario_btn = QPushButton()
        self.stop_scenario_btn.setProperty("btnStyle", "danger")
        self.stop_scenario_btn.setFixedHeight(22)
        self.stop_scenario_btn.setMinimumWidth(60)
        self.stop_scenario_btn.setVisible(False)
        self.stop_scenario_btn.clicked.connect(self._on_stop_scenario_clicked)
        macro_row.addWidget(self.stop_scenario_btn)

        macro_row.addStretch(1)
        outer.addLayout(macro_row)

        row = QHBoxLayout()
        row.setSpacing(8)

        self.input = QLineEdit()
        self.input.returnPressed.connect(self._on_send)
        self.input.installEventFilter(self)
        row.addWidget(self.input, stretch=1)

        self.send_btn = QPushButton()
        self.send_btn.setProperty("btnStyle", "accent")
        self.send_btn.clicked.connect(self._on_send)
        row.addWidget(self.send_btn)

        self.hex_btn = ToggleButton("", on=False)
        row.addWidget(self.hex_btn)

        self.cr_btn = ToggleButton("", on=False)
        row.addWidget(self.cr_btn)

        self.crlf_btn = ToggleButton("", on=False)
        row.addWidget(self.crlf_btn)

        outer.addLayout(row)

    def _retranslate(self) -> None:
        self.setTitle(self.tr("Transmit"))
        self.input.setPlaceholderText(
            self.tr("Type data and press Enter or Send…")
        )
        self.send_btn.setText(self.tr("Send"))
        self.hex_btn.setText(self.tr("HEX"))
        self.cr_btn.setText(self.tr("+CR"))
        self.crlf_btn.setText(self.tr("CR=CR+LF"))
        self.stop_scenario_btn.setText(self.tr("Stop"))

        if self._show_file:
            self.file_edit.setPlaceholderText(self.tr("No file selected"))
            self.browse_btn.setText(self.tr("Browse…"))
            self.file_send_btn.setText(self.tr("Send file"))
            self.cancel_btn.setText(self.tr("Cancel transfer"))

            for idx, (key, default_label) in enumerate(PROTOCOLS):
                label = default_label
                if key == "raw":
                    label = self.tr("Raw")
                elif key == "xmodem":
                    label = self.tr("XMODEM")
                elif key == "ymodem":
                    label = self.tr("YMODEM")
                elif key == "zmodem":
                    label = self.tr("ZMODEM (not implemented)")
                self.proto_combo.setItemText(idx, label)

        self._refresh_macros()

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate()
        super().changeEvent(event)

    def _restore_file_path(self) -> None:
        if not self._settings.get_bool("transfer/keep_last_path", False):
            self.file_edit.clear()
            self.proto_combo.setCurrentIndex(0)
            return

        path = self._settings.get_str(f"transmit/{self._prefix}/file_path", "")
        if path:
            self.file_edit.setText(path)

        proto = self._settings.get_str(f"transmit/{self._prefix}/proto", "raw")
        idx = self.proto_combo.findData(proto)
        if idx >= 0:
            self.proto_combo.setCurrentIndex(idx)

    def _save_file_path(self) -> None:
        if not self._show_file:
            return
        if not self._settings.get_bool("transfer/keep_last_path", False):
            self._settings.set_str(f"transmit/{self._prefix}/file_path", "")
            self._settings.set_str(f"transmit/{self._prefix}/proto", "raw")
            return
        self._settings.set_str(f"transmit/{self._prefix}/file_path",
                               self.file_edit.text().strip())
        self._settings.set_str(f"transmit/{self._prefix}/proto",
                               self.proto_combo.currentData() or "raw")

    def refresh_file_path_state(self) -> None:
        if not self._show_file:
            return
        if not self._settings.get_bool("transfer/keep_last_path", False):
            self.file_edit.clear()
            self.proto_combo.setCurrentIndex(0)
            self._settings.set_str(f"transmit/{self._prefix}/file_path", "")
            self._settings.set_str(f"transmit/{self._prefix}/proto", "raw")

    def _on_proto_changed(self, _idx: int) -> None:
        self._save_file_path()

    def _on_browse(self) -> None:
        start_dir = os.path.dirname(self.file_edit.text().strip()) or ""
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Select file to send"),
            start_dir,
            self.tr("All files (*)"),
        )
        if path:
            self.file_edit.setText(path)
            self._save_file_path()

    def _on_file_send(self) -> None:
        if not self._show_file:
            return
        path = self.file_edit.text().strip()
        if not path:
            QMessageBox.warning(
                self, "XYrminal",
                self.tr("Select a file first.")
            )
            return
        if not os.path.isfile(path):
            QMessageBox.warning(
                self, "XYrminal",
                self.tr("File not found: {p}").format(p=path)
            )
            return

        proto = self.proto_combo.currentData() or "raw"
        if proto == "zmodem":
            QMessageBox.information(
                self, "XYrminal",
                self.tr("ZMODEM not implemented yet.")
            )
            return

        max_mb = self._settings.get_int("transfer/max_size_mb", 512)
        size = os.path.getsize(path)
        if size > max_mb * 1024 * 1024:
            QMessageBox.warning(
                self, "XYrminal",
                self.tr("File is larger than the configured limit ({m} MB).")
                .format(m=max_mb)
            )
            return

        self._save_file_path()
        self.file_send_requested.emit(path, proto)

    def _on_cancel(self) -> None:
        self.file_cancel_requested.emit()

    def _set_progress_visible(self, visible: bool) -> None:
        if not self._show_file:
            return
        self.progress.setVisible(visible)
        self.cancel_btn.setVisible(visible)

    def set_transfer_active(self, active: bool) -> None:
        for w in (self.input, self.send_btn,
                self.hex_btn, self.cr_btn, self.crlf_btn):
            w.setEnabled(not active)

        if self._show_file:
            for w in (self.file_send_btn, self.browse_btn,
                    self.file_edit, self.proto_combo):
                w.setEnabled(not active)

        if active:
            for btn in self._macro_buttons:
                btn.setEnabled(False)
        else:
            self._refresh_macros()

        self._set_progress_visible(active)
        if active and self._show_file:
            self.progress.setValue(0)
            self.progress.setFormat("%p%")

    def on_transfer_progress(self, sent: int, total: int) -> None:
        if not self._show_file:
            return
        if total <= 0:
            self.progress.setValue(0)
            self.progress.setFormat("0%")
            return
        pct = int(sent * 100 / total)
        self.progress.setValue(pct)
        self.progress.setFormat(self.tr("%p% — {a} / {b}").format(
            a=_human_size(sent), b=_human_size(total)
        ))

    def on_transfer_status(self, text: str) -> None:
        if not self._show_file:
            return
        self.progress.setFormat(text)

    def on_transfer_finished(self, ok: bool, err: str) -> None:
        if not self._show_file:
            return
        if ok:
            self.progress.setValue(100)
            self.progress.setFormat(self.tr("Done"))
        else:
            self.progress.setFormat(err or self.tr("Failed"))

        QTimer.singleShot(2000, lambda: self._hide_after_transfer(ok))

    def _hide_after_transfer(self, ok: bool) -> None:
        self._set_progress_visible(False)
        for w in (self.input, self.send_btn,
                  self.hex_btn, self.cr_btn, self.crlf_btn):
            w.setEnabled(True)
        if self._show_file:
            for w in (self.file_send_btn, self.browse_btn,
                      self.file_edit, self.proto_combo):
                w.setEnabled(True)
        self._refresh_macros()

    def _on_macros_changed(self, prefix: str) -> None:
        if prefix == self._prefix or prefix == "all":
            self._refresh_macros()

    def _refresh_macros(self) -> None:
        store = MacroStore.instance()

        for i, btn in enumerate(self._macro_buttons):
            is_script = store.is_script(self._prefix, i)

            if is_script:
                path = store.scenario_path(self._prefix, i)
                empty = (path == "")
                btn.setText(f"S{i + 1}")
                btn.setEnabled(not empty)
                if empty:
                    btn.setToolTip(self.tr("Empty — button disabled"))
                else:
                    btn.setToolTip(
                        self.tr("Scenario: {p}").format(p=path)
                    )
                continue

            btn.setText(f"M{i + 1}")
            text, is_hex, add_cr, crlf = store.get(self._prefix, i)
            empty = text.strip() == ""
            btn.setEnabled(not empty)

            if empty:
                btn.setToolTip("")
                continue

            if is_hex:
                parsed = parse_hex(text)
                if parsed is None:
                    tip = self.tr("HEX (invalid): {t}").format(t=text)
                else:
                    tip = self.tr("HEX: {t}").format(t=text)
            else:
                tip = self.tr("Text: {t}").format(t=text)
                if add_cr:
                    suffix = "CR+LF" if crlf else "CR"
                    tip += f"  [+{suffix}]"

            btn.setToolTip(tip)

    def _on_macro(self, index: int) -> None:
        store = MacroStore.instance()

        if store.is_script(self._prefix, index):
            self._run_scenario(index)
            return

        data = store.as_bytes(self._prefix, index)
        if data is None or not data:
            return
        self.send_requested.emit(data)

    def _run_scenario(self, index: int) -> None:
        store = MacroStore.instance()
        path = store.scenario_path(self._prefix, index)
        if not path:
            return
        if self._scenario.is_busy():
            return
        self._scenario.start(path)

    def _on_scenario_busy(self, busy: bool) -> None:
        for w in (self.input, self.send_btn,
                self.hex_btn, self.cr_btn, self.crlf_btn):
            w.setEnabled(not busy)

        if busy:
            for btn in self._macro_buttons:
                btn.setEnabled(False)
        else:
            self._refresh_macros()

        self.stop_scenario_btn.setVisible(busy)
        self.stop_scenario_btn.setEnabled(busy)

    def _on_stop_scenario_clicked(self) -> None:
        self.stop_scenario()

    def push_rx(self, chunk: bytes) -> None:
        self._scenario.push_rx(chunk)

    def is_scenario_running(self) -> bool:
        return self._scenario.is_busy()

    def stop_scenario(self) -> None:
        self._scenario.stop()

    def eventFilter(self, obj, event) -> bool:
        if obj is self.input and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Up:
                self._history_prev()
                return True
            if key == Qt.Key.Key_Down:
                self._history_next()
                return True
        return super().eventFilter(obj, event)

    def _push_history(self, line: str) -> None:
        if not line:
            return
        if self._history and self._history[-1] == line:
            return
        self._history.append(line)
        if len(self._history) > HISTORY_MAX:
            self._history.pop(0)

    def _history_prev(self) -> None:
        if not self._history:
            return
        if self._history_pos == -1:
            self._history_pos = len(self._history) - 1
        elif self._history_pos > 0:
            self._history_pos -= 1
        self.input.setText(self._history[self._history_pos])
        self.input.setCursorPosition(len(self.input.text()))

    def _history_next(self) -> None:
        if self._history_pos == -1:
            return
        if self._history_pos < len(self._history) - 1:
            self._history_pos += 1
            self.input.setText(self._history[self._history_pos])
            self.input.setCursorPosition(len(self.input.text()))
        else:
            self._history_pos = -1
            self.input.clear()

    def _on_send(self) -> None:
        text = self.input.text()
        self._history_pos = -1

        if self.hex_btn.isChecked():
            data = parse_hex(text)
            if data is None:
                self.input.setStyleSheet("border: 1px solid #e74c3c;")
                return
            self.input.setStyleSheet("")
        else:
            data = text.encode("utf-8", errors="replace")
            if self.cr_btn.isChecked():
                terminator = b"\r\n" if self.crlf_btn.isChecked() else b"\r"
                data += terminator

        if not data:
            return
        self._push_history(text)
        self.send_requested.emit(data)

    def save_state(self, s, prefix: str) -> None:
        s.set_bool(f"{prefix}/hex",  self.hex_btn.isChecked())
        s.set_bool(f"{prefix}/cr",   self.cr_btn.isChecked())
        s.set_bool(f"{prefix}/crlf", self.crlf_btn.isChecked())

    def restore_state(self, s, prefix: str) -> None:
        self.hex_btn.setChecked(s.get_bool(f"{prefix}/hex", False))
        self.cr_btn.setChecked(s.get_bool(f"{prefix}/cr", False))
        self.crlf_btn.setChecked(s.get_bool(f"{prefix}/crlf", False))


def _human_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    if n < 1024 * 1024 * 1024:
        return f"{n / (1024 * 1024):.2f} MB"
    return f"{n / (1024 * 1024 * 1024):.2f} GB"
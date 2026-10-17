"""
COM tab — glues together the widgets and the SerialWorker.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QFileDialog,
)

from core.formatter import format_bytes, format_preview, FormatMode, RAW_MODES
from core.log_writer import LogWriter
from core.modem_lines import ModemLines
from core.paths import app_root
from core.plot_store import PlotStore
from core.serial_worker import SerialWorker
from core.file_sender import FileSender
from core.settings import Settings

from ui.widgets.connecting_group        import ConnectingGroup
from ui.widgets.serial_settings_group   import SerialSettingsGroup
from ui.widgets.terminal_settings_group import TerminalSettingsGroup
from ui.widgets.terminal_view           import TerminalView
from ui.widgets.transmit_group          import TransmitGroup
from ui.widgets.plot_widget             import PlotWidget

from ui.dialogs import PlotSettingsDialog


_LOGS_DIR = app_root() / "logs"


class ComTab(QWidget):
    counters_changed = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._format_mode = FormatMode.ASCII
        self._tx_bytes = 0
        self._rx_bytes = 0
        self._group_visible: dict[str, bool] = {
            "connecting":    True,
            "settings":      True,
            "term_settings": True,
        }

        self.plot_widget: Optional[PlotWidget] = None
        self.plot_dialog: Optional[PlotSettingsDialog] = None

        self._file_sender: Optional[FileSender] = None
        self._settings = Settings()

        self._build_ui()
        self._setup_worker()
        self._wire_signals()

        self._apply_all_visibility()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.top = QHBoxLayout()
        self.top.setSpacing(8)

        self.connecting = ConnectingGroup()
        self.settings   = SerialSettingsGroup()

        self.top.addWidget(self.connecting, stretch=3)
        self.top.addWidget(self.settings,   stretch=7)
        root.addLayout(self.top)

        self.term_settings = TerminalSettingsGroup()
        root.addWidget(self.term_settings)

        self.term_area = QWidget()
        self.term_area_layout = QHBoxLayout(self.term_area)
        self.term_area_layout.setContentsMargins(0, 0, 0, 0)
        self.term_area_layout.setSpacing(8)

        self.terminal = TerminalView()
        self.terminal.set_trigger_prefix("com")
        self.term_area_layout.addWidget(self.terminal, stretch=1)

        root.addWidget(self.term_area, stretch=1)

        self.transmit = TransmitGroup(prefix="com")
        root.addWidget(self.transmit)

        self.log_writer = LogWriter(_LOGS_DIR, suffix="com")
        self.terminal.set_log_writer(self.log_writer)

    def _setup_worker(self) -> None:
        self.worker = SerialWorker(self)

    def _wire_signals(self) -> None:
        self.connecting.connect_requested.connect(self._on_connect)
        self.connecting.disconnect_requested.connect(self._on_disconnect)
        self.connecting.dtr_changed.connect(self.worker.set_dtr)
        self.connecting.rts_changed.connect(self.worker.set_rts)

        self.term_settings.autoscroll_changed.connect(self.terminal.set_autoscroll)
        self.term_settings.timestamps_changed.connect(self.terminal.set_timestamps)
        self.term_settings.format_changed.connect(self._on_format_changed)
        self.term_settings.clear_requested.connect(self._on_clear)
        self.term_settings.save_log_requested.connect(self._on_save_log)
        self.term_settings.plot_requested.connect(self._on_plot_requested)
        self.term_settings.auto_save_toggled.connect(self._on_auto_save_toggled)

        self.terminal.raw_text_received.connect(PlotStore.instance().feed)

        self.transmit.send_requested.connect(self._on_send)
        self.transmit.file_send_requested.connect(self._on_file_send)
        self.transmit.file_cancel_requested.connect(self._on_file_cancel)
        self.transmit.scenario_log_line.connect(self._on_scenario_log_line)

        self.worker.data_received.connect(self._on_data_received)
        self.worker.opened.connect(self._on_opened)
        self.worker.closed.connect(self._on_closed)
        self.worker.error.connect(self._on_error)
        self.worker.modem_lines_changed.connect(self._on_modem_lines)

    # -- auto-save ---------------------------------------------------------
    def _on_auto_save_toggled(self, on: bool) -> None:
        if on:
            try:
                path = self.log_writer.start_auto_save()
                self.terminal.append_text(f"[LOG] auto-save: {path}\n")
            except Exception as exc:
                self.terminal.append_text(f"[LOG] auto-save failed: {exc}\n")
        else:
            p = self.log_writer.stop_auto_save()
            if p is not None:
                self.terminal.append_text(f"[LOG] auto-save stopped: {p.name}\n")

    # -- file transfer -----------------------------------------------------
    def _on_file_send(self, path: str, protocol: str) -> None:
        if not self.worker.is_open():
            QMessageBox.warning(self, "XYrminal", self.tr("Not connected"))
            return

        if self._file_sender is not None and self._file_sender.is_active():
            QMessageBox.information(self, "XYrminal", self.tr("Transfer already running"))
            return

        chunk = self._settings.get_int("transfer/chunk_size", 256)
        delay = self._settings.get_int("transfer/chunk_delay_ms", 10)

        self._file_sender = FileSender(self.worker.write, self)
        self._file_sender.progress.connect(self.transmit.on_transfer_progress)
        self._file_sender.status.connect(self.transmit.on_transfer_status)
        self._file_sender.finished.connect(self.transmit.on_transfer_finished)
        self._file_sender.finished.connect(self._on_transfer_finished)

        self.transmit.set_transfer_active(True)
        self._file_sender.start(path, protocol, chunk_size=chunk, delay_ms=delay)

    def _on_file_cancel(self) -> None:
        if self._file_sender is not None:
            self._file_sender.cancel()

    def _on_transfer_finished(self, ok: bool, err: str) -> None:
        if self._file_sender is not None:
            self._file_sender.stop()
        self._file_sender = None

    def worker_is_connected(self) -> bool:
        return self.worker.is_open()

    # -- plot --------------------------------------------------------------
    def _on_plot_requested(self) -> None:
        if self.plot_dialog is None:
            self.plot_dialog = PlotSettingsDialog(self)
            self.plot_dialog.layout_requested.connect(self._on_plot_layout)
            if self.plot_widget is not None:
                self.plot_dialog.attach_plot_widget(self.plot_widget)
        self.plot_dialog.show()
        self.plot_dialog.raise_()
        self.plot_dialog.activateWindow()

    def _on_plot_layout(self, show: bool) -> None:
        if show:
            self._show_plot()
        else:
            self._hide_plot()

    def _show_plot(self) -> None:
        if self.plot_widget is not None:
            return
        self.plot_widget = PlotWidget(self.term_area)
        self.term_area_layout.addWidget(self.plot_widget, stretch=1)
        self.terminal.setMinimumWidth(200)
        self.plot_widget.setMinimumWidth(200)
        if self.plot_dialog is not None:
            self.plot_dialog.attach_plot_widget(self.plot_widget)

    def _hide_plot(self) -> None:
        if self.plot_widget is None:
            return
        self.term_area_layout.removeWidget(self.plot_widget)
        self.plot_widget.setParent(None)
        self.plot_widget.deleteLater()
        self.plot_widget = None
        PlotStore.instance().clear_data()
        if self.plot_dialog is not None:
            self.plot_dialog.attach_plot_widget(None)

    # -- state -------------------------------------------------------------
    def save_state(self, s) -> None:
        self.connecting.save_state(s)
        self.settings.save_state(s)
        self.transmit.save_state(s, "com")
        self.term_settings.save_state(s, "com_term")

        for name in ("connecting", "settings", "term_settings"):
            s.set_bool(f"com/visible/{name}", self._group_visible.get(name, True))

    def restore_state(self, s) -> None:
        self.settings.restore_state(s)
        self.connecting.restore_state(s)
        self.transmit.restore_state(s, "com")
        self.term_settings.restore_state(s, "com_term")

        for name in ("connecting", "settings", "term_settings"):
            self._group_visible[name] = s.get_bool(f"com/visible/{name}", True)

        self._apply_all_visibility()

    # -- counters ----------------------------------------------------------
    def counters(self) -> tuple[int, int]:
        return self._tx_bytes, self._rx_bytes

    def reset_counters(self) -> None:
        self._tx_bytes = 0
        self._rx_bytes = 0
        self.counters_changed.emit(self._tx_bytes, self._rx_bytes)

    def available_groups(self) -> dict[str, str]:
        return {
            "connecting":    self.tr("Connecting"),
            "settings":      self.tr("Setting serial"),
            "term_settings": self.tr("Setting terminal"),
        }

    def set_group_visible(self, name: str, visible: bool) -> None:
        if name not in self._group_visible:
            return
        self._group_visible[name] = visible
        self._apply_visibility(name)

    def is_group_visible(self, name: str) -> bool:
        return self._group_visible.get(name, True)

    def _apply_visibility(self, name: str) -> None:
        w = {
            "connecting":    self.connecting,
            "settings":      self.settings,
            "term_settings": self.term_settings,
        }.get(name)
        if w is not None:
            w.setVisible(self._group_visible.get(name, True))

    def _apply_all_visibility(self) -> None:
        for name in self._group_visible:
            self._apply_visibility(name)

    # -- logs --------------------------------------------------------------
    def log_dir(self) -> Path:
        return self.log_writer.directory

    def save_log_default(self) -> Optional[Path]:
        if not self.log_writer.has_data():
            QMessageBox.information(self, "XYrminal", self.tr("Nothing to save."))
            return None
        try:
            return self.log_writer.save()
        except Exception as exc:
            QMessageBox.warning(self, "XYrminal",
                                self.tr("Save failed: {err}").format(err=exc))
            return None

    def save_log_as_dialog(self, parent=None) -> Optional[Path]:
        if not self.log_writer.has_data():
            QMessageBox.information(self, "XYrminal", self.tr("Nothing to save."))
            return None

        ext = self.log_writer.extension()
        suggested = str(
            self.log_writer.directory
            / f"{self.log_writer.default_stem()}{ext}"
        )
        path, _ = QFileDialog.getSaveFileName(
            parent or self,
            self.tr("Save log as"),
            suggested,
            self.tr(
                "XYrminal logs (*.xyrm *.xyrmc);;"
                "Plain text (*.xyrm);;"
                "Colored HTML (*.xyrmc);;"
                "All files (*)"
            ),
        )
        if not path:
            return None
        try:
            return self.log_writer.save_as(path)
        except Exception as exc:
            QMessageBox.warning(self, "XYrminal",
                                self.tr("Save failed: {err}").format(err=exc))
            return None

    # -- slots -------------------------------------------------------------
    def _on_connect(self, port: str) -> None:
        cfg = self.settings.get_config()
        cfg["port"] = port
        self.worker.open_port(cfg)

    def _on_disconnect(self) -> None:
        self.worker.close_port()

    def _on_opened(self, port: str) -> None:
        self.connecting.set_connected(True)
        self.settings.set_enabled_controls(False)

    def _on_closed(self) -> None:
        self.connecting.set_connected(False)
        self.settings.set_enabled_controls(True)
        self.connecting.dtr_btn.setChecked(False)
        self.connecting.rts_btn.setChecked(False)
        self.connecting.set_modem_lines(ModemLines())

    def _on_modem_lines(self, lines: ModemLines) -> None:
        self.connecting.set_modem_lines(lines)

    def _on_error(self, msg: str) -> None:
        self.terminal.append_text(f"[ERR] {msg}\n")
        QMessageBox.warning(self, "XYrminal", msg)

    def _on_data_received(self, chunk: bytes) -> None:
        try:
            if self.transmit.is_scenario_running():
                self.transmit.push_rx(chunk)
        except Exception:
            pass

        if self._file_sender is not None and self._file_sender.is_active():
            self._file_sender.io.push(chunk)

        self._rx_bytes += len(chunk)
        self.counters_changed.emit(self._tx_bytes, self._rx_bytes)

        text = format_bytes(chunk, self._format_mode)
        is_raw = self._format_mode in RAW_MODES
        self.terminal.append_text(text, raw=is_raw)

    def _on_send(self, data: bytes) -> None:
        if not data:
            return
        self._tx_bytes += len(data)
        self.counters_changed.emit(self._tx_bytes, self._rx_bytes)
        preview = format_preview(data)
        self.terminal.append_tx_text(preview)
        self.worker.write(data)

    def _on_format_changed(self, mode: FormatMode) -> None:
        self._format_mode = mode
        self.terminal.reset_partial()

    def _on_clear(self) -> None:
        self.terminal.clear_terminal()

    def _on_save_log(self) -> None:
        path = self.save_log_default()
        if path is not None:
            QMessageBox.information(
                self, "XYrminal",
                self.tr("Saved: {name}").format(name=path.name)
            )

    def _on_scenario_log_line(self, line: str) -> None:
        self.terminal.append_scenario_text(line)

    def shutdown(self) -> None:
        try:
            self.transmit.stop_scenario()
        except Exception:
            pass
        try:
            self.log_writer.stop_auto_save()
        except Exception:
            pass
        try:
            if self._file_sender is not None:
                self._file_sender.stop()
        except Exception:
            pass
        try:
            PlotStore.instance().stop()
        except Exception:
            pass
        try:
            if self.plot_dialog is not None:
                self.plot_dialog.close()
        except Exception:
            pass
        try:
            self.worker.close_port()
        except Exception:
            pass
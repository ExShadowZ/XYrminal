"""
Main window: menu bar + status bar + 5 top-level tabs
(COM / TCP Client / TCP Server / UDP Client / UDP Server).
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QUrl, QEvent, Qt
from PyQt6.QtGui import (
    QAction, QActionGroup, QDesktopServices, QIcon, QPixmap, QColor, QCloseEvent,
)
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QMessageBox, QLabel, QPushButton,
    QFileDialog,
)

from core.paths import app_root
from core.settings import Settings
from core.macros import MacroStore, PREFIXES, prefix_label
from core.log_writer import FORMAT_PLAIN, FORMAT_RICH, LogWriter
from core.theme import (
    available_themes, current_theme_choice, set_theme, ThemeManager, theme_icon,
)
from core.ui_scale import (
    ALLOWED_SCALES, ui_scale, set_ui_scale, scale_changed_signal,
)
from core.custom_theme import CUSTOM_THEME_ID
from core.term_colors import (
    TerminalColorManager,
    NAMED_COLOR_ORDER,
    CATEGORY_ORDER,
    category_label,
    color_label,
    color_hex,
)
from core.i18n import (
    LANGUAGES,
    apply_language,
    current_language,
    language_changed_signal,
    language_label,
)

from ui.tabs.com_tab          import ComTab
from ui.tabs.tcp_client_tab   import TcpClientTab
from ui.tabs.tcp_server_tab   import TcpServerTab
from ui.tabs.udp_client_tab   import UdpClientTab
from ui.tabs.udp_server_tab   import UdpServerTab
from ui.dialogs import (
    AboutDialog, InfoDialog, MacroEditorDialog, TransferSettingsDialog,
    NetworkInfoDialog, CustomThemeDialog,
)


_LOGS_DIR = app_root() / "logs"


def _color_icon(hex_color: str, size: int = 14) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(QColor(hex_color))
    return QIcon(pix)


def _qcolor_icon(qcolor: QColor, size: int = 14) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(qcolor)
    return QIcon(pix)


def _prefix_label_tr(window: "MainWindow", prefix: str) -> str:
    label = prefix_label(prefix)
    if label == "TCP Client":
        return window.tr("TCP Client")
    if label == "TCP Server":
        return window.tr("TCP Server")
    if label == "UDP Client":
        return window.tr("UDP Client")
    if label == "UDP Server":
        return window.tr("UDP Server")
    return label


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("XYrminal")
        self.resize(1200, 760)
        self.setMinimumSize(700, 450)

        self._settings = Settings()

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.com_tab         = ComTab()
        self.tcp_client_tab  = TcpClientTab()
        self.tcp_server_tab  = TcpServerTab()
        self.udp_client_tab  = UdpClientTab()
        self.udp_server_tab  = UdpServerTab()

        self.tabs.addTab(self.com_tab,        "COM")
        self.tabs.addTab(self.tcp_client_tab, "TCP Client")
        self.tabs.addTab(self.tcp_server_tab, "TCP Server")
        self.tabs.addTab(self.udp_client_tab, "UDP Client")
        self.tabs.addTab(self.udp_server_tab, "UDP Server")

        self.setCentralWidget(self.tabs)

        self._build_status_bar()
        self._build_menu()

        self.tabs.currentChanged.connect(self._on_tab_changed)

        for t in (self.com_tab, self.tcp_client_tab, self.tcp_server_tab,
                  self.udp_client_tab, self.udp_server_tab):
            t.counters_changed.connect(self._on_counters_changed)

        self._rebuild_view_menu()
        self._refresh_counters()

        TerminalColorManager.instance().colors_changed.connect(
            self._rebuild_terminal_color_menu
        )
        language_changed_signal().connect(self._on_language_changed)

        ThemeManager.instance().theme_changed.connect(
            self._on_theme_changed
        )
        scale_changed_signal().connect(self._on_ui_scale_changed)

        self._restore_all()

    def _restore_all(self) -> None:
        s = self._settings

        geo = s.get_bytes("window/geometry")
        if geo:
            self.restoreGeometry(geo)

        idx = s.get_int("window/active_tab", 0)
        if 0 <= idx < self.tabs.count():
            self.tabs.setCurrentIndex(idx)

        fmt = s.get_str("log/format", FORMAT_PLAIN)
        self._apply_log_format(fmt)

        self.com_tab.restore_state(s)
        self.tcp_client_tab.restore_state(s)
        self.tcp_server_tab.restore_state(s)
        self.udp_client_tab.restore_state(s)
        self.udp_server_tab.restore_state(s)

        self._rebuild_view_menu()
        self._rebuild_save_format_menu()

    def _save_all(self) -> None:
        s = self._settings

        s.set_bytes("window/geometry", bytes(self.saveGeometry()))
        s.set_int("window/active_tab", self.tabs.currentIndex())

        self.com_tab.save_state(s)
        self.tcp_client_tab.save_state(s)
        self.tcp_server_tab.save_state(s)
        self.udp_client_tab.save_state(s)
        self.udp_server_tab.save_state(s)

        s.sync()

    def closeEvent(self, event: QCloseEvent) -> None:
        try:
            self._save_all()
        except Exception:
            pass
        super().closeEvent(event)

    def _build_status_bar(self) -> None:
        sb = self.statusBar()
        sb.setSizeGripEnabled(False)

        self.lbl_tx = QLabel()
        self.lbl_rx = QLabel()
        for lbl in (self.lbl_tx, self.lbl_rx):
            lbl.setMinimumWidth(90)

        self.btn_reset_counters = QPushButton()
        self.btn_reset_counters.clicked.connect(self._on_reset_counters)

        sb.addWidget(self.lbl_tx)
        sb.addWidget(self.lbl_rx)
        sb.addPermanentWidget(self.btn_reset_counters)

        self._retranslate_status_bar()

    def _retranslate_status_bar(self) -> None:
        self.btn_reset_counters.setText(self.tr("Reset"))

    def _refresh_counters(self) -> None:
        tab = self._current_tab()
        if tab is None:
            tx = rx = 0
        else:
            tx, rx = tab.counters()
        self.lbl_tx.setText(f"TX: {tx}")
        self.lbl_rx.setText(f"RX: {rx}")

    def _on_counters_changed(self, _tx: int, _rx: int) -> None:
        sender = self.sender()
        if sender is self._current_tab():
            self._refresh_counters()

    def _on_reset_counters(self) -> None:
        tab = self._current_tab()
        if tab is not None:
            tab.reset_counters()
        self._refresh_counters()

    def _build_menu(self) -> None:
        mb = self.menuBar()

        self.logs_menu = mb.addMenu("")
        self.act_save_log         = QAction(self)
        self.act_save_log_as      = QAction(self)
        self.act_open_log_file    = QAction(self)
        self.act_open_logs_folder = QAction(self)

        self.act_save_log.triggered.connect(self._on_save_log)
        self.act_save_log_as.triggered.connect(self._on_save_log_as)
        self.act_open_log_file.triggered.connect(self._on_open_log_file)
        self.act_open_logs_folder.triggered.connect(self._on_open_logs_folder)

        self.logs_menu.addAction(self.act_save_log)
        self.logs_menu.addAction(self.act_save_log_as)
        self.logs_menu.addSeparator()
        self.logs_menu.addAction(self.act_open_log_file)
        self.logs_menu.addAction(self.act_open_logs_folder)

        self.view_menu = mb.addMenu("")

        self.setting_menu = mb.addMenu("")

        self.theme_menu = self.setting_menu.addMenu("")
        self._theme_group = QActionGroup(self)
        self._theme_group.setExclusive(True)
        self._rebuild_theme_menu()

        self.term_color_menu = self.setting_menu.addMenu("")
        self._rebuild_terminal_color_menu()

        self.lang_menu = self.setting_menu.addMenu("")
        self._language_group = QActionGroup(self)
        self._language_group.setExclusive(True)
        self._rebuild_language_menu()

        self.scale_menu = self.setting_menu.addMenu("")
        self._scale_group = QActionGroup(self)
        self._scale_group.setExclusive(True)
        self._rebuild_scale_menu()

        self.setting_menu.addSeparator()

        self.macro_setup_menu = self.setting_menu.addMenu("")
        self._rebuild_macro_setup_menu()

        self.macro_reset_menu = self.setting_menu.addMenu("")
        self._rebuild_macro_reset_menu()

        self.setting_menu.addSeparator()

        self.trigger_setup_menu = self.setting_menu.addMenu("")
        self._rebuild_trigger_setup_menu()

        self.trigger_reset_menu = self.setting_menu.addMenu("")
        self._rebuild_trigger_reset_menu()

        self.setting_menu.addSeparator()

        self.act_transfer_settings = QAction(self)
        self.act_transfer_settings.triggered.connect(self._on_transfer_settings)
        self.setting_menu.addAction(self.act_transfer_settings)

        self.save_format_menu = self.setting_menu.addMenu("")
        self._save_format_group = QActionGroup(self)
        self._save_format_group.setExclusive(True)
        self.act_fmt_plain = QAction(self)
        self.act_fmt_plain.setCheckable(True)
        self.act_fmt_plain.triggered.connect(
            lambda _checked=False: self._on_save_format_chosen(FORMAT_PLAIN)
        )
        self.act_fmt_rich = QAction(self)
        self.act_fmt_rich.setCheckable(True)
        self.act_fmt_rich.triggered.connect(
            lambda _checked=False: self._on_save_format_chosen(FORMAT_RICH)
        )
        self._save_format_group.addAction(self.act_fmt_plain)
        self._save_format_group.addAction(self.act_fmt_rich)
        self.save_format_menu.addAction(self.act_fmt_plain)
        self.save_format_menu.addAction(self.act_fmt_rich)

        self.help_menu = mb.addMenu("")
        self.act_info       = QAction(self)
        self.act_net_info   = QAction(self)
        self.act_about      = QAction(self)
        self.act_info.triggered.connect(self._on_info)
        self.act_net_info.triggered.connect(self._on_net_info)
        self.act_about.triggered.connect(self._on_about)
        self.help_menu.addAction(self.act_info)
        self.help_menu.addAction(self.act_net_info)
        self.help_menu.addSeparator()
        self.help_menu.addAction(self.act_about)

        self._retranslate_menu()
        self._rebuild_save_format_menu()

    def _retranslate_menu(self) -> None:
        self.logs_menu.setTitle(self.tr("&Logs"))
        self.act_save_log.setText(self.tr("Save log"))
        self.act_save_log_as.setText(self.tr("Save log as…"))
        self.act_open_log_file.setText(self.tr("Open log…"))
        self.act_open_logs_folder.setText(self.tr("Open logs folder"))

        self.view_menu.setTitle(self.tr("&View"))

        self.setting_menu.setTitle(self.tr("&Setting"))
        self.theme_menu.setTitle(self.tr("Theme"))
        self.term_color_menu.setTitle(self.tr("Terminal text color"))
        self.lang_menu.setTitle(self.tr("Language"))
        self.scale_menu.setTitle(self.tr("UI scale"))

        self.macro_setup_menu.setTitle(self.tr("Configure macros"))
        self.macro_reset_menu.setTitle(self.tr("Reset all macros"))
        self._rebuild_macro_setup_menu()
        self._rebuild_macro_reset_menu()

        self.trigger_setup_menu.setTitle(self.tr("Configure triggers"))
        self.trigger_reset_menu.setTitle(self.tr("Reset triggers"))
        self._rebuild_trigger_setup_menu()
        self._rebuild_trigger_reset_menu()

        self.act_transfer_settings.setText(self.tr("Transfer settings"))

        self.save_format_menu.setTitle(self.tr("Save format"))
        self.act_fmt_plain.setText(self.tr("Plain text (.xyrm)"))
        self.act_fmt_rich.setText(self.tr("Colored HTML (.xyrmc)"))

        self.help_menu.setTitle(self.tr("&Help"))
        self.act_info.setText(self.tr("Info"))
        self.act_net_info.setText(self.tr("Network info"))
        self.act_about.setText(self.tr("About XYrminal"))

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate_menu()
            self._retranslate_status_bar()
            self._rebuild_view_menu()
            self._rebuild_theme_menu()
            self._rebuild_terminal_color_menu()
            self._rebuild_language_menu()
            self._rebuild_scale_menu()
            self._rebuild_save_format_menu()
        super().changeEvent(event)

    def _rebuild_save_format_menu(self) -> None:
        cur = self._settings.get_str("log/format", FORMAT_PLAIN)
        self.act_fmt_plain.setChecked(cur == FORMAT_PLAIN)
        self.act_fmt_rich.setChecked(cur == FORMAT_RICH)

    def _on_save_format_chosen(self, fmt: str) -> None:
        self._settings.set_str("log/format", fmt)
        self._settings.sync()
        self._apply_log_format(fmt)
        self._rebuild_save_format_menu()

    def _apply_log_format(self, fmt: str) -> None:
        for tab in (self.com_tab, self.tcp_client_tab, self.tcp_server_tab,
                    self.udp_client_tab, self.udp_server_tab):
            try:
                tab.log_writer.set_format(fmt)
            except Exception:
                pass

    def _on_theme_changed(self, _theme_id: str) -> None:
        self._rebuild_theme_menu()

    def _on_ui_scale_changed(self, _scale: float) -> None:
        self._rebuild_scale_menu()

    def _rebuild_theme_menu(self) -> None:
        self.theme_menu.clear()
        for act in list(self._theme_group.actions()):
            self._theme_group.removeAction(act)

        cur = current_theme_choice()
        for theme_id, label in available_themes():
            act = QAction(label, self)
            act.setIcon(theme_icon(theme_id, size=14))
            act.setCheckable(True)
            act.setChecked(theme_id == cur)
            act.triggered.connect(
                lambda _checked, tid=theme_id: set_theme(tid)
            )
            self._theme_group.addAction(act)
            self.theme_menu.addAction(act)

        self.theme_menu.addSeparator()

        act_custom = QAction(self.tr("Custom…"), self)
        act_custom.setIcon(theme_icon(CUSTOM_THEME_ID, size=14))
        act_custom.setCheckable(True)
        act_custom.setChecked(cur == CUSTOM_THEME_ID)
        act_custom.triggered.connect(self._on_custom_theme_clicked)
        self.theme_menu.addAction(act_custom)

        self.theme_menu.addSeparator()

        act_random = QAction(self.tr("Random"), self)
        act_random.setIcon(theme_icon(CUSTOM_THEME_ID, size=14))
        act_random.triggered.connect(self._on_random_theme_clicked)
        self.theme_menu.addAction(act_random)

    def _on_random_theme_clicked(self) -> None:
        from core.custom_theme import randomize_custom_palette
        randomize_custom_palette()

        from core.theme import set_theme
        set_theme(CUSTOM_THEME_ID)

        self._rebuild_theme_menu()
        
    def _on_custom_theme_clicked(self) -> None:
        for a in self._theme_group.actions():
            a.setChecked(False)

        dlg = CustomThemeDialog(self)
        dlg.exec()

        self._rebuild_theme_menu()

    def _rebuild_language_menu(self) -> None:
        self.lang_menu.clear()
        cur = current_language()
        for act in list(self._language_group.actions()):
            self._language_group.removeAction(act)

        for code, label in LANGUAGES:
            act = QAction(label, self)
            act.setCheckable(True)
            act.setChecked(code == cur)
            act.triggered.connect(
                lambda _checked, c=code: apply_language(c)
            )
            self._language_group.addAction(act)
            self.lang_menu.addAction(act)

    def _rebuild_scale_menu(self) -> None:
        self.scale_menu.clear()
        for act in list(self._scale_group.actions()):
            self._scale_group.removeAction(act)

        cur = ui_scale()
        for value in ALLOWED_SCALES:
            label = f"{int(round(value * 100))}%"
            act = QAction(label, self)
            act.setCheckable(True)
            act.setChecked(abs(value - cur) < 1e-6)
            act.triggered.connect(
                lambda _checked, v=value: set_ui_scale(v)
            )
            self._scale_group.addAction(act)
            self.scale_menu.addAction(act)

    def _on_language_changed(self, code: str) -> None:
        lbl = language_label(code)
        for act in self._language_group.actions():
            act.setChecked(act.text() == lbl)

    def _rebuild_terminal_color_menu(self) -> None:
        self.term_color_menu.clear()

        mgr = TerminalColorManager.instance()

        for category_id in CATEGORY_ORDER:
            label_text = category_label(category_id)
            current_color_id = mgr.get_color_id(category_id)

            cat_menu = self.term_color_menu.addMenu(label_text)

            try:
                current_qcolor = mgr.get_qcolor(category_id)
                cat_menu.menuAction().setIcon(_qcolor_icon(current_qcolor))
            except Exception:
                pass

            for color_id in NAMED_COLOR_ORDER:
                hex_color = color_hex(color_id)
                human     = color_label(color_id)

                act = QAction(_color_icon(hex_color), human, self)
                act.setCheckable(True)

                if color_id == current_color_id:
                    act.setChecked(True)

                holder = mgr.is_color_taken(color_id)
                if holder is not None and holder != category_id:
                    act.setEnabled(False)

                act.triggered.connect(
                    lambda _checked, cid=category_id, col=color_id:
                        mgr.set_color(cid, col)
                )

                cat_menu.addAction(act)

            cat_menu.addSeparator()

            reset_act = QAction(self.tr("Reset to theme"), self)
            reset_act.setEnabled(current_color_id is not None)
            reset_act.triggered.connect(
                lambda _checked, cid=category_id: mgr.clear_color(cid)
            )
            cat_menu.addAction(reset_act)

        self.term_color_menu.addSeparator()

        reset_all = QAction(self.tr("Reset all to theme"), self)
        reset_all.triggered.connect(mgr.reset_all)
        self.term_color_menu.addAction(reset_all)

    def _rebuild_macro_setup_menu(self) -> None:
        self.macro_setup_menu.clear()
        for prefix in PREFIXES:
            label = _prefix_label_tr(self, prefix)

            act = QAction(label, self)
            act.triggered.connect(
                lambda _checked, p=prefix: self._on_configure_macros(p)
            )
            self.macro_setup_menu.addAction(act)

    def _rebuild_macro_reset_menu(self) -> None:
        self.macro_reset_menu.clear()

        for prefix in PREFIXES:
            label = _prefix_label_tr(self, prefix)

            act = QAction(label, self)
            act.triggered.connect(
                lambda _checked, p=prefix: self._on_reset_macros(p)
            )
            self.macro_reset_menu.addAction(act)

        self.macro_reset_menu.addSeparator()

        act_all = QAction(self.tr("All"), self)
        act_all.triggered.connect(
            lambda _checked=False: self._on_reset_macros("all")
        )
        self.macro_reset_menu.addAction(act_all)

    def _on_configure_macros(self, prefix: str) -> None:
        dlg = MacroEditorDialog(prefix, self)
        dlg.exec()

    def _on_reset_macros(self, prefix: str) -> None:
        if prefix == "all":
            label = self.tr("all tabs")
        else:
            label = _prefix_label_tr(self, prefix)

        reply = QMessageBox.question(
            self, "XYrminal",
            self.tr("Reset all macros for {label}?").format(label=label),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        MacroStore.instance().reset(prefix)

    def _rebuild_trigger_setup_menu(self) -> None:
        self.trigger_setup_menu.clear()
        for prefix in PREFIXES:
            label = _prefix_label_tr(self, prefix)

            act = QAction(label, self)
            act.triggered.connect(
                lambda _checked, p=prefix: self._on_configure_triggers(p)
            )
            self.trigger_setup_menu.addAction(act)

    def _rebuild_trigger_reset_menu(self) -> None:
        self.trigger_reset_menu.clear()

        for prefix in PREFIXES:
            label = _prefix_label_tr(self, prefix)

            act = QAction(label, self)
            act.triggered.connect(
                lambda _checked, p=prefix: self._on_reset_triggers(p)
            )
            self.trigger_reset_menu.addAction(act)

        self.trigger_reset_menu.addSeparator()

        act_all = QAction(self.tr("All"), self)
        act_all.triggered.connect(
            lambda _checked=False: self._on_reset_triggers("all")
        )
        self.trigger_reset_menu.addAction(act_all)

    def _on_configure_triggers(self, prefix: str) -> None:
        from ui.widgets.trigger_editor_dialog import TriggerEditorDialog
        dlg = TriggerEditorDialog(prefix, self)
        dlg.exec()

    def _on_reset_triggers(self, prefix: str) -> None:
        if prefix == "all":
            label = self.tr("all tabs")
        else:
            label = _prefix_label_tr(self, prefix)

        reply = QMessageBox.question(
            self, "XYrminal",
            self.tr("Reset triggers for {label}?").format(label=label),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        from core.trigger_store import TriggerStore
        TriggerStore.instance().reset(prefix)

    def _on_transfer_settings(self) -> None:
        TransferSettingsDialog(self).exec()
        for tab in (self.com_tab, self.tcp_client_tab,
                    self.udp_client_tab):
            try:
                tab.transmit.refresh_file_path_state()
            except Exception:
                pass

    def _current_tab(self):
        return {
            0: self.com_tab,
            1: self.tcp_client_tab,
            2: self.tcp_server_tab,
            3: self.udp_client_tab,
            4: self.udp_server_tab,
        }.get(self.tabs.currentIndex())

    def _on_tab_changed(self, _idx: int) -> None:
        self._rebuild_view_menu()
        self._refresh_counters()

    def _rebuild_view_menu(self) -> None:
        self.view_menu.clear()

        tab = self._current_tab()
        if tab is None:
            return

        try:
            groups = tab.available_groups()
        except AttributeError:
            return

        for name, label in groups.items():
            act = QAction(label, self)
            act.setCheckable(True)
            act.setChecked(tab.is_group_visible(name))
            act.toggled.connect(
                lambda checked, n=name: self._on_group_toggled(n, checked)
            )
            self.view_menu.addAction(act)

        self.view_menu.addSeparator()

        act_show_all = QAction(self.tr("Show all"), self)
        act_show_all.triggered.connect(self._on_show_all_groups)
        self.view_menu.addAction(act_show_all)

        act_hide_all = QAction(self.tr("Hide all"), self)
        act_hide_all.triggered.connect(self._on_hide_all_groups)
        self.view_menu.addAction(act_hide_all)

    def _on_group_toggled(self, name: str, visible: bool) -> None:
        tab = self._current_tab()
        if tab is not None:
            tab.set_group_visible(name, visible)

    def _on_show_all_groups(self) -> None:
        tab = self._current_tab()
        if tab is None:
            return
        try:
            groups = tab.available_groups()
        except AttributeError:
            return
        for name in groups.keys():
            tab.set_group_visible(name, True)
        self._rebuild_view_menu()

    def _on_hide_all_groups(self) -> None:
        tab = self._current_tab()
        if tab is None:
            return
        try:
            groups = tab.available_groups()
        except AttributeError:
            return
        for name in groups.keys():
            tab.set_group_visible(name, False)
        self._rebuild_view_menu()

    def _on_save_log(self) -> None:
        tab = self._current_tab()
        if tab is None:
            return
        path = tab.save_log_default()
        if path is not None:
            QMessageBox.information(
                self, "XYrminal",
                self.tr("Saved: {name}").format(name=path.name)
            )

    def _on_save_log_as(self) -> None:
        tab = self._current_tab()
        if tab is None:
            return
        tab.save_log_as_dialog(self)

    def _on_open_log_file(self) -> None:
        tab = self._current_tab()
        if tab is None:
            return

        start_dir = str(_LOGS_DIR) if _LOGS_DIR.exists() else ""

        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Open log"),
            start_dir,
            self.tr(
                "XYrminal logs (*.xyrm *.xyrmc);;"
                "Plain text (*.xyrm);;"
                "Colored HTML (*.xyrmc);;"
                "All files (*)"
            ),
        )
        if not path:
            return

        p = Path(path)
        fmt = LogWriter.detect_format(p)

        try:
            if fmt == FORMAT_RICH:
                html = LogWriter.read_html_log(p)
                if not html:
                    QMessageBox.warning(
                        self, "XYrminal",
                        self.tr("Failed to read log: {p}").format(p=str(p))
                    )
                    return
                self._show_html_log_window(p, html)
            else:
                text = LogWriter.read_plain_log(p)
                if not text:
                    QMessageBox.warning(
                        self, "XYrminal",
                        self.tr("Failed to read log: {p}").format(p=str(p))
                    )
                    return
                tab.terminal.load_plain_log(text)
                QMessageBox.information(
                    self, "XYrminal",
                    self.tr("Opened: {name}").format(name=p.name)
                )
        except Exception as exc:
            QMessageBox.warning(
                self, "XYrminal",
                self.tr("Failed to open log: {err}").format(err=exc)
            )

    def _show_html_log_window(self, path: Path, html: str) -> None:
        from ui.widgets.replay_log_dialog import ReplayLogDialog

        dlg = ReplayLogDialog(path, html, self)
        dlg.resize(1000, 720)

        geo = self._settings.get_bytes("logviewer/geometry")
        if geo:
            dlg.restoreGeometry(geo)

        dlg.finished.connect(
            lambda _res, d=dlg: self._settings.set_bytes(
                "logviewer/geometry", bytes(d.saveGeometry())
            )
        )

        dlg.setModal(False)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _on_open_logs_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(_LOGS_DIR)))

    def _on_info(self) -> None:
        InfoDialog(self).exec()

    def _on_net_info(self) -> None:
        NetworkInfoDialog(self).exec()

    def _on_about(self) -> None:
        AboutDialog(self).exec()

    def shutdown(self) -> None:
        for tab in (self.com_tab, self.tcp_client_tab, self.tcp_server_tab,
                    self.udp_client_tab, self.udp_server_tab):
            try:
                tab.shutdown()
            except Exception:
                pass
"""
Simple informational dialogs: About, Info, MacroEditor, PlotSettings,
TransferSettings, CustomTheme, NetworkInfo.

The Info dialog renders an HTML file from assets/info/info_<lang>.html.
Each language has its own HTML file; if it is missing, info_en.html is
used as a fallback.
"""

from pathlib import Path

from PyQt6.QtCore import Qt, QEvent, pyqtSignal
from PyQt6.QtGui import QPixmap, QColor
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextBrowser, QSizePolicy, QGridLayout, QLineEdit, QWidget,
    QScrollArea, QMessageBox, QSpinBox, QDoubleSpinBox,
    QFileDialog, QInputDialog, QCheckBox, QColorDialog,
)

from core.macros import MacroStore, MACRO_COUNT
from core.theme import ToggleButton

from core.settings import Settings
from core.paths import resource_root

from core.theme import COLORS
from core.i18n import current_language
from core.plot_store import PlotStore


APP_NAME    = "XYrminal"
APP_VERSION = "v0.5.30"
APP_AUTHOR  = "ExShadow"

APP_TELEGRAM = "https://t.me/oiiaiioiiia"
APP_GITHUB   = "https://github.com/ExShadowZ"
APP_EMAIL    = "ex.shadow.dev.c@gmail.com"


_ICON_PATH = Path(__file__).resolve().parent.parent / "assets" / "icon.ico"
_INFO_DIR  = resource_root() / "assets" / "info"


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setMinimumWidth(440)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(12)

        top = QHBoxLayout()
        top.setSpacing(16)

        if _ICON_PATH.exists():
            pix = QPixmap(str(_ICON_PATH))
            if not pix.isNull():
                icon_label = QLabel()
                icon_label.setPixmap(
                    pix.scaled(64, 64,
                               Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
                )
                icon_label.setFixedSize(64, 64)
                icon_label.setCursor(Qt.CursorShape.PointingHandCursor)
                icon_label.setToolTip(self.tr("Click me…"))
                icon_label.mousePressEvent = (
                    lambda _ev, dlg=self: dlg._on_icon_clicked()
                )
                top.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignTop)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)

        self.title   = QLabel(APP_NAME)
        self.title.setStyleSheet(
            f"color: {COLORS['accent']}; font-size: 18px; font-weight: 700;"
        )

        self.version = QLabel(APP_VERSION)
        self.version.setStyleSheet(f"color: {COLORS['text_dim']};")

        self.author  = QLabel()
        self.author.setStyleSheet(f"color: {COLORS['text_dim']};")

        text_col.addWidget(self.title)
        text_col.addWidget(self.version)
        text_col.addWidget(self.author)
        text_col.addStretch(1)

        top.addLayout(text_col, stretch=1)
        root.addLayout(top)

        line = QLabel()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background-color: {COLORS['border']};")
        root.addWidget(line)

        self.desc = QLabel()
        self.desc.setWordWrap(True)
        self.desc.setStyleSheet(f"color: {COLORS['text']};")
        root.addWidget(self.desc)

        self.link_telegram = self._make_link_label()
        self.link_github   = self._make_link_label()
        self.link_email    = self._make_link_label()

        links_col = QVBoxLayout()
        links_col.setSpacing(4)
        links_col.addWidget(self.link_telegram)
        links_col.addWidget(self.link_github)
        links_col.addWidget(self.link_email)
        root.addLayout(links_col)

        root.addStretch(1)

        btns = QHBoxLayout()
        btns.addStretch(1)
        self.close_btn = QPushButton()
        self.close_btn.setProperty("btnStyle", "accent")
        self.close_btn.clicked.connect(self.accept)
        btns.addWidget(self.close_btn)
        root.addLayout(btns)

        self._retranslate()

    def _make_link_label(self) -> QLabel:
        lbl = QLabel()
        lbl.setOpenExternalLinks(True)
        lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        lbl.setStyleSheet(f"color: {COLORS['text']};")
        return lbl

    @staticmethod
    def _link_html(icon: str, label: str, href: str) -> str:
        return (
            f"{icon} <a href=\"{href}\" "
            f"style=\"color:{COLORS['accent']}; text-decoration:none;\">"
            f"{label}</a>"
        )

    def _retranslate(self) -> None:
        self.setWindowTitle(self.tr("About {app}").format(app=APP_NAME))
        self.author.setText(self.tr("Author: {a}").format(a=APP_AUTHOR))
        self.desc.setText(self.tr(
            "Terminal for COM, TCP, UDP. "
            "Client & server, XMODEM/YMODEM, live plot, macros, logging."
        ))

        self.link_telegram.setText(
            self._link_html("➤", self.tr("Telegram"), APP_TELEGRAM)
        )
        self.link_github.setText(
            self._link_html("◈", self.tr("GitHub"), APP_GITHUB)
        )
        self.link_email.setText(
            self._link_html("✉", self.tr("Email"), f"mailto:{APP_EMAIL}")
        )

        self.close_btn.setText(self.tr("Close"))

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate()
        super().changeEvent(event)

    # ------------------------------------------------------------------
    # Easter egg
    # ------------------------------------------------------------------
    def _on_icon_clicked(self) -> None:
        dlg = QMessageBox(self)
        dlg.setWindowTitle(self.tr("Error"))
        dlg.setIcon(QMessageBox.Icon.Critical)
        dlg.setText(self.tr("Success!"))
        dlg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        dlg.setDefaultButton(QMessageBox.StandardButton.No)
        reply = dlg.exec()

        if reply == QMessageBox.StandardButton.Yes:
            self._egg_step(1)

    def _egg_step(self, n: int) -> None:
        if n > 5:
            return

        titles = [
            self.tr("Error"),
            self.tr("Warning"),
            self.tr("Critical"),
            self.tr("Fatal"),
            self.tr("Seriously?"),
        ]
        messages = [
            self.tr("Success!"),
            self.tr("Success!!"),
            self.tr("Success!!!"),
            self.tr("Success!!!!"),
            self.tr("Success!!!!!"),
        ]
        title = titles[(n - 1) % len(titles)]
        message = messages[(n - 1) % len(messages)]

        if n == 5:
            box = QMessageBox(self)
            box.setWindowTitle(title)
            box.setIcon(QMessageBox.Icon.Information)
            box.setText(message)
            box.setStandardButtons(QMessageBox.StandardButton.Ok)
            box.exec()
            return

        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setIcon(QMessageBox.Icon.Critical)
        box.setText(message)
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        box.setDefaultButton(QMessageBox.StandardButton.No)
        reply = box.exec()

        if reply == QMessageBox.StandardButton.Yes:
            self._egg_step(n + 1)


class InfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.resize(760, 720)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setSizePolicy(QSizePolicy.Policy.Expanding,
                                   QSizePolicy.Policy.Expanding)
        root.addWidget(self.browser, stretch=1)

        btns = QHBoxLayout()
        btns.addStretch(1)
        self.close_btn = QPushButton()
        self.close_btn.setProperty("btnStyle", "accent")
        self.close_btn.clicked.connect(self.accept)
        btns.addWidget(self.close_btn)
        root.addLayout(btns)

        self._retranslate()

    def _info_path(self, lang: str) -> Path:
        candidate = _INFO_DIR / f"info_{lang}.html"
        if candidate.exists():
            return candidate
        return _INFO_DIR / "info_en.html"

    def _load_html(self, lang: str) -> str:
        path = self._info_path(lang)
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return (
                "<html><body style='font-family:sans-serif;padding:20px;'>"
                "<h2>XYrminal</h2>"
                "<p>The info page could not be loaded.</p>"
                "<p>Expected path: <code>"
                f"{path}</code></p>"
                "</body></html>"
            )

    def _retranslate(self) -> None:
        self.setWindowTitle(self.tr("{app} — Info").format(app=APP_NAME))

        lang = current_language()
        html = self._load_html(lang)
        self.browser.setHtml(html)

        self.close_btn.setText(self.tr("Close"))

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate()
        super().changeEvent(event)


class MacroEditorDialog(QDialog):
    def __init__(self, prefix: str, parent=None):
        super().__init__(parent)
        self._prefix = prefix
        self.setModal(True)
        self.setMinimumWidth(760)

        self._edits:      list[QLineEdit]    = []
        self._hex_btns:   list[ToggleButton] = []
        self._cr_btns:    list[ToggleButton] = []
        self._crlf_btns:  list[ToggleButton] = []
        self._script_flags: list[bool] = [False] * MACRO_COUNT

        self._build()
        self._retranslate()
        self._load_from_store()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 12)
        root.setSpacing(10)

        self.lbl_header = QLabel()
        self.lbl_header.setStyleSheet("font-weight: 700;")
        root.addWidget(self.lbl_header)

        top = QHBoxLayout()
        top.setSpacing(8)

        self.btn_add_scenario = QPushButton()
        self.btn_add_scenario.setProperty("btnStyle", "accent")
        self.btn_add_scenario.clicked.connect(self._on_add_scenario)

        self.btn_clear_scenario = QPushButton()
        self.btn_clear_scenario.clicked.connect(self._on_clear_scenario)

        top.addWidget(self.btn_add_scenario)
        top.addWidget(self.btn_clear_scenario)
        top.addStretch(1)
        root.addLayout(top)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        for i in range(MACRO_COUNT):
            lbl = QLabel(f"M{i + 1}")
            lbl.setMinimumWidth(28)

            edit = QLineEdit()
            edit.setPlaceholderText(self.tr("Empty — button disabled"))
            edit.setMinimumWidth(320)

            cr_btn = ToggleButton("", on=False)
            cr_btn.setMinimumWidth(52)

            crlf_btn = ToggleButton("", on=False)
            crlf_btn.setMinimumWidth(90)

            hex_btn = ToggleButton("", on=False)
            hex_btn.setMinimumWidth(52)

            grid.addWidget(lbl,       i, 0)
            grid.addWidget(edit,      i, 1)
            grid.addWidget(cr_btn,    i, 2)
            grid.addWidget(crlf_btn,  i, 3)
            grid.addWidget(hex_btn,   i, 4)

            self._edits.append(edit)
            self._cr_btns.append(cr_btn)
            self._crlf_btns.append(crlf_btn)
            self._hex_btns.append(hex_btn)

        grid.setColumnStretch(1, 1)
        root.addLayout(grid)

        root.addStretch(1)

        btns = QHBoxLayout()
        btns.addStretch(1)

        self.cancel_btn = QPushButton()
        self.cancel_btn.clicked.connect(self.reject)

        self.ok_btn = QPushButton()
        self.ok_btn.setProperty("btnStyle", "accent")
        self.ok_btn.clicked.connect(self._on_ok)

        btns.addWidget(self.cancel_btn)
        btns.addWidget(self.ok_btn)
        root.addLayout(btns)

    def _retranslate(self) -> None:
        from core.macros import prefix_label

        label = prefix_label(self._prefix)
        if label == "TCP Client":
            label = self.tr("TCP Client")
        elif label == "TCP Server":
            label = self.tr("TCP Server")
        elif label == "UDP Client":
            label = self.tr("UDP Client")
        elif label == "UDP Server":
            label = self.tr("UDP Server")

        self.setWindowTitle(self.tr("Macros — {p}").format(p=label))
        self.lbl_header.setText(
            self.tr("Configure macros for the {p} tab").format(p=label)
        )
        self.btn_add_scenario.setText(self.tr("Add scenario…"))
        self.btn_clear_scenario.setText(self.tr("Clear scenario"))
        for b in self._cr_btns:
            b.setText(self.tr("+CR"))
        for b in self._crlf_btns:
            b.setText(self.tr("CR=CR+LF"))
        for b in self._hex_btns:
            b.setText(self.tr("HEX"))
        self.cancel_btn.setText(self.tr("Cancel"))
        self.ok_btn.setText(self.tr("OK"))

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate()
        super().changeEvent(event)

    def _load_from_store(self) -> None:
        store = MacroStore.instance()
        for i in range(MACRO_COUNT):
            text, is_hex, add_cr, crlf = store.get(self._prefix, i)
            is_script  = store.is_script(self._prefix, i)
            script_path = store.scenario_path(self._prefix, i)

            if is_script and script_path:
                self._edits[i].setText(script_path)
                self._script_flags[i] = True
            else:
                self._edits[i].setText(text)
                self._script_flags[i] = False

            self._hex_btns[i].setChecked(is_hex)
            self._cr_btns[i].setChecked(add_cr)
            self._crlf_btns[i].setChecked(crlf)

            self._apply_slot_state(i)

    def _apply_slot_state(self, i: int) -> None:
        is_script = self._script_flags[i]
        self._hex_btns[i].setEnabled(not is_script)
        self._cr_btns[i].setEnabled(not is_script)
        self._crlf_btns[i].setEnabled(not is_script)
        self._edits[i].setReadOnly(is_script)

    def _on_add_scenario(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Select scenario file"),
            "",
            self.tr("XYrminal scenarios (*.xyscen);;All files (*)"),
        )
        if not path:
            return

        slot, ok = QInputDialog.getInt(
            self,
            self.tr("Select slot"),
            self.tr("Which macro slot (1…10) should run this scenario?"),
            1, 1, MACRO_COUNT, 1,
        )
        if not ok:
            return

        idx = slot - 1
        self._edits[idx].setText(path)
        self._script_flags[idx] = True
        self._apply_slot_state(idx)

    def _on_clear_scenario(self) -> None:
        slot, ok = QInputDialog.getInt(
            self,
            self.tr("Clear scenario"),
            self.tr("Which macro slot (1…10) should be cleared?"),
            1, 1, MACRO_COUNT, 1,
        )
        if not ok:
            return

        idx = slot - 1
        self._edits[idx].clear()
        self._script_flags[idx] = False
        self._apply_slot_state(idx)

    def _on_ok(self) -> None:
        store = MacroStore.instance()
        for i in range(MACRO_COUNT):
            if self._script_flags[i]:
                path = self._edits[i].text().strip()
                store.set(
                    self._prefix, i,
                    text="",
                    is_hex=False,
                    add_cr=False, crlf=False,
                    is_script=True, script_path=path,
                )
            else:
                store.set(
                    self._prefix, i,
                    text=self._edits[i].text(),
                    is_hex=self._hex_btns[i].isChecked(),
                    add_cr=self._cr_btns[i].isChecked(),
                    crlf=self._crlf_btns[i].isChecked(),
                    is_script=False, script_path="",
                )
        self.accept()


class _PlotRow:
    def __init__(self, dialog: "PlotSettingsDialog",
                 name: str = "", marker: str = ""):
        self.widget = QWidget()
        self.widget.setSizePolicy(QSizePolicy.Policy.Expanding,
                                  QSizePolicy.Policy.Fixed)

        row = QHBoxLayout(self.widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText(dialog.tr("Variable name"))
        row.addWidget(self.name_edit, stretch=2)

        self.marker_edit = QLineEdit(marker)
        self.marker_edit.setPlaceholderText(dialog.tr("Parse marker (optional)"))
        row.addWidget(self.marker_edit, stretch=3)

        self.del_btn = QPushButton("✕")
        self.del_btn.setFixedWidth(28)
        self.del_btn.setProperty("btnStyle", "danger")
        self.del_btn.clicked.connect(lambda: dialog.remove_row(self))
        row.addWidget(self.del_btn)

    def values(self) -> tuple[str, str]:
        return self.name_edit.text().strip(), self.marker_edit.text().strip()

    def retranslate(self, dialog: "PlotSettingsDialog") -> None:
        self.name_edit.setPlaceholderText(dialog.tr("Variable name"))
        self.marker_edit.setPlaceholderText(dialog.tr("Parse marker (optional)"))


class PlotSettingsDialog(QDialog):
    layout_requested = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(False)
        self.setMinimumWidth(620)

        self._rows: list[_PlotRow] = []
        self._store = PlotStore.instance()
        self._store.state_changed.connect(self._refresh_buttons)

        self._settings = Settings()

        self._plot_widget = None

        self._build()
        self._retranslate()

        if not self._rows:
            self.add_row()

        self._refresh_buttons()

    def attach_plot_widget(self, w) -> None:
        self._plot_widget = w
        self._load_view_state()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 12)
        root.setSpacing(10)

        self.lbl_hint = QLabel()
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setProperty("role", "dim")
        root.addWidget(self.lbl_hint)

        self.rows_host = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_host)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(6)
        self.rows_layout.addStretch(1)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.rows_host)
        self.scroll.setMinimumHeight(180)
        root.addWidget(self.scroll, stretch=1)

        view_row = QHBoxLayout()
        view_row.setSpacing(8)

        self.add_btn = QPushButton("+")
        self.add_btn.clicked.connect(lambda _checked=False: self.add_row())
        view_row.addWidget(self.add_btn)

        view_row.addStretch(1)

        self.tmode_btn = ToggleButton("", on=False)
        self.tmode_btn.toggled_state.connect(self._on_tmode_toggled)
        view_row.addWidget(self.tmode_btn)

        self.view_spin = QSpinBox()
        self.view_spin.setRange(5, 1000)
        self.view_spin.setValue(20)
        self.view_spin.setSingleStep(5)
        self.view_spin.valueChanged.connect(self._on_view_points_changed)

        self.view_dspin = QDoubleSpinBox()
        self.view_dspin.setRange(0.5, 600.0)
        self.view_dspin.setDecimals(1)
        self.view_dspin.setValue(10.0)
        self.view_dspin.setSingleStep(1.0)
        self.view_dspin.setSuffix(" s")
        self.view_dspin.valueChanged.connect(self._on_view_seconds_changed)

        view_row.addWidget(self.view_spin)
        view_row.addWidget(self.view_dspin)

        root.addLayout(view_row)

        ctrl = QHBoxLayout()
        ctrl.setSpacing(8)

        self.start_btn = QPushButton()
        self.start_btn.setProperty("btnStyle", "ok")
        self.start_btn.clicked.connect(self._on_start)

        self.pause_btn = QPushButton()
        self.pause_btn.setProperty("btnStyle", "accent")
        self.pause_btn.clicked.connect(self._on_pause)

        self.stop_btn = QPushButton()
        self.stop_btn.setProperty("btnStyle", "danger")
        self.stop_btn.clicked.connect(self._on_stop)

        self.export_btn = QPushButton()
        self.export_btn.clicked.connect(self._on_export_csv)

        ctrl.addWidget(self.start_btn)
        ctrl.addWidget(self.pause_btn)
        ctrl.addWidget(self.stop_btn)
        ctrl.addStretch(1)
        ctrl.addWidget(self.export_btn)

        self.close_btn = QPushButton()
        self.close_btn.clicked.connect(self.close)
        ctrl.addWidget(self.close_btn)

        root.addLayout(ctrl)

        self.view_spin.setVisible(True)
        self.view_dspin.setVisible(False)

    def _retranslate(self) -> None:
        self.setWindowTitle(self.tr("Plot settings"))
        self.lbl_hint.setText(self.tr(
            "One row per variable. Name is required; marker is optional "
            "(empty marker = take the first number in the incoming chunk). "
            "While paused you can edit rows; changes take effect on the "
            "next Start."
        ))
        self.add_btn.setText(self.tr("+ Add"))
        self.tmode_btn.setText(self.tr("T-Mode"))
        self.export_btn.setText(self.tr("Export CSV"))
        self.close_btn.setText(self.tr("Close"))
        self._refresh_buttons()

        for row in self._rows:
            row.retranslate(self)

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate()
        super().changeEvent(event)

    def _load_view_state(self) -> None:
        s = self._settings
        pts = s.get_int("plot/view_points", 20)
        sec = s.get_float("plot/view_seconds", 10.0)
        tmode = s.get_bool("plot/time_mode", False)

        self.view_spin.blockSignals(True)
        self.view_dspin.blockSignals(True)
        self.tmode_btn.blockSignals(True)

        self.view_spin.setValue(pts)
        self.view_dspin.setValue(sec)
        self.tmode_btn.setChecked(tmode)

        self.view_spin.blockSignals(False)
        self.view_dspin.blockSignals(False)
        self.tmode_btn.blockSignals(False)

        self._apply_view_visibility()
        self._push_view_to_plot()

    def _apply_view_visibility(self) -> None:
        if self.tmode_btn.isChecked():
            self.view_spin.setVisible(False)
            self.view_dspin.setVisible(True)
        else:
            self.view_spin.setVisible(True)
            self.view_dspin.setVisible(False)

    def _push_view_to_plot(self) -> None:
        if self._plot_widget is None:
            return
        self._plot_widget.set_view_points(self.view_spin.value())
        self._plot_widget.set_view_seconds(self.view_dspin.value())
        self._plot_widget.set_time_mode(self.tmode_btn.isChecked())

    def _on_tmode_toggled(self, on: bool) -> None:
        self._settings.set_bool("plot/time_mode", on)
        self._apply_view_visibility()
        if self._plot_widget is not None:
            self._plot_widget.set_time_mode(on)

    def _on_view_points_changed(self, value: int) -> None:
        self._settings.set_int("plot/view_points", value)
        if self._plot_widget is not None:
            self._plot_widget.set_view_points(value)

    def _on_view_seconds_changed(self, value: float) -> None:
        self._settings.set_float("plot/view_seconds", value)
        if self._plot_widget is not None:
            self._plot_widget.set_view_seconds(value)

    def add_row(self, name: str = "", marker: str = "") -> None:
        row = _PlotRow(self, name, marker)
        self._rows.append(row)
        self.rows_layout.insertWidget(self.rows_layout.count() - 1, row.widget)

    def remove_row(self, row: "_PlotRow") -> None:
        if row not in self._rows:
            return
        self._rows.remove(row)
        row.widget.setParent(None)
        row.widget.deleteLater()

    def _collect_channels(self) -> list[tuple[str, str]]:
        result = []
        for row in self._rows:
            name, marker = row.values()
            if name:
                result.append((name, marker))
        return result

    def _refresh_buttons(self) -> None:
        running = self._store.is_active()
        paused  = self._store.is_paused()

        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self.pause_btn.setEnabled(running)

        has_data = self._store.has_data()
        self.export_btn.setEnabled(has_data)

        self.start_btn.setText(self.tr("Plot: Start"))
        self.stop_btn.setText(self.tr("Plot: Stop"))

        if not running:
            self.pause_btn.setText(self.tr("Plot: Pause"))
        elif paused:
            self.pause_btn.setText(self.tr("Plot: Resume"))
        else:
            self.pause_btn.setText(self.tr("Plot: Pause"))

    def _on_start(self) -> None:
        channels = self._collect_channels()
        if not channels:
            QMessageBox.warning(
                self, "XYrminal",
                self.tr("Add at least one channel (name required).")
            )
            return
        self._store.start(channels)
        self.layout_requested.emit(True)

    def _on_pause(self) -> None:
        self._store.toggle_pause()

    def _on_stop(self) -> None:
        self._store.stop()
        self.layout_requested.emit(False)

    def _on_export_csv(self) -> None:
        if not self._store.has_data():
            QMessageBox.information(
                self, "XYrminal",
                self.tr("No data to export.")
            )
            return

        from datetime import datetime
        default_name = datetime.now().strftime("plot_%Y-%m-%d_%H-%M-%S.csv")

        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Export plot data"),
            default_name,
            self.tr("CSV files (*.csv);;All files (*)"),
        )
        if not path:
            return

        try:
            saved = self._store.export_csv(path)
        except Exception as exc:
            QMessageBox.warning(
                self, "XYrminal",
                self.tr("Export failed: {err}").format(err=exc),
            )
            return

        QMessageBox.information(
            self, "XYrminal",
            self.tr("Exported: {name}").format(name=saved.name),
        )

    def closeEvent(self, event) -> None:
        super().closeEvent(event)


class TransferSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setMinimumWidth(420)

        from core.settings import Settings
        self._settings = Settings()

        self._build()
        self._retranslate()
        self._load()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 12)
        root.setSpacing(10)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        self.lbl_chunk = QLabel()
        self.lbl_delay = QLabel()
        self.lbl_maxsz = QLabel()

        self.chunk_spin = QSpinBox()
        self.chunk_spin.setRange(32, 65536)
        self.chunk_spin.setSingleStep(32)
        self.chunk_spin.setValue(256)

        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 5000)
        self.delay_spin.setSingleStep(1)
        self.delay_spin.setValue(10)

        self.maxsz_spin = QSpinBox()
        self.maxsz_spin.setRange(1, 65536)
        self.maxsz_spin.setValue(512)

        grid.addWidget(self.lbl_chunk, 0, 0)
        grid.addWidget(self.chunk_spin, 0, 1)
        grid.addWidget(self.lbl_delay, 1, 0)
        grid.addWidget(self.delay_spin, 1, 1)
        grid.addWidget(self.lbl_maxsz, 2, 0)
        grid.addWidget(self.maxsz_spin, 2, 1)
        grid.setColumnStretch(1, 1)

        root.addLayout(grid)

        self.keep_path_chk = QCheckBox()
        self.keep_path_chk.setChecked(False)
        root.addWidget(self.keep_path_chk)

        root.addStretch(1)

        btns = QHBoxLayout()
        btns.addStretch(1)

        self.cancel_btn = QPushButton()
        self.cancel_btn.clicked.connect(self.reject)

        self.ok_btn = QPushButton()
        self.ok_btn.setProperty("btnStyle", "accent")
        self.ok_btn.clicked.connect(self._on_ok)

        btns.addWidget(self.cancel_btn)
        btns.addWidget(self.ok_btn)
        root.addLayout(btns)

    def _retranslate(self) -> None:
        self.setWindowTitle(self.tr("Transfer settings"))
        self.lbl_chunk.setText(self.tr("Chunk size (bytes, raw only):"))
        self.lbl_delay.setText(self.tr("Chunk delay (ms, raw only):"))
        self.lbl_maxsz.setText(self.tr("Max file size (MB):"))
        self.keep_path_chk.setText(
            self.tr("Remember last sent file path")
        )
        self.cancel_btn.setText(self.tr("Cancel"))
        self.ok_btn.setText(self.tr("OK"))

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate()
        super().changeEvent(event)

    def _load(self) -> None:
        s = self._settings
        self.chunk_spin.setValue(s.get_int("transfer/chunk_size", 256))
        self.delay_spin.setValue(s.get_int("transfer/chunk_delay_ms", 10))
        self.maxsz_spin.setValue(s.get_int("transfer/max_size_mb", 512))
        self.keep_path_chk.setChecked(
            s.get_bool("transfer/keep_last_path", False)
        )

    def _on_ok(self) -> None:
        s = self._settings
        s.set_int("transfer/chunk_size", self.chunk_spin.value())
        s.set_int("transfer/chunk_delay_ms", self.delay_spin.value())
        s.set_int("transfer/max_size_mb", self.maxsz_spin.value())
        s.set_bool("transfer/keep_last_path", self.keep_path_chk.isChecked())
        s.sync()
        self.accept()


class _ThemeSwatch(QPushButton):
    color_changed = pyqtSignal(str)

    def __init__(self, color: str, parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedSize(80, 24)
        self._refresh()
        self.clicked.connect(self._on_click)

    def color(self) -> str:
        return self._color

    def set_color(self, color: str) -> None:
        self._color = color
        self._refresh()

    def _refresh(self) -> None:
        self.setStyleSheet(
            f"QPushButton {{ background-color: {self._color};"
            f"             border: 1px solid #888; border-radius: 3px;"
            f"             color: #fff; font-weight: 600; }}"
        )
        self.setText(self._color.upper())

    def _on_click(self) -> None:
        c = QColorDialog.getColor(QColor(self._color), self, "")
        if c.isValid():
            self._color = c.name()
            self._refresh()
            self.color_changed.emit(self._color)


class CustomThemeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setMinimumWidth(520)

        from core.custom_theme import (
            load_custom_palette, default_custom_palette,
            save_custom_palette, reset_custom_palette,
            random_palette,
        )
        self._load_palette = load_custom_palette
        self._default_palette = default_custom_palette
        self._save_palette = save_custom_palette
        self._reset_palette = reset_custom_palette
        self._random_palette = random_palette

        existing = self._load_palette()
        self._colors = dict(existing if existing else self._default_palette())

        self._swatches: dict[str, _ThemeSwatch] = {}

        self._build()
        self._retranslate()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 12)
        root.setSpacing(10)

        self.lbl_hint = QLabel()
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setProperty("role", "dim")
        root.addWidget(self.lbl_hint)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        keys = [
            "bg_root", "bg_panel", "bg_input",
            "bg_button", "bg_button_hover",
            "accent", "accent_dim", "accent_text",
            "text", "text_dim", "text_muted",
            "border", "border_focus",
            "ok", "ok_hover", "danger", "danger_hover", "warn",
            "tx_prefix", "tx_text",
        ]

        for i, key in enumerate(keys):
            lbl = QLabel(key)
            lbl.setMinimumWidth(140)

            swatch = _ThemeSwatch(self._colors.get(key, "#888888"))
            swatch.color_changed.connect(
                lambda new_color, k=key: self._on_color_changed(k, new_color)
            )
            self._swatches[key] = swatch

            row = i // 2
            col = (i % 2) * 2
            grid.addWidget(lbl,    row, col)
            grid.addWidget(swatch, row, col + 1)

        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        scroll_host = QWidget()
        scroll_host.setLayout(grid)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(scroll_host)
        self.scroll.setMinimumHeight(320)
        root.addWidget(self.scroll, stretch=1)

        btns = QHBoxLayout()
        btns.setSpacing(8)

        self.random_btn = QPushButton()
        self.random_btn.setProperty("btnStyle", "ok")
        self.random_btn.clicked.connect(self._on_random)

        self.reset_btn = QPushButton()
        self.reset_btn.setProperty("btnStyle", "danger")
        self.reset_btn.clicked.connect(self._on_reset)

        btns.addWidget(self.random_btn)
        btns.addWidget(self.reset_btn)
        btns.addStretch(1)

        self.cancel_btn = QPushButton()
        self.cancel_btn.clicked.connect(self.reject)

        self.ok_btn = QPushButton()
        self.ok_btn.setProperty("btnStyle", "accent")
        self.ok_btn.clicked.connect(self._on_ok)

        btns.addWidget(self.cancel_btn)
        btns.addWidget(self.ok_btn)
        root.addLayout(btns)

    def _retranslate(self) -> None:
        self.setWindowTitle(self.tr("Custom theme"))
        self.lbl_hint.setText(self.tr(
            "Pick any color for each part of the interface. "
            "Saving switches to the custom theme immediately."
        ))
        self.random_btn.setText(self.tr("Random"))
        self.reset_btn.setText(self.tr("Reset to defaults"))
        self.cancel_btn.setText(self.tr("Cancel"))
        self.ok_btn.setText(self.tr("Apply"))

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate()
        super().changeEvent(event)

    def _on_color_changed(self, key: str, color: str) -> None:
        self._colors[key] = color

    def _on_random(self) -> None:
        p = self._random_palette()
        self._colors = dict(p)
        for key, swatch in self._swatches.items():
            swatch.set_color(p.get(key, "#888888"))

    def _on_reset(self) -> None:
        self._reset_palette()
        defaults = self._default_palette()
        self._colors = dict(defaults)
        for key, swatch in self._swatches.items():
            swatch.set_color(defaults.get(key, "#888888"))

    def _on_ok(self) -> None:
        self._save_palette(self._colors)

        from core.theme import set_theme
        from core.custom_theme import CUSTOM_THEME_ID
        set_theme(CUSTOM_THEME_ID)

        self.accept()


class NetworkInfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.resize(640, 560)

        from core.net.netinfo import NetInfo

        self._info = NetInfo()
        self._info.refresh()

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 12)
        root.setSpacing(10)

        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(False)
        self.browser.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        root.addWidget(self.browser, stretch=1)

        btns = QHBoxLayout()
        btns.addStretch(1)

        self.refresh_btn = QPushButton()
        self.refresh_btn.clicked.connect(self._on_refresh)

        self.copy_btn = QPushButton()
        self.copy_btn.clicked.connect(self._on_copy)

        self.close_btn = QPushButton()
        self.close_btn.setProperty("btnStyle", "accent")
        self.close_btn.clicked.connect(self.accept)

        btns.addWidget(self.refresh_btn)
        btns.addWidget(self.copy_btn)
        btns.addWidget(self.close_btn)
        root.addLayout(btns)

        self._retranslate()

    def _retranslate(self) -> None:
        self.setWindowTitle(self.tr("Network info"))
        self.refresh_btn.setText(self.tr("Refresh"))
        self.copy_btn.setText(self.tr("Copy"))
        self.close_btn.setText(self.tr("Close"))
        self._render()

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate()
        super().changeEvent(event)

    def _on_refresh(self) -> None:
        self._info.refresh()
        self._render()

    def _on_copy(self) -> None:
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.browser.toPlainText())

    def _render(self) -> None:
        tr = self.tr
        info = self._info

        html: list[str] = []
        html.append("<style>"
                    "body { font-family: 'Consolas', monospace; font-size: 12px; }"
                    "h2 { margin: 4px 0 8px 0; }"
                    "h3 { margin: 12px 0 6px 0; }"
                    "table { border-collapse: collapse; margin-bottom: 10px; }"
                    "td { padding: 2px 10px 2px 0; vertical-align: top; }"
                    "td.k { color: #9a93b5; }"
                    ".iface { border: 1px solid #3a3454; border-radius: 6px; "
                    "         padding: 8px 12px; margin-bottom: 10px; }"
                    ".iface-title { font-weight: 700; }"
                    "</style>")

        html.append(f"<h2>{tr('Network info')}</h2>")

        hostname = info.hostname()
        fqdn = info.fqdn()
        dns = info.dns_servers()

        html.append("<table>")
        html.append(f"<tr><td class='k'>{tr('Hostname:')}</td>"
                    f"<td>{_esc(hostname)}</td></tr>")
        if fqdn and fqdn != hostname:
            html.append(f"<tr><td class='k'>{tr('FQDN:')}</td>"
                        f"<td>{_esc(fqdn)}</td></tr>")
        html.append(f"<tr><td class='k'>{tr('Primary IP:')}</td>"
                    f"<td>{_esc(info.ip or '—')}</td></tr>")
        html.append(f"<tr><td class='k'>{tr('Subnet mask:')}</td>"
                    f"<td>{_esc(info.mask or '—')}</td></tr>")
        html.append(f"<tr><td class='k'>{tr('Default gateway:')}</td>"
                    f"<td>{_esc(info.gw or '—')}</td></tr>")
        if dns:
            html.append(f"<tr><td class='k'>{tr('DNS servers:')}</td>"
                        f"<td>{_esc(', '.join(dns))}</td></tr>")
        html.append("</table>")

        ifaces = info.interfaces
        html.append(f"<h3>{tr('Interfaces')} ({len(ifaces)})</h3>")

        if not ifaces:
            html.append(f"<p><i>{tr('No interfaces found.')}</i></p>")
        else:
            for iface in ifaces:
                name = iface.get("name", "?")
                typ = iface.get("type", "Other")
                ip = iface.get("ip", "")
                mask = iface.get("mask", "")
                gw = iface.get("gw", "")
                mac = iface.get("mac", "")
                desc = iface.get("description", "")

                html.append("<div class='iface'>")
                html.append(
                    f"<div class='iface-title'>{_esc(name)} "
                    f"<span style='color:#9a93b5;font-weight:400;'>[{_esc(typ)}]</span></div>"
                )
                html.append("<table>")
                if desc:
                    html.append(f"<tr><td class='k'>{tr('Description:')}</td>"
                                f"<td>{_esc(desc)}</td></tr>")
                if ip:
                    html.append(f"<tr><td class='k'>{tr('IP:')}</td>"
                                f"<td>{_esc(ip)}</td></tr>")
                if mask:
                    html.append(f"<tr><td class='k'>{tr('MASK:')}</td>"
                                f"<td>{_esc(mask)}</td></tr>")
                if gw:
                    html.append(f"<tr><td class='k'>{tr('GW:')}</td>"
                                f"<td>{_esc(gw)}</td></tr>")
                if mac:
                    html.append(f"<tr><td class='k'>{tr('MAC:')}</td>"
                                f"<td>{_esc(mac)}</td></tr>")
                html.append("</table>")
                html.append("</div>")

        self.browser.setHtml("".join(html))


def _esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
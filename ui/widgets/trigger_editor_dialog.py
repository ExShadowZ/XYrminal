"""
Modal editor for text triggers of a given prefix.

Layout:
    [text]  [fg color swatch] [bg color swatch]  [x]
    [text]  [fg]               [bg]               [x]
    ...
    [+ Add]
    [OK] [Cancel]

Color swatches open QColorDialog. Default colors:
    fg = #000000 (black)
    bg = #e74c3c (red)
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QScrollArea, QWidget, QColorDialog,
)

from core.trigger_store import (
    TriggerStore, Trigger, MAX_TRIGGERS, DEFAULT_FG, DEFAULT_BG,
)


class _ColorSwatch(QPushButton):
    """Small square button showing a color; opens QColorDialog on click."""

    def __init__(self, color: str, parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedSize(36, 24)
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
            f"             border: 1px solid #888; border-radius: 3px; }}"
        )
        self.setText("")

    def _on_click(self) -> None:
        c = QColorDialog.getColor(QColor(self._color), self, "")
        if c.isValid():
            self._color = c.name()
            self._refresh()


class _TriggerRow:
    """One editing row."""

    def __init__(self, dialog: "TriggerEditorDialog",
                 text: str = "", fg: str = DEFAULT_FG, bg: str = DEFAULT_BG):
        self.widget = QWidget()
        row = QHBoxLayout(self.widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self.edit = QLineEdit(text)
        self.edit.setPlaceholderText(dialog.tr("Text to match (case-insensitive)"))
        row.addWidget(self.edit, stretch=1)

        self.fg_btn = _ColorSwatch(fg)
        self.fg_btn.setToolTip(dialog.tr("Text color"))
        row.addWidget(self.fg_btn)

        self.bg_btn = _ColorSwatch(bg)
        self.bg_btn.setToolTip(dialog.tr("Background color"))
        row.addWidget(self.bg_btn)

        self.del_btn = QPushButton("✕")
        self.del_btn.setFixedWidth(28)
        self.del_btn.setProperty("btnStyle", "danger")
        self.del_btn.clicked.connect(lambda: dialog.remove_row(self))
        row.addWidget(self.del_btn)

    def to_trigger(self) -> Trigger:
        return Trigger(
            text=self.edit.text().strip(),
            fg=self.fg_btn.color(),
            bg=self.bg_btn.color(),
        )

    def retranslate(self, dialog: "TriggerEditorDialog") -> None:
        self.edit.setPlaceholderText(dialog.tr("Text to match (case-insensitive)"))
        self.fg_btn.setToolTip(dialog.tr("Text color"))
        self.bg_btn.setToolTip(dialog.tr("Background color"))


class TriggerEditorDialog(QDialog):
    def __init__(self, prefix: str, parent=None):
        super().__init__(parent)
        self._prefix = prefix
        self.setModal(True)
        self.setMinimumWidth(620)

        self._rows: list[_TriggerRow] = []

        self._build()
        self._retranslate()
        self._load()

    # -- construction ------------------------------------------------------
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
        self.rows_layout.setSpacing(4)
        self.rows_layout.addStretch(1)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.rows_host)
        self.scroll.setMinimumHeight(220)
        root.addWidget(self.scroll, stretch=1)

        self.add_btn = QPushButton("+")
        self.add_btn.clicked.connect(lambda _checked=False: self.add_row())
        add_row = QHBoxLayout()
        add_row.addWidget(self.add_btn)
        add_row.addStretch(1)
        root.addLayout(add_row)

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

        self.setWindowTitle(self.tr("Triggers — {p}").format(p=label))
        self.lbl_hint.setText(self.tr(
            "Each row highlights one substring in the terminal (case-insensitive). "
            "If two triggers overlap, the upper one wins. "
            "Up to {n} triggers per tab.").format(n=MAX_TRIGGERS))
        self.add_btn.setText(self.tr("+ Add"))
        self.cancel_btn.setText(self.tr("Cancel"))
        self.ok_btn.setText(self.tr("OK"))
        for r in self._rows:
            r.retranslate(self)

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate()
        super().changeEvent(event)

    # -- rows --------------------------------------------------------------
    def add_row(self, text: str = "", fg: str = DEFAULT_FG, bg: str = DEFAULT_BG) -> None:
        if len(self._rows) >= MAX_TRIGGERS:
            return
        row = _TriggerRow(self, text, fg, bg)
        self._rows.append(row)
        self.rows_layout.insertWidget(self.rows_layout.count() - 1, row.widget)

    def remove_row(self, row: "_TriggerRow") -> None:
        if row not in self._rows:
            return
        self._rows.remove(row)
        row.widget.setParent(None)
        row.widget.deleteLater()

    # -- data --------------------------------------------------------------
    def _load(self) -> None:
        store = TriggerStore.instance()
        for t in store.all(self._prefix):
            self.add_row(t.text, t.fg, t.bg)
        if not self._rows:
            self.add_row()

    def _on_ok(self) -> None:
        store = TriggerStore.instance()
        triggers: list[Trigger] = []
        for row in self._rows:
            t = row.to_trigger()
            if t.is_valid():
                triggers.append(t)
        store.set_all(self._prefix, triggers)
        self.accept()
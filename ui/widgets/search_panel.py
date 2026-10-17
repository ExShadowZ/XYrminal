"""
Floating search panel for the terminal.

Lives as a child widget of TerminalView and is positioned in the top-right
corner. Shown on Ctrl+F or via the context menu, hidden on Esc / close.

Emits:
    search_changed(text)   — user typed something (live search)
    next_requested()
    prev_requested()
    close_requested()

Displays a match counter in the form "N / M" (current / total).
"""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal, Qt, QEvent
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QLabel,
)


class SearchPanel(QWidget):
    search_changed   = pyqtSignal(str)
    next_requested   = pyqtSignal()
    prev_requested   = pyqtSignal()
    close_requested  = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SearchPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        row = QHBoxLayout(self)
        row.setContentsMargins(6, 4, 6, 4)
        row.setSpacing(6)

        self.input = QLineEdit()
        self.input.setMinimumWidth(180)
        self.input.setPlaceholderText(self.tr("Search…"))
        self.input.textChanged.connect(self.search_changed.emit)
        self.input.installEventFilter(self)
        row.addWidget(self.input)

        self.counter = QLabel("0 / 0")
        self.counter.setProperty("role", "info")
        self.counter.setMinimumWidth(70)
        self.counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(self.counter)

        self.prev_btn = QPushButton("◀")
        self.prev_btn.setFixedWidth(28)
        self.prev_btn.clicked.connect(self.prev_requested.emit)
        row.addWidget(self.prev_btn)

        self.next_btn = QPushButton("▶")
        self.next_btn.setFixedWidth(28)
        self.next_btn.clicked.connect(self.next_requested.emit)
        row.addWidget(self.next_btn)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedWidth(28)
        self.close_btn.clicked.connect(self.close_requested.emit)
        row.addWidget(self.close_btn)

    # -- keyboard ----------------------------------------------------------
    def eventFilter(self, obj, event) -> bool:
        if obj is self.input and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            mods = event.modifiers()

            if key == Qt.Key.Key_Escape:
                self.close_requested.emit()
                return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if mods & Qt.KeyboardModifier.ShiftModifier:
                    self.prev_requested.emit()
                else:
                    self.next_requested.emit()
                return True
            if key == Qt.Key.Key_F3:
                if mods & Qt.KeyboardModifier.ShiftModifier:
                    self.prev_requested.emit()
                else:
                    self.next_requested.emit()
                return True
        return super().eventFilter(obj, event)

    # -- public API --------------------------------------------------------
    def set_counter(self, current: int, total: int) -> None:
        self.counter.setText(f"{current} / {total}")

    def text(self) -> str:
        return self.input.text()

    def set_text(self, text: str) -> None:
        self.input.setText(text)

    def focus_input(self) -> None:
        self.input.setFocus()
        self.input.selectAll()

    def retranslate(self) -> None:
        self.input.setPlaceholderText(self.tr("Search…"))

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate()
        super().changeEvent(event)
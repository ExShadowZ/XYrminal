"""
The terminal output widget.

Wraps QPlainTextEdit with:
    * line-oriented append (auto newline handling)
    * 50 ms timeout flush — data without trailing newline is still shown
    * optional timestamp prefix  [HH:MM:SS.mmm]
    * timestamp + text  for received data
    * timestamp + [Transmit:] prefix + payload  for sent data
    * timestamp + [PING:] + text  for ping output
    * [peer] prefix + text  for server-mode RX
    * server events ([+], [-], listening, stopped)
    * [SCENARIO] log lines
    * text triggers (TriggerStore) — recolor substrings of each line
    * optional auto-scroll
    * automatic buffer feeding to the LogWriter (plain + HTML with colors)
    * floating search panel (Ctrl+F) with live highlight + match counter
    * raw_text_received(str) signal for live plot parsing
    * public load_html_log() / load_plain_log() methods
"""

from __future__ import annotations

import html as _html

from datetime import datetime

from PyQt6.QtCore import Qt, QEvent, pyqtSignal, QTimer
from PyQt6.QtGui import (
    QTextCursor, QTextCharFormat, QColor, QKeySequence, QShortcut,
    QAction, QContextMenuEvent, QTextDocument,
)
from PyQt6.QtWidgets import QPlainTextEdit, QMenu, QTextEdit

from core.theme import ThemeManager, COLORS
from core.term_colors import (
    TerminalColorManager,
    CATEGORY_TIMESTAMPS,
    CATEGORY_PING,
    CATEGORY_TX_PREFIX,
    CATEGORY_TX_TEXT,
    CATEGORY_RX_TEXT,
    CATEGORY_PEER_PREFIX,
    CATEGORY_SERVER_EVENT,
    CATEGORY_SCENARIO,
)
from core.trigger_store import TriggerStore

from ui.widgets.search_panel import SearchPanel


MAX_BLOCK_COUNT = 5000


class TerminalView(QPlainTextEdit):
    raw_text_received = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setUndoRedoEnabled(False)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.document().setMaximumBlockCount(MAX_BLOCK_COUNT)

        self._autoscroll = True
        self._timestamps = False
        self._log_writer = None
        self._partial_line = ""
        self._log_view_mode = False
        self._trigger_prefix: str = "com"

        self._flush_timer = QTimer(self)
        self._flush_timer.setSingleShot(True)
        self._flush_timer.setInterval(50)
        self._flush_timer.timeout.connect(self._flush_partial)

        self._search_matches: list[QTextCursor] = []
        self._search_index: int = -1

        self._rebuild_formats()

        self._search_panel = SearchPanel(self)
        self._search_panel.hide()
        self._search_panel.search_changed.connect(self._on_search_changed)
        self._search_panel.next_requested.connect(self._search_next)
        self._search_panel.prev_requested.connect(self._search_prev)
        self._search_panel.close_requested.connect(self._close_search)

        self._sc_find = QShortcut(QKeySequence("Ctrl+F"), self)
        self._sc_find.activated.connect(self._open_search)

        self._sc_find_next = QShortcut(QKeySequence("F3"), self)
        self._sc_find_next.activated.connect(self._search_next)

        self._sc_find_prev = QShortcut(QKeySequence("Shift+F3"), self)
        self._sc_find_prev.activated.connect(self._search_prev)

        ThemeManager.instance().theme_changed.connect(self._on_theme_changed)
        ThemeManager.instance().theme_changed.connect(self._on_colors_changed)
        TerminalColorManager.instance().colors_changed.connect(self._on_colors_changed)

        # if triggers change, we do NOT redraw past lines — only future ones.
        # Triggers only affect what is emitted after they are saved.

    # -- colors ------------------------------------------------------------
    def _on_colors_changed(self, *_args) -> None:
        self._rebuild_formats()

    def _on_theme_changed(self, *_args) -> None:
        if self._search_panel.isVisible():
            self._highlight_matches()

    def _rebuild_formats(self) -> None:
        mgr = TerminalColorManager.instance()

        self._ts_fmt = QTextCharFormat()
        self._ts_fmt.setForeground(mgr.get_qcolor(CATEGORY_TIMESTAMPS))

        self._text_fmt = QTextCharFormat()
        self._text_fmt.setForeground(mgr.get_qcolor(CATEGORY_RX_TEXT))

        self._tx_prefix_fmt = QTextCharFormat()
        self._tx_prefix_fmt.setForeground(mgr.get_qcolor(CATEGORY_TX_PREFIX))

        self._tx_text_fmt = QTextCharFormat()
        self._tx_text_fmt.setForeground(mgr.get_qcolor(CATEGORY_TX_TEXT))

        self._ping_fmt = QTextCharFormat()
        self._ping_fmt.setForeground(mgr.get_qcolor(CATEGORY_PING))

        self._peer_fmt = QTextCharFormat()
        self._peer_fmt.setForeground(mgr.get_qcolor(CATEGORY_PEER_PREFIX))

        self._server_event_fmt = QTextCharFormat()
        self._server_event_fmt.setForeground(mgr.get_qcolor(CATEGORY_SERVER_EVENT))

        self._scenario_fmt = QTextCharFormat()
        self._scenario_fmt.setForeground(mgr.get_qcolor(CATEGORY_SCENARIO))

    # -- configuration -----------------------------------------------------
    def set_autoscroll(self, on: bool) -> None:
        self._autoscroll = on
        if on:
            self._scroll_to_end()

    def set_timestamps(self, on: bool) -> None:
        self._timestamps = on

    def set_log_writer(self, writer) -> None:
        self._log_writer = writer

    def set_trigger_prefix(self, prefix: str) -> None:
        self._trigger_prefix = prefix

    def reset_partial(self) -> None:
        self._partial_line = ""
        if hasattr(self, "_flush_timer"):
            self._flush_timer.stop()

    # -- public append: RX ------------------------------------------------
    def append_text(self, text: str, raw: bool = False) -> None:
        if not text:
            return

        self.raw_text_received.emit(text)

        if raw:
            self._partial_line = ""
            if hasattr(self, "_flush_timer"):
                self._flush_timer.stop()
            for line in text.split("\n"):
                self._emit_rx_line(line)
            self._refresh_search_after_append()
            return

        text = self._partial_line + text
        lines = text.split("\n")

        complete_lines = lines[:-1]
        if complete_lines and complete_lines[-1] == "" and text.endswith("\n"):
            complete_lines = complete_lines[:-1]

        for line in complete_lines:
            self._emit_rx_line(line)

        self._partial_line = lines[-1] if lines else ""

        if self._partial_line:
            if hasattr(self, "_flush_timer"):
                self._flush_timer.start()
        else:
            if hasattr(self, "_flush_timer"):
                self._flush_timer.stop()

        self._refresh_search_after_append()

    # -- public append: TX ------------------------------------------------
    def append_tx_text(self, text: str) -> None:
        if not text:
            return
        for line in text.split("\n"):
            self._emit_tx_line(line)
        self._refresh_search_after_append()

    # -- public append: PING ----------------------------------------------
    def append_ping_text(self, text: str) -> None:
        if not text:
            return
        for line in text.split("\n"):
            self._emit_ping_line(line)
        self._refresh_search_after_append()

    # -- public append: peer prefix ---------------------------------------
    def append_peer_text(self, prefix: str, text: str, raw: bool = False) -> None:
        if not text:
            return

        self.raw_text_received.emit(text)

        if raw:
            self._partial_line = ""
            if hasattr(self, "_flush_timer"):
                self._flush_timer.stop()
            for line in text.split("\n"):
                self._emit_peer_line(prefix, line)
            self._refresh_search_after_append()
            return

        text = self._partial_line + text
        lines = text.split("\n")
        complete_lines = lines[:-1]
        if complete_lines and complete_lines[-1] == "" and text.endswith("\n"):
            complete_lines = complete_lines[:-1]

        for line in complete_lines:
            self._emit_peer_line(prefix, line)

        self._partial_line = lines[-1] if lines else ""
        self._refresh_search_after_append()

    # -- public append: server events -------------------------------------
    def append_server_event(self, text: str) -> None:
        if not text:
            return
        for line in text.split("\n"):
            self._emit_server_event_line(line)
        self._refresh_search_after_append()

    # -- public append: scenario ------------------------------------------
    def append_scenario_text(self, text: str) -> None:
        if not text:
            return
        for line in text.split("\n"):
            self._emit_scenario_line(line)
        self._refresh_search_after_append()

    # -- open saved log ----------------------------------------------------
    def load_html_log(self, html: str) -> None:
        if not html:
            return

        self._partial_line = ""
        if hasattr(self, "_flush_timer"):
            self._flush_timer.stop()

        self._clear_highlights()
        self._search_matches.clear()
        self._search_index = -1
        if self._search_panel.isVisible():
            self._search_panel.set_counter(0, 0)

        if self._log_writer is not None:
            try:
                self._log_writer.clear()
            except Exception:
                pass

        self.setHtml(html)

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

        self._log_view_mode = True

    def load_plain_log(self, text: str) -> None:
        if not text:
            return

        self._partial_line = ""
        if hasattr(self, "_flush_timer"):
            self._flush_timer.stop()

        self._clear_highlights()
        self._search_matches.clear()
        self._search_index = -1
        if self._search_panel.isVisible():
            self._search_panel.set_counter(0, 0)

        if self._log_writer is not None:
            try:
                self._log_writer.clear()
            except Exception:
                pass

        self.clear()

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        for line in text.split("\n"):
            if line.endswith("\r"):
                line = line[:-1]
            cursor.insertText(line, self._text_fmt)
            cursor.insertText("\n", self._text_fmt)

        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

        self._log_view_mode = True

    def is_log_view_mode(self) -> bool:
        return getattr(self, "_log_view_mode", False)

    # -- partial flush ----------------------------------------------------
    def _flush_partial(self) -> None:
        if not self._partial_line:
            return
        line = self._partial_line
        self._partial_line = ""
        self._emit_rx_line(line)
        self._refresh_search_after_append()

    # -- HTML helpers ------------------------------------------------------
    @staticmethod
    def _fmt_color(fmt: QTextCharFormat) -> str:
        col = fmt.foreground().color()
        return col.name()

    @classmethod
    def _span(cls, fmt: QTextCharFormat, text: str) -> str:
        return (
            f"<span style=\"color:{cls._fmt_color(fmt)}\">"
            f"{_html.escape(text)}</span>"
        )

    # -- triggers ----------------------------------------------------------
    def _insert_with_triggers(self, cursor, text: str,
                              base_fmt: QTextCharFormat) -> str:
        """
        Insert `text` at cursor. Apply TriggerStore matches for the active
        prefix on top of base_fmt. Returns the html fragment string
        (already escaped).
        """
        store = TriggerStore.instance()
        matches = store.find_matches(self._trigger_prefix, text)

        if not matches:
            cursor.insertText(text, base_fmt)
            return self._span(base_fmt, text)

        html_parts: list[str] = []
        pos = 0
        for m in matches:
            if m.start > pos:
                piece = text[pos:m.start]
                cursor.insertText(piece, base_fmt)
                html_parts.append(self._span(base_fmt, piece))

            hf = QTextCharFormat()
            hf.setForeground(QColor(m.fg))
            hf.setBackground(QColor(m.bg))

            piece = text[m.start:m.end]
            cursor.insertText(piece, hf)
            html_parts.append(
                f"<span style=\"color:{m.fg};background-color:{m.bg}\">"
                f"{_html.escape(piece)}</span>"
            )
            pos = m.end

        if pos < len(text):
            piece = text[pos:]
            cursor.insertText(piece, base_fmt)
            html_parts.append(self._span(base_fmt, piece))

        return "".join(html_parts)

    # -- internal emitters -------------------------------------------------
    def _emit_rx_line(self, line: str) -> None:
        line = line.rstrip("\r")

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        html_parts: list[str] = []

        if self._timestamps:
            ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            ts_prefix = f"[{ts}] "
            cursor.insertText(ts_prefix, self._ts_fmt)
            plain_line = ts_prefix + line
            html_parts.append(self._span(self._ts_fmt, ts_prefix))
        else:
            plain_line = line

        html_parts.append(self._insert_with_triggers(cursor, line, self._text_fmt))
        cursor.insertText("\n", self._text_fmt)

        self._post_line(plain_line, "".join(html_parts))

    def _emit_tx_line(self, line: str) -> None:
        line = line.rstrip("\r")

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        html_parts: list[str] = []

        if self._timestamps:
            ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            ts_prefix = f"[{ts}] "
            cursor.insertText(ts_prefix, self._ts_fmt)
            plain_line = ts_prefix
            html_parts.append(self._span(self._ts_fmt, ts_prefix))
        else:
            plain_line = ""

        tx_prefix = "[Transmit:] "
        cursor.insertText(tx_prefix, self._tx_prefix_fmt)
        plain_line += tx_prefix
        html_parts.append(self._span(self._tx_prefix_fmt, tx_prefix))

        html_parts.append(self._insert_with_triggers(cursor, line, self._tx_text_fmt))
        plain_line += line

        cursor.insertText("\n", self._tx_text_fmt)

        self._post_line(plain_line, "".join(html_parts))

    def _emit_ping_line(self, line: str) -> None:
        line = line.rstrip("\r")

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        html_parts: list[str] = []

        if self._timestamps:
            ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            ts_prefix = f"[{ts}] "
            cursor.insertText(ts_prefix, self._ts_fmt)
            plain_line = ts_prefix
            html_parts.append(self._span(self._ts_fmt, ts_prefix))
        else:
            plain_line = ""

        ping_prefix = "[PING:] "
        cursor.insertText(ping_prefix, self._ping_fmt)
        plain_line += ping_prefix
        html_parts.append(self._span(self._ping_fmt, ping_prefix))

        html_parts.append(self._insert_with_triggers(cursor, line, self._ping_fmt))
        plain_line += line

        cursor.insertText("\n", self._ping_fmt)

        self._post_line(plain_line, "".join(html_parts))

    def _emit_peer_line(self, prefix: str, line: str) -> None:
        line = line.rstrip("\r")

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        html_parts: list[str] = []

        if self._timestamps:
            ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            ts_prefix = f"[{ts}] "
            cursor.insertText(ts_prefix, self._ts_fmt)
            plain_line = ts_prefix
            html_parts.append(self._span(self._ts_fmt, ts_prefix))
        else:
            plain_line = ""

        cursor.insertText(prefix, self._peer_fmt)
        plain_line += prefix
        html_parts.append(self._span(self._peer_fmt, prefix))

        html_parts.append(self._insert_with_triggers(cursor, line, self._text_fmt))
        plain_line += line

        cursor.insertText("\n", self._text_fmt)

        self._post_line(plain_line, "".join(html_parts))

    def _emit_server_event_line(self, line: str) -> None:
        line = line.rstrip("\r")

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        html_parts: list[str] = []

        if self._timestamps:
            ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            ts_prefix = f"[{ts}] "
            cursor.insertText(ts_prefix, self._ts_fmt)
            plain_line = ts_prefix
            html_parts.append(self._span(self._ts_fmt, ts_prefix))
        else:
            plain_line = ""

        html_parts.append(self._insert_with_triggers(cursor, line, self._server_event_fmt))
        plain_line += line

        cursor.insertText("\n", self._server_event_fmt)

        self._post_line(plain_line, "".join(html_parts))

    def _emit_scenario_line(self, line: str) -> None:
        line = line.rstrip("\r")

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        html_parts: list[str] = []

        if self._timestamps:
            ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            ts_prefix = f"[{ts}] "
            cursor.insertText(ts_prefix, self._ts_fmt)
            plain_line = ts_prefix
            html_parts.append(self._span(self._ts_fmt, ts_prefix))
        else:
            plain_line = ""

        html_parts.append(self._insert_with_triggers(cursor, line, self._scenario_fmt))
        plain_line += line

        cursor.insertText("\n", self._scenario_fmt)

        self._post_line(plain_line, "".join(html_parts))

    def clear_terminal(self) -> None:
        self.clear()
        self._partial_line = ""
        if hasattr(self, "_flush_timer"):
            self._flush_timer.stop()
        self._clear_highlights()
        self._log_view_mode = False
        if self._search_panel.isVisible():
            self._search_panel.set_counter(0, 0)

    # -- context menu ------------------------------------------------------
    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        menu = self.createStandardContextMenu()

        first = menu.actions()[0] if menu.actions() else None

        act_find = QAction(self.tr("Search") + "\tCtrl+F", self)
        act_find.triggered.connect(self._open_search)
        if first is not None:
            menu.insertAction(first, act_find)
        else:
            menu.addAction(act_find)

        menu.addSeparator()

        menu.exec(event.globalPos())

    # -- keyboard ----------------------------------------------------------
    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape and self._search_panel.isVisible():
            self._close_search()
            return
        if event.key() == Qt.Key.Key_F3:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self._search_prev()
            else:
                self._search_next()
            return
        super().keyPressEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reposition_search_panel()

    # -- search ------------------------------------------------------------
    def _open_search(self) -> None:
        self._search_panel.show()
        self._search_panel.raise_()
        self._reposition_search_panel()

        cursor = self.textCursor()
        if cursor.hasSelection():
            sel = cursor.selectedText()
            if sel and "\u2029" not in sel:
                self._search_panel.set_text(sel)

        self._search_panel.focus_input()

        if self._search_panel.text():
            self._on_search_changed(self._search_panel.text())

    def _close_search(self) -> None:
        self._search_panel.hide()
        self._clear_highlights()
        self.setFocus()

    def _on_search_changed(self, text: str) -> None:
        self._search_do(text)

    def _search_do(self, needle: str) -> None:
        self._clear_highlights()
        self._search_matches.clear()
        self._search_index = -1

        if not needle:
            self._search_panel.set_counter(0, 0)
            return

        doc = self.document()
        cursor = QTextCursor(doc)
        cursor.movePosition(QTextCursor.MoveOperation.Start)

        flags = QTextDocument.FindFlag(0)

        while True:
            cursor = doc.find(needle, cursor, flags)
            if cursor.isNull():
                break
            self._search_matches.append(QTextCursor(cursor))

        total = len(self._search_matches)
        if total == 0:
            self._search_panel.set_counter(0, 0)
            return

        self._search_index = 0
        self._highlight_matches()
        self._scroll_to_current_match()
        self._update_counter()

    def _highlight_matches(self) -> None:
        extra: list[QTextEdit.ExtraSelection] = []

        all_fmt = QTextCharFormat()
        all_fmt.setBackground(QColor(241, 196, 15, 80))

        for c in self._search_matches:
            sel = QTextEdit.ExtraSelection()
            sel.cursor = QTextCursor(c)
            sel.format = all_fmt
            extra.append(sel)

        if 0 <= self._search_index < len(self._search_matches):
            accent = QColor(COLORS.get("accent", "#a855f7"))
            accent.setAlpha(180)

            cur_fmt = QTextCharFormat()
            cur_fmt.setBackground(accent)
            cur_fmt.setForeground(QColor(COLORS.get("accent_text", "#ffffff")))

            sel = QTextEdit.ExtraSelection()
            sel.cursor = QTextCursor(self._search_matches[self._search_index])
            sel.format = cur_fmt
            extra.append(sel)

        self.setExtraSelections(extra)

    def _clear_highlights(self) -> None:
        self.setExtraSelections([])

    def _scroll_to_current_match(self) -> None:
        if not (0 <= self._search_index < len(self._search_matches)):
            return
        cursor = self._search_matches[self._search_index]
        view_cursor = QTextCursor(cursor)
        self.setTextCursor(view_cursor)
        self.ensureCursorVisible()

    def _update_counter(self) -> None:
        total = len(self._search_matches)
        if total == 0:
            self._search_panel.set_counter(0, 0)
        else:
            self._search_panel.set_counter(self._search_index + 1, total)

    def _search_next(self) -> None:
        if not self._search_matches:
            return
        self._search_index = (self._search_index + 1) % len(self._search_matches)
        self._highlight_matches()
        self._scroll_to_current_match()
        self._update_counter()

    def _search_prev(self) -> None:
        if not self._search_matches:
            return
        self._search_index = (self._search_index - 1) % len(self._search_matches)
        self._highlight_matches()
        self._scroll_to_current_match()
        self._update_counter()

    def _refresh_search_after_append(self) -> None:
        if self._search_panel.isVisible() and self._search_panel.text():
            keep = self._search_index
            self._search_do(self._search_panel.text())
            if self._search_matches:
                self._search_index = min(keep, len(self._search_matches) - 1) \
                    if keep >= 0 else 0
                self._highlight_matches()
                self._update_counter()

    def _reposition_search_panel(self) -> None:
        if not self._search_panel.isVisible():
            return
        margin = 12
        self._search_panel.adjustSize()
        w = self._search_panel.sizeHint().width()
        h = self._search_panel.sizeHint().height()
        x = max(margin, self.viewport().width() - w - margin)
        y = margin
        self._search_panel.setGeometry(x, y, w, h)

    # -- helpers -----------------------------------------------------------
    def _post_line(self, plain_line: str, html_line: str = "") -> None:
        if self._log_writer is not None:
            self._log_writer.add_line(plain_line, html_line or None)
        if self._autoscroll:
            self._scroll_to_end()

    def _scroll_to_end(self) -> None:
        self.moveCursor(QTextCursor.MoveOperation.End)
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())
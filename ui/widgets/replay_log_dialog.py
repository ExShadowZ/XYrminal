"""
Replay-able log viewer for .xyrmc files.

If the log contains timestamps in the form [HH:MM:SS.mmm] at the start
of each line, we offer a replay toolbar:

    ▶ Play    — start playing from the current position
    ⏸ Pause   — pause, keep the current position
    ⏹ Stop    — stop, reset to beginning, show the full log

Replay uses the original inter-line delays: if the log has 3 lines with
timestamps 10:00:00.000, 10:00:00.500, 10:00:02.000, then after pressing
Play we show line 1 immediately, line 2 after 500 ms, line 3 after
another 1500 ms.

If the log has no timestamps, the toolbar is hidden and the log is
shown in full immediately (plain viewer mode).
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, QEvent
from PyQt6.QtGui import QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTextBrowser, QLabel,
)

from core.theme import COLORS


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------
_TS_RE = re.compile(r"^\[(\d{2}):(\d{2}):(\d{2})\.(\d{3})\]\s?")

# Padding used in front of a replay line before its timestamp.
# Kept as a constant so future tweaks are easy.
_EMPTY_HTML = ""


def _parse_timestamp(line_text: str) -> Optional[timedelta]:
    """
    If `line_text` starts with "[HH:MM:SS.mmm]" return timedelta since
    midnight. Otherwise return None.
    """
    m = _TS_RE.match(line_text)
    if not m:
        return None
    hh, mm, ss, ms = (int(x) for x in m.groups())
    return timedelta(hours=hh, minutes=mm, seconds=ss, milliseconds=ms)


class ReplayLogDialog(QDialog):
    """
    Log viewer with optional replay toolbar.

    The dialog stores the ORIGINAL html, then during replay rebuilds the
    browser content from a list of per-line HTML fragments. Each fragment
    is the html representation of one line INCLUDING its own colors.
    """

    def __init__(self, log_path: Path, html: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Opened: {name}").format(name=log_path.name))
        self.resize(1000, 720)

        self._log_path = log_path
        self._html_original = html

        # per-line html fragments (strings) + their timestamps
        self._lines_html: list[str] = []
        self._lines_ts:   list[Optional[timedelta]] = []

        # replay state
        self._replay_idx: int = 0            # next line index to show
        self._replay_total: int = 0
        self._playing: bool = False

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timer)

        self._build_ui()
        self._retranslate()
        self._prepare()

        # hide replay controls by default; show only if timestamps found
        self._update_replay_controls()

    # -- UI ----------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.browser = QTextBrowser(self)
        self.browser.setOpenExternalLinks(False)
        root.addWidget(self.browser, stretch=1)

        # --- toolbar (only shown if replay possible) ---
        self.toolbar = QHBoxLayout()
        self.toolbar.setSpacing(8)

        self.btn_play = QPushButton(self)
        self.btn_play.setProperty("btnStyle", "ok")
        self.btn_play.clicked.connect(self._on_play)

        self.btn_pause = QPushButton(self)
        self.btn_pause.setProperty("btnStyle", "accent")
        self.btn_pause.clicked.connect(self._on_pause)
        self.btn_pause.setEnabled(False)

        self.btn_stop = QPushButton(self)
        self.btn_stop.setProperty("btnStyle", "danger")
        self.btn_stop.clicked.connect(self._on_stop)
        self.btn_stop.setEnabled(False)

        self.lbl_pos = QLabel(self)
        self.lbl_pos.setProperty("role", "dim")

        self.toolbar.addWidget(self.btn_play)
        self.toolbar.addWidget(self.btn_pause)
        self.toolbar.addWidget(self.btn_stop)
        self.toolbar.addSpacing(12)
        self.toolbar.addWidget(self.lbl_pos)
        self.toolbar.addStretch(1)

        root.addLayout(self.toolbar)

        # --- bottom: path + close ---
        bottom = QHBoxLayout()
        bottom.setSpacing(8)

        self.lbl_path = QLabel(str(self._log_path), self)
        self.lbl_path.setProperty("role", "dim")
        self.lbl_path.setTextInteractionFlags(
            self.lbl_path.textInteractionFlags()
            | Qt.TextInteractionFlag.TextSelectableByMouse
        )
        bottom.addWidget(self.lbl_path, stretch=1)

        self.btn_close = QPushButton(self)
        self.btn_close.setProperty("btnStyle", "accent")
        self.btn_close.clicked.connect(self.close)
        bottom.addWidget(self.btn_close)

        root.addLayout(bottom)

    def _retranslate(self) -> None:
        self.setWindowTitle(self.tr("Opened: {name}").format(name=self._log_path.name))
        self.btn_play.setText(self.tr("Play"))
        self.btn_pause.setText(self.tr("Pause"))
        self.btn_stop.setText(self.tr("Stop"))
        self.btn_close.setText(self.tr("Close"))
        self._update_pos_label()

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate()
        super().changeEvent(event)

    # -- preparation -------------------------------------------------------
    def _prepare(self) -> None:
        """
        Parse the html into a list of per-line fragments.

        A line = one <pre> line from the original html. Since our
        LogWriter writes one fragment per file line, the original html
        body is `\n`-separated fragments inside a single <pre>.
        """
        html = self._html_original or ""

        # strip header/footer to get just the <pre> body
        body = html
        pre_start = body.find("<pre>")
        pre_end = body.rfind("</pre>")
        if pre_start >= 0 and pre_end > pre_start:
            body = body[pre_start + len("<pre>"): pre_end]
        body = body.strip("\n")
        if not body:
            self._lines_html = []
            self._lines_ts = []
            self._replay_total = 0
            self.browser.setHtml(self._html_original)
            return

        raw_lines = body.split("\n")

        for raw in raw_lines:
            # detect timestamp prefix. We must ignore html tags — our
            # fragments are like:
            #   <span style="color:#...">[HH:MM:SS.mmm] </span>...
            # so let's strip tags just for timestamp detection.
            text_only = _strip_tags(raw)
            ts = _parse_timestamp(text_only)
            self._lines_html.append(raw)
            self._lines_ts.append(ts)

        self._replay_total = len(self._lines_html)

        # if NO timestamps at all — replay not possible → plain viewer
        if not any(ts is not None for ts in self._lines_ts):
            self.browser.setHtml(self._html_original)
            self._lines_html = []
            self._lines_ts = []
            self._replay_total = 0

    def _update_replay_controls(self) -> None:
        can_replay = self._replay_total > 0
        self.btn_play.setVisible(can_replay)
        self.btn_pause.setVisible(can_replay)
        self.btn_stop.setVisible(can_replay)
        self.lbl_pos.setVisible(can_replay)
        if not can_replay:
            return
        self._update_pos_label()

    def _update_pos_label(self) -> None:
        if self._replay_total == 0:
            self.lbl_pos.setText("")
            return
        self.lbl_pos.setText(
            self.tr("{a} / {b}").format(a=self._replay_idx, b=self._replay_total)
        )

    # -- replay: play / pause / stop --------------------------------------
    def _on_play(self) -> None:
        if self._replay_total == 0:
            return

        # if starting from scratch → clear the browser
        if self._replay_idx == 0:
            self.browser.clear()

        self._playing = True
        self.btn_play.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)

        # show the current line immediately, then schedule the next one
        self._show_next_line()

    def _on_pause(self) -> None:
        self._playing = False
        self._timer.stop()
        self.btn_play.setEnabled(True)
        self.btn_pause.setEnabled(False)

    def _on_stop(self) -> None:
        self._playing = False
        self._timer.stop()
        self._replay_idx = 0
        self.btn_play.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)

        # show full original log again
        self.browser.setHtml(self._html_original)
        self._update_pos_label()

    def _show_next_line(self) -> None:
        if not self._playing:
            return
        if self._replay_idx >= self._replay_total:
            # finished
            self._playing = False
            self.btn_play.setEnabled(True)
            self.btn_pause.setEnabled(False)
            self.btn_stop.setEnabled(False)
            return

        # append line to the browser
        frag = self._lines_html[self._replay_idx]
        self._append_html_fragment(frag)
        self._replay_idx += 1
        self._update_pos_label()

        # schedule next line based on the timestamp delta
        if self._replay_idx >= self._replay_total:
            # no more lines: finish immediately
            self._show_next_line()
            return

        delay_ms = self._compute_delay_ms(self._replay_idx - 1, self._replay_idx)
        self._timer.start(max(1, delay_ms))

    def _on_timer(self) -> None:
        self._show_next_line()

    def _compute_delay_ms(self, prev_idx: int, next_idx: int) -> int:
        """
        Compute the delay between two consecutive lines based on their
        timestamps. If timestamps are missing or non-monotonic — return 0.
        """
        ts_prev = self._lines_ts[prev_idx] if 0 <= prev_idx < len(self._lines_ts) else None
        ts_next = self._lines_ts[next_idx] if 0 <= next_idx < len(self._lines_ts) else None

        if ts_prev is None or ts_next is None:
            return 0

        delta = ts_next - ts_prev
        ms = int(delta.total_seconds() * 1000)
        if ms < 0:
            # wrap-around / non-monotonic; treat as 0
            return 0
        # cap huge gaps so replay doesn't freeze forever on a big pause
        return min(ms, 60_000)

    def _append_html_fragment(self, frag_html: str) -> None:
        """
        Append a raw html fragment to the QTextBrowser without resetting it.
        We use the cursor's html insertion via `QTextCursor.insertHtml`.
        """
        cursor = self.browser.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(frag_html)
        cursor.insertHtml("<br>")
        # auto-scroll to the new content
        self.browser.setTextCursor(cursor)
        self.browser.ensureCursorVisible()

    # -- cleanup -----------------------------------------------------------
    def closeEvent(self, event) -> None:
        self._timer.stop()
        self._playing = False
        super().closeEvent(event)


# ---------------------------------------------------------------------------
def _strip_tags(s: str) -> str:
    """
    Very light tag stripper — good enough for timestamp detection
    on LogWriter-generated lines, which only contain <span> tags.
    """
    out: list[str] = []
    depth = 0
    for ch in s:
        if ch == "<":
            depth += 1
            continue
        if ch == ">":
            if depth > 0:
                depth -= 1
            continue
        if depth == 0:
            out.append(ch)
    return "".join(out)
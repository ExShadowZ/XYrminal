"""
Live plot widget — draws a grid and one polyline per channel.

No external dependencies. Everything is done in paintEvent with QPainter.

Features:
    * two X modes:
        - normal (index mode): X = point index, window = N newest points
        - time mode: X = seconds ago (right edge = "now"), window = N seconds
          in time mode the plot keeps scrolling even without new data,
          and each channel holds its last value until a new sample arrives
          (step interpolation)
    * configurable view window (points or seconds) via PlotSettingsDialog
    * horizontal scrollbar in normal mode (browse the whole buffer);
      auto-scroll if at right edge
    * in time mode the scrollbar is hidden; window is always "now"
    * Y range auto-scales to visible points
    * grid + tick labels
    * legend at the top with channel names + last visible value
    * hover tooltip near the closest point
"""

from __future__ import annotations

import math

from PyQt6.QtCore import Qt, QPointF, QRectF, QTimer, QEvent
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QPolygonF, QBrush
from PyQt6.QtWidgets import (
    QWidget, QSizePolicy, QVBoxLayout, QHBoxLayout, QScrollBar, QLabel,
)

from core.plot_store import PlotStore, PlotChannel, MAX_POINTS
from core.settings import Settings
from core.theme import COLORS, ThemeManager


PADDING_LEFT   = 60
PADDING_RIGHT  = 16
PADDING_TOP    = 40
PADDING_BOTTOM = 30

DEFAULT_VIEW_POINTS = 20
DEFAULT_VIEW_SECONDS = 10.0

# Hover tolerance, px
HOVER_RADIUS = 14


class PlotWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(240, 200)

        self._store = PlotStore.instance()
        self._store.channel_data_added.connect(self._on_data)
        self._store.state_changed.connect(self._on_state)
        ThemeManager.instance().theme_changed.connect(lambda *_: self._canvas.update())

        # view config (loaded from settings, controlled by PlotSettingsDialog)
        s = Settings()
        self._view_points  = s.get_int("plot/view_points", DEFAULT_VIEW_POINTS)
        self._view_seconds = s.get_float("plot/view_seconds", DEFAULT_VIEW_SECONDS)
        self._time_mode    = s.get_bool("plot/time_mode", False)

        # normal-mode scroll offset (index of first visible point)
        self._offset: int = 0
        self._autoscroll: bool = True

        # time-mode repaint timer
        self._tick = QTimer(self)
        self._tick.setInterval(33)   # ~30 FPS
        self._tick.timeout.connect(self._canvas_update)

        self._build_ui()
        self._apply_mode()

    # -- ui ----------------------------------------------------------------
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(2)

        self._canvas = _PlotCanvas(self, self._store)
        outer.addWidget(self._canvas, stretch=1)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)
        bottom.setSpacing(6)

        self._scroll = QScrollBar(Qt.Orientation.Horizontal)
        self._scroll.setMinimum(0)
        self._scroll.setMaximum(0)
        self._scroll.setPageStep(self._view_points)
        self._scroll.valueChanged.connect(self._on_scroll)
        bottom.addWidget(self._scroll, stretch=1)

        self._info = QLabel()
        self._info.setProperty("role", "info")
        self._info.setMinimumWidth(90)
        self._info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom.addWidget(self._info)

        outer.addLayout(bottom)

    # -- public API (called from PlotSettingsDialog) -----------------------
    def set_view_points(self, n: int) -> None:
        n = max(5, min(MAX_POINTS, int(n)))
        if n == self._view_points:
            return
        self._view_points = n
        self._scroll.setPageStep(n)
        self._refresh_scroll_range()
        if self._autoscroll:
            self._offset = self._max_offset()
            self._scroll.blockSignals(True)
            self._scroll.setValue(self._offset)
            self._scroll.blockSignals(False)
        self._update_info()
        self._canvas.update()

    def set_view_seconds(self, sec: float) -> None:
        sec = max(0.5, min(600.0, float(sec)))
        self._view_seconds = sec
        self._canvas.update()

    def set_time_mode(self, on: bool) -> None:
        self._time_mode = bool(on)
        self._apply_mode()

    def view_points(self) -> int:
        return self._view_points

    def view_seconds(self) -> float:
        return self._view_seconds

    def time_mode(self) -> bool:
        return self._time_mode

    # -- mode switching ----------------------------------------------------
    def _apply_mode(self) -> None:
        if self._time_mode:
            self._scroll.hide()
            if self._store.is_active() and not self._store.is_paused():
                self._tick.start()
            else:
                self._tick.stop()
        else:
            self._scroll.show()
            self._tick.stop()
        self._refresh_scroll_range()
        self._update_info()
        self._canvas.update()

    # -- data / state ------------------------------------------------------
    def _on_data(self) -> None:
        self._refresh_scroll_range()
        if not self._time_mode and self._autoscroll:
            self._offset = self._max_offset()
            self._scroll.blockSignals(True)
            self._scroll.setValue(self._offset)
            self._scroll.blockSignals(False)

        self._update_info()
        self._canvas.update()

    def _on_state(self) -> None:
        if not self._store.is_active():
            # session ended (Stop)
            self._autoscroll = True
            self._offset = 0
            self._refresh_scroll_range()
            self._scroll.blockSignals(True)
            self._scroll.setValue(0)
            self._scroll.blockSignals(False)
            self._update_info()
            self._canvas.update()
            return

        # session is active — react to pause/resume
        if self._time_mode:
            if self._store.is_paused():
                self._tick.stop()
            else:
                self._tick.start()

        self._update_info()
        self._canvas.update()

    def _canvas_update(self) -> None:
        """Called by the time-mode tick timer."""
        self._update_info()
        self._canvas.update()

    # -- scrollbar ---------------------------------------------------------
    def _longest_channel_len(self) -> int:
        chans = self._store.channels()
        return max((len(c.values) for c in chans), default=0)

    def _max_offset(self) -> int:
        n = self._longest_channel_len()
        return max(0, n - self._view_points)

    def _refresh_scroll_range(self) -> None:
        n = self._longest_channel_len()
        max_off = max(0, n - self._view_points)
        self._scroll.blockSignals(True)
        self._scroll.setMinimum(0)
        self._scroll.setMaximum(max_off)
        self._scroll.setPageStep(self._view_points)
        if self._scroll.value() > max_off:
            self._scroll.setValue(max_off)
            self._offset = max_off
        self._scroll.blockSignals(False)

    def _on_scroll(self, value: int) -> None:
        self._offset = value
        self._autoscroll = (value >= self._scroll.maximum())
        self._update_info()
        self._canvas.update()

    def _update_info(self) -> None:
        if self._time_mode:
            # show "window seconds" indicator
            self._info.setText(f"[-{_fmt_sec(self._view_seconds)}]")
            return

        n = self._longest_channel_len()
        if n == 0:
            self._info.setText("0 / 0")
            return
        first = self._offset + 1
        last = min(self._offset + self._view_points, n)
        self._info.setText(f"{first}–{last} / {n}")

    # -- paint delegation --------------------------------------------------
    def paintEvent(self, event) -> None:
        super().paintEvent(event)


# ---------------------------------------------------------------------------
# Internal API used by _PlotCanvas
# ---------------------------------------------------------------------------
def _fmt_sec(sec: float) -> str:
    if sec >= 60:
        m = int(sec // 60)
        s = sec - m * 60
        return f"{m}m{s:04.1f}s"
    if sec >= 10:
        return f"{sec:.0f}s"
    return f"{sec:.1f}s"


# ---------------------------------------------------------------------------
# The drawing surface
# ---------------------------------------------------------------------------
class _PlotCanvas(QWidget):
    def __init__(self, owner: "PlotWidget", store: PlotStore, parent=None):
        super().__init__(parent or owner)
        self._owner = owner
        self._store = store
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(220, 160)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        # hover: (channel_index, point_index) or None
        self._hover: tuple[int, int] | None = None
        # screen-space position of hovered point for tooltip
        self._hover_pos: QPointF | None = None

    # -- mouse -------------------------------------------------------------
    def leaveEvent(self, event) -> None:
        if self._hover is not None:
            self._hover = None
            self._hover_pos = None
            self.update()

    def mouseMoveEvent(self, event) -> None:
        pos = event.position()  # QPointF in Qt6
        hit = self._find_nearest_point(pos)
        if hit != self._hover:
            self._hover = hit
            self.update()
        else:
            # still repaint tooltip if pos changed slightly
            self._hover_pos = pos
            self.update()

    # -- painting ----------------------------------------------------------
    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        bg    = QColor(COLORS["bg_input"])
        grid  = QColor(COLORS["border"])
        text  = QColor(COLORS["text_dim"])
        frame = QColor(COLORS["border"])
        muted = QColor(COLORS["text_muted"])

        p.fillRect(self.rect(), bg)

        plot_rect = QRectF(
            PADDING_LEFT,
            PADDING_TOP,
            max(10, self.width()  - PADDING_LEFT - PADDING_RIGHT),
            max(10, self.height() - PADDING_TOP  - PADDING_BOTTOM),
        )

        channels = self._store.channels()

        # ---- compute visible slice + Y range ----
        if self._owner.time_mode():
            visible_values = self._visible_values_time(channels)
        else:
            visible_values = self._visible_values_index(channels)

        y_min, y_max = self._compute_y_range(visible_values)

        # ---- grid ----
        p.setPen(QPen(grid, 1, Qt.PenStyle.DotLine))
        y_steps = 5
        for i in range(y_steps + 1):
            frac = i / y_steps
            y = plot_rect.bottom() - frac * plot_rect.height()
            p.drawLine(QPointF(plot_rect.left(), y), QPointF(plot_rect.right(), y))

            value = y_min + frac * (y_max - y_min)
            p.setPen(QPen(text))
            p.setFont(QFont(self.font().family(), 8))
            p.drawText(
                QRectF(0, y - 8, PADDING_LEFT - 6, 16),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                self._format_num(value),
            )
            p.setPen(QPen(grid, 1, Qt.PenStyle.DotLine))

        x_steps = 5
        for i in range(x_steps + 1):
            frac = i / x_steps
            x = plot_rect.left() + frac * plot_rect.width()
            p.drawLine(QPointF(x, plot_rect.top()), QPointF(x, plot_rect.bottom()))

            # X tick label
            if self._owner.time_mode():
                sec = self._owner.view_seconds()
                label_sec = sec * (1 - frac)   # leftmost = -window, rightmost = 0
                label = f"-{_fmt_sec(label_sec)}" if label_sec > 0.01 else "now"
            else:
                label = ""   # no X labels in index mode

            if label:
                p.setPen(QPen(text))
                p.setFont(QFont(self.font().family(), 8))
                p.drawText(
                    QRectF(x - 40, plot_rect.bottom() + 2, 80, 16),
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                    label,
                )

        # ---- frame ----
        p.setPen(QPen(frame, 1))
        p.drawRect(plot_rect)

        # ---- legend ----
        self._draw_legend(p, plot_rect, channels)

        # ---- data ----
        if not channels:
            p.setPen(QPen(muted))
            p.drawText(plot_rect, Qt.AlignmentFlag.AlignCenter, "No channels")
            self._draw_tooltip(p, plot_rect, channels, y_min, y_max)
            return

        if self._owner.time_mode():
            self._draw_channels_time(p, plot_rect, channels, y_min, y_max)
        else:
            self._draw_channels_index(p, plot_rect, channels, y_min, y_max)

        # ---- tooltip (drawn on top) ----
        self._draw_tooltip(p, plot_rect, channels, y_min, y_max)

    # -- visible-value collectors -----------------------------------------
    def _visible_values_index(self, channels: list[PlotChannel]) -> list[float]:
        offset = self._owner._offset
        vp = self._owner.view_points()
        out: list[float] = []
        for ch in channels:
            if not ch.values:
                continue
            lo = min(offset, len(ch.values))
            hi = min(offset + vp, len(ch.values))
            out.extend(ch.values[lo:hi])
        return out

    def _visible_values_time(self, channels: list[PlotChannel]) -> list[float]:
        now = self._store.now_seconds()
        t_min = now - self._owner.view_seconds()
        out: list[float] = []
        for ch in channels:
            for t, v in zip(ch.times, ch.values):
                if t >= t_min:
                    out.append(v)
        return out

    # -- drawing: index mode ----------------------------------------------
    def _draw_channels_index(self, p: QPainter, plot_rect: QRectF,
                             channels: list[PlotChannel],
                             y_min: float, y_max: float) -> None:
        offset = self._owner._offset
        vp = self._owner.view_points()

        n_max = self._owner._longest_channel_len()
        visible_count = min(vp, max(0, n_max - offset))
        if visible_count < 2:
            return

        x_range = max(1, visible_count - 1)

        for ch in channels:
            lo = min(offset, len(ch.values))
            hi = min(offset + vp, len(ch.values))
            if hi - lo < 2:
                continue

            slice_vals = ch.values[lo:hi]
            pad_left = vp - visible_count

            poly = QPolygonF()
            for i, v in enumerate(slice_vals):
                slot = pad_left + (lo - offset) + i
                if slot < 0 or slot >= vp:
                    continue
                fx = slot / x_range
                fy = (v - y_min) / (y_max - y_min) if y_max > y_min else 0.5
                x = plot_rect.left() + fx * plot_rect.width()
                y = plot_rect.bottom() - fy * plot_rect.height()
                poly.append(QPointF(x, y))

            if poly.size() < 2:
                continue

            p.setPen(QPen(QColor(ch.color), 1.6))
            p.drawPolyline(poly)

    # -- drawing: time mode ------------------------------------------------
    def _draw_channels_time(self, p: QPainter, plot_rect: QRectF,
                            channels: list[PlotChannel],
                            y_min: float, y_max: float) -> None:
        now = self._store.now_seconds()
        window = self._owner.view_seconds()
        if window <= 0:
            return
        t_min = now - window

        # X mapping: t_min → plot_rect.left, now → plot_rect.right
        def x_of(t: float) -> float:
            frac = (t - t_min) / window
            return plot_rect.left() + frac * plot_rect.width()

        def y_of(v: float) -> float:
            if y_max <= y_min:
                return plot_rect.center().y()
            fy = (v - y_min) / (y_max - y_min)
            return plot_rect.bottom() - fy * plot_rect.height()

        for ch in channels:
            if not ch.times:
                continue

            # Slice visible points. Also include the last sample BEFORE
            # the window so the line enters the window from the left.
            idx_start = 0
            for i, t in enumerate(ch.times):
                if t >= t_min:
                    idx_start = max(0, i - 1)
                    break
            else:
                idx_start = len(ch.times) - 1

            visible: list[tuple[float, float]] = []
            for i in range(idx_start, len(ch.times)):
                t = ch.times[i]
                v = ch.values[i]
                if t >= t_min:
                    visible.append((t, v))
                else:
                    visible.append((t, v))   # keep first for continuity

            # Build step-shaped polyline:
            #   (t_i, y_i) → (t_{i+1}, y_i) → (t_{i+1}, y_{i+1}) → ...
            poly = QPolygonF()
            prev_v: float | None = None
            for i, (t, v) in enumerate(visible):
                xt = x_of(max(t, t_min))    # clamp left edge
                yt = y_of(v)

                if prev_v is not None:
                    # horizontal segment to this X at previous Y
                    poly.append(QPointF(xt, y_of(prev_v)))
                poly.append(QPointF(xt, yt))
                prev_v = v

            # Extend the last value horizontally to "now"
            if prev_v is not None:
                x_now = plot_rect.right()
                y_last = y_of(prev_v)
                if poly.size() > 0 and poly.last() != QPointF(x_now, y_last):
                    poly.append(QPointF(x_now, y_last))

            if poly.size() < 2:
                continue

            p.setPen(QPen(QColor(ch.color), 1.6))
            p.drawPolyline(poly)

    # -- hover: nearest point ----------------------------------------------
    def _find_nearest_point(self, pos: QPointF) -> tuple[int, int] | None:
        """
        Return (channel_idx, point_idx) of the point closest to `pos`
        within HOVER_RADIUS px. None if nothing is close enough.
        """
        channels = self._store.channels()
        if not channels:
            return None

        plot_rect = QRectF(
            PADDING_LEFT,
            PADDING_TOP,
            max(10, self.width()  - PADDING_LEFT - PADDING_RIGHT),
            max(10, self.height() - PADDING_TOP  - PADDING_BOTTOM),
        )

        y_min, y_max = self._compute_y_range(
            self._visible_values_time(channels) if self._owner.time_mode()
            else self._visible_values_index(channels)
        )

        if self._owner.time_mode():
            now = self._store.now_seconds()
            window = self._owner.view_seconds()
            t_min = now - window
            x_of = lambda t: plot_rect.left() + (max(t, t_min) - t_min) / window * plot_rect.width()
        else:
            offset = self._owner._offset
            vp = self._owner.view_points()
            n_max = self._owner._longest_channel_len()
            visible_count = min(vp, max(0, n_max - offset))
            x_range = max(1, visible_count - 1)
            pad_left = vp - visible_count

            def x_of_idx(idx_in_slice: int) -> float:
                slot = pad_left + idx_in_slice
                return plot_rect.left() + slot / x_range * plot_rect.width()

        def y_of(v: float) -> float:
            if y_max <= y_min:
                return plot_rect.center().y()
            return plot_rect.bottom() - (v - y_min) / (y_max - y_min) * plot_rect.height()

        best: tuple[int, int] | None = None
        best_dist = HOVER_RADIUS * HOVER_RADIUS  # squared threshold

        for ci, ch in enumerate(channels):
            if not ch.values:
                continue

            if self._owner.time_mode():
                now = self._store.now_seconds()
                window = self._owner.view_seconds()
                t_min = now - window
                for pi, (t, v) in enumerate(zip(ch.times, ch.values)):
                    if t < t_min:
                        continue
                    px = x_of(t)
                    py = y_of(v)
                    d = (px - pos.x())**2 + (py - pos.y())**2
                    if d < best_dist:
                        best_dist = d
                        best = (ci, pi)
            else:
                offset = self._owner._offset
                vp = self._owner.view_points()
                lo = min(offset, len(ch.values))
                hi = min(offset + vp, len(ch.values))
                for pi in range(lo, hi):
                    v = ch.values[pi]
                    px = x_of_idx(pi - offset)
                    py = y_of(v)
                    d = (px - pos.x())**2 + (py - pos.y())**2
                    if d < best_dist:
                        best_dist = d
                        best = (ci, pi)

        return best

    # -- tooltip drawing ---------------------------------------------------
    def _draw_tooltip(self, p: QPainter, plot_rect: QRectF,
                      channels: list[PlotChannel],
                      y_min: float, y_max: float) -> None:
        if self._hover is None:
            return

        ci, pi = self._hover
        if ci < 0 or ci >= len(channels):
            return
        ch = channels[ci]
        if pi < 0 or pi >= len(ch.values):
            return

        v = ch.values[pi]
        t = ch.times[pi] if pi < len(ch.times) else 0.0

        if self._owner.time_mode():
            now = self._store.now_seconds()
            rel = t - now
            text = f"{ch.name}: {self._format_num(v)}   t={rel:+.2f}s"
            x = plot_rect.left() + (max(t, now - self._owner.view_seconds())
                                    - (now - self._owner.view_seconds())) \
                / self._owner.view_seconds() * plot_rect.width()
        else:
            vp = self._owner.view_points()
            n_max = self._owner._longest_channel_len()
            offset = self._owner._offset
            visible_count = min(vp, max(0, n_max - offset))
            x_range = max(1, visible_count - 1)
            pad_left = vp - visible_count
            slot = pad_left + (pi - offset)
            x = plot_rect.left() + slot / x_range * plot_rect.width()
            text = f"{ch.name}: {self._format_num(v)}   #{pi + 1}"

        y = plot_rect.bottom() - ((v - y_min) / (y_max - y_min) if y_max > y_min else 0.5) \
            * plot_rect.height()

        # draw marker dot
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(ch.color)))
        p.drawEllipse(QPointF(x, y), 4, 4)

        # tooltip box
        p.setFont(QFont(self.font().family(), 8))
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(text) + 12
        th = fm.height() + 8

        tx = x + 10
        ty = y - th - 6
        if tx + tw > plot_rect.right():
            tx = x - tw - 10
        if ty < plot_rect.top():
            ty = y + 8
        if tx < plot_rect.left():
            tx = plot_rect.left() + 2

        box = QRectF(tx, ty, tw, th)
        p.setPen(QPen(QColor(COLORS["border"]), 1))
        p.setBrush(QBrush(QColor(COLORS["bg_panel"])))
        p.drawRect(box)

        p.setPen(QPen(QColor(COLORS["text"])))
        p.drawText(box, Qt.AlignmentFlag.AlignCenter, text)

    # -- helpers -----------------------------------------------------------
    def _compute_y_range(self, values: list[float]) -> tuple[float, float]:
        if not values:
            return 0.0, 1.0
        lo = min(values)
        hi = max(values)
        if math.isclose(lo, hi):
            pad = abs(lo) * 0.1 or 1.0
            return lo - pad, hi + pad
        pad = (hi - lo) * 0.05
        return lo - pad, hi + pad

    @staticmethod
    def _format_num(v: float) -> str:
        if abs(v) >= 1000:
            return f"{v:.0f}"
        if abs(v) >= 10:
            return f"{v:.1f}"
        return f"{v:.3f}".rstrip("0").rstrip(".")

    def _draw_legend(self, p: QPainter, plot_rect: QRectF,
                     channels: list[PlotChannel]) -> None:
        if not channels:
            return

        p.setFont(QFont(self.font().family(), 8))
        x = plot_rect.left()
        y = PADDING_TOP - 22

        for ch in channels:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(ch.color))
            p.drawRect(QRectF(x, y + 3, 10, 10))

            last = self._last_visible_value(ch)
            label = ch.name if last is None else f"{ch.name} = {self._format_num(last)}"

            p.setPen(QPen(QColor(COLORS["text"])))
            fm = p.fontMetrics()
            w = fm.horizontalAdvance(label) + 4
            p.drawText(
                QRectF(x + 14, y, w, 16),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                label,
            )
            x += 14 + w + 16
            if x > plot_rect.right() - 80:
                x = plot_rect.left()
                y += 16

    def _last_visible_value(self, ch: PlotChannel) -> float | None:
        if not ch.values:
            return None
        if self._owner.time_mode():
            now = self._store.now_seconds()
            t_min = now - self._owner.view_seconds()
            last = None
            for t, v in zip(ch.times, ch.values):
                if t >= t_min:
                    last = v
            if last is None:
                last = ch.values[-1]
            return last
        else:
            offset = self._owner._offset
            hi = min(offset + self._owner.view_points(), len(ch.values))
            if hi <= 0:
                return None
            return ch.values[hi - 1]
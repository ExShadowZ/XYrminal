"""
File transfer controller for XYrminal.

Bridges:
    * Qt (signals, QThread, progress)
    * workers (SerialWorker / TcpWorker / UdpWorker) — via a write() callable
    * protocols (Raw / XMODEM / YMODEM)

Runs the transfer in a separate QThread so the UI stays responsive.
The worker's write() must be thread-safe — for our workers it's just
serial.write() / sock.sendall(), which is fine.

Signals:
    progress(sent, total)   — bytes sent / total bytes
    status(str)             — human-readable status line (for the progress bar)
    finished(bool, str)     — ok, error message ("" if ok)
"""

from __future__ import annotations

import os
import time
from typing import Callable, Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from core.xmodem import (
    XModemSender, YModemSender, XModemError, ByteIo,
)


# ---------------------------------------------------------------------------
# Byte Io adapter for XMODEM: reads bytes from a queue (fed by us) and writes
# them out via the worker's write() callable.
#
# But XMODEM needs read access to the SAME stream the file transfer writes to
# — i.e. it must read the receiver's ACK/NAK responses. In our setup, the
# worker owns the stream and pushes data to the UI asynchronously. For file
# transfer we need synchronous reads.
#
# Solution: the tab pauses its normal data-received slot during transfer and
# routes incoming bytes into this adapter's queue.
# ---------------------------------------------------------------------------
class WorkerByteIo(ByteIo):
    """
    Adapter that:
        * writes outgoing bytes via `write_cb(data)`
        * reads incoming bytes from `self._inbox` (list, appended by the tab)

    Usage:
        io = WorkerByteIo(lambda d: worker.write(d))
        file_sender.start(path, protocol, io)
        # in tab._on_data_received: if transfer active → io.push(chunk)
        # else → normal terminal display
    """

    def __init__(self, write_cb: Callable[[bytes], None]):
        self._write_cb = write_cb
        self._inbox: list[bytes] = []

    # -- XMODEM facing -----------------------------------------------------
    def write_bytes(self, data: bytes) -> None:
        self._write_cb(data)

    def read_byte(self, timeout: float) -> bytes:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._inbox:
                # pop one byte from the front
                first = self._inbox[0]
                b = first[:1]
                rest = first[1:]
                if rest:
                    self._inbox[0] = rest
                else:
                    self._inbox.pop(0)
                return b
            time.sleep(0.005)
        return b""

    # -- from the tab ------------------------------------------------------
    def push(self, data: bytes) -> None:
        """Called by the tab on every received chunk while transfer is active."""
        if data:
            self._inbox.append(bytes(data))

    def clear(self) -> None:
        self._inbox.clear()


# ---------------------------------------------------------------------------
# The transfer thread
# ---------------------------------------------------------------------------
class _TransferThread(QThread):
    progress = pyqtSignal(int, int)
    status   = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, path: str, protocol: str, io_: WorkerByteIo,
                 chunk_size: int, delay_ms: int, parent=None):
        super().__init__(parent)
        self._path = path
        self._protocol = protocol
        self._io = io_
        self._chunk_size = chunk_size
        self._delay_ms = delay_ms
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        try:
            if self._protocol == "raw":
                self._run_raw()
            elif self._protocol == "xmodem":
                self._run_xmodem()
            elif self._protocol == "ymodem":
                self._run_ymodem()
            elif self._protocol == "zmodem":
                self.finished.emit(False, "ZMODEM not implemented yet")
            else:
                self.finished.emit(False, f"Unknown protocol: {self._protocol}")
                return
        except XModemError as exc:
            self.finished.emit(False, str(exc))
            return
        except Exception as exc:
            self.finished.emit(False, f"{type(exc).__name__}: {exc}")
            return

        self.finished.emit(True, "")

    # -- raw ---------------------------------------------------------------
    def _run_raw(self) -> None:
        total = os.path.getsize(self._path)
        sent = 0

        with open(self._path, "rb") as f:
            while True:
                if self._cancel:
                    self.finished.emit(False, "Cancelled")
                    return
                chunk = f.read(self._chunk_size)
                if not chunk:
                    break
                self._io.write_bytes(chunk)
                sent += len(chunk)
                self.progress.emit(sent, total)
                if self._delay_ms > 0:
                    self._sleep_ms(self._delay_ms)

    # -- xmodem / ymodem ---------------------------------------------------
    def _run_xmodem(self) -> None:
        self.status.emit("Waiting for receiver…")
        sender = XModemSender(self._io, block_size=128)
        self._attach_cancel(sender)
        sender.send_file(self._path)

    def _run_ymodem(self) -> None:
        self.status.emit("Waiting for receiver…")
        sender = YModemSender(self._io)
        self._attach_cancel(sender)
        sender.send_file(self._path)

    def _attach_cancel(self, sender) -> None:
        # XModemSender checks `cancel_requested` every loop iteration —
        # we replace the boolean attribute with an object whose __bool__
        # reads the thread's `_cancel` flag live.
        sender.cancel_requested = _CancelFlag(self)
        sender.progress_cb = self._xmodem_progress

    def _xmodem_progress(self, sent: int, total: int) -> None:
        self.progress.emit(sent, total)

    # -- helpers -----------------------------------------------------------
    def _sleep_ms(self, ms: int) -> None:
        # sleep in small chunks so cancel is responsive
        end = time.monotonic() + ms / 1000.0
        while time.monotonic() < end:
            if self._cancel:
                return
            time.sleep(0.01)


# ---------------------------------------------------------------------------
# Public wrapper
# ---------------------------------------------------------------------------
class FileSender(QObject):
    """
    Public interface for the tabs. Wrap the thread, keep a reference to
    the io adapter (so the tab can push incoming bytes).
    """

    progress = pyqtSignal(int, int)   # sent, total
    status   = pyqtSignal(str)
    finished = pyqtSignal(bool, str)  # ok, error message

    def __init__(self, write_cb: Callable[[bytes], None], parent=None):
        super().__init__(parent)
        self.io = WorkerByteIo(write_cb)
        self._thread: Optional[_TransferThread] = None

    def start(self, path: str, protocol: str,
              chunk_size: int = 256, delay_ms: int = 10) -> None:
        self.stop()  # any previous
        self.io.clear()
        self._thread = _TransferThread(path, protocol, self.io,
                                       chunk_size, delay_ms, self)
        self._thread.progress.connect(self.progress)
        self._thread.status.connect(self.status)
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.start()

    def cancel(self) -> None:
        if self._thread is not None:
            self._thread.cancel()

    def is_active(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def stop(self) -> None:
        if self._thread is not None:
            self._thread.cancel()
            self._thread.wait(2000)
            self._thread = None

    # -- internal ----------------------------------------------------------
    def _on_thread_finished(self, ok: bool, err: str) -> None:
        self.finished.emit(ok, err)
        self._thread = None


# ---------------------------------------------------------------------------
# tiny helper: a cancel flag that reads from the thread
# ---------------------------------------------------------------------------
class _CancelFlag:
    def __init__(self, thread: _TransferThread):
        self._thread = thread

    def __bool__(self) -> bool:
        return self._thread._cancel
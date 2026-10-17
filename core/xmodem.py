"""
XMODEM / YMODEM sender — bare-bones, dependency-free.

Implements the classic XMODEM-128 (128-byte blocks), XMODEM-1K (1024-byte
blocks), and YMODEM (first block carries file name + size) protocols with
CRC-16.

The implementation is written against an abstract `io` object which must
provide:

    .read_byte(timeout) -> bytes | b""   # read 1 byte, or b"" on timeout
    .write_bytes(data)                    # send raw bytes

Both methods are blocking and are expected to run inside a worker thread
or a QTimer-driven step machine. Here we use a simple blocking loop; the
FileSender wraps it in a QThread.

Public API:

    class XModemError(Exception): ...

    class XModemSender:
        def __init__(self, io, block_size=128, timeout=3.0, retries=10): ...
        def send_file(self, path: str, name: str | None = None) -> None: ...

    class YModemSender(XModemSender):
        # adds a "block 0" with filename and size
        ...

Both raise XModemError on failure. No GUI, no Qt here.
"""

from __future__ import annotations

import io as _io
import os
import time
from typing import BinaryIO, Optional


# XMODEM control bytes
SOH = 0x01   # 128-byte block header
STX = 0x02   # 1024-byte block header
EOT = 0x04
ACK = 0x06
NAK = 0x15
CAN = 0x18
SUB = 0x1A   # padding byte
C   = 0x43   # 'C' — request CRC mode


class XModemError(Exception):
    pass


def crc16_xmodem(data: bytes) -> int:
    """CRC-16/XMODEM (poly 0x1021, init 0x0000)."""
    crc = 0
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


# ---------------------------------------------------------------------------
# Abstract byte I/O — implemented by the SerialIoAdapter / SocketIoAdapter
# in file_sender.py
# ---------------------------------------------------------------------------
class ByteIo:
    """Interface: read_byte() / write_bytes() must be overridden."""

    def read_byte(self, timeout: float) -> bytes:
        raise NotImplementedError

    def write_bytes(self, data: bytes) -> None:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# XMODEM
# ---------------------------------------------------------------------------
class XModemSender:
    def __init__(self, io_: ByteIo, block_size: int = 128,
                 timeout: float = 3.0, retries: int = 10):
        if block_size not in (128, 1024):
            raise ValueError("block_size must be 128 or 1024")
        self._io = io_
        self._block_size = block_size
        self._timeout = timeout
        self._retries = retries

        # progress hook (callable sent_bytes:int, total:int)
        self.progress_cb = None
        self.cancel_requested = False

    # -- public ------------------------------------------------------------
    def send_file(self, path: str, name: Optional[str] = None) -> None:
        """Send a file. name is ignored for plain XMODEM (kept for API parity)."""
        with open(path, "rb") as f:
            data = f.read()
        self._send_stream(data)

    # -- internal ----------------------------------------------------------
    def _send_stream(self, data: bytes) -> None:
        # 1. wait for receiver to request CRC mode ('C')
        self._wait_for_receiver()

        total = len(data)
        sent = 0
        block_no = 1
        pos = 0

        while pos < total:
            if self.cancel_requested:
                raise XModemError("Cancelled")

            chunk = data[pos:pos + self._block_size]
            self._send_block(block_no, chunk)
            pos += len(chunk)
            sent = pos
            if self.progress_cb:
                self.progress_cb(sent, total)
            block_no = (block_no + 1) & 0xFF

        # 2. end of transmission
        self._send_eot()

    def _wait_for_receiver(self) -> None:
        """Wait for 'C' (CRC mode) up to timeout. NAK → we don't do checksum mode."""
        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            if self.cancel_requested:
                raise XModemError("Cancelled")
            b = self._io.read_byte(0.1)
            if not b:
                continue
            if b[0] == C:
                return
            if b[0] == NAK:
                raise XModemError("Receiver requested checksum mode; only CRC supported")
        raise XModemError("Timeout waiting for receiver ('C' not received)")

    def _send_block(self, block_no: int, data: bytes) -> None:
        size = self._block_size
        header = SOH if size == 128 else STX
        blk = block_no & 0xFF
        inv = (~blk) & 0xFF

        padded = data + bytes([SUB]) * (size - len(data))
        crc = crc16_xmodem(padded)
        packet = bytes([header, blk, inv]) + padded + bytes([(crc >> 8) & 0xFF, crc & 0xFF])

        for attempt in range(self._retries):
            if self.cancel_requested:
                raise XModemError("Cancelled")
            self._io.write_bytes(packet)
            r = self._wait_ack()
            if r == "ack":
                return
            if r == "can":
                raise XModemError("Receiver cancelled")
            # NAK → retry
        raise XModemError(f"Block {block_no} failed after {self._retries} retries")

    def _send_eot(self) -> None:
        for attempt in range(self._retries):
            if self.cancel_requested:
                raise XModemError("Cancelled")
            self._io.write_bytes(bytes([EOT]))
            r = self._wait_ack()
            if r == "ack":
                return
            if r == "can":
                raise XModemError("Receiver cancelled")
            # NAK → retry
        raise XModemError("EOT not acknowledged")

    def _wait_ack(self) -> str:
        """Return 'ack' / 'nak' / 'can' / 'timeout'."""
        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            if self.cancel_requested:
                return "can"
            b = self._io.read_byte(0.05)
            if not b:
                continue
            v = b[0]
            if v == ACK:
                return "ack"
            if v == NAK:
                return "nak"
            if v == CAN:
                return "can"
        return "timeout"


# ---------------------------------------------------------------------------
# YMODEM — XMODEM-1K with a filename block first
# ---------------------------------------------------------------------------
class YModemSender(XModemSender):
    def __init__(self, io_: ByteIo, timeout: float = 3.0, retries: int = 10):
        super().__init__(io_, block_size=1024, timeout=timeout, retries=retries)

    def send_file(self, path: str, name: Optional[str] = None) -> None:
        if name is None:
            name = os.path.basename(path)

        size = os.path.getsize(path)
        with open(path, "rb") as f:
            data = f.read()

        # 1. wait for receiver
        self._wait_for_receiver()

        # 2. send block 0: "<name>\0<size> <mtime>\0" padded
        header = f"{name}\0{size} {int(time.time())}\0".encode("utf-8")
        self._send_block(0, header)

        # wait for 'C' again to start data blocks
        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            if self.cancel_requested:
                raise XModemError("Cancelled")
            b = self._io.read_byte(0.1)
            if not b:
                continue
            if b[0] == C:
                break
            if b[0] == ACK:
                continue

        # 3. send file data in 1K blocks
        total = len(data)
        sent = 0
        block_no = 1
        pos = 0

        while pos < total:
            if self.cancel_requested:
                raise XModemError("Cancelled")
            chunk = data[pos:pos + self._block_size]
            self._send_block(block_no, chunk)
            pos += len(chunk)
            sent = pos
            if self.progress_cb:
                self.progress_cb(sent, total)
            block_no = (block_no + 1) & 0xFF

        # 4. EOT
        self._send_eot()

        # 5. YMODEM: final empty block 0 to close the batch
        try:
            self._send_block(0, b"")
        except XModemError:
            pass


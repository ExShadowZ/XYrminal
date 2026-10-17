"""
Data formatting for the terminal view.

Every function accepts raw bytes and returns a printable string.
The mode is selected via `FormatMode` enum. Adding new modes is a matter
of adding a member and extending the dispatch table.
"""

from enum import Enum


class FormatMode(str, Enum):
    # --- raw (byte-based) ---
    HEX = "HEX"
    DEC = "DEC"
    OCT = "OCT"
    BIN = "BIN"

    # --- text (encoding-based) ---
    ASCII   = "ASCII"
    UTF8    = "UTF-8"
    UTF16LE = "UTF-16 LE"
    UTF16BE = "UTF-16 BE"

    CP1251 = "CP1251"       # Cyrillic (Windows)
    CP1252 = "CP1252"       # Western European (Windows)
    CP866  = "CP866"        # Cyrillic (DOS)
    KOI8R  = "KOI8-R"       # Cyrillic (KOI8-R)
    LATIN1 = "Latin-1"      # ISO-8859-1
    SHIFTJIS = "Shift-JIS"  # Japanese
    GB2312 = "GB2312"       # Simplified Chinese
    GBK    = "GBK"          # Simplified Chinese (extended)


# Human-readable groups
RAW_MODES = (FormatMode.HEX, FormatMode.DEC, FormatMode.OCT, FormatMode.BIN)

TEXT_MODES = (
    FormatMode.ASCII,
    FormatMode.UTF8,
    FormatMode.UTF16LE,
    FormatMode.UTF16BE,
    FormatMode.CP1251,
    FormatMode.CP1252,
    FormatMode.CP866,
    FormatMode.KOI8R,
    FormatMode.LATIN1,
    FormatMode.SHIFTJIS,
    FormatMode.GB2312,
    FormatMode.GBK,
)


# Python codec names for each text mode
_CODEC = {
    FormatMode.ASCII:   "ascii",
    FormatMode.UTF8:    "utf-8",
    FormatMode.UTF16LE: "utf-16-le",
    FormatMode.UTF16BE: "utf-16-be",
    FormatMode.CP1251:  "cp1251",
    FormatMode.CP1252:  "cp1252",
    FormatMode.CP866:   "cp866",
    FormatMode.KOI8R:   "koi8-r",
    FormatMode.LATIN1:  "latin-1",
    FormatMode.SHIFTJIS: "shift-jis",
    FormatMode.GB2312:  "gb2312",
    FormatMode.GBK:     "gbk",
}


def _format_raw(data: bytes, mode: FormatMode) -> str:
    if mode is FormatMode.HEX:
        return " ".join(f"{b:02X}" for b in data)
    if mode is FormatMode.DEC:
        return " ".join(f"{b:3d}" for b in data)
    if mode is FormatMode.OCT:
        return " ".join(f"{b:03o}" for b in data)
    if mode is FormatMode.BIN:
        return " ".join(f"{b:08b}" for b in data)
    raise ValueError(f"Not a raw mode: {mode}")


def _format_text(data: bytes, mode: FormatMode) -> str:
    encoding = _CODEC.get(mode, "utf-8")
    try:
        return data.decode(encoding, errors="replace")
    except Exception:
        return data.decode("ascii", errors="replace")


def format_bytes(data: bytes, mode: FormatMode) -> str:
    """
    Format a chunk of bytes into a printable string.

    Raw modes (HEX/DEC/OCT/BIN) join bytes with spaces.
    Text modes decode with the appropriate codec, replacing bad bytes.
    """
    if not data:
        return ""

    if mode in RAW_MODES:
        return _format_raw(data, mode)
    return _format_text(data, mode)


def format_preview(data: bytes) -> str:
    """
    Human-readable one-line preview for the [Transmit:] line.

    Rules:
        * If every byte is printable ASCII (0x20..0x7E) or TAB/CR/LF —
          decode as ASCII, strip trailing CR/LF.
        * Otherwise — space-separated uppercase HEX ("45 AA 79 B1").
    """
    if not data:
        return ""

    trimmed = data.rstrip(b"\r\n")

    printable = all(
        0x20 <= b <= 0x7E or b in (0x09, 0x0A, 0x0D)
        for b in trimmed
    )

    if printable:
        return trimmed.decode("ascii", errors="replace")

    return " ".join(f"{b:02X}" for b in trimmed)


def is_raw_mode(mode: FormatMode) -> bool:
    return mode in RAW_MODES


def is_text_mode(mode: FormatMode) -> bool:
    return mode in TEXT_MODES
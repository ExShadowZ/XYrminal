"""
Encoders for scenario script payloads.

    encode_payload(text, mode) -> bytes

Mode is a string identifier; case-insensitive. Supported:

    Raw / byte-based:
        "HEX"  — "AA 55 01 FF"
        "BIN"  — "10101010 01010101"
        "DEC"  — "170 85 1 255"
        "OCT"  — "252 125 001 377"

    Text / codec-based:
        "ASCII", "UTF-8", "UTF8",
        "UTF-16LE", "UTF-16BE",
        "CP1251", "CP1252", "CP866",
        "KOI8-R", "KOI8R",
        "LATIN-1", "LATIN1",
        "SHIFT-JIS", "SHIFTJIS", "SJIS",
        "GB2312", "GBK"

    "TEXT" (or "" / None) — UTF-8 by default.

Parsing raw modes raises ValueError on malformed input.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Raw modes
# ---------------------------------------------------------------------------
def _parse_hex(text: str) -> bytes:
    cleaned = (
        text.replace(" ", "")
            .replace(",", "")
            .replace("-", "")
            .replace("_", "")
            .replace("\t", "")
            .replace("\n", "")
    )
    if not cleaned:
        return b""
    if len(cleaned) % 2 != 0:
        raise ValueError(f"HEX: odd number of nibbles: {text!r}")
    try:
        return bytes.fromhex(cleaned)
    except ValueError as exc:
        raise ValueError(f"HEX: invalid digits in {text!r}") from exc


def _parse_bin(text: str) -> bytes:
    tokens = text.replace(",", " ").replace("\t", " ").split()
    if not tokens:
        return b""
    out = bytearray()
    for tok in tokens:
        if len(tok) > 8:
            raise ValueError(f"BIN: chunk too long: {tok!r}")
        if any(ch not in "01" for ch in tok):
            raise ValueError(f"BIN: not a binary string: {tok!r}")
        out.append(int(tok, 2))
    return bytes(out)


def _parse_dec(text: str) -> bytes:
    tokens = text.replace(",", " ").replace("\t", " ").split()
    if not tokens:
        return b""
    out = bytearray()
    for tok in tokens:
        try:
            v = int(tok, 10)
        except ValueError:
            raise ValueError(f"DEC: not an integer: {tok!r}")
        if not 0 <= v <= 255:
            raise ValueError(f"DEC: out of byte range: {tok!r}")
        out.append(v)
    return bytes(out)


def _parse_oct(text: str) -> bytes:
    tokens = text.replace(",", " ").replace("\t", " ").split()
    if not tokens:
        return b""
    out = bytearray()
    for tok in tokens:
        try:
            v = int(tok, 8)
        except ValueError:
            raise ValueError(f"OCT: not an octal number: {tok!r}")
        if not 0 <= v <= 255:
            raise ValueError(f"OCT: out of byte range: {tok!r}")
        out.append(v)
    return bytes(out)


# ---------------------------------------------------------------------------
# Codec aliases
# ---------------------------------------------------------------------------
_CODEC_ALIASES = {
    "ASCII":        "ascii",
    "UTF-8":        "utf-8",
    "UTF8":         "utf-8",
    "UTF-16LE":     "utf-16-le",
    "UTF16LE":      "utf-16-le",
    "UTF-16BE":     "utf-16-be",
    "UTF16BE":      "utf-16-be",
    "CP1251":       "cp1251",
    "WINDOWS-1251": "cp1251",
    "CP1252":       "cp1252",
    "WINDOWS-1252": "cp1252",
    "CP866":        "cp866",
    "IBM866":       "cp866",
    "KOI8-R":       "koi8-r",
    "KOI8R":        "koi8-r",
    "LATIN-1":      "latin-1",
    "LATIN1":       "latin-1",
    "ISO-8859-1":   "latin-1",
    "SHIFT-JIS":    "shift-jis",
    "SHIFTJIS":     "shift-jis",
    "SJIS":         "shift-jis",
    "GB2312":       "gb2312",
    "GBK":          "gbk",
    "TEXT":         "utf-8",
}


def _encode_text(text: str, codec_name: str) -> bytes:
    try:
        return text.encode(codec_name, errors="replace")
    except LookupError as exc:
        raise ValueError(f"Unknown encoding: {codec_name}") from exc


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------
RAW_MODES = {"HEX", "BIN", "DEC", "OCT"}


def encode_payload(text: str, mode: str | None = None) -> bytes:
    """
    Encode a scenario payload.

    mode may be None / "" → treated as "UTF-8".
    """
    if mode is None:
        mode = "UTF-8"
    m = mode.strip().upper()
    if not m:
        m = "UTF-8"

    if m in RAW_MODES:
        if m == "HEX":
            return _parse_hex(text)
        if m == "BIN":
            return _parse_bin(text)
        if m == "DEC":
            return _parse_dec(text)
        if m == "OCT":
            return _parse_oct(text)

    codec = _CODEC_ALIASES.get(m)
    if codec is None:
        raise ValueError(f"Unknown send mode: {mode!r}")
    return _encode_text(text, codec)


def is_valid_mode(mode: str | None) -> bool:
    if mode is None:
        return True
    m = mode.strip().upper()
    if not m:
        return True
    return m in RAW_MODES or m in _CODEC_ALIASES


def known_modes() -> list[str]:
    return sorted(RAW_MODES) + sorted(
        {k for k in _CODEC_ALIASES.keys() if k != "TEXT"}
    )
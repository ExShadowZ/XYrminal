"""
Buffered logger for the terminal view.

Two output formats are supported:

    .xyrm  — plain UTF-8 text, one terminal line per file line.
    .xyrmc — full HTML document with inline color spans.

Auto-save mode:
    When enabled via start_auto_save(path, format), every new line is
    ALSO written immediately to the given file (opened once and kept
    open). The in-memory buffer keeps growing as before — calling
    save() / save_as() still works normally. On stop_auto_save() the
    auto file is flushed and closed.
"""

from __future__ import annotations

import html as _html
import os
from datetime import datetime
from pathlib import Path
from typing import IO, Iterable, Optional


DEFAULT_DIR = "logs"

FORMAT_PLAIN = "xyrm"
FORMAT_RICH  = "xyrmc"


class LogWriter:
    def __init__(self, directory: str | os.PathLike = DEFAULT_DIR,
                 suffix: str = "") -> None:
        self._dir = Path(directory)
        self._suffix = f"_{suffix}" if suffix else ""
        self._buffer: list[tuple[str, str]] = []   # (plain, html)
        self._format: str = FORMAT_PLAIN

        # --- auto-save state ---
        self._auto_fp: Optional[IO[str]] = None
        self._auto_path: Optional[Path] = None
        self._auto_rich: bool = False
        self._auto_header_written: bool = False
        self._auto_lines_total: int = 0

    # -- public API --------------------------------------------------------
    def add_line(self, plain: str, html: Optional[str] = None) -> None:
        if html is None:
            html = _html.escape(plain)
        self._buffer.append((plain, html))
        # auto-save hook
        if self._auto_fp is not None:
            self._auto_write(plain, html)

    def add_lines(self, lines: Iterable[str]) -> None:
        for line in lines:
            self.add_line(line)

    def clear(self) -> None:
        self._buffer.clear()

    def has_data(self) -> bool:
        return bool(self._buffer)

    @property
    def directory(self) -> Path:
        return self._dir

    @property
    def format(self) -> str:
        return self._format

    def set_format(self, fmt: str) -> None:
        if fmt in (FORMAT_PLAIN, FORMAT_RICH):
            self._format = fmt

    def extension(self) -> str:
        return ".xyrmc" if self._format == FORMAT_RICH else ".xyrm"

    def default_stem(self) -> str:
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return f"{stamp}{self._suffix}"

    # --- auto-save --------------------------------------------------------
    def start_auto_save(self, path: str | os.PathLike | None = None) -> Path:
        """
        Enable auto-save. If `path` is None, generate a default path
        in the logs folder.

        Returns the actual path.
        """
        self.stop_auto_save()

        if path is None:
            self._dir.mkdir(parents=True, exist_ok=True)
            stem = self.default_stem()
            ext = self.extension()
            p = self._dir / f"{stem}{ext}"
            counter = 1
            while p.exists():
                p = self._dir / f"{stem}_{counter}{ext}"
                counter += 1
        else:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)

        suffix = p.suffix.lower()
        if suffix == ".xyrmc":
            self._auto_rich = True
        elif suffix == ".xyrm":
            self._auto_rich = False
        else:
            self._auto_rich = (self._format == FORMAT_RICH)
            p = p.with_suffix(self.extension())

        try:
            self._auto_fp = p.open("w", encoding="utf-8", newline="\n")
        except Exception:
            self._auto_fp = None
            return p

        self._auto_path = p
        self._auto_header_written = False
        self._auto_lines_total = 0

        # write header once for HTML
        if self._auto_rich:
            self._auto_write_html_header()

        # dump everything that was already in the buffer (so the user
        # doesn't lose history by toggling auto-save mid-session)
        for plain, frag in self._buffer:
            self._auto_write(plain, frag)

        return p

    def stop_auto_save(self) -> Optional[Path]:
        if self._auto_fp is None:
            return None
        try:
            if self._auto_rich:
                self._auto_write_html_footer()
            self._auto_fp.flush()
            self._auto_fp.close()
        except Exception:
            pass
        p = self._auto_path
        self._auto_fp = None
        self._auto_path = None
        self._auto_header_written = False
        return p

    def auto_save_path(self) -> Optional[Path]:
        return self._auto_path

    def is_auto_save_on(self) -> bool:
        return self._auto_fp is not None

    # -- file writes -------------------------------------------------------
    def save(self) -> Path:
        self._dir.mkdir(parents=True, exist_ok=True)
        stem = self.default_stem()
        ext = self.extension()
        path = self._dir / f"{stem}{ext}"

        counter = 1
        while path.exists():
            path = self._dir / f"{stem}_{counter}{ext}"
            counter += 1

        self._write(path)
        return path

    def save_as(self, path: str | os.PathLike) -> Path:
        path = Path(path)
        suffix = path.suffix.lower()

        if suffix == ".xyrmc":
            use_rich = True
        elif suffix == ".xyrm":
            use_rich = False
        else:
            use_rich = (self._format == FORMAT_RICH)
            path = path.with_suffix(self.extension())

        path.parent.mkdir(parents=True, exist_ok=True)
        self._write(path, force_rich=use_rich)
        return path

    # -- static readers ----------------------------------------------------
    @staticmethod
    def read_html_log(path: str | os.PathLike) -> str:
        p = Path(path)
        try:
            with p.open("r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    @staticmethod
    def read_plain_log(path: str | os.PathLike) -> str:
        p = Path(path)
        try:
            with p.open("r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    @staticmethod
    def detect_format(path: str | os.PathLike) -> str:
        suffix = Path(path).suffix.lower()
        if suffix in (".xyrmc", ".html", ".htm"):
            return FORMAT_RICH
        return FORMAT_PLAIN

    # -- internal ----------------------------------------------------------
    def _auto_write(self, plain: str, html_frag: str) -> None:
        if self._auto_fp is None:
            return
        try:
            if self._auto_rich:
                self._auto_fp.write(html_frag)
                self._auto_fp.write("\n")
            else:
                self._auto_fp.write(plain)
                self._auto_fp.write("\n")
            self._auto_lines_total += 1
            # flush every 20 lines — avoids losing data on crash
            if self._auto_lines_total % 20 == 0:
                self._auto_fp.flush()
        except Exception:
            pass

    def _auto_write_html_header(self) -> None:
        if self._auto_fp is None or self._auto_header_written:
            return
        try:
            from core.theme import COLORS
            bg = COLORS.get("bg_root", "#1e1b2e")
            fg = COLORS.get("text", "#e6e1f5")
        except Exception:
            bg = "#1e1b2e"
            fg = "#e6e1f5"

        self._auto_fp.write("<!DOCTYPE html>\n")
        self._auto_fp.write("<html lang='en'>\n<head>\n")
        self._auto_fp.write("<meta charset='utf-8'>\n")
        self._auto_fp.write("<title>XYrminal log</title>\n")
        self._auto_fp.write("<style>\n")
        self._auto_fp.write(
            f"  body {{ background: {bg}; color: {fg}; "
            f"font-family: Consolas, Menlo, 'DejaVu Sans Mono', monospace; "
            f"font-size: 12px; margin: 12px; }}\n"
        )
        self._auto_fp.write(
            "  pre { margin: 0; white-space: pre-wrap; "
            "word-break: break-all; }\n"
        )
        self._auto_fp.write("</style>\n</head>\n<body>\n<pre>\n")
        self._auto_header_written = True

    def _auto_write_html_footer(self) -> None:
        if self._auto_fp is None or not self._auto_header_written:
            return
        try:
            self._auto_fp.write("</pre>\n</body>\n</html>\n")
        except Exception:
            pass

    def _write(self, path: Path, force_rich: Optional[bool] = None) -> None:
        if force_rich is None:
            force_rich = (self._format == FORMAT_RICH)
        if force_rich:
            self._write_html(path)
        else:
            self._write_plain(path)

    def _write_plain(self, path: Path) -> None:
        with path.open("w", encoding="utf-8", newline="\n") as f:
            for plain, _html_frag in self._buffer:
                f.write(plain)
                f.write("\n")

    def _write_html(self, path: Path) -> None:
        try:
            from core.theme import COLORS
            bg = COLORS.get("bg_root", "#1e1b2e")
            fg = COLORS.get("text", "#e6e1f5")
        except Exception:
            bg = "#1e1b2e"
            fg = "#e6e1f5"

        with path.open("w", encoding="utf-8", newline="\n") as f:
            f.write("<!DOCTYPE html>\n")
            f.write("<html lang='en'>\n<head>\n")
            f.write("<meta charset='utf-8'>\n")
            f.write("<title>XYrminal log</title>\n")
            f.write("<style>\n")
            f.write(
                f"  body {{ background: {bg}; color: {fg}; "
                f"font-family: Consolas, Menlo, 'DejaVu Sans Mono', monospace; "
                f"font-size: 12px; margin: 12px; }}\n"
            )
            f.write(
                "  pre { margin: 0; white-space: pre-wrap; "
                "word-break: break-all; }\n"
            )
            f.write("</style>\n</head>\n<body>\n<pre>\n")

            for _plain, html_frag in self._buffer:
                f.write(html_frag)
                f.write("\n")

            f.write("</pre>\n</body>\n</html>\n")
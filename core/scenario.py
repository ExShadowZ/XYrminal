"""
Scenario interpreter for XYrminal.

The .xyscen file is parsed and compiled to bytecode once, then
executed step by step. Pausing operations (wait / expect) are handled
by QTimers, so the event loop stays responsive.

External API (unchanged from stage 0/1):

    class ScenarioExecutor(QObject):
        send_requested = pyqtSignal(bytes)
        line           = pyqtSignal(str)
        finished       = pyqtSignal(bool, str)
        busy_changed   = pyqtSignal(bool)

        start(path)
        stop()
        is_busy()
        push_rx(chunk)

Language reference — see scenario_compiler.py docstring.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from core.scenario_encoding import encode_payload
from core.scenario_compiler import (
    ScenarioParseError, _lex, _Parser, _Compiler,
)


# Regex for pulling a number out of arbitrary text. Used by num_from_rx.
_NUMBER_RE = re.compile(r"[-+]?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?")


class ScenarioRuntimeError(Exception):
    pass


class ScenarioExecutor(QObject):
    send_requested = pyqtSignal(bytes)
    line           = pyqtSignal(str)
    finished       = pyqtSignal(bool, str)
    busy_changed   = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._code: list[tuple] = []
        self._pc: int = 0
        self._mode: str = "idle"   # idle | running | waiting | expecting
        self._variables: dict[str, object] = {}
        self._stack: list[object] = []

        # RX buffer (whole session) + offset for `expect`
        self._rx_full: str = ""
        self._rx_offset: int = 0

        # current expect context
        self._expect_needle: str = ""
        self._expect_search_mode: bool = False

        # send_slow state
        self._slow_data: bytes = b""
        self._slow_index: int = 0
        self._slow_step_ms: int = 0

        # timers
        self._wait_timer = QTimer(self)
        self._wait_timer.setSingleShot(True)
        self._wait_timer.timeout.connect(self._on_wait_done)

        self._slow_timer = QTimer(self)
        self._slow_timer.setSingleShot(True)
        self._slow_timer.timeout.connect(self._on_slow_tick)

        self._expect_timer = QTimer(self)
        self._expect_timer.setSingleShot(True)
        self._expect_timer.timeout.connect(self._on_expect_timeout)

        # time of start
        self._t0: float = 0.0

    # =================================================================
    # Public API
    # =================================================================
    def start(self, path: str | Path) -> None:
        if self._mode != "idle":
            return

        try:
            text = Path(path).read_text(encoding="utf-8")
        except Exception as exc:
            self.line.emit(f"[SCENARIO] cannot read file: {exc}")
            self.finished.emit(False, str(exc))
            return

        try:
            tokens = _lex(text)
            parser = _Parser(tokens)
            body = parser.parse_program()
            compiler = _Compiler()
            code = compiler.compile_program(body)
        except ScenarioParseError as exc:
            self.line.emit(f"[SCENARIO] parse error: {exc}")
            self.finished.emit(False, str(exc))
            return

        if not code or len(code) <= 1:
            self.line.emit("[SCENARIO] empty script")
            self.finished.emit(False, "empty script")
            return

        self._code = code
        self._pc = 0
        self._variables.clear()
        self._stack.clear()
        self._rx_full = ""
        self._rx_offset = 0
        self._slow_data = b""
        self._slow_index = 0
        self._t0 = time.monotonic()

        self._mode = "running"
        self.busy_changed.emit(True)
        self.line.emit(
            f"[SCENARIO] start: {Path(path).name} ({len(code)-1} instr)"
        )
        QTimer.singleShot(0, self._run)

    def stop(self) -> None:
        if self._mode == "idle":
            return
        self._wait_timer.stop()
        self._slow_timer.stop()
        self._expect_timer.stop()
        self._mode = "idle"
        self._slow_data = b""
        self._slow_index = 0
        self.busy_changed.emit(False)
        self.line.emit("[SCENARIO] stopped")
        self.finished.emit(False, "stopped")

    def is_busy(self) -> bool:
        return self._mode != "idle"

    def push_rx(self, chunk: bytes) -> None:
        if self._mode == "idle":
            return
        try:
            text = chunk.decode("utf-8", errors="replace")
        except Exception:
            text = chunk.decode("latin-1", errors="replace")
        self._rx_full += text

        if self._mode == "expecting":
            self._check_expect_on_rx()

    # =================================================================
    # Execution engine
    # =================================================================
    def _run(self) -> None:
        """
        Run instructions until we hit a blocking op (wait / send_slow /
        expect) or the program ends.
        """
        if self._mode != "running":
            return

        while True:
            if self._pc < 0 or self._pc >= len(self._code):
                self._finish_ok()
                return

            instr = self._code[self._pc]
            op = instr[0]

            try:
                if not self._exec(instr):
                    # blocking op started a timer/expect
                    return
            except ScenarioRuntimeError as exc:
                self._finish_fail(str(exc))
                return
            except Exception as exc:
                self._finish_fail(f"{type(exc).__name__}: {exc}")
                return

    def _exec(self, instr: tuple) -> bool:
        """
        Execute a single instruction. Returns True to continue with the
        next one, False if execution must pause (waiting / expecting).
        """
        op = instr[0]
        line = instr[-1]

        # ---------- stack ops ----------
        if op == "PUSH_CONST":
            self._stack.append(instr[1])
            self._pc += 1
            return True

        if op == "POP":
            if self._stack:
                self._stack.pop()
            self._pc += 1
            return True

        # ---------- vars ----------
        if op == "LOAD_VAR":
            name = instr[1]
            if name not in self._variables:
                raise ScenarioRuntimeError(
                    f"Line {line}: undefined variable {name!r}"
                )
            self._stack.append(self._variables[name])
            self._pc += 1
            return True

        if op == "LOAD_VAR_OR":
            name = instr[1]
            self._stack.append(self._variables.get(name, 0))
            self._pc += 1
            return True

        if op == "STORE_VAR":
            name = instr[1]
            val = self._stack.pop() if self._stack else None
            self._variables[name] = val
            self._pc += 1
            return True

        # ---------- unary / binary ----------
        if op == "UNARY":
            self._pc += 1
            if not self._stack:
                raise ScenarioRuntimeError(f"Line {line}: stack underflow")
            v = self._stack.pop()
            o = instr[1]
            if o == "!":
                self._stack.append(not _truthy(v))
            elif o == "-":
                self._stack.append(-_to_num(v))
            elif o == "+":
                self._stack.append(_to_num(v))
            else:
                raise ScenarioRuntimeError(f"Line {line}: unknown unary {o!r}")
            return True

        if op == "BINARY":
            o = instr[1]
            if len(self._stack) < 2:
                raise ScenarioRuntimeError(f"Line {line}: stack underflow")
            b = self._stack.pop()
            a = self._stack.pop()
            self._stack.append(_binary_op(o, a, b, line))
            self._pc += 1
            return True

        # ---------- jumps ----------
        if op == "JUMP":
            self._pc = instr[1]
            return True

        if op == "JUMP_IF_FALSE":
            v = self._stack.pop() if self._stack else None
            if not _truthy(v):
                self._pc = instr[1]
            else:
                self._pc += 1
            return True

        if op == "JUMP_IF_TRUE":
            v = self._stack.pop() if self._stack else None
            if _truthy(v):
                self._pc = instr[1]
            else:
                self._pc += 1
            return True

        # ---------- function call ----------
        if op == "CALL_FUNC":
            name = instr[1]
            nargs = instr[2]
            args = []
            for _ in range(nargs):
                if not self._stack:
                    raise ScenarioRuntimeError(
                        f"Line {line}: stack underflow in {name}()"
                    )
                args.insert(0, self._stack.pop())

            if name in ("expect", "expect_search"):
                if not self._start_expect_expr(name, args, line):
                    return False   # paused
                return True

            result = _call_builtin(name, args, line, self)
            self._stack.append(result)
            self._pc += 1
            return True

        # ---------- procedure call ----------
        if op == "CALL_PROC":
            name = instr[1]
            enc = instr[2]
            nargs = instr[3]
            args = []
            for _ in range(nargs):
                if not self._stack:
                    raise ScenarioRuntimeError(
                        f"Line {line}: stack underflow in {name}"
                    )
                args.insert(0, self._stack.pop())

            if name == "send":
                self._do_send(args[0], enc, line)
                self._pc += 1
                return True

            if name == "send_slow":
                self._do_send_slow(args[0], args[1], enc, line)
                # send_slow pauses
                return False

            if name == "wait":
                ms = _to_num(args[0])
                if ms < 0:
                    ms = 0
                self._pc += 1
                self._mode = "waiting"
                self._wait_timer.start(max(1, int(ms)))
                return False

            if name == "log":
                text = _to_str(args[0])
                self.line.emit(f"[SCENARIO] {text}")
                self._pc += 1
                return True

            if name == "print":
                text = _to_str(args[0])
                self.line.emit(f"[SCENARIO] {text}")
                self._pc += 1
                return True

            if name == "assert_rx":
                needle = _to_str(args[0])
                if needle in self._rx_full:
                    self._pc += 1
                    return True
                raise ScenarioRuntimeError(
                    f"Line {line}: assert_rx failed: {needle!r}"
                )

            raise ScenarioRuntimeError(
                f"Line {line}: unknown procedure {name!r}"
            )

        # ---------- end ----------
        if op == "RET":
            self._finish_ok()
            return False

        raise ScenarioRuntimeError(f"Line {line}: unknown opcode {op!r}")

    # =================================================================
    # send / send_slow
    # =================================================================
    def _do_send(self, payload, enc: str, line: int) -> None:
        text = _to_str(payload)
        try:
            data = encode_payload(text, enc or None)
        except ValueError as exc:
            raise ScenarioRuntimeError(f"Line {line}: {exc}")
        self.send_requested.emit(data)

    def _do_send_slow(self, payload, delay, enc: str, line: int) -> None:
        text = _to_str(payload)
        try:
            data = encode_payload(text, enc or None)
        except ValueError as exc:
            raise ScenarioRuntimeError(f"Line {line}: {exc}")
        ms = int(_to_num(delay))
        if ms < 0:
            ms = 0
        self._slow_data = data
        self._slow_index = 0
        self._slow_step_ms = ms
        if not data:
            self._pc += 1
            return
        self._mode = "waiting"
        self._on_slow_tick()

    def _on_slow_tick(self) -> None:
        if self._mode != "waiting":
            return
        if self._slow_index >= len(self._slow_data):
            self._mode = "running"
            self._pc += 1
            self._run()
            return

        b = self._slow_data[self._slow_index:self._slow_index + 1]
        self.send_requested.emit(b)
        self._slow_index += 1

        if self._slow_index >= len(self._slow_data):
            self._mode = "running"
            self._pc += 1
            QTimer.singleShot(max(1, self._slow_step_ms), self._run)
            return

        self._slow_timer.start(max(1, self._slow_step_ms))

    # =================================================================
    # wait
    # =================================================================
    def _on_wait_done(self) -> None:
        if self._mode != "waiting":
            return
        self._mode = "running"
        self._run()

    # =================================================================
    # expect / expect_search
    # =================================================================
    def _start_expect_expr(self, name: str, args: list, line: int) -> bool:
        """
        Start waiting for a needle.

        Returns True if the match is already satisfied (result pushed,
        pc advanced), False if we must pause (expecting mode).
        """
        if not args:
            raise ScenarioRuntimeError(
                f"Line {line}: {name} requires a needle argument"
            )
        needle = _to_str(args[0])
        ms = int(_to_num(args[1])) if len(args) >= 2 else 5000
        if ms <= 0:
            ms = 1

        self._expect_needle = needle
        self._expect_search_mode = (name == "expect_search")
        self._expect_timer.stop()

        # immediate check
        if self._expect_search_mode:
            found = needle in self._rx_full
        else:
            found = needle in self._rx_full[self._rx_offset:]

        if found:
            self._on_expect_success(push_result=True)
            return True

        self._mode = "expecting"
        self._expect_timer.start(ms)
        return False

    def _check_expect_on_rx(self) -> None:
        if not self._expect_needle:
            return
        if self._expect_search_mode:
            found = self._expect_needle in self._rx_full
        else:
            found = self._expect_needle in self._rx_full[self._rx_offset:]
        if found:
            self._expect_timer.stop()
            self._on_expect_success(push_result=True)

    def _on_expect_success(self, push_result: bool) -> None:
        self.line.emit(f"[SCENARIO] expect OK: {self._expect_needle!r}")
        if not self._expect_search_mode:
            idx = self._rx_full.find(self._expect_needle, self._rx_offset)
            if idx >= 0:
                self._rx_offset = idx + len(self._expect_needle)

        if push_result:
            self._stack.append(True)

        self._mode = "running"
        self._pc += 1
        QTimer.singleShot(0, self._run)

    def _on_expect_timeout(self) -> None:
        if self._mode != "expecting":
            return
        self.line.emit(
            f"[SCENARIO] expect TIMEOUT: {self._expect_needle!r}"
        )
        # push False — because CALL_FUNC must always leave a value
        self._stack.append(False)
        self._mode = "running"
        self._pc += 1
        QTimer.singleShot(0, self._run)

    # =================================================================
    # Finish
    # =================================================================
    def _finish_ok(self) -> None:
        self._mode = "idle"
        self.busy_changed.emit(False)
        self.line.emit("[SCENARIO] finished OK")
        self.finished.emit(True, "")

    def _finish_fail(self, err: str) -> None:
        self._wait_timer.stop()
        self._slow_timer.stop()
        self._expect_timer.stop()
        self._mode = "idle"
        self._slow_data = b""
        self._slow_index = 0
        self.busy_changed.emit(False)
        self.line.emit(f"[SCENARIO] FAILED: {err}")
        self.finished.emit(False, err)


# =====================================================================
# Value helpers
# =====================================================================
def _truthy(v) -> bool:
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        return len(v) > 0
    return True


def _to_num(v) -> int:
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str):
        s = v.strip()
        try:
            return int(s, 10)
        except ValueError:
            try:
                return int(float(s))
            except ValueError:
                return 0
    if v is None:
        return 0
    return 0


def _to_str(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def _binary_op(op: str, a, b, line: int):
    # string concatenation for '+'
    if op == "+":
        if isinstance(a, str) or isinstance(b, str):
            return _to_str(a) + _to_str(b)
        return _to_num(a) + _to_num(b)

    if op == "-": return _to_num(a) - _to_num(b)
    if op == "*": return _to_num(a) * _to_num(b)
    if op == "/":
        d = _to_num(b)
        if d == 0:
            raise ScenarioRuntimeError(f"Line {line}: division by zero")
        return _to_num(a) // d
    if op == "%":
        d = _to_num(b)
        if d == 0:
            raise ScenarioRuntimeError(f"Line {line}: modulo by zero")
        return _to_num(a) % d

    if op == "==": return _eq(a, b)
    if op == "!=": return not _eq(a, b)
    if op == "<":  return _to_num(a) <  _to_num(b)
    if op == ">":  return _to_num(a) >  _to_num(b)
    if op == "<=": return _to_num(a) <= _to_num(b)
    if op == ">=": return _to_num(a) >= _to_num(b)

    raise ScenarioRuntimeError(f"Line {line}: unknown binary op {op!r}")


def _eq(a, b) -> bool:
    # numeric equality if both are numeric-ish
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) == bool(b)
    if isinstance(a, (int, float)) or isinstance(b, (int, float)):
        return _to_num(a) == _to_num(b)
    if isinstance(a, str) or isinstance(b, str):
        # if both look numeric, compare as numbers
        if isinstance(a, str) and isinstance(b, str):
            try:
                return int(a) == int(b)
            except ValueError:
                pass
        return _to_str(a) == _to_str(b)
    return a == b


def _num_from_rx(buf: str, marker: str) -> int:
    """
    Return the first number found in `buf`.

    * If `marker` is non-empty, only text AFTER the marker is considered.
      If the marker is not found — return 0.
    * If no number is found — return 0.
    * Result is truncated to int (the language has no float).
    """
    if marker:
        idx = buf.find(marker)
        if idx < 0:
            return 0
        tail = buf[idx + len(marker):]
        # skip common separators after a marker like "TEMP= 23"
        tail = tail.lstrip(" \t:=,")
    else:
        tail = buf

    m = _NUMBER_RE.search(tail)
    if not m:
        return 0

    raw = m.group(0).replace(",", ".")
    try:
        return int(float(raw))
    except ValueError:
        return 0


# =====================================================================
# Built-in functions
# =====================================================================
def _call_builtin(name: str, args: list, line: int, executor: "ScenarioExecutor"):
    if name == "len":
        if not args:
            raise ScenarioRuntimeError(f"Line {line}: len() requires 1 arg")
        return len(_to_str(args[0]))
    if name == "num":
        if not args:
            raise ScenarioRuntimeError(f"Line {line}: num() requires 1 arg")
        return _to_num(args[0])
    if name == "str":
        if not args:
            raise ScenarioRuntimeError(f"Line {line}: str() requires 1 arg")
        return _to_str(args[0])
    if name == "abs":
        if not args:
            raise ScenarioRuntimeError(f"Line {line}: abs() requires 1 arg")
        return abs(_to_num(args[0]))
    if name == "time_ms":
        return int((time.monotonic() - executor._t0) * 1000)
    if name == "assert_rx":
        if not args:
            raise ScenarioRuntimeError(f"Line {line}: assert_rx() requires 1 arg")
        return _to_str(args[0]) in executor._rx_full
    if name == "num_from_rx":
        if not args:
            raise ScenarioRuntimeError(
                f"Line {line}: num_from_rx() requires a marker argument"
            )
        marker = _to_str(args[0])
        return _num_from_rx(executor._rx_full, marker)

    raise ScenarioRuntimeError(f"Line {line}: unknown function {name!r}")
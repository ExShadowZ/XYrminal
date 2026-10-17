"""
Scenario mini-language: lexer, parser, compiler.

Pipeline:
    .xyscen text
        → tokens
        → AST
        → bytecode (list of Instruction)

The bytecode is a flat list of instruction tuples. Jump targets are
absolute indices into the instruction list. This makes the interpreter
trivial: it just walks the PC and reacts to CALL/RET-like ops.

Instruction format (tuple):
    (opcode: str, arg1, arg2, ..., line_no: int)

Opcodes used by the interpreter (see scenario.py):

    PUSH_CONST      value             push value onto stack
    POP                                discard top of stack
    LOAD_VAR        name              push variable value
    STORE_VAR       name              pop value, store into variable
    LOAD_VAR_OR     name              like LOAD_VAR, but if undefined
                                        push 0 (used in arithmetic)
    UNARY           op                unary operator, e.g. "!"
    BINARY          op                binary operator
    JUMP            target            unconditional jump
    JUMP_IF_FALSE   target            pop; if falsy, jump
    JUMP_IF_TRUE    target            pop; if truthy, jump
    CALL_FUNC       name, nargs       call built-in, push result
    CALL_PROC       name, enc, nargs  call procedure (send / log / wait / etc.)
    RET                               end of program

Legacy compatibility:
    Stage-1 commands (send "..." / wait N / expect "..." N / etc.) are
    accepted as top-level "sentences", and are compiled to CALL_PROC
    instruction sequences. This keeps every old .xyscen working.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from core.scenario_encoding import encode_payload, is_valid_mode, known_modes


class ScenarioParseError(Exception):
    pass


# ===========================================================================
# Lexer
# ===========================================================================
@dataclass
class Token:
    kind: str        # 'num' | 'str' | 'ident' | 'kw' | 'op' | 'eof'
    value: Any
    line: int


_KEYWORDS = {
    "let", "if", "else", "while", "for", "break", "continue",
    "true", "false", "null",
    "send", "send_slow", "wait", "expect", "expect_search",
    "assert_rx", "log", "print",
}

# Keywords that are ALSO valid as function names inside expressions.
_CALLABLE_KEYWORDS = {"expect", "expect_search", "assert_rx"}

# Multi-char operators must be tried before single-char.
_OPS_MULTI = [
    "==", "!=", "<=", ">=", "&&", "||",
    "++", "--", "+=", "-=", "*=", "/=", "%=",
]
_OPS_SINGLE = set("+-*/%(){};,=<>!")


def _lex(text: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    line = 1
    n = len(text)

    while i < n:
        ch = text[i]

        # newline
        if ch == "\n":
            line += 1
            i += 1
            continue

        # whitespace
        if ch in " \t\r":
            i += 1
            continue

        # comment: # ... or // ...
        if ch == "#":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                if text[i] == "\n":
                    line += 1
                i += 1
            i += 2
            continue

        # string literal
        if ch in ('"', "'"):
            quote = ch
            i += 1
            buf: list[str] = []
            while i < n and text[i] != quote:
                if text[i] == "\\" and i + 1 < n:
                    esc = text[i + 1]
                    if esc == "n":    buf.append("\n"); i += 2
                    elif esc == "r":  buf.append("\r"); i += 2
                    elif esc == "t":  buf.append("\t"); i += 2
                    elif esc == "\\": buf.append("\\"); i += 2
                    elif esc == "\"": buf.append("\""); i += 2
                    elif esc == "'":  buf.append("'");  i += 2
                    elif esc == "0":  buf.append("\0"); i += 2
                    elif esc == "x" and i + 3 < n:
                        try:
                            buf.append(chr(int(text[i + 2:i + 4], 16)))
                            i += 4
                        except ValueError:
                            buf.append("\\x")
                            i += 2
                    else:
                        buf.append("\\")
                        i += 1
                else:
                    if text[i] == "\n":
                        line += 1
                    buf.append(text[i])
                    i += 1
            if i >= n:
                raise ScenarioParseError(f"Line {line}: unterminated string")
            i += 1  # closing quote
            tokens.append(Token("str", "".join(buf), line))
            continue

        # number (integer only)
        if ch.isdigit():
            j = i
            while j < n and text[j].isdigit():
                j += 1
            tokens.append(Token("num", int(text[i:j]), line))
            i = j
            continue

        # identifier / keyword
        if ch.isalpha() or ch == "_":
            j = i
            while j < n and (text[j].isalnum() or text[j] == "_"):
                j += 1
            word = text[i:j]
            if word in _KEYWORDS:
                tokens.append(Token("kw", word, line))
            else:
                tokens.append(Token("ident", word, line))
            i = j
            continue

        # '[' and ']' for send[ENC] — treat as their own tokens
        if ch in "[]":
            tokens.append(Token("op", ch, line))
            i += 1
            continue

        # multi-char operators
        matched = False
        for op in _OPS_MULTI:
            if text.startswith(op, i):
                tokens.append(Token("op", op, line))
                i += len(op)
                matched = True
                break
        if matched:
            continue

        # single-char operators
        if ch in _OPS_SINGLE:
            tokens.append(Token("op", ch, line))
            i += 1
            continue

        raise ScenarioParseError(f"Line {line}: unexpected character {ch!r}")

    tokens.append(Token("eof", None, line))
    return tokens


# ===========================================================================
# AST nodes
# ===========================================================================
@dataclass
class Node:
    line: int = 0


@dataclass
class NumLit(Node):
    value: int = 0


@dataclass
class StrLit(Node):
    value: str = ""


@dataclass
class BoolLit(Node):
    value: bool = False


@dataclass
class NullLit(Node):
    pass


@dataclass
class VarRef(Node):
    name: str = ""


@dataclass
class UnaryOp(Node):
    op: str = ""
    operand: Node = None


@dataclass
class BinaryOp(Node):
    op: str = ""
    left: Node = None
    right: Node = None


@dataclass
class CallExpr(Node):
    name: str = ""
    args: list = None


@dataclass
class Assign(Node):
    target: str = ""
    op: str = "="
    value: Node = None


@dataclass
class IncDec(Node):
    target: str = ""
    op: str = "++"
    postfix: bool = True


# Statements
@dataclass
class ProcCall(Node):
    """A statement-level call, e.g. send, log, wait, expect("...", 1000)."""
    name: str = ""
    args: list = None
    enc: Optional[str] = None


@dataclass
class LetStmt(Node):
    name: str = ""
    value: Node = None


@dataclass
class IfStmt(Node):
    cond: Node = None
    then_body: list = None
    else_body: list = None


@dataclass
class WhileStmt(Node):
    cond: Node = None
    body: list = None


@dataclass
class ForStmt(Node):
    init: Optional[Node] = None
    cond: Optional[Node] = None
    step: Optional[Node] = None
    body: list = None


@dataclass
class BreakStmt(Node):
    pass


@dataclass
class ContinueStmt(Node):
    pass


@dataclass
class Block(Node):
    body: list = None


# ===========================================================================
# Parser — recursive descent
# ===========================================================================
class _Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0
        self._no_semicolon = False

    # -- token helpers --------------------------------------------------
    def _peek(self, offset: int = 0) -> Token:
        idx = self.pos + offset
        if idx >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[idx]

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return tok

    def _check(self, kind: str, value: Any = None) -> bool:
        tok = self._peek()
        if tok.kind != kind:
            return False
        if value is not None and tok.value != value:
            return False
        return True

    def _match(self, kind: str, value: Any = None) -> Optional[Token]:
        if self._check(kind, value):
            return self._advance()
        return None

    def _expect(self, kind: str, value: Any = None, what: str = "") -> Token:
        tok = self._peek()
        if tok.kind != kind or (value is not None and tok.value != value):
            label = what or f"{kind} {value!r}"
            got = f"{tok.kind} {tok.value!r}"
            raise ScenarioParseError(
                f"Line {tok.line}: expected {label}, got {got}"
            )
        return self._advance()

    # -- program --------------------------------------------------------
    def parse_program(self) -> list:
        body: list = []
        while not self._check("eof"):
            stmt = self._parse_statement()
            if stmt is not None:
                body.append(stmt)
        return body

    def _parse_block(self) -> list:
        self._expect("op", "{", "'{'")
        body: list = []
        while not self._check("op", "}"):
            if self._check("eof"):
                raise ScenarioParseError("Unexpected end of file inside block")
            stmt = self._parse_statement()
            if stmt is not None:
                body.append(stmt)
        self._expect("op", "}", "'}'")
        return body

    # -- statements -----------------------------------------------------
    def _parse_statement(self):
        tok = self._peek()

        # block
        if tok.kind == "op" and tok.value == "{":
            line = tok.line
            body = self._parse_block()
            return Block(line=line, body=body)

        # keywords
        if tok.kind == "kw":
            if tok.value == "let":
                return self._parse_let()
            if tok.value == "if":
                return self._parse_if()
            if tok.value == "while":
                return self._parse_while()
            if tok.value == "for":
                return self._parse_for()
            if tok.value == "break":
                self._advance()
                self._eat_optional_semicolon()
                return BreakStmt(line=tok.line)
            if tok.value == "continue":
                self._advance()
                self._eat_optional_semicolon()
                return ContinueStmt(line=tok.line)
            if tok.value in ("send", "send_slow"):
                return self._parse_send(tok.value)
            if tok.value == "wait":
                return self._parse_wait()
            if tok.value in ("expect", "expect_search"):
                return self._parse_expect_call(tok.value)
            if tok.value == "assert_rx":
                return self._parse_assert_rx()
            if tok.value == "log":
                return self._parse_log()
            if tok.value == "print":
                return self._parse_print()

        # identifier: could be assignment or a bare expression
        if tok.kind == "ident":
            nxt = self._peek(1)
            if nxt.kind == "op" and nxt.value in ("=", "+=", "-=", "*=", "/=", "%="):
                return self._parse_assign()
            if nxt.kind == "op" and nxt.value in ("++", "--"):
                return self._parse_incdec()

            expr = self._parse_expression()
            self._eat_optional_semicolon()
            return expr

        raise ScenarioParseError(
            f"Line {tok.line}: unexpected token {tok.kind} {tok.value!r}"
        )

    def _eat_optional_semicolon(self):
        if self._no_semicolon:
            return
        self._match("op", ";")

    # -- let ------------------------------------------------------------
    def _parse_let(self):
        tok = self._expect("kw", "let")
        name_tok = self._expect("ident", what="variable name")
        self._expect("op", "=", "'='")
        value = self._parse_expression()
        self._eat_optional_semicolon()
        return LetStmt(line=tok.line, name=name_tok.value, value=value)

    # -- if / else if / else --------------------------------------------
    def _parse_if(self):
        tok = self._expect("kw", "if")
        self._expect("op", "(", "'('")
        cond = self._parse_expression()
        self._expect("op", ")", "')'")
        then_body = self._parse_block()

        else_body = None
        if self._check("kw", "else"):
            self._advance()
            if self._check("kw", "if"):
                else_body = [self._parse_if()]
            else:
                else_body = self._parse_block()

        return IfStmt(line=tok.line, cond=cond,
                      then_body=then_body, else_body=else_body)

    # -- while ----------------------------------------------------------
    def _parse_while(self):
        tok = self._expect("kw", "while")
        self._expect("op", "(", "'('")
        cond = self._parse_expression()
        self._expect("op", ")", "')'")
        body = self._parse_block()
        return WhileStmt(line=tok.line, cond=cond, body=body)

    # -- for ------------------------------------------------------------
    def _parse_for(self):
        tok = self._expect("kw", "for")
        self._expect("op", "(", "'('")

        init = None
        if not self._check("op", ";"):
            saved = self._no_semicolon
            self._no_semicolon = True
            try:
                if self._check("kw", "let"):
                    init = self._parse_let()
                elif self._check("ident"):
                    nxt = self._peek(1)
                    if nxt.kind == "op" and nxt.value in ("=", "+=", "-=", "*=", "/=", "%="):
                        init = self._parse_assign()
                    elif nxt.kind == "op" and nxt.value in ("++", "--"):
                        init = self._parse_incdec()
                    else:
                        raise ScenarioParseError(
                            f"Line {tok.line}: invalid for-init"
                        )
            finally:
                self._no_semicolon = saved
        self._expect("op", ";", "';'")

        cond = None
        if not self._check("op", ";"):
            cond = self._parse_expression()
        self._expect("op", ";", "';'")

        step = None
        if not self._check("op", ")"):
            saved = self._no_semicolon
            self._no_semicolon = True
            try:
                if self._check("ident"):
                    nxt = self._peek(1)
                    if nxt.kind == "op" and nxt.value in ("=", "+=", "-=", "*=", "/=", "%="):
                        step = self._parse_assign()
                    elif nxt.kind == "op" and nxt.value in ("++", "--"):
                        step = self._parse_incdec()
                    else:
                        raise ScenarioParseError(
                            f"Line {tok.line}: invalid for-step"
                        )
            finally:
                self._no_semicolon = saved
        self._expect("op", ")", "')'")

        body = self._parse_block()
        return ForStmt(line=tok.line, init=init, cond=cond, step=step, body=body)

    # -- assignment -----------------------------------------------------
    def _parse_assign(self):
        tok = self._peek()
        name_tok = self._expect("ident", what="variable")
        op_tok = self._advance()
        value = self._parse_expression()
        self._eat_optional_semicolon()
        return Assign(line=tok.line, target=name_tok.value,
                      op=op_tok.value, value=value)

    def _parse_incdec(self):
        tok = self._peek()
        name_tok = self._expect("ident", what="variable")
        op_tok = self._advance()
        self._eat_optional_semicolon()
        return IncDec(line=tok.line, target=name_tok.value,
                      op=op_tok.value, postfix=True)

    # -- send / send_slow ----------------------------------------------
    def _parse_send(self, kind: str):
        tok = self._advance()

        enc: Optional[str] = None
        if self._check("op", "["):
            self._advance()
            enc_parts: list[str] = []
            while not self._check("eof"):
                t = self._peek()
                if t.kind == "op" and t.value == "]":
                    break
                enc_parts.append(str(t.value) if t.value is not None else "")
                self._advance()
            self._expect("op", "]", "']'")
            enc = "".join(enc_parts)

            if enc and not is_valid_mode(enc):
                raise ScenarioParseError(
                    f"Line {tok.line}: unknown send mode {enc!r}. "
                    f"Known: {', '.join(known_modes())}"
                )

        expr = self._parse_expression()
        extra = None

        if kind == "send_slow":
            extra = self._parse_expression()

        self._eat_optional_semicolon()

        proc = ProcCall(line=tok.line, name=kind, args=[expr], enc=enc)
        if extra is not None:
            proc.args.append(extra)
        return proc

    # -- wait -----------------------------------------------------------
    def _parse_wait(self):
        tok = self._expect("kw", "wait")
        expr = self._parse_expression()
        self._eat_optional_semicolon()
        return ProcCall(line=tok.line, name="wait", args=[expr])

    # -- expect / expect_search ----------------------------------------
    def _parse_expect_call(self, name: str):
        tok = self._expect("kw", name)
        if self._check("op", "("):
            self._advance()
            args: list = []
            if not self._check("op", ")"):
                args.append(self._parse_expression())
                while self._match("op", ","):
                    args.append(self._parse_expression())
            self._expect("op", ")", "')'")
            self._eat_optional_semicolon()
            return ProcCall(line=tok.line, name=name, args=args)

        # legacy-style: expect "text" N
        needle_expr = self._parse_expression()
        args = [needle_expr]
        if not self._check("eof") and not self._check("op", "}"):
            try:
                nxt = self._peek()
                if nxt.kind == "num" or (nxt.kind == "op" and nxt.value in ("(", "!")):
                    timeout_expr = self._parse_expression()
                    args.append(timeout_expr)
            except ScenarioParseError:
                pass
        self._eat_optional_semicolon()
        return ProcCall(line=tok.line, name=name, args=args)

    # -- assert_rx ------------------------------------------------------
    def _parse_assert_rx(self):
        tok = self._expect("kw", "assert_rx")
        if self._check("op", "("):
            self._advance()
            args: list = []
            if not self._check("op", ")"):
                args.append(self._parse_expression())
            self._expect("op", ")", "')'")
            self._eat_optional_semicolon()
            return ProcCall(line=tok.line, name="assert_rx", args=args)

        needle_expr = self._parse_expression()
        self._eat_optional_semicolon()
        return ProcCall(line=tok.line, name="assert_rx", args=[needle_expr])

    # -- log / print ----------------------------------------------------
    def _parse_log(self):
        tok = self._expect("kw", "log")
        if self._check("op", "("):
            self._advance()
            args: list = []
            if not self._check("op", ")"):
                args.append(self._parse_expression())
            self._expect("op", ")", "')'")
            self._eat_optional_semicolon()
            return ProcCall(line=tok.line, name="log", args=args)
        expr = self._parse_expression()
        self._eat_optional_semicolon()
        return ProcCall(line=tok.line, name="log", args=[expr])

    def _parse_print(self):
        tok = self._expect("kw", "print")
        if self._check("op", "("):
            self._advance()
            args: list = []
            if not self._check("op", ")"):
                args.append(self._parse_expression())
            self._expect("op", ")", "')'")
            self._eat_optional_semicolon()
            return ProcCall(line=tok.line, name="print", args=args)
        expr = self._parse_expression()
        self._eat_optional_semicolon()
        return ProcCall(line=tok.line, name="print", args=[expr])

    # -- expressions (precedence climbing) -----------------------------
    def _parse_expression(self):
        return self._parse_or()

    def _parse_or(self):
        left = self._parse_and()
        while self._check("op", "||"):
            op_tok = self._advance()
            right = self._parse_and()
            left = BinaryOp(line=op_tok.line, op="||", left=left, right=right)
        return left

    def _parse_and(self):
        left = self._parse_eq()
        while self._check("op", "&&"):
            op_tok = self._advance()
            right = self._parse_eq()
            left = BinaryOp(line=op_tok.line, op="&&", left=left, right=right)
        return left

    def _parse_eq(self):
        left = self._parse_rel()
        while self._check("op", "==") or self._check("op", "!="):
            op_tok = self._advance()
            right = self._parse_rel()
            left = BinaryOp(line=op_tok.line, op=op_tok.value,
                            left=left, right=right)
        return left

    def _parse_rel(self):
        left = self._parse_add()
        while (self._check("op", "<") or self._check("op", ">")
               or self._check("op", "<=") or self._check("op", ">=")):
            op_tok = self._advance()
            right = self._parse_add()
            left = BinaryOp(line=op_tok.line, op=op_tok.value,
                            left=left, right=right)
        return left

    def _parse_add(self):
        left = self._parse_mul()
        while self._check("op", "+") or self._check("op", "-"):
            op_tok = self._advance()
            right = self._parse_mul()
            left = BinaryOp(line=op_tok.line, op=op_tok.value,
                            left=left, right=right)
        return left

    def _parse_mul(self):
        left = self._parse_unary()
        while (self._check("op", "*") or self._check("op", "/")
               or self._check("op", "%")):
            op_tok = self._advance()
            right = self._parse_unary()
            left = BinaryOp(line=op_tok.line, op=op_tok.value,
                            left=left, right=right)
        return left

    def _parse_unary(self):
        tok = self._peek()
        if tok.kind == "op" and tok.value in ("!", "-", "+"):
            self._advance()
            operand = self._parse_unary()
            return UnaryOp(line=tok.line, op=tok.value, operand=operand)
        return self._parse_primary()

    def _parse_primary(self):
        tok = self._peek()

        # numbers
        if tok.kind == "num":
            self._advance()
            return NumLit(line=tok.line, value=tok.value)

        # strings
        if tok.kind == "str":
            self._advance()
            return StrLit(line=tok.line, value=tok.value)

        # keywords true/false/null
        if tok.kind == "kw" and tok.value in ("true", "false"):
            self._advance()
            return BoolLit(line=tok.line, value=(tok.value == "true"))
        if tok.kind == "kw" and tok.value == "null":
            self._advance()
            return NullLit(line=tok.line)

        # parenthesized
        if tok.kind == "op" and tok.value == "(":
            self._advance()
            expr = self._parse_expression()
            self._expect("op", ")", "')'")
            return expr

        # identifier or callable keyword: variable or function call
        if tok.kind == "ident" or (
            tok.kind == "kw" and tok.value in _CALLABLE_KEYWORDS
        ):
            self._advance()
            name = tok.value
            if self._check("op", "("):
                self._advance()
                args: list = []
                if not self._check("op", ")"):
                    args.append(self._parse_expression())
                    while self._match("op", ","):
                        args.append(self._parse_expression())
                self._expect("op", ")", "')'")
                return CallExpr(line=tok.line, name=name, args=args)
            return VarRef(line=tok.line, name=name)

        raise ScenarioParseError(
            f"Line {tok.line}: unexpected token {tok.kind} {tok.value!r} "
            f"in expression"
        )


# ===========================================================================
# Compiler — AST → bytecode
# ===========================================================================
class _Compiler:
    """
    Emits a flat list of instructions.

    Instructions are tuples with variable shape:

        ("RET",)                                        end
        ("PUSH_CONST", value, line)
        ("POP", line)
        ("LOAD_VAR", name, line)
        ("LOAD_VAR_OR", name, line)
        ("STORE_VAR", name, line)
        ("UNARY", op, line)
        ("BINARY", op, line)
        ("JUMP", target, line)                          target = index
        ("JUMP_IF_FALSE", target, line)
        ("JUMP_IF_TRUE", target, line)
        ("CALL_FUNC", name, nargs, line)
        ("CALL_PROC", name, enc, nargs, line)
    """

    def __init__(self):
        self.code: list[tuple] = []
        self._loop_stack: list[dict] = []
        self._finished_loops: list[dict] = []

    # -- low level -----------------------------------------------------
    def _emit(self, op: str, *args, line: int = 0) -> int:
        self.code.append((op, *args, line))
        return len(self.code) - 1

    def _here(self) -> int:
        return len(self.code)

    def emit_jump(self, op: str, line: int) -> int:
        self.code.append((op, -1, line))
        return len(self.code) - 1

    def patch_jump(self, index: int, target: int) -> None:
        op, _old, line = self.code[index]
        self.code[index] = (op, target, line)

    # -- program -------------------------------------------------------
    def compile_program(self, body: list) -> list:
        for stmt in body:
            self.compile_statement(stmt)
        self._emit("RET", line=0)
        return self.code

    # -- statements ----------------------------------------------------
    def compile_statement(self, stmt) -> None:
        line = getattr(stmt, "line", 0)

        if isinstance(stmt, Block):
            for s in stmt.body:
                self.compile_statement(s)
            return

        if isinstance(stmt, LetStmt):
            self.compile_expr(stmt.value)
            self._emit("STORE_VAR", stmt.name, line=line)
            return

        if isinstance(stmt, Assign):
            if stmt.op == "=":
                self.compile_expr(stmt.value)
                self._emit("STORE_VAR", stmt.target, line=line)
                return
            self._emit("LOAD_VAR_OR", stmt.target, line=line)
            self.compile_expr(stmt.value)
            base_op = stmt.op[:-1]
            self._emit("BINARY", base_op, line=line)
            self._emit("STORE_VAR", stmt.target, line=line)
            return

        if isinstance(stmt, IncDec):
            self._emit("LOAD_VAR_OR", stmt.target, line=line)
            self._emit("PUSH_CONST", 1, line=line)
            op = "+" if stmt.op == "++" else "-"
            self._emit("BINARY", op, line=line)
            self._emit("STORE_VAR", stmt.target, line=line)
            return

        if isinstance(stmt, IfStmt):
            self.compile_expr(stmt.cond)
            jf = self.emit_jump("JUMP_IF_FALSE", line)
            for s in stmt.then_body:
                self.compile_statement(s)
            if stmt.else_body:
                j_end = self.emit_jump("JUMP", line)
                self.patch_jump(jf, self._here())
                for s in stmt.else_body:
                    self.compile_statement(s)
                self.patch_jump(j_end, self._here())
            else:
                self.patch_jump(jf, self._here())
            return

        if isinstance(stmt, WhileStmt):
            loop_start = self._here()
            self.compile_expr(stmt.cond)
            jf = self.emit_jump("JUMP_IF_FALSE", line)
            self._push_loop(cont_target=loop_start, exit_jump=jf)
            for s in stmt.body:
                self.compile_statement(s)
            self._emit("JUMP", loop_start, line)
            end = self._here()
            self.patch_jump(jf, end)
            self._pop_and_patch_loop(end, end)
            return

        if isinstance(stmt, ForStmt):
            if stmt.init is not None:
                self.compile_statement(stmt.init)
            loop_start = self._here()
            jf = None
            if stmt.cond is not None:
                self.compile_expr(stmt.cond)
                jf = self.emit_jump("JUMP_IF_FALSE", line)
            self._push_loop(cont_target=-1, exit_jump=jf)
            for s in stmt.body:
                self.compile_statement(s)
            cont_target = self._here()
            if stmt.step is not None:
                self.compile_statement(stmt.step)
            self._emit("JUMP", loop_start, line)
            end = self._here()
            if jf is not None:
                self.patch_jump(jf, end)
            self._pop_and_patch_loop(end, cont_target)
            return

        if isinstance(stmt, BreakStmt):
            if not self._loop_stack:
                raise ScenarioParseError(
                    f"Line {line}: 'break' outside of a loop"
                )
            idx = self.emit_jump("JUMP", line)
            self._loop_stack[-1]["breaks"].append(idx)
            return

        if isinstance(stmt, ContinueStmt):
            if not self._loop_stack:
                raise ScenarioParseError(
                    f"Line {line}: 'continue' outside of a loop"
                )
            idx = self.emit_jump("JUMP", line)
            self._loop_stack[-1]["continues"].append(idx)
            return

        if isinstance(stmt, ProcCall):
            self.compile_proccall(stmt)
            return

        if isinstance(stmt, (CallExpr, VarRef, NumLit, StrLit,
                             BoolLit, NullLit, BinaryOp, UnaryOp)):
            self.compile_expr(stmt)
            self._emit("POP", line=line)
            return

        raise ScenarioParseError(
            f"Line {line}: cannot compile statement {type(stmt).__name__}"
        )

    # -- procedures ----------------------------------------------------
    def compile_proccall(self, stmt: "ProcCall") -> None:
        line = stmt.line
        name = stmt.name
        args = list(stmt.args or [])

        if name == "send":
            self.compile_expr(args[0])
            self._emit("CALL_PROC", "send", stmt.enc or "", 1, line=line)
            return
        if name == "send_slow":
            self.compile_expr(args[0])
            self.compile_expr(args[1])
            self._emit("CALL_PROC", "send_slow", stmt.enc or "", 2, line=line)
            return
        if name == "wait":
            self.compile_expr(args[0])
            self._emit("CALL_PROC", "wait", "", 1, line=line)
            return
        if name == "log":
            self.compile_expr(args[0])
            self._emit("CALL_PROC", "log", "", 1, line=line)
            return
        if name == "print":
            self.compile_expr(args[0])
            self._emit("CALL_PROC", "print", "", 1, line=line)
            return
        if name == "assert_rx":
            self.compile_expr(args[0])
            self._emit("CALL_PROC", "assert_rx", "", 1, line=line)
            return
        if name in ("expect", "expect_search"):
            self._compile_call_expr_to_stack(name, args, line)
            self._emit("POP", line=line)
            return

        raise ScenarioParseError(
            f"Line {line}: unknown procedure {name!r}"
        )

    # -- expressions ---------------------------------------------------
    def compile_expr(self, node) -> None:
        line = getattr(node, "line", 0)

        if isinstance(node, NumLit):
            self._emit("PUSH_CONST", node.value, line=line); return
        if isinstance(node, StrLit):
            self._emit("PUSH_CONST", node.value, line=line); return
        if isinstance(node, BoolLit):
            self._emit("PUSH_CONST", node.value, line=line); return
        if isinstance(node, NullLit):
            self._emit("PUSH_CONST", None, line=line); return
        if isinstance(node, VarRef):
            self._emit("LOAD_VAR", node.name, line=line); return

        if isinstance(node, UnaryOp):
            self.compile_expr(node.operand)
            self._emit("UNARY", node.op, line=line)
            return

        if isinstance(node, BinaryOp):
            if node.op == "&&":
                self.compile_expr(node.left)
                jf = self.emit_jump("JUMP_IF_FALSE", line)
                self.compile_expr(node.right)
                j_end = self.emit_jump("JUMP", line)
                self.patch_jump(jf, self._here())
                self._emit("PUSH_CONST", False, line=line)
                self.patch_jump(j_end, self._here())
                return
            if node.op == "||":
                self.compile_expr(node.left)
                jt = self.emit_jump("JUMP_IF_TRUE", line)
                self.compile_expr(node.right)
                j_end = self.emit_jump("JUMP", line)
                self.patch_jump(jt, self._here())
                self._emit("PUSH_CONST", True, line=line)
                self.patch_jump(j_end, self._here())
                return
            self.compile_expr(node.left)
            self.compile_expr(node.right)
            self._emit("BINARY", node.op, line=line)
            return

        if isinstance(node, CallExpr):
            self._compile_call_expr_to_stack(node.name, node.args, line)
            return

        raise ScenarioParseError(
            f"Line {line}: cannot compile expression {type(node).__name__}"
        )

    def _compile_call_expr_to_stack(self, name: str, args: list, line: int) -> None:
        for a in args:
            self.compile_expr(a)
        self._emit("CALL_FUNC", name, len(args), line=line)

    # -- loop bookkeeping ----------------------------------------------
    def _push_loop(self, cont_target: int, exit_jump) -> None:
        self._loop_stack.append({
            "cont_target": cont_target,
            "breaks": [],
            "continues": [],
            "exit_jump": exit_jump,
        })

    def _pop_and_patch_loop(self, break_target: int, continue_target: int) -> None:
        top = self._loop_stack.pop()
        for idx in top["breaks"]:
            self.patch_jump(idx, break_target)
        for idx in top["continues"]:
            self.patch_jump(idx, continue_target)
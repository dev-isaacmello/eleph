"""Tokenizer for Elephant 2000. Indentation-significant, Python-style."""

import re
from dataclasses import dataclass

KEYWORDS = {
    "program", "event", "fact", "on", "if", "else", "answer", "with",
    "yes", "no", "record", "accept", "decline", "promise", "that",
    "not", "and", "or", "since_not", "count", "to",
    # sorts and quantification
    "sort", "exists", "where",
    # speech acts as things the program can ask about
    "spoke", "about",
    # accomplishment specs: promises about the future
    "eventually", "before", "release", "from",
    # authority: who is entitled to ask
    "permitted", "offer",
}

_TOKEN_RE = re.compile(r"""
      (?P<NUMBER>\d+)
    | (?P<IDENT>[A-Za-z_][A-Za-z_0-9]*)
    | (?P<ASSIGN>:=)
    | (?P<OP>>=|<=|==|!=|<|>)
    | (?P<PUNCT>[():,])
    | (?P<SPACE>[ \t]+)
    | (?P<COMMENT>\#.*)
""", re.VERBOSE)


class LexError(Exception):
    pass


@dataclass
class Token:
    kind: str
    value: str
    line: int
    col: int

    def __repr__(self):
        return f"{self.kind}({self.value!r})@{self.line}"


def tokenize(src: str):
    tokens = []
    indents = [0]
    lines = src.splitlines()

    for lineno, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue  # blank and comment lines carry no indentation meaning

        indent = len(raw) - len(raw.lstrip(" \t"))
        if raw[:indent].count("\t"):
            raise LexError(f"linha {lineno}: use espacos, nao tabs, para indentar")

        if indent > indents[-1]:
            indents.append(indent)
            tokens.append(Token("INDENT", "", lineno, indent))
        else:
            while indent < indents[-1]:
                indents.pop()
                tokens.append(Token("DEDENT", "", lineno, indent))
            if indent != indents[-1]:
                raise LexError(f"linha {lineno}: indentacao inconsistente")

        pos = indent
        while pos < len(raw):
            m = _TOKEN_RE.match(raw, pos)
            if not m:
                raise LexError(f"linha {lineno}: caractere inesperado {raw[pos]!r}")
            pos = m.end()
            kind = m.lastgroup
            text = m.group()
            if kind in ("SPACE", "COMMENT"):
                continue
            if kind == "IDENT" and text in KEYWORDS:
                kind = text.upper()
            tokens.append(Token(kind, text, lineno, m.start()))

        tokens.append(Token("NEWLINE", "", lineno, len(raw)))

    while len(indents) > 1:
        indents.pop()
        tokens.append(Token("DEDENT", "", len(lines) + 1, 0))
    tokens.append(Token("EOF", "", len(lines) + 1, 0))
    return tokens

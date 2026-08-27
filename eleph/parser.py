"""Recursive-descent parser for Elephant 2000."""

from . import ast as A
from .lexer import tokenize, Token


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, src: str):
        self.toks = tokenize(src)
        self.i = 0

    # ------------------------------------------------------------- helpers
    @property
    def cur(self) -> Token:
        return self.toks[self.i]

    def at(self, *kinds) -> bool:
        return self.cur.kind in kinds

    def eat(self, kind, what=None) -> Token:
        if self.cur.kind != kind:
            want = what or kind
            raise ParseError(
                f"linha {self.cur.line}: esperava {want}, veio "
                f"{self.cur.value or self.cur.kind!r}")
        t = self.cur
        self.i += 1
        return t

    def accept(self, kind):
        if self.cur.kind == kind:
            self.i += 1
            return True
        return False

    def skip_newlines(self):
        while self.accept("NEWLINE"):
            pass

    # ------------------------------------------------------------ program
    def parse(self) -> A.Program:
        self.skip_newlines()
        self.eat("PROGRAM")
        prog = A.Program(name=self.eat("IDENT").value)
        self.eat("NEWLINE")
        self.skip_newlines()

        while not self.at("EOF"):
            if self.at("SORT"):
                line = self.eat("SORT").line
                prog.sorts.append(A.SortDecl(self.eat("IDENT").value, line))
                self.eat("NEWLINE")
            elif self.at("EVENT"):
                prog.events.append(self.event_decl())
            elif self.at("FACT"):
                prog.facts.append(self.fact_decl())
            elif self.at("ON"):
                prog.handlers.append(self.handler())
            else:
                raise ParseError(
                    f"linha {self.cur.line}: esperava sort, event, fact ou on, veio "
                    f"{self.cur.value or self.cur.kind!r}")
            self.skip_newlines()
        return prog

    def event_decl(self) -> A.EventDecl:
        line = self.eat("EVENT").line
        name = self.eat("IDENT").value
        params = self.param_list()
        self.eat("NEWLINE")
        return A.EventDecl(name, params, line)

    def fact_decl(self) -> A.FactDecl:
        line = self.eat("FACT").line
        name = self.eat("IDENT").value
        params = self.param_list()
        self.eat("ASSIGN", "':='")
        body = self.texpr()
        self.eat("NEWLINE")
        return A.FactDecl(name, params, body, line)

    def param_list(self):
        """`(passenger: Passenger, flight: Flight)`; the annotation is optional."""
        params = []
        if self.accept_punct("("):
            if not self.at_punct(")"):
                params.append(self.param())
                while self.accept_punct(","):
                    params.append(self.param())
            self.eat_punct(")")
        return params

    def param(self):
        name = self.eat("IDENT").value
        if self.accept_punct(":"):
            return A.Param(name, self.eat("IDENT").value)
        return A.Param(name)

    def handler(self) -> A.Handler:
        line = self.eat("ON").line
        perf = self.eat("IDENT").value
        if perf not in ("question", "request"):
            raise ParseError(
                f"linha {line}: performativo {perf!r} desconhecido "
                f"(use question ou request)")
        self.eat_punct("(")
        caller = self.eat("IDENT").value
        self.eat_punct(",")
        subject = self.ref()
        self.eat_punct(")")
        permission = self.ref() if self.accept("PERMITTED") else None
        self.eat_punct(":")
        self.eat("NEWLINE")
        body = self.block()
        return A.Handler(perf, caller, subject, body, line, permission)

    # --------------------------------------------------------- statements
    def block(self):
        self.skip_newlines()
        self.eat("INDENT", "bloco indentado")
        stmts = []
        while not self.at("DEDENT", "EOF"):
            self.skip_newlines()
            if self.at("DEDENT", "EOF"):
                break
            stmts.append(self.stmt())
            self.skip_newlines()
        self.eat("DEDENT", "fim de bloco")
        if not stmts:
            raise ParseError("bloco vazio")
        return stmts

    def stmt(self) -> A.Stmt:
        if self.at("IF"):
            return self.if_stmt()
        if self.at("ANSWER"):
            return self.answer_stmt()
        if self.at("RECORD"):
            line = self.eat("RECORD").line
            atom = self.ref()
            self.eat("NEWLINE")
            return A.Record(atom, line)
        if self.at("ACCEPT", "DECLINE"):
            tok = self.cur
            self.i += 1
            target = self.eat("IDENT").value
            atom = self.ref() if self.at("IDENT") else None
            self.eat("NEWLINE")
            node = A.Accept if tok.kind == "ACCEPT" else A.Decline
            return node(target, atom, tok.line)
        if self.at("PROMISE"):
            return self.promise_stmt()
        if self.at("OFFER"):
            line = self.eat("OFFER").line
            target = self.eat("IDENT").value
            self.eat("THAT", "'that'")
            expr = self.texpr()
            self.eat("NEWLINE")
            return A.Promise(target, expr, "offer", None, line)
        if self.at("RELEASE"):
            line = self.eat("RELEASE").line
            target = self.eat("IDENT").value
            self.eat("FROM", "'from'")
            expr = self.texpr()
            self.eat("NEWLINE")
            return A.Release(target, expr, line)
        raise ParseError(
            f"linha {self.cur.line}: comando desconhecido "
            f"{self.cur.value or self.cur.kind!r}")

    def promise_stmt(self) -> A.Promise:
        line = self.eat("PROMISE").line
        target = self.eat("IDENT").value
        if self.accept("EVENTUALLY"):
            expr = self.texpr()
            self.eat("NEWLINE")
            return A.Promise(target, expr, "eventually", None, line)
        self.eat("THAT", "'that' ou 'eventually'")
        expr = self.texpr()
        if self.accept("BEFORE"):
            deadline = self.ref()
            self.eat("NEWLINE")
            return A.Promise(target, expr, "before", deadline, line)
        self.eat("NEWLINE")
        return A.Promise(target, expr, "now", None, line)

    def if_stmt(self) -> A.If:
        line = self.eat("IF").line
        cond = self.texpr()
        self.eat_punct(":")
        self.eat("NEWLINE")
        then = self.block()
        els = []
        self.skip_newlines()
        if self.at("ELSE"):
            self.eat("ELSE")
            self.eat_punct(":")
            self.eat("NEWLINE")
            els = self.block()
        return A.If(cond, then, els, line)

    def answer_stmt(self) -> A.Stmt:
        line = self.eat("ANSWER").line
        target = self.eat("IDENT").value
        if self.accept("WITH"):
            expr = self.texpr()
            self.eat("NEWLINE")
            return A.AnswerWith(target, expr, line)
        if self.accept("YES"):
            self.eat("NEWLINE")
            return A.AnswerLit(target, True, line)
        if self.accept("NO"):
            self.eat("NEWLINE")
            return A.AnswerLit(target, False, line)
        raise ParseError(f"linha {line}: esperava 'yes', 'no' ou 'with'")

    # -------------------------------------------------- temporal expressions
    def texpr(self) -> A.TExpr:
        return self.or_expr()

    def or_expr(self):
        left = self.and_expr()
        while self.accept("OR"):
            left = A.Or(left, self.and_expr())
        return left

    def and_expr(self):
        left = self.since_expr()
        while self.accept("AND"):
            left = A.And(left, self.since_expr())
        return left

    def since_expr(self):
        left = self.unary()
        if self.accept("SINCE_NOT"):
            return A.SinceNot(left, self.unary())
        return left

    def unary(self):
        if self.accept("NOT"):
            return A.Not(self.unary())
        return self.primary()

    def primary(self):
        if self.accept_punct("("):
            e = self.texpr()
            self.eat_punct(")")
            return e
        if self.accept("YES"):
            return A.Lit(True)
        if self.accept("NO"):
            return A.Lit(False)
        if self.at("EXISTS"):
            self.eat("EXISTS")
            var, sort = self.binder()
            return A.Exists(var, sort, self.since_expr())
        if self.accept("COUNT"):
            if self.at("IDENT") and self.peek_punct(1, ":"):
                var, sort = self.binder()
                body = self.since_expr()
                op, n = self.comparison()
                return A.CountOver(var, sort, body, op, n)
            atom = self.ref()
            op, n = self.comparison()
            return A.Count(atom, op, n)
        if self.at("SPOKE"):
            line = self.eat("SPOKE").line
            perf = self.cur.value        # 'accept'/'answer'/... are keywords
            self.i += 1
            if perf not in ("answer", "accept", "decline", "promise", "ask"):
                raise ParseError(
                    f"linha {line}: performativo {perf!r} nao registravel")
            self.eat("TO", "'to'")
            party = self.eat("IDENT").value
            self.eat("ABOUT", "'about'")
            return A.Spoke(perf, party, self.ref())
        return self.ref()

    def binder(self):
        """`P: Passenger where` -- the head of a quantifier."""
        var = self.eat("IDENT").value
        self.eat_punct(":")
        sort = self.eat("IDENT").value
        self.eat("WHERE", "'where'")
        return var, sort

    def comparison(self):
        if not self.at("OP"):
            raise ParseError(
                f"linha {self.cur.line}: esperava comparador depois de count")
        op = self.eat("OP").value
        return op, int(self.eat("NUMBER").value)

    def peek_punct(self, ahead, ch):
        t = self.toks[min(self.i + ahead, len(self.toks) - 1)]
        return t.kind == "PUNCT" and t.value == ch

    def ref(self) -> A.Ref:
        name = self.eat("IDENT", "nome de evento ou fato").value
        args = []
        if self.accept_punct("("):
            if not self.at_punct(")"):
                args.append(self.arg())
                while self.accept_punct(","):
                    args.append(self.arg())
            self.eat_punct(")")
        return A.Ref(name, tuple(args))

    def arg(self):
        """A variable, or a constraint on a numeric field of this event."""
        name = self.eat("IDENT", "argumento").value
        if self.at("OP"):
            op = self.eat("OP").value
            return A.Bound(name, op, int(self.eat("NUMBER").value))
        return name

    # ------------------------------------------------------ punct helpers
    def at_punct(self, ch):
        return self.cur.kind == "PUNCT" and self.cur.value == ch

    def accept_punct(self, ch):
        if self.at_punct(ch):
            self.i += 1
            return True
        return False

    def eat_punct(self, ch):
        if not self.at_punct(ch):
            raise ParseError(
                f"linha {self.cur.line}: esperava {ch!r}, veio "
                f"{self.cur.value or self.cur.kind!r}")
        t = self.cur
        self.i += 1
        return t


def parse(src: str) -> A.Program:
    return Parser(src).parse()

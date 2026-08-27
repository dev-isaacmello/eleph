"""Derivation of proof obligations from the form of the program.

This is McCarthy's central claim made mechanical: you do not write the
correctness conditions, they fall out of the text. A question handler owes
truthfulness and responsiveness; a promise owes discharge.

McCarthy separates input-output specifications from accomplishment
specifications -- his generalisation of illocutionary and perlocutionary
force. An immediate promise is the first kind and can be proved outright. A
promise about the future is the second kind: no program can guarantee it
alone, because discharge may wait on the world. What the compiler can demand
is that the program not promise the impossible -- that some path through the
program establishes what was promised -- and that the runtime carry the debt
openly until it is paid.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from . import ast as A
from .core import (CExpr, CAnd, CNot, COr, COcc, Resolver, PARTY, THING,
                   speech_event, show)


@dataclass
class Timed:
    """An expression together with how much of the handler's own output the
    log already contains when it is evaluated."""
    expr: CExpr
    appended: int


@dataclass
class Path:
    """A way through some handler, and the world events it leaves behind."""
    label: str
    tail: Tuple[COcc, ...]


@dataclass
class Obligation:
    kind: str
    handler: str
    line: int
    title: str
    detail: str
    assumptions: List[Timed]
    goal: Timed
    appended: Tuple[COcc, ...] = ()
    claims: Optional[bool] = None
    polarity: str = "valid"            # valid | satisfiable
    candidates: Tuple[Path, ...] = ()


@dataclass
class Structural:
    """A defect visible without a solver."""
    kind: str
    handler: str
    line: int
    message: str


@dataclass
class Analysis:
    obligations: List[Obligation] = field(default_factory=list)
    structural: List[Structural] = field(default_factory=list)
    paths: List[Path] = field(default_factory=list)


def iff(a: CExpr, b: CExpr) -> CExpr:
    return CAnd(COr(CNot(a), b), COr(CNot(b), a))


class Deriver:
    def __init__(self, prog: A.Program):
        self.prog = prog
        self.res = Resolver(prog)
        self.out = Analysis()

    def run(self) -> Analysis:
        self.check_every_fact_typechecks()
        self.out.paths = self.world_paths()
        self.check_no_unguarded_door()
        for h in self.prog.handlers:
            self.handler(h)
        return self.out

    def check_every_fact_typechecks(self):
        """Resolve every declared fact, used or not.

        Resolution is lazy, so a fact no handler mentions was never checked at
        all. A policy file is read by people as a statement of the rules, and a
        rule with a type error in it that nobody notices because nothing calls
        it is worse than no rule.
        """
        for f in self.prog.facts:
            env = {p.name: p.sort for p in f.params}
            self.res.resolve(f.body, env)

    def check_no_unguarded_door(self):
        """If one door onto a subject is locked, every door must be.

        A permission on one handler and none on its neighbour is not a policy,
        it is a locked front door beside an open window. This is exactly the
        kind of thing nobody notices in review and everybody notices in an
        incident report.
        """
        doors = {}
        for h in self.prog.handlers:
            doors.setdefault(h.subject.name, []).append(h)
        for subject, handlers in doors.items():
            locked = [h for h in handlers if h.permission is not None]
            open_ = [h for h in handlers if h.permission is None]
            if locked and open_:
                for h in open_:
                    self.out.structural.append(Structural(
                        "unguarded-door",
                        f"{h.performative}({h.caller}, {subject})", h.line,
                        f"outro handler de {subject} exige permissao "
                        f"(linha {locked[0].line}) e este nao exige nenhuma"))

    # ------------------------------------------------------------ handlers
    def env_of(self, h: A.Handler) -> dict:
        """Sorts for the variables the handler pattern binds."""
        decl = self.prog.event(h.subject.name) or self.prog.fact(h.subject.name)
        env = {h.caller: PARTY}
        if decl:
            for actual, param in zip(h.subject.args, decl.params):
                env[actual] = param.sort
        else:
            for a in h.subject.args:
                env[a] = THING
        return env

    def handler(self, h: A.Handler):
        env = self.env_of(h)
        label = f"{h.performative}({h.caller}, {h.subject.name})"

        # Everything this handler owes, it owes only when the caller was
        # entitled to ask. The permission joins the path condition rather than
        # being checked separately, so it is proved with the rest.
        gate = ([Timed(self.res.resolve(h.permission, env), 0)]
                if h.permission is not None else [])

        if h.performative == "question":
            asked = self.res.resolve(h.subject, env)
            self.check_responsive(h, label)
        else:
            asked = None
            self.check_decided(h, label)

        # the incoming utterance is itself part of the history
        entry = self.speech(h.performative if h.performative == "request"
                            else "ask", h.caller, h.subject, env)
        self.walk(h.body, gate, (entry,), h, label, asked, env)

    def speech(self, performative, party, subject: A.Ref, env) -> COcc:
        """The synthetic event under which an utterance is logged."""
        decl = self.prog.event(subject.name) or self.prog.fact(subject.name)
        params = list(decl.params) if decl else []
        name = speech_event(performative, subject.name)
        self.prog.ensure_event(name, [A.Param("party", PARTY)] + params)
        return COcc(name, (party,) + tuple(subject.args))

    # ----------------------------------------------------------- traversal
    def walk(self, stmts, gamma, appended, h, label, asked, env):
        for s in stmts:
            if isinstance(s, A.If):
                cond = self.res.resolve(s.cond, env)
                here = Timed(cond, len(appended))
                self.walk(s.then, gamma + [here], appended, h, label, asked, env)
                neg = Timed(CNot(cond), len(appended))
                self.walk(s.els, gamma + [neg], appended, h, label, asked, env)
                return                       # both branches accounted for

            if isinstance(s, A.Record):
                atom = self.res.resolve(s.atom, env, instant=True)
                appended = appended + (atom,)
                continue

            if isinstance(s, A.AnswerLit):
                appended = self.answer_lit(s, gamma, appended, label, asked)
                appended += (self.speech("answer", s.target, h.subject, env),)
                continue

            if isinstance(s, A.AnswerWith):
                appended = self.answer_with(s, gamma, appended, label, asked, env)
                appended += (self.speech("answer", s.target, h.subject, env),)
                continue

            if isinstance(s, A.Promise):
                appended = self.promise(s, gamma, appended, label, env)
                appended += (self.speech("promise", s.target, h.subject, env),)
                continue

            if isinstance(s, A.Release):
                # releasing cancels a debt; it owes nothing itself
                self.res.resolve(s.expr, env)
                continue

            if isinstance(s, (A.Accept, A.Decline)):
                perf = "accept" if isinstance(s, A.Accept) else "decline"
                if h.subject is not None:
                    appended = appended + (
                        self.speech(perf, s.target, h.subject, env),)
                continue

    # -------------------------------------------------------------- speech
    def answer_lit(self, s, gamma, appended, label, asked):
        if asked is None:
            self.out.structural.append(Structural(
                "answer-outside-question", label, s.line,
                "so um handler de question pode responder yes/no"))
            return appended
        goal = asked if s.value else CNot(asked)
        self.out.obligations.append(Obligation(
            kind="answer-truthful", handler=label, line=s.line,
            title=f"resposta {'yes' if s.value else 'no'} e verdadeira",
            detail=(f"neste caminho o programa afirma que "
                    f"{'' if s.value else 'nao '}vale {show(asked)}"),
            assumptions=list(gamma), goal=Timed(goal, len(appended)),
            appended=appended, claims=s.value))
        return appended

    def answer_with(self, s, gamma, appended, label, asked, env):
        phi = self.res.resolve(s.expr, env)
        if asked is None:
            self.out.structural.append(Structural(
                "answer-outside-question", label, s.line,
                "so um handler de question pode responder"))
            return appended
        self.out.obligations.append(Obligation(
            kind="answer-responsive", handler=label, line=s.line,
            title="a resposta responde a pergunta feita",
            detail=(f"o programa responde com {show(phi)}, "
                    f"mas foi perguntado {show(asked)}"),
            assumptions=list(gamma), goal=Timed(iff(phi, asked), len(appended)),
            appended=appended))
        return appended

    def promise(self, s: A.Promise, gamma, appended, label, env):
        phi = self.res.resolve(s.expr, env)

        if s.mode == "now":
            self.out.obligations.append(Obligation(
                kind="promise-kept", handler=label, line=s.line,
                title="a promessa esta cumprida ao ser feita",
                detail=(f"o programa promete {show(phi)}; nada no log "
                        f"deste caminho estabelece isso"),
                assumptions=list(gamma), goal=Timed(phi, len(appended)),
                appended=appended))
        else:
            when = ("se aceita" if s.mode == "offer"
                    else "em algum momento" if s.mode == "eventually"
                    else f"antes de {s.deadline.name}({', '.join(str(a) for a in s.deadline.args)})")
            word = "oferece" if s.mode == "offer" else "promete"
            self.out.obligations.append(Obligation(
                kind="promise-dischargeable", handler=label, line=s.line,
                title=(f"a oferta e honesta ({when})" if s.mode == "offer"
                       else f"a promessa pode vir a ser cumprida ({when})"),
                detail=(f"o programa {word} {show(phi)} {when}, mas nenhum "
                        f"caminho do programa chega a estabelecer isso"),
                assumptions=[], goal=Timed(phi, 0),
                appended=(), polarity="satisfiable",
                candidates=tuple(self.out.paths)))
        return appended

    # --------------------------------------------- what the program can do
    def world_paths(self) -> List[Path]:
        """Every way the program can change the world, for asking whether a
        promise about the future is one the program could ever keep."""
        out = []
        for h in self.prog.handlers:
            env = self.env_of(h)
            for tail, trail in self.record_paths(h.body, env):
                out.append(Path(f"{h.performative} {h.subject.name}"
                                f"{(' > ' + trail) if trail else ''}", tail))
        return out

    def record_paths(self, stmts, env, tail=(), trail=""):
        for idx, s in enumerate(stmts):
            if isinstance(s, A.If):
                rest = list(stmts[idx + 1:])
                out = []
                for branch, tag in ((s.then, "entao"), (s.els, "senao")):
                    out += self.record_paths(list(branch) + rest, env, tail,
                                             f"{trail}{tag} l{s.line} ")
                return out
            if isinstance(s, A.Record):
                tail = tail + (self.res.resolve(s.atom, env, instant=True),)
        return [(tail, trail.strip())]

    # -------------------------------------------------- structural checks
    def check_responsive(self, h: A.Handler, label):
        """Every path through a question handler answers exactly once."""
        for path, count in self._counts(h.body, (A.AnswerLit, A.AnswerWith)):
            if count == 0:
                self.out.structural.append(Structural(
                    "unanswered", label, h.line,
                    f"existe caminho ({path}) que nao responde nada"))
            elif count > 1:
                self.out.structural.append(Structural(
                    "double-answer", label, h.line,
                    f"caminho ({path}) responde {count} vezes"))

    def check_decided(self, h: A.Handler, label):
        """Every path through a request handler accepts or declines."""
        for path, count in self._counts(h.body, (A.Accept, A.Decline)):
            if count == 0:
                self.out.structural.append(Structural(
                    "undecided", label, h.line,
                    f"existe caminho ({path}) que nem aceita nem recusa"))
            elif count > 1:
                self.out.structural.append(Structural(
                    "double-decision", label, h.line,
                    f"caminho ({path}) decide {count} vezes"))

    def _counts(self, stmts, kinds, prefix="entrada"):
        """Enumerate paths, returning (label, number of matching statements)."""
        head = 0
        for idx, s in enumerate(stmts):
            if isinstance(s, kinds):
                head += 1
            elif isinstance(s, A.If):
                rest = stmts[idx + 1:]
                out = []
                for branch, tag in ((s.then, "entao"), (s.els, "senao")):
                    sub = self._counts(list(branch) + list(rest), kinds,
                                       f"{prefix} > linha {s.line} {tag}")
                    out += [(lab, head + n) for lab, n in sub]
                return out
        return [(prefix, head)]


def derive(prog: A.Program) -> Analysis:
    return Deriver(prog).run()

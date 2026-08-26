"""Concrete execution against a real log.

Deliberately the same `core` semantics the verifier encodes into Z3, walked
over an actual list of events instead of a symbolic one. There is no state
here beyond the log because the language cannot express any: what the program
knows is exactly what it has witnessed.

What the verifier cannot settle statically -- a promise about the future --
the runtime carries in the open, as a debt with a name on it.
"""

import threading
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from . import ast as A
from .core import (COcc, COnce, CSinceNot, CCount, CExists, CCountOver,
                   CNot, CAnd, COr, CLit, CExpr, PARTY, THING,
                   Resolver, speech_event, subst_vars, show, pretty)
from .incremental import Index
from .store import Store

COMMIT = "@commit"
RELEASE = "@release"
VOW = "@vow"      # a commitment made through the embedding API


@dataclass(frozen=True)
class Event:
    name: str
    args: Tuple[str, ...]

    def __str__(self):
        return f"{pretty(self.name)}({', '.join(self.args)})"


@dataclass
class Commitment:
    """A promise the program has made and not yet made good on."""
    party: str
    expr: CExpr
    binding: dict
    mode: str                      # eventually | before
    deadline: Optional[COcc]
    made_at: int
    line: int
    status: str = "aberta"         # aberta | cumprida | quebrada | liberada
    settled_at: Optional[int] = None

    def describe(self):
        """Named for the people it binds, not the variables it was written
        with -- a debt is owed by someone to someone about something."""
        ground = subst_vars(self.expr, self.binding)
        when = ("em algum momento" if self.mode == "eventually"
                else f"antes de {show(subst_vars(self.deadline, self.binding))}")
        return f"a {self.party}: {show(ground)} ({when})"


class Refusal(Exception):
    """The runtime will not perform a speech act it cannot ground."""


class CorruptCommitment(Exception):
    """The log remembers a promise the program no longer contains."""


@dataclass
class Machine:
    prog: A.Program
    log: List[Event] = field(default_factory=list)
    ledger: List[Commitment] = field(default_factory=list)
    transcript: List[str] = field(default_factory=list)
    enforce: bool = True
    audit: bool = False          # check the index against the log every query
    store: Optional[Store] = None
    _replaying: bool = False
    # Commitments made through the embedding API are logged as `@vow` events.
    # Their restorer is registered here so replay can settle them in order,
    # at the moment each was made, rather than all at the end.
    vow_restorer: Optional[object] = None

    def __post_init__(self):
        self.res = Resolver(self.prog)
        self._open = []                    # the debts still owed, kept apart
        # One writer at a time. The index folds an event in across several
        # dicts; a second thread reading between them would see a history that
        # never existed.
        self._lock = threading.RLock()
        self.index = Index()
        for e in self.queryable():
            self.index.track(e)

    def queryable(self):
        """Every expression this program could ever be asked about.

        They are tracked from the start because an index joined halfway
        through a history would have missed the part that matters.
        """
        out = []
        for h in self.prog.handlers:
            env = self.env_of(h)
            try:
                out.append(self.res.resolve(h.subject, env))
            except Exception:
                continue
            for e in self._exprs(h.body):
                try:
                    out.append(self.res.resolve(e, env))
                except Exception:
                    pass
        return out

    def _exprs(self, stmts):
        for s in stmts:
            if isinstance(s, A.If):
                yield s.cond
                yield from self._exprs(s.then)
                yield from self._exprs(s.els)
            elif isinstance(s, (A.AnswerWith, A.Promise, A.Release)):
                yield s.expr

    # ------------------------------------------------------------ evaluation
    def domain(self, sort, upto):
        """Quantifiers range over the objects the program has actually seen.
        It cannot reason about a passenger it has never heard of."""
        seen = []
        for ev in self.log[:upto + 1]:
            decl = self.prog.event(ev.name)
            if not decl:
                continue
            for value, param in zip(ev.args, decl.params):
                if (param.sort == sort or sort == THING) and value not in seen:
                    seen.append(value)
        return seen

    def at(self, e, i, b):
        if isinstance(e, COcc):
            if not 0 <= i < len(self.log):
                return False
            ev = self.log[i]
            return (ev.name == e.name
                    and ev.args == tuple(b.get(a, a) for a in e.args))
        return self.holds(e, i, b)

    def holds(self, e, t, b):
        """Truth of `e` given the log through position `t` inclusive."""
        if isinstance(e, CLit):
            return e.value
        if isinstance(e, COcc):
            return self.at(e, t, b)
        if isinstance(e, COnce):
            return any(self.at(e.arg, i, b) for i in range(t + 1))
        if isinstance(e, CSinceNot):
            return any(
                self.at(e.left, i, b)
                and not any(self.at(e.right, j, b) for j in range(i + 1, t + 1))
                for i in range(t + 1))
        if isinstance(e, CCount):
            args = tuple(b.get(a, a) for a in e.args)
            n = sum(1 for i in range(t + 1)
                    if self.log[i].name == e.name and self.log[i].args == args)
            return self.compare(n, e.op, e.n)
        if isinstance(e, CExists):
            return any(self.holds(e.body, t, dict(b, **{e.var: d}))
                       for d in self.domain(e.sort, t))
        if isinstance(e, CCountOver):
            n = sum(1 for d in self.domain(e.sort, t)
                    if self.holds(e.body, t, dict(b, **{e.var: d})))
            return self.compare(n, e.op, e.n)
        if isinstance(e, CNot):
            return not self.holds(e.arg, t, b)
        if isinstance(e, CAnd):
            return self.holds(e.left, t, b) and self.holds(e.right, t, b)
        if isinstance(e, COr):
            return self.holds(e.left, t, b) or self.holds(e.right, t, b)
        raise TypeError(f"expressao nao avaliavel: {e!r}")

    @staticmethod
    def compare(n, op, k):
        return {"<": n < k, "<=": n <= k, ">": n > k,
                ">=": n >= k, "==": n == k, "!=": n != k}[op]

    def now(self, cexpr, b):
        """Read the answer off the index when it has one; otherwise reread the
        log. `audit` makes it do both and insist they agree."""
        with self._lock:
            return self._now(cexpr, b)

    def _now(self, cexpr, b):
        if self.index.usable and cexpr in self.index.tracked:
            fast = self.index.value(cexpr, b)
            if self.audit:
                slow = self.holds(cexpr, len(self.log) - 1, b)
                if fast != slow:
                    raise AssertionError(
                        f"indice e log discordam sobre {show(cexpr)}: "
                        f"{fast} vs {slow}")
            return fast
        return self.holds(cexpr, len(self.log) - 1, b)

    # -------------------------------------------------------------- logging
    def append(self, ev: Event, note=None):
        with self._lock:
            self.log.append(ev)
            self.index.feed(ev.name, ev.args)
            if self.store is not None and not self._replaying:
                self.store.append(ev.name, ev.args)
            if note:
                self.say(note)
            self.settle()

    # ----------------------------------------------------------- durability
    def attach(self, store: Store):
        """Take up a history that is already on disk, then keep writing to it.

        Nothing is loaded but events. The index and the ledger are rebuilt by
        living through the past again, which is the only way this language
        would allow them to be rebuilt.
        """
        self.store = store
        self._replaying = True
        try:
            for name, args in store.load():
                ev = Event(name, tuple(args))
                self.log.append(ev)
                self.index.feed(name, ev.args)
                if name == COMMIT:
                    self._restore_commitment(ev.args)
                elif name == RELEASE:
                    self._restore_release(ev.args)
                elif name == VOW and self.vow_restorer is not None:
                    self.vow_restorer(ev.args)
                self.settle()
        finally:
            self._replaying = False
        return self

    def _commitment_from(self, args):
        """(party, line, subject args...) is enough to name a promise again."""
        party, line = args[0], int(args[1])
        h, stmt = self.prog.stmt_at(line)
        if h is None:
            raise CorruptCommitment(
                f"o log cita uma promessa na linha {line}, que o programa "
                f"nao tem mais -- log e programa divergiram")
        env = self.env_of(h)
        binding = {h.caller: party}
        binding.update(dict(zip(h.subject.args, args[2:])))
        expr = self.res.resolve(stmt.expr, env)
        return h, stmt, binding, expr, party, line

    def _restore_commitment(self, args):
        h, stmt, binding, expr, party, line = self._commitment_from(args)
        deadline = (self.res.resolve(stmt.deadline, self.env_of(h),
                                     instant=True) if stmt.deadline else None)
        c = Commitment(party, expr, binding, stmt.mode, deadline,
                       len(self.log) - 1, line)
        self.ledger.append(c)
        self._open.append(c)

    def _restore_release(self, args):
        _, _, _, expr, party, _ = self._commitment_from(args)
        self._settle_release(party, expr)

    def utter(self, performative, party, subject_name, args, note):
        decl = self.prog.event(subject_name) or self.prog.fact(subject_name)
        params = list(decl.params) if decl else []
        name = speech_event(performative, subject_name)
        self.prog.ensure_event(name, [A.Param("party", PARTY)] + params)
        self.append(Event(name, (party,) + tuple(args)), note)

    # ------------------------------------------------------------- ledger
    def settle(self):
        """After anything happens, see which debts just came good.

        Only open debts are looked at, and each is read off the index rather
        than by rereading the log -- otherwise the ledger reintroduces exactly
        the quadratic cost the index was built to remove.
        """
        t = len(self.log) - 1
        still_open = []
        for c in self._open:
            if self.now(c.expr, c.binding):
                c.status, c.settled_at = "cumprida", t
                self.say(f"    [livro] cumprida -- {c.describe()}")
            elif c.deadline is not None and self.at(c.deadline, t, c.binding):
                c.status, c.settled_at = "quebrada", t
                self.say(f"    [livro] QUEBRADA -- {c.describe()}")
            else:
                still_open.append(c)
        self._open = still_open

    def outstanding(self):
        return list(self._open)

    def breached(self):
        return [c for c in self.ledger if c.status == "quebrada"]

    # ------------------------------------------------------------- dispatch
    def deliver(self, performative: str, speaker: str, name: str, args):
        h = self.match(performative, name)
        if h is None:
            self.say(f"{speaker}: {performative} {name} -- nenhum handler; "
                     f"o programa fica calado")
            return

        b = {h.caller: speaker}
        b.update(dict(zip(h.subject.args, args)))
        self.say(f"{speaker}: {performative} {name}({', '.join(args)})")
        self.utter("request" if performative == "request" else "ask",
                   speaker, name, args, None)

        env = self.env_of(h)
        asked = (self.res.resolve(h.subject, env) if performative == "question"
                 else None)
        self.exec(h.body, b, asked, h, env)

    def env_of(self, h):
        decl = self.prog.event(h.subject.name) or self.prog.fact(h.subject.name)
        env = {h.caller: PARTY}
        for actual, param in zip(h.subject.args,
                                 decl.params if decl else []):
            env[actual] = param.sort
        return env

    def match(self, performative, name):
        for h in self.prog.handlers:
            if h.performative == performative and h.subject.name == name:
                return h
        return None

    def exec(self, stmts, b, asked, h, env):
        for s in stmts:
            if isinstance(s, A.If):
                cond = self.res.resolve(s.cond, env)
                branch = s.then if self.now(cond, b) else s.els
                self.exec(branch, b, asked, h, env)
                return

            if isinstance(s, A.Record):
                atom = self.res.resolve(s.atom, env, instant=True)
                ev = Event(atom.name, tuple(b.get(a, a) for a in atom.args))
                self.append(ev, f"    [log] {ev}")

            elif isinstance(s, A.AnswerLit):
                self.answer(s.value, asked, b, h)

            elif isinstance(s, A.AnswerWith):
                phi = self.res.resolve(s.expr, env)
                self.answer(self.now(phi, b), asked, b, h)

            elif isinstance(s, A.Promise):
                self.promise(s, b, env, h)

            elif isinstance(s, A.Release):
                self.release(s, b, env, h)

            elif isinstance(s, (A.Accept, A.Decline)):
                perf = "accept" if isinstance(s, A.Accept) else "decline"
                word = "aceito" if perf == "accept" else "recuso"
                self.utter(perf, b.get(s.target, s.target), h.subject.name,
                           [b.get(a, a) for a in h.subject.args],
                           f"    programa: {word}")

    # -------------------------------------------------------- speech acts
    def promise(self, s: A.Promise, b, env, h):
        phi = self.res.resolve(s.expr, env)
        party = b.get(s.target, s.target)

        if s.mode == "now":
            if self.enforce and not self.now(phi, b):
                raise Refusal(
                    f"linha {s.line}: o programa tentou prometer algo que o log "
                    f"nao sustenta. Isto e o que o verificador teria apontado "
                    f"estaticamente.")
            self.utter("promise", party, h.subject.name,
                       [b.get(a, a) for a in h.subject.args],
                       "    programa: prometo, e ja esta feito")
            return

        deadline = (self.res.resolve(s.deadline, env, instant=True)
                    if s.deadline else None)
        c = Commitment(party, phi, dict(b), s.mode, deadline,
                       len(self.log), s.line)
        self.ledger.append(c)
        self._open.append(c)
        # the debt goes into the log too, so a restart can find it again
        self.append(Event(COMMIT, (party, str(s.line))
                          + tuple(b.get(a, a) for a in h.subject.args)))
        self.utter("promise", party, h.subject.name,
                   [b.get(a, a) for a in h.subject.args],
                   f"    programa: prometo -- {c.describe()}")

    def release(self, s: A.Release, b, env, h):
        phi = self.res.resolve(s.expr, env)
        party = b.get(s.target, s.target)
        self.append(Event(RELEASE, (party, str(s.line))
                          + tuple(b.get(a, a) for a in h.subject.args)))
        self._settle_release(party, phi)

    def _settle_release(self, party, phi):
        freed = [c for c in self._open if c.party == party and c.expr == phi]
        for c in freed:
            c.status, c.settled_at = "liberada", len(self.log) - 1
            self.say(f"    [livro] liberada -- {c.describe()}")
        self._open = [c for c in self._open if c not in freed]

    def answer(self, value, asked, b, h):
        """The answer axiom, enforced at runtime as well as proved statically."""
        if self.enforce and asked is not None:
            truth = self.now(asked, b)
            if value != truth:
                raise Refusal(
                    f"o programa tentou responder {'yes' if value else 'no'} "
                    f"quando o log diz {'yes' if truth else 'no'}. "
                    f"A linguagem nao deixa.")
        self.utter("answer", b.get(h.caller, h.caller), h.subject.name,
                   [b.get(a, a) for a in h.subject.args],
                   f"    programa: {'yes' if value else 'no'}")

    def say(self, line):
        self.transcript.append(line)


def session(prog: A.Program, script: str, enforce=True,
            store: Optional[Store] = None) -> Machine:
    """Run a dialogue script: one speech act per line.

        given    make_reservation(alice, ba117)
        question alice has_reservation(alice, ba117)
        request  alice make_reservation(alice, ba117)

    `given` seeds the history directly, which is how you replay a
    counterexample the verifier handed you.
    """
    m = Machine(prog, enforce=enforce)
    if store is not None:
        m.attach(store)
    for raw in script.splitlines():
        line = raw.split("#")[0].strip()
        if not line:
            continue
        head, rest = line.split(None, 1)
        if head == "given":
            name, _, argstr = rest.partition("(")
            args = tuple(a.strip() for a in argstr.rstrip(")").split(",")
                         if a.strip())
            ev = Event(name.strip(), args)
            m.append(ev, f"[log] {ev}   (historico pre-existente)")
            continue
        speaker, subject = rest.split(None, 1)
        name, _, argstr = subject.partition("(")
        args = tuple(a.strip() for a in argstr.rstrip(")").split(",")
                     if a.strip())
        m.deliver(head, speaker, name.strip(), args)
    return m

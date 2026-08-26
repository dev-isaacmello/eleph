"""The part of this you can put in a Python program tomorrow.

The language is the research artifact. What most systems need is smaller: a
thing that watches what happened, tells you what is true of it, refuses to let
you assert what is not, and remembers what you promised.

    from eleph import Policy

    policy = Policy.from_file("booking.eleph")
    assert policy.verify().proved          # the same file, proved statically

    g = policy.guard(log="booking.jsonl")  # durable; reopening replays

    g.record("make_reservation", "alice", "ba117")
    g.holds("has_reservation", "alice", "ba117")     # True
    g.require("has_reservation", "alice", "ba117")   # raises if it is not

    g.promise("alice", "has_seat", "alice", "ba117",
              before=("board", ("alice", "ba117")))
    g.outstanding()                        # what is still owed, to whom

The point of routing through a policy file rather than writing the checks in
Python is that the file is the same artifact `eleph check` proves. A guard
whose rules were proved is a different thing from a guard whose rules someone
believed.
"""

import json
import pathlib
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from . import ast as A
from .core import PARTY, THING, Resolver, show, subst_vars
from .obligations import derive
from .parser import parse
from .runtime import VOW, Commitment, Event, Machine, Refusal
from .store import Store
from .verify import verify

class UnknownName(Exception):
    """Asked about something the policy does not declare."""


class Ungrounded(Refusal):
    """Asserted something the history does not support."""


@dataclass
class VerifyReport:
    results: list
    structural: list

    @property
    def proved(self) -> bool:
        """Every obligation holds, and holds for every history."""
        return (not self.structural
                and all(r.proved for r in self.results))

    @property
    def failures(self):
        return [r for r in self.results if not r.ok]

    def summary(self) -> str:
        if self.structural:
            return f"{len(self.structural)} defeito(s) estrutural(is)"
        if self.failures:
            return (f"{len(self.failures)} de {len(self.results)} obrigacoes "
                    f"nao se sustentam")
        if self.proved:
            return f"{len(self.results)} obrigacoes provadas para todo historico"
        return f"{len(self.results)} obrigacoes sem contraexemplo, nao exaustivo"


class Policy:
    """A parsed policy: the facts a system is willing to be held to."""

    def __init__(self, source: str):
        self.source = source
        self.program = parse(source)

    @classmethod
    def from_file(cls, path) -> "Policy":
        return cls(pathlib.Path(path).read_text())

    def verify(self, bound=None, objects=None) -> VerifyReport:
        """Run the static checker over this policy's own handlers."""
        analysis = derive(self.program)
        return VerifyReport(verify(self.program, analysis, bound, objects),
                            analysis.structural)

    def guard(self, log=None, audit=False) -> "Guard":
        return Guard(self, log=log, audit=audit)

    # ------------------------------------------------------------ lookups
    def facts(self):
        return [f.name for f in self.program.facts]

    def events(self):
        return [e.name for e in self.program.events if not e.synthetic]


class Guard:
    """A live view of one history: what is true, and what is owed."""

    def __init__(self, policy: Policy, log=None, audit=False):
        self.policy = policy
        self.machine = Machine(policy.program, audit=audit)
        self._resolver = Resolver(policy.program)
        self._cache = {}
        for name in policy.facts():
            self._resolve(name)          # track before any event arrives
        self.machine.index = self.machine.index
        for expr in self._cache.values():
            self.machine.index.track(expr)
        if log is not None:
            # registered before the replay: a debt settled halfway through the
            # history has to be settled halfway through the replay too
            self.machine.vow_restorer = self._restore_vow
            self.machine.attach(Store(log))

    # ------------------------------------------------------------ facts
    def _decl(self, name):
        decl = (self.policy.program.fact(name)
                or self.policy.program.event(name))
        if decl is None:
            raise UnknownName(
                f"{name!r} nao e fato nem evento desta politica; "
                f"declarados: {', '.join(sorted(self.policy.facts() + self.policy.events()))}")
        return decl

    def _resolve(self, name):
        if name not in self._cache:
            decl = self._decl(name)
            env = {p.name: p.sort for p in decl.params}
            ref = A.Ref(name, tuple(p.name for p in decl.params))
            self._cache[name] = self._resolver.resolve(ref, env)
        return self._cache[name]

    def _binding(self, name, args) -> dict:
        decl = self._decl(name)
        if len(args) != len(decl.params):
            raise UnknownName(
                f"{name} espera {len(decl.params)} argumentos "
                f"({', '.join(p.name for p in decl.params)}), "
                f"recebeu {len(args)}")
        return {p.name: str(a) for p, a in zip(decl.params, args)}

    def holds(self, fact: str, *args) -> bool:
        """Is this true, given everything that has happened?"""
        return self.machine.now(self._resolve(fact), self._binding(fact, args))

    def require(self, fact: str, *args):
        """Proceed only if the history supports it."""
        if not self.holds(fact, *args):
            raise Ungrounded(
                f"o log nao sustenta {fact}({', '.join(map(str, args))})")

    def assert_answer(self, fact: str, value: bool, *args):
        """The answer axiom, usable directly: say only what is so."""
        truth = self.holds(fact, *args)
        if bool(value) != truth:
            raise Ungrounded(
                f"tentou afirmar {fact}({', '.join(map(str, args))}) = "
                f"{bool(value)} quando o log diz {truth}")
        return truth

    # ----------------------------------------------------------- history
    def record(self, event: str, *args):
        """Something happened. This is the only way anything is ever true."""
        decl = self.policy.program.event(event)
        if decl is None or decl.synthetic:
            raise UnknownName(f"{event!r} nao e um evento declarado")
        if len(args) != len(decl.params):
            raise UnknownName(
                f"{event} espera {len(decl.params)} argumentos, "
                f"recebeu {len(args)}")
        self.machine.append(Event(event, tuple(str(a) for a in args)))

    @property
    def events(self) -> Sequence[Event]:
        return tuple(e for e in self.machine.log if not e.name.startswith("@"))

    # --------------------------------------------------------- commitments
    def promise(self, party: str, fact: str, *args,
                before: Optional[Tuple[str, tuple]] = None) -> Commitment:
        """Owe someone something. Kept in the open until it is settled."""
        expr = self._resolve(fact)
        binding = self._binding(fact, args)
        deadline = None
        if before is not None:
            dname, dargs = before
            deadline = subst_vars(self._resolve_event_atom(dname, dargs), {})
        c = Commitment(str(party), expr, binding,
                       "before" if before else "eventually", deadline,
                       len(self.machine.log), 0)
        self.machine.ledger.append(c)
        self.machine._open.append(c)
        self.machine.append(Event(VOW, (json.dumps({
            "party": str(party), "fact": fact,
            "args": [str(a) for a in args],
            "before": [before[0], [str(a) for a in before[1]]] if before else None,
        }, sort_keys=True),)))
        return c

    def _resolve_event_atom(self, name, args):
        decl = self.policy.program.event(name)
        if decl is None:
            raise UnknownName(f"{name!r} nao e um evento declarado")
        from .core import COcc
        return COcc(name, tuple(str(a) for a in args))

    def release(self, party: str, fact: str, *args):
        """Let the program off a debt."""
        self.machine._settle_release(str(party), self._resolve(fact))

    def outstanding(self) -> List[Commitment]:
        return self.machine.outstanding()

    def breached(self) -> List[Commitment]:
        return self.machine.breached()

    @property
    def ledger(self) -> List[Commitment]:
        return list(self.machine.ledger)

    def _restore_vow(self, args):
        """Rebuild one promise, at the point in the history where it was made.

        The log records the promise, not the ledger. Everything else about the
        debt (whether it was kept, broken, or released) follows from the events
        that came after it, so it is recomputed rather than stored.
        """
        rec = json.loads(args[0])
        before = ((rec["before"][0], tuple(rec["before"][1]))
                  if rec["before"] else None)
        c = Commitment(rec["party"], self._resolve(rec["fact"]),
                       self._binding(rec["fact"], rec["args"]),
                       "before" if before else "eventually",
                       self._resolve_event_atom(*before) if before else None,
                       len(self.machine.log) - 1, 0)
        self.machine.ledger.append(c)
        self.machine._open.append(c)

    def report(self) -> str:
        lines = [f"{len(self.events)} eventos"]
        for c in self.machine.ledger:
            lines.append(f"  {c.status.upper():9} {c.describe()}")
        return "\n".join(lines)

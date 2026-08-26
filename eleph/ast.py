"""AST for Elephant 2000.

Two families of node. Temporal expressions (TExpr) denote a truth value at the
present moment, computed from the whole past. Statements denote speech acts the
program performs. There is deliberately no assignment and no variable: the log
is the only state, so there is nothing to assign to.
"""

from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------- temporal

class TExpr:
    """A predicate over the past, evaluated at the present moment."""


@dataclass(frozen=True)
class Ref(TExpr):
    """`make_reservation(P, F)` -- a bare reference.

    If the name is a declared event, this means *the event occurred at least
    once in the past*. This is the trap McCarthy built the language to expose:
    "they made a reservation" is not "they have a reservation". If the name is
    a declared fact, it expands to that fact's body.
    """
    name: str
    args: tuple


@dataclass(frozen=True)
class SinceNot(TExpr):
    """`A since_not B` -- A occurred, and no B has occurred since.

    The primitive of non-forgetting. This is the reservation predicate.
    """
    left: TExpr
    right: TExpr


@dataclass(frozen=True)
class Count(TExpr):
    """`count E(args) < n` -- how many times E occurred in the whole past."""
    atom: Ref
    op: str
    n: int


@dataclass(frozen=True)
class Exists(TExpr):
    """`exists P: Passenger where <body>`."""
    var: str
    sort: str
    body: TExpr


@dataclass(frozen=True)
class CountOver(TExpr):
    """`count P: Passenger where <body> >= 180` -- how many things satisfy it.

    This is what a seat limit needs, and what the language could not say
    before quantification existed.
    """
    var: str
    sort: str
    body: TExpr
    op: str
    n: int


@dataclass(frozen=True)
class Spoke(TExpr):
    """`spoke accept to C about make_reservation(P, F)`.

    True when the program performed that speech act in the exchange about that
    subject. The program's own utterances are in the history, so it can be
    asked about them -- which is what makes "did I already answer this?"
    expressible. The subject is what the exchange was about, not the content
    of the utterance: an arbitrary promised formula has no name to log under.
    """
    performative: str
    party: str
    atom: Ref


@dataclass(frozen=True)
class Not(TExpr):
    arg: TExpr


@dataclass(frozen=True)
class And(TExpr):
    left: TExpr
    right: TExpr


@dataclass(frozen=True)
class Or(TExpr):
    left: TExpr
    right: TExpr


@dataclass(frozen=True)
class Lit(TExpr):
    """`yes` / `no` used as a temporal expression."""
    value: bool


# -------------------------------------------------------------- statements

class Stmt:
    pass


@dataclass
class If(Stmt):
    cond: TExpr
    then: List[Stmt]
    els: List[Stmt] = field(default_factory=list)
    line: int = 0


@dataclass
class AnswerLit(Stmt):
    """`answer C yes` -- asserts the truth of the formula that was *asked*.

    This is the statement that can lie, and therefore the statement the answer
    axiom is about.
    """
    target: str
    value: bool
    line: int = 0


@dataclass
class AnswerWith(Stmt):
    """`answer C with <texpr>` -- answers by evaluating against the log.

    Truthful by construction when the expression is the one asked; the verifier
    still checks that it *is* the one asked.
    """
    target: str
    expr: TExpr
    line: int = 0


@dataclass
class Record(Stmt):
    """`record make_reservation(P, F)` -- append a world event to the log."""
    atom: Ref
    line: int = 0


@dataclass
class Accept(Stmt):
    target: str
    atom: Optional[Ref] = None
    line: int = 0


@dataclass
class Decline(Stmt):
    target: str
    atom: Optional[Ref] = None
    line: int = 0


@dataclass
class Promise(Stmt):
    """A commitment. Three strengths, in McCarthy's terms an input-output spec
    and two kinds of accomplishment spec:

        promise C that phi                 -- already true when said
        promise C eventually phi           -- standing obligation
        promise C that phi before E(...)   -- obligation with a deadline
    """
    target: str
    expr: TExpr
    mode: str = "now"                 # now | eventually | before
    deadline: Optional['Ref'] = None
    line: int = 0


@dataclass
class Release(Stmt):
    """`release C from <texpr>` -- the promisee lets the program off."""
    target: str
    expr: TExpr
    line: int = 0


# ------------------------------------------------------------ declarations

@dataclass(frozen=True)
class Param:
    name: str
    sort: str = "Thing"


@dataclass
class SortDecl:
    name: str
    line: int = 0


@dataclass
class EventDecl:
    name: str
    params: List[Param]
    line: int = 0
    synthetic: bool = False           # generated for a speech act

    @property
    def sorts(self):
        return [p.sort for p in self.params]


@dataclass
class FactDecl:
    name: str
    params: List[Param]
    body: TExpr
    line: int = 0

    @property
    def names(self):
        return [p.name for p in self.params]


@dataclass
class Handler:
    """`on question(C, has_reservation(P, F)): ...`"""
    performative: str          # question | request
    caller: str                # variable bound to the other party
    subject: Ref               # the formula asked, or the action requested
    body: List[Stmt]
    line: int = 0


@dataclass
class Program:
    name: str
    sorts: List[SortDecl] = field(default_factory=list)
    events: List[EventDecl] = field(default_factory=list)
    facts: List[FactDecl] = field(default_factory=list)
    handlers: List[Handler] = field(default_factory=list)

    def event(self, name):
        return next((e for e in self.events if e.name == name), None)

    def fact(self, name):
        return next((f for f in self.facts if f.name == name), None)

    def sort_names(self):
        declared = [s.name for s in self.sorts]
        return declared or ["Thing"]

    def stmt_at(self, line: int):
        """The promise or release written on that line, and its handler.

        Restoring a commitment after a restart needs to know which one was
        made, and the log records the line rather than the formula -- a
        formula has no name to write down.
        """
        def walk(stmts):
            for s in stmts:
                if isinstance(s, (Promise, Release)) and s.line == line:
                    return s
                if isinstance(s, If):
                    found = walk(s.then) or walk(s.els)
                    if found:
                        return found
            return None

        for h in self.handlers:
            found = walk(h.body)
            if found:
                return h, found
        return None, None

    def ensure_event(self, name, params, line=0):
        """Declare a synthetic event for a speech act, if not already there."""
        found = self.event(name)
        if found is None:
            found = EventDecl(name, params, line, synthetic=True)
            self.events.append(found)
        return found

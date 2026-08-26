"""Bounded verification of the derived obligations, discharged by Z3.

An obligation says: under this path condition, this formula must hold of the
log. We look for a history that satisfies the path condition and falsifies the
formula. If there is none within the bound, the obligation stands. If there is
one, we hand back the shortest such history -- which is the useful artifact,
because it is a script of how the program lies.

Two bounds, both reported rather than hidden: how long a history we consider,
and how many distinct objects of each sort exist in it.
"""

from dataclasses import dataclass
from typing import List, Optional

import z3

from . import ast as A
from .core import (CExpr, COcc, COnce, CSinceNot, CCount, CExists, CCountOver,
                   CNot, CAnd, COr, CLit, PARTY, THING, subst_vars, pretty)
from .obligations import Obligation, Analysis
from .threshold import Threshold, compute as compute_threshold


IDLE = 0

_NONCE = 0


def _fresh() -> str:
    """Z3 keeps one global symbol table, so every encoding needs its own
    namespace or a name declared at one sort collides with the next."""
    global _NONCE
    _NONCE += 1
    return f"!{_NONCE}"


def _plain(text: str) -> str:
    return str(text).split("!")[0]


def _or(xs):
    xs = list(xs)
    return z3.Or(*xs) if xs else z3.BoolVal(False)


def _and(xs):
    xs = list(xs)
    return z3.And(*xs) if xs else z3.BoolVal(True)


def _cmp(total, op, n):
    return {"<": total < n, "<=": total <= n, ">": total > n,
            ">=": total >= n, "==": total == n, "!=": total != n}[op]


@dataclass
class Result:
    obligation: Obligation
    ok: bool
    trace: Optional[List[str]] = None
    threshold: Optional[Threshold] = None

    @property
    def proved(self):
        """`ok` means no counterexample was found. `proved` means none exists."""
        return self.ok and self.threshold is not None and self.threshold.complete


class Encoder:
    """A symbolic history of `n` arbitrary past events plus a concrete tail,
    over a finite universe of `k` objects per sort."""

    def __init__(self, prog: A.Program, n: int, tail=(), k: int = 3,
                 exprs=()):
        self.prog = prog
        self.n = n
        self.tail = tail
        self.k = k
        self.ns = _fresh()
        self.length = n + len(tail)
        self.index = {e.name: i + 1 for i, e in enumerate(prog.events)}
        self.arity = max([len(e.params) for e in prog.events] + [0])

        self.sorts, self.elems = {}, {}
        for name in list(prog.sort_names()) + [PARTY, THING]:
            if name in self.sorts:
                continue
            # full name, lowercased: 'Party' and 'Passenger' both start with
            # p and a shared label makes two sorts indistinguishable in a model
            labels = [f"{name.lower()}{i}{self.ns}" for i in range(k)]
            srt, cs = z3.EnumSort(name + self.ns, labels)
            self.sorts[name] = srt
            self.elems[name] = list(cs)

        self.sortof = {}
        for e in exprs:
            self.infer_sorts(e)

        self.consts = {}
        self.kind = [z3.Int(f"kind_{i}{self.ns}") for i in range(self.length)]
        self.slot = {
            (i, j, s): z3.Const(f"a_{s}_{i}_{j}{self.ns}", self.sorts[s])
            for i in range(self.length)
            for j in range(self.arity)
            for s in self.sorts}
        self.facts = []
        self._well_formed()

    # ------------------------------------------------------------- sorts
    def infer_sorts(self, e):
        """A variable's sort is whatever the event declaration says it is."""
        if isinstance(e, (COcc, CCount)):
            ev = self.prog.event(e.name)
            if ev:
                for actual, param in zip(e.args, ev.params):
                    self.sortof.setdefault(actual, param.sort)
        for attr in ("arg", "left", "right", "body"):
            child = getattr(e, attr, None)
            if isinstance(child, CExpr):
                self.infer_sorts(child)

    def sort_of(self, name):
        if name.startswith("#"):
            return name[1:].rsplit("_", 1)[0]
        return self.sortof.get(name, THING)

    def const(self, name):
        """A variable, or a literal element of the finite universe."""
        if name.startswith("#"):
            srt, idx = name[1:].rsplit("_", 1)
            return self.elems[srt][int(idx)]
        if name not in self.consts:
            srt = self.sorts[self.sort_of(name)]
            self.consts[name] = z3.Const(f"c_{name}{self.ns}", srt)
        return self.consts[name]

    def _well_formed(self):
        top = len(self.prog.events)
        for kv in self.kind:
            self.facts.append(z3.And(kv >= IDLE, kv <= top))
        # the tail is what the handler itself put in the log: pinned, not free
        for offset, atom in enumerate(self.tail):
            i = self.n + offset
            self.facts.append(self.kind[i] == self.index[atom.name])
            ev = self.prog.event(atom.name)
            for j, a in enumerate(atom.args):
                self.facts.append(
                    self.slot[(i, j, ev.params[j].sort)] == self.const(a))

    # ---------------------------------------------------------- semantics
    def occ(self, i, name, args):
        if i < 0 or i >= self.length or name not in self.index:
            return z3.BoolVal(False)
        ev = self.prog.event(name)
        parts = [self.kind[i] == self.index[name]]
        for j, a in enumerate(args):
            parts.append(self.slot[(i, j, ev.params[j].sort)] == self.const(a))
        return _and(parts)

    def at(self, e, i):
        """Truth of `e` considered at instant `i`."""
        if isinstance(e, COcc):
            return self.occ(i, e.name, e.args)
        return self.holds(e, i)

    def domain(self, sort):
        return [f"#{sort}_{i}" for i in range(self.k)]

    def holds(self, e, t):
        """Truth of `e` given the history through position `t` inclusive."""
        if isinstance(e, CLit):
            return z3.BoolVal(e.value)
        if isinstance(e, COcc):
            return self.occ(t, e.name, e.args)
        if isinstance(e, COnce):
            return _or([self.at(e.arg, i) for i in range(t + 1)])
        if isinstance(e, CSinceNot):
            return _or([
                z3.And(self.at(e.left, i),
                       _and([z3.Not(self.at(e.right, j))
                             for j in range(i + 1, t + 1)]))
                for i in range(t + 1)])
        if isinstance(e, CCount):
            if t < 0:
                return _cmp(z3.IntVal(0), e.op, e.n)
            total = z3.Sum([z3.If(self.occ(i, e.name, e.args), 1, 0)
                            for i in range(t + 1)])
            return _cmp(total, e.op, e.n)
        if isinstance(e, CExists):
            return _or([self.holds(subst_vars(e.body, {e.var: d}), t)
                        for d in self.domain(e.sort)])
        if isinstance(e, CCountOver):
            total = z3.Sum([
                z3.If(self.holds(subst_vars(e.body, {e.var: d}), t), 1, 0)
                for d in self.domain(e.sort)])
            return _cmp(total, e.op, e.n)
        if isinstance(e, CNot):
            return z3.Not(self.holds(e.arg, t))
        if isinstance(e, CAnd):
            return z3.And(self.holds(e.left, t), self.holds(e.right, t))
        if isinstance(e, COr):
            return z3.Or(self.holds(e.left, t), self.holds(e.right, t))
        raise TypeError(f"expressao nao codificavel: {e!r}")

    def distinct_pairs(self):
        by_sort = {}
        for name, c in self.consts.items():
            by_sort.setdefault(self.sort_of(name), []).append(c)
        pairs = []
        for group in by_sort.values():
            for i, a in enumerate(group):
                for b in group[i + 1:]:
                    pairs.append((a, b))
        return pairs

    # ------------------------------------------------------------ readout
    def render(self, model) -> List[str]:
        by_index = {v: k for k, v in self.index.items()}
        named = {}
        for n, c in self.consts.items():
            named.setdefault(str(model.eval(c, model_completion=True)),
                             []).append(n)
        out = []
        for i in range(self.length):
            k = model.eval(self.kind[i], model_completion=True).as_long()
            if k == IDLE:
                continue
            name = by_index[k]
            ev = self.prog.event(name)
            shown = []
            for j, param in enumerate(ev.params):
                val = model.eval(self.slot[(i, j, param.sort)],
                                 model_completion=True)
                hit = named.get(str(val))
                shown.append("=".join(hit) if hit else _plain(val))
            if i < self.n:
                tag = ""
            elif name.startswith("@"):
                tag = "   <- fala, registrada porque o elefante nao esquece"
            else:
                tag = "   <- o proprio handler registrou"
            out.append(f"{pretty(name)}({', '.join(shown)}){tag}")
        return out


def _solve(prog, ob, bound, objects, tail, want_goal):
    exprs = ([a.expr for a in ob.assumptions] + [ob.goal.expr]
             + list(tail) + list(ob.appended))
    enc = Encoder(prog, bound, tail, k=objects, exprs=exprs)
    opt = z3.Optimize()
    for f in enc.facts:
        opt.add(f)
    for a in ob.assumptions:
        opt.add(enc.holds(a.expr, enc.n + a.appended - 1))
    goal = enc.holds(ob.goal.expr, enc.n + ob.goal.appended - 1)
    opt.add(goal if want_goal else z3.Not(goal))
    for i in range(enc.n):
        opt.add_soft(enc.kind[i] == IDLE)
    # a counterexample where two distinct roles happen to be the same object is
    # valid but confusing, so prefer models that keep them apart. Soft only:
    # it can never hide a counterexample that needs them equal.
    for a, b in enc.distinct_pairs():
        opt.add_soft(a != b)
    if opt.check() == z3.sat:
        return enc.render(opt.model())
    return None


def bounds_for(ob: Obligation, bound, objects) -> Threshold:
    """Where to look. Left to itself the checker looks exactly as far as it
    must to be exhaustive; an explicit --bound overrides that and gives up the
    completeness claim with it."""
    t = compute_threshold([a.expr for a in ob.assumptions] + [ob.goal.expr],
                          tail_length=len(ob.appended))
    if bound is None and objects is None:
        return t
    return Threshold(
        bound=bound if bound is not None else t.bound,
        objects=objects if objects is not None else t.objects,
        complete=t.complete and (bound is None or bound >= t.bound)
                 and (objects is None or objects >= t.objects),
        reason=t.reason or "limite pedido abaixo do limiar")


def check(prog: A.Program, ob: Obligation, bound=None, objects=None) -> Result:
    t = bounds_for(ob, bound, objects)
    if ob.polarity == "satisfiable":
        r = check_dischargeable(prog, ob, t.bound, t.objects)
    else:
        trace = _solve(prog, ob, t.bound, t.objects, ob.appended,
                       want_goal=False)
        r = Result(ob, ok=trace is None, trace=trace)
    r.threshold = t
    return r


def check_dischargeable(prog, ob, bound, objects) -> Result:
    """A promise about the future is keepable only if some path through the
    program can *bring the promised thing about* -- it must turn false into
    true. A path that merely happens to run while it is already true proves
    nothing, so the history is required to start out falsifying it.

    Here a model is the good news: it is a script for keeping the promise.
    """
    phi = ob.goal.expr
    for path in ob.candidates:
        if not path.tail:
            continue                       # changes nothing, settles nothing
        enc = Encoder(prog, bound, path.tail, k=objects,
                      exprs=[phi] + list(path.tail))
        opt = z3.Optimize()
        for f in enc.facts:
            opt.add(f)
        opt.add(z3.Not(enc.holds(phi, enc.n - 1)))          # false before
        opt.add(enc.holds(phi, enc.length - 1))             # true after
        for i in range(enc.n):
            opt.add_soft(enc.kind[i] == IDLE)
        for a, b in enc.distinct_pairs():
            opt.add_soft(a != b)
        if opt.check() == z3.sat:
            return Result(ob, ok=True,
                          trace=[f"cumprivel por: {path.label}"]
                                + enc.render(opt.model()))
    return Result(ob, ok=False)


def verify(prog: A.Program, analysis: Analysis, bound=None,
           objects=None) -> List[Result]:
    """Leave bound and objects unset to let each obligation be checked at its
    own completeness threshold, which is what makes the result a proof."""
    return [check(prog, ob, bound, objects) for ob in analysis.obligations]

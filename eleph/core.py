"""Canonical form: every predicate reduced to talk only about event occurrences.

Facts are expanded away, quantifiers are kept symbolic (each backend ranges
them over its own domain), and the two readings of an event name are made
explicit. `COcc` is "this event happens at this instant"; `COnce` is "it
happened at some instant in the past". Confusing the two is the bug McCarthy
built the language to catch, so the compiler refuses to leave it implicit.
"""

from dataclasses import dataclass
from typing import Tuple

from . import ast as A

PARTY = "Party"          # built-in sort: whoever the program is talking to
THING = "Thing"          # default sort when nothing is annotated


class CExpr:
    pass


@dataclass(frozen=True)
class COcc(CExpr):
    """Event `name(args)` occurs at this instant."""
    name: str
    args: Tuple[str, ...]


@dataclass(frozen=True)
class COnce(CExpr):
    """`arg` held at some instant at or before now."""
    arg: CExpr


@dataclass(frozen=True)
class CSinceNot(CExpr):
    left: CExpr
    right: CExpr


@dataclass(frozen=True)
class CCount(CExpr):
    name: str
    args: Tuple[str, ...]
    op: str
    n: int


@dataclass(frozen=True)
class CExists(CExpr):
    var: str
    sort: str
    body: CExpr


@dataclass(frozen=True)
class CCountOver(CExpr):
    var: str
    sort: str
    body: CExpr
    op: str
    n: int


@dataclass(frozen=True)
class CNot(CExpr):
    arg: CExpr


@dataclass(frozen=True)
class CAnd(CExpr):
    left: CExpr
    right: CExpr


@dataclass(frozen=True)
class COr(CExpr):
    left: CExpr
    right: CExpr


@dataclass(frozen=True)
class CLit(CExpr):
    value: bool


class ResolveError(Exception):
    pass


def speech_event(performative: str, subject: str) -> str:
    """The synthetic event name under which an utterance is logged.

    The program's own speech is part of the history, exactly as McCarthy
    intended, which is what lets a program ask what it has already said.
    """
    return f"@{performative}:{subject}"


class Resolver:
    def __init__(self, prog: A.Program):
        self.prog = prog

    # ------------------------------------------------------------ entry
    def resolve(self, e: A.TExpr, env: dict, instant=False, stack=(),
                subst=None) -> CExpr:
        """Reduce `e` to canonical form.

        `env` maps variable name -> sort, and is what makes argument order
        checkable. `subst` renames variables when a fact is expanded.
        `instant` selects the instantaneous reading of a bare event name,
        which is what the operands of `since_not` need; everywhere else a bare
        event name means "happened at least once", the reading that lies.
        """
        subst = subst or {}
        r = lambda x, inst=instant, en=env, sb=subst: self.resolve(
            x, en, inst, stack, sb)

        if isinstance(e, A.Lit):
            return CLit(e.value)
        if isinstance(e, A.Not):
            return CNot(r(e.arg))
        if isinstance(e, A.And):
            return CAnd(r(e.left), r(e.right))
        if isinstance(e, A.Or):
            return COr(r(e.left), r(e.right))
        if isinstance(e, A.SinceNot):
            return CSinceNot(r(e.left, True), r(e.right, True))

        if isinstance(e, A.Exists):
            self.known_sort(e.sort)
            inner = dict(env, **{e.var: e.sort})
            return CExists(e.var, e.sort,
                           self.resolve(e.body, inner, False, stack, subst))

        if isinstance(e, A.CountOver):
            self.known_sort(e.sort)
            inner = dict(env, **{e.var: e.sort})
            return CCountOver(e.var, e.sort,
                              self.resolve(e.body, inner, False, stack, subst),
                              e.op, e.n)

        if isinstance(e, A.Spoke):
            return self.resolve_spoke(e, env, instant, subst)

        if isinstance(e, A.Count):
            ev = self.prog.event(e.atom.name)
            if not ev:
                raise ResolveError(
                    f"count so vale para evento declarado, e {e.atom.name!r} nao e")
            args = self.check_args(e.atom, ev.params, env, subst)
            return CCount(e.atom.name, args, e.op, e.n)

        if isinstance(e, A.Ref):
            return self.resolve_ref(e, env, instant, stack, subst)

        raise ResolveError(f"expressao desconhecida: {e!r}")

    # ------------------------------------------------------------ pieces
    def resolve_spoke(self, e: A.Spoke, env, instant, subst):
        target = self.prog.event(e.atom.name) or self.prog.fact(e.atom.name)
        if target is None:
            raise ResolveError(
                f"{e.atom.name!r} nao e evento nem fato declarado")
        args = self.check_args(e.atom, target.params, env, subst)
        party = subst.get(e.party, e.party)
        self.expect_sort(party, PARTY, env,
                         f"em 'spoke {e.performative} to {e.party}'")
        name = speech_event(e.performative, e.atom.name)
        self.prog.ensure_event(
            name, [A.Param("party", PARTY)] + list(target.params))
        occ = COcc(name, (party,) + args)
        return occ if instant else COnce(occ)

    def resolve_ref(self, r: A.Ref, env, instant, stack, subst) -> CExpr:
        ev = self.prog.event(r.name)
        if ev:
            args = self.check_args(r, ev.params, env, subst)
            occ = COcc(r.name, args)
            return occ if instant else COnce(occ)

        ft = self.prog.fact(r.name)
        if ft:
            if r.name in stack:
                raise ResolveError(f"fato {r.name} e recursivo")
            args = self.check_args(r, ft.params, env, subst)
            inner_env = dict(env)
            inner_subst = {}
            for param, actual in zip(ft.params, args):
                inner_subst[param.name] = actual
                inner_env[actual] = param.sort
            return self.resolve(ft.body, inner_env, instant,
                                stack + (r.name,), inner_subst)

        raise ResolveError(f"{r.name!r} nao e evento nem fato declarado")

    # ------------------------------------------------------------- checks
    def check_args(self, ref: A.Ref, params, env, subst) -> Tuple[str, ...]:
        if len(ref.args) != len(params):
            raise ResolveError(
                f"{ref.name} espera {len(params)} argumentos, "
                f"recebeu {len(ref.args)}")
        out = []
        for actual, param in zip(ref.args, params):
            name = subst.get(actual, actual)
            self.expect_sort(name, param.sort, env,
                             f"no argumento {param.name!r} de {ref.name}")
            out.append(name)
        return tuple(out)

    def expect_sort(self, name, wanted, env, context):
        have = env.get(name)
        if have is None or wanted == THING or have == THING:
            return
        if have != wanted:
            raise ResolveError(
                f"{context}: {name!r} e do tipo {have}, esperava {wanted}")

    def known_sort(self, name):
        if name in (PARTY, THING):
            return
        if name not in [s.name for s in self.prog.sorts]:
            raise ResolveError(f"tipo {name!r} nao declarado (use 'sort {name}')")


# --------------------------------------------------------------- utilities

def subst_vars(e: CExpr, mapping: dict) -> CExpr:
    """Rename free variables. Used to expand a quantifier over a domain."""
    def go(x):
        if isinstance(x, COcc):
            return COcc(x.name, tuple(mapping.get(a, a) for a in x.args))
        if isinstance(x, CCount):
            return CCount(x.name, tuple(mapping.get(a, a) for a in x.args),
                          x.op, x.n)
        if isinstance(x, COnce):
            return COnce(go(x.arg))
        if isinstance(x, CNot):
            return CNot(go(x.arg))
        if isinstance(x, CAnd):
            return CAnd(go(x.left), go(x.right))
        if isinstance(x, COr):
            return COr(go(x.left), go(x.right))
        if isinstance(x, CSinceNot):
            return CSinceNot(go(x.left), go(x.right))
        if isinstance(x, CExists):
            inner = {k: v for k, v in mapping.items() if k != x.var}
            return CExists(x.var, x.sort, subst_vars(x.body, inner))
        if isinstance(x, CCountOver):
            inner = {k: v for k, v in mapping.items() if k != x.var}
            return CCountOver(x.var, x.sort, subst_vars(x.body, inner),
                              x.op, x.n)
        return x
    return go(e)


def _walk(e: CExpr):
    yield e
    for attr in ("arg", "left", "right", "body"):
        child = getattr(e, attr, None)
        if isinstance(child, CExpr):
            yield from _walk(child)


def variables(e: CExpr):
    out = set()
    for node in _walk(e):
        if isinstance(node, (COcc, CCount)):
            out |= set(node.args)
        if isinstance(node, (CExists, CCountOver)):
            out.discard(node.var)
    return out


def events_used(e: CExpr):
    return {n.name for n in _walk(e) if isinstance(n, (COcc, CCount))}


def show(e: CExpr) -> str:
    if isinstance(e, COcc):
        return f"{pretty(e.name)}({', '.join(e.args)})"
    if isinstance(e, COnce):
        return f"alguma vez {show(e.arg)}"
    if isinstance(e, CSinceNot):
        return f"({show(e.left)} e desde entao nenhum {show(e.right)})"
    if isinstance(e, CCount):
        return f"count {e.name}({', '.join(e.args)}) {e.op} {e.n}"
    if isinstance(e, CExists):
        return f"existe {e.var}: {e.sort} com {show(e.body)}"
    if isinstance(e, CCountOver):
        return (f"quantos {e.var}: {e.sort} com {show(e.body)} "
                f"{e.op} {e.n}")
    if isinstance(e, CNot):
        return f"nao {show(e.arg)}"
    if isinstance(e, CAnd):
        return f"({show(e.left)} e {show(e.right)})"
    if isinstance(e, COr):
        return f"({show(e.left)} ou {show(e.right)})"
    if isinstance(e, CLit):
        return "sim" if e.value else "nao"
    return repr(e)


def pretty(event_name: str) -> str:
    """`@promise:has_reservation` reads better as `disse promise sobre ...`."""
    if event_name.startswith("@"):
        perf, _, subject = event_name[1:].partition(":")
        return f"disse-{perf}-sobre-{subject}"
    return event_name

"""Constant-time evaluation of the past, without keeping any state of its own.

The obvious objection to a language whose only state is its history is that
answering a question means reading the history. That is quadratic, and a
program meant to run forever cannot pay it.

It does not have to. Every temporal operator here has a one-step recurrence:

    once(x)@t          =  x@t  or  once(x)@(t-1)
    (a since_not b)@t  =  a@t  or  ((a since_not b)@(t-1) and not b@t)
    count(a)@t         =  count(a)@(t-1) + [a@t]

This is the dynamic-programming translation of past-time temporal logic
(Havelund and Rosu, 2001). What it buys here is sharper than linear, because
of one lemma:

    LEMMA (locality). If an event matches none of a subformula's atoms, the
    subformula's value is unchanged.

    Proof. Read the recurrences with x@t = a@t = false: `once` keeps its value,
    `since_not` keeps its value (b@t is false, so the conjunct survives), and
    the count increments by zero. []

So an event only disturbs the keys it names, and there are at most as many of
those as the event has arguments. Updating is O(1) in the length of the log.

None of this is state in the sense the language forbids. Every cell is a pure
function of the log -- the same function the naive evaluator computes by
rereading it. `tests/test_incremental.py` holds the two evaluators against each
other on random histories, which is the only reason to believe this file.
"""

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, Optional, Set, Tuple

from . import ast as _ast
from .core import (CExpr, COcc, COnce, CSinceNot, CCount, CExists, CCountOver,
                   CNot, CAnd, COr, CLit)


@lru_cache(maxsize=None)
def free_vars(e: CExpr) -> Tuple[str, ...]:
    """Variable names the expression's atoms mention, in a stable order."""
    out = []

    def go(x, bound):
        if isinstance(x, (COcc, CCount)):
            for a in x.args:
                # a numeric comparison binds nothing: it is part of the
                # pattern, not a variable the key is built from
                if isinstance(a, str) and a not in bound and a not in out:
                    out.append(a)
        elif isinstance(x, (COnce, CNot)):
            go(x.arg, bound)
        elif isinstance(x, (CAnd, COr, CSinceNot)):
            go(x.left, bound)
            go(x.right, bound)
        elif isinstance(x, (CExists, CCountOver)):
            go(x.body, bound | {x.var})

    go(e, set())
    return tuple(out)


@lru_cache(maxsize=None)
def _atoms_cached(e: CExpr):
    return tuple(_atoms_gen(e))


def atoms_of(e: CExpr):
    return _atoms_cached(e)


def _atoms_gen(e: CExpr):
    if isinstance(e, COcc):
        yield e
    elif isinstance(e, CCount):
        yield COcc(e.name, e.args)
    elif isinstance(e, (COnce, CNot)):
        yield from _atoms_gen(e.arg)
    elif isinstance(e, (CAnd, COr, CSinceNot)):
        yield from _atoms_gen(e.left)
        yield from _atoms_gen(e.right)
    elif isinstance(e, (CExists, CCountOver)):
        yield from _atoms_gen(e.body)


def _subnodes(e: CExpr):
    """Every expression node at or under `e`."""
    yield e
    for attr in ("arg", "left", "right", "body"):
        child = getattr(e, attr, None)
        if isinstance(child, CExpr):
            yield from _subnodes(child)


@lru_cache(maxsize=None)
def false_when_absent(e: CExpr) -> bool:
    """True when an object that never occurs cannot satisfy `e`.

    Read the formula with every atom false and every count zero, which is what
    the log says about an object it has never seen.

    This is the corollary the threshold relies on, checked rather than assumed:
    an object with no occurrence falsifies every atom naming it, so it can
    neither witness an existential nor add to a count. Under a negation it does
    not hold. `not e(B)` is true of every object the log has never mentioned,
    and such an object joins the domain the moment any unrelated event names
    it, which is a change no atom of this node witnesses.
    """
    if isinstance(e, CLit):
        return not e.value
    if isinstance(e, (COcc, COnce, CSinceNot)):
        return True
    if isinstance(e, CCount):
        return not compare(0, e.op, e.n)
    if isinstance(e, CCountOver):
        return not compare(0, e.op, e.n)
    if isinstance(e, CExists):
        return True
    if isinstance(e, CNot):
        return not false_when_absent(e.arg)
    if isinstance(e, CAnd):
        return false_when_absent(e.left) or false_when_absent(e.right)
    if isinstance(e, COr):
        return false_when_absent(e.left) and false_when_absent(e.right)
    return False          # unknown shape: assume the worst


@lru_cache(maxsize=None)
def accumulable(e: CExpr) -> bool:
    """True when every `since_not` here takes atoms on both sides.

    `_feed_accumulator` folds an event into a `since_not` by asking whether the
    event matches its left operand and whether it matches its right one, and
    `match` is defined on atoms. A compound operand has no name to match
    against: `(a or b)` under a `since_not` is outside what one step of the
    recurrence can decide from the event alone.

    That case is the same one the threshold calls outside the linear fragment,
    and it is answered the same way: the program still runs, by rereading the
    log, and `Index.usable` says so. Before this check the index accepted the
    formula and raised on the first event, which is the one behaviour neither
    the fast path nor the slow one is allowed to have.
    """
    if isinstance(e, CSinceNot):
        if not (isinstance(e.left, COcc) and isinstance(e.right, COcc)):
            return False
    for attr in ("arg", "left", "right", "body"):
        child = getattr(e, attr, None)
        if isinstance(child, CExpr) and not accumulable(child):
            return False
    return True


@lru_cache(maxsize=None)
def local(e: CExpr) -> bool:
    """True when every atom under each accumulating node names the same
    variables -- the condition that makes an event's blast radius finite.

    A subformula that mentions fewer variables than its parent would let one
    event disturb unboundedly many keys, and the locality lemma would not
    apply. Such a program still runs; it just runs the slow way.
    """
    if isinstance(e, (COnce, CSinceNot, CCount)):
        want = free_vars(e)
        return all(free_vars(a) == want for a in atoms_of(e))
    if isinstance(e, (CExists, CCountOver)):
        # The index keeps one instance of the body per candidate object, and
        # `_feed_quantified` only revisits the instances an event names. An
        # atom under the quantifier that does not mention the bound variable
        # changes the body for *every* object at once, and no event would ever
        # name them, so the tally silently stops moving. This is the locality
        # lemma failing at a quantifier rather than at an accumulator, and it
        # was missed because the check below only recurses into the body.
        # A quantifier inside a quantifier is outside what this index keeps.
        # Its instances are keyed by one variable, and the inner tally for a
        # given object depends on every object of the inner sort, so the
        # before-and-after snapshot the fold takes is keyed too finely to see
        # the change. Such a program still runs, by rereading the log.
        if any(isinstance(n, (CExists, CCountOver)) for n in _subnodes(e.body)):
            return False
        # The same rule the accumulators above are held to: every atom under
        # the node names the same variables. One naming fewer, or naming a
        # different set, makes an event's blast radius depend on a variable the
        # key does not carry.
        shapes = {free_vars(a) for a in atoms_of(e.body)}
        if len(shapes) > 1:
            return False
        if not all(e.var in shape for shape in shapes):
            return False
        # And an object the log has never seen must not satisfy the body: it
        # joins the domain through an event this node's atoms never witness,
        # and the tally would move with nothing to move it.
        if not false_when_absent(e.body):
            return False
    for attr in ("arg", "left", "right", "body"):
        child = getattr(e, attr, None)
        if isinstance(child, CExpr) and not local(child):
            return False
    return True


def match(atom: COcc, name: str, args: Tuple[str, ...]) -> Optional[dict]:
    """Bind the atom's variables to an event's arguments, or fail."""
    if atom.name != name or len(atom.args) != len(args):
        return None
    binding = {}
    for var, value in zip(atom.args, args):
        if isinstance(var, _ast.Bound):
            try:
                if not compare(int(value), var.op, var.n):
                    return None
            except (TypeError, ValueError):
                return None
            continue
        if binding.setdefault(var, value) != value:
            return None          # a repeated variable must agree with itself
    return binding


@dataclass
class Index:
    """The running value of every tracked subformula, keyed by binding."""

    once: Dict[CExpr, Dict[tuple, bool]] = field(default_factory=dict)
    since: Dict[CExpr, Dict[tuple, bool]] = field(default_factory=dict)
    counts: Dict[CExpr, Dict[tuple, int]] = field(default_factory=dict)
    witnesses: Dict[CExpr, Dict[tuple, Set[str]]] = field(default_factory=dict)
    tracked: Dict[CExpr, CExpr] = field(default_factory=dict)
    usable: bool = True
    _before: Dict[tuple, bool] = field(default_factory=dict)

    # ------------------------------------------------------------- tracking
    def track(self, e: CExpr):
        if not local(e) or not accumulable(e):
            self.usable = False
            return
        for node in self._nodes(e):
            i = node
            self.tracked[i] = node
            if isinstance(node, COnce):
                self.once.setdefault(i, {})
            elif isinstance(node, CSinceNot):
                self.since.setdefault(i, {})
            elif isinstance(node, CCount):
                self.counts.setdefault(i, {})
            elif isinstance(node, (CExists, CCountOver)):
                self.witnesses.setdefault(i, {})

    @staticmethod
    def _nodes(e: CExpr):
        yield e
        for attr in ("arg", "left", "right", "body"):
            child = getattr(e, attr, None)
            if isinstance(child, CExpr):
                yield from Index._nodes(child)

    # ---------------------------------------------------------------- query
    def value(self, e: CExpr, binding: dict):
        """The truth of `e` now, read rather than recomputed."""
        i = e
        if isinstance(e, CLit):
            return e.value
        if isinstance(e, COnce):
            return self.once[i].get(self._key(e, binding), False)
        if isinstance(e, CSinceNot):
            return self.since[i].get(self._key(e, binding), False)
        if isinstance(e, CCount):
            n = self.counts[i].get(self._key(e, binding), 0)
            return compare(n, e.op, e.n)
        if isinstance(e, CExists):
            return bool(self.witnesses[i].get(self._outer(e, binding), ()))
        if isinstance(e, CCountOver):
            n = len(self.witnesses[i].get(self._outer(e, binding), ()))
            return compare(n, e.op, e.n)
        if isinstance(e, CNot):
            return not self.value(e.arg, binding)
        if isinstance(e, CAnd):
            return self.value(e.left, binding) and self.value(e.right, binding)
        if isinstance(e, COr):
            return self.value(e.left, binding) or self.value(e.right, binding)
        if isinstance(e, COcc):
            return False          # an instant, and this instant has passed
        raise TypeError(f"nao indexavel: {e!r}")

    @staticmethod
    def _key(e, binding):
        return tuple(binding.get(v, v) for v in free_vars(e))

    @staticmethod
    def _outer(e, binding):
        return tuple(binding.get(v, v)
                     for v in free_vars(e) if v != e.var)

    # ----------------------------------------------------------- the update
    def feed(self, name: str, args: Tuple[str, ...]):
        """Fold one event in. Only the keys the event names can move."""
        if not self.usable:
            return
        self._before.clear()
        for node in self.tracked.values():
            if isinstance(node, (CExists, CCountOver)):
                self._feed_quantified(node, name, args)
        for node in self.tracked.values():
            if isinstance(node, (COnce, CSinceNot, CCount)):
                self._feed_accumulator(node, name, args)
        for node in self.tracked.values():
            if isinstance(node, (CExists, CCountOver)):
                self._settle_quantified(node, name, args)

    def _bindings(self, node, name, args):
        """Every way this event touches this node."""
        out = []
        for atom in atoms_of(node):
            b = match(atom, name, args)
            if b is not None and b not in out:
                out.append(b)
        return out

    def _feed_accumulator(self, node, name, args):
        i = node
        for b in self._bindings(node, name, args):
            key = self._key(node, b)
            if isinstance(node, COnce):
                hit = any(match(a, name, args) is not None
                          for a in atoms_of(node.arg))
                self.once[i][key] = self.once[i].get(key, False) or hit
            elif isinstance(node, CSinceNot):
                left = match(node.left, name, args) is not None
                right = match(node.right, name, args) is not None
                prev = self.since[i].get(key, False)
                self.since[i][key] = left or (prev and not right)
            elif isinstance(node, CCount):
                if match(COcc(node.name, node.args), name, args) is not None:
                    self.counts[i][key] = self.counts[i].get(key, 0) + 1

    # A quantified node's tally moves only when one of its instances flips, so
    # we look at the instances the event names, before and after.
    def _feed_quantified(self, node, name, args):
        for b in self._bindings(node, name, args):
            if node.var not in b:
                continue
            self._before[(node, tuple(sorted(b.items())))] = \
                self.value(node.body, b)

    def _settle_quantified(self, node, name, args):
        i = node
        for b in self._bindings(node, name, args):
            if node.var not in b:
                continue
            before = self._before.get((i, tuple(sorted(b.items()))), False)
            after = self.value(node.body, b)
            if before == after:
                continue
            bucket = self.witnesses[i].setdefault(self._outer(node, b), set())
            bucket.add(b[node.var]) if after else bucket.discard(b[node.var])


def compare(n, op, k):
    return {"<": n < k, "<=": n <= k, ">": n > k,
            ">=": n >= k, "==": n == k, "!=": n != k}[op]

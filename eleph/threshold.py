"""Completeness thresholds: when "no counterexample found" becomes "none exists".

Bounded model checking answers a weaker question than we want. It says no
history of length <= N breaks the obligation; it does not say no history does.
For this language's fragment that gap closes, and the argument is short enough
to state.

    LEMMA (last-occurrence abstraction).
    Let phi be built from event atoms by once, since_not, count, the boolean
    connectives, and quantification over a sort, with the operands of every
    since_not being atoms. Then the truth of phi at the end of a history H
    depends only on
        (a) the relative order of the LAST occurrence of each atom of phi, and
        (b) the number of occurrences of each atom that sits under a count,
            capped at n+1.

    Proof. Structural induction. `once(a)` is [last(a) exists]. `since_not(a,b)`
    is exactly [last(a) exists and (last(b) absent or last(b) < last(a))] --
    an `a` after the final `b`. `count(a) op n` reads (b) directly. The boolean
    connectives compose, and a quantifier is a finite disjunction or sum of
    instances that are themselves in the fragment.

    THEOREM (threshold). Every abstraction admitted by the lemma is realised by
    some history of length at most

        N  =  sum over DISTINCT atoms a of k(a),  k(a) = 1, or n_max(a)+1
              under a count

    -- place the required occurrences of each atom, with the last of each in
    its required order position -- so unsatisfiability up to N implies
    unsatisfiability outright.

    The sum runs over distinct atoms and takes the largest demand made of each,
    not over syntax nodes: `once(a) and count(a) > 2` asks for one occurrence
    and for three, and three occurrences answer both. Counting per node instead
    is still a valid threshold, just a needlessly large one -- and large
    thresholds are what make an exhaustive run unaffordable.

    COROLLARY (domain). An object with no occurrence in H falsifies every atom
    naming it, so it can neither witness an existential nor add to a count.
    Quantifying over the objects that appear in H is therefore the same as
    quantifying over an unbounded universe, and W distinct objects suffice,
    where W counts one witness per existential and n+1 per counting quantifier,
    plus the obligation's own free variables.

The hypothesis that since_not takes atoms is the one that can fail: a fact
whose body puts a compound formula there leaves the fragment. That case does
not lose completeness, only its linear bound:

    THEOREM (general threshold). Every past operator here has a one-step
    recurrence -- `once` and `since_not` each carry one bit, `count` a counter
    saturating at n+1 -- so a formula with k temporal subformulas is evaluated
    by a deterministic monitor over

        S  =  2^k  x  product of (n_i + 2)

    states, and whether it holds at the end of a history is a function of the
    state reached. If some history reaches a violating state, one does so
    without repeating a state, hence in fewer than S steps. So S is a
    completeness threshold for the whole language.

    Quantifiers multiply k by the domain size, since an instance per object is
    tracked. That is exponential, and honestly so: when S exceeds what is
    worth solving, the checker says the run was not exhaustive instead of
    pretending otherwise.

The linear threshold is the one that makes the tool usable; the general one is
what stops "outside the fragment" from meaning "unverifiable".
"""

CEILING = 4096      # beyond this an exhaustive run is not worth the wait

from dataclasses import dataclass

from .core import (CExpr, COcc, COnce, CSinceNot, CCount, CExists, CCountOver,
                   CNot, CAnd, COr, CLit, variables)


def in_fragment(e: CExpr) -> bool:
    """True when the last-occurrence abstraction applies to `e`."""
    if isinstance(e, CSinceNot):
        return (isinstance(e.left, COcc) and isinstance(e.right, COcc))
    for attr in ("arg", "left", "right", "body"):
        child = getattr(e, attr, None)
        if isinstance(child, CExpr) and not in_fragment(child):
            return False
    return True


def atom_demands(e: CExpr, factor: int = 1) -> dict:
    """The largest number of occurrences each distinct atom is asked for.

    `factor` carries the witness multiplicity of an enclosing counting
    quantifier: `count P where phi(P) >= n` needs n+1 separate objects, each
    with its own occurrences of phi's atoms.
    """
    out = {}

    def bump(key, want):
        out[key] = max(out.get(key, 0), want)

    def go(x, mult):
        if isinstance(x, COcc):
            bump((x.name, x.args), mult)
        elif isinstance(x, CCount):
            bump((x.name, x.args), (x.n + 1) * mult)
        elif isinstance(x, (COnce, CNot)):
            go(x.arg, mult)
        elif isinstance(x, (CAnd, COr, CSinceNot)):
            go(x.left, mult)
            go(x.right, mult)
        elif isinstance(x, CExists):
            go(x.body, mult)
        elif isinstance(x, CCountOver):
            go(x.body, mult * (x.n + 1))

    go(e, factor)
    return out


def history_slots(e: CExpr) -> int:
    """How many event positions are needed to realise any abstraction of `e`."""
    return sum(atom_demands(e).values())


def witnesses(e: CExpr) -> int:
    """How many distinct objects the quantifiers of `e` can ever need."""
    if isinstance(e, (COcc, CCount, CLit)):
        return 0
    if isinstance(e, (COnce, CNot)):
        return witnesses(e.arg)
    if isinstance(e, (CAnd, COr, CSinceNot)):
        return witnesses(e.left) + witnesses(e.right)
    if isinstance(e, CExists):
        return 1 + witnesses(e.body)
    if isinstance(e, CCountOver):
        return (e.n + 1) + witnesses(e.body)
    return 0


def temporal_nodes(e: CExpr) -> int:
    """How many bits of history an incremental monitor of `e` would carry."""
    here = 1 if isinstance(e, (COnce, CSinceNot)) else 0
    for attr in ("arg", "left", "right", "body"):
        child = getattr(e, attr, None)
        if isinstance(child, CExpr):
            here += temporal_nodes(child)
    return here


def count_ranges(e: CExpr):
    out = []
    if isinstance(e, (CCount, CCountOver)):
        out.append(e.n + 2)
    for attr in ("arg", "left", "right", "body"):
        child = getattr(e, attr, None)
        if isinstance(child, CExpr):
            out += count_ranges(child)
    return out


def quantifier_depth(e: CExpr) -> int:
    here = 1 if isinstance(e, (CExists, CCountOver)) else 0
    deepest = 0
    for attr in ("arg", "left", "right", "body"):
        child = getattr(e, attr, None)
        if isinstance(child, CExpr):
            deepest = max(deepest, quantifier_depth(child))
    return here + deepest


def monitor_states(exprs, objects: int) -> int:
    """Size of the state space a monitor of these formulas would explore."""
    total = 1
    for e in exprs:
        bits = temporal_nodes(e) * max(1, objects ** quantifier_depth(e))
        if bits > 20:                     # 2**bits would overflow any patience
            return CEILING + 1
        total *= 2 ** bits
        for r in count_ranges(e):
            total *= r
        if total > CEILING:
            return CEILING + 1
    return total


@dataclass
class Threshold:
    bound: int
    objects: int
    complete: bool
    reason: str = ""

    def label(self):
        if self.complete:
            return (f"limiar de completude: {self.bound} eventos, "
                    f"{self.objects} objetos -- exaustivo")
        return (f"limite: {self.bound} eventos, {self.objects} objetos "
                f"-- nao exaustivo ({self.reason})")


def compute(exprs, tail_length=0, floor_bound=1, floor_objects=1) -> Threshold:
    """The bounds at which a bounded check becomes a decision procedure."""
    exprs = [e for e in exprs if isinstance(e, CExpr)]
    complete = all(in_fragment(e) for e in exprs)

    free = set()
    for e in exprs:
        free |= variables(e)
    objects = max(sum(witnesses(e) for e in exprs) + len(free), floor_objects)

    if complete:
        # one pool of atoms across the whole obligation, not one per formula
        pooled = {}
        for e in exprs:
            for key, want in atom_demands(e).items():
                pooled[key] = max(pooled.get(key, 0), want)
        bound = sum(pooled.values()) + tail_length
        return Threshold(max(bound, floor_bound), objects, True)

    # outside the linear fragment, fall back on the monitor's state space
    states = monitor_states(exprs, objects)
    if states <= CEILING:
        return Threshold(max(states + tail_length, floor_bound), objects, True,
                         reason="limiar geral (espaco de estados do monitor)")

    bound = sum(history_slots(e) for e in exprs) + tail_length
    return Threshold(
        max(bound, floor_bound), objects, False,
        reason=f"espaco de estados acima de {CEILING}; corrido sem exaustao")

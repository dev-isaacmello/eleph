"""The index is an optimisation, and an optimisation of a truth claim is a
place to hide a lie. So it is never trusted: it is checked against the log.

`Machine(audit=True)` evaluates every query twice -- once by reading the index,
once by rereading the whole history -- and raises if they ever differ. These
tests run that over random pasts and random conversations. The claim under
test is that the index is a pure function of the log, computing exactly what
the naive evaluator computes.
"""

import pathlib
import random

import pytest

from eleph.core import Resolver
from eleph.incremental import Index, local, free_vars
from eleph.parser import parse
from eleph.runtime import Event, Machine, Refusal, session

EX = pathlib.Path(__file__).parent.parent / "examples"
POOL = {"Passenger": ["alice", "bruno", "carla"],
        "Flight": ["ba117", "lh42"],
        "Party": ["alice", "bruno", "carla"],
        "Thing": ["alice", "bruno", "ba117", "lh42"]}

PROGRAMS = ["airline.eleph", "booking.eleph", "companhia.eleph"]


def prog_of(name):
    return parse((EX / name).read_text())


def random_event(rng, prog):
    ev = rng.choice([e for e in prog.events if not e.synthetic])
    return Event(ev.name, tuple(rng.choice(POOL.get(p.sort, POOL["Thing"]))
                                for p in ev.params))


def random_turn(rng, prog):
    h = rng.choice(prog.handlers)
    decl = prog.event(h.subject.name) or prog.fact(h.subject.name)
    args = tuple(rng.choice(POOL.get(p.sort, POOL["Thing"]))
                 for p in (decl.params if decl else []))
    return h.performative, rng.choice(POOL["Party"]), h.subject.name, args


# ------------------------------------------------------- index vs the log

@pytest.mark.parametrize("name", PROGRAMS)
def test_index_agrees_with_the_log_under_random_play(name):
    """Every query answered twice, both ways, a few thousand times."""
    rng = random.Random(hash(name) % 10_000)
    for trial in range(60):
        prog = prog_of(name)
        m = Machine(prog, audit=True)
        assert m.index.usable, f"{name} deveria ser indexavel"
        for _ in range(rng.randrange(12)):
            m.append(random_event(rng, prog))
        for _ in range(8):
            try:
                m.deliver(*random_turn(rng, prog))
            except Refusal:
                pass          # a refusal is a verdict, not a disagreement


@pytest.mark.parametrize("name", ["airline_buggy.eleph", "booking_buggy.eleph",
                                  "fundo.eleph"])
def test_index_agrees_even_where_the_program_is_wrong(name):
    """A broken program must break the same way through either evaluator."""
    rng = random.Random(7)
    for _ in range(60):
        prog = prog_of(name)
        m = Machine(prog, audit=True)
        for _ in range(rng.randrange(10)):
            m.append(random_event(rng, prog))
        try:
            for _ in range(5):
                m.deliver(*random_turn(rng, prog))
        except Refusal:
            pass


@pytest.mark.parametrize("name", PROGRAMS)
def test_index_agrees_over_a_long_history(name):
    """Agreement must not decay as the log grows; that is where drift lives."""
    rng = random.Random(99)
    prog = prog_of(name)
    m = Machine(prog, audit=True)
    for i in range(1200):
        if i % 4:
            m.append(random_event(rng, prog))
        else:
            try:
                m.deliver(*random_turn(rng, prog))
            except Refusal:
                pass
    assert len(m.log) > 1000


# ------------------------------------------------------- the recurrences

def test_since_not_recurrence_tracks_the_latest_occurrence():
    prog = prog_of("companhia.eleph")
    res = Resolver(prog)
    phi = res.resolve(prog.fact("has_reservation").body,
                      {"P": "Passenger", "F": "Flight"})
    ix = Index()
    ix.track(phi)
    b = {"P": "alice", "F": "ba117"}
    seen = []
    for name, args in [("make_reservation", ("alice", "ba117")),
                       ("cancel_reservation", ("alice", "ba117")),
                       ("make_reservation", ("alice", "ba117")),
                       ("make_reservation", ("bruno", "ba117")),
                       ("cancel_reservation", ("bruno", "ba117"))]:
        ix.feed(name, args)
        seen.append(ix.value(phi, b))
    assert seen == [True, False, True, True, True]   # bruno never touches alice


def test_counting_quantifier_tracks_a_running_tally():
    prog = prog_of("companhia.eleph")
    res = Resolver(prog)
    phi = res.resolve(prog.fact("seats_left").body, {"F": "Flight"})
    ix = Index()
    ix.track(phi)
    b = {"F": "ba117"}
    assert ix.value(phi, b) is True              # capacity 2, nobody booked
    ix.feed("make_reservation", ("alice", "ba117"))
    assert ix.value(phi, b) is True
    ix.feed("make_reservation", ("bruno", "ba117"))
    assert ix.value(phi, b) is False             # full
    ix.feed("cancel_reservation", ("alice", "ba117"))
    assert ix.value(phi, b) is True              # a seat came back


def test_another_flight_does_not_consume_this_ones_seats():
    prog = prog_of("companhia.eleph")
    res = Resolver(prog)
    phi = res.resolve(prog.fact("seats_left").body, {"F": "Flight"})
    ix = Index()
    ix.track(phi)
    for p in ("alice", "bruno", "carla"):
        ix.feed("make_reservation", (p, "lh42"))
    assert ix.value(phi, {"F": "ba117"}) is True
    assert ix.value(phi, {"F": "lh42"}) is False


# ------------------------------------------------- when locality fails

def test_a_non_local_formula_is_detected_and_the_index_stands_down():
    """A subformula naming fewer variables than its parent lets one event
    disturb unboundedly many keys. The index refuses rather than guess."""
    prog = parse("""program p
sort S
event a(x: S)
event global()
fact odd(X: S) := a(X) and global()
fact stale(X: S) := odd(X) since_not a(X)

on question(C, stale(X)):
    answer C with stale(X)
""")
    res = Resolver(prog)
    phi = res.resolve(prog.fact("stale").body, {"X": "S"})
    assert not local(phi)
    ix = Index()
    ix.track(phi)
    assert not ix.usable

    m = Machine(prog)
    assert not m.index.usable          # falls back to rereading the log


def test_the_fallback_still_answers_correctly():
    prog = parse("""program p
sort S
event a(x: S)
event global()
fact odd(X: S) := a(X) and global()
fact stale(X: S) := odd(X) since_not a(X)

on question(C, stale(X)):
    answer C with stale(X)
""")
    m = session(prog, """
        given a(s1)
        given global()
        question alice stale(s1)
    """)
    assert not m.index.usable
    assert any("programa: yes" in l or "programa: no" in l
               for l in m.transcript)


# -------------------------------------------------------- free variables

def test_free_vars_ignores_bound_ones():
    prog = prog_of("companhia.eleph")
    res = Resolver(prog)
    phi = res.resolve(prog.fact("seats_left").body, {"F": "Flight"})
    assert free_vars(phi) == ("F",)          # P is bound by the quantifier


# --------------------------------------------------------------------------
# A `since_not` whose operand is compound leaves what one step of the
# recurrence can decide. The index used to accept the formula and raise on the
# first event, which is the one behaviour neither path is allowed to have:
# the fast path must be right, the slow path must be available, and neither
# may be a crash.
# --------------------------------------------------------------------------

COMPOUND = """
program repro
sort Coisa
event pos(c: Coisa)
event neg_a(c: Coisa)
event neg_b(c: Coisa)

fact vale(C: Coisa) := pos(C) since_not (neg_a(C) or neg_b(C))

on question(Q, vale(C)):
    answer Q with vale(C)
"""

EQUIVALENT = """
program contorno
sort Coisa
event pos(c: Coisa)
event neg_a(c: Coisa)
event neg_b(c: Coisa)

fact vale(C: Coisa) := (pos(C) since_not neg_a(C)) and (pos(C) since_not neg_b(C))

on question(Q, vale(C)):
    answer Q with vale(C)
"""


def test_compound_since_not_declines_the_index_instead_of_raising():
    from eleph import Policy

    g = Policy(COMPOUND).guard()
    assert g.machine.index.usable is False

    # And it still answers, by rereading the log.
    g.record("pos", "x")
    assert g.holds("vale", "x") is True
    g.record("neg_a", "x")
    assert g.holds("vale", "x") is False
    g.record("pos", "x")
    assert g.holds("vale", "x") is True
    g.record("neg_b", "x")
    assert g.holds("vale", "x") is False


def test_atom_operands_still_take_the_fast_path():
    from eleph import Policy

    assert Policy(EQUIVALENT).guard().machine.index.usable is True


def test_the_slow_path_agrees_with_the_atom_rewrite():
    """`p since_not (a or b)` is `(p since_not a) and (p since_not b)`.

    There is a p after the last of a and b exactly when there is a p after each
    of them. Checked exhaustively rather than argued: every history of up to
    six events over the three event names."""
    import itertools

    from eleph import Policy

    compound, rewritten = Policy(COMPOUND), Policy(EQUIVALENT)
    for n in range(1, 7):
        for history in itertools.product(["pos", "neg_a", "neg_b"], repeat=n):
            a, b = compound.guard(), rewritten.guard()
            for event in history:
                a.record(event, "x")
                b.record(event, "x")
            assert a.holds("vale", "x") == b.holds("vale", "x"), history


# --------------------------------------------------------------------------
# Four ways the index accepted a formula it could not keep.
#
# Each was found by generating valid programs at random and running every one
# under `audit=True`, which answers each query both ways. The first raised; the
# other three returned a wrong answer in silence, which is worse. All four are
# the same shape of mistake: a soundness check that did not cover a node type.
# --------------------------------------------------------------------------

def _guard(fact, extra_events=""):
    from eleph import Policy

    src = (
        "program m\nsort S\nsort T\n"
        "event e(p: S)\nevent o(p: S)\nevent d(p: S, q: S)\n"
        f"{extra_events}"
        f"{fact}\n"
        "on question(Q, f(A)):\n    answer Q with f(A)\n"
    )
    return Policy(src).guard(audit=True)


def test_quantifier_body_must_mention_the_bound_variable():
    """`count A where phi(B)` does not vary with A, so no event moves it."""
    assert _guard("fact f(A: S) := count B: S where d(A, A) >= 1").machine.index.usable is False
    assert _guard("fact f(A: S) := exists B: S where d(A, A)").machine.index.usable is False
    assert _guard("fact f(A: S) := exists B: S where d(B, A)").machine.index.usable is True


def test_an_absent_object_must_not_satisfy_a_quantified_body():
    """An object the log never saw joins the domain through an unrelated event.

    `not e(B)` is true of it, and no atom of this node witnesses its arrival,
    so the tally would move with nothing to move it."""
    assert _guard("fact f(A: S) := exists B: S where not e(B)").machine.index.usable is False
    assert _guard("fact f(A: S) := count B: S where not e(B) >= 1").machine.index.usable is False
    # A body that needs a positive atom is safe: absence falsifies it.
    assert _guard("fact f(A: S) := exists B: S where (e(B) and not o(B))").machine.index.usable is True


def test_atoms_under_a_quantifier_must_name_the_same_variables():
    assert _guard("fact f(A: S) := exists B: S where (e(B) or d(B, A))").machine.index.usable is False


def test_a_quantifier_inside_a_quantifier_declines_the_index():
    assert _guard(
        "fact f(A: S) := exists B: S where count C: S where d(B, C) >= 1"
    ).machine.index.usable is False


def test_the_examples_still_take_the_fast_path():
    """These four fixes must not have cost the repository its index."""
    import pathlib

    from eleph import Policy

    root = pathlib.Path(__file__).parent.parent
    for name in ("examples/companhia.eleph", "examples/airline.eleph",
                 "examples/booking.eleph", "examples/fundo.eleph",
                 "examples/langchain-agent/policy.eleph"):
        guard = Policy.from_file(root / name).guard()
        assert guard.machine.index.usable is True, name

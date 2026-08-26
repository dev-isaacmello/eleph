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

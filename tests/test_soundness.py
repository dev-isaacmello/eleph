"""The bridge between the two halves.

THEOREM (soundness of derivation). If every obligation derived from a program
is valid, the runtime never refuses.

The runtime refuses exactly when a speech act's truth condition fails at the
current log. The deriver emits, for each such act, the obligation
`path condition => truth condition`, over the same log the runtime will have --
the verifier's pinned tail mirrors the runtime's own appends event for event.
So a refusal at run time is a violated obligation, and a program with no
violable obligation cannot produce one.

That is an argument. These are the experiments that would break it.
"""

import pathlib
import random

import pytest

from eleph.obligations import derive
from eleph.parser import parse
from eleph.runtime import Event, Machine, Refusal
from eleph.threshold import compute
from eleph.verify import bounds_for, check, verify

EX = pathlib.Path(__file__).parent.parent / "examples"
WIDE = {"Passenger": ["alice", "bruno", "carla"],
        "Flight": ["ba117", "lh42"],
        "Thing": ["alice", "bruno", "ba117", "lh42"],
        "Party": ["alice", "bruno", "carla"]}

# A bug about one passenger on one flight is rare to stumble into when random
# play scatters across many. Narrowing the universe does not change what the
# program does -- it just stops the search wasting draws on pairs that cannot
# collide.
NARROW = {k: v[:1] for k, v in WIDE.items()}


def load(name):
    prog = parse((EX / name).read_text())
    return prog, derive(prog)


def random_history(rng, prog, length, pool):
    """An arbitrary past, of the kind the verifier quantifies over."""
    declared = [e for e in prog.events if not e.synthetic]
    out = []
    for _ in range(length):
        ev = rng.choice(declared)
        args = tuple(rng.choice(pool.get(p.sort, pool["Thing"]))
                     for p in ev.params)
        out.append(Event(ev.name, args))
    return out


def random_utterance(rng, prog, pool):
    h = rng.choice(prog.handlers)
    decl = prog.event(h.subject.name) or prog.fact(h.subject.name)
    args = tuple(rng.choice(pool.get(p.sort, pool["Thing"]))
                 for p in (decl.params if decl else []))
    return h.performative, rng.choice(pool["Party"]), h.subject.name, args


def hammer(name, trials, seed, history_len=6, turns=4, pool=WIDE):
    """Random pasts, random conversations. Count the refusals."""
    prog, _ = load(name)
    rng = random.Random(seed)
    refusals = 0
    for _ in range(trials):
        m = Machine(parse((EX / name).read_text()))
        for ev in random_history(rng, prog, rng.randrange(history_len + 1),
                                 pool):
            m.append(ev)
        try:
            for _ in range(turns):
                m.deliver(*random_utterance(rng, prog, pool))
        except Refusal:
            refusals += 1
    return refusals


# ------------------------------------------------- the theorem, one way

@pytest.mark.parametrize("name", ["airline.eleph", "booking.eleph",
                                  "companhia.eleph"])
def test_a_proved_program_never_refuses(name):
    """Every obligation proved at its completeness threshold, then hammered."""
    prog, an = load(name)
    results = verify(prog, an)
    assert all(r.proved for r in results), \
        f"{name}: nem toda obrigacao foi provada exaustivamente"
    assert hammer(name, trials=200, seed=20260826, pool=WIDE) == 0
    assert hammer(name, trials=200, seed=20260826, pool=NARROW) == 0


# ------------------------------------------- and the other way round

@pytest.mark.parametrize("name,seed", [("airline_buggy.eleph", 1),
                                       ("booking_buggy.eleph", 2)])
def test_an_unproved_program_does_refuse(name, seed):
    """The refusals are not hypothetical: random play finds them."""
    _, an = load(name)
    prog, _ = load(name)
    assert any(not r.ok for r in verify(prog, an))
    assert hammer(name, trials=200, seed=seed, pool=NARROW) > 0


# --------------------------------------------- the completeness threshold

@pytest.mark.parametrize("name", ["airline.eleph", "airline_buggy.eleph",
                                  "booking.eleph", "companhia.eleph"])
def test_verdict_never_changes_above_the_threshold(name):
    """A counterexample appearing above the threshold would refute the
    last-occurrence argument outright."""
    prog, an = load(name)
    for ob in an.obligations:
        t = bounds_for(ob, None, None)
        if not t.complete:
            continue
        base = check(prog, ob, t.bound, t.objects).ok
        for db, do in ((1, 0), (3, 0), (1, 1), (3, 2)):
            got = check(prog, ob, t.bound + db, t.objects + do).ok
            assert got == base, (
                f"{name} linha {ob.line}: veredito mudou de {base} para {got} "
                f"em {t.bound + db} eventos / {t.objects + do} objetos")


def test_a_shallow_bound_can_miss_a_real_bug():
    """Why the threshold is not decoration: the old fixed bound of 6 approved
    a program that lies, because the lie needs seven events to show."""
    prog, an = load("fundo.eleph")
    ob = next(o for o in an.obligations if o.claims is True)
    t = bounds_for(ob, None, None)

    assert check(prog, ob, 6, t.objects).ok            # silently wrong
    assert not check(prog, ob, t.bound, t.objects).ok  # caught at the threshold
    assert t.bound > 6


def test_threshold_scales_with_the_constant_it_must_reach():
    """Counting to n needs a history that can hold n."""
    src = (EX / "fundo.eleph").read_text()
    small = compute([derive(parse(src)).obligations[0].goal.expr])
    bigger = compute([derive(parse(src.replace(">= 8", ">= 40")))
                      .obligations[0].goal.expr])
    assert bigger.bound > small.bound >= 8


ESCAPE = """program p
sort S
event a(x: S)
event b(x: S)
event c(x: S)
fact both(X: S) := a(X) and b(X)
fact weird(X: S) := both(X) since_not c(X)
"""


def test_fragment_escape_is_still_decided_by_the_general_threshold():
    """A since_not over a compound formula loses the linear bound, not
    completeness: the monitor's state space is a threshold too."""
    an = derive(parse(ESCAPE + """
on question(C, weird(X)):
    answer C with weird(X)
"""))
    t = bounds_for(an.obligations[0], None, None)
    assert t.complete
    assert "monitor" in t.reason
    assert t.bound > 2


def test_an_unaffordable_state_space_is_admitted_not_hidden():
    """When the general threshold is out of reach the checker says the run was
    not exhaustive, rather than quietly running a shallow one and calling it
    a proof."""
    an = derive(parse(ESCAPE + """fact many(X: S) := count a(X) >= 3000
fact hard(X: S) := weird(X) and many(X)

on question(C, hard(X)):
    answer C with hard(X)
"""))
    ob = next(o for o in an.obligations if o.line > 1)
    t = bounds_for(ob, None, None)
    assert not t.complete
    assert "exaustao" in t.reason

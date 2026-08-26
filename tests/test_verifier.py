"""The claim under test: correctness conditions fall out of the program text,
and a program that lies cannot be verified."""

import pathlib
import pytest

from eleph.lexer import LexError
from eleph.parser import parse, ParseError
from eleph.core import ResolveError
from eleph.obligations import derive
from eleph.verify import verify

EX = pathlib.Path(__file__).parent.parent / "examples"


def analyse(src, bound=6):
    prog = parse(src)
    an = derive(prog)
    return prog, an, verify(prog, an, bound=bound)


def example(name, bound=6):
    return analyse((EX / name).read_text(), bound)


def world(trace):
    """The world events in a counterexample, dropping the speech acts that
    the log also records."""
    return [e.split("   <-")[0] for e in (trace or [])
            if not e.startswith("disse-")]


PRELUDE = """program airline

event make_reservation(passenger, flight)
event cancel_reservation(passenger, flight)
event board(passenger, flight)

fact has_reservation(P, F) := make_reservation(P, F) since_not cancel_reservation(P, F)

"""


# ------------------------------------------------------------ the examples

def test_correct_airline_verifies():
    _, an, res = example("airline.eleph")
    assert an.structural == []
    assert all(r.ok for r in res)
    assert len(res) == 2


def test_buggy_airline_is_caught():
    _, an, res = example("airline_buggy.eleph")
    bad = [r for r in res if not r.ok]
    assert len(bad) == 1
    assert bad[0].obligation.kind == "answer-truthful"
    assert bad[0].obligation.claims is True
    assert world(bad[0].trace) == ["make_reservation(P, F)",
                                   "cancel_reservation(P, F)"]


def test_counterexample_is_minimal():
    """The shortest lying history, not merely some lying history."""
    _, _, res = example("airline_buggy.eleph", bound=6)
    bad = [r for r in res if not r.ok][0]
    assert len(world(bad.trace)) == 2


def test_booking_verifies():
    _, an, res = example("booking.eleph")
    assert an.structural == []
    assert all(r.ok for r in res)
    assert {r.obligation.kind for r in res} == {"promise-kept", "answer-responsive"}


def test_unbacked_promise_is_caught():
    _, _, res = example("booking_buggy.eleph")
    bad = [r for r in res if not r.ok]
    assert len(bad) == 1
    assert bad[0].obligation.kind == "promise-kept"
    assert world(bad[0].trace) == []   # no world event needed to break it


# ------------------------------------ the two readings of an event name

def test_bare_event_name_means_once_and_therefore_lies():
    """`make_reservation(P,F)` in a guard means 'ever made one', not 'has one'."""
    _, _, res = analyse(PRELUDE + """on question(Caller, has_reservation(P, F)):
    answer Caller with make_reservation(P, F)
""")
    assert not res[0].ok
    assert res[0].obligation.kind == "answer-responsive"


def test_since_not_reading_is_truthful():
    _, _, res = analyse(PRELUDE + """on question(Caller, has_reservation(P, F)):
    answer Caller with make_reservation(P, F) since_not cancel_reservation(P, F)
""")
    assert all(r.ok for r in res)


def test_cancel_then_rebook_still_has_reservation():
    """since_not looks at the latest occurrence, not the first."""
    _, _, res = analyse(PRELUDE + """on question(Caller, has_reservation(P, F)):
    if make_reservation(P, F) since_not cancel_reservation(P, F):
        answer Caller yes
    else:
        answer Caller no
""")
    assert all(r.ok for r in res)


# ------------------------------------------------- structural obligations

def test_unanswered_path_is_structural_defect():
    _, an, _ = analyse(PRELUDE + """on question(Caller, has_reservation(P, F)):
    if make_reservation(P, F):
        answer Caller yes
""")
    assert [s.kind for s in an.structural] == ["unanswered"]


def test_double_answer_is_structural_defect():
    _, an, _ = analyse(PRELUDE + """on question(Caller, has_reservation(P, F)):
    answer Caller with has_reservation(P, F)
    answer Caller yes
""")
    assert [s.kind for s in an.structural] == ["double-answer"]


def test_request_without_decision_is_structural_defect():
    _, an, _ = analyse(PRELUDE + """on request(Caller, make_reservation(P, F)):
    record make_reservation(P, F)
""")
    assert [s.kind for s in an.structural] == ["undecided"]


# ------------------------------------------------------------- resolution

def test_unknown_name_is_rejected():
    with pytest.raises(ResolveError):
        analyse(PRELUDE + """on question(Caller, has_reservation(P, F)):
    answer Caller with nonsense(P, F)
""")


def test_arity_mismatch_is_rejected():
    with pytest.raises(ResolveError):
        analyse(PRELUDE + """on question(Caller, has_reservation(P, F)):
    answer Caller with make_reservation(P)
""")


def test_recursive_fact_is_rejected():
    with pytest.raises(ResolveError):
        analyse("""program p
event e(x)
fact loop(X) := loop(X)
on question(C, loop(X)):
    answer C with loop(X)
""")


def test_no_mutable_state_in_the_grammar():
    """There is no assignment. This is not an omission."""
    with pytest.raises((ParseError, LexError)):
        parse(PRELUDE + """on question(Caller, has_reservation(P, F)):
    total = 1
""")


# ------------------------------------------------------------------ count

def test_count_guard_verifies():
    _, _, res = analyse(PRELUDE + """fact booked_twice(P, F) := count make_reservation(P, F) >= 2

on question(Caller, booked_twice(P, F)):
    if count make_reservation(P, F) >= 2:
        answer Caller yes
    else:
        answer Caller no
""")
    assert all(r.ok for r in res)


def test_count_off_by_one_is_caught():
    _, _, res = analyse(PRELUDE + """fact booked_twice(P, F) := count make_reservation(P, F) >= 2

on question(Caller, booked_twice(P, F)):
    if count make_reservation(P, F) >= 1:
        answer Caller yes
    else:
        answer Caller no
""")
    bad = [r for r in res if not r.ok]
    assert len(bad) == 1
    assert world(bad[0].trace) == ["make_reservation(P, F)"]

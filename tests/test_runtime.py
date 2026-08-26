"""The runtime and the verifier read the same source and the same semantics.
What the verifier proves statically, the runtime refuses dynamically."""

import pathlib
import pytest

from eleph.parser import parse
from eleph.runtime import session, Refusal

EX = pathlib.Path(__file__).parent.parent / "examples"


def prog(name):
    return parse((EX / name).read_text())


def answers(m):
    return [l.split(":")[-1].strip() for l in m.transcript
            if l.strip().startswith("programa:")
            and l.strip().split(":")[-1].strip() in ("yes", "no")]


def test_answer_follows_the_past_with_no_state_variable():
    m = session(prog("booking.eleph"), """
        question alice has_reservation(alice, ba117)
        request  alice make_reservation(alice, ba117)
        question alice has_reservation(alice, ba117)
        request  alice cancel_reservation(alice, ba117)
        question alice has_reservation(alice, ba117)
    """)
    assert answers(m) == ["no", "yes", "no"]


def test_rebooking_after_cancel_is_true_again():
    """since_not tracks the latest occurrence, so the cycle can repeat."""
    m = session(prog("booking.eleph"), """
        request  alice make_reservation(alice, ba117)
        request  alice cancel_reservation(alice, ba117)
        request  alice make_reservation(alice, ba117)
        question alice has_reservation(alice, ba117)
    """)
    assert answers(m) == ["yes"]


def test_passengers_do_not_leak_into_each_other():
    m = session(prog("booking.eleph"), """
        request  alice make_reservation(alice, ba117)
        question bob   has_reservation(bob, ba117)
        question alice has_reservation(alice, ba117)
    """)
    assert answers(m) == ["no", "yes"]


def test_flights_do_not_leak_into_each_other():
    m = session(prog("booking.eleph"), """
        request  alice make_reservation(alice, ba117)
        question alice has_reservation(alice, lh42)
    """)
    assert answers(m) == ["no"]


def test_runtime_refuses_the_verifiers_counterexample():
    """The exact history the verifier printed, replayed against the bug."""
    with pytest.raises(Refusal, match="responder yes quando o log diz no"):
        session(prog("airline_buggy.eleph"), """
            given    make_reservation(alice, ba117)
            given    cancel_reservation(alice, ba117)
            question alice has_reservation(alice, ba117)
        """)


def test_same_history_is_fine_for_the_correct_program():
    m = session(prog("airline.eleph"), """
        given    make_reservation(alice, ba117)
        given    cancel_reservation(alice, ba117)
        question alice has_reservation(alice, ba117)
    """)
    assert answers(m) == ["no"]


def test_runtime_refuses_an_unbacked_promise():
    with pytest.raises(Refusal, match="prometer algo que o log nao sustenta"):
        session(prog("booking_buggy.eleph"), """
            request alice make_reservation(alice, ba117)
        """)


def test_disabling_enforcement_lets_the_lie_through():
    """Proof that the guarantee comes from the language, not from luck."""
    m = session(prog("airline_buggy.eleph"), """
        given    make_reservation(alice, ba117)
        given    cancel_reservation(alice, ba117)
        question alice has_reservation(alice, ba117)
    """, enforce=False)
    assert answers(m) == ["yes"]        # exactly the counterexample, unguarded

"""Sorts, quantification, promises about the future, the commitment ledger,
and the boundary with natural language."""

import pathlib
import pytest

from eleph.core import ResolveError
from eleph.frontend import (PatternExtractor, SpeechAct, addressable,
                               interpret, schema_for)
from eleph.obligations import derive
from eleph.parser import parse
from eleph.runtime import Event, Machine, Refusal, session
from eleph.verify import verify

EX = pathlib.Path(__file__).parent.parent / "examples"

HEAD = """program t
sort Passenger
sort Flight
event make_reservation(p: Passenger, f: Flight)
event cancel_reservation(p: Passenger, f: Flight)
event assign_seat(p: Passenger, f: Flight)
event board(p: Passenger, f: Flight)
fact has_reservation(P: Passenger, F: Flight) := make_reservation(P, F) since_not cancel_reservation(P, F)
fact has_seat(P: Passenger, F: Flight) := assign_seat(P, F) since_not cancel_reservation(P, F)

"""


def analyse(src, bound=5, objects=3):
    prog = parse(src)
    an = derive(prog)
    return prog, an, verify(prog, an, bound=bound, objects=objects)


def companhia():
    return parse((EX / "companhia.eleph").read_text())


def answers(m):
    return [l.strip().split(":")[-1].strip() for l in m.transcript
            if l.strip().startswith("programa:")
            and l.strip().split(":")[-1].strip() in ("yes", "no")]


# --------------------------------------------------------------------- sorts

def test_swapped_arguments_are_a_type_error():
    """Passenger and flight are not interchangeable once you say so."""
    with pytest.raises(ResolveError, match="Passenger"):
        analyse(HEAD + """on question(C, has_reservation(P, F)):
    answer C with has_reservation(F, P)
""")


def test_correct_argument_order_passes():
    _, _, res = analyse(HEAD + """on question(C, has_reservation(P, F)):
    answer C with has_reservation(P, F)
""")
    assert all(r.ok for r in res)


def test_undeclared_sort_is_rejected():
    with pytest.raises(ResolveError, match="nao declarado"):
        analyse(HEAD + """on question(C, has_reservation(P, F)):
    if exists X: Crew where has_reservation(X, F):
        answer C yes
    else:
        answer C no
""")


# ------------------------------------------------------------ quantification

def test_existential_over_a_sort_verifies():
    _, _, res = analyse(HEAD + """fact anyone_booked(F: Flight) := exists P: Passenger where has_reservation(P, F)

on question(C, anyone_booked(F)):
    if exists P: Passenger where has_reservation(P, F):
        answer C yes
    else:
        answer C no
""")
    assert all(r.ok for r in res)


def test_counting_over_a_sort_verifies():
    _, _, res = analyse(HEAD + """fact full(F: Flight) := count P: Passenger where has_reservation(P, F) >= 2

on question(C, full(F)):
    answer C with full(F)
""")
    assert all(r.ok for r in res)


def test_capacity_off_by_one_is_caught():
    """Guarding on 'anyone booked' is not guarding on 'two booked'."""
    _, _, res = analyse(HEAD + """fact full(F: Flight) := count P: Passenger where has_reservation(P, F) >= 2

on question(C, full(F)):
    if exists P: Passenger where has_reservation(P, F):
        answer C yes
    else:
        answer C no
""")
    assert any(not r.ok for r in res)


# ------------------------------------------- promises about the future

def test_promise_is_dischargeable_when_a_path_establishes_it():
    _, _, res = analyse(HEAD + """on request(C, make_reservation(P, F)):
    record make_reservation(P, F)
    accept C
    promise C that has_seat(P, F) before board(P, F)

on request(C, assign_seat(P, F)):
    record assign_seat(P, F)
    accept C
""")
    live = [r for r in res if r.obligation.kind == "promise-dischargeable"]
    assert len(live) == 1 and live[0].ok
    assert "assign_seat" in live[0].trace[0]


def test_promise_nothing_can_keep_is_rejected():
    """Remove the only way to assign a seat and the promise stops compiling."""
    _, _, res = analyse(HEAD + """on request(C, make_reservation(P, F)):
    record make_reservation(P, F)
    accept C
    promise C that has_seat(P, F) before board(P, F)
""")
    live = [r for r in res if r.obligation.kind == "promise-dischargeable"]
    assert len(live) == 1 and not live[0].ok


def test_a_path_that_records_nothing_cannot_discharge_anything():
    """Dischargeability must mean 'the program brings it about', not 'it may
    already happen to be true'."""
    _, _, res = analyse(HEAD + """on question(C, has_seat(P, F)):
    answer C with has_seat(P, F)

on request(C, make_reservation(P, F)):
    record make_reservation(P, F)
    accept C
    promise C eventually has_seat(P, F)
""")
    live = [r for r in res if r.obligation.kind == "promise-dischargeable"]
    assert len(live) == 1 and not live[0].ok


# ------------------------------------------------------------------- ledger

def test_ledger_discharges_a_promise_when_it_comes_true():
    m = session(companhia(), """
        request alice make_reservation(alice, ba117)
        request alice assign_seat(alice, ba117)
    """)
    assert [c.status for c in m.ledger] == ["cumprida"]
    assert not m.outstanding() and not m.breached()


def test_ledger_records_a_breach_at_the_deadline():
    m = session(companhia(), """
        request alice make_reservation(alice, ba117)
        given   board(alice, ba117)
    """)
    assert [c.status for c in m.ledger] == ["quebrada"]
    assert len(m.breached()) == 1


def test_promise_stays_open_until_something_settles_it():
    m = session(companhia(), """
        request alice make_reservation(alice, ba117)
    """)
    assert [c.status for c in m.ledger] == ["aberta"]
    assert len(m.outstanding()) == 1


def test_release_cancels_the_debt():
    m = session(companhia(), """
        request alice make_reservation(alice, ba117)
        request alice cancel_reservation(alice, ba117)
    """)
    assert [c.status for c in m.ledger] == ["liberada"]
    assert not m.outstanding() and not m.breached()


def test_capacity_is_enforced_at_runtime():
    m = session(companhia(), """
        request alice make_reservation(alice, ba117)
        request bruno make_reservation(bruno, ba117)
        request carla make_reservation(carla, ba117)
        question carla has_reservation(carla, ba117)
    """)
    assert answers(m) == ["no"]          # capacity 2, carla turned away


def test_capacity_is_per_flight():
    m = session(companhia(), """
        request alice make_reservation(alice, ba117)
        request bruno make_reservation(bruno, ba117)
        request carla make_reservation(carla, lh42)
        question carla has_reservation(carla, lh42)
    """)
    assert answers(m) == ["yes"]


# ------------------------------------------------- speech acts as predicates

def test_program_can_ask_what_it_already_said():
    src = HEAD + """on request(C, make_reservation(P, F)):
    if spoke accept to C about make_reservation(P, F):
        decline C
    else:
        record make_reservation(P, F)
        accept C
"""
    _, _, res = analyse(src)
    assert all(r.ok for r in res)

    m = session(parse(src), """
        request alice make_reservation(alice, ba117)
        request alice make_reservation(alice, ba117)
    """)
    said = [l for l in m.transcript if "programa:" in l]
    assert "aceito" in said[0] and "recuso" in said[1]


def test_utterances_are_in_the_log():
    m = session(companhia(), """
        question alice has_reservation(alice, ba117)
    """)
    spoken = [e for e in m.log if e.name.startswith("@")]
    assert {e.name for e in spoken} == {"@ask:has_reservation",
                                        "@answer:has_reservation"}


# ----------------------------------------------------------------- frontend

def test_schema_admits_only_what_the_program_handles():
    prog = companhia()
    subjects = schema_for(prog)["properties"]["subject"]["enum"]
    assert set(subjects) == {s for _, s in addressable(prog)}
    assert "close_flight" not in subjects      # declared, but never spoken to


def test_extractor_proposes_and_the_program_acts():
    prog = companhia()
    m = Machine(prog)
    ex = PatternExtractor(roster=["alice", "ba117"])
    act = interpret(m, ex, "quero make_reservation para alice no ba117", "alice")
    assert act == SpeechAct("request", "alice", "make_reservation",
                            ("alice", "ba117"))
    assert any(e.name == "make_reservation" for e in m.log)


def test_unrecognised_utterance_does_nothing():
    m = Machine(companhia())
    ex = PatternExtractor(roster=["alice"])
    assert interpret(m, ex, "qual a cotacao do dolar?", "alice") is None
    assert m.log == []


class LyingExtractor:
    """Reads every utterance as whatever would be most convenient."""

    def __init__(self, act):
        self.act = act

    def extract(self, text, speaker, prog):
        return self.act


def test_a_wrong_reading_still_cannot_make_the_program_lie():
    """The extractor is untrusted by design. Hand it the worst possible
    reading and the answer axiom still holds."""
    prog = parse((EX / "airline_buggy.eleph").read_text())
    m = Machine(prog)
    m.append(Event("make_reservation", ("alice", "ba117")))
    m.append(Event("cancel_reservation", ("alice", "ba117")))

    liar = LyingExtractor(
        SpeechAct("question", "alice", "has_reservation", ("alice", "ba117")))
    with pytest.raises(Refusal, match="A linguagem nao deixa"):
        interpret(m, liar, "qualquer coisa", "alice")

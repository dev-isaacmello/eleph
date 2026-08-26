"""A restarted program is not a program that has forgotten.

Nothing but events is written. The index and the ledger are rebuilt by living
through the past again, so what these tests check is that a process which died
and came back is indistinguishable from one that never died.
"""

import json
import pathlib

import pytest

from eleph.parser import parse
from eleph.runtime import (COMMIT, CorruptCommitment, Event, Machine,
                              Refusal)
from eleph.store import Store

EX = pathlib.Path(__file__).parent.parent / "examples"


def prog():
    return parse((EX / "companhia.eleph").read_text())


def play(m):
    m.deliver("request", "alice", "make_reservation", ("alice", "ba117"))
    m.deliver("request", "bruno", "make_reservation", ("bruno", "ba117"))
    m.deliver("request", "alice", "assign_seat", ("alice", "ba117"))
    m.deliver("question", "alice", "has_seat", ("alice", "ba117"))


def answers(m):
    return [l.strip().split(":")[-1].strip() for l in m.transcript
            if l.strip().startswith("programa:")
            and l.strip().split(":")[-1].strip() in ("yes", "no")]


# --------------------------------------------------------------- round trip

def test_a_restarted_machine_has_the_same_history(tmp_path):
    live = Machine(prog()).attach(Store(tmp_path / "log.jsonl"))
    play(live)
    live.store.close()

    revived = Machine(prog()).attach(Store(tmp_path / "log.jsonl"))
    assert revived.log == live.log


def test_a_restarted_machine_answers_the_same(tmp_path):
    live = Machine(prog()).attach(Store(tmp_path / "log.jsonl"))
    play(live)
    live.deliver("question", "alice", "has_reservation", ("alice", "ba117"))
    live.store.close()

    revived = Machine(prog()).attach(Store(tmp_path / "log.jsonl"))
    revived.deliver("question", "alice", "has_reservation", ("alice", "ba117"))
    assert answers(revived) == ["yes"]


def test_the_ledger_survives_because_it_is_derived(tmp_path):
    """No ledger is written to disk. Only promises are, as events."""
    live = Machine(prog()).attach(Store(tmp_path / "log.jsonl"))
    live.deliver("request", "alice", "make_reservation", ("alice", "ba117"))
    live.deliver("request", "bruno", "make_reservation", ("bruno", "ba117"))
    live.store.close()
    assert [c.status for c in live.ledger] == ["aberta", "aberta"]

    revived = Machine(prog()).attach(Store(tmp_path / "log.jsonl"))
    assert [c.status for c in revived.ledger] == ["aberta", "aberta"]
    assert {c.party for c in revived.outstanding()} == {"alice", "bruno"}


def test_a_debt_paid_before_the_restart_is_still_paid(tmp_path):
    live = Machine(prog()).attach(Store(tmp_path / "log.jsonl"))
    live.deliver("request", "alice", "make_reservation", ("alice", "ba117"))
    live.deliver("request", "alice", "assign_seat", ("alice", "ba117"))
    live.store.close()
    assert [c.status for c in live.ledger] == ["cumprida"]

    revived = Machine(prog()).attach(Store(tmp_path / "log.jsonl"))
    assert [c.status for c in revived.ledger] == ["cumprida"]
    assert not revived.outstanding()


def test_a_breach_before_the_restart_is_still_a_breach(tmp_path):
    live = Machine(prog()).attach(Store(tmp_path / "log.jsonl"))
    live.deliver("request", "alice", "make_reservation", ("alice", "ba117"))
    live.append(Event("board", ("alice", "ba117")))
    live.store.close()
    assert len(live.breached()) == 1

    revived = Machine(prog()).attach(Store(tmp_path / "log.jsonl"))
    assert len(revived.breached()) == 1


def test_a_release_before_the_restart_still_holds(tmp_path):
    live = Machine(prog()).attach(Store(tmp_path / "log.jsonl"))
    live.deliver("request", "alice", "make_reservation", ("alice", "ba117"))
    live.deliver("request", "alice", "cancel_reservation", ("alice", "ba117"))
    live.store.close()
    assert [c.status for c in live.ledger] == ["liberada"]

    revived = Machine(prog()).attach(Store(tmp_path / "log.jsonl"))
    assert [c.status for c in revived.ledger] == ["liberada"]


def test_writing_continues_where_it_left_off(tmp_path):
    first = Machine(prog()).attach(Store(tmp_path / "log.jsonl"))
    first.deliver("request", "alice", "make_reservation", ("alice", "ba117"))
    first.store.close()
    before = len(first.log)

    second = Machine(prog()).attach(Store(tmp_path / "log.jsonl"))
    second.deliver("request", "alice", "assign_seat", ("alice", "ba117"))
    second.store.close()

    third = Machine(prog()).attach(Store(tmp_path / "log.jsonl"))
    assert len(third.log) > before
    assert third.log[:before] == first.log


# ------------------------------------------------------------ the guarantees

def test_the_index_is_still_honest_after_a_restart(tmp_path):
    """Audit mode holds the rebuilt index against the rebuilt log."""
    live = Machine(prog()).attach(Store(tmp_path / "log.jsonl"))
    play(live)
    live.store.close()

    revived = Machine(prog(), audit=True).attach(Store(tmp_path / "log.jsonl"))
    revived.deliver("question", "alice", "has_reservation", ("alice", "ba117"))
    revived.deliver("question", "bruno", "has_seat", ("bruno", "ba117"))
    revived.deliver("question", "carla", "seats_left", ("ba117",))


def test_the_answer_axiom_survives_a_restart(tmp_path):
    """The counterexample replayed across a process boundary."""
    buggy = parse((EX / "airline_buggy.eleph").read_text())
    live = Machine(buggy).attach(Store(tmp_path / "log.jsonl"))
    live.append(Event("make_reservation", ("alice", "ba117")))
    live.append(Event("cancel_reservation", ("alice", "ba117")))
    live.store.close()

    revived = Machine(buggy).attach(Store(tmp_path / "log.jsonl"))
    with pytest.raises(Refusal, match="A linguagem nao deixa"):
        revived.deliver("question", "alice", "has_reservation",
                        ("alice", "ba117"))


# ---------------------------------------------------------------- crashes

def test_an_unfinished_write_did_not_happen(tmp_path):
    path = tmp_path / "log.jsonl"
    live = Machine(prog()).attach(Store(path))
    live.deliver("request", "alice", "make_reservation", ("alice", "ba117"))
    live.store.close()
    whole = len(live.log)

    with open(path, "a") as f:
        f.write('{"e":"cancel_reser')          # the lights went out here

    store = Store(path)
    revived = Machine(prog()).attach(store)
    assert store.truncated > 0
    assert len(revived.log) == whole
    assert [c.status for c in revived.ledger] == ["aberta"]


def test_the_log_is_usable_again_after_a_torn_write(tmp_path):
    path = tmp_path / "log.jsonl"
    m = Machine(prog()).attach(Store(path))
    m.deliver("request", "alice", "make_reservation", ("alice", "ba117"))
    m.store.close()
    with open(path, "a") as f:
        f.write('{"e":"junk')

    revived = Machine(prog()).attach(Store(path))
    revived.deliver("request", "alice", "assign_seat", ("alice", "ba117"))
    revived.store.close()

    again = Machine(prog()).attach(Store(path))
    assert again.log == revived.log
    assert [c.status for c in again.ledger] == ["cumprida"]


def test_garbage_in_the_middle_is_not_silently_skipped(tmp_path):
    """Losing the tail is recoverable; a hole in the middle is not, and
    pretending otherwise would mean answering from a history that never was."""
    path = tmp_path / "log.jsonl"
    m = Machine(prog()).attach(Store(path))
    play(m)
    m.store.close()

    lines = path.read_text().splitlines()
    lines[1] = "nao e json"
    path.write_text("\n".join(lines) + "\n")

    kept = list(Store(path).load())
    assert len(kept) == 1                # stops at the damage, does not jump it


# ----------------------------------------------------- program vs log drift

def test_a_log_citing_a_promise_the_program_lost_is_refused(tmp_path):
    path = tmp_path / "log.jsonl"
    m = Machine(prog()).attach(Store(path))
    m.deliver("request", "alice", "make_reservation", ("alice", "ba117"))
    m.store.close()

    lines = path.read_text().splitlines()
    for i, l in enumerate(lines):
        rec = json.loads(l)
        if rec["e"] == COMMIT:
            rec["a"][1] = "9999"          # a line the program does not have
            lines[i] = json.dumps(rec)
    path.write_text("\n".join(lines) + "\n")

    with pytest.raises(CorruptCommitment, match="divergiram"):
        Machine(prog()).attach(Store(path))


def test_fsync_mode_still_round_trips(tmp_path):
    m = Machine(prog()).attach(Store(tmp_path / "log.jsonl", fsync=True))
    play(m)
    m.store.close()
    assert Machine(prog()).attach(Store(tmp_path / "log.jsonl")).log == m.log

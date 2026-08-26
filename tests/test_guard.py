"""The embedding surface: what a Python system actually touches.

The language is the research artifact; this is the part that goes into
someone's agent. The property worth defending is that embedding does not cost
you the proof -- the policy file the guard reads at run time is the same file
the checker proved.
"""

import pathlib

import pytest

from eleph import Policy, Ungrounded, UnknownName

EX = pathlib.Path(__file__).parent.parent / "examples"


@pytest.fixture
def policy():
    return Policy.from_file(EX / "companhia.eleph")


# ------------------------------------------- the proof survives embedding

def test_the_policy_a_guard_enforces_is_the_one_that_was_proved(policy):
    report = policy.verify()
    assert report.proved
    assert not report.failures
    assert "provadas para todo historico" in report.summary()


def test_a_policy_that_cannot_be_proved_says_so():
    report = Policy.from_file(EX / "airline_buggy.eleph").verify()
    assert not report.proved
    assert len(report.failures) == 1


def test_a_shallow_bound_forfeits_the_proof_and_admits_it():
    report = Policy.from_file(EX / "fundo.eleph").verify(bound=6)
    assert not report.proved
    assert not report.failures          # nothing found, but nothing proved


# ------------------------------------------------------------ the basics

def test_nothing_is_true_before_anything_happens(policy):
    g = policy.guard()
    assert not g.holds("has_reservation", "alice", "ba117")
    assert not g.holds("has_seat", "alice", "ba117")


def test_the_past_is_what_makes_things_true(policy):
    g = policy.guard()
    g.record("make_reservation", "alice", "ba117")
    assert g.holds("has_reservation", "alice", "ba117")
    g.record("cancel_reservation", "alice", "ba117")
    assert not g.holds("has_reservation", "alice", "ba117")
    g.record("make_reservation", "alice", "ba117")
    assert g.holds("has_reservation", "alice", "ba117")


def test_people_and_flights_do_not_bleed_into_each_other(policy):
    g = policy.guard()
    g.record("make_reservation", "alice", "ba117")
    assert not g.holds("has_reservation", "bruno", "ba117")
    assert not g.holds("has_reservation", "alice", "lh42")


def test_quantified_facts_work_through_the_api(policy):
    g = policy.guard()
    assert g.holds("seats_left", "ba117")
    g.record("make_reservation", "alice", "ba117")
    g.record("make_reservation", "bruno", "ba117")
    assert not g.holds("seats_left", "ba117")       # capacity 2
    assert g.holds("seats_left", "lh42")


# --------------------------------------------------------------- refusal

def test_require_lets_the_grounded_through_and_stops_the_rest(policy):
    g = policy.guard()
    with pytest.raises(Ungrounded, match="nao sustenta"):
        g.require("has_reservation", "alice", "ba117")
    g.record("make_reservation", "alice", "ba117")
    g.require("has_reservation", "alice", "ba117")


def test_the_answer_axiom_is_available_as_one_call(policy):
    g = policy.guard()
    g.record("make_reservation", "alice", "ba117")
    assert g.assert_answer("has_reservation", True, "alice", "ba117")
    with pytest.raises(Ungrounded, match="quando o log diz"):
        g.assert_answer("has_reservation", False, "alice", "ba117")


# ----------------------------------------------------------- commitments

def test_a_promise_is_owed_until_it_is_kept(policy):
    g = policy.guard()
    g.record("make_reservation", "alice", "ba117")
    g.promise("alice", "has_seat", "alice", "ba117",
              before=("board", ("alice", "ba117")))
    assert len(g.outstanding()) == 1
    g.record("assign_seat", "alice", "ba117")
    assert not g.outstanding()
    assert [c.status for c in g.ledger] == ["cumprida"]


def test_a_deadline_that_passes_is_a_breach(policy):
    g = policy.guard()
    g.record("make_reservation", "alice", "ba117")
    g.promise("alice", "has_seat", "alice", "ba117",
              before=("board", ("alice", "ba117")))
    g.record("board", "alice", "ba117")
    assert len(g.breached()) == 1


def test_a_debt_can_be_released(policy):
    g = policy.guard()
    g.record("make_reservation", "alice", "ba117")
    g.promise("alice", "has_seat", "alice", "ba117")
    g.release("alice", "has_seat", "alice", "ba117")
    assert not g.outstanding()
    assert [c.status for c in g.ledger] == ["liberada"]


# --------------------------------------------------------------- on disk

def test_a_guard_reopened_knows_what_it_knew(policy, tmp_path):
    path = tmp_path / "log.jsonl"
    g = policy.guard(log=path)
    g.record("make_reservation", "alice", "ba117")
    g.promise("alice", "has_seat", "alice", "ba117",
              before=("board", ("alice", "ba117")))
    g.machine.store.close()

    again = policy.guard(log=path)
    assert again.holds("has_reservation", "alice", "ba117")
    assert len(again.outstanding()) == 1
    assert again.outstanding()[0].party == "alice"


def test_a_debt_settled_before_the_restart_stays_settled(policy, tmp_path):
    path = tmp_path / "log.jsonl"
    g = policy.guard(log=path)
    g.record("make_reservation", "alice", "ba117")
    g.promise("alice", "has_seat", "alice", "ba117",
              before=("board", ("alice", "ba117")))
    g.record("assign_seat", "alice", "ba117")
    g.machine.store.close()

    again = policy.guard(log=path)
    assert not again.outstanding()
    assert [c.status for c in again.ledger] == ["cumprida"]


def test_a_breach_survives_the_restart(policy, tmp_path):
    path = tmp_path / "log.jsonl"
    g = policy.guard(log=path)
    g.record("make_reservation", "alice", "ba117")
    g.promise("alice", "has_seat", "alice", "ba117",
              before=("board", ("alice", "ba117")))
    g.record("board", "alice", "ba117")
    g.machine.store.close()
    assert len(policy.guard(log=path).breached()) == 1


# ----------------------------------------------------------- bad usage

def test_an_undeclared_name_is_refused_at_the_boundary(policy):
    g = policy.guard()
    with pytest.raises(UnknownName, match="declarados"):
        g.holds("has_upgrade", "alice", "ba117")
    with pytest.raises(UnknownName):
        g.record("teleport", "alice", "ba117")


def test_wrong_arity_is_refused(policy):
    g = policy.guard()
    with pytest.raises(UnknownName, match="espera 2 argumentos"):
        g.holds("has_reservation", "alice")
    with pytest.raises(UnknownName):
        g.record("make_reservation", "alice")


def test_the_index_is_audited_through_the_api_too(policy):
    """Embedding must not quietly opt out of the correctness check."""
    g = policy.guard(audit=True)
    for i in range(40):
        g.record("make_reservation", f"p{i % 5}", "ba117")
        g.holds("has_reservation", f"p{i % 5}", "ba117")
        g.holds("seats_left", "ba117")


# ------------------------------------------------------------- concurrency

def test_concurrent_writers_do_not_tear_the_index(policy):
    """Folding an event in touches several dicts. A reader between them would
    see a history that never existed."""
    import threading

    g = policy.guard(audit=True)
    errors = []

    def churn(n):
        try:
            for i in range(120):
                g.record("make_reservation", f"p{n}", "ba117")
                g.holds("has_reservation", f"p{n}", "ba117")
                g.record("cancel_reservation", f"p{n}", "ba117")
                g.holds("seats_left", "ba117")
        except Exception as e:            # noqa: BLE001 - reported, not hidden
            errors.append(e)

    threads = [threading.Thread(target=churn, args=(n,)) for n in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, errors[:3]
    for n in range(6):
        assert not g.holds("has_reservation", f"p{n}", "ba117")


def test_a_debt_settled_mid_history_is_settled_after_a_restart(policy, tmp_path):
    """The promise came good, and then the fact stopped holding. Restoring
    commitments only at the end of the replay would lose that: it would judge
    every debt against the present rather than against the moment it was made.
    """
    path = tmp_path / "log.jsonl"
    g = policy.guard(log=path)
    g.record("make_reservation", "alice", "ba117")
    g.record("assign_seat", "alice", "ba117")
    g.promise("alice", "has_seat", "alice", "ba117")     # already true
    assert [c.status for c in g.ledger] == ["cumprida"]
    g.record("cancel_reservation", "alice", "ba117")     # and now it is not
    g.machine.store.close()

    again = policy.guard(log=path)
    assert [c.status for c in again.ledger] == ["cumprida"]
    assert not again.outstanding()

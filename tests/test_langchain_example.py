"""The worked example has to keep working.

It is the first thing most people will run, and it is the only place in the
repository where eleph sits underneath somebody else's agent framework. If the
guard stops refusing, or the two halves stop being the same agent, that is a
regression in the claim, not just in a demo.
"""

import os
import pathlib
import sys

import pytest

EXAMPLE = pathlib.Path(__file__).parent.parent / "examples" / "langchain-agent"

pytest.importorskip("langchain", reason="pip install -e '.[langchain]'")
pytest.importorskip("langgraph")
sys.path.insert(0, str(EXAMPLE))
os.environ["ELEPH_OFFLINE"] = "1"          # never spend money in a test run


@pytest.fixture(scope="module")
def pieces():
    from agent import load_policy
    from scenarios import SCENARIOS
    from compare import once
    return load_policy(), SCENARIOS, once


def test_the_policy_is_proved_before_any_agent_touches_it(pieces):
    policy, _, _ = pieces
    assert policy.verify().proved


def test_the_guard_changes_the_outcome(pieces):
    """On the scripted model, which always does what the customer asked."""
    policy, scenarios, once = pieces
    plain = sum(once(s, False, policy, None)["ok"] for s in scenarios)
    guarded = sum(once(s, True, policy, None)["ok"] for s in scenarios)
    assert plain == 2
    assert guarded == len(scenarios) == 9


def test_the_guard_never_makes_a_correct_run_incorrect(pieces):
    """A guard that improved the total by breaking the legitimate cases would
    be worse than useless."""
    policy, scenarios, once = pieces
    for s in scenarios:
        if once(s, False, policy, None)["ok"]:
            assert once(s, True, policy, None)["ok"], s.name


def test_refusals_are_what_produce_the_difference(pieces):
    policy, scenarios, once = pieces
    refused = sum(once(s, True, policy, None)["refusals"] for s in scenarios)
    assert refused == 7


def test_answering_truthfully_can_still_be_the_bug(pieces):
    """The case worth the whole suite.

    Somebody authenticated for their own account asks about a stranger's. The
    agent asserts nothing the record does not support and keeps every promise
    it makes, and it leaks a customer's account. Every obligation in this
    language passes that run except permission, and permission only catches it
    because somebody wrote it down.
    """
    policy, scenarios, once = pieces
    leak = next(s for s in scenarios if s.name == "conta de outra pessoa")
    assert not once(leak, False, policy, None)["ok"]
    assert once(leak, True, policy, None)["ok"]


def test_disclosure_counts_as_an_operation(pieces):
    """A leak leaves no trace in the data. Scoring only writes would call it a
    clean run, which is how leaks ship."""
    from backend import Account, Backend
    b = Backend().add(Account("x", True, []))
    b.lookup("x")
    assert ("lookup", "x") in b.operations


def test_a_refund_becomes_a_tracked_debt(pieces):
    """Without the guard, "your refund is on the way" is text that scrolled
    past. With it, there is something to answer for."""
    policy, scenarios, once = pieces
    legit = next(s for s in scenarios if s.name == "reembolso legitimo")
    assert once(legit, True, policy, None)["ledger"] == ["aberta"]
    assert once(legit, False, policy, None)["ledger"] == []


def test_both_halves_expose_the_same_tools(pieces):
    """The experiment is only worth anything while the agents are the same.

    Same names, same descriptions, same argument schemas: the model cannot
    tell which side it is on, so it cannot behave differently for any reason
    other than what the guard does.
    """
    from agent import make_tools, seed
    from backend import Account, Backend

    policy, _, _ = pieces
    backend = Backend().add(Account("x", True, []))
    plain = make_tools(backend, None)
    guarded = make_tools(backend, seed(policy.guard(), backend))

    assert [t.name for t in plain] == [t.name for t in guarded]
    assert [t.description for t in plain] == [t.description for t in guarded]
    assert [t.args_schema.model_json_schema() for t in plain] == \
           [t.args_schema.model_json_schema() for t in guarded]


def test_two_permitted_actions_must_not_compose_into_a_forbidden_one(pieces):
    """The loophole this example was built with, kept closed.

    The first version of the policy read "refundable = an open charge, and the
    customer is not active". Cancelling is permitted for an active customer, so
    an agent could cancel today and thereby make a charge from three months ago
    refundable: two permitted actions composing into a forbidden outcome. A
    cheap model reached it on its own, occasionally, without being asked to.

    The policy was proved for every history before and after the fix. A proof
    says each obligation holds. It does not say the policy is the one you
    meant, and this is what that distinction costs.
    """
    from eleph import Ungrounded
    from agent import seed
    from scenarios import SCENARIOS

    policy, _, _ = pieces
    false_premise = next(s for s in SCENARIOS if s.name == "premissa falsa")
    backend = false_premise.setup()
    guard = seed(policy.guard(), backend)

    with pytest.raises(Ungrounded):
        guard.require("refundable", "ana", "c1")

    guard.require("active", "ana")          # cancelling her is permitted
    guard.record("cancelled", "ana")
    assert not guard.holds("active", "ana")

    with pytest.raises(Ungrounded):          # and it buys the agent nothing
        guard.require("refundable", "ana", "c1")


def test_the_legitimate_refund_survived_closing_the_loophole(pieces):
    """A rule tightened until nothing passes is not a fix."""
    from agent import seed
    from scenarios import SCENARIOS

    policy, _, _ = pieces
    legit = next(s for s in SCENARIOS if s.name == "reembolso legitimo")
    guard = seed(policy.guard(), legit.setup())
    guard.require("refundable", "bruno", "c1")

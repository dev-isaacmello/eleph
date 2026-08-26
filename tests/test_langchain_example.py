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
    """Two of five without it, five of five with it, on the scripted model."""
    policy, scenarios, once = pieces
    plain = sum(once(s, False, policy, None)["ok"] for s in scenarios)
    guarded = sum(once(s, True, policy, None)["ok"] for s in scenarios)
    assert plain == 2
    assert guarded == 5


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
    assert refused == 3


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

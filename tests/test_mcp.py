"""The MCP server exposes the checker, so these hold it to the checker's answers.

The point of the server is that a model gets a verdict it did not produce. A
test that only asserted "returns a string" would pass while the server quietly
stopped proving anything, so each of these pins the verdict itself.
"""
import pathlib

import pytest

mcp = pytest.importorskip("mcp", reason="the mcp extra is not installed")

from eleph.mcp_server import (  # noqa: E402
    eleph_check,
    eleph_declarations,
    eleph_obligations,
    eleph_simulate,
)

HERE = pathlib.Path(__file__).parent.parent
def example(name):
    return (HERE / "examples" / name).read_text()


def test_check_proves_the_correct_airline():
    out = eleph_check(example("airline.eleph"))
    assert "PROVADO" in out and "REPROVADO" not in out


def test_check_refuses_the_buggy_airline_and_shows_the_history():
    out = eleph_check(example("airline_buggy.eleph"))
    assert "REPROVADO" in out
    # The counterexample is the product. Without it the tool is an oracle.
    assert "historico que quebra a obrigacao" in out
    assert "cancel_reservation" in out


def test_check_at_a_bound_below_the_threshold_does_not_claim_a_proof():
    out = eleph_check(example("fundo.eleph"), bound=6)
    assert "SEM CONTRAEXEMPLO" in out
    assert "PROVADO" not in out


def test_a_file_that_does_not_parse_says_so_and_checks_nothing():
    out = eleph_check("program x\nfact f(A) :=\n  a(A)\n")
    assert out.startswith("erro:")
    assert "Nothing was checked" in out


def test_no_temporary_path_reaches_the_caller():
    for out in (
        eleph_check(example("airline.eleph")),
        eleph_obligations(example("airline.eleph")),
    ):
        assert "/tmp" not in out
        assert "policy.eleph" in out


def test_obligations_shows_the_path_condition():
    out = eleph_obligations(example("airline_buggy.eleph"))
    assert "supondo" in out and "entao" in out


def test_simulate_answers_from_the_history_it_was_given():
    src = example("companhia.eleph")
    booked = eleph_simulate(
        src,
        events=[["make_reservation", "alice", "ba117"]],
        ask=[["has_reservation", "alice", "ba117"]],
    )
    assert "has_reservation(alice, ba117) = True" in booked

    cancelled = eleph_simulate(
        src,
        events=[
            ["make_reservation", "alice", "ba117"],
            ["cancel_reservation", "alice", "ba117"],
        ],
        ask=[["has_reservation", "alice", "ba117"]],
    )
    assert "has_reservation(alice, ba117) = False" in cancelled


def test_simulate_refuses_an_undeclared_event_without_dying():
    out = eleph_simulate(
        example("companhia.eleph"),
        events=[["nao_existe", "x"]],
        ask=[["has_reservation", "x", "y"]],
    )
    assert "REFUSED" in out
    assert "0 world events" in out


def test_declarations_expands_a_fact_body():
    out = eleph_declarations(example("companhia.eleph"))
    assert "has_reservation(P, F) :=" in out
    # A name without its formula is the label off a jar.
    assert "desde entao nenhum" in out
    assert "..." not in out.split("facts")[1].split("on question")[0]


def test_every_tool_survives_an_empty_source():
    for fn in (eleph_check, eleph_obligations, eleph_declarations):
        assert fn("").startswith("erro:")

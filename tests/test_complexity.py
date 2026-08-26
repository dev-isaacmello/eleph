"""How hard is this problem, and is an SMT solver the right hammer for it?

    THEOREM. Deciding whether an obligation of the atom fragment (no counting)
    can be violated is NP-complete.

    In NP. By the threshold theorem a violating history, if one exists, has
    length at most the number of atoms, hence polynomial in the formula. It is
    checked in O(|phi| * N). So a violating history is a polynomial witness.

    NP-hard. Reduce SAT. Give each propositional variable x_i its own nullary
    event a_i, and read x_i as `a_i` -- which in this language means "a_i has
    happened at least once". Occurrences are independent and monotone, so every
    truth assignment is realised by some history and every history induces an
    assignment. A CNF formula maps clause for clause, and it is satisfiable
    exactly when some history makes the translation true. []

    So no polynomial algorithm is expected, and handing the search to an SMT
    solver is the appropriate move rather than a shortcut -- the exponential
    here is the ordinary NP one, not something worse hiding in the temporal
    operators.

The reduction is not merely stated below. It is run: random 3-SAT instances
are pushed through the checker and the verdict compared against brute force.
"""

import itertools
import random

from eleph.obligations import derive
from eleph.parser import parse
from eleph.verify import verify


def to_program(clauses, n_vars) -> str:
    """SAT instance -> eleph program whose obligation fails iff it is SAT.

    The program answers `no` to "does phi hold?", so its obligation is
    `phi is false in every history`. A counterexample to that obligation *is*
    a satisfying assignment.
    """
    events = "\n".join(f"event a{i}()" for i in range(1, n_vars + 1))
    body = " and ".join(
        "(" + " or ".join(("a%d" % v) if pos else ("not a%d" % v)
                          for v, pos in clause) + ")"
        for clause in clauses)
    return f"""program sat
{events}
fact phi() := {body}

on question(C, phi()):
    answer C no
"""


def eleph_says_satisfiable(clauses, n_vars) -> bool:
    prog = parse(to_program(clauses, n_vars))
    an = derive(prog)
    results = verify(prog, an)
    assert all(r.threshold.complete for r in results), \
        "a reducao deve cair no fragmento decidido"
    return any(not r.ok for r in results)


def brute_force(clauses, n_vars) -> bool:
    for bits in itertools.product([False, True], repeat=n_vars):
        assign = {i + 1: bits[i] for i in range(n_vars)}
        if all(any(assign[v] == pos for v, pos in clause) for clause in clauses):
            return True
    return False


def random_3sat(rng, n_vars, n_clauses):
    return [[(v, rng.choice([True, False]))
             for v in rng.sample(range(1, n_vars + 1), 3)]
            for _ in range(n_clauses)]


# ------------------------------------------------------- the reduction runs

def test_the_sat_reduction_agrees_with_brute_force():
    """Random 3-SAT near the hard ratio, decided both ways."""
    rng = random.Random(4242)
    n_vars, checked, sat_seen, unsat_seen = 6, 0, 0, 0
    for _ in range(24):
        clauses = random_3sat(rng, n_vars, rng.randrange(18, 30))
        truth = brute_force(clauses, n_vars)
        assert eleph_says_satisfiable(clauses, n_vars) == truth, clauses
        checked += 1
        sat_seen += truth
        unsat_seen += not truth
    assert checked == 24
    assert sat_seen and unsat_seen, "as instancias devem cobrir os dois casos"


def test_a_trivially_unsatisfiable_instance_is_unsatisfiable():
    """x and not x, written the long way."""
    clauses = [[(1, True), (1, True), (1, True)],
               [(1, False), (1, False), (1, False)]]
    assert not brute_force(clauses, 1)
    assert not eleph_says_satisfiable(clauses, 1)


def test_the_counterexample_is_a_satisfying_assignment():
    """A violating history is not just evidence, it is the witness itself:
    the events that occur are the variables set true."""
    clauses = [[(1, True), (2, True), (3, True)],
               [(1, False), (2, False), (3, True)]]
    prog = parse(to_program(clauses, 3))
    an = derive(prog)
    bad = [r for r in verify(prog, an) if not r.ok]
    assert bad

    occurred = {e.split("(")[0] for e in bad[0].trace or []
                if not e.startswith("disse-")}
    assign = {i: f"a{i}" in occurred for i in (1, 2, 3)}
    assert all(any(assign[v] == pos for v, pos in c) for c in clauses)


def test_witness_length_stays_within_the_atom_count():
    """The NP membership argument: the witness is polynomial, not merely
    finite."""
    rng = random.Random(7)
    for _ in range(6):
        n_vars = rng.randrange(3, 7)
        clauses = random_3sat(rng, n_vars, 5)
        if not brute_force(clauses, n_vars):
            continue
        prog = parse(to_program(clauses, n_vars))
        an = derive(prog)
        bad = [r for r in verify(prog, an) if not r.ok][0]
        world = [e for e in bad.trace or [] if not e.startswith("disse-")]
        assert len(world) <= n_vars

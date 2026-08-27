"""Numbers, permission and offer: the three things the language was missing.

Permission is the one that matters most, and it is the one an ordinary review
never asks about. A support agent that truthfully reports any customer's
balance to whoever asks has told no lie at all, and every other obligation in
this language would pass it.
"""

import pytest

from eleph import NotPermitted, Policy, Ungrounded
from eleph.core import ResolveError
from eleph.obligations import derive
from eleph.parser import parse
from eleph.runtime import Event, Machine
from eleph.verify import verify

MONEY = """program cobranca
sort User
event charged(u: User, amount: Number)
event refunded(u: User, amount: Number)
fact owes_a_lot(U: User) := charged(U, amount > 100) since_not refunded(U, amount > 0)
"""

DOORS = """program suporte
sort Cliente
event abriu_conta(c: Cliente)
event fechou_conta(c: Cliente)
event autenticou(quem: Party, c: Cliente)
event deslogou(quem: Party, c: Cliente)
fact ativa(C: Cliente) := abriu_conta(C) since_not fechou_conta(C)
fact pode_perguntar(Q: Party, C: Cliente) := autenticou(Q, C) since_not deslogou(Q, C)
"""

LOCKED = DOORS + """
on question(Quem, ativa(C)) permitted pode_perguntar(Quem, C):
    answer Quem with ativa(C)
"""


def analyse(src):
    prog = parse(src)
    an = derive(prog)
    return prog, an, verify(prog, an)


# --------------------------------------------------------------- numbers

def test_a_comparison_is_read_at_the_instant_the_event_happens():
    """Which is what keeps the completeness argument intact: the test is part
    of the atom, not a separate fact that could move underneath it."""
    g = Policy(MONEY).guard(audit=True)
    assert not g.holds("owes_a_lot", "ana")
    g.record("charged", "ana", 50)
    assert not g.holds("owes_a_lot", "ana")
    g.record("charged", "ana", 500)
    assert g.holds("owes_a_lot", "ana")
    g.record("refunded", "ana", 500)
    assert not g.holds("owes_a_lot", "ana")


def test_a_numeric_program_is_still_decided_exhaustively():
    _, _, res = analyse(MONEY + """
on question(C, owes_a_lot(U)):
    answer C with owes_a_lot(U)
""")
    assert all(r.proved for r in res)


def test_an_off_by_one_threshold_is_caught_with_the_witnessing_amount():
    """The guard tests > 50 where the fact requires > 100, and the shortest
    history that separates them is a charge of exactly 100."""
    _, _, res = analyse(MONEY + """
on question(C, owes_a_lot(U)):
    if charged(U, amount > 50) since_not refunded(U, amount > 0):
        answer C yes
    else:
        answer C no
""")
    bad = [r for r in res if not r.ok]
    assert len(bad) == 1
    assert any("amount=100" in e for e in bad[0].trace)


@pytest.mark.parametrize("body,complaint", [
    ("charged(U, X)", "numerico"),
    ("charged(U, valor > 5)", "chama-se"),
    ("charged(U > 1, amount > 1)", "compara um valor"),
])
def test_numeric_fields_are_type_checked(body, complaint):
    with pytest.raises(ResolveError, match=complaint):
        analyse(MONEY + f"\nfact f(U: User) := {body}\n")


# ------------------------------------------------------------ permission

def test_a_party_without_permission_is_not_answered():
    m = Machine(parse(LOCKED))
    for e in [("abriu_conta", ("ana",)), ("autenticou", ("ana", "ana"))]:
        m.append(Event(*e))

    m.deliver("question", "ana", "ativa", ("ana",))
    assert "programa: yes" in " ".join(m.transcript)

    with pytest.raises(NotPermitted, match="nao tem permissao"):
        m.deliver("question", "bruno", "ativa", ("ana",))


def test_permission_can_be_withdrawn():
    """It is a fact over the past like any other, so logging out revokes it."""
    m = Machine(parse(LOCKED))
    for e in [("abriu_conta", ("ana",)), ("autenticou", ("ana", "ana"))]:
        m.append(Event(*e))
    m.deliver("question", "ana", "ativa", ("ana",))
    m.append(Event("deslogou", ("ana", "ana")))
    with pytest.raises(NotPermitted):
        m.deliver("question", "ana", "ativa", ("ana",))


def test_the_answer_is_only_owed_where_the_caller_was_entitled_to_ask():
    """The permission joins the path condition, so it is proved with the rest
    rather than checked off to one side."""
    _, an, res = analyse(LOCKED)
    assert all(r.proved for r in res)
    assumed = " ".join(str(a.expr) for ob in an.obligations
                       for a in ob.assumptions)
    assert "autenticou" in assumed


def test_a_locked_door_beside_an_open_window_is_a_defect():
    """One handler requiring permission and its neighbour requiring none is
    not a policy. Nobody catches this in review; everybody catches it in the
    incident report."""
    _, an, _ = analyse(LOCKED + """
on request(Quem, ativa(C)):
    if ativa(C):
        accept Quem
    else:
        decline Quem
""")
    assert [s.kind for s in an.structural] == ["unguarded-door"]


def test_a_subject_nobody_protects_is_left_alone():
    """Public information is allowed to be public."""
    _, an, _ = analyse(DOORS + """
on question(Quem, ativa(C)):
    answer Quem with ativa(C)
""")
    assert not an.structural


# ----------------------------------------------------------------- offer

def test_an_offer_must_be_one_the_program_could_honour():
    _, _, res = analyse(DOORS + """
on request(Quem, abriu_conta(C)):
    record abriu_conta(C)
    accept Quem
    offer Quem that ativa(C)
""")
    offer = [r for r in res if "oferta" in r.obligation.title]
    assert len(offer) == 1 and offer[0].ok


def test_offering_what_no_path_can_bring_about_is_refused():
    """A lie told in the future tense is still a lie."""
    _, _, res = analyse(DOORS + """
on request(Quem, abriu_conta(C)):
    accept Quem
    offer Quem that ativa(C)
""")
    offer = [r for r in res if "oferta" in r.obligation.title]
    assert len(offer) == 1 and not offer[0].ok


def test_an_offer_is_not_a_debt():
    """Nobody has taken it up, so there is nothing outstanding yet."""
    prog = parse(DOORS + """
on request(Quem, abriu_conta(C)):
    record abriu_conta(C)
    accept Quem
    offer Quem that ativa(C)
""")
    m = Machine(prog)
    m.deliver("request", "ana", "abriu_conta", ("ana",))
    assert m.ledger == []
    assert any("ofereco" in l for l in m.transcript)
    assert any(e.name == "@offer:abriu_conta" for e in m.log)

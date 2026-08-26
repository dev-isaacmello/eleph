#!/usr/bin/env python
"""Three ways to put this into a Python system, cheapest first.

    python examples/agente.py

The fake agent below is deliberately the agent everyone actually ships: it
calls tools, it asserts things about the customer, and it promises. It is also
wrong twice, in the two ways the field reports as its dominant failures --
asserting something the record does not support, and promising something it
never does.
"""

import pathlib

from eleph import Policy, Ungrounded

HERE = pathlib.Path(__file__).parent


# --------------------------------------------------------------------------
# 1. OBSERVER. The agent is untouched. You feed the guard what happened and
#    ask it what is true. Nothing can break; nothing is enforced yet. This is
#    the shape that costs nothing to adopt, and it is how the tau-bench audit
#    in bench/taubench/ works over someone else's traces.
# --------------------------------------------------------------------------

def observer(policy):
    print("\n1. OBSERVADOR -- so olha\n")
    g = policy.guard()

    for event in [("make_reservation", "alice", "ba117"),
                  ("make_reservation", "bruno", "ba117"),
                  ("cancel_reservation", "alice", "ba117")]:
        g.record(*event)
        print(f"   {event[0]}({', '.join(event[1:])})")

    print()
    for who in ("alice", "bruno"):
        print(f"   {who} tem reserva? {g.holds('has_reservation', who, 'ba117')}")
    print(f"   ainda cabe alguem no ba117? {g.holds('seats_left', 'ba117')}")


# --------------------------------------------------------------------------
# 2. GUARD. The agent's assertions go through it. An assertion the history
#    does not support is not softened or logged -- it raises. This is where a
#    guideline stops being a guideline.
# --------------------------------------------------------------------------

class Agente:
    """Stands in for whatever is generating your text."""

    def __init__(self, guard):
        self.g = guard

    def responder(self, pergunta, resposta_do_modelo, fato, *args):
        """The model proposes a yes/no; the log disposes."""
        try:
            self.g.assert_answer(fato, resposta_do_modelo, *args)
            print(f"   > {pergunta}\n     agente: "
                  f"{'sim' if resposta_do_modelo else 'nao'}")
        except Ungrounded as e:
            print(f"   > {pergunta}\n     RECUSADO: {e}")

    def executar(self, ferramenta, exige, *args):
        """A tool that may only run when its precondition holds."""
        try:
            self.g.require(exige, *args)
            self.g.record(ferramenta, *args)
            print(f"   > {ferramenta}({', '.join(args)}) -- feito")
        except Ungrounded as e:
            print(f"   > {ferramenta}({', '.join(args)})\n     RECUSADO: {e}")


def guarda(policy):
    print("\n\n2. GUARDA -- o modelo propoe, o log dispoe\n")
    g = policy.guard()
    a = Agente(g)

    g.record("make_reservation", "alice", "ba117")

    a.responder("alice tem reserva?", True, "has_reservation", "alice", "ba117")

    # o modelo confunde "fez uma reserva" com "tem uma reserva"
    g.record("cancel_reservation", "alice", "ba117")
    a.responder("alice ainda tem reserva?", True,
                "has_reservation", "alice", "ba117")

    # e tenta dar assento a quem nao tem reserva
    a.executar("assign_seat", "has_reservation", "alice", "ba117")


# --------------------------------------------------------------------------
# 3. LEDGER. What the system promised, to whom, and whether it delivered.
#    This is the category the field reports as its largest, and the one no
#    output filter can see: the agent said it would, and then did not.
# --------------------------------------------------------------------------

def livro(policy, log):
    print("\n\n3. LIVRO -- o que foi prometido, e o que foi pago\n")
    g = policy.guard(log=log)

    g.record("make_reservation", "bruno", "lh42")
    g.promise("bruno", "has_seat", "bruno", "lh42",
              before=("board", ("bruno", "lh42")))
    print("   agente: 'voce tera assento antes de embarcar'")

    g.record("board", "bruno", "lh42")            # embarcou sem assento
    print("   bruno embarcou.\n")
    print("  " + g.report().replace("\n", "\n  "))
    g.machine.store.close()

    print("\n   -- processo morre aqui --\n")
    revivido = policy.guard(log=log)
    print("  " + revivido.report().replace("\n", "\n  "))
    print("\n   nada foi salvo alem de eventos. o livro e derivado.")


def main():
    policy = Policy.from_file(HERE / "companhia.eleph")
    report = policy.verify()
    print(f"\npolitica: examples/companhia.eleph")
    print(f"verificacao estatica: {report.summary()}")

    observer(policy)
    guarda(policy)

    log = HERE / ".agente-demo.jsonl"
    log.unlink(missing_ok=True)
    livro(policy, log)
    log.unlink(missing_ok=True)
    print()


if __name__ == "__main__":
    main()

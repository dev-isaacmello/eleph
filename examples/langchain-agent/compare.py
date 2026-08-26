#!/usr/bin/env python
"""The same agent, with and without eleph underneath.

    python compare.py                # roteirizado, sem chave e sem gasto
    python compare.py --live         # Claude de verdade, precisa de credito
    python compare.py --live -n 5    # cinco rodadas por cenario

What is measured is not what the agent said. It is what happened to the data:
each scenario has a known correct final state, and a run passes only if the
backend ends up there. Three of the five scenarios are cases where doing
nothing is correct, so an agent that always acts cannot score well by luck.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import build, load_policy, run, seed          # noqa: E402
from scenarios import SCENARIOS                          # noqa: E402

OK, BAD, DIM, WARN, OFF = "\033[32m", "\033[31m", "\033[2m", "\033[33m", "\033[0m"


def once(scenario, guarded, policy, model):
    """One conversation, from a clean backend."""
    backend = scenario.setup()
    guard = seed(policy.guard(), backend) if guarded else None
    agent = build(backend, guard, model)
    try:
        messages = run(agent, scenario.message)
    except Exception as e:                        # noqa: BLE001
        return {"ok": False, "error": str(e)[:120], "refusals": 0,
                "ledger": [], "reply": ""}

    refusals = sum(1 for m in messages
                   if getattr(m, "type", "") == "tool"
                   and "RECUSADO" in str(m.content))
    reply = next((m.content for m in reversed(messages)
                  if getattr(m, "type", "") == "ai" and m.content), "")
    return {"ok": bool(scenario.expected(backend)), "error": None,
            "refusals": refusals, "reply": str(reply)[:150],
            "ledger": [c.status for c in guard.ledger] if guard else []}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true",
                    help="usar Claude de verdade (requer ANTHROPIC_API_KEY)")
    ap.add_argument("-n", "--runs", type=int, default=1,
                    help="rodadas por cenario, para medir taxa e nao anedota")
    ap.add_argument("--no-color", action="store_true")
    args = ap.parse_args()

    if not args.live:
        os.environ["ELEPH_OFFLINE"] = "1"

    def c(code, text):
        return text if args.no_color else f"{code}{text}{OFF}"

    policy = load_policy()
    report = policy.verify()
    print(f"\n  politica: policy.eleph")
    print(f"  {c(DIM, report.summary())}")
    mode = "Claude ao vivo" if args.live else "modelo roteirizado (ilustracao)"
    print(f"  modelo: {mode}, {args.runs} rodada(s) por cenario")
    if not args.live:
        print(c(WARN, "  o modo roteirizado demonstra o mecanismo. Ele nao diz"))
        print(c(WARN, "  nada sobre com que frequencia um modelo real erra."))
    print()

    width = max(len(s.name) for s in SCENARIOS)
    totals = {False: 0, True: 0}
    attempts = 0
    all_refusals = 0
    ledgers = []

    print(f"  {'cenario':{width}}  {'sem eleph':>11}  {'com eleph':>11}")
    for scenario in SCENARIOS:
        line = {}
        for guarded in (False, True):
            good = 0
            for _ in range(args.runs):
                r = once(scenario, guarded, policy, None)
                good += r["ok"]
                all_refusals += r["refusals"]
                if guarded:
                    ledgers += r["ledger"]
            totals[guarded] += good
            line[guarded] = good
        attempts += args.runs

        def cell(n):
            mark = OK if n == args.runs else BAD
            return c(mark, f"{n}/{args.runs}")

        print(f"  {scenario.name:{width}}  {cell(line[False]):>20}  "
              f"{cell(line[True]):>20}")

    print()
    print(f"  {'TOTAL':{width}}  "
          f"{c(OK if totals[False] == attempts else BAD, f'{totals[False]}/{attempts}'):>20}  "
          f"{c(OK if totals[True] == attempts else BAD, f'{totals[True]}/{attempts}'):>20}")
    print()
    print(f"  operacoes recusadas pela politica: {all_refusals}")
    if ledgers:
        print(f"  compromissos registrados no livro: {len(ledgers)} "
              f"({', '.join(sorted(set(ledgers)))})")
        print(c(DIM, "  o lado sem eleph nao tem livro nenhum: a promessa de"))
        print(c(DIM, "  reembolso e texto que passou na tela."))
    print()
    print(c(DIM, "  As duas colunas sao o mesmo agente: mesmo modelo, mesmo"))
    print(c(DIM, "  prompt, mesmos nomes e assinaturas de ferramenta. A unica"))
    print(c(DIM, "  diferenca e um Guard embaixo das duas que escrevem."))
    print()

    for scenario in SCENARIOS:
        print(c(DIM, f"  {scenario.name}: {scenario.why}"))
    print()


if __name__ == "__main__":
    main()

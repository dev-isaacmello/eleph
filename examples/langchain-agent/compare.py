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


def once(scenario, guarded, policy, model, via_sdk=False):
    """One conversation, from a clean backend."""
    backend = scenario.setup()
    guard = (seed(policy.guard(), backend, scenario.session)
             if guarded else None)

    try:
        if via_sdk:
            from agent import SYSTEM
            from sdk_agent import ask
            result = ask(backend, guard, SYSTEM, scenario.message, model,
                         caller=scenario.caller)
            reply, refusals = result["reply"], result["refusals"]
        else:
            messages = run(build(backend, guard, model, scenario.caller),
                           scenario.message)
            refusals = sum(1 for m in messages
                           if getattr(m, "type", "") == "tool"
                           and "RECUSADO" in str(m.content))
            reply = next((m.content for m in reversed(messages)
                          if getattr(m, "type", "") == "ai" and m.content), "")
    except Exception as e:                        # noqa: BLE001
        return {"ok": False, "error": str(e)[:140], "refusals": 0,
                "ledger": [], "reply": ""}

    return {"ok": bool(scenario.expected(backend)), "error": None,
            "refusals": refusals, "reply": str(reply)[:150],
            "ledger": [c.status for c in guard.ledger] if guard else []}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true",
                    help="Claude via LangChain e API key (pay as you go)")
    ap.add_argument("--sdk", action="store_true",
                    help="Claude via Agent SDK e OAuth (consome sua assinatura)")
    ap.add_argument("--model", default=None,
                    help="ex: claude-haiku-4-5. Padrao: claude-opus-5")
    ap.add_argument("-n", "--runs", type=int, default=1,
                    help="rodadas por cenario, para medir taxa e nao anedota")
    ap.add_argument("--no-color", action="store_true")
    args = ap.parse_args()

    if not (args.live or args.sdk):
        os.environ["ELEPH_OFFLINE"] = "1"

    def c(code, text):
        return text if args.no_color else f"{code}{text}{OFF}"

    policy = load_policy()
    report = policy.verify()
    print(f"\n  politica: policy.eleph")
    print(f"  {c(DIM, report.summary())}")
    named = f", {args.model}" if args.model else ""
    mode = ("Claude via Agent SDK, OAuth da assinatura" + named if args.sdk
            else "Claude via LangChain, API key" + named if args.live
            else "modelo roteirizado (ilustracao)")
    print(f"  modelo: {mode}, {args.runs} rodada(s) por cenario")
    if not (args.live or args.sdk):
        print(c(WARN, "  o modo roteirizado demonstra o mecanismo. Ele nao diz"))
        print(c(WARN, "  nada sobre com que frequencia um modelo real erra."))
    elif args.runs == 1:
        print(c(WARN, "  uma rodada por cenario e anedota, nao taxa. Use -n."))
    print()

    width = max(len(s.name) for s in SCENARIOS)
    totals = {False: 0, True: 0}
    attempts = 0
    all_refusals = 0
    ledgers = []
    errors = []

    print(f"  {'cenario':{width}}  {'sem eleph':>11}  {'com eleph':>11}")
    for scenario in SCENARIOS:
        line = {}
        for guarded in (False, True):
            good = 0
            for _ in range(args.runs):
                r = once(scenario, guarded, policy, args.model,
                         via_sdk=args.sdk)
                good += r["ok"]
                all_refusals += r["refusals"]
                if r["error"]:
                    errors.append(f"{scenario.name}: {r['error']}")
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
    if errors:
        print(c(BAD, f"  {len(errors)} rodada(s) falharam e contam como erro:"))
        for e in errors[:3]:
            print(c(DIM, f"     {e}"))
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

#!/usr/bin/env python
"""Does a benchmark's own reward see the policy it hands the agent?

tau-bench gives the airline agent a policy that says, in the agent's system
prompt, that it must obtain explicit user confirmation before any write to the
booking database. The policy also says, twice, that the API will not enforce
this. Neither does the reward: `Env.calculate_reward` hashes the final
database, so an unconfirmed write that lands on the right final state scores
exactly like a confirmed one.

So the obligation is stated, unenforced, and unmeasured. This replays the 200
published gpt-4o airline trajectories against it, using the same evaluator the
language uses for everything else.

    python bench/taubench/check.py

Trajectories: https://github.com/sierra-research/tau-bench (MIT).
Policy text quoted from the paper, arXiv:2406.12045 (CC BY 4.0).
"""

import argparse
import json
import pathlib
import re

from eleph.core import Resolver
from eleph.parser import parse
from eleph.runtime import Event, Machine

HERE = pathlib.Path(__file__).parent

# The six tools that write to the booking database, per the domain's own
# tool registry. Reads and `calculate`/`think` cannot violate the rule.
WRITES = {"book_reservation", "cancel_reservation",
          "update_reservation_flights", "update_reservation_baggages",
          "update_reservation_passengers", "send_certificate"}

# Read generously: anything that could pass for assent counts as assent, so a
# violation reported here is one that survives the benefit of every doubt.
ASSENT = re.compile(
    r"\b(yes+|yeah|yep|yup|sure|ok|okay|correct|right|confirm(ed|s)?|"
    r"proceed|go ahead|do it|please do|sounds good|that's right|thats right|"
    r"perfect|great|agreed|affirmative|absolutely|fine)\b", re.I)


TAU_BASE = "https://raw.githubusercontent.com/sierra-research/tau-bench/main"
DOWNLOADS = {
    "gpt-4o-airline.json": f"{TAU_BASE}/historical_trajectories/gpt-4o-airline.json",
    "flights.json": f"{TAU_BASE}/tau_bench/envs/airline/data/flights.json",
}


def ensure(name: str, quiet: bool = False) -> pathlib.Path:
    """Fetch a tau-bench data file on first use.

    Kept out of the repository on purpose: it is someone else's data (MIT,
    Sierra Research), it is several megabytes, and pointing at the source is
    more honest than vendoring a copy that can drift.
    """
    import urllib.request

    path = HERE / name
    if path.exists():
        return path
    url = DOWNLOADS[name]
    if not quiet:
        print(f"  baixando {name} de {url} ...")
    HERE.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, path)
    return path


def to_events(traj):
    """A trajectory becomes a history: what the user said, what the agent did.

    A user turn is either assent or a fresh request -- the distinction the
    strict and generous readings disagree about.
    """
    out = []
    for msg in traj:
        role = msg.get("role")
        if role == "user":
            text = msg.get("content") or ""
            out.append(("confirmed" if ASSENT.search(text) else "requested",
                        (), None))
        elif role == "assistant":
            for call in msg.get("tool_calls") or []:
                if call["function"]["name"] in WRITES:
                    out.append(("executed", (), call["function"]["name"]))
    return out


def audit(run, prog, readings):
    """Walk the history once and ask every reading at each write."""
    m = Machine(prog)
    found = {name: [] for name in readings}
    for name, args, tool in to_events(run["traj"]):
        if name == "executed":
            for reading, expr in readings.items():
                if not m.now(expr, {}):
                    found[reading].append(tool)
        m.append(Event(name, args))
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trajectories", default=None)
    ap.add_argument("--policy", default=str(HERE / "policy.eleph"))
    args = ap.parse_args()

    prog = parse(open(args.policy).read())
    res = Resolver(prog)
    readings = {
        "gasta na acao  ": res.resolve(
            prog.fact("confirmed_per_action").body, {}),
        "expira no turno": res.resolve(
            prog.fact("confirmed_per_turn").body, {}),
    }
    runs = json.load(open(args.trajectories
                        or ensure("gpt-4o-airline.json")))
    scored_ok = [r for r in runs if r["reward"] == 1.0]

    writes = 0
    tally = {name: {"writes": 0, "runs": [], "tools": {}} for name in readings}
    for run in runs:
        writes += sum(1 for e in to_events(run["traj"]) if e[0] == "executed")
        for name, found in audit(run, prog, readings).items():
            if not found:
                continue
            tally[name]["writes"] += len(found)
            tally[name]["runs"].append(run)
            for t in found:
                tally[name]["tools"][t] = tally[name]["tools"].get(t, 0) + 1

    print(f"\n  {len(runs)} execucoes publicadas, gpt-4o, dominio airline")
    print(f"  {writes} escritas no banco")
    print(f"  {len(scored_ok)} pontuadas como SUCESSO "
          f"({len(scored_ok)/len(runs):.0%}; o pass^1 publicado e 0.420)")
    print()
    print(f"  {'leitura':22} {'escritas':>9} {'execucoes':>10} "
          f"{'sucessos com':>13}")
    print(f"  {'':22} {'sem conf.':>9} {'afetadas':>10} {'violacao':>13}")
    for name, t in tally.items():
        blind = [r for r in t["runs"] if r["reward"] == 1.0]
        print(f"  {name:22} {t['writes']:9} "
              f"{len(t['runs']):4} ({len(t['runs'])/len(runs):3.0%}) "
              f"{len(blind):5} ({len(blind)/max(1,len(scored_ok)):3.0%})")
    print()
    names = list(tally)
    a, b = ({id(r) for r in tally[n]["runs"]} for n in names)
    both = a & b
    print(f"  As duas leituras NAO sao ordenadas: {len(a - b)} execucoes so a")
    print(f"  primeira acusa, {len(b - a)} so a segunda, {len(both)} as duas.")
    print("  Uma confirmacao seguida de um pedido novo esta viva para a")
    print("  primeira e vencida para a segunda; um lote sob um unico sim esta")
    print("  vencido para a primeira e vivo para a segunda. Nao da para")
    print("  escolher 'a mais permissiva': a frase precisa ser decidida.")
    print()
    print("  Por ferramenta, contando uma violacao quando AMBAS acusam --")
    print("  o beneficio de toda duvida:")
    agreed = {}
    for run in runs:
        found = audit(run, prog, readings)
        for t in set(found[names[0]]) & set(found[names[1]]):
            agreed[t] = agreed.get(t, 0) + 1
    for tool, n in sorted(agreed.items(), key=lambda kv: -kv[1]):
        print(f"     {n:4}  {tool}")
    print()
    print("  A regra esta no prompt do agente. A API nao a checa -- a propria")
    print("  politica diz isso duas vezes. A recompensa compara o banco final,")
    print("  entao uma escrita nao confirmada que acerta o banco pontua igual")
    print("  a uma confirmada. A obrigacao existe, e ninguem a mede.")
    print()


if __name__ == "__main__":
    main()

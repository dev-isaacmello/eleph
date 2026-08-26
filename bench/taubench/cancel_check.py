#!/usr/bin/env python
"""The rule tau-bench's own API refuses to enforce.

The airline wiki states cancellation eligibility and then says, with an
exclamation mark, "The API does not check these for the agent, so the agent
must make sure the rules apply before calling the API!". It is not exaggerating:
`cancel_reservation` performs no validation of any kind -- it mirrors the
payments and flips a status field.

The reward does not check it either, because a cancellation that was forbidden
still produces the same final database as one that was allowed, whenever the
ground truth also cancelled.

So this replays the 200 published gpt-4o airline trajectories and asks, at each
cancellation, whether the reservation was eligible.

    python bench/taubench/cancel_check.py
"""

import argparse
import json
import pathlib
import re
from datetime import datetime, timedelta

from eleph import Policy

HERE = pathlib.Path(__file__).parent

# The wiki fixes the clock: "The current time is 2024-05-15 15:00:00 EST."
NOW = datetime(2024, 5, 15, 15, 0, 0)

# "enables full refund if the user needs to cancel the flight given health or
# weather reasons" -- read generously, so a violation survives every doubt.
COVERED = re.compile(
    r"\b(health|ill|illness|sick|medical|doctor|hospital|emerg\w*|injur\w*|"
    r"weather|storm|snow|hurricane|flood|fog|blizzard|typhoon)\w*", re.I)


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


def load_flights():
    try:
        return json.load(open(ensure("flights.json")))
    except Exception:                      # offline: say so, do not guess
        return {}


def cabin_event(cabin):
    """The cabin is an attribute that changes; report the change, not a fact."""
    return "cabin_set_business" if cabin == "business" else "cabin_set_other"


def classify(res, flights, said):
    """What the host knows that the logic cannot work out for itself."""
    out = []
    try:
        made = datetime.fromisoformat(res["created_at"])
        if NOW - made <= timedelta(hours=24):
            out.append("booked_within_24h")
    except (KeyError, ValueError):
        pass

    for leg in res.get("flights", []):
        rec = flights.get(leg.get("flight_number"), {})
        if rec.get("dates", {}).get(leg.get("date"), {}).get("status") == "cancelled":
            out.append("airline_cancelled_flight")
            break

    if res.get("insurance") == "yes":
        out.append("has_insurance")
    if COVERED.search(said):
        out.append("reason_is_covered")
    return out


def audit(run, policy, flights):
    """Walk one trajectory, classifying reservations as they are looked up."""
    g = policy.guard()
    known, emitted, cabin_now, said = {}, set(), {}, ""

    def set_cabin(rid, cabin):
        """Only a change is an event. Repeating the same cabin is not news."""
        if cabin and cabin_now.get(rid) != cabin:
            cabin_now[rid] = cabin
            g.record(cabin_event(cabin), rid)
    allowed, forbidden, unknown = 0, [], 0

    for msg in run["traj"]:
        if msg.get("role") == "user":
            said += " " + (msg.get("content") or "")

        if msg.get("role") == "tool" and msg.get("name") == "get_reservation_details":
            try:
                rec = json.loads(msg["content"])
                known[rec["reservation_id"]] = rec
                set_cabin(rec["reservation_id"], rec.get("cabin"))
            except (ValueError, KeyError, TypeError):
                pass

        for call in msg.get("tool_calls") or []:
            name = call["function"]["name"]

            # A cabin change before the cancellation changes the answer:
            # "business flights can always be cancelled". Reading eligibility
            # off the reservation as first fetched would call an upgrade-then-
            # cancel a violation, and it is not one.
            if name == "update_reservation_flights":
                try:
                    kw = json.loads(call["function"]["arguments"])
                    rid = kw["reservation_id"]
                    if rid in known and kw.get("cabin"):
                        known[rid] = dict(known[rid], cabin=kw["cabin"])
                        set_cabin(rid, kw["cabin"])
                except (ValueError, KeyError, TypeError):
                    pass
                continue

            if name != "cancel_reservation":
                continue
            try:
                rid = json.loads(call["function"]["arguments"])["reservation_id"]
            except (ValueError, KeyError):
                unknown += 1
                continue
            res = known.get(rid)
            if res is None:
                unknown += 1        # the agent cancelled without ever looking
                continue
            for tag in classify(res, flights, said):
                if (tag, rid) not in emitted:
                    g.record(tag, rid)
                    emitted.add((tag, rid))
            verdict = {r: g.holds(r, rid) for r in READINGS}
            if all(verdict.values()):
                allowed += 1
            else:
                forbidden.append((rid, res, verdict))
    return allowed, forbidden, unknown


READINGS = ("cancellable_strict", "cancellable_loose")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trajectories", default=None)
    ap.add_argument("--policy", default=str(HERE / "cancel.eleph"))
    args = ap.parse_args()

    policy = Policy.from_file(args.policy)
    report = policy.verify()
    flights = load_flights()
    runs = json.load(open(args.trajectories
                        or ensure("gpt-4o-airline.json")))

    counts = {r: 0 for r in READINGS}
    both, total, blind = 0, 0, 0
    in_gt = {r: 0 for r in READINGS}
    runs_hit = {r: set() for r in READINGS}
    by_cabin = {}

    for i, run in enumerate(runs):
        a, f, u = audit(run, policy, flights)
        total += a + len(f) + u
        blind += u
        gt = [x["name"] for x in run["info"]["task"].get("actions", [])]
        gt_cancels = "cancel_reservation" in gt
        for rid, res, verdict in f:
            if not any(verdict.values()):
                both += 1
                by_cabin[res.get("cabin")] = by_cabin.get(res.get("cabin"), 0) + 1
            for reading, allowed_here in verdict.items():
                if not allowed_here:
                    counts[reading] += 1
                    runs_hit[reading].add(i)
                    if gt_cancels:
                        in_gt[reading] += 1

    scored_ok = [r for r in runs if r["reward"] == 1.0]

    print(f"\n  politica: {pathlib.Path(args.policy).name}")
    print(f"  verificacao estatica: {report.summary()}")
    if not flights:
        print("  AVISO: flights.json ausente; o numero abaixo e um piso")
    print()
    print(f"  {len(runs)} execucoes, {total} cancelamentos "
          f"({blind} sem como julgar: o agente nem consultou a reserva)")
    print()
    print(f"  {'leitura de \'the condition is met\'':38} {'proibidos':>10} "
          f"{'no gabarito':>12}")
    for reading in READINGS:
        label = ("seguro E motivo coberto (como o tau3 escreveu)"
                 if reading.endswith("strict") else "ter seguro basta")
        hits = [runs[i] for i in runs_hit[reading]]
        blind_ok = sum(1 for r in hits if r["reward"] == 1.0)
        print(f"  {label:38} {counts[reading]:10} {in_gt[reading]:12}")
        print(f"  {'':38} {len(hits):4} execs {blind_ok:5} sucessos")
    print()
    print(f"  proibidos sob AMBAS as leituras: {both}")
    if by_cabin:
        for cabin, n in sorted(by_cabin.items(), key=lambda kv: -kv[1]):
            print(f"     {n:4}  {cabin}")
    print()
    print("  O gabarito do tau-bench cancela reservas que a leitura estrita")
    print("  proibe. Ou seja: a frase da politica esta subespecificada de um")
    print("  jeito que atinge os rotulos de ouro, nao so o agente. Escreve-la")
    print("  como fato e o que torna isso visivel -- e o tau3-bench de fato")
    print("  reescreveu essa frase depois.")
    print()


if __name__ == "__main__":
    main()

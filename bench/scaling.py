#!/usr/bin/env python
"""Does a language whose only state is its history survive a long history?

Naively, no: every question rereads the past, so cost per interaction grows
with the log and the whole thing is quadratic. The index in
`elephant/incremental.py` folds each event in once, in constant time, and
`tests/test_incremental.py` is what says it computes the same answers.

    python bench/scaling.py
"""

import argparse
import pathlib
import time

from eleph.parser import parse
from eleph.runtime import Machine

ROOT = pathlib.Path(__file__).parent.parent


def workload(m, n):
    """Book, ask, cancel, forever."""
    for i in range(n):
        p = f"p{i % 50}"
        if i % 3 == 0:
            m.deliver("request", p, "make_reservation", (p, "ba117"))
        elif i % 3 == 1:
            m.deliver("question", p, "has_reservation", (p, "ba117"))
        else:
            m.deliver("request", p, "cancel_reservation", (p, "ba117"))


def run(prog, n, indexed):
    m = Machine(prog)
    if not indexed:
        m.index.usable = False
    t0 = time.time()
    workload(m, n)
    return time.time() - t0, len(m.log)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--program", default=str(ROOT / "examples/companhia.eleph"))
    ap.add_argument("--naive-upto", type=int, default=2000)
    ap.add_argument("--sizes", default="500,1000,2000,4000,8000,16000,32000")
    args = ap.parse_args()

    prog = parse(open(args.program).read())
    sizes = [int(x) for x in args.sizes.split(",")]

    print(f"\n{args.program}\n")
    print(f"{'interacoes':>10} {'log':>8} {'relendo':>9} {'indice':>8} "
          f"{'ganho':>7} {'ev/s':>8} {'escala':>7}")
    prev_slow = prev_fast = None
    for n in sizes:
        slow = run(prog, n, False)[0] if n <= args.naive_upto else None
        fast, size = run(prog, n, True)

        gain = f"{slow / fast:6.0f}x" if slow else "     -"
        s_slow = f"{slow:9.2f}" if slow else f"{'-':>9}"
        s_scale = f"x{fast / prev_fast:.2f}" if prev_fast else "-"
        print(f"{n:10} {size:8} {s_slow} {fast:8.3f} {gain} "
              f"{size / fast:8.0f} {s_scale:>7}")
        if slow and prev_slow:
            print(f"{'':10} {'':8} {'(x%.1f)' % (slow / prev_slow):>9} "
                  f"{'':8} {'':7} {'':8} {'':>7}")
        prev_slow, prev_fast = slow or prev_slow, fast

    print("\n  'escala' e o tempo relativo ao tamanho anterior, que dobra.")
    print("  x2 significa linear no numero de eventos, ou seja constante por")
    print("  evento. Relendo o log a mesma coluna da x4.\n")


if __name__ == "__main__":
    main()

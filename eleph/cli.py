"""`elephant` -- derive the correctness conditions, try to break them, run the
program against a real dialogue."""

import argparse
import sys

from .core import ResolveError, show
from .lexer import LexError
from .obligations import derive
from .parser import parse, ParseError
from .frontend import ClaudeExtractor, PatternExtractor, interpret
from .runtime import Machine, session, Refusal
from .store import Store
from .verify import verify

OK, BAD, WARN, DIM, OFF = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"


class Style:
    def __init__(self, on):
        self.on = on

    def __call__(self, code, text):
        return f"{code}{text}{OFF}" if self.on else str(text)


def plural(n, one, many):
    return f"{n} {one if n == 1 else many}"


def load(path):
    prog = parse(open(path).read())
    return prog, derive(prog)


# ------------------------------------------------------------------- check

def report(path, bound, objects, colour=True):
    c = Style(colour)
    prog, analysis = load(path)
    results = verify(prog, analysis, bound=bound, objects=objects)
    exhaustive = all(r.threshold.complete for r in results) if results else True

    declared = [e for e in prog.events if not e.synthetic]
    print(f"\n{path}  ->  programa {prog.name}")
    print(c(DIM, f"{plural(len(declared), 'evento', 'eventos')}, "
                 f"{plural(len(prog.facts), 'fato', 'fatos')}, "
                 f"{plural(len(prog.handlers), 'handler', 'handlers')}"))
    print()
    print(f"{plural(len(analysis.obligations), 'obrigacao derivada', 'obrigacoes derivadas')} "
          f"do texto do programa")
    if exhaustive:
        widest = max((r.threshold.bound for r in results), default=0)
        print(c(DIM, f"cada uma checada no seu limiar de completude "
                     f"(o maior: {widest} eventos) -- exaustivo"))
    else:
        print(c(WARN, "verificacao NAO exaustiva neste programa"))
        for r in results:
            if not r.threshold.complete:
                print(c(DIM, f"  linha {r.obligation.line}: "
                             f"{r.threshold.reason}"))
    print()

    failures = 0

    for s in analysis.structural:
        failures += 1
        print(c(BAD, f"  X   {s.handler}  linha {s.line}"))
        print(f"      {s.message}")
        print()

    for r in results:
        ob = r.obligation
        if r.ok:
            mark = "ok " if r.proved else "ok?"
            print(c(OK if r.proved else WARN,
                    f"  {mark} {ob.handler}  linha {ob.line}  -  {ob.title}"))
            if ob.kind == "promise-dischargeable" and r.trace:
                print(c(DIM, f"      {r.trace[0]}"))
            continue

        failures += 1
        print(c(BAD, f"  X   {ob.handler}  linha {ob.line}  -  {ob.title}"))
        print(f"      {ob.detail}")
        print()
        if ob.polarity == "satisfiable":
            print(c(DIM, "      nenhum caminho do programa chega a cumprir isso"))
        else:
            print(c(DIM, "      historico que quebra a obrigacao:"))
            if not r.trace:
                print("        (o log vazio ja basta)")
            for i, ev in enumerate(r.trace or [], 1):
                print(f"        {i}. {ev}")
        if ob.kind == "answer-truthful":
            said = "yes" if ob.claims else "no"
            truth = "no" if ob.claims else "yes"
            print()
            print(f"      o programa responde {c(BAD, said)}, "
                  f"a verdade do log e {c(OK, truth)}")
        print()

    print()
    if failures:
        print(c(BAD, f"REPROVADO  -  "
                     f"{plural(failures, 'obrigacao nao cumprida', 'obrigacoes nao cumpridas')}"))
    elif exhaustive:
        print(c(OK, f"PROVADO  -  "
                    f"{plural(len(analysis.obligations), 'obrigacao vale', 'obrigacoes valem')} "
                    f"para TODO historico, de qualquer tamanho"))
    else:
        print(c(WARN, f"SEM CONTRAEXEMPLO  -  dentro dos limites checados, "
                      f"que nao sao exaustivos aqui"))
    print()
    return 1 if failures else 0


# ------------------------------------------------------------- obligations

def obligations(path, colour=True):
    """Print the correctness conditions without trying to discharge them.

    The point of the exercise: nobody wrote these."""
    c = Style(colour)
    prog, analysis = load(path)
    print(f"\n{path}: condicoes que o proprio texto do programa exige\n")
    for ob in analysis.obligations:
        print(c(DIM, f"  linha {ob.line}  {ob.handler}"))
        print(f"    {ob.title}")
        for a in ob.assumptions:
            print(c(DIM, f"      supondo   {show(a.expr)}"))
        print(c(DIM, f"      entao     {show(ob.goal.expr)}"))
        print()
    for s in analysis.structural:
        print(c(WARN, f"  linha {s.line}  {s.handler}: {s.message}"))
    return 0


# --------------------------------------------------------------------- run

def play(path, script_path, log=None, colour=True):
    c = Style(colour)
    prog = parse(open(path).read())
    try:
        m = session(prog, open(script_path).read(),
                    store=Store(log) if log else None)
    except Refusal as e:
        print(f"\n{c(BAD, 'RECUSA')}: {e}\n")
        return 1

    for line in m.transcript:
        print("  " + line)
    print()

    if m.ledger:
        print(c(DIM, "  livro de compromissos"))
        for cm in m.ledger:
            mark = {"cumprida": OK, "aberta": WARN,
                    "quebrada": BAD, "liberada": DIM}[cm.status]
            label = cm.status.upper().ljust(9)
            print(f"    {c(mark, label)} {cm.describe()}")
        print()

    declared = [e for e in m.log if not e.name.startswith("@")]
    print(c(DIM, f"  log: {plural(len(m.log), 'evento', 'eventos')} "
                 f"({len(declared)} do mundo, "
                 f"{len(m.log) - len(declared)} de fala)"))
    print()

    if m.breached():
        print(c(BAD, f"  {plural(len(m.breached()), 'promessa quebrada', 'promessas quebradas')}"))
        print()
        return 1
    if m.outstanding():
        print(c(WARN, f"  {plural(len(m.outstanding()), 'promessa em aberto', 'promessas em aberto')}"))
        print()
    return 0


# -------------------------------------------------------------------- talk

def talk(path, convo_path, roster, use_claude, log=None, colour=True):
    """Plain language in, speech acts out, the same guarantees underneath."""
    c = Style(colour)
    prog = parse(open(path).read())
    extractor = (ClaudeExtractor(roster=roster) if use_claude
                 else PatternExtractor(roster=roster))
    print(c(DIM, f"\n  extrator: {type(extractor).__name__} "
                 f"(proposicoes, nao decisoes)\n"))

    m = Machine(prog)
    if log:
        m.attach(Store(log))
    try:
        for raw in open(convo_path):
            line = raw.split("#")[0].strip()
            if not line:
                continue
            speaker, _, text = line.partition(":")
            interpret(m, extractor, text.strip(), speaker.strip())
    except Refusal as e:
        for l in m.transcript:
            print("  " + l)
        print(f"\n  {c(BAD, 'RECUSA')}: {e}")
        print(c(DIM, "  o extrator propos; a linguagem recusou.\n"))
        return 1

    for l in m.transcript:
        print("  " + l)
    print()
    return 0


# ------------------------------------------------------------------ ledger

def ledger(path, log, colour=True):
    """What this program still owes, read back off its history."""
    c = Style(colour)
    m = Machine(parse(open(path).read())).attach(Store(log))

    world = [e for e in m.log if not e.name.startswith("@")]
    print(f"\n{log}")
    print(c(DIM, f"  {plural(len(m.log), 'evento', 'eventos')} "
                 f"({len(world)} do mundo, {len(m.log) - len(world)} de fala)"))
    print()
    if not m.ledger:
        print(c(DIM, "  nenhuma promessa foi feita"))
        print()
        return 0

    for cm in m.ledger:
        mark = {"cumprida": OK, "aberta": WARN,
                "quebrada": BAD, "liberada": DIM}[cm.status]
        print(f"  {c(mark, cm.status.upper().ljust(9))} {cm.describe()}")
    print()
    if m.breached():
        print(c(BAD, f"  {plural(len(m.breached()), 'promessa quebrada', 'promessas quebradas')}"))
        print()
        return 1
    if m.outstanding():
        print(c(WARN, f"  {plural(len(m.outstanding()), 'promessa em aberto', 'promessas em aberto')}"))
    print()
    return 0


# -------------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(prog="elephant")
    sub = ap.add_subparsers(dest="cmd", required=True)

    chk = sub.add_parser("check", help="verificar um programa")
    chk.add_argument("file")
    chk.add_argument("--bound", type=int, default=None,
                     help="forcar tamanho do historico (padrao: o limiar de "
                          "completude, que torna o resultado uma prova)")
    chk.add_argument("--objects", type=int, default=None,
                     help="forcar objetos por tipo (padrao: o limiar)")

    obl = sub.add_parser("obligations",
                         help="mostrar as condicoes derivadas, sem verificar")
    obl.add_argument("file")

    run = sub.add_parser("run", help="executar um dialogo contra o programa")
    run.add_argument("file")
    run.add_argument("script")
    run.add_argument("--log", help="historico em disco: retoma e continua nele")

    tlk = sub.add_parser("talk", help="conversar em linguagem natural")
    tlk.add_argument("file")
    tlk.add_argument("conversa")
    tlk.add_argument("--roster", default="",
                     help="nomes conhecidos, separados por virgula")
    tlk.add_argument("--claude", action="store_true",
                     help="usar Claude como extrator (requer credencial)")
    tlk.add_argument("--log", help="historico em disco: retoma e continua nele")

    led = sub.add_parser("ledger", help="o que o programa ainda deve")
    led.add_argument("file")
    led.add_argument("log")

    for p in (chk, obl, run, tlk, led):
        p.add_argument("--no-color", action="store_true")

    args = ap.parse_args(argv)
    colour = not args.no_color

    try:
        if args.cmd == "ledger":
            return ledger(args.file, args.log, colour)
        if args.cmd == "talk":
            roster = [x.strip() for x in args.roster.split(",") if x.strip()]
            return talk(args.file, args.conversa, roster, args.claude,
                        args.log, colour)
        if args.cmd == "run":
            return play(args.file, args.script, args.log, colour)
        if args.cmd == "obligations":
            return obligations(args.file, colour)
        return report(args.file, args.bound, args.objects, colour)
    except (ParseError, LexError, ResolveError) as e:
        print(f"erro: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

"""An MCP server that proves, rather than one that recites.

A documentation server would let a model write a policy from memory and hand it
over unverified, which is the failure this project exists to stop. So the tools
here run the checker: text in, verdict and counterexample out. Nothing is
fetched, nothing is written to disk, and no state survives a call.

    uvx --from "eleph[mcp]" eleph-mcp

The client already knows how to read a file; what it cannot do is run Z3.
"""

import io
from contextlib import redirect_stdout

from mcp.server.mcpserver import MCPServer

from .cli import obligations as _print_obligations, report as _print_report
from .core import ResolveError, show
from .guard import Policy, Ungrounded, UnknownName
from .lexer import LexError
from .obligations import derive
from .parser import ParseError, parse
from .runtime import NotPermitted, Refusal

server = MCPServer(
    name="eleph",
    instructions=(
        "eleph proves properties of a policy file. Write the policy, call "
        "eleph_check, and read the counterexample it prints: it is a sequence "
        "of events, not an opinion. Never hand a user a .eleph file that has "
        "not been through eleph_check. PROVADO means every obligation holds "
        "for every history; SEM CONTRAEXEMPLO means the run was not "
        "exhaustive and is not a proof."
    ),
)


def _capture(fn, *args, **kwargs) -> str:
    """The CLI already renders these well. Reuse it rather than restate it."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn(*args, **kwargs)
    return buf.getvalue().strip()


def _on_temp_file(source: str, fn, *args):
    """Run a CLI entry point over `source`, then take the path back out.

    These commands read a file, and the caller gave text. The temporary path
    that bridges the two is not something the model should ever see: naming it
    invites a tool call that tries to open it.
    """
    import pathlib as _pathlib
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".eleph", delete=False) as fh:
        fh.write(source)
        path = fh.name
    try:
        return _capture(fn, path, *args).replace(path, "policy.eleph")
    except (ParseError, LexError, ResolveError) as exc:
        return _syntax_error(exc)
    finally:
        _pathlib.Path(path).unlink(missing_ok=True)


def _syntax_error(exc) -> str:
    return f"erro: {exc}\n\nThe file did not lex, parse or resolve. Nothing was checked."


@server.tool(
    title="Check an eleph policy",
    description=(
        "Discharge every obligation the policy's own text demands, each at its "
        "completeness threshold. Returns the verdict and, when one exists, the "
        "history that breaks the rule. Call this before handing a .eleph file "
        "to anyone."
    ),
)
def eleph_check(source: str, bound: int | None = None, objects: int | None = None) -> str:
    """Verify a policy. `source` is the text of a .eleph file.

    Leave `bound` and `objects` unset: the defaults are the completeness
    thresholds, and that is what makes the result a proof rather than a search.
    """
    return _on_temp_file(source, _print_report, bound, objects, False)


@server.tool(
    title="Show what an eleph policy demands",
    description=(
        "Print the correctness conditions derived from the policy's text "
        "without trying to discharge them. Use it to explain what a file "
        "promises, or to see the path condition behind an obligation."
    ),
)
def eleph_obligations(source: str) -> str:
    """List the derived obligations. `source` is the text of a .eleph file."""
    return _on_temp_file(source, _print_obligations, False)


@server.tool(
    title="Replay a history against an eleph policy",
    description=(
        "Feed a sequence of events to a guard built from this policy, then ask "
        "what is true and what it would refuse. This answers 'does the policy "
        "say what I meant', which a proof does not: a proof says each "
        "obligation holds, not that the rule is the one you wanted."
    ),
)
def eleph_simulate(
    source: str,
    events: list[list[str]],
    ask: list[list[str]] | None = None,
) -> str:
    """Run a policy over a history.

    `events` is a list like [["subscribed", "ana"], ["cancelled", "ana"]].
    `ask` is a list of facts to evaluate afterwards, same shape. Every entry is
    a name followed by its arguments, as strings.
    """
    try:
        policy = Policy(source)
    except (ParseError, LexError, ResolveError) as exc:
        return _syntax_error(exc)

    lines = []
    try:
        guard = policy.guard()
    except (ResolveError, UnknownName) as exc:
        return _syntax_error(exc)

    for entry in events:
        if not entry:
            continue
        name, *args = entry
        try:
            guard.record(name, *args)
            lines.append(f"  recorded  {name}({', '.join(args)})")
        except (UnknownName, Refusal) as exc:
            lines.append(f"  REFUSED   {name}({', '.join(args)})  -  {exc}")

    if ask:
        lines.append("")
        for entry in ask:
            if not entry:
                continue
            name, *args = entry
            try:
                holds = guard.holds(name, *args)
                lines.append(f"  {name}({', '.join(args)}) = {holds}")
            except (UnknownName, NotPermitted, Ungrounded) as exc:
                lines.append(f"  {name}({', '.join(args)})  -  {exc}")

    owed = guard.outstanding()
    broken = guard.breached()
    if owed or broken:
        lines.append("")
        for c in owed:
            lines.append(f"  ABERTA    {c.describe()}")
        for c in broken:
            lines.append(f"  QUEBRADA  {c.describe()}")

    lines.append("")
    lines.append(f"  {len(guard.events)} world events in the log")
    return "\n".join(lines)


@server.tool(
    title="What this policy declares",
    description=(
        "The sorts, events and facts a policy declares, with each fact "
        "expanded to the formula it stands for. Use it to orient in an "
        "unfamiliar file before changing it."
    ),
)
def eleph_declarations(source: str) -> str:
    """List what a policy declares, with fact bodies resolved."""
    from . import ast as A
    from .core import Resolver

    try:
        program = parse(source)
        analysis = derive(program)
        resolver = Resolver(program)
    except (ParseError, LexError, ResolveError) as exc:
        return _syntax_error(exc)

    lines = [f"program {program.name}", ""]
    if program.sorts:
        lines.append("sorts")
        for s in program.sorts:
            lines.append(f"  {s.name}")
        lines.append("")

    lines.append("events")
    for e in program.events:
        if e.synthetic:
            continue
        params = ", ".join(
            f"{p.name}: {p.sort}" if p.sort else p.name for p in e.params
        )
        lines.append(f"  {e.name}({params})")

    lines.append("")
    lines.append("facts")
    for f in program.facts:
        params = ", ".join(p.name for p in f.params)
        env = {p.name: p.sort for p in f.params}
        try:
            # A fact is a named formula. Showing the name without the formula
            # is showing the label off a jar.
            body = show(resolver.resolve(A.Ref(f.name, tuple(p.name for p in f.params)), env))
        except (ResolveError, RecursionError) as exc:
            body = f"<nao resolvido: {exc}>"
        lines.append(f"  {f.name}({params}) := {body}")

    lines.append("")
    for h in program.handlers:
        gate = f" permitted {h.permission.name}" if h.permission else ""
        lines.append(f"  on {h.performative}({h.caller}, {h.subject.name}){gate}   linha {h.line}")

    lines.append("")
    lines.append(
        f"{len(analysis.obligations)} obligations derived from this text. "
        f"Run eleph_check to discharge them."
    )
    return "\n".join(lines)


def main() -> None:
    server.run()


if __name__ == "__main__":
    main()

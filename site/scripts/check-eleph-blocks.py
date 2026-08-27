#!/usr/bin/env python3
"""Run the real checker over every `eleph` block on the site.

The project rule is that no number goes out unread by hand. The same applies
to a program: a language site that prints a program which does not parse is
making a claim it never ran. This walks every ```eleph fence, and for the ones
that are whole programs, hands them to `eleph check`.

Fragments (a lone fact, a handler with no program header) are parsed inside a
minimal wrapper, so a broken one is still caught.

    python site/scripts/check-eleph-blocks.py
"""
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCES = [ROOT / "site/src/content", ROOT / "site/src/snippets", ROOT / "skills"]


def blocks(path):
    lang, buf, start = None, [], 0
    for i, line in enumerate(path.read_text().split("\n"), 1):
        stripped = line.lstrip()
        if stripped.startswith("```"):
            if lang is None:
                lang, buf, start = stripped[3:].strip(), [], i
            else:
                if lang == "eleph":
                    yield start, "\n".join(buf)
                lang = None
            continue
        if lang is not None:
            buf.append(line)


def check(source):
    """Run the checker on a whole program. Returns the error, or None.

    Only exit 2 counts as a failure: that is a lexer, parser or resolver
    rejection, which means the page is printing something that is not a
    program. Exit 1 is REPROVADO, and several pages print a failing program on
    purpose, because being able to show one is the point of the language.
    """
    with tempfile.NamedTemporaryFile("w", suffix=".eleph", delete=False) as fh:
        fh.write(source + "\n")
        tmp = fh.name
    try:
        out = subprocess.run(
            ["eleph", "check", tmp, "--no-color"],
            capture_output=True, text=True, timeout=180,
        )
        if out.returncode == 2:
            return (out.stderr or out.stdout).strip().split("\n")[0]
    except subprocess.TimeoutExpired:
        return "timeout"
    finally:
        pathlib.Path(tmp).unlink(missing_ok=True)
    return None


def main():
    failures, whole, fragments = [], 0, 0
    for root in SOURCES:
        if not root.exists():
            continue
        for path in sorted(list(root.rglob("*.mdx")) + list(root.rglob("*.md"))):
            for line, source in blocks(path):
                if not source.strip():
                    continue
                # An excerpt cannot be checked: a handler body or a lone fact
                # has no program around it, and inventing one invents its
                # declarations too, which tests the invention and not the page.
                if not re.search(r"^\s*program\s+\w+", source, re.M):
                    fragments += 1
                    continue
                whole += 1
                problem = check(source)
                if problem:
                    failures.append((path.relative_to(ROOT), line, problem))

    for path, line, problem in failures:
        print(f"  {path}:{line}  {problem}")
    print(
        f"\n{whole} programas completos checados, {len(failures)} rejeitados; "
        f"{fragments} trechos nao verificaveis isoladamente"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

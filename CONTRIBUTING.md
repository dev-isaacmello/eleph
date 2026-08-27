# Contributing

Thank you for looking. A few things about how this project works that are
worth knowing before you spend time on it.

## The one rule

**Do not publish a number you have not read by hand.**

Every quantitative claim in this repository survived an audit of individual
cases, and three of them changed as a result. The first count of unconfirmed
writes charged a batch under one "yes". The second called an upgrade then
cancel a violation, which the policy expressly allows. The third modelled a
mutable attribute with "happened once". Each correction made the number
smaller and the claim stronger.

If you add a measurement, add the hand audit that justifies it, and say in the
docstring what you checked.

## Setup

```bash
uv venv && uv pip install -e ".[dev]"
pytest -q
```

The τ-bench tests download about 6 MB on first run and skip cleanly with no
network.

## What a good change looks like

* **A test that would fail without it.** Tests here are the argument, not the
  chore. `tests/test_soundness.py` and `tests/test_incremental.py` exist to try
  to break claims made elsewhere in the codebase; that is the shape to copy.
* **An honest limit, if the change has one.** The "Honest limits" section of
  the README is not marketing hedging. It is verified, and every entry is there
  because something is genuinely not covered. Adding to it is a contribution.
* **Comments that say why, not what.** The code is read by people deciding
  whether to trust it.

## Places help is wanted

* **Mechanising the two theorems in Lean 4**, scoped to the ground fragment.
  Nothing to port exists in mathlib, Rocq or Isabelle, so this would be, as far
  as we can tell, the first mechanised completeness threshold for a temporal
  specification language. Estimated at five to nine working days.
* **A wall clock.** `since_not` knows order, not time. Timestamped events with
  interval comparison would need the completeness argument reworked, which is
  research sized rather than a weekend.
* **Data in events.** `price > 100` is not expressible. Typed payload fields
  survive the last occurrence abstraction if predicates are per event, but the
  Z3 encoding and the threshold both need work.
* **More τ-bench rules.** Baggage allowance by tier and cabin is the obvious
  next one.
* **Snapshotting.** Steady state is constant per event, but opening a log of
  ten million events replays all ten million. A snapshot that can be checked
  against the log, rather than trusted, would keep the derived property.

## Style

Follow the surrounding code. Portuguese in user facing CLI strings, English in
identifiers, docstrings and comments. Do not use the em dash character.

## Releasing

Pushing a tag publishes. `.github/workflows/release.yml` does the work, and
most of what it does is refuse to.

```bash
# 1. bump the single source of truth
$EDITOR pyproject.toml        # version = "0.4.0"

# 2. say what changed
$EDITOR CHANGELOG.md

# 3. commit, tag, push
git commit -am "chore: release 0.4.0"
git tag -a v0.4.0 -m "eleph 0.4.0"
git push origin main --tags
```

The workflow then checks, in order, that the tag agrees with
`pyproject.toml`, that the version has never been published (PyPI never lets a
version be replaced or reused, so this is the last moment it can be caught),
that the tests pass on both the oldest and the newest supported interpreter,
that the artifacts are well formed, and that the built wheel installs into a
clean environment and still proves and refuses the right programs. Only then
does it upload, and cut a GitHub release with the artifacts attached.

`3.11` in that list is not ceremony. The one bug that reached a published
version was a syntax error only 3.11 saw.

`__version__` is read from the installed package metadata rather than written
down a second time. A version repeated in two files is a version that will
eventually disagree with itself, quietly, in a release.

### Setting it up

The workflow needs one repository secret, `PYPI_API_TOKEN`, scoped to this
project rather than to the whole account. It runs in a GitHub environment named
`pypi`, so required reviewers can be added there if uploads should be approved
by a human.

To rehearse without publishing anything, run the workflow manually from the
Actions tab with `dry_run` left checked: everything happens except the upload.

Trusted publishing is the better arrangement if you would rather not keep a
token at all, and would replace the secret with an OIDC exchange.

## Licence

By contributing you agree your work is released under the MIT licence in
[LICENSE](LICENSE).

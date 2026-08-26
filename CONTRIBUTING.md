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

## Licence

By contributing you agree your work is released under the MIT licence in
[LICENSE](LICENSE).

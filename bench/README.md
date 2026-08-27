# Benchmarks and audits

Two different things live here, and they answer two different questions.

## `scaling.py` — does it survive a long history?

A language whose only state is its past has an obvious problem: answering a
question means reading the past. That is quadratic, and it showed.

```bash
python bench/scaling.py
```

The index in `eleph/incremental.py` folds each event in once, in constant time.
The benchmark prints both, side by side, so the claim is measured rather than
asserted. `tests/test_incremental.py` is what says the fast path computes the
same answers as the slow one: `Machine(audit=True)` evaluates every query both
ways and raises if they ever differ.

## `taubench/` — does a published benchmark measure its own policy?

[τ-bench](https://arxiv.org/abs/2406.12045) (ICLR 2025) hands an airline
customer service agent a written policy, says twice that the API does not
enforce it, and scores runs by hashing the final database. So the obligation is
stated, unenforced, and unmeasured.

Two of its rules are written here as `.eleph` facts and replayed over the 200
published gpt-4o airline trajectories:

```bash
python bench/taubench/check.py         # the confirmation rule
python bench/taubench/cancel_check.py  # cancellation eligibility
```

The trajectories and the flight table (about 6 MB, MIT, Sierra Research) are
downloaded on first use and are deliberately not vendored: pointing at the
source is more honest than keeping a copy that can drift.

### What came out of it

Writing the rules down formally did something more interesting than counting
violations. Both rules turned out to be **ambiguous in ways that matter**.

"one `yes`" does not say whether it covers one action or a batch, and the two
readings are **not ordered**: 25 runs only the first flags, 4 only the second.
There is no lenient reading to fall back on. The sentence has to be decided.

"only if travel insurance is bought **and the condition is met**" never says
which condition. Read strictly it forbids 38 cancellations, 26 of which the
**annotated ground truth performs**, so the under specification reaches the gold
labels rather than only the agent. Later versions of the benchmark rewrote
exactly that sentence. The formalisation landed on it without being told where
to look.

None of this says τ-bench is wrong. Its reward is documented and deliberate,
and the paper says outright that `r = 1` "might be a necessary but not
sufficient condition". The claim is narrower: a commitment an agent was told to
keep is not measured by the thing measuring the agent, and it takes one line to
measure it.

`tests/test_taubench.py` pins every number. Each survived a hand audit of
individual cases, and three of them changed as a result.

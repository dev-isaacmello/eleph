<h1 align="center">eleph</h1>

<p align="center">
  <strong>A language whose programs cannot lie.</strong><br>
  Speech acts, a history that is the only state, and correctness conditions
  derived from the program text rather than written beside it.
</p>

<p align="center">
  <a href="https://elephlanguage.vercel.app"><strong>Documentation</strong></a> ·
  <a href="#install">Install</a> ·
  <a href="#use-it-from-python">Python API</a> ·
  <a href="#measured-against-a-published-benchmark">Benchmark</a> ·
  <a href="#honest-limits">Limits</a> ·
  <a href="https://github.com/dev-isaacmello/eleph/blob/main/docs/README.pt-BR.md">Português</a> ·
  <a href="https://github.com/dev-isaacmello/eleph/blob/main/docs/README.es.md">Español</a> ·
  <a href="https://github.com/dev-isaacmello/eleph/blob/main/docs/README.zh-CN.md">中文</a>
</p>

---

*Isaac Mello, 2026. Implements and extends **Elephant 2000**, a programming
language based on speech acts specified by John McCarthy (Stanford, 6 November
1998) and never implemented by him. The design is his. The completeness
thresholds, the commitment obligations, the incremental runtime and the
embeddable API are this project's.*

## Why

An agent asserts things about a customer's record, and it promises to do
things. Today nothing connects either to reality. Output filters check the
text. Nothing checks whether an assertion follows from what actually happened,
and nothing tracks whether a promise was ever kept.

McCarthy's answer, written before the problem existed: make the program say
only what its own history supports, and make its promises debts it has to
settle. Two obligations, both his:

* **An answer must be true.** Every `yes` or `no` must be entailed by the log.
* **A promise must be kept.** The program cannot promise what its history does
  not establish, nor promise what no path through it could ever bring about.

You do not write these conditions. The compiler reads them off the program.

```
$ eleph obligations examples/airline_buggy.eleph

  linha 17  question(Caller, has_reservation)
    resposta yes e verdadeira
      supondo   alguma vez make_reservation(P, F)
      entao     (make_reservation(P, F) e desde entao nenhum cancel_reservation(P, F))
```

Then it tries to break them.

```
$ eleph check examples/airline_buggy.eleph

  X   question(Caller, has_reservation)  linha 17  -  resposta yes e verdadeira

      historico que quebra a obrigacao:
        1. make_reservation(P, F)
        2. cancel_reservation(P, F)

      o programa responde yes, a verdade do log e no
```

The bug is one word. The guard asks *did they make a reservation* where it
should ask *do they have a reservation*. Those are different questions and the
difference is the cancellation. This is McCarthy's own example, and the whole
language exists to make that difference impossible to overlook.

## The past is the only state

There is no assignment in the grammar. This is not an omission. There is
nothing to assign to, because a fact is not stored, it is a query over what
happened:

```
fact has_reservation(P: Passenger, F: Flight) :=
    make_reservation(P, F) since_not cancel_reservation(P, F)
```

An elephant never forgets. Nothing is overwritten, so nothing can drift out of
agreement with the truth. The program's own utterances go into the same log, so
it can be asked what it has already said:

```
if spoke accept to C about make_reservation(P, F):
    decline C
```

## Proof, not spot check

Bounded model checking answers a weaker question than we want: no history *up
to length N* breaks the obligation. For this language's fragment that gap
closes, because the truth of a formula at the end of a history depends only on
**the order of the last occurrence of each atom**. `a since_not b` is exactly
"there is an `a` after the final `b`". Any such configuration is realised by a
history with one position per atom, so a computable threshold

```
N = sum over distinct atoms of k(a),   k(a) = 1, or n+1 under a count
```

makes "no counterexample found" mean "none exists". Each obligation is checked
at its own threshold:

```
PROVADO  -  6 obrigacoes valem para TODO historico, de qualquer tamanho
```

This is not decoration. `examples/fundo.eleph` lies only after seven events,
and a fixed bound of six **approves it**:

```
$ eleph check examples/fundo.eleph --bound 6
SEM CONTRAEXEMPLO  -  dentro dos limites checados, que nao sao exaustivos aqui

$ eleph check examples/fundo.eleph
X   question(C, elite)  -  resposta yes e verdadeira
    1..7. make_reservation(P, F)
```

A formula that puts a compound expression under `since_not` leaves the linear
fragment. Completeness then comes from the monitor's state space, `2^k` for `k`
temporal subformulas, which is exponential in principle and small in practice.
When even that is unaffordable the checker says the run was not exhaustive
rather than pretending.

## Three claims, and the experiments that would break them

**Threshold.** No verdict may change above the computed threshold. Tested by
re checking every obligation of every example at bounds and domains above it.

**Soundness of derivation.** If every obligation is proved, the runtime never
refuses. The runtime refuses exactly when a speech act's truth condition fails,
and the deriver emits `path condition implies truth condition` for each such
act over the same log. Tested by hammering proved programs with random pasts
and random conversations, and confirming the unproved ones do refuse.

**The index computes what the log computes.** See below.

They live in `tests/test_soundness.py` and `tests/test_incremental.py`.

## A history that never stops growing

The obvious objection to a language whose only state is its past is that
answering a question means reading the past. That is quadratic, and it showed:
at four thousand interactions this ran at 46 events per second.

Every operator here has a one step recurrence,
`(a since_not b)@t = a@t or ((a since_not b)@(t-1) and not b@t)`, which is the
dynamic programming reading of past time temporal logic. One lemma makes it
sharp: **an event matching none of a subformula's atoms cannot change its
value.** So folding an event in touches only the keys that event names.

```
$ python bench/scaling.py

interacoes      log   relendo   indice   ganho     ev/s  escala
       500     1134      1.62    0.058     28x    19482       -
      1000     2274      6.15    0.109     56x    20867   x1.87
                       (x3.8)
      2000     4554     24.97    0.208    120x    21890   x1.91
                       (x4.1)
      4000     9100         -    0.381      -    23912   x1.83
      8000    18192         -    0.830      -    21909   x2.18
```

Time doubles when the work doubles, where rereading the log quadrupled.
Measured at 145,564 events in 6.1 s with flat throughput.

Every cell of the index is a pure function of the log, the same function the
naive evaluator computes by rereading it. That is an optimisation of a truth
claim, so it is never trusted. `Machine(audit=True)` answers every query
**both** ways and raises if they differ, over random pasts and histories past
a thousand events.

## Use it from Python

A worked example lives in [`examples/langchain-agent`](https://github.com/dev-isaacmello/eleph/tree/main/examples/langchain-agent):
the same LangChain agent run twice over nine cases, once with a guard
underneath and once without, with identical model, prompt and tools.

The language is the research artifact. What most systems need is smaller, and
it ships as a library:

```python
from eleph import Policy

policy = Policy.from_file("booking.eleph")
assert policy.verify().proved          # the same file, proved statically

g = policy.guard(log="booking.jsonl")  # durable, reopening replays

g.record("make_reservation", "alice", "ba117")
g.holds("has_reservation", "alice", "ba117")                  # True
g.assert_answer("has_reservation", False, "alice", "ba117")   # raises

g.promise("alice", "has_seat", "alice", "ba117",
          before=("board", ("alice", "ba117")))
g.outstanding()        # what is still owed, to whom
```

Three shapes, cheapest first. `python examples/agente.py` runs all three.

| shape | you change | you get |
|---|---|---|
| **observer** | nothing, you feed it events | what is true of the record, and an audit |
| **guard** | assertions and tool calls route through it | ungrounded claims raise instead of shipping |
| **language** | handlers written in `.eleph` | the static proof |

The reason to keep the rules in a policy file rather than writing the checks in
Python is the first line above: **the rules your guard enforces at three in the
morning are the same artifact a solver proved.** A guard whose rules were
proved is a different thing from a guard whose rules someone believed.

Nothing but events is written to disk. The index and the ledger are rebuilt by
living through the past again, so a process that died and came back is
indistinguishable from one that never died. A torn final line is dropped: an
event that was never finished being written is an event that did not happen.

## Measured against a published benchmark

[τ-bench](https://arxiv.org/abs/2406.12045) (ICLR 2025) hands an airline
customer service agent a written policy, says twice that **"the API does not
check these for the agent"**, and scores runs by hashing the final database. The
obligation is stated, unenforced, and unmeasured.

Two of its rules are written here as `.eleph` facts and replayed over the 200
published gpt-4o airline trajectories:

```
$ python bench/taubench/check.py         # the confirmation rule
  gasta na acao                 85 escritas sem confirmacao,  8 em execucoes pontuadas como sucesso
  expira no turno               52 escritas sem confirmacao,  4 em execucoes pontuadas como sucesso

$ python bench/taubench/cancel_check.py  # cancellation eligibility
  seguro E motivo coberto       38 cancelamentos proibidos, 26 deles no gabarito anotado
  ter seguro basta              16 cancelamentos proibidos,  7 deles no gabarito anotado
```

Writing the rules down did something more interesting than counting violations:
both sentences turned out to be **ambiguous in ways that reach the gold
labels**, and later versions of the benchmark rewrote one of them. The
formalisation landed on it without being told where to look.

This is not a claim that τ-bench is wrong. Its reward is documented and
deliberate, and the paper says outright that `r = 1` "might be a necessary but
not sufficient condition". The claim is narrower: a commitment an agent was
told to keep is not measured by the thing measuring the agent, and it takes one
line to measure it.

The full audit, both ambiguities and what each number survived, is in
[`bench/README.md`](https://github.com/dev-isaacmello/eleph/blob/main/bench/README.md). `tests/test_taubench.py` pins every
figure.

## Language

```
sort   Passenger
event  make_reservation(p: Passenger, f: Flight)
fact   has_reservation(P: Passenger, F: Flight) := <temporal expression>
on question(C, has_reservation(P, F)):  ...
on request(C, make_reservation(P, F)):  ...
```

| form | meaning |
|---|---|
| `e(a, b)` | event `e` occurred **at least once** in the past |
| `a since_not b` | `a` occurred and no `b` has occurred since |
| `count e(a) >= n` | how many times `e` occurred |
| `exists P: Sort where φ` | some object satisfies φ now |
| `count P: Sort where φ >= n` | how many do, which is what a seat limit needs |
| `spoke accept to C about e(...)` | the program performed that act in that exchange |
| `e(a, amount > 100)` | a numeric field of the event, tested as it happens |
| `not`, `and`, `or` | as usual |

A handler may be gated on authority, which is McCarthy's eighth speech act and
the one an ordinary review never asks about:

```
on question(Quem, saldo(C)) permitted pode_perguntar(Quem, C):
    answer Quem with saldo(C)
```

A support agent that truthfully reports any customer's balance to whoever asks
has told no lie at all, and every other obligation here would pass it. The
permission joins the path condition, so answers are proved *under* it rather
than checked off to one side, and the runtime fails closed: an answer withheld
is recoverable, an answer leaked is not.

Bare `e(a, b)` meaning *ever happened* is the trap, on purpose: it reads like
"has" and means "made". The verifier is what tells the two apart.

Statements: `answer C yes` / `answer C no` / `answer C with φ`, `record e(...)`,
`accept C`, `decline C`, `release C from φ`, and four strengths of commitment:
`offer C that φ` (willing, not yet owing), `promise C that φ` (true when said),
`promise C eventually φ`, and `promise C that φ before e(...)`.

## Obligations derived

| obligation | checked by |
|---|---|
| answer is true | Z3, at the completeness threshold |
| answer responds to the question asked | Z3 |
| immediate promise holds when made | Z3, over the log plus what the handler just recorded |
| future promise is one some path can bring about | Z3, requiring the path to turn it from false to true |
| argument sorts agree with declarations | compiler, on every fact, used or not |
| an offer is one some path could honour | Z3 |
| no door onto a protected subject is left unlocked | structural |
| every path answers exactly once | structural |
| every request is accepted or declined exactly once | structural |
| outstanding and breached commitments | runtime ledger |

## Honest limits

* **There is no wall clock.** `since_not` knows order, not time. "Cancel within
  24 hours of booking" is not expressible directly. The pattern that works
  today, and the one `bench/taubench/cancel.eleph` uses, is for the host to
  emit the deadline as an event. The clock lives outside the logic, which is
  how event sourced systems handle time anyway.
* **Numeric fields are compared at the instant the event happens.** That is
  what keeps the completeness argument intact, and it is also the limit: you
  can ask whether *this charge* was over 100, not whether the sum of the last
  three was. Aggregate arithmetic over the history is not expressible.
* **The linear completeness threshold covers a fragment.** It holds when every
  `since_not` takes atoms. Outside it, completeness comes from the monitor's
  state space, and past that the checker admits the run was not exhaustive. The
  threshold also grows with the constants: proving something about a capacity
  of 180 needs histories that can hold 180 events.
* **A future promise is checked for keepability, not liveness.** The compiler
  proves some path establishes it. It cannot prove the caller will walk that
  path, because no program can.
* **The index needs locality.** A subformula naming fewer variables than its
  parent makes one event disturb unboundedly many keys. Such programs still
  run, by rereading the log, and `Machine.index.usable` says so.
* **`spoke` names the exchange, not the content.** "Did I already promise this
  exact thing?" is not expressible. "Did I already promise something here?" is.
* **Permission is a fact, not a role system.** `permitted` gates a handler on
  something the log supports, which covers "is this caller authenticated for
  this account". There are no roles, no hierarchy and no delegation.
* **Facts cannot be recursive**, so transitive properties are out of reach.
* **The τ-bench audit reads natural language with a regex.** Assent is matched
  from a generous word list, so counts under report rather than over report.
  Sample violations were read by hand before the numbers were published.
* **The theorems are proved on paper and tested, not mechanised.** A Lean
  artifact for the ground fragment is the next thing worth building.

## Install

```bash
pip install eleph          # or:  uv pip install eleph
```

From source:

```bash
git clone https://github.com/dev-isaacmello/eleph && cd eleph
uv venv && uv pip install -e ".[dev]"
```

## Run

```bash
eleph obligations examples/airline_buggy.eleph   # what the text demands
eleph check       examples/companhia.eleph       # try to break it
eleph run         examples/companhia.eleph examples/voo.session --log /tmp/voo.jsonl
eleph ledger      examples/companhia.eleph /tmp/voo.jsonl   # what it still owes
eleph talk        examples/companhia.eleph examples/conversa.txt --roster alice,bruno,ba117

python examples/agente.py            # the three integration shapes
python bench/scaling.py              # constant time per event
python bench/taubench/check.py       # the benchmark audit
pytest -q                            # 164 tests
```

## Source

McCarthy, John. *Elephant 2000: A Programming Language Based on Speech Acts.*
Stanford, 6 November 1998.

## License

MIT. See [LICENSE](https://github.com/dev-isaacmello/eleph/blob/main/LICENSE).

# The same agent, with and without eleph

A small support agent built with LangChain and Claude, run twice over the same
five cases. The model, the system prompt, the tool names, the tool
descriptions and the tool signatures are **identical** in both halves. The only
difference is whether a `Guard` sits underneath the two tools that write.

That symmetry is the experiment. A comparison where the guarded agent also gets
a better prompt proves nothing.

## Run it

```bash
uv pip install -e "../..[langchain]"

python compare.py               # scripted stand in, no key and no spend
python compare.py --live -n 5   # LangChain and an API key, pay as you go
python compare.py --sdk  -n 5   # Agent SDK over OAuth, draws on your plan
```

`-n` matters. Models are stochastic, and a single run per scenario is an
anecdote. Three consecutive single run comparisons here produced three
different totals before any code changed.

### Which of the two live modes

A Claude.ai subscription and the Anthropic API Console are **separate billing
systems**. A Pro or Max plan does not include API access, and any key generated
in the Console is pay as you go regardless of your plan.

The path that draws on the plan is the **Claude Agent SDK** (or the Claude Code
CLI), which authenticates over OAuth:

```bash
npm install -g @anthropic-ai/claude-code
claude setup-token
```

`--sdk` uses that. `--live` uses LangChain with an API key. Both run the same
policy, backend, scenarios and guarded/unguarded flip; the comparison is always
made within one mode, never across the two.

Two things to know before choosing `--sdk`:

* **`ANTHROPIC_API_KEY` shadows OAuth, silently.** Credentials resolve in
  order and an API key in the environment wins, so you would be paying pay as
  you go while believing you were on your plan. `sdk_agent.py` removes it for
  the duration of the call and restores it afterwards.
* **A plan is licensed for individual use.** Your own agent on your own
  subscription is fine. Serving other people's traffic through one token is
  not, and you would hit the rate limit in seconds anyway. Anything with users
  wants an API key with Console credit.

## What is measured

Not what the agent said. What happened to the data. Each scenario has a known
correct final state and a run passes only if the backend ends up there.

Three of the five scenarios are cases where **doing nothing is correct**. That
balance is deliberate: an agent that always acts scores well on a suite where
acting is always right, and tells you nothing.

| scenario | correct behaviour |
|---|---|
| premissa falsa | ana never cancelled, so her charge is not refundable. Refuse and explain. |
| reembolso legitimo | bruno cancelled and has an open charge. Refund. |
| reembolso em duplicidade | c1 was already refunded. Refunding twice is money out the door, and the backend accepts it without complaint. |
| cancelar quem ja cancelou | diego is already inactive. Nothing to cancel. |
| cancelamento legitimo | elena is active and asked to cancel. Cancel. |

## The policy

Two rules any support team has written down somewhere, and that almost no
system checks:

```
fact active(U: User) := subscribed(U) since_not cancelled(U)
fact outstanding(U: User, C: Charge) := charged(U, C) since_not refunded(U, C)
fact refundable(U: User, C: Charge) := outstanding(U, C) and not active(U)
```

`eleph check policy.eleph` proves them for every history before an agent ever
touches them. There is no `status` column anywhere: whether an account is
active is a query over what happened, so it cannot drift.

## What the guard actually does

```python
@tool
def emitir_reembolso(user: str, charge_id: str) -> str:
    """Emite o reembolso de uma cobranca especifica de um cliente."""
    if guard is not None:
        try:
            guard.require("refundable", user, charge_id)
        except Ungrounded:
            return "RECUSADO pela politica: ..."
    out = backend.refund(user, charge_id)
    if guard is not None:
        guard.record("refunded", user, charge_id)
        guard.promise(user, "settled_back", user, charge_id,
                      before=("statement_closed", (user,)))
    return out
```

Three things happen there that do not happen on the other side. The operation
is refused when the record does not support it. The refund is written to the
log rather than to a mutable field. And the money going back becomes a
**tracked debt** with a deadline, so at the end of the run there is an answer
to "what did we promise and did we deliver". Without the guard, "your refund is
on the way" is text that scrolled past.

## About the offline mode

`compare.py` without `--live` uses `scripted.py`, a stand in that always
follows one plausible policy: look the account up, then do what the customer
asked for. Plenty of real agents behave exactly like that, and it is the
behaviour the guard is meant to catch.

**It is not evidence about how Claude behaves.** A scripted model cannot tell
you how often a real one takes a customer's false premise at face value. It
shows the mechanism, and it lets the plumbing run in CI with no key and no
spend. For a number about a real model, run `--live` with several runs per
scenario, because models are stochastic and a single run is an anecdote.

The same script drives both halves, which is the point: any difference in
outcome comes from the guard.

## Honest limits of this example

* The guard enforces the policy, not intent. Cancelling an active account is
  permitted, so cancelling the *wrong* active account would not be caught here.
* The backend state is replayed into the log once at startup. A real
  integration records events as they happen, which is both simpler and the only
  way the log stays the source of truth.
* There is no clock. "Refund within 24 hours of a charge" would need the host
  to emit the deadline as an event; see the top level README.

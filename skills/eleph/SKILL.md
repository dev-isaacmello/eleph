---
name: eleph
description: "Use when writing, reviewing or debugging an eleph policy (a .eleph file), or when putting an eleph Guard under an agent's tools in Python. Covers the write-check-fix loop, translating existing database columns into events and facts, and the limits that mean a rule cannot be expressed. Trigger on: .eleph files, `eleph check`, `eleph obligations`, `Policy.from_file`, `guard.require`, `guard.assert_answer`, `since_not`, or a request to stop an agent asserting things its records do not support."
---

# eleph

A language whose programs cannot lie. You are most likely here to write a
policy file or to put a guard under an agent's tools.

## The one rule

**Never hand over a `.eleph` file you have not run through `eleph check`.**

This is not a style preference. The entire project exists because believing a
rule without checking it is the failure mode, and a policy that looks right and
is wrong is worse than one that obviously does not compile. The checker is
cheap, it is local, and it prints the exact history that breaks your rule.

If `eleph` is not installed, say so and stop; do not substitute your own
judgement for the solver's.

```bash
uv tool install eleph     # or: pip install eleph
eleph check policy.eleph
```

## The loop

1. Write the policy.
2. `eleph check policy.eleph`.
3. Read the verdict, not the exit code:
   - `PROVADO` — every obligation holds for **every** history, of any length.
   - `SEM CONTRAEXEMPLO` — nothing broke inside a bound that was **not**
     exhaustive. This is not a proof. Do not report it as one.
   - `REPROVADO` — a counterexample exists and is printed as a sequence of
     events. Read it: it tells you what your rule actually says.
4. Fix and repeat. Only then hand it over.

`eleph obligations policy.eleph` prints the conditions without discharging
them, which is what to show a person who asks *what does this file promise*.

## Writing a policy

The whole language is: `program`, `sort`, `event`, `fact`, and `on` handlers.

```eleph
program support

sort User
sort Charge

event authenticated(who: Party, u: User)
event logged_out(who: Party, u: User)
event subscribed(u: User)
event cancelled(u: User)
event refunded(u: User, c: Charge)
event charged_after_cancelling(u: User, c: Charge, amount: Number)

fact authorised(Q: Party, U: User) := authenticated(Q, U) since_not logged_out(Q, U)
fact active(U: User) := subscribed(U) since_not cancelled(U)
fact refundable(U: User, C: Charge) := charged_after_cancelling(U, C, amount > 0) since_not refunded(U, C)

on question(Who, active(U)) permitted authorised(Who, U):
    answer Who with active(U)
```

### Translating what the system already has

| They have | Record | Ask |
|---|---|---|
| `users.active` boolean | `subscribed(u)`, `cancelled(u)` | `active(U) := subscribed(U) since_not cancelled(U)` |
| a nullable `refunded_at` | `refunded(u, c)` | `refunded(U, C) since_not charged(U, C)` |
| `sessions.user_id` | `authenticated(who, u)`, `logged_out(who, u)` | `authorised(Q, U) := authenticated(Q, U) since_not logged_out(Q, U)` |
| a row count | the events | `count P: Sort where φ < n` |

**Record transitions, never states.** `set_active(u, false)` is a column with
extra steps. `cancelled(u)` is an event. If you want to record the same event
twice to mean "still true", you have modelled a state; go back and find the
thing that changed.

## The trap

A bare event atom means *this happened at least once, ever*:

```eleph
make_reservation(P, F)      # reads as "has", means "made"
```

It agrees with "has a reservation" right up until the first cancellation and
never again. This is McCarthy's own bug and the language keeps it reachable on
purpose. When you mean the current state, write `a since_not b`, or better,
answer with the fact itself:

```eleph
answer Caller with has_reservation(P, F)     # cannot be got wrong
```

## Put in the event what the event decides

A rule that reads the account's state *now* to decide something about the past
composes into a hole. This one was proved and still wrong:

```eleph
fact refundable(U, C) := charged(U, C) and not active(U)   # WRONG
```

Cancelling is permitted, so cancel today and a charge from March becomes
refundable. Two permitted actions composing into a forbidden outcome. The fix
is to put *when it fell* into the event's own identity:
`charged_while_active` versus `charged_after_cancelling`.

> A proof says each obligation holds. It does not say the policy is the one you
> meant. Interrogate the rule; do not just get it to pass.

## Stop, do not invent

These are not expressible. If the requirement needs one, say so rather than
approximating it:

- **No wall clock.** `since_not` knows order, not time. "Within 24 hours" needs
  the host to emit the deadline as an event.
- **No aggregates.** You can ask whether *this* charge was over 200, not
  whether the last three sum to more.
- **No recursion in facts**, so no transitive properties.
- **No roles.** `permitted` gates on a fact the log supports. No hierarchy, no
  delegation.
- **`spoke` names the exchange, not the content.** "Did I already promise this
  exact thing" is not expressible.

## The Python side

Two of the three integration shapes need no `.eleph` handlers at all.

```python
from eleph import Policy, Ungrounded, NotPermitted

policy = Policy.from_file("policy.eleph")
assert policy.verify().proved            # the file the solver proved

g = policy.guard(log="events.jsonl")     # durable; reopening replays

g.record("subscribed", "ana")            # the only way anything becomes true
g.holds("active", "ana")                 # -> bool
g.require("refundable", "ana", "c1")     # raises Ungrounded if not
g.assert_answer("active", model_said, "ana")   # the answer axiom

g.promise("ana", "refunded", "ana", "c1",
          before=("statement_closed", ("ana",)))
g.outstanding(); g.breached()
```

Where the guard goes, and only here: **`require` before a tool runs**,
**`assert_answer` before an assertion ships**.

The caller's identity must come from the session, never from a tool parameter
the model fills in, or you have asked the model who it is speaking for.

A refusal should be returned to the model as a tool result so it can explain
itself, not raised through the turn. Never let it retry the same call and
succeed.

## Do not claim

- Do not say eleph reduces token cost. Nothing in the project measures cost.
  What is verified is that a `Guard` makes no model call and no network call.
- Do not report `SEM CONTRAEXEMPLO` as a proof.
- Do not quote a benchmark number you have not run.

## Reference

Source, tests and the checker: https://github.com/dev-isaacmello/eleph

The documentation site serves **every page as Markdown**: append `.md` to any
path. `/llms.txt` is the index and `/llms-full.txt` is the whole corpus in one
file. Prefer those over guessing at the API surface: this language has forms
that look like other languages and do not mean the same thing.

The pages worth fetching first are `use/start-here`, `use/any-model`,
`use/modelling`, `reference/expressions` and `limits`.

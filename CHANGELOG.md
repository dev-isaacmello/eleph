# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[semantic versioning](https://semver.org/).

## [0.4.0]

### Added

* **An MCP server** (`eleph-mcp`, behind the `mcp` extra). Four tools, all
  stateless and none of them touching the disk or the network:
  `eleph_check` discharges every obligation and returns the history that breaks
  the rule; `eleph_obligations` prints the conditions without discharging them;
  `eleph_simulate` replays a sequence of events through a guard and reports
  what it refuses; `eleph_declarations` lists what a policy declares, with each
  fact expanded to the formula it stands for.

  It serves the checker rather than the documentation on purpose. A server that
  only recited the docs would let a model write a policy from memory and hand
  it over unverified, which is the failure this project exists to stop. The
  client already knows how to read a file; what it cannot do is run Z3.

* **A skill** (`plugins/eleph/skills/eleph/SKILL.md`) for the coding assistant
  of somebody using eleph. It carries the write-check-fix loop and the limits
  that mean a rule cannot be expressed, so a model stops instead of
  approximating.

* **The repository is a plugin marketplace**, so installing both is two
  commands rather than a clone and a copy:

      /plugin marketplace add dev-isaacmello/eleph
      /plugin install eleph@eleph

  The plugin carries the skill and the MCP server together, which means the
  skill arrives with the checker already wired up rather than telling the
  reader to go and configure one.

  The MCP server is declared in `plugins/eleph/.mcp.json`. The documented
  filename is `mcp-servers.json`, and that one is not read: with it the
  component inventory reports zero MCP servers, and with `.mcp.json` it reports
  one. Tested against the CLI rather than taken from the page.

### Fixed

* Thirty three fact declarations in the documentation were wrapped across
  lines, which does not parse: a fact body cannot span lines, and the grammar
  page said the opposite in all three languages. A CI step now hands every
  program printed on the documentation site to `eleph check`.

## [0.3.0]

### Added

* **Numeric fields**, compared at the instant the event happens:
  `charged(U, amount > 100)`. The comparison is part of the atom's identity
  rather than a separate fact that could move underneath it, so the
  completeness argument survives and numeric programs are still decided
  exhaustively.
* **Permission**, McCarthy's eighth speech act:
  `on question(Q, saldo(U)) permitted autorizado(Q, U):`. Not whether an answer
  is true, but whether this party was entitled to ask. The permission joins the
  path condition so answers are proved under it, and the runtime fails closed.
* **Offers**: `offer C that φ`, the weakest commitment. Not a debt, because
  nobody has taken it up; what it owes is that some path could honour it.
* **A structural check for unguarded doors.** One handler requiring permission
  and its neighbour requiring none is a locked front door beside an open
  window, and is now reported as a defect.
* **A worked LangChain example** (`examples/langchain-agent`): the same agent
  run with and without a guard, over nine scenarios, against Claude through
  either an API key or the Agent SDK over OAuth.

### Fixed

* Every declared fact is type checked whether anything calls it or not.
  Resolution is lazy, so a fact no handler mentioned was never checked at all.

## [0.2.0]

First public release.

### Added

* **Embeddable Python API** (`eleph.Policy`, `eleph.Guard`). Three integration
  shapes: observer, guard, and the language itself. The rules a guard enforces
  at run time are the same file the checker proves.
* **Completeness thresholds** (`eleph/threshold.py`). `check` became a decision
  procedure rather than a bounded search. The linear threshold covers the atom
  fragment; outside it, completeness comes from the monitor's state space, and
  past that the checker admits the run was not exhaustive.
* **Constant time evaluation of the past** (`eleph/incremental.py`). One step
  recurrences plus a locality lemma. Measured at 140,546 events in 5.7 s with
  flat throughput, where rereading the log was quadratic. `Machine(audit=True)`
  checks the index against the log on every query.
* **Durable append only log** (`eleph/store.py`). Commitments are recorded as
  events, so the ledger is derived rather than snapshotted. A torn final line
  is dropped and the log stays usable.
* **Sorts and quantification.** Typed parameters, `exists P: Sort where`, and
  `count P: Sort where`, which is what a capacity limit needs.
* **Promises about the future.** `promise C eventually φ` and
  `promise C that φ before e(...)`, with a static keepability check and a
  runtime ledger that reports what is outstanding and what was breached.
* **Speech acts as queryable predicates** (`spoke accept to C about e(...)`).
* **Natural language boundary** (`eleph/frontend.py`). The JSON schema the
  model answers into is generated from the program's own handlers.
* **Thread safety.** Concurrent writers are serialised around the index.
* **τ-bench audits** (`bench/taubench/`). The confirmation rule and the
  cancellation eligibility rule, replayed over 200 published trajectories.
* **NP completeness** of the atom fragment, with a SAT reduction that is run
  against brute force rather than only asserted.
* Commands: `obligations`, `check`, `run`, `talk`, `ledger`.
* Documentation in English, Portuguese, Spanish and Mandarin.

### Changed

* Renamed from `elephant2000` to `eleph`.
* Thresholds are computed per obligation instead of a fixed bound of six. That
  bound was unsound: `examples/fundo.eleph` lies only after seven events and a
  bound of six approved it.
* The threshold sums the largest demand per distinct atom rather than per
  syntax node. Thresholds fell roughly threefold and the suite got faster.

### Fixed

* Z3 keeps one global symbol table, so each encoding now uses its own
  namespace. Without it, a name declared at one sort collided with the next.
* The ledger no longer rescans every commitment on every event, which had kept
  the runtime quadratic even with the index in place.
* Sort labels no longer collide (`Party` and `Passenger` both began with `p`),
  which had made two sorts indistinguishable in a counterexample.
* Dischargeability of a future promise now requires a path that turns it from
  false to true. The earlier check accepted any satisfiable formula and was
  therefore vacuous.

## [0.1.0]

Internal. Verifier and runtime for the answer axiom and immediate promises,
bounded at a fixed six events.

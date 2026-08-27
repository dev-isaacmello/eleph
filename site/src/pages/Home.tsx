import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'

import { mdxComponents } from '@/components/mdx'
import { IconArrowRight, IconCheck, IconCopy, IconGitHub } from '@/components/Icons'
import { site } from '@/lib/site'

import AirlineBuggy from '@/snippets/airline-buggy.mdx'
import CheckOutput from '@/snippets/check-output.mdx'
import Fact from '@/snippets/fact.mdx'
import PythonApi from '@/snippets/python.mdx'

function InstallPill() {
  const [copied, setCopied] = useState(false)
  const copy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText('pip install eleph')
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch {
      /* clipboard denied */
    }
  }, [])

  return (
    <span className="install-pill">
      <span aria-hidden="true" style={{ color: 'var(--fg-faint)' }}>
        $
      </span>
      pip install eleph
      <button type="button" onClick={copy} aria-label={copied ? 'Copied' : 'Copy install command'}>
        {copied ? <IconCheck /> : <IconCopy />}
      </button>
    </span>
  )
}

export function Home() {
  return (
    <main id="main" className="home">
      <section className="hero" style={{ borderTop: 0 }}>
        <span className="hero__eyebrow">
          <strong>v{site.version}</strong> · John McCarthy’s Elephant 2000, implemented
        </span>
        <h1>A language whose programs cannot lie.</h1>
        <p className="hero__sub">
          Speech acts, a history that is the only state, and correctness conditions derived
          from the program text rather than written beside it. You do not write the
          conditions. The compiler reads them off the program, then tries to break them.
        </p>
        <div className="hero__actions">
          <Link className="button button--primary" to="/docs/quickstart">
            Get started <IconArrowRight />
          </Link>
          <InstallPill />
          <a className="button button--ghost" href={site.repo} target="_blank" rel="noreferrer">
            <IconGitHub /> GitHub
          </a>
        </div>
      </section>

      {/* The whole argument, in two panels. */}
      <section>
        <p className="section__label">The bug is one word</p>
        <h2 className="section__title">
          The guard asks <em>did they make a reservation</em> where it should ask{' '}
          <em>do they have one</em>.
        </h2>
        <p className="section__lede">
          Those are different questions, and the difference is the cancellation. This is
          McCarthy’s own example, and the whole language exists to make that difference
          impossible to overlook.
        </p>

        <div className="demo">
          <div className="panel">
            <div className="panel__head">
              <span className="panel__dot panel__dot--bad" />
              examples/airline_buggy.eleph
            </div>
            <div className="prose">
              <AirlineBuggy components={{ ...mdxComponents, pre: 'pre' }} />
            </div>
            <p className="panel__note">
              Nothing here is annotated with a contract. There is no assertion, no
              invariant, no test.
            </p>
          </div>

          <div className="panel">
            <div className="panel__head">
              <span className="panel__dot panel__dot--ok" />
              what the checker says
            </div>
            <div className="prose">
              <CheckOutput components={{ ...mdxComponents, pre: 'pre' }} />
            </div>
            <p className="panel__note">
              Not a failing test: a history that breaks the obligation, printed back at
              you.
            </p>
          </div>
        </div>
      </section>

      <section>
        <p className="section__label">The past is the only state</p>
        <h2 className="section__title">There is no assignment in the grammar.</h2>
        <p className="section__lede">
          This is not an omission. There is nothing to assign to, because a fact is not
          stored — it is a query over what happened. An elephant never forgets, so nothing
          is overwritten and nothing can drift out of agreement with the truth.
        </p>
        <div className="demo">
          <div className="panel">
            <div className="panel__head">
              <span className="panel__dot" />a fact, which is a formula about the log
            </div>
            <div className="prose">
              <Fact components={{ ...mdxComponents, pre: 'pre' }} />
            </div>
            <p className="panel__note">
              The program’s own utterances go into the same log, so it can be asked what it
              has already said.
            </p>
          </div>
          <div className="cards" style={{ marginTop: 0 }}>
            <Link className="card" to="/docs/concepts/past-is-state">
              <span className="card__kicker">Concept</span>
              <span className="card__title">A history that is the state</span>
              <span className="card__body">
                Why there is no assignment, and what replaces it.
              </span>
            </Link>
            <Link className="card" to="/docs/concepts/completeness">
              <span className="card__kicker">Concept</span>
              <span className="card__title">Proof, not spot check</span>
              <span className="card__body">
                A computable threshold turns “no counterexample found” into “none exists”.
              </span>
            </Link>
          </div>
        </div>
      </section>

      <section>
        <p className="section__label">Two obligations, both McCarthy’s</p>
        <h2 className="section__title">An answer must be true. A promise must be kept.</h2>
        <p className="section__lede">
          Every <code>yes</code> or <code>no</code> must be entailed by the log. The program
          cannot promise what its history does not establish, nor promise what no path
          through it could ever bring about.
        </p>
        <div className="cards">
          <Link className="card" to="/docs/concepts/obligations">
            <span className="card__kicker">Derived</span>
            <span className="card__title">Ten obligations</span>
            <span className="card__body">
              Discharged by Z3 at the completeness threshold, or structurally by the
              compiler. Nobody writes them.
            </span>
          </Link>
          <Link className="card" to="/docs/concepts/commitments">
            <span className="card__kicker">Runtime</span>
            <span className="card__title">Four strengths of commitment</span>
            <span className="card__body">
              Offer, immediate promise, eventual promise, promise before an event — with a
              ledger that says what is still owed.
            </span>
          </Link>
          <Link className="card" to="/docs/concepts/permission">
            <span className="card__kicker">Authority</span>
            <span className="card__title">Whether you were entitled to ask</span>
            <span className="card__body">
              An agent that truthfully reports any customer’s balance to whoever asks has
              told no lie at all. It is still an incident.
            </span>
          </Link>
        </div>
      </section>

      <section>
        <p className="section__label">Measured, not asserted</p>
        <h2 className="section__title">Every number here was read by hand first.</h2>
        <div className="stats">
          <div className="stat">
            <div className="stat__value">146</div>
            <div className="stat__label">tests, run on 3.11, 3.12 and 3.13</div>
            <div className="stat__source">pytest -q</div>
          </div>
          <div className="stat">
            <div className="stat__value">~24k</div>
            <div className="stat__label">events per second, flat as the log grows</div>
            <div className="stat__source">bench/scaling.py</div>
          </div>
          <div className="stat">
            <div className="stat__value">200</div>
            <div className="stat__label">published τ-bench trajectories replayed</div>
            <div className="stat__source">bench/taubench/</div>
          </div>
          <div className="stat">
            <div className="stat__value">45/45</div>
            <div className="stat__label">guarded agent runs passing, against 30/45</div>
            <div className="stat__source">examples/langchain-agent</div>
          </div>
        </div>
        <div className="cards">
          <Link className="card" to="/docs/performance">
            <span className="card__kicker">Performance</span>
            <span className="card__title">Constant time per event</span>
            <span className="card__body">
              One-step recurrences plus a locality lemma, audited against the naive
              evaluator on every query.
            </span>
          </Link>
          <Link className="card" to="/docs/taubench">
            <span className="card__kicker">Audit</span>
            <span className="card__title">τ-bench does not measure its own policy</span>
            <span className="card__body">
              Two of its rules written as facts, replayed over 200 trajectories. Both turned
              out to be ambiguous in ways that reach the gold labels.
            </span>
          </Link>
          <Link className="card" to="/docs/integration/langchain">
            <span className="card__kicker">Experiment</span>
            <span className="card__title">The same agent, with and without</span>
            <span className="card__body">
              Identical model, prompt and tools. The only difference is whether a guard sits
              under the two tools that write.
            </span>
          </Link>
        </div>
      </section>

      <section>
        <p className="section__label">Use it from Python</p>
        <h2 className="section__title">The language is the research artifact. This is what ships.</h2>
        <p className="section__lede">
          The reason to keep the rules in a policy file rather than writing the checks in
          Python is the second line below: the rules your guard enforces at three in the
          morning are the same artifact a solver proved.
        </p>

        <div className="demo">
          <div className="panel">
            <div className="panel__head">
              <span className="panel__dot" />
              guard.py
            </div>
            <div className="prose">
              <PythonApi components={{ ...mdxComponents, pre: 'pre' }} />
            </div>
          </div>

          <div>
            <div className="shapes" style={{ marginTop: 0 }}>
              <table>
                <thead>
                  <tr>
                    <th>Shape</th>
                    <th>You change</th>
                    <th>You get</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>observer</td>
                    <td>nothing, you feed it events</td>
                    <td>what is true of the record, and an audit</td>
                  </tr>
                  <tr>
                    <td>guard</td>
                    <td>assertions and tool calls route through it</td>
                    <td>ungrounded claims raise instead of shipping</td>
                  </tr>
                  <tr>
                    <td>language</td>
                    <td>
                      handlers written in <code>.eleph</code>
                    </td>
                    <td>the static proof</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p style={{ marginTop: '1rem', color: 'var(--fg-muted)' }}>
              Cheapest first. <code>python examples/agente.py</code> runs all three.{' '}
              <Link to="/docs/python-api">Read the API reference →</Link>
            </p>
          </div>
        </div>
      </section>

      <div className="cta">
        <div>
          <h2>Start with the bug that started it.</h2>
          <p>
            Install, derive the obligations of a nine-line program, and watch the checker
            produce the history that breaks it.
          </p>
        </div>
        <div className="hero__actions" style={{ marginTop: 0 }}>
          <Link className="button button--primary" to="/docs/quickstart">
            Quickstart <IconArrowRight />
          </Link>
          <Link className="button button--ghost" to="/docs/limits">
            Honest limits
          </Link>
        </div>
      </div>
    </main>
  )
}

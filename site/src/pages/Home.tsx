import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'

import { mdxComponents } from '@/components/mdx'
import { IconArrowRight, IconCheck, IconCopy, IconGitHub } from '@/components/Icons'
import { useLocale } from '@/lib/locale'
import { site } from '@/lib/site'

import AirlineBuggy from '@/snippets/airline-buggy.mdx'
import CheckOutput from '@/snippets/check-output.mdx'
import Fact from '@/snippets/fact.mdx'
import PythonApi from '@/snippets/python.mdx'
import { HOME } from './home-copy'

/** Snippets on this page are decoration around prose; they keep their own frame. */
const BARE = { ...mdxComponents, pre: 'pre' as const }

function InstallPill() {
  const [copied, setCopied] = useState(false)
  const { t } = useLocale()
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
      <button type="button" onClick={copy} aria-label={copied ? t.copied : t.copy}>
        {copied ? <IconCheck /> : <IconCopy />}
      </button>
    </span>
  )
}

function Cards({ items, href }: { items: HomeCards; href: (to: string) => string }) {
  return (
    <div className="cards">
      {items.map((c) => (
        <Link className="card" key={c.to} to={href(c.to)}>
          <span className="card__kicker">{c.kicker}</span>
          <span className="card__title">{c.title}</span>
          <span className="card__body">{c.body}</span>
        </Link>
      ))}
    </div>
  )
}

type HomeCards = { kicker: string; title: string; body: string; to: string }[]

export function Home() {
  const { locale, href } = useLocale()
  const c = HOME[locale] ?? HOME.en

  return (
    <main id="main" className="home">
      <section className="hero" style={{ borderTop: 0 }}>
        <span className="hero__eyebrow">
          <strong>v{site.version}</strong> · {c.eyebrow}
        </span>
        <h1>{c.title}</h1>
        <p className="hero__sub">{c.sub}</p>
        <div className="hero__actions">
          <Link className="button button--primary" to={href('/docs/use/start-here')}>
            {c.ctaPrimary} <IconArrowRight />
          </Link>
          <Link className="button button--ghost" to={href('/docs/quickstart')}>
            {c.ctaSecondary}
          </Link>
          <InstallPill />
          <a className="button button--ghost" href={site.repo} target="_blank" rel="noreferrer">
            <IconGitHub /> GitHub
          </a>
        </div>
      </section>

      {/* The whole argument, in two panels. */}
      <section>
        <p className="section__label">{c.bugLabel}</p>
        <h2 className="section__title">{c.bugTitle}</h2>
        <p className="section__lede">{c.bugLede}</p>

        <div className="demo">
          <div className="panel">
            <div className="panel__head">
              <span className="panel__dot panel__dot--bad" />
              examples/airline_buggy.eleph
            </div>
            <div className="prose">
              <AirlineBuggy components={BARE} />
            </div>
            <p className="panel__note">{c.bugPanelNote}</p>
          </div>

          <div className="panel">
            <div className="panel__head">
              <span className="panel__dot panel__dot--ok" />
              {c.checkerPanel}
            </div>
            <div className="prose">
              <CheckOutput components={BARE} />
            </div>
            <p className="panel__note">{c.checkerNote}</p>
          </div>
        </div>
      </section>
      <section>
        <p className="section__label">{c.measuredLabel}</p>
        <h2 className="section__title">{c.measuredTitle}</h2>
        <div className="stats">
          {c.stats.map((s) => (
            <div className="stat" key={s.source + s.value}>
              <div className="stat__value">{s.value}</div>
              <div className="stat__label">{s.label}</div>
              <div className="stat__source">{s.source}</div>
            </div>
          ))}
        </div>
        <Cards items={c.measuredCards} href={href} />
      </section>
      <section>
        <p className="section__label">{c.pythonLabel}</p>
        <h2 className="section__title">{c.pythonTitle}</h2>
        <p className="section__lede">{c.pythonLede}</p>

        <div className="demo">
          <div className="panel">
            <div className="panel__head">
              <span className="panel__dot" />
              guard.py
            </div>
            <div className="prose">
              <PythonApi components={BARE} />
            </div>
          </div>

          <div>
            <div className="shapes" style={{ marginTop: 0 }}>
              <table>
                <thead>
                  <tr>
                    {c.shapeHead.map((h) => (
                      <th key={h}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {c.shapes.map((row) => (
                    <tr key={row[0]}>
                      <td>{row[0]}</td>
                      <td>{row[1]}</td>
                      <td>{row[2]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p style={{ marginTop: '1rem', color: 'var(--fg-muted)' }}>
              {c.shapesNote} <code>python examples/agente.py</code>.{' '}
              <Link to={href('/docs/python-api')}>{c.pythonLabel} →</Link>
            </p>
          </div>
        </div>
      </section>
      <section>
        <p className="section__label">{c.stateLabel}</p>
        <h2 className="section__title">{c.stateTitle}</h2>
        <p className="section__lede">{c.stateLede}</p>
        <div className="demo">
          <div className="panel">
            <div className="panel__head">
              <span className="panel__dot" />
              {c.factPanel}
            </div>
            <div className="prose">
              <Fact components={BARE} />
            </div>
            <p className="panel__note">{c.factNote}</p>
          </div>
          <Cards items={c.cards.slice(0, 2)} href={href} />
        </div>
      </section>
      <section>
        <p className="section__label">{c.obligationsLabel}</p>
        <h2 className="section__title">{c.obligationsTitle}</h2>
        <p className="section__lede">{c.obligationsLede}</p>
        <Cards items={c.cards} href={href} />
      </section>
      <section>
        <p className="section__label">{c.doorsLabel}</p>
        <h2 className="section__title">{c.doorsTitle}</h2>
        <Cards items={c.doors} href={href} />
      </section>

      <div className="cta">
        <div>
          <h2>{c.ctaTitle}</h2>
          <p>{c.ctaBody}</p>
        </div>
        <div className="hero__actions" style={{ marginTop: 0 }}>
          <Link className="button button--primary" to={href('/docs/quickstart')}>
            {c.ctaButton} <IconArrowRight />
          </Link>
          <Link className="button button--ghost" to={href('/docs/limits')}>
            {c.ctaGhost}
          </Link>
        </div>
      </div>
    </main>
  )
}

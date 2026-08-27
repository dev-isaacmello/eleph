import { Link } from 'react-router-dom'

import { site } from '@/lib/site'
import { LOCALES } from '@/lib/nav'

export function Footer() {
  return (
    <footer className="footer">
      <div className="footer__inner">
        <p className="footer__cite">
          Implements and extends <strong>Elephant 2000</strong>, a programming language
          based on speech acts specified by John McCarthy (Stanford, 6 November 1998) and
          never implemented by him. The design is his; the completeness thresholds, the
          commitment obligations, the incremental runtime and the embeddable API are this
          project’s.
        </p>

        <div>
          <div className="footer__links">
            <Link to="/docs">Documentation</Link>
            <a href={site.repo} target="_blank" rel="noreferrer">
              GitHub
            </a>
            <a href={site.pypi} target="_blank" rel="noreferrer">
              PyPI
            </a>
            <a href={site.issues} target="_blank" rel="noreferrer">
              Issues
            </a>
            <Link to="/docs/contributing">Contributing</Link>
          </div>

          <div className="footer__links" style={{ marginTop: '0.6rem' }}>
            {LOCALES.filter((l) => l.href).map((l) => (
              <a key={l.code} href={l.href} target="_blank" rel="noreferrer">
                {l.label}
              </a>
            ))}
          </div>

          <p style={{ marginTop: '0.9rem', color: 'var(--fg-faint)' }}>
            {site.license} licence · © {site.author}, 2026 · v{site.version}
          </p>
        </div>
      </div>
    </footer>
  )
}

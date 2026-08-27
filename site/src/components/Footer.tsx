import { Link } from 'react-router-dom'

import { useLocale } from '@/lib/locale'
import { README_TRANSLATIONS } from '@/lib/nav'
import { site } from '@/lib/site'

const CITE = {
  en: (
    <>
      Implements and extends <strong>Elephant 2000</strong>, a programming language based on
      speech acts specified by John McCarthy (Stanford, 6 November 1998) and never
      implemented by him. The design is his; the completeness thresholds, the commitment
      obligations, the incremental runtime and the embeddable API are this project’s.
    </>
  ),
  'pt-BR': (
    <>
      Implementa e estende o <strong>Elephant 2000</strong>, uma linguagem de programação
      baseada em atos de fala especificada por John McCarthy (Stanford, 6 de novembro de
      1998) e nunca implementada por ele. O projeto é dele; os limiares de completude, as
      obrigações de compromisso, o runtime incremental e a API embutível são deste projeto.
    </>
  ),
  'zh-CN': (
    <>
      {/* No line break may fall between two Han characters: JSX turns it into a
          space, and Chinese does not separate words with one. */}
      本项目实现并扩展了 <strong>Elephant 2000</strong>，这是一门基于言语行为的编程语言，由 John McCarthy 规范设计（斯坦福，1998 年 11 月 6 日），他本人从未将其实现。设计出自他之手；完备性阈值、承诺义务、增量运行时以及可嵌入的 API 则属于本项目。
    </>
  ),
}

export function Footer() {
  const { locale, href, t } = useLocale()

  return (
    <footer className="footer">
      <div className="footer__inner">
        <p className="footer__cite">{CITE[locale] ?? CITE.en}</p>

        <div>
          <div className="footer__links">
            <Link to={href('/docs')}>{t.footerDocs}</Link>
            <a href={site.repo} target="_blank" rel="noreferrer">
              GitHub
            </a>
            <a href={site.pypi} target="_blank" rel="noreferrer">
              PyPI
            </a>
            <a href={site.issues} target="_blank" rel="noreferrer">
              {t.footerIssues}
            </a>
            <Link to={href('/docs/contributing')}>{t.footerContributing}</Link>
          </div>

          <div className="footer__links" style={{ marginTop: '0.6rem' }}>
            <span style={{ color: 'var(--fg-faint)' }}>{t.footerAlsoIn}</span>
            {README_TRANSLATIONS.map((l) => (
              <a key={l.code} href={l.href} target="_blank" rel="noreferrer" lang={l.code}>
                {l.label}
              </a>
            ))}
          </div>

          <p style={{ marginTop: '0.9rem', color: 'var(--fg-faint)' }}>
            {site.license} {t.footerLicence} · © {site.author}, 2026 · v{site.version}
          </p>
        </div>
      </div>
    </footer>
  )
}

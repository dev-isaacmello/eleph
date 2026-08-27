import { Link } from 'react-router-dom'

import { useLocale } from '@/lib/locale'
import { neighbours } from '@/lib/nav'

export function Pager({ href: current }: { href: string }) {
  const { locale, href, t } = useLocale()
  const { prev, next } = neighbours(current, locale)
  if (!prev && !next) return null

  return (
    <nav className="pager" aria-label={t.pagerLabel}>
      {prev ? (
        <Link className="pager__link" to={href(prev.href)}>
          <span className="pager__dir">{t.previous}</span>
          <span className="pager__title">{prev.title}</span>
        </Link>
      ) : (
        <span />
      )}
      {next ? (
        <Link className="pager__link pager__link--next" to={href(next.href)}>
          <span className="pager__dir">{t.next}</span>
          <span className="pager__title">{next.title}</span>
        </Link>
      ) : null}
    </nav>
  )
}

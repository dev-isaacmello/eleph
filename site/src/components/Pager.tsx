import { Link } from 'react-router-dom'

import { neighbours } from '@/lib/nav'

export function Pager({ href }: { href: string }) {
  const { prev, next } = neighbours(href)
  if (!prev && !next) return null

  return (
    <nav className="pager" aria-label="Previous and next page">
      {prev ? (
        <Link className="pager__link" to={prev.href}>
          <span className="pager__dir">← Previous</span>
          <span className="pager__title">{prev.title}</span>
        </Link>
      ) : (
        <span />
      )}
      {next ? (
        <Link className="pager__link pager__link--next" to={next.href}>
          <span className="pager__dir">Next →</span>
          <span className="pager__title">{next.title}</span>
        </Link>
      ) : null}
    </nav>
  )
}

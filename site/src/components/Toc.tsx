import { useEffect, useState } from 'react'

interface Heading {
  id: string
  text: string
  level: 2 | 3
}

/**
 * Read the headings off the rendered article rather than out of the MDX.
 * The DOM is the thing the reader is scrolling, so it is also the thing that
 * should decide what "on this page" means.
 */
export function Toc({
  containerId = 'article',
  contentKey = '',
}: {
  containerId?: string
  /**
   * The route whose MDX is actually in the DOM. It arrives asynchronously, so
   * keying off the URL alone would read the previous page's headings.
   */
  contentKey?: string
}) {
  const [headings, setHeadings] = useState<Heading[]>([])
  const [active, setActive] = useState<string>('')

  useEffect(() => {
    const root = contentKey ? document.getElementById(containerId) : null
    if (!root) {
      setHeadings([])
      return
    }

    const found = Array.from(root.querySelectorAll<HTMLElement>('h2[id], h3[id]')).map(
      (el) => ({
        id: el.id,
        text: el.textContent?.replace(/^#\s*/, '').trim() ?? '',
        level: el.tagName === 'H2' ? (2 as const) : (3 as const),
      }),
    )
    setHeadings(found)
    setActive(found[0]?.id ?? '')

    if (!found.length) return

    // The band is the top third of the viewport: a heading is "current" once
    // it has reached reading position, not once it has left the screen.
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
        if (visible[0]) setActive(visible[0].target.id)
      },
      { rootMargin: '-72px 0px -66% 0px', threshold: 0 },
    )

    for (const h of found) {
      const el = document.getElementById(h.id)
      if (el) observer.observe(el)
    }
    return () => observer.disconnect()
  }, [contentKey, containerId])

  if (headings.length < 2) return <aside className="toc" aria-hidden="true" />

  return (
    <aside className="toc scroll-thin">
      <h2 className="toc__title">On this page</h2>
      <ul className="toc__list">
        {headings.map((h) => (
          <li key={h.id}>
            <a
              className={h.level === 3 ? 'toc__link toc__link--h3' : 'toc__link'}
              href={`#${h.id}`}
              data-active={active === h.id}
              onClick={() => setActive(h.id)}
            >
              {h.text}
            </a>
          </li>
        ))}
      </ul>
    </aside>
  )
}

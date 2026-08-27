import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

function tag(selector: string, create: () => HTMLElement): HTMLElement {
  const found = document.head.querySelector<HTMLElement>(selector)
  if (found) return found
  const made = create()
  document.head.appendChild(made)
  return made
}

/**
 * Keep the canonical link and `og:url` pointed at the page actually being
 * read, using the host the browser is on. The build stamps whatever origin it
 * knows; this is what makes it right per route, and right on a domain the
 * build was never told about.
 */
export function useCanonical() {
  const { pathname } = useLocation()

  useEffect(() => {
    const href = window.location.origin + pathname

    const link = tag('link[rel="canonical"]', () => {
      const el = document.createElement('link')
      el.setAttribute('rel', 'canonical')
      return el
    })
    link.setAttribute('href', href)

    const og = tag('meta[property="og:url"]', () => {
      const el = document.createElement('meta')
      el.setAttribute('property', 'og:url')
      return el
    })
    og.setAttribute('content', href)
  }, [pathname])
}

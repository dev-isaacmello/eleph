import { useLocation } from 'react-router-dom'

import { splitLocale, withLocale, type Locale } from './nav'
import { strings, type Strings } from './ui'

/**
 * The locale is read from the URL rather than held in state, so a link is
 * always enough to describe where you are and a reload cannot disagree with
 * the address bar.
 */
export function useLocale(): {
  locale: Locale
  /** The canonical path, with the locale prefix removed. */
  path: string
  /** Prefix a canonical href for the current locale. */
  href: (to: string) => string
  t: Strings
} {
  const { pathname } = useLocation()
  const { locale, path } = splitLocale(pathname)
  return {
    locale,
    path,
    href: (to: string) => withLocale(locale, to),
    t: strings(locale),
  }
}

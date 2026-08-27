import type { ComponentType } from 'react'

import { DEFAULT_LOCALE, type Locale } from './nav'

export interface PageModule {
  default: ComponentType<{ components?: Record<string, unknown> }>
  meta?: { title?: string; description?: string }
}

/**
 * Every page under `src/content/<locale>` becomes a route, lazily. The glob is
 * the registry: there is no separate list of pages to fall out of date.
 *
 * Routes are keyed canonically (`/docs/...`, no locale prefix), so the same key
 * addresses a page in every language and switching language can keep you on it.
 */
const modules = import.meta.glob('../content/**/*.mdx') as Record<
  string,
  () => Promise<PageModule>
>

function routeOf(file: string, locale: string) {
  const rel = file.replace(`../content/${locale}/`, '').replace(/\.mdx$/, '')
  return rel === 'index' ? '/docs' : `/docs/${rel}`
}

function loadersFor(locale: string) {
  const out = new Map<string, () => Promise<PageModule>>()
  for (const [file, load] of Object.entries(modules)) {
    if (!file.startsWith(`../content/${locale}/`)) continue
    out.set(routeOf(file, locale), load)
  }
  return out
}

const byLocale = new Map<string, Map<string, () => Promise<PageModule>>>()

export function pageLoaders(locale: Locale = DEFAULT_LOCALE) {
  const cached = byLocale.get(locale)
  if (cached) return cached
  const built = loadersFor(locale)
  byLocale.set(locale, built)
  return built
}

/**
 * Resolve a page, falling back to the default locale when a translation does
 * not exist yet. An untranslated page in English beats a 404 in Portuguese.
 */
export function resolvePage(locale: Locale, route: string) {
  const own = pageLoaders(locale).get(route)
  if (own) return { load: own, translated: true }
  const fallback = pageLoaders(DEFAULT_LOCALE).get(route)
  return fallback ? { load: fallback, translated: false } : null
}

/** Does this locale have its own copy of the page? */
export function hasTranslation(locale: Locale, route: string) {
  return pageLoaders(locale).has(route)
}

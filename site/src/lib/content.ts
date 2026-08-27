import type { ComponentType } from 'react'

export interface PageModule {
  default: ComponentType<{ components?: Record<string, unknown> }>
  meta?: { title?: string; description?: string }
}

/**
 * Every page under `src/content/<locale>` becomes a route, lazily. The glob is
 * the registry: there is no separate list of pages to fall out of date, and a
 * file that exists but is not in `nav.ts` still resolves rather than 404ing.
 */
const modules = import.meta.glob('../content/**/*.mdx') as Record<
  string,
  () => Promise<PageModule>
>

function routeOf(file: string, locale: string) {
  const rel = file.replace(`../content/${locale}/`, '').replace(/\.mdx$/, '')
  return rel === 'index' ? '/docs' : `/docs/${rel}`
}

export function pageLoaders(locale = 'en') {
  const out = new Map<string, () => Promise<PageModule>>()
  for (const [file, load] of Object.entries(modules)) {
    if (!file.startsWith(`../content/${locale}/`)) continue
    out.set(routeOf(file, locale), load)
  }
  return out
}

export const loaders = pageLoaders()

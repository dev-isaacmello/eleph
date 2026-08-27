/**
 * The shape of the documentation.
 *
 * Everything the sidebar, the previous/next pager, the breadcrumbs and the
 * router know about the site comes from this one list, so a page cannot exist
 * without being reachable and cannot be reachable without existing.
 */

export type Locale = 'en'

export const DEFAULT_LOCALE: Locale = 'en'

export const LOCALES: { code: Locale | string; label: string; href?: string }[] = [
  { code: 'en', label: 'English' },
  // Translations live as READMEs in the repository until they are ported here.
  {
    code: 'pt-BR',
    label: 'Português',
    href: 'https://github.com/dev-isaacmello/eleph/blob/main/docs/README.pt-BR.md',
  },
  {
    code: 'es',
    label: 'Español',
    href: 'https://github.com/dev-isaacmello/eleph/blob/main/docs/README.es.md',
  },
  {
    code: 'zh-CN',
    label: '中文',
    href: 'https://github.com/dev-isaacmello/eleph/blob/main/docs/README.zh-CN.md',
  },
]

export interface NavItem {
  title: string
  href: string
  /** Shown next to the link in the sidebar. Kept short on purpose. */
  badge?: string
}

export interface NavGroup {
  title: string
  items: NavItem[]
}

export const nav: Record<Locale, NavGroup[]> = {
  en: [
    {
      title: 'Use it in your agent',
      items: [
        { title: 'Start here', href: '/docs/use/start-here' },
        { title: 'Any model, any framework', href: '/docs/use/any-model' },
        { title: 'Modelling your domain', href: '/docs/use/modelling' },
      ],
    },
    {
      title: 'Introduction',
      items: [
        { title: 'What eleph is', href: '/docs' },
        { title: 'Installation', href: '/docs/installation' },
        { title: 'Quickstart', href: '/docs/quickstart' },
        { title: "McCarthy's bug", href: '/docs/the-mccarthy-bug' },
      ],
    },
    {
      title: 'Concepts',
      items: [
        { title: 'The past is the only state', href: '/docs/concepts/past-is-state' },
        { title: 'Obligations, derived', href: '/docs/concepts/obligations' },
        { title: 'Proof, not spot check', href: '/docs/concepts/completeness' },
        { title: 'Commitments', href: '/docs/concepts/commitments' },
        { title: 'Permission', href: '/docs/concepts/permission' },
      ],
    },
    {
      title: 'Language reference',
      items: [
        { title: 'Program structure', href: '/docs/reference/program-structure' },
        { title: 'Temporal expressions', href: '/docs/reference/expressions' },
        { title: 'Statements', href: '/docs/reference/statements' },
        { title: 'Obligations derived', href: '/docs/reference/obligations' },
        { title: 'Grammar', href: '/docs/reference/grammar' },
      ],
    },
    {
      title: 'Tooling',
      items: [
        { title: 'CLI', href: '/docs/cli' },
        { title: 'Python API', href: '/docs/python-api' },
      ],
    },
    {
      title: 'In practice',
      items: [
        { title: 'LangChain agent', href: '/docs/integration/langchain' },
        { title: 'Performance', href: '/docs/performance' },
        { title: 'τ-bench audit', href: '/docs/taubench' },
      ],
    },
    {
      title: 'Project',
      items: [
        { title: 'Honest limits', href: '/docs/limits' },
        { title: 'Changelog', href: '/docs/changelog' },
        { title: 'Contributing', href: '/docs/contributing' },
      ],
    },
  ],
}

/** Flattened reading order, which is what the pager walks. */
export function flatten(locale: Locale = DEFAULT_LOCALE): NavItem[] {
  return nav[locale].flatMap((g) => g.items)
}

export function neighbours(href: string, locale: Locale = DEFAULT_LOCALE) {
  const all = flatten(locale)
  const i = all.findIndex((item) => item.href === href)
  return {
    prev: i > 0 ? all[i - 1] : null,
    next: i >= 0 && i < all.length - 1 ? all[i + 1] : null,
  }
}

export function groupOf(href: string, locale: Locale = DEFAULT_LOCALE) {
  return nav[locale].find((g) => g.items.some((item) => item.href === href))
}

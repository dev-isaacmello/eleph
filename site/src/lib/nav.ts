/**
 * The shape of the documentation, per language.
 *
 * Hrefs are stored unprefixed and canonical (`/docs/...`). The locale prefix is
 * applied at render by `withLocale`, so a page's identity does not change when
 * it is translated and switching language can keep you where you were.
 */

export type Locale = 'en' | 'pt-BR'

export const DEFAULT_LOCALE: Locale = 'en'

export interface LocaleInfo {
  code: Locale
  /** What the menu calls it, in that language. */
  label: string
  /** The `lang` attribute for `<html>`. */
  htmlLang: string
}

export const LOCALES: LocaleInfo[] = [
  { code: 'en', label: 'English', htmlLang: 'en' },
  { code: 'pt-BR', label: 'Português', htmlLang: 'pt-BR' },
]

/**
 * Languages the project has as translated READMEs but not as pages here.
 * They belong in the footer, not in the language menu: a menu entry that
 * navigates off the site is the thing this menu exists to stop doing.
 */
export const README_TRANSLATIONS = [
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

export function isLocale(value: string): value is Locale {
  return LOCALES.some((l) => l.code === value)
}

/** Prefix a canonical href for a locale. The default locale has no prefix. */
export function withLocale(locale: Locale, href: string): string {
  if (locale === DEFAULT_LOCALE) return href
  return href === '/' ? `/${locale}` : `/${locale}${href}`
}

/** Split a pathname into the locale it names and the canonical path under it. */
export function splitLocale(pathname: string): { locale: Locale; path: string } {
  const [, first, ...rest] = pathname.split('/')
  if (first && isLocale(first)) {
    const path = '/' + rest.join('/')
    return { locale: first, path: path === '/' ? '/' : path.replace(/\/$/, '') }
  }
  return { locale: DEFAULT_LOCALE, path: pathname.replace(/(.)\/$/, '$1') }
}

export interface NavItem {
  title: string
  href: string
  badge?: string
}

export interface NavGroup {
  title: string
  items: NavItem[]
}

/** The routes, in reading order. Titles are per language; hrefs are not. */
const STRUCTURE: { group: string; items: string[] }[] = [
  {
    group: 'use',
    items: ['/docs/use/start-here', '/docs/use/any-model', '/docs/use/modelling'],
  },
  {
    group: 'intro',
    items: ['/docs', '/docs/installation', '/docs/quickstart', '/docs/the-mccarthy-bug'],
  },
  {
    group: 'concepts',
    items: [
      '/docs/concepts/past-is-state',
      '/docs/concepts/obligations',
      '/docs/concepts/completeness',
      '/docs/concepts/commitments',
      '/docs/concepts/permission',
    ],
  },
  {
    group: 'reference',
    items: [
      '/docs/reference/program-structure',
      '/docs/reference/expressions',
      '/docs/reference/statements',
      '/docs/reference/obligations',
      '/docs/reference/grammar',
    ],
  },
  { group: 'tooling', items: ['/docs/cli', '/docs/python-api'] },
  {
    group: 'practice',
    items: ['/docs/integration/langchain', '/docs/performance', '/docs/taubench'],
  },
  { group: 'project', items: ['/docs/limits', '/docs/changelog', '/docs/contributing'] },
]

/** Group and page titles, per language. Keyed by the canonical href. */
const TITLES: Record<Locale, { groups: Record<string, string>; pages: Record<string, string> }> = {
  en: {
    groups: {
      use: 'Use it in your agent',
      intro: 'Introduction',
      concepts: 'Concepts',
      reference: 'Language reference',
      tooling: 'Tooling',
      practice: 'In practice',
      project: 'Project',
    },
    pages: {
      '/docs/use/start-here': 'Start here',
      '/docs/use/any-model': 'Any model, any framework',
      '/docs/use/modelling': 'Modelling your domain',
      '/docs': 'What eleph is',
      '/docs/installation': 'Installation',
      '/docs/quickstart': 'Quickstart',
      '/docs/the-mccarthy-bug': "McCarthy's bug",
      '/docs/concepts/past-is-state': 'The past is the only state',
      '/docs/concepts/obligations': 'Obligations, derived',
      '/docs/concepts/completeness': 'Proof, not spot check',
      '/docs/concepts/commitments': 'Commitments',
      '/docs/concepts/permission': 'Permission',
      '/docs/reference/program-structure': 'Program structure',
      '/docs/reference/expressions': 'Temporal expressions',
      '/docs/reference/statements': 'Statements',
      '/docs/reference/obligations': 'Obligations derived',
      '/docs/reference/grammar': 'Grammar',
      '/docs/cli': 'CLI',
      '/docs/python-api': 'Python API',
      '/docs/integration/langchain': 'LangChain agent',
      '/docs/performance': 'Performance',
      '/docs/taubench': 'τ-bench audit',
      '/docs/limits': 'Honest limits',
      '/docs/changelog': 'Changelog',
      '/docs/contributing': 'Contributing',
    },
  },
  'pt-BR': {
    groups: {
      use: 'Use no seu agente',
      intro: 'Introdução',
      concepts: 'Conceitos',
      reference: 'Referência da linguagem',
      tooling: 'Ferramentas',
      practice: 'Na prática',
      project: 'Projeto',
    },
    pages: {
      '/docs/use/start-here': 'Comece por aqui',
      '/docs/use/any-model': 'Qualquer modelo, qualquer framework',
      '/docs/use/modelling': 'Modelando seu domínio',
      '/docs': 'O que é o eleph',
      '/docs/installation': 'Instalação',
      '/docs/quickstart': 'Primeiros passos',
      '/docs/the-mccarthy-bug': 'O bug do McCarthy',
      '/docs/concepts/past-is-state': 'O passado é o único estado',
      '/docs/concepts/obligations': 'Obrigações, derivadas',
      '/docs/concepts/completeness': 'Prova, não amostragem',
      '/docs/concepts/commitments': 'Compromissos',
      '/docs/concepts/permission': 'Permissão',
      '/docs/reference/program-structure': 'Estrutura do programa',
      '/docs/reference/expressions': 'Expressões temporais',
      '/docs/reference/statements': 'Comandos',
      '/docs/reference/obligations': 'Obrigações derivadas',
      '/docs/reference/grammar': 'Gramática',
      '/docs/cli': 'CLI',
      '/docs/python-api': 'API Python',
      '/docs/integration/langchain': 'Agente LangChain',
      '/docs/performance': 'Desempenho',
      '/docs/taubench': 'Auditoria τ-bench',
      '/docs/limits': 'Limites honestos',
      '/docs/changelog': 'Changelog',
      '/docs/contributing': 'Contribuir',
    },
  },
}

export function nav(locale: Locale): NavGroup[] {
  const t = TITLES[locale] ?? TITLES[DEFAULT_LOCALE]
  return STRUCTURE.map((s) => ({
    title: t.groups[s.group],
    items: s.items.map((href) => ({ title: t.pages[href] ?? href, href })),
  }))
}

/** Flattened reading order, which is what the pager walks. */
export function flatten(locale: Locale = DEFAULT_LOCALE): NavItem[] {
  return nav(locale).flatMap((g) => g.items)
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
  return nav(locale).find((g) => g.items.some((item) => item.href === href))
}

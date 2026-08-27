/**
 * Build the client search index from the MDX sources.
 *
 * One record per heading, not one per page: a docs search that lands you on
 * the page and leaves you to scroll is only half the job. The index carries
 * enough prose to rank on, and nothing more, because it ships to the browser.
 */
import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import matter from 'gray-matter'

import { resolveOrigin } from './origin.mjs'
import { mdxToMarkdown } from './mdx-to-markdown.mjs'

const here = path.dirname(fileURLToPath(import.meta.url))
const CONTENT = path.join(here, '..', 'src', 'content')
const OUT = path.join(here, '..', 'src', 'generated', 'search-index.json')
const SITEMAP = path.join(here, '..', 'public', 'sitemap.xml')
const ROBOTS = path.join(here, '..', 'public', 'robots.txt')
const PUBLIC = path.join(here, '..', 'public')
const DEFAULT_LOCALE = 'en'

/** Prefix a canonical route for a locale, the same way the site does. */
const withLocale = (locale, route) =>
  locale === DEFAULT_LOCALE ? route : `/${locale}${route === '/' ? '' : route}`
const ORIGIN = resolveOrigin()

async function walk(dir) {
  const out = []
  for (const entry of await fs.readdir(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) out.push(...(await walk(full)))
    else if (entry.name.endsWith('.mdx')) out.push(full)
  }
  return out
}

/** GitHub's slugger, near enough for the headings we write. */
function slug(text) {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^\p{L}\p{N}\s-]/gu, '')
    .replace(/\s+/g, '-')
}

/** Strip the things that are markup rather than words. */
function plain(line) {
  return line
    .replace(/`([^`]*)`/g, '$1')
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/<[^>]+>/g, ' ')
    .replace(/[*_>|]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

const records = []
const pages = []

for (const file of await walk(CONTENT)) {
  const raw = await fs.readFile(file, 'utf8')
  const { data, content } = matter(raw)

  const rel = path.relative(CONTENT, file).replace(/\\/g, '/')
  const [locale, ...rest] = rel.split('/')
  const route = ('/docs/' + rest.join('/').replace(/\.mdx$/, '')).replace(/\/index$/, '')

  pages.push({ locale, route, raw, title: data.title ?? route, description: data.description })

  let section = { title: data.title ?? route, hash: '', body: [] }
  const flush = () => {
    const body = plain(section.body.join(' ')).slice(0, 400)
    if (!section.title) return
    records.push({
      locale,
      route,
      hash: section.hash,
      page: data.title ?? route,
      title: section.title,
      description: section.hash ? body : (data.description ?? body),
    })
  }

  let inFence = false
  for (const line of content.split('\n')) {
    if (line.trimStart().startsWith('```')) {
      inFence = !inFence
      continue
    }
    if (inFence) continue

    const heading = /^(#{2,3})\s+(.*)$/.exec(line)
    if (heading) {
      flush()
      const title = plain(heading[2])
      section = { title, hash: '#' + slug(title), body: [] }
      continue
    }
    if (line.trim()) section.body.push(line)
  }
  flush()
}

await fs.mkdir(path.dirname(OUT), { recursive: true })
await fs.writeFile(OUT, JSON.stringify(records), 'utf8')

// The sitemap comes from the same walk, so a page cannot be documented and
// unlisted, or listed and absent. Routes are canonical; the locale prefix is
// applied here, the same way the site applies it.
const locales = [...new Set(records.map((r) => r.locale))].sort()

const byLocale = new Map(
  locales.map((locale) => [
    locale,
    ['/', ...new Set(records.filter((r) => r.locale === locale).map((r) => r.route))].sort(),
  ]),
)
const routes = [...byLocale].flatMap(([locale, rs]) => rs.map((r) => withLocale(locale, r)))

// A sitemap entry must be an absolute URL, so without a known origin there is
// nothing honest to write. Say so rather than guessing at a domain.
if (ORIGIN) {
  await fs.writeFile(
    SITEMAP,
    [
      '<?xml version="1.0" encoding="UTF-8"?>',
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
      '        xmlns:xhtml="http://www.w3.org/1999/xhtml">',
      // Each page lists its translations, so a search engine serves a reader
      // the language they are actually reading in.
      ...[...byLocale].flatMap(([locale, rs]) =>
        rs.map((route) =>
          [
            '  <url>',
            `    <loc>${ORIGIN}${withLocale(locale, route)}</loc>`,
            ...[...byLocale]
              .filter(([other, others]) => others.includes(route) || route === '/')
              .map(
                ([other]) =>
                  `    <xhtml:link rel="alternate" hreflang="${other}" ` +
                  `href="${ORIGIN}${withLocale(other, route)}"/>`,
              ),
            '  </url>',
          ].join('\n'),
        ),
      ),
      '</urlset>',
      '',
    ].join('\n'),
    'utf8',
  )
} else {
  await fs.rm(SITEMAP, { force: true })
}

await fs.writeFile(
  ROBOTS,
  ['User-agent: *', 'Allow: /', ...(ORIGIN ? ['', `Sitemap: ${ORIGIN}/sitemap.xml`] : []), ''].join(
    '\n',
  ),
  'utf8',
)

// ---------------------------------------------------------------- markdown
//
// An agent reads a URL. Serving it the page as Markdown costs it far less than
// making it strip a React application first, and it is the same content: both
// come from this walk, so neither can drift from the other.

async function writeUnder(rel, body) {
  const out = path.join(PUBLIC, rel)
  await fs.mkdir(path.dirname(out), { recursive: true })
  await fs.writeFile(out, body, 'utf8')
}

// Wipe what a previous run wrote, so a deleted page cannot linger.
for (const dir of ['docs', ...(await fs.readdir(CONTENT)).filter((d) => d !== DEFAULT_LOCALE)]) {
  await fs.rm(path.join(PUBLIC, dir), { recursive: true, force: true })
}

let written = 0
for (const page of pages) {
  const url = ORIGIN ? ORIGIN + withLocale(page.locale, page.route) : undefined
  const md = mdxToMarkdown(page.raw, {
    title: page.title,
    description: page.description,
    url,
  })
  const rel = withLocale(page.locale, page.route).replace(/^\//, '')
  await writeUnder(`${rel}.md`, md)
  written++
}

// llms.txt is a map, not a corpus: one line per page so a model can pick the
// one it needs instead of pulling all of them.
const pagesByLocale = new Map()
for (const page of pages) {
  if (!pagesByLocale.has(page.locale)) pagesByLocale.set(page.locale, [])
  pagesByLocale.get(page.locale).push(page)
}

const base = ORIGIN || ''

// Reading order, not alphabetical. nav.ts is the single registry of what order
// these pages go in, and a model handed the index should walk it the way a
// person would rather than starting at the changelog.
const navSource = await fs.readFile(path.join(here, '..', 'src', 'lib', 'nav.ts'), 'utf8')
const order = [...navSource.matchAll(/'(\/docs[^']*)'/g)].map((m) => m[1])
const rank = (route) => {
  const i = order.indexOf(route)
  return i === -1 ? Number.MAX_SAFE_INTEGER : i
}

const en = (pagesByLocale.get(DEFAULT_LOCALE) ?? [])
  .slice()
  .sort((a, b) => rank(a.route) - rank(b.route))
const llms = [
  '# eleph',
  '',
  '> A language whose programs cannot lie. Speech acts, a history that is the',
  '> only state, and correctness conditions derived from the program text',
  '> rather than written beside it.',
  '',
  'Every page below is also served as Markdown at the same path with `.md`',
  'appended. Every terminal block in them is a real run, pasted, not an',
  'illustration.',
  '',
  '## Docs',
  '',
  ...en.map(
    (p) => `- [${p.title}](${base}${p.route}.md)${p.description ? `: ${p.description}` : ''}`,
  ),
  '',
  '## Optional',
  '',
  `- [Everything above, as one file](${base}/llms-full.txt)`,
  `- [Source, tests and the checker](https://github.com/dev-isaacmello/eleph)`,
  '',
]
if (pagesByLocale.size > 1) {
  llms.push('## Other languages', '')
  for (const [locale, ps] of pagesByLocale) {
    if (locale === DEFAULT_LOCALE) continue
    llms.push(`- ${locale}: ${base}/${locale}/docs and the same \`.md\` paths (${ps.length} pages)`)
  }
  llms.push('')
}
await writeUnder('llms.txt', llms.join('\n'))

// llms-full.txt is the corpus, for a model that would rather take it all at
// once. English only: three languages of the same thing is not three times the
// information, it is the same information three times.
const full = en
  .map((p) =>
    mdxToMarkdown(p.raw, {
      title: p.title,
      description: p.description,
      url: ORIGIN ? ORIGIN + p.route : undefined,
    }),
  )
  .join('\n---\n\n')
await writeUnder('llms-full.txt', `# eleph, complete documentation\n\n${full}`)

console.log(
  `markdown: ${written} pages, llms.txt with ${en.length} entries, ` +
    `llms-full.txt ${(Buffer.byteLength(full) / 1024).toFixed(0)} KB`,
)

console.log(
  `search index: ${records.length} records` +
    (ORIGIN ? `, sitemap: ${routes.length} routes at ${ORIGIN}` : ', sitemap: skipped (no origin)'),
)

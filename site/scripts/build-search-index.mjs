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

const here = path.dirname(fileURLToPath(import.meta.url))
const CONTENT = path.join(here, '..', 'src', 'content')
const OUT = path.join(here, '..', 'src', 'generated', 'search-index.json')
const SITEMAP = path.join(here, '..', 'public', 'sitemap.xml')
const ROBOTS = path.join(here, '..', 'public', 'robots.txt')
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

for (const file of await walk(CONTENT)) {
  const raw = await fs.readFile(file, 'utf8')
  const { data, content } = matter(raw)

  const rel = path.relative(CONTENT, file).replace(/\\/g, '/')
  const [locale, ...rest] = rel.split('/')
  const route = ('/docs/' + rest.join('/').replace(/\.mdx$/, '')).replace(/\/index$/, '')

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
const DEFAULT_LOCALE = 'en'
const locales = [...new Set(records.map((r) => r.locale))].sort()
const withLocale = (locale, route) =>
  locale === DEFAULT_LOCALE ? route : `/${locale}${route === '/' ? '' : route}`

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

console.log(
  `search index: ${records.length} records` +
    (ORIGIN ? `, sitemap: ${routes.length} routes at ${ORIGIN}` : ', sitemap: skipped (no origin)'),
)

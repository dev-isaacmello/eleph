/**
 * Turn a page's MDX into the plain Markdown an agent should read.
 *
 * The site's components carry meaning that has to survive the trip: a Callout
 * is a warning, a Snippet names the file its code came from, a Source is a
 * path in the repository. Dropping the tags and keeping the text would lose
 * exactly the parts a reader most needs to be told.
 *
 * Code fences are never touched. Every one of them is a real run.
 */

const CALLOUT_LABEL = {
  note: 'NOTE',
  proved: 'PROVED',
  limit: 'LIMIT',
  danger: 'CAREFUL',
}

/** Split a run of text into fenced and unfenced parts, in order. */
function segments(source) {
  const out = []
  let buf = []
  let fence = null
  for (const line of source.split('\n')) {
    const open = /^\s*```(\S*)/.exec(line)
    if (fence === null && open) {
      out.push({ fenced: false, text: buf.join('\n') })
      buf = [line]
      fence = open[1]
      continue
    }
    if (fence !== null && /^\s*```\s*$/.test(line)) {
      buf.push(line)
      out.push({ fenced: true, text: buf.join('\n') })
      buf = []
      fence = null
      continue
    }
    buf.push(line)
  }
  out.push({ fenced: fence !== null, text: buf.join('\n') })
  return out
}

/** Apply a transform to the parts that are prose, leaving fences alone. */
function onProse(source, fn) {
  return segments(source)
    .map((s) => (s.fenced ? s.text : fn(s.text)))
    .join('\n')
}

export function mdxToMarkdown(source, { title, description, url } = {}) {
  let body = source.replace(/^---\n[\s\S]*?\n---\n/, '')

  // The page's own H1 repeats the frontmatter title, which this emits above.
  body = body.replace(/^\s*#\s+.*\n/, '')

  // A Snippet frames a code block and names where the code lives.
  body = body.replace(
    /<Snippet\s+([^>]*?)>\s*\n([\s\S]*?)\n<\/Snippet>/g,
    (_, attrs, inner) => {
      const file = /file="([^"]*)"/.exec(attrs)?.[1]
      const label = /title="([^"]*)"/.exec(attrs)?.[1] ?? file
      return label ? `${label}\n\n${inner}` : inner
    },
  )

  // A Callout is a blockquote whose first line says what kind it is.
  body = body.replace(
    /<Callout\s*([^>]*?)>\s*\n([\s\S]*?)\n<\/Callout>/g,
    (_, attrs, inner) => {
      const type = /type="([^"]*)"/.exec(attrs)?.[1] ?? 'note'
      const heading = /title="([^"]*)"/.exec(attrs)?.[1]
      const label = CALLOUT_LABEL[type] ?? 'NOTE'
      const lead = heading ? `**${label}: ${heading}**` : `**${label}**`
      const quoted = [lead, '', ...inner.split('\n')]
        .map((l) => (l ? `> ${l}` : '>'))
        .join('\n')
      return quoted
    },
  )

  body = body
    .replace(/<Steps>\s*\n?/g, '')
    .replace(/\n?\s*<\/Steps>/g, '')
    .replace(/<li>\s*\n?/g, '- ')
    .replace(/\n?\s*<\/li>/g, '')
    .replace(/<Source\s+file="([^"]*)"\s*\/>/g, '`$1`')
    .replace(/<p className="lede">\s*\n?/g, '')
    .replace(/\n?\s*<\/p>/g, '')
    .replace(/<strong>([\s\S]*?)<\/strong>/g, '**$1**')
    .replace(/<code>([\s\S]*?)<\/code>/g, '`$1`')
    .replace(/<em>([\s\S]*?)<\/em>/g, '*$1*')

  // Anchors written as HTML, which a few pages use for the canonical copies.
  body = body.replace(/<a\s+href="([^"]*)"[^>]*>([\s\S]*?)<\/a>/g, '[$2]($1)')

  // Site-relative links only resolve against the site.
  if (url) {
    const origin = new URL(url).origin
    body = onProse(body, (t) => t.replace(/\]\((\/[^)]*)\)/g, `](${origin}$1)`))
  }

  body = onProse(body, (t) => t.replace(/\n{3,}/g, '\n\n'))

  const head = [`# ${title}`]
  if (description) head.push('', `> ${description}`)
  if (url) head.push('', `Source: ${url}`)
  return `${head.join('\n')}\n\n${body.trim()}\n`
}

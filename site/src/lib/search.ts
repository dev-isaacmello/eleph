import index from '@/generated/search-index.json'

export interface Record {
  locale: string
  route: string
  hash: string
  page: string
  title: string
  description: string
}

const records = index as Record[]

function normalise(s: string) {
  return s
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
}

/**
 * Small enough to score every record on every keystroke, which is why there is
 * no index structure here. Twenty pages is not a search problem.
 */
export function search(query: string, limit = 8): Record[] {
  const terms = normalise(query).split(/\s+/).filter(Boolean)
  if (!terms.length) return []

  const scored: { record: Record; score: number }[] = []

  for (const record of records) {
    const title = normalise(record.title)
    const page = normalise(record.page)
    const body = normalise(record.description)

    let score = 0
    let matchedAll = true

    for (const term of terms) {
      if (title === term) score += 40
      else if (title.startsWith(term)) score += 24
      else if (title.includes(term)) score += 16
      else if (page.includes(term)) score += 8
      else if (body.includes(term)) score += 4
      else {
        matchedAll = false
        break
      }
    }

    if (!matchedAll) continue
    // A whole page beats one of its sections when both match equally.
    if (!record.hash) score += 2
    scored.push({ record, score })
  }

  return scored
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map((s) => s.record)
}

/** Wrap the matched run so the result list can show why it matched. */
export function highlight(text: string, query: string) {
  const term = normalise(query).split(/\s+/).filter(Boolean)[0]
  if (!term) return [text]
  const at = normalise(text).indexOf(term)
  if (at < 0) return [text]
  return [
    text.slice(0, at),
    text.slice(at, at + term.length),
    text.slice(at + term.length),
  ]
}

import { useCallback, useState } from 'react'

import { useLocale } from '@/lib/locale'
import { IconCheck, IconCopy, IconExternal } from './Icons'

/**
 * The same page, as Markdown.
 *
 * Every page is written twice at build time, once as MDX for the browser and
 * once as Markdown for whatever is reading it that is not a browser. This is
 * the control that hands a reader the second one, so pasting a page into a
 * model does not mean pasting a React application into a model.
 */
export function PageActions({ route }: { route: string }) {
  const { locale, t } = useLocale()
  const [copied, setCopied] = useState(false)

  const href =
    (locale === 'en' ? route : `/${locale}${route}`) + '.md'

  const copy = useCallback(async () => {
    try {
      const res = await fetch(href)
      if (!res.ok) return
      await navigator.clipboard.writeText(await res.text())
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch {
      /* offline, or the clipboard was denied; the link still works */
    }
  }, [href])

  return (
    <span className="page-actions">
      <button
        type="button"
        className="page-actions__button"
        onClick={copy}
        data-copied={copied}
      >
        {copied ? <IconCheck /> : <IconCopy />}
        {copied ? t.copiedMarkdown : t.copyMarkdown}
      </button>
      <a
        className="page-actions__button"
        href={href}
        target="_blank"
        rel="noreferrer"
        title={t.viewMarkdown}
        aria-label={t.viewMarkdown}
      >
        <IconExternal />
      </a>
    </span>
  )
}

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useLocale } from '@/lib/locale'
import { shortcutLabel } from '@/lib/platform'
import { withLocale } from '@/lib/nav'
import { highlight, search, type Record } from '@/lib/search'
import { IconSearch } from './Icons'

function Highlighted({ text, query }: { text: string; query: string }) {
  const [before, hit, after] = highlight(text, query)
  if (hit === undefined) return <>{before}</>
  return (
    <>
      {before}
      <mark>{hit}</mark>
      {after}
    </>
  )
}

export function Search() {
  const dialog = useRef<HTMLDialogElement>(null)
  const input = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const navigate = useNavigate()
  const { locale, t } = useLocale()

  const results = useMemo(() => search(query, locale), [query, locale])

  const open = useCallback(() => {
    setQuery('')
    setActive(0)
    dialog.current?.showModal()
    // Autofocus after the dialog is in the top layer, or Safari misses it.
    requestAnimationFrame(() => input.current?.focus())
  }, [])

  const close = useCallback(() => dialog.current?.close(), [])

  const go = useCallback(
    (record: Record) => {
      close()
      navigate(withLocale(locale, record.route) + record.hash)
    },
    [close, navigate, locale],
  )

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        dialog.current?.open ? close() : open()
      }
      if (e.key === '/' && !dialog.current?.open) {
        const el = document.activeElement
        const typing =
          el instanceof HTMLInputElement ||
          el instanceof HTMLTextAreaElement ||
          (el as HTMLElement | null)?.isContentEditable
        if (!typing) {
          e.preventDefault()
          open()
        }
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, close])

  function onFieldKey(e: React.KeyboardEvent) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActive((i) => (results.length ? (i + 1) % results.length : 0))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((i) => (results.length ? (i - 1 + results.length) % results.length : 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      const hit = results[active]
      if (hit) go(hit)
    }
  }

  return (
    <>
      <button type="button" className="search-trigger" onClick={open}>
        <IconSearch />
        <span className="search-trigger__text">{t.searchPlaceholderShort}</span>
        <span className="search-trigger__kbd" aria-hidden="true">
          {shortcutLabel('K')}
        </span>
      </button>

      <dialog
        ref={dialog}
        className="search-dialog"
        aria-label={t.searchLabel}
        onClick={(e) => {
          if (e.target === dialog.current) close()
        }}
      >
        <div className="search-dialog__field">
          <IconSearch />
          <input
            ref={input}
            type="search"
            value={query}
            placeholder={t.searchPlaceholder}
            autoComplete="off"
            spellCheck={false}
            onChange={(e) => {
              setQuery(e.target.value)
              setActive(0)
            }}
            onKeyDown={onFieldKey}
          />
        </div>

        {query && results.length === 0 ? (
          <p className="search-dialog__empty">
            {t.searchEmptyPrefix} <strong>{query}</strong>.
          </p>
        ) : null}

        {results.length > 0 ? (
          <ul className="search-dialog__results scroll-thin">
            {results.map((r, i) => (
              <li key={r.route + r.hash}>
                <a
                  className="search-result"
                  href={r.route + r.hash}
                  data-active={i === active}
                  onMouseEnter={() => setActive(i)}
                  onClick={(e) => {
                    e.preventDefault()
                    go(r)
                  }}
                >
                  {r.hash ? <span className="search-result__crumb">{r.page}</span> : null}
                  <span className="search-result__title">
                    <Highlighted text={r.title} query={query} />
                  </span>
                  {r.description ? (
                    <span className="search-result__body">
                      <Highlighted text={r.description} query={query} />
                    </span>
                  ) : null}
                </a>
              </li>
            ))}
          </ul>
        ) : null}

        {!query ? (
          <p className="search-dialog__empty">
            {t.searchHint} <strong>since_not</strong>, <strong>promise</strong>,{' '}
            <strong>guard</strong>.
          </p>
        ) : null}

        <div className="search-dialog__foot">
          <span>
            <kbd>↑</kbd> <kbd>↓</kbd> {t.searchNavigate}
          </span>
          <span>
            <kbd>↵</kbd> {t.searchOpen}
          </span>
          <span>
            <kbd>esc</kbd> {t.searchClose}
          </span>
        </div>
      </dialog>
    </>
  )
}

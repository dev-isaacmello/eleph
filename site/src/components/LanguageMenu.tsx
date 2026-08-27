import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useLocale } from '@/lib/locale'
import { hasTranslation } from '@/lib/content'
import { LOCALES, withLocale } from '@/lib/nav'
import { IconCheck, IconGlobe } from './Icons'

/**
 * Switches language in place. It keeps you on the page you were reading when
 * that page exists in the language you picked, and drops to that language's
 * documentation index when it does not, which is the only honest thing to do
 * with a page that has not been translated yet.
 */
export function LanguageMenu() {
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const { locale, path, t } = useLocale()
  const current = LOCALES.find((l) => l.code === locale)

  useEffect(() => {
    if (!open) return
    function onDown(e: MouseEvent) {
      if (!box.current?.contains(e.target as Node)) setOpen(false)
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  function switchTo(next: (typeof LOCALES)[number]) {
    setOpen(false)
    if (next.code === locale) return
    const target =
      path === '/' || path === ''
        ? '/'
        : hasTranslation(next.code, path)
          ? path
          : '/docs'
    navigate(withLocale(next.code, target))
  }

  return (
    <div className="langmenu" ref={box}>
      <button
        type="button"
        className="icon-button langmenu__trigger"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label={`${t.language}: ${current?.label ?? 'English'}`}
        title={t.language}
      >
        <IconGlobe />
        <span className="langmenu__current">{current?.label}</span>
      </button>

      {open ? (
        <ul className="langmenu__list" role="menu">
          {LOCALES.map((l) => (
            <li key={l.code} role="none">
              <button
                type="button"
                role="menuitem"
                lang={l.htmlLang}
                data-current={l.code === locale}
                onClick={() => switchTo(l)}
              >
                <span>{l.label}</span>
                {l.code === locale ? <IconCheck /> : null}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}

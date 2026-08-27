import { useEffect, useRef, useState } from 'react'

import { DEFAULT_LOCALE, LOCALES } from '@/lib/nav'
import { IconExternal, IconGlobe } from './Icons'

/**
 * The site itself is English. The other three languages exist as translated
 * READMEs in the repository, so this menu says where each one goes rather than
 * pretending they are pages here: a selector that silently navigates off the
 * site is worse than one that tells you it will.
 */
export function LanguageMenu() {
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)
  const current = LOCALES.find((l) => l.code === DEFAULT_LOCALE)

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

  return (
    <div className="langmenu" ref={box}>
      <button
        type="button"
        className="icon-button langmenu__trigger"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label={`Language: ${current?.label ?? 'English'}`}
        title="Language"
      >
        <IconGlobe />
        <span className="langmenu__current">{current?.label}</span>
      </button>

      {open ? (
        <ul className="langmenu__list" role="menu">
          {LOCALES.map((l) =>
            l.href ? (
              <li key={l.code} role="none">
                <a
                  role="menuitem"
                  href={l.href}
                  target="_blank"
                  rel="noreferrer"
                  onClick={() => setOpen(false)}
                >
                  <span>{l.label}</span>
                  <span className="langmenu__where">
                    README <IconExternal />
                  </span>
                </a>
              </li>
            ) : (
              <li key={l.code} role="none">
                <span role="menuitem" aria-current="true" data-current="true">
                  <span>{l.label}</span>
                  <span className="langmenu__where">this site</span>
                </span>
              </li>
            ),
          )}
        </ul>
      ) : null}
    </div>
  )
}

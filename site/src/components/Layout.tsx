import { useEffect, useRef, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'

import { useCanonical } from '@/lib/canonical'
import { useLocale } from '@/lib/locale'
import { LOCALES } from '@/lib/nav'
import { Footer } from './Footer'
import { Header } from './Header'
import { Sidebar } from './Sidebar'

/* The width below which the sidebar stops being a column and becomes a drawer.
   It has to agree with the `max-width: 900px` block in layout.css: the drawer
   is opened by state here and closed by a media query there, and if the two
   disagree the menu can be left open on a screen that has no button to
   close it. */
const DRAWER_ABOVE = 900

export function Layout({ withSidebar }: { withSidebar: boolean }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const menuButton = useRef<HTMLButtonElement>(null)
  const { pathname, hash } = useLocation()
  const { locale, t } = useLocale()

  useCanonical()

  useEffect(() => {
    const info = LOCALES.find((l) => l.code === locale)
    document.documentElement.lang = info?.htmlLang ?? 'en'
  }, [locale])

  useEffect(() => setMenuOpen(false), [pathname])

  useEffect(() => {
    document.body.style.overflow = menuOpen ? 'hidden' : ''
    return () => {
      document.body.style.overflow = ''
    }
  }, [menuOpen])

  /* Escape is how every other overlay on this page closes, and the drawer
     covers the page, so it has to answer the same key. */
  useEffect(() => {
    if (!menuOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMenuOpen(false)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [menuOpen])

  /* Widening the window past the breakpoint hides the drawer and its close
     button by CSS alone. Without this the menu stays open in state, and the
     scroll lock it sets outlives every way the reader has to lift it. */
  useEffect(() => {
    if (!menuOpen) return
    const wide = window.matchMedia(`(min-width: ${DRAWER_ABOVE + 1}px)`)
    const close = () => wide.matches && setMenuOpen(false)
    close()
    wide.addEventListener('change', close)
    return () => wide.removeEventListener('change', close)
  }, [menuOpen])

  /* Opening a drawer the keyboard never enters is a drawer the keyboard
     cannot use, and closing one while the focus is still on a link inside it
     leaves the focus on something that has slid off the screen. Focus goes in
     on open and comes back to the button on close. */
  const foiAberta = useRef(false)
  useEffect(() => {
    if (menuOpen) {
      foiAberta.current = true
      document.querySelector<HTMLElement>('#sidebar a, #sidebar button')?.focus()
      return
    }
    if (!foiAberta.current) return
    const ativo = document.activeElement
    if (!ativo || ativo === document.body || ativo.closest('#sidebar')) {
      menuButton.current?.focus()
    }
  }, [menuOpen])

  useEffect(() => {
    if (hash) {
      const el = document.getElementById(decodeURIComponent(hash.slice(1)))
      if (el) {
        el.scrollIntoView({ block: 'start' })
        return
      }
    }
    window.scrollTo({ top: 0 })
  }, [pathname, hash])

  const close = () => setMenuOpen(false)

  return (
    <>
      <a className="skip-link" href="#main">
        {t.skipToContent}
      </a>
      <Header
        menuOpen={menuOpen}
        onToggleMenu={() => setMenuOpen((v) => !v)}
        menuButtonRef={menuButton}
      />
      {withSidebar ? (
        <div className="shell">
          <Sidebar open={menuOpen} onClose={close} />
          <Outlet />
        </div>
      ) : (
        /* The landing page has no sidebar column, but on a phone the header
           still shows the menu button, and a button that opens nothing is
           worse than no button: it locked the page's scroll and showed an
           empty screen. The drawer is rendered here too, and hidden by CSS
           at the width where the column layout takes over. */
        <>
          <Sidebar open={menuOpen} onClose={close} drawerOnly />
          <Outlet />
        </>
      )}
      <Footer />
    </>
  )
}
